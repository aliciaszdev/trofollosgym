"""Catálogo de texto, propuestas y notas privadas con autorización por objeto."""
import time
import uuid
from flask import Blueprint, abort, g, jsonify, render_template, request, url_for
from .validation import EQUIPMENT, data, integer, result, revision, text, write


def register_catalog(app, db, protected, audit):
    bp = Blueprint('catalog', __name__)

    def visible(row):
        return row and (g.user['role'] == 'TOP' or row['status'] == 'approved' or row['creator_id'] == g.user['id'])

    def machine(mid, follow=True):
        row = db().execute('SELECT * FROM machines WHERE id=?', (mid,)).fetchone()
        if not visible(row):
            abort(404)
        if follow and row['canonical_id']:
            row = db().execute('SELECT * FROM machines WHERE id=?', (row['canonical_id'],)).fetchone()
        return dict(row)

    def machines(include_archived=False):
        rows = db().execute('SELECT * FROM machines ORDER BY name COLLATE NOCASE').fetchall()
        return [dict(r) for r in rows if visible(r) and (include_archived or r['status'] != 'archived') and not r['canonical_id']]

    def fields(values):
        return dict(name=text(values,'name',120,True), sticker=text(values,'sticker',30).upper() or None,
                    zone=text(values,'zone',120), brand=text(values,'brand',120), model=text(values,'model',120),
                    description=text(values,'description',1500), instructions=text(values,'instructions',1500))

    @bp.get('/catalog')
    @bp.get('/api/machines', endpoint='api_index')
    @protected()
    def index():
        q = request.args.get('q', '').strip()[:120]
        rows = [r for r in machines(request.args.get('archived') == '1') if q.casefold() in r['name'].casefold() or (r['sticker'] and q.casefold() in r['sticker'].casefold())]
        if request.path.startswith('/api/'):
            return jsonify(machines=rows)
        exercises = db().execute('SELECT * FROM exercises WHERE archived=0 ORDER BY name').fetchall()
        return render_template('catalog.html', screen='catalog', machines=rows, exercises=exercises, q=q, equipment=EQUIPMENT)

    @bp.route('/machines/new', methods=['GET','POST'])
    @bp.post('/api/machines', endpoint='api_new_machine')
    @protected()
    def new_machine():
        if request.method == 'GET':
            q = request.args.get('q','').strip()[:120]
            matches = [m for m in machines() if q and (q.casefold() in m['name'].casefold() or (m['sticker'] and q.casefold() in m['sticker'].casefold()))]
            return render_template('catalog.html', screen='machine_form', machine=None, q=q, matches=matches)
        return create_machine()

    @write(db)
    def create_machine():
        values = data()
        f = fields(values)
        if values.get('checked_matches') != 'yes':
            abort(400, 'Busca primero por nombre y número y confirma que no es una coincidencia.')
        mid = str(uuid.uuid4())
        state = 'approved' if g.user['role'] == 'TOP' else 'provisional'
        db().execute('INSERT INTO machines(id,creator_id,name,sticker,zone,brand,model,description,instructions,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                     (mid,g.user['id'],*f.values(),state,int(time.time())))
        if state == 'provisional':
            db().execute('INSERT INTO machine_requests(id,machine_id,creator_id,state) VALUES (?,?,?,?)', (str(uuid.uuid4()),mid,g.user['id'],'pending'))
        audit('machine_created',mid)
        return result({'id':mid},url_for('catalog.detail',mid=mid),201)

    @bp.get('/machines/<mid>')
    @bp.get('/api/machines/<mid>', endpoint='api_detail')
    @protected()
    def detail(mid):
        m = machine(mid)
        proposal = db().execute('SELECT * FROM machine_requests WHERE machine_id=?',(mid,)).fetchone()
        # Public catalog metadata never includes private notes, even for TOP.
        if request.path.startswith('/api/'):
            return jsonify(machine=m, proposal=dict(proposal) if proposal and (proposal['creator_id']==g.user['id'] or g.user['role']=='TOP') else None)
        notes = db().execute('SELECT n.*,m.name AS source_name FROM private_notes n JOIN machines m ON m.id=n.machine_id WHERE n.owner_id=? AND (m.id=? OR m.canonical_id=?) ORDER BY m.created_at', (g.user['id'],m['id'],m['id'])).fetchall()
        history = db().execute('SELECT action,message,created_at FROM request_resolutions WHERE request_id=? ORDER BY created_at,rowid', (proposal['id'],)).fetchall() if proposal and (proposal['creator_id']==g.user['id'] or g.user['role']=='TOP') else []
        own_note = next((n for n in notes if n['machine_id']==m['id']),None)
        return render_template('catalog.html',screen='machine',machine=m,proposal=proposal,notes=notes,own_note=own_note,history=history,
                               targets=[t for t in machines() if t['status']=='approved' and t['id']!=mid])

    @bp.route('/machines/<mid>/edit', methods=['GET','POST'])
    @bp.post('/api/machines/<mid>/edit', endpoint='api_edit_machine')
    @protected()
    def edit_machine(mid):
        if request.method=='GET':
            m=machine(mid,False)
            if g.user['role']!='TOP' and not (m['creator_id']==g.user['id'] and m['status']=='provisional'):
                abort(403)
            return render_template('catalog.html',screen='machine_form',machine=m,matches=[],q='')
        return save_machine(mid)

    @write(db)
    def save_machine(mid):
        m=machine(mid,False); values=data(); revision(m,values)
        if m['canonical_id'] or m['status']=='archived':
            abort(409,'Una máquina archivada o vinculada no se edita.')
        if g.user['role']!='TOP' and not (m['creator_id']==g.user['id'] and m['status']=='provisional'):
            abort(403)
        f=fields(values)
        db().execute('UPDATE machines SET name=?,sticker=?,zone=?,brand=?,model=?,description=?,instructions=?,revision=revision+1 WHERE id=?',(*f.values(),mid))
        if m['status']=='provisional':
            db().execute("UPDATE machine_requests SET state='pending',message='',revision=revision+1 WHERE machine_id=?",(mid,))
            req=db().execute('SELECT id FROM machine_requests WHERE machine_id=?',(mid,)).fetchone()
            db().execute('INSERT INTO request_resolutions VALUES (?,?,?,?,?,?,?)',(str(uuid.uuid4()),req['id'],g.user['id'],'resubmitted','',None,int(time.time())))
        audit('machine_updated',mid)
        return result({'id':mid},url_for('catalog.detail',mid=mid))

    @bp.post('/machines/<mid>/archive')
    @bp.post('/api/machines/<mid>/archive', endpoint='api_archive_machine')
    @protected(top=True)
    @write(db)
    def archive_machine(mid):
        m=machine(mid,False); values=data(); revision(m,values)
        if values.get('confirm')!='yes':
            abort(400,'Confirma el archivado.')
        if m['status']!='approved':
            abort(409,'Resuelve primero la propuesta.')
        db().execute("UPDATE machines SET status='archived',revision=revision+1 WHERE id=?",(mid,))
        audit('machine_archived',mid)
        return result({'id':mid},url_for('catalog.index'))

    @bp.get('/requests')
    @protected()
    def requests():
        rows=db().execute('SELECT r.*,m.name,m.sticker FROM machine_requests r JOIN machines m ON m.id=r.machine_id WHERE (?=1 OR r.creator_id=?) ORDER BY r.rowid DESC',(int(g.user['role']=='TOP'),g.user['id'])).fetchall()
        return render_template('catalog.html',screen='requests',proposals=rows)

    @bp.post('/machines/<mid>/resolve')
    @bp.post('/api/machines/<mid>/resolve', endpoint='api_resolve')
    @protected(top=True)
    @write(db)
    def resolve(mid):
        m=machine(mid,False); values=data(); revision(m,values)
        proposal=db().execute('SELECT * FROM machine_requests WHERE machine_id=?',(mid,)).fetchone()
        if not proposal or proposal['state'] not in ('pending','info'):
            abort(409,'La propuesta ya está resuelta; el creador puede corregirla y reenviarla.')
        action=text(values,'action',20); message=text(values,'message',1500)
        target=None
        if action=='approve':
            db().execute("UPDATE machines SET status='approved',revision=revision+1 WHERE id=?",(mid,))
            state='approved'
        elif action=='link':
            if values.get('confirm')!='yes':
                abort(400,'Confirma la vinculación de referencias.')
            target=machine(text(values,'target_id',64,True))
            if target['id']==mid or target['status']!='approved':
                abort(400,'El destino debe ser otra máquina aprobada.')
            db().execute("UPDATE machines SET status='archived',canonical_id=?,revision=revision+1 WHERE id=?",(target['id'],mid))
            db().execute('UPDATE machines SET canonical_id=? WHERE canonical_id=?',(target['id'],mid))
            # Repair canonical identity, keeping original equipment IDs and textual snapshots.
            db().execute('UPDATE routine_items SET machine_id=? WHERE machine_id=?',(target['id'],mid))
            db().execute('INSERT OR IGNORE INTO exercise_machines SELECT exercise_id,? FROM exercise_machines WHERE machine_id=?',(target['id'],mid))
            db().execute('DELETE FROM exercise_machines WHERE machine_id=?',(mid,))
            state='linked'
        elif action in ('reject','info'):
            if not message:
                abort(400,'Indica el motivo o la información que falta.')
            state='rejected' if action=='reject' else 'info'
            db().execute('UPDATE machines SET revision=revision+1 WHERE id=?',(mid,))
        else:
            abort(400,'Resolución no válida.')
        db().execute('UPDATE machine_requests SET state=?,message=?,revision=revision+1 WHERE id=?',(state,message,proposal['id']))
        db().execute('INSERT INTO request_resolutions VALUES (?,?,?,?,?,?,?)',(str(uuid.uuid4()),proposal['id'],g.user['id'],action,message,target['id'] if target else None,int(time.time())))
        audit('machine_'+action,mid)
        return result({'state':state,'id':target['id'] if target else mid},url_for('catalog.detail',mid=mid))

    @bp.route('/api/machines/<mid>/note', methods=['GET','POST'], endpoint='api_note')
    @bp.post('/machines/<mid>/note')
    @protected()
    def note(mid):
        if request.method=='GET':
            m=machine(mid)
            rows=db().execute('SELECT n.machine_id,n.body,n.revision FROM private_notes n JOIN machines m ON m.id=n.machine_id WHERE n.owner_id=? AND (m.id=? OR m.canonical_id=?)',(g.user['id'],m['id'],m['id'])).fetchall()
            return jsonify(notes=[dict(n) for n in rows])
        return save_note(mid)

    @write(db)
    def save_note(mid):
        m=machine(mid); values=data(); body=text(values,'body',3000)
        current=db().execute('SELECT * FROM private_notes WHERE owner_id=? AND machine_id=?',(g.user['id'],m['id'])).fetchone()
        expected=integer(values.get('revision','0'),0,10**9)
        if expected!=(current['revision'] if current else 0):
            abort(409,'Tu nota ha cambiado. Recarga antes de guardar.')
        db().execute('INSERT INTO private_notes(owner_id,machine_id,body) VALUES (?,?,?) ON CONFLICT(owner_id,machine_id) DO UPDATE SET body=excluded.body,revision=private_notes.revision+1',(g.user['id'],m['id'],body))
        return result({'saved':True},url_for('catalog.detail',mid=m['id']))

    @bp.route('/exercises/new',methods=['GET','POST'])
    @bp.post('/api/exercises', endpoint='api_new_exercise')
    @protected(top=True)
    def new_exercise():
        if request.method=='GET':
            return render_template('catalog.html',screen='exercise_form',exercise=None,machines=[m for m in machines() if m['status']=='approved'],selected=[],equipment=EQUIPMENT)
        return save_exercise()

    @bp.route('/exercises/<eid>/edit',methods=['GET','POST'])
    @bp.post('/api/exercises/<eid>/edit', endpoint='api_edit_exercise')
    @protected(top=True)
    def edit_exercise(eid):
        exercise=db().execute('SELECT * FROM exercises WHERE id=?',(eid,)).fetchone()
        if not exercise:
            abort(404)
        if request.method=='GET':
            selected=[r[0] for r in db().execute('SELECT machine_id FROM exercise_machines WHERE exercise_id=?',(eid,))]
            return render_template('catalog.html',screen='exercise_form',exercise=exercise,machines=[m for m in machines() if m['status']=='approved'],selected=selected,equipment=EQUIPMENT)
        return save_exercise(eid)

    @write(db)
    def save_exercise(eid=None):
        values=data()
        if eid:
            existing=db().execute('SELECT * FROM exercises WHERE id=?',(eid,)).fetchone(); revision(existing,values)
        name=text(values,'name',120,True); description=text(values,'description',1500); muscles=text(values,'muscles',300); equipment=text(values,'equipment',20,True)
        if equipment not in EQUIPMENT:
            abort(400,'Tipo de material no válido.')
        ids=values.get('machine_ids',[]) if request.is_json else values.getlist('machine_ids')
        if not isinstance(ids,list) or len(ids)>100 or any(not isinstance(mid,str) for mid in ids):
            abort(400,'Lista de máquinas no válida.')
        ids=list(dict.fromkeys(ids))
        for mid in ids:
            if not isinstance(mid,str) or machine(mid)['status']!='approved':
                abort(400,'Selecciona máquinas aprobadas.')
        archived=1 if values.get('archived')=='yes' else 0
        if eid:
            db().execute('UPDATE exercises SET name=?,description=?,muscles=?,equipment=?,archived=?,revision=revision+1 WHERE id=?',(name,description,muscles,equipment,archived,eid))
            db().execute('DELETE FROM exercise_machines WHERE exercise_id=?',(eid,))
        else:
            eid=str(uuid.uuid4())
            db().execute('INSERT INTO exercises(id,name,description,muscles,equipment) VALUES (?,?,?,?,?)',(eid,name,description,muscles,equipment))
        db().executemany('INSERT INTO exercise_machines VALUES (?,?)',[(eid,mid) for mid in ids])
        audit('exercise_saved',eid)
        return result({'id':eid},url_for('catalog.index'),201)

    @bp.get('/api/exercises')
    @protected()
    def exercises_api():
        return jsonify(exercises=[dict(r) for r in db().execute('SELECT * FROM exercises WHERE archived=0 ORDER BY name')])

    app.register_blueprint(bp)

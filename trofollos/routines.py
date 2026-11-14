"""Rutinas versionadas, asignación y planificación personal sin solapamientos."""
import hashlib
import json
import time
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, g, jsonify, render_template, request, url_for
from .validation import DAYS, EQUIPMENT, data, dates, integer, result, revision, text, write


def today_madrid():
    return datetime.now(ZoneInfo('Europe/Madrid')).date()


def register_routines(app, db, protected, audit):
    bp=Blueprint('routines',__name__)

    def get_routine(rid, own=False):
        row=db().execute('SELECT r.*,u.role AS owner_role FROM routines r JOIN users u ON u.id=r.owner_id WHERE r.id=?',(rid,)).fetchone()
        if not row:
            abort(404)
        owner=row['owner_id']==g.user['id']
        assigned=db().execute('SELECT 1 FROM routine_assignments WHERE routine_id=? AND user_id=?',(rid,g.user['id'])).fetchone()
        allowed=owner or (not row['archived'] and row['owner_role']=='TOP' and (row['visibility']=='public' or (row['visibility']=='assigned' and assigned)))
        if not allowed:
            abort(404)
        if own and not owner:
            abort(403,'Solo el propietario puede modificar esta rutina. Puedes crear una copia personal.')
        return dict(row)

    def load_version(r, number=None):
        row=db().execute('SELECT * FROM routine_versions WHERE routine_id=? AND number=?',(r['id'],number or r['current_number'])).fetchone()
        if not row:
            abort(404)
        version=dict(row)
        days=[]
        for d in db().execute('SELECT * FROM routine_days WHERE version_id=? ORDER BY weekday',(row['id'],)):
            day=dict(d); day['items']=[]
            for i in db().execute('SELECT * FROM routine_items WHERE version_id=? AND weekday=? ORDER BY position',(row['id'],d['weekday'])):
                item=dict(i); item['reps']=json.loads(item.pop('reps_json'))
                if item['machine_id']:
                    m=db().execute('SELECT * FROM machines WHERE id=?',(item['machine_id'],)).fetchone()
                    item['current_machine_name']=m['name']; item['current_sticker']=m['sticker']; item['machine_status']=m['status']
                day['items'].append(item)
            days.append(day)
        version['days']=days
        return version

    def available(include_archived=False):
        values=[]
        for row in db().execute('SELECT id FROM routines ORDER BY created_at DESC,rowid DESC'):
            try:
                r=get_routine(row['id'])
            except Exception as err:
                if getattr(err,'code',None)==404:
                    continue
                raise
            if not r['archived'] or include_archived:
                values.append(dict(r,version=load_version(r)))
        return values

    def check_shared(r,version):
        if r['visibility']=='private':
            return
        if r['owner_role']!='TOP':
            abort(403)
        for day in version['days']:
            for item in day['items']:
                e=db().execute('SELECT archived FROM exercises WHERE id=?',(item['exercise_id'],)).fetchone()
                if e['archived']:
                    abort(409,'Una rutina publicada no puede incluir ejercicios archivados.')
                if item['machine_id']:
                    m=db().execute('SELECT status FROM machines WHERE id=?',(item['machine_id'],)).fetchone()
                    if m['status']!='approved':
                        abort(409,'Para publicar o asignar, todas las máquinas deben estar aprobadas.')

    def persist(r,version):
        number=r['current_number']+1
        vid=str(uuid.uuid4())
        check_shared(r,version)
        db().execute('INSERT INTO routine_versions VALUES (?,?,?,?,?,?,?)',(vid,r['id'],number,version['name'],version['date_from'],version['date_until'],int(time.time())))
        for day in version['days']:
            db().execute('INSERT INTO routine_days VALUES (?,?,?,?)',(vid,day['weekday'],day['title'],day['rest']))
            for pos,item in enumerate(day['items']):
                db().execute('INSERT INTO routine_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(vid,day['weekday'],item['item_key'],pos,item['exercise_id'],item['machine_id'],item['original_machine_id'],item['exercise_name'],item['machine_name'],item['sticker'],json.dumps(item['reps']),item['rest_seconds']))
        db().execute('UPDATE routines SET current_number=?,revision=revision+1 WHERE id=?',(number,r['id']))
        audit('routine_version_created',r['id'])

    # The initial version uses the same writer as subsequent edits.
    def create(name,start,end,copied_from=None,source=None):
        rid=str(uuid.uuid4())
        db().execute('INSERT INTO routines(id,owner_id,current_number,revision,copied_from,created_at) VALUES (?,?,0,0,?,?)',(rid,g.user['id'],copied_from,int(time.time())))
        r=get_routine(rid)
        version=dict(name=name,date_from=start,date_until=end,days=source['days'] if source else [dict(weekday=i,title='',rest=1,items=[]) for i in range(7)])
        persist(r,version)
        return rid

    def plans():
        return [dict(r) for r in db().execute('SELECT * FROM planning WHERE owner_id=? ORDER BY date_from,id',(g.user['id'],))]

    def plan_revision():
        return hashlib.sha256(json.dumps(plans(),sort_keys=True).encode()).hexdigest()

    @bp.get('/routines')
    @bp.get('/api/routines', endpoint='api_index')
    @protected()
    def index():
        rows=available(request.args.get('archived')=='1')
        if request.path.startswith('/api/'):
            return jsonify(routines=rows)
        return render_template('routines.html',screen='list',routines=rows)

    @bp.route('/routines/new',methods=['GET','POST'])
    @bp.post('/api/routines', endpoint='api_new')
    @protected()
    def new():
        if request.method=='GET':
            return render_template('routines.html',screen='new',today=today_madrid().isoformat())
        return create_route()

    @write(db)
    def create_route():
        values=data(); name=text(values,'name',120,True); start,end=dates(values)
        rid=create(name,start,end)
        return result({'id':rid},url_for('routines.detail',rid=rid),201)

    @bp.get('/routines/<rid>')
    @bp.get('/api/routines/<rid>', endpoint='api_detail')
    @protected()
    def detail(rid):
        r=get_routine(rid); version=load_version(r)
        if request.path.startswith('/api/'):
            return jsonify(routine=r,version=version)
        exercises=db().execute('SELECT * FROM exercises WHERE archived=0 ORDER BY name').fetchall()
        machines=[dict(m) for m in db().execute("SELECT * FROM machines WHERE status!='archived' AND canonical_id IS NULL AND (status='approved' OR creator_id=?) ORDER BY name",(g.user['id'],))]
        users=db().execute('SELECT id,username FROM users WHERE active=1 ORDER BY username').fetchall() if r['owner_id']==g.user['id'] and g.user['role']=='TOP' else []
        selected=[u[0] for u in db().execute('SELECT user_id FROM routine_assignments WHERE routine_id=?',(rid,))] if r['owner_id']==g.user['id'] else []
        return render_template('routines.html',screen='detail',routine=r,version=version,days=DAYS,exercises=exercises,machines=machines,users=users,selected=selected,
                               planning_revision=plan_revision(),today=today_madrid().isoformat())

    @bp.post('/routines/<rid>/edit')
    @bp.post('/api/routines/<rid>/edit', endpoint='api_edit')
    @protected()
    @write(db)
    def edit(rid):
        r=get_routine(rid,True); values=data(); revision(r,values)
        if r['archived']:
            abort(409,'La rutina está archivada.')
        version=load_version(r)
        action=text(values,'action',20,True)
        if action=='metadata':
            start,end=dates(values)
            planned=db().execute("SELECT 1 FROM planning WHERE routine_id=? AND (date_from<? OR (? IS NOT NULL AND (date_until IS NULL OR date_until>?))) LIMIT 1",(rid,start,end,end)).fetchone()
            if planned:
                abort(409,'Hay planificaciones fuera de las nuevas fechas. Conserva la vigencia o ajusta primero esas planificaciones.')
            version.update(name=text(values,'name',120,True),date_from=start,date_until=end)
        elif action=='day':
            weekday=integer(values.get('weekday'),0,6)
            day=version['days'][weekday]; day['title']=text(values,'title',120)
            rest=1 if values.get('rest')=='yes' else 0
            if rest and day['items']:
                abort(409,'Quita primero los ejercicios antes de marcar este día como descanso.')
            day['rest']=rest
        elif action in ('add','update','remove','move'):
            weekday=integer(values.get('weekday'),0,6); day=version['days'][weekday]
            if action=='add':
                eid=text(values,'exercise_id',64,True)
                e=db().execute('SELECT * FROM exercises WHERE id=? AND archived=0',(eid,)).fetchone()
                if not e:
                    abort(400,'Selecciona un ejercicio del catálogo.')
                mid=text(values,'machine_id',64) or None
                m=None
                if mid:
                    m=db().execute("SELECT * FROM machines WHERE id=? AND status!='archived' AND (status='approved' OR creator_id=?)",(mid,g.user['id'])).fetchone()
                    if not m:
                        abort(400,'Selecciona equipamiento visible y activo.')
                item=dict(item_key=str(uuid.uuid4()),exercise_id=eid,machine_id=mid,original_machine_id=mid,exercise_name=e['name'],machine_name=m['name'] if m else '',sticker=m['sticker'] if m else None)
                if len(day['items'])>=50:
                    abort(400,'Máximo de 50 ejercicios por día.')
                day['items'].append(item); day['rest']=0
            else:
                key=text(values,'item_key',64,True)
                item=next((i for i in day['items'] if i['item_key']==key),None)
                if not item:
                    abort(404)
                if action=='remove':
                    day['items'].remove(item)
                elif action=='move':
                    target=integer(values.get('position'),0,len(day['items'])-1)
                    day['items'].remove(item); day['items'].insert(target,item)
            if action in ('add','update'):
                count=integer(values.get('set_count'),1,30)
                same=values.get('same_reps')=='yes'
                if same:
                    reps=[integer(values.get('reps'),1,1000)]*count
                else:
                    raw=values.get('reps_each',[])
                    if not request.is_json:
                        raw=text(values,'reps_each',300).split(',')
                        raw=[r.strip() for r in raw]
                    if not isinstance(raw,list) or len(raw)!=count:
                        abort(400,'Indica una repetición prevista por serie, separada por comas.')
                    reps=[integer(value,1,1000) for value in raw]
                item['reps']=reps; item['rest_seconds']=integer(values.get('rest_seconds'),0,3600)
        else:
            abort(400,'Cambio de rutina no válido.')
        persist(r,version)
        return result({'id':rid,'revision':r['revision']+1},url_for('routines.detail',rid=rid))

    @bp.post('/routines/<rid>/copy')
    @bp.post('/api/routines/<rid>/copy', endpoint='api_copy')
    @protected()
    @write(db)
    def copy(rid):
        r=get_routine(rid)
        if r['archived']:
            abort(409,'La rutina está archivada.')
        version=load_version(r)
        new_id=create((version['name']+' · copia')[:120],version['date_from'],version['date_until'],rid,version)
        return result({'id':new_id},url_for('routines.detail',rid=new_id),201)

    @bp.post('/routines/<rid>/publish')
    @bp.post('/api/routines/<rid>/publish', endpoint='api_publish')
    @protected(top=True)
    @write(db)
    def publish(rid):
        r=get_routine(rid,True); values=data(); revision(r,values)
        if r['archived']:
            abort(409,'La rutina está archivada.')
        visibility=text(values,'visibility',20,True)
        if visibility not in ('private','public','assigned'):
            abort(400,'Visibilidad no válida.')
        recipients=values.get('user_ids',[]) if request.is_json else values.getlist('user_ids')
        if not isinstance(recipients,list) or len(recipients)>1000 or any(not isinstance(uid,str) for uid in recipients):
            abort(400,'Destinatarios no válidos.')
        recipients=list(dict.fromkeys(recipients)) if visibility=='assigned' else []
        if visibility=='assigned' and not recipients:
            abort(400,'Selecciona al menos un destinatario.')
        for uid in recipients:
            if not db().execute('SELECT 1 FROM users WHERE id=? AND active=1',(uid,)).fetchone():
                abort(400,'Uno de los usuarios ya no está activo.')
        check_shared(dict(r,visibility=visibility),load_version(r))
        # Do not silently remove an active personal plan by withdrawing availability.
        if visibility!='public':
            owners=[p[0] for p in db().execute('SELECT DISTINCT owner_id FROM planning WHERE routine_id=?',(rid,))]
            if any(owner!=r['owner_id'] and owner not in recipients for owner in owners):
                abort(409,'Hay usuarios siguiendo esta rutina. Conserva su acceso o espera a que retiren su planificación.')
        db().execute('UPDATE routines SET visibility=?,revision=revision+1 WHERE id=?',(visibility,rid))
        db().execute('DELETE FROM routine_assignments WHERE routine_id=?',(rid,))
        db().executemany('INSERT INTO routine_assignments VALUES (?,?)',[(rid,uid) for uid in recipients])
        audit('routine_published',rid)
        return result({'id':rid},url_for('routines.detail',rid=rid))

    @bp.post('/routines/<rid>/archive')
    @bp.post('/api/routines/<rid>/archive', endpoint='api_archive')
    @protected()
    @write(db)
    def archive(rid):
        r=get_routine(rid,True); values=data(); revision(r,values)
        if values.get('confirm')!='yes':
            abort(400,'Confirma el archivado.')
        if db().execute('SELECT 1 FROM planning WHERE routine_id=?',(rid,)).fetchone():
            abort(409,'Retira primero las planificaciones que utilizan esta rutina.')
        db().execute('UPDATE routines SET archived=1,revision=revision+1 WHERE id=?',(rid,))
        audit('routine_archived',rid)
        return result({'id':rid},url_for('routines.index'))

    @bp.get('/api/routines/<rid>/versions')
    @protected()
    def versions(rid):
        r=get_routine(rid,True)
        return jsonify(versions=[load_version(r,v[0]) for v in db().execute('SELECT number FROM routine_versions WHERE routine_id=? ORDER BY number',(rid,))])

    @bp.get('/planning')
    @bp.get('/api/planning', endpoint='api_planning')
    @protected()
    def planning():
        rows=plans(); signature=plan_revision()
        if request.path.startswith('/api/'):
            return jsonify(plans=rows,revision=signature)
        for row in rows:
            # Ownership of the plan is verified separately from catalog availability.
            routine=db().execute('SELECT name FROM routine_versions WHERE routine_id=? ORDER BY number DESC LIMIT 1',(row['routine_id'],)).fetchone()
            row['name']=routine['name']
        return render_template('routines.html',screen='planning',plans=rows,routines=available(),planning_revision=signature,today=today_madrid().isoformat())

    @bp.post('/planning')
    @bp.post('/api/planning', endpoint='api_select_plan')
    @protected()
    @write(db)
    def select_plan():
        values=data()
        if text(values,'planning_revision',64,True)!=plan_revision():
            abort(409,'Tu planificación ha cambiado. Recarga antes de volver a elegir.')
        rid=text(values,'routine_id',64,True); r=get_routine(rid)
        if r['archived']:
            abort(409,'No puedes planificar una rutina archivada.')
        version=load_version(r); start,end=dates(values)
        if start<version['date_from'] or (version['date_until'] and (not end or end>version['date_until'])):
            abort(400,'El intervalo debe quedar dentro de la vigencia de la rutina.')
        overlaps=[p for p in plans() if (not p['date_until'] or p['date_until']>=start) and (not end or p['date_from']<=end)]
        if overlaps and values.get('replace')!='yes':
            if request.is_json:
                return jsonify(error='Hay solapamientos. Confirma replace=yes para sustituir solo ese intervalo.',conflicts=overlaps),409
            return render_template('routines.html',screen='conflict',conflicts=overlaps,values=values,planning_revision=plan_revision()),409
        for p in overlaps:
            db().execute('DELETE FROM planning WHERE id=?',(p['id'],))
            if p['date_from']<start:
                db().execute('INSERT INTO planning(id,owner_id,routine_id,date_from,date_until) VALUES (?,?,?,?,?)',(str(uuid.uuid4()),g.user['id'],p['routine_id'],p['date_from'],(date.fromisoformat(start)-timedelta(days=1)).isoformat()))
            if end and end<date.max.isoformat() and (not p['date_until'] or p['date_until']>end):
                db().execute('INSERT INTO planning(id,owner_id,routine_id,date_from,date_until) VALUES (?,?,?,?,?)',(str(uuid.uuid4()),g.user['id'],p['routine_id'],(date.fromisoformat(end)+timedelta(days=1)).isoformat(),p['date_until']))
        pid=str(uuid.uuid4())
        db().execute('INSERT INTO planning(id,owner_id,routine_id,date_from,date_until) VALUES (?,?,?,?,?)',(pid,g.user['id'],rid,start,end))
        audit('personal_plan_selected',pid)
        return result({'id':pid},url_for('routines.planning'),201)

    @bp.post('/planning/<pid>/remove')
    @bp.post('/api/planning/<pid>/remove', endpoint='api_remove_plan')
    @protected()
    @write(db)
    def remove_plan(pid):
        values=data()
        if values.get('confirm')!='yes' or text(values,'planning_revision',64,True)!=plan_revision():
            abort(409,'Confirma la retirada desde una planificación actualizada.')
        p=db().execute('SELECT * FROM planning WHERE id=? AND owner_id=?',(pid,g.user['id'])).fetchone()
        if not p:
            abort(404)
        db().execute('DELETE FROM planning WHERE id=?',(pid,))
        return result({'removed':True},url_for('routines.planning'))

    def today_payload(value=None):
        day=value or today_madrid()
        selected=db().execute('SELECT * FROM planning WHERE owner_id=? AND date_from<=? AND (date_until IS NULL OR date_until>=?)',(g.user['id'],day.isoformat(),day.isoformat())).fetchall()
        if len(selected)>1:
            abort(409,'Hay un conflicto de planificación que debes resolver.')
        payload={'date':day.isoformat(),'weekday':DAYS[day.weekday()],'plan':None,'routine':None,'day':None}
        if selected:
            r=get_routine(selected[0]['routine_id']); version=load_version(r)
            payload.update(plan=dict(selected[0]),routine={'id':r['id'],'name':version['name']},day=version['days'][day.weekday()])
        return payload

    @bp.get('/today')
    @bp.get('/api/today', endpoint='api_today')
    @protected()
    def today():
        value=request.args.get('date')
        parsed=None
        if value:
            start,_=dates({'date_from':value}); parsed=date.fromisoformat(start)
        payload=today_payload(parsed)
        if request.path.startswith('/api/'):
            return jsonify(payload)
        return render_template('routines.html',screen='today',today=payload)

    app.register_blueprint(bp)

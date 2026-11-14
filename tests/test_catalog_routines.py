import json
import sqlite3
import time
from datetime import date
import pytest
from test_identity import setup, login, token
from trofollos.app import connect, initialize, ROOT


class Client:
    def __init__(self,app,name):
        self.c=app.test_client(); assert login(self.c,name).status_code==302
    def get(self,path):
        return self.c.get(path)
    def post(self,path,values):
        return self.c.post(path,json=values,headers={'X-CSRF-Token':token(self.c)})
    def machine(self,name='Máquina PRUEBA',sticker=''):
        r=self.post('/api/machines',dict(name=name,sticker=sticker,checked_matches='yes'))
        assert r.status_code==201,r.text
        return r.json['id']
    def exercise(self):
        r=self.post('/api/exercises',dict(name='Ejercicio PRUEBA',equipment='machine',muscles='Pierna',description='Ficha de prueba'))
        assert r.status_code==201,r.text
        return r.json['id']
    def routine(self,name='Rutina PRUEBA'):
        r=self.post('/api/routines',dict(name=name,date_from='2026-01-01',date_until=''))
        assert r.status_code==201,r.text
        return r.json['id']
    def edit(self,rid,**values):
        r=self.get('/api/routines/'+rid).json['routine']
        return self.post('/api/routines/'+rid+'/edit',dict(revision=r['revision'],**values))
    def publish(self,rid,visibility='public',user_ids=None):
        revision=self.get('/api/routines/'+rid).json['routine']['revision']
        return self.post('/api/routines/'+rid+'/publish',dict(revision=revision,visibility=visibility,user_ids=user_ids or []))
    def plan(self,rid,start='2026-11-01',end='',replace=None):
        values=dict(routine_id=rid,date_from=start,date_until=end,planning_revision=self.get('/api/planning').json['revision'])
        if replace: values['replace']=replace
        return self.post('/api/planning',values)
    def resolve(self,mid,action,**values):
        revision=self.get('/api/machines/'+mid).json['machine']['revision']
        return self.post('/api/machines/'+mid+'/resolve',dict(revision=revision,action=action,**values))


@pytest.fixture
def team(setup):
    app,path=setup
    return app,path,Client(app,'owner'),Client(app,'alice'),Client(app,'bob')


def test_catalog_visibility_search_and_ownership(team):
    app,path,top,a,b=team
    provisional=a.machine('Prensa provisional','12')
    assert b.get('/api/machines/'+provisional).status_code==404
    assert b.get('/api/machines?q=12').json['machines']==[]
    assert top.get('/api/machines?q=12').json['machines'][0]['id']==provisional
    assert b.post('/api/machines/'+provisional+'/edit',dict(revision=1,name='No')).status_code==404
    assert a.post('/api/exercises',dict(name='No',equipment='machine')).status_code==403
    approved=top.machine('Aprobada','13')
    assert b.get('/api/machines/'+approved).status_code==200
    assert a.post('/api/machines/'+approved+'/edit',dict(revision=1,name='No')).status_code==403
    assert top.machine('Sin pegatina')
    assert top.post('/api/machines',dict(name='Duplicada',sticker='13',checked_matches='yes')).status_code==409
    assert a.post('/api/machines',dict(name='Sin comprobar')).status_code==400
    assert top.get('/catalog?q=13').status_code==200
    assert provisional in top.get('/requests').text
    assert provisional not in b.get('/requests').text


def test_resolution_lifecycle_and_stale_edits(team):
    app,path,top,a,b=team
    mid=a.machine()
    assert a.resolve(mid,'approve').status_code==403
    assert top.resolve(mid,'reject').status_code==400
    assert top.resolve(mid,'info',message='Falta zona').json['state']=='info'
    rev=a.get('/api/machines/'+mid).json['machine']['revision']
    assert a.post('/api/machines/'+mid+'/edit',dict(revision=1,name='Obsoleta')).status_code==409
    assert a.post('/api/machines/'+mid+'/edit',dict(revision=rev,name='Prensa corregida',zone='Zona PRUEBA')).status_code==200
    assert a.get('/api/machines/'+mid).json['proposal']['state']=='pending'
    assert top.resolve(mid,'reject',message='Revisar el nombre').status_code==200
    assert b.get('/api/machines/'+mid).status_code==404
    rev=a.get('/api/machines/'+mid).json['machine']['revision']
    assert a.post('/api/machines/'+mid+'/edit',dict(revision=rev,name='Nombre revisado')).status_code==200
    assert top.resolve(mid,'approve').json['state']=='approved'
    assert b.get('/api/machines/'+mid).status_code==200
    with connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM request_resolutions').fetchone()[0]==5


def test_private_notes_hidden_from_top_and_merge_keeps_references(team):
    app,path,top,a,b=team
    target=top.machine('Prensa aprobada','40')
    source=a.machine('Prensa propuesta')
    eid=top.exercise(); rid=a.routine()
    assert a.post('/api/machines/'+source+'/note',dict(body='SECRETO asiento 4',revision=0)).status_code==200
    assert a.post('/api/machines/'+target+'/note',dict(body='SECRETO respaldo 2',revision=0)).status_code==200
    assert top.get('/api/machines/'+source+'/note').json['notes']==[]
    assert 'SECRETO' not in top.get('/machines/'+source).text
    assert 'SECRETO' not in top.get('/api/machines/'+source).text
    assert a.edit(rid,action='add',weekday=0,exercise_id=eid,machine_id=source,set_count=3,same_reps='yes',reps=12,rest_seconds=90).status_code==200
    assert top.resolve(source,'link',target_id=target).status_code==400
    assert top.resolve(source,'link',target_id=target,confirm='yes').json['state']=='linked'
    item=a.get('/api/routines/'+rid).json['version']['days'][0]['items'][0]
    assert item['machine_id']==target and item['original_machine_id']==source
    assert item['machine_name']=='Prensa propuesta'
    assert len(a.get('/api/machines/'+target+'/note').json['notes'])==2
    assert top.get('/api/machines/'+target+'/note').json['notes']==[]
    assert b.get('/api/routines/'+rid).status_code==404
    assert top.get('/api/routines/'+rid).status_code==404
    assert top.get('/api/routines/'+rid+'/versions').status_code==404
    assert a.get('/machines/'+source).status_code==200


def test_routine_publication_copy_versions_and_series(team):
    app,path,top,a,b=team
    mid=top.machine('Prensa PRUEBA','5'); eid=top.exercise(); rid=top.routine()
    assert a.get('/api/routines/'+rid).status_code==404
    assert top.edit(rid,action='add',weekday=0,exercise_id=eid,machine_id=mid,set_count=3,reps_each=[12,10,8],rest_seconds=90).status_code==200
    before=top.get('/api/routines/'+rid).json
    assert top.publish(rid,'assigned',['alice']).status_code==200
    assert b.get('/api/routines/'+rid).status_code==404
    assert a.get('/api/routines/'+rid).status_code==200
    assert a.edit(rid,action='day',weekday=0,title='No').status_code==403
    copy=a.post('/api/routines/'+rid+'/copy',{}).json['id']
    assert a.edit(copy,action='day',weekday=0,title='Mi pierna').status_code==200
    assert top.edit(rid,action='day',weekday=0,title='Pierna TOP').status_code==200
    copied=a.get('/api/routines/'+copy).json
    assert copied['version']['days'][0]['title']=='Mi pierna'
    assert copied['routine']['visibility']=='private'
    assert copied['version']['days'][0]['items'][0]['reps']==[12,10,8]
    versions=top.get('/api/routines/'+rid+'/versions').json['versions']
    assert versions[1]['days'][0]['title']==before['version']['days'][0]['title']
    assert versions[-1]['days'][0]['title']=='Pierna TOP'
    assert a.post('/api/routines/'+copy+'/publish',dict(revision=copied['routine']['revision'],visibility='public')).status_code==403
    assert top.publish(rid).status_code==200
    assert b.get('/api/routines/'+rid).status_code==200
    assert b.get('/api/planning').json['plans']==[]
    assert a.get('/routines/'+copy).status_code==200
    assert a.get('/routines/'+rid).status_code==200


def test_provisional_can_be_used_but_not_shared(team):
    app,path,top,a,b=team
    mid=a.machine(); eid=top.exercise(); rid=a.routine()
    assert a.edit(rid,action='add',weekday=2,exercise_id=eid,machine_id=mid,set_count=2,same_reps='yes',reps=10,rest_seconds=60).status_code==200
    assert top.resolve(mid,'approve').status_code==200
    assert a.get('/api/routines/'+rid).json['version']['days'][2]['items'][0]['machine_id']==mid
    # TOP can inspect private proposals but cannot include another user's private machine in a routine.
    other=a.machine('Otra propuesta')
    top_rid=top.routine()
    assert top.edit(top_rid,action='add',weekday=0,exercise_id=eid,machine_id=other,set_count=1,same_reps='yes',reps=10,rest_seconds=60).status_code==400


def test_planning_dates_overlap_split_and_today(team):
    app,path,top,a,b=team
    rid=a.routine('Plan A'); rid2=a.routine('Plan B')
    eid=top.exercise()
    assert a.edit(rid,action='add',weekday=0,exercise_id=eid,machine_id='',set_count=1,same_reps='yes',reps=10,rest_seconds=0).status_code==200
    assert a.plan(rid).status_code==201
    before=a.get('/api/planning').json
    assert a.plan(rid2,'2026-11-10','2026-11-20').status_code==409
    assert a.get('/api/planning').json==before
    assert a.plan(rid2,'2026-11-10','2026-11-20','yes').status_code==201
    plans=a.get('/api/planning').json['plans']
    assert [(p['date_from'],p['date_until']) for p in plans]==[('2026-11-01','2026-11-09'),('2026-11-10','2026-11-20'),('2026-11-21',None)]
    assert a.get('/api/today?date=2026-11-09').json['routine']['id']==rid
    assert a.get('/api/today?date=2026-11-10').json['routine']['id']==rid2
    assert a.get('/api/today?date=2026-11-20').json['routine']['id']==rid2
    assert a.get('/api/today?date=2026-11-21').json['routine']['id']==rid
    monday=a.get('/api/today?date=2026-11-23').json
    assert monday['weekday']=='Lunes' and monday['day']['rest']==0
    assert a.get('/api/today?date=2026-11-24').json['day']['rest']==1
    assert b.get('/api/today?date=2026-11-23').json['plan'] is None
    assert a.get('/api/today?date=2026-10-31').json['plan'] is None
    assert a.get('/api/today?date=invalid').status_code==400
    assert a.get('/today').status_code==200
    assert a.get('/planning').status_code==200
    assert b.post('/api/planning/'+plans[0]['id']+'/remove',dict(confirm='yes',planning_revision=b.get('/api/planning').json['revision'])).status_code==404
    assert a.post('/api/planning',dict(routine_id=rid,date_from='2026-12-01',date_until='',planning_revision=before['revision'],replace='yes')).status_code==409


def test_validation_archive_and_day_operations(team):
    app,path,top,a,b=team
    rid=a.routine(); eid=top.exercise()
    assert a.plan(rid,'2025-01-01').status_code==400
    assert a.edit(rid,action='metadata',name='Fechas',date_from='2026-12-01',date_until='2026-11-01').status_code==400
    assert a.edit(rid,action='add',weekday=0,exercise_id=eid,set_count=3,reps_each=[12,10],rest_seconds=90).status_code==400
    assert a.edit(rid,action='add',weekday=0,exercise_id=eid,set_count=3,same_reps='yes',reps=10,rest_seconds=90).status_code==200
    assert a.edit(rid,action='day',weekday=0,title='Descanso',rest='yes').status_code==409
    key=a.get('/api/routines/'+rid).json['version']['days'][0]['items'][0]['item_key']
    assert a.edit(rid,action='update',weekday=0,item_key=key,set_count=2,reps_each=[8,6],rest_seconds=120).status_code==200
    assert a.edit(rid,action='remove',weekday=0,item_key=key).status_code==200
    assert a.edit(rid,action='day',weekday=0,title='Descanso',rest='yes').status_code==200
    rev=a.get('/api/routines/'+rid).json['routine']['revision']
    assert a.post('/api/routines/'+rid+'/archive',dict(revision=rev,confirm='yes')).status_code==200
    assert a.get('/api/routines/'+rid).json['routine']['archived']==1
    assert a.plan(rid).status_code==409
    mid=top.machine(); m=top.get('/api/machines/'+mid).json['machine']
    assert top.post('/api/machines/'+mid+'/archive',dict(revision=m['revision'],confirm='yes')).status_code==200
    assert top.get('/api/machines').json['machines']==[]


def test_shared_routine_cannot_be_withdrawn_or_narrowed_while_planned(team):
    app,path,top,a,b=team
    rid=top.routine(); assert top.publish(rid).status_code==200
    assert a.plan(rid).status_code==201
    assert top.publish(rid,'private').status_code==409
    assert top.edit(rid,action='metadata',name='Short',date_from='2026-01-01',date_until='2026-11-30').status_code==409
    rev=top.get('/api/routines/'+rid).json['routine']['revision']
    assert top.post('/api/routines/'+rid+'/archive',dict(revision=rev,confirm='yes')).status_code==409


def test_existing_phase_one_database_upgrade_preserves_accounts(tmp_path):
    path=tmp_path/'old.sqlite3'
    with sqlite3.connect(path) as db:
        db.executescript((ROOT/'migrations/001_identity.sql').read_text(encoding='utf-8-sig'))
        db.execute("INSERT INTO users(id,username,role,created_at) VALUES ('stable-id','existing','TOP',1)")
    initialize(path); initialize(path)
    with connect(path) as db:
        assert tuple(db.execute('SELECT id,username FROM users').fetchone())==('stable-id','existing')
        assert db.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==2
        assert db.execute('SELECT COUNT(*) FROM machines').fetchone()[0]==0
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]

def test_html_forms_and_conflict_confirmation(team):
    app,path,top,a,b=team
    c=top.c
    r=c.post('/machines/new',data=dict(csrf=token(c),checked_matches='yes',name='Ficha HTML PRUEBA',sticker='77'))
    assert r.status_code==303
    machine_url=r.location
    assert 'Ficha HTML PRUEBA' in c.get(machine_url).text
    mid=machine_url.rsplit('/',1)[1]
    assert c.get('/machines/new?q=77').status_code==200
    assert c.get('/machines/'+mid+'/edit').status_code==200
    r=c.post('/exercises/new',data=dict(csrf=token(c),name='Ejercicio HTML PRUEBA',equipment='machine',machine_ids=mid))
    assert r.status_code==303
    eid=top.get('/api/exercises').json['exercises'][0]['id']
    assert c.get('/exercises/'+eid+'/edit').status_code==200
    r=a.c.post('/routines/new',data=dict(csrf=token(a.c),name='Rutina HTML PRUEBA',date_from='2026-01-01',date_until=''))
    assert r.status_code==303
    rid=r.location.rsplit('/',1)[1]
    revision=a.get('/api/routines/'+rid).json['routine']['revision']
    r=a.c.post('/routines/'+rid+'/edit',data=dict(csrf=token(a.c),revision=revision,action='add',weekday='0',exercise_id=eid,machine_id=mid,set_count='3',reps_each='12, 10, 8',rest_seconds='90'))
    assert r.status_code==303
    assert '12 / 10 / 8' in a.get('/routines/'+rid).text
    assert a.plan(rid).status_code==201
    r=a.c.post('/planning',data=dict(csrf=token(a.c),planning_revision=a.get('/api/planning').json['revision'],routine_id=rid,date_from='2026-11-10',date_until='2026-11-20'))
    assert r.status_code==409 and 'No se ha cambiado tu planificación.' in r.text
    assert len(a.get('/api/planning').json['plans'])==1


def test_untrusted_input_does_not_crash_or_override_notes(team):
    app,path,top,a,b=team
    assert top.post('/api/exercises',dict(name='Ejercicio',equipment='machine',machine_ids=[{}])).status_code==400
    assert a.post('/api/routines',dict(name=['mal'],date_from='2026-01-01')).status_code==400
    mid=top.machine()
    assert a.post('/api/machines/'+mid+'/note',dict(body='Solo Alice',revision=0,user_id='bob')).status_code==200
    assert b.get('/api/machines/'+mid+'/note').json['notes']==[]
    assert a.post('/api/machines/'+mid+'/note',dict(body='Cambio obsoleto',revision=0)).status_code==409
    assert 'Solo Alice' in a.get('/machines/'+mid).text
    assert 'Solo Alice' not in b.get('/machines/'+mid).text
    escaped=a.machine('<script>alert(1)</script>')
    assert '<script>alert(1)</script>' not in a.get('/machines/'+escaped).text


def test_calendar_extreme_date_and_account_role_change(team):
    app,path,top,a,b=team
    rid=a.routine()
    assert a.plan(rid).status_code==201
    assert a.plan(rid,'2026-11-01','9999-12-31','yes').status_code==201
    assert len(a.get('/api/planning').json['plans'])==1
    # Another active TOP permits checking the shared-routine demotion guard.
    with connect(path) as db:
        db.execute("UPDATE users SET role='TOP' WHERE id='bob'")
    btop=Client(app,'bob'); public=btop.routine()
    assert btop.publish(public).status_code==200
    r=top.c.post('/admin/users/bob',data={'csrf':token(top.c),'action':'normal','confirm':'yes'})
    assert r.status_code==409

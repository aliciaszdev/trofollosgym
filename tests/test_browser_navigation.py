"""Regresiones de navegación: el navegador debe acabar en HTML, no en la API."""
from urllib.parse import urlsplit
from html.parser import HTMLParser
import pytest
from flask import url_for
from test_identity import setup, token
from test_catalog_routines import Client


@pytest.mark.parametrize('endpoint,values,expected',[
    ('catalog.index',{},'/catalog'),
    ('catalog.detail',{'mid':'fixture'},'/machines/fixture'),
    ('catalog.new_machine',{},'/machines/new'),
    ('catalog.edit_machine',{'mid':'fixture'},'/machines/fixture/edit'),
    ('catalog.new_exercise',{},'/exercises/new'),
    ('catalog.edit_exercise',{'eid':'fixture'},'/exercises/fixture/edit'),
    ('routines.index',{},'/routines'),
    ('routines.new',{},'/routines/new'),
    ('routines.detail',{'rid':'fixture'},'/routines/fixture'),
    ('routines.planning',{},'/planning'),
    ('routines.today',{},'/today'),
])
def test_canonical_browser_urls(setup,endpoint,values,expected):
    app,_=setup
    with app.test_request_context():
        assert url_for(endpoint,**values)==expected


class BrowserLinks(HTMLParser):
    def __init__(self):
        super().__init__(); self.urls=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('a','form'):
            for name,value in attrs:
                if name in ('href','action') and value:
                    self.urls.append(value)


def html_response(response):
    assert response.status_code==200
    assert response.mimetype=='text/html'
    assert not urlsplit(response.request.url).path.startswith('/api/')
    links=BrowserLinks(); links.feed(response.text)
    assert not any(urlsplit(link).path.startswith('/api/') for link in links.urls)


def test_browser_create_and_edit_flow_stays_in_html(setup):
    app,_=setup
    top=Client(app,'owner'); c=top.c
    r=c.post('/machines/new',data={'csrf':token(c),'name':'Remo PRUEBA','sticker':'24','checked_matches':'yes'},follow_redirects=True)
    html_response(r)
    assert 'Remo PRUEBA' in r.text
    mid=urlsplit(r.request.url).path.rsplit('/',1)[1]
    rev=top.get('/api/machines/'+mid).json['machine']['revision']
    r=c.post('/machines/'+mid+'/edit',data={'csrf':token(c),'revision':rev,'name':'Remo revisado PRUEBA','sticker':'24'},follow_redirects=True)
    html_response(r)
    r=c.post('/exercises/new',data={'csrf':token(c),'name':'Remo PRUEBA','equipment':'machine','machine_ids':mid},follow_redirects=True)
    html_response(r)
    eid=top.get('/api/exercises').json['exercises'][0]['id']
    r=c.post('/routines/new',data={'csrf':token(c),'name':'Rutina de prueba','date_from':'2026-01-01','date_until':''},follow_redirects=True)
    html_response(r)
    assert 'Rutina de prueba' in r.text
    rid=urlsplit(r.request.url).path.rsplit('/',1)[1]
    rev=top.get('/api/routines/'+rid).json['routine']['revision']
    r=c.post('/routines/'+rid+'/edit',data={'csrf':token(c),'revision':rev,'action':'add','weekday':'0','exercise_id':eid,'machine_id':mid,'set_count':'3','same_reps':'yes','reps':'10','rest_seconds':'90'},follow_redirects=True)
    html_response(r)
    assert 'Remo revisado PRUEBA' in r.text
    r=c.post('/routines/'+rid+'/copy',data={'csrf':token(c)},follow_redirects=True)
    html_response(r)
    r=c.post('/planning',data={'csrf':token(c),'routine_id':rid,'date_from':'2026-11-01','date_until':'','planning_revision':top.get('/api/planning').json['revision']},follow_redirects=True)
    html_response(r)
    for path in ('/catalog','/routines','/today','/planning','/machines/'+mid,'/routines/'+rid):
        html_response(c.get(path))
    assert top.get('/api/machines/'+mid).is_json
    assert top.get('/api/routines/'+rid).is_json

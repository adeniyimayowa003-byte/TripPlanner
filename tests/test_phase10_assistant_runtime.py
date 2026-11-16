"""Real Flask/session/SQLite integration, simulated provider, NOT live sign-in."""
from dataclasses import replace
from decimal import Decimal
import importlib
import json
import sqlite3
import threading

import pytest


class FakeProvider:
    def __init__(self):self.calls=[];self.result='{"source_ids":["faq:allowance"]}';self.hook=None
    def count_tokens(self,text):return len(text.encode('utf-8'))
    def select(self,payload,*,deadline,authorized):
        assert authorized()
        self.calls.append(payload)
        if self.hook:self.hook()
        return self.result


class SyntheticOwnedTrips:
    """Read-only test gateway over actual SQLite; not production trip claiming."""
    def __init__(self,path):self.path=path
    def list_owned(self,account_id):
        with sqlite3.connect(self.path) as db:
            return [{'id':row[0],'label':'Synthetic owned Paris snapshot'} for row in db.execute('SELECT id FROM owned_trips WHERE account_id=?',(account_id,))]
    def get_owned(self,account_id,trip_id):
        import hashlib
        with sqlite3.connect(self.path) as db:
            row=db.execute('SELECT snapshot_json FROM owned_trips WHERE id=? AND account_id=?',(trip_id,account_id)).fetchone()
        if not row:return None
        return {'owner_kind':'account','owner_id':account_id,'snapshot':json.loads(row[0]),
                'fingerprint':hashlib.sha256(row[0].encode()).hexdigest()}


@pytest.fixture
def state(app,tmp_path):
    from account_sessions import create_store,SessionStore,VerifiedIdentity
    from assistant_limits import create_limits,Limits
    from catalog import load_catalog
    from snapshots import build_snapshot,dump_snapshot
    module=importlib.import_module('assistant_runtime')
    path=tmp_path/'accounts.sqlite3';create_store(path)
    sessions=SessionStore(path,clock=lambda:100000)
    one=sessions.issue(VerifiedIdentity('https://issuer.example','A',True,100000))
    two=sessions.issue(VerifiedIdentity('https://issuer.example','B',True,100000))
    limitpath=tmp_path/'quotas.sqlite3';create_limits(limitpath)
    provider=FakeProvider()
    tripdb=tmp_path/'synthetic-owned.sqlite3'
    snapshot=build_snapshot({'destination':'Paris, France','days':3,'budget':Decimal('300.00'),
        'currency':'EUR','interests':['history','food'],'pace':'relaxed','family_friendly':True},load_catalog())
    snapshot['private_metadata']={'email':'NEVER-SEND@example.com','secret':'NEVER-SEND-SECRET'}
    with sqlite3.connect(tripdb) as db:
        db.execute('CREATE TABLE owned_trips(id TEXT PRIMARY KEY,account_id TEXT,snapshot_json TEXT)')
        db.execute('INSERT INTO owned_trips VALUES(?,?,?)',('selected-private-id',one.principal.account_id,dump_snapshot(snapshot)))
        db.execute('INSERT INTO owned_trips VALUES(?,?,?)',('foreign-private-id',two.principal.account_id,dump_snapshot(snapshot)))
    gateway=SyntheticOwnedTrips(tripdb)
    ready=module.Readiness(identity=True,privacy=True,free_only=True,provider=True,storage=True)
    runtime=module.AssistantRuntime(sessions=sessions,limits=Limits(limitpath,clock=lambda:100000),
        provider=provider,trip_reader=gateway,readiness=ready,timeout=0.2,
        disclosure=module.ProviderDisclosure('Synthetic Test Provider','test region','test-only no retention',
            'https://model.example/terms',no_training=True))
    app.extensions['assistant_runtime']=runtime
    browser=app.test_client();browser.set_cookie('__Host-tripplanner_account',one.token)
    yield module,runtime,provider,sessions,one,two,browser,gateway
    runtime.close()


def send(browser,parse_page,question='What does allowance cover?',**extra):
    page=parse_page(browser.get('/assistant',base_url='https://localhost'))
    token=page.find('input',name='csrf_token').attrs['value']
    return browser.post('/assistant',base_url='https://localhost',data={'csrf_token':token,
        'question':question,'use_model':'on','consent':'on',**extra})


def test_model_pipeline_is_integrated_in_real_flask_page(state,parse_page):
    _,_,provider,_,_,_,browser,_=state
    response=send(browser,parse_page)
    assert response.status_code==200
    assert 'AI-selected sources' in response.text
    assert len(provider.calls)==1
    assert '/help#allowance' in response.text
    assert 'per person' in response.text


@pytest.mark.parametrize('gate',['identity','privacy','free_only','provider','storage'])
def test_missing_activation_gate_never_calls_model(state,parse_page,gate):
    _,runtime,provider,_,_,_,browser,_=state
    runtime.readiness=replace(runtime.readiness,**{gate:False})
    response=send(browser,parse_page)
    assert 'FAQ fallback' in response.text and provider.calls==[]


@pytest.mark.parametrize('kind',['no-consent','no-model','no-session','revoked','http','forged-account'])
def test_authority_and_consent_are_required_before_provider_calls(state,parse_page,kind):
    _,_,provider,sessions,one,_,browser,_=state
    extra={}
    if kind=='no-consent':extra['consent']=''
    if kind=='no-model':extra['use_model']=''
    if kind=='no-session':browser.delete_cookie('__Host-tripplanner_account')
    if kind=='revoked':sessions.revoke(one.token)
    if kind=='forged-account':browser.set_cookie('__Host-tripplanner_account','Z'*43);extra['account_id']=one.principal.account_id
    if kind=='http':
        token=parse_page(browser.get('/assistant')).find('input',name='csrf_token').attrs['value']
        response=browser.post('/assistant',data={'csrf_token':token,'question':'allowance','use_model':'on','consent':'on'})
    else:response=send(browser,parse_page,**extra)
    assert response.status_code==200
    assert 'FAQ fallback' in response.text and provider.calls==[]


def test_no_trip_is_sent_without_separate_selection_consent(state,parse_page):
    _,_,provider,_,one,_,browser,_=state
    send(browser,parse_page,trip_id='selected-private-id')
    assert provider.calls[0].get('trip') is None
    body=json.dumps(provider.calls[0])
    assert one.principal.account_id not in body and one.token not in body
    assert 'NEVER-SEND' not in body and 'selected-private-id' not in body


def test_explicit_selected_trip_is_projected_and_authorized(state,parse_page):
    _,_,provider,_,one,_,browser,_=state
    response=send(browser,parse_page,trip_id='selected-private-id',use_trip='on')
    assert response.status_code==200 and len(provider.calls)==1
    trip=provider.calls[0]['trip']
    assert trip['destination']=='Paris, France' and trip['estimates']=='illustrative historical snapshot'
    assert trip['days']
    body=json.dumps(provider.calls[0])
    for forbidden in ('NEVER-SEND','private_metadata','selected-private-id',one.token,one.principal.account_id):assert forbidden not in body


@pytest.mark.parametrize('trip_id',['foreign-private-id','missing','selected-private-id,foreign-private-id'])
def test_foreign_or_invalid_trip_does_not_trigger_any_provider_call(state,parse_page,trip_id):
    _,_,provider,_,_,_,browser,_=state
    response=send(browser,parse_page,trip_id=trip_id,use_trip='on')
    assert 'FAQ fallback' in response.text and provider.calls==[]


def test_revocation_while_provider_runs_discards_late_result(state,parse_page):
    _,_,provider,sessions,one,_,browser,_=state
    provider.hook=lambda:sessions.revoke(one.token)
    response=send(browser,parse_page)
    assert len(provider.calls)==1
    assert 'FAQ fallback' in response.text


def test_ownership_loss_while_provider_runs_discards_late_result(state,parse_page):
    _,_,provider,_,_,two,browser,gateway=state
    def move():
        with sqlite3.connect(gateway.path) as db:db.execute('UPDATE owned_trips SET account_id=? WHERE id=?',(two.principal.account_id,'selected-private-id'))
    provider.hook=move
    response=send(browser,parse_page,trip_id='selected-private-id',use_trip='on')
    assert 'FAQ fallback' in response.text


@pytest.mark.parametrize('result',[
    '{"source_ids":["faq:invented"]}',
    '{"source_ids":["faq:allowance"],"text":"The Eiffel Tower costs 1 euro today"}',
    '{"source_ids":["https://evil.example"]}',
    '<script>alert(1)</script>', '{"source_ids":[]}',
    '{"source_ids":["faq:allowance","faq:allowance"]}', 'x'*5000])
def test_invalid_or_fabricated_model_output_is_withheld(state,parse_page,result):
    _,_,provider,_,_,_,browser,_=state;provider.result=result
    response=send(browser,parse_page)
    assert 'FAQ fallback' in response.text
    assert 'evil.example' not in response.text and 'costs 1 euro' not in response.text


def test_provider_error_is_redacted_and_core_planner_still_works(state,parse_page):
    _,_,provider,_,_,_,browser,_=state
    def fail():raise RuntimeError('SECRET-provider-key')
    provider.hook=fail
    response=send(browser,parse_page)
    assert 'FAQ fallback' in response.text and 'SECRET-provider-key' not in response.text
    assert browser.get('/plan').status_code==200


def test_input_budget_rejects_before_call_and_quota_stays_usable(state,parse_page):
    _,_,provider,_,_,_,browser,_=state
    provider.count_tokens=lambda text:6001
    assert 'FAQ fallback' in send(browser,parse_page).text
    assert provider.calls==[]
    provider.count_tokens=lambda text:len(text.encode())
    assert 'AI-selected sources' in send(browser,parse_page).text


def test_request_timeout_and_no_retry(state,parse_page):
    _,runtime,provider,_,_,_,browser,_=state
    runtime.timeout=0.02
    release=threading.Event()
    provider.hook=lambda:release.wait(1)
    try:
        response=send(browser,parse_page)
        assert 'FAQ fallback' in response.text and len(provider.calls)==1
    finally:release.set()


def test_quota_fallback_and_input_limits(state,parse_page):
    _,_,provider,_,_,_,browser,_=state
    for _ in range(5):assert send(browser,parse_page).status_code==200
    response=send(browser,parse_page)
    assert 'FAQ fallback' in response.text and len(provider.calls)==5
    assert send(browser,parse_page,'x'*1001).status_code==400


def test_selected_trip_citation_page_checks_current_owner(state):
    _,_,_,_,_,_,browser,_=state
    assert browser.get('/assistant/context/selected-private-id',base_url='https://localhost').status_code==200
    assert browser.get('/assistant/context/foreign-private-id',base_url='https://localhost').status_code==404
    browser.delete_cookie('__Host-tripplanner_account')
    assert browser.get('/assistant/context/selected-private-id',base_url='https://localhost').status_code==404

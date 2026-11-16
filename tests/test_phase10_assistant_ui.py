"""Actual application assistant UX contracts, written before implementation."""
from pathlib import Path
import importlib

import pytest


def send(browser, parse_page, question, **extra):
    page=parse_page(browser.get('/assistant'))
    token=page.find('input',name='csrf_token')
    assert token is not None
    return browser.post('/assistant',data={'question':question,'csrf_token':token.attrs['value'],**extra})


def test_assistant_page_is_usable_honest_and_has_samples(client,parse_page):
    response=client.get('/assistant')
    assert response.status_code==200
    page=parse_page(response)
    assert len(page.find_all('h1'))==1
    assert page.find('form',action='/assistant',method='post')
    assert page.find('label',**{'for':'assistant-question'})
    assert page.find('textarea',name='question').attrs.get('maxlength')=='1000'
    assert page.find('section',**{'aria-label':'Conversation'})
    samples=page.find_all('button',name='question')
    assert len(samples)>=3
    assert 'FAQ fallback' in page.text
    assert 'not a live model' in page.text
    assert 'illustrative' in page.text
    assert page.find('a',href='/help')
    assert 'disabled' in page.find('select',name='trip_id').attrs
    assert 'no account' in page.text.casefold()


@pytest.mark.parametrize('path',['/','/plan','/trips','/help'])
def test_assistant_has_working_navigation(client,parse_page,path):
    assert parse_page(client.get(path)).find('a',href='/assistant')


@pytest.mark.parametrize('question,source,phrase',[
    ('What does my allowance cover?','allowance','per person'),
    ('Why are meals missing?','gaps','Restaurants'),
    ('I cleared my cookies and lost my trips','saving','365'),
    ('Why is the demo slow to wake?','hosting','Free hosting'),
    ('Do my Android saves sync online?','native','independent'),
    ('How do I change the theme?','themes','Light'),
])
def test_natural_questions_get_approved_answers_without_javascript(client,parse_page,question,source,phrase):
    response=send(client,parse_page,question)
    assert response.status_code==200
    page=parse_page(response)
    assert phrase in page.text
    assert page.find('a',href='/help#'+source)
    assert 'FAQ fallback' in page.text


def test_catalog_answer_cites_actual_internal_source(client,parse_page):
    response=send(client,parse_page,'Tell me about the Eiffel Tower')
    assert response.status_code==200
    page=parse_page(response)
    link=page.find('a',href='/assistant/sources/paris-eiffel-tower')
    assert link
    source=client.get(link.attrs['href'])
    assert source.status_code==200
    assert 'Eiffel Tower' in source.text and '32.00' in source.text and 'EUR' in source.text
    assert 'Illustrative' in source.text
    assert client.get('/assistant/sources/unknown-place').status_code==404


def test_unknown_facts_are_not_invented(client,parse_page):
    response=send(client,parse_page,'What is the exact visa fee for Mars today?')
    assert response.status_code==200
    assert 'not verified in TripPlanner' in parse_page(response).text


def test_csrf_invalid_and_overlong_inputs_never_send(client,parse_page):
    assert client.post('/assistant',data={'question':'hello'}).status_code==400
    assert send(client,parse_page,'x'*1001).status_code==400
    assert send(client,parse_page,'  ').status_code==400


def test_question_is_escaped_private_and_not_in_cookie(client,parse_page):
    text='<script>alert("private-question-sentinel")</script>'
    response=send(client,parse_page,text)
    assert response.status_code==200
    assert text not in response.text and '&lt;script&gt;' in response.text
    assert response.headers['Cache-Control']=='private, no-store'
    assert response.headers['Referrer-Policy']=='no-referrer'
    with client.session_transaction() as session:
        assert 'private-question-sentinel' not in repr(dict(session))
    assert 'private-question-sentinel' not in response.headers.get('Location','')
    assert text not in client.get('/assistant').text


def test_fallback_survives_broken_catalog_and_storage_without_changing_draft(app,client,parse_page,monkeypatch):
    import app as web
    import socket
    def forbidden(*a,**k):raise OSError('offline synthetic store')
    for name in ('load_catalog','load_destinations','get_trip','list_trips'):
        monkeypatch.setattr(web,name,forbidden)
    monkeypatch.setattr(socket,'create_connection',forbidden)
    with client.session_transaction() as session:session['trip_draft']={'sentinel':'stale'}
    response=send(client,parse_page,'What does allowance mean?')
    assert response.status_code==200
    assert 'per person' in response.text
    with client.session_transaction() as session:assert session['trip_draft']=={'sentinel':'stale'}
    assert not Path(app.config['DATABASE']).exists()


def test_guest_forged_account_and_trip_consent_still_get_only_fallback(client,parse_page):
    client.set_cookie('__Host-tripplanner_account','A'*43)
    response=send(client,parse_page,'Help with saving',use_model='on',consent='on',
                  trip_id='1',use_trip='on',account_id='forged')
    assert response.status_code==200
    assert 'FAQ fallback' in response.text
    assert 'Live AI is unavailable' in response.text


def test_assistant_switch_removes_route_and_navigation(app,client,parse_page):
    app.config['PHASE10_ASSISTANT_ENABLED']=False
    assert client.get('/assistant').status_code==404
    assert not parse_page(client.get('/')).find('a',href='/assistant')
    assert client.get('/help').status_code==200


def test_native_staging_includes_fallback_resources_not_model_credentials():
    import build_windows,build_android
    root=Path(__file__).resolve().parents[1]
    for builder in (build_windows,build_android):
        paths=builder.application_files(root)
        assert 'assistant_web.py' in paths and 'assistant_answers.py' in paths
        assert 'templates/assistant.html' in paths and 'templates/assistant_source.html' in paths
        assert 'assistant_provider.py' not in paths


def test_fallback_source_selection_is_grounded_and_bounded():
    module=importlib.import_module('assistant_answers')
    answer=module.fallback_answer('Why are meals missing?')
    assert answer.mode=='faq'
    assert any(source.id=='faq:gaps' for source in answer.sources)
    assert len(answer.sources)<=3
    assert all(source.url.startswith(('/help#','/assistant/sources/')) for source in answer.sources)

"""Privacy lifecycle and real adapter wiring with no external network access."""
import json
from pathlib import Path
import shutil
import subprocess
import time
import threading

import pytest

from test_phase10_assistant_runtime import state,send


def test_actual_http_adapter_is_wired_through_real_app(state,parse_page):
    from assistant_provider import ChatSourceAdapter,EndpointConfig
    _,runtime,_,_,_,_,browser,_=state
    sent=[]
    def transport(endpoint,headers,body,**kwargs):
        sent.append(json.loads(body))
        assert headers['Authorization']=='Bearer FAKE-INTEGRATED-KEY'
        return json.dumps({'choices':[{'finish_reason':'stop','message':{
            'content':'{"source_ids":["faq:allowance"]}'}}]}).encode()
    runtime.provider=ChatSourceAdapter(EndpointConfig('https://model.example/v1/chat/completions',
        'model.example','m','FAKE-INTEGRATED-KEY'),token_counter=lambda text:len(text.encode()),transport=transport)
    response=send(browser,parse_page)
    assert 'AI-selected sources' in response.text and len(sent)==1
    assert 'FAKE-INTEGRATED-KEY' not in response.text
    assert 'tools' not in sent[0]


def test_privacy_script_exists_in_rendered_page_and_native_staging(client,parse_page):
    page=parse_page(client.get('/assistant'))
    assert page.find('script',src='/static/js/assistant_privacy.js')
    assert page.find('section',**{'data-assistant-private':None})
    import build_windows,build_android
    root=Path(__file__).resolve().parents[1]
    for builder in (build_windows,build_android):assert 'static/js/assistant_privacy.js' in builder.application_files(root)


@pytest.mark.parametrize('event',['pagehide','pageshow'])
def test_actual_privacy_script_clears_dom_without_network_or_storage(event):
    root=Path(__file__).resolve().parents[1]
    script=root/'static/js/assistant_privacy.js'
    assert script.is_file()
    node=shutil.which('node');assert node
    harness=r'''
const fs=require('fs'),vm=require('vm');const handlers={};
const secret={cleared:false,replaceChildren(){this.cleared=true;}};
const textarea={value:'private question'};const check={checked:true};
const context={document:{querySelectorAll(s){if(s==='[data-assistant-private]')return [secret];if(s==='textarea')return [textarea];if(s==='input[type="checkbox"]')return [check];throw Error('unexpected selector');}},
window:{addEventListener(k,fn){handlers[k]=fn;}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
handlers[process.argv[2]]({persisted:true});
if(!secret.cleared||textarea.value!==''||check.checked)throw Error('private content remained');
process.stdout.write('privacy-cleared');
'''
    result=subprocess.run([node,'-e',harness,str(script),event],capture_output=True,text=True,timeout=5)
    assert result.returncode==0,result.stderr
    assert result.stdout=='privacy-cleared'


@pytest.mark.parametrize('path',['/v1/chat/completions','/openai/v1/chat/completions'])
def test_documented_compatible_endpoint_paths_are_explicitly_allowlisted(path):
    from assistant_provider import EndpointConfig
    config=EndpointConfig('https://model.example'+path,'model.example','m','FAKE')
    assert config.endpoint.endswith(path)


def test_http_transport_never_follows_redirect_or_retries(monkeypatch):
    import assistant_provider as module
    requests=[]
    class Socket:
        def settimeout(self,value):assert 0<value<=15
    class Connection:
        def __init__(self,*a,**k):self.sock=Socket()
        def connect(self):pass
        def request(self,*a,**k):requests.append(a)
        def getresponse(self):return type('Response',(),{'status':302})()
        def close(self):pass
    monkeypatch.setattr(module.http.client,'HTTPSConnection',Connection)
    with pytest.raises(ValueError):module._post_json('https://model.example/v1/chat/completions',{},b'{}',
        deadline=time.monotonic()+1,authorized=lambda:True)
    assert len(requests)==1


def test_authority_loss_after_connect_prevents_data_send(monkeypatch):
    import assistant_provider as module
    active=[True]
    class Connection:
        def __init__(self,*a,**k):pass
        def connect(self):active[0]=False
        def request(self,*a,**k):pytest.fail('No body or key may be sent after authorization loss')
        def close(self):pass
    monkeypatch.setattr(module.http.client,'HTTPSConnection',Connection)
    with pytest.raises(ValueError):module._post_json('https://model.example/v1/chat/completions',{},b'PRIVATE',
        deadline=time.monotonic()+1,authorized=lambda:active[0])


def test_quota_response_shows_explicit_retry_timing(state,parse_page):
    _,_,_,_,_,_,browser,_=state
    for _ in range(5):send(browser,parse_page)
    response=send(browser,parse_page)
    assert 'Try again in 60 seconds' in response.text


def test_timed_out_running_worker_keeps_its_account_reservation(state,parse_page):
    _,runtime,provider,_,_,_,browser,_=state
    runtime.timeout=0.05
    release=threading.Event();provider.hook=lambda:release.wait(2)
    try:
        assert 'FAQ fallback' in send(browser,parse_page).text
        assert 'FAQ fallback' in send(browser,parse_page).text
        assert len(provider.calls)==1
    finally:release.set()


def test_output_token_limit_applies_even_to_valid_padded_json(state,parse_page):
    _,_,provider,_,_,_,browser,_=state
    provider.result=' '*600+'{"source_ids":["faq:allowance"]}'
    assert 'FAQ fallback' in send(browser,parse_page).text

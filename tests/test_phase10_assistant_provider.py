"""Server HTTP adapter contract with simulated transport, zero live model calls."""
import importlib
import json
import time

import pytest


def api():return importlib.import_module('assistant_provider')


def payload():return {'instructions':'Select source IDs only.','question':'Allowance?',
    'sources':[{'id':'faq:allowance','text':'Approved allowance excerpt.'}],'trip':None}


def envelope(content='{"source_ids":["faq:allowance"]}'):
    return json.dumps({'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':content}}],
                       'usage':{'completion_tokens':20}}).encode()


@pytest.mark.parametrize('endpoint',[
    'http://model.example/v1/chat/completions','https://evil.example/v1/chat/completions',
    'https://user:pass@model.example/v1/chat/completions','https://model.example:8443/v1/chat/completions',
    'https://model.example/v1/chat/completions?key=secret','https://model.example/v1/chat/completions#x',
    'https://127.0.0.1/v1/chat/completions','https://model.example/other',
])
def test_endpoint_is_explicit_https_allowlist_without_credentials(endpoint):
    with pytest.raises(ValueError):api().EndpointConfig(endpoint,'model.example','approved-model','FAKE-SERVER-KEY')


def test_server_adapter_request_body_and_key_boundaries():
    module=api();seen=[]
    config=module.EndpointConfig('https://model.example/v1/chat/completions','model.example','approved-model','FAKE-SERVER-KEY')
    def transport(endpoint,headers,body,*,deadline,authorized):
        seen.append((endpoint,headers,json.loads(body)))
        assert authorized() and deadline>time.monotonic()
        return envelope()
    provider=module.ChatSourceAdapter(config,token_counter=lambda text:len(text.encode()),transport=transport)
    result=provider.select(payload(),deadline=time.monotonic()+1,authorized=lambda:True)
    assert result=='{"source_ids":["faq:allowance"]}'
    assert len(seen)==1
    _,headers,body=seen[0]
    assert headers['Authorization']=='Bearer FAKE-SERVER-KEY'
    assert body['model']=='approved-model' and body['max_completion_tokens']==600 and body['stream'] is False
    assert 'tools' not in body and 'FAKE-SERVER-KEY' not in json.dumps(body)
    assert 'FAKE-SERVER-KEY' not in repr(config) and 'FAKE-SERVER-KEY' not in repr(provider)


@pytest.mark.parametrize('case',['unauthorized','expired','too-many-tokens'])
def test_preflight_rejects_before_transport(case):
    module=api();config=module.EndpointConfig('https://model.example/v1/chat/completions','model.example','m','FAKE-KEY')
    def forbidden(*a,**k):pytest.fail('No transport permitted')
    provider=module.ChatSourceAdapter(config,token_counter=lambda text:6001 if case=='too-many-tokens' else 10,transport=forbidden)
    with pytest.raises(module.ProviderUnavailable):provider.select(payload(),
        deadline=time.monotonic()+(-1 if case=='expired' else 1),authorized=lambda:case!='unauthorized')


@pytest.mark.parametrize('response',[
    b'not JSON',b'x'*65537,
    json.dumps({'choices':[{'finish_reason':'length','message':{'content':'{}'}}]}).encode(),
    json.dumps({'choices':[{'finish_reason':'stop','message':{'tool_calls':[{'function':'book'}],'content':'{}'}}]}).encode(),
    json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'{}'}}],'usage':{'completion_tokens':601}}).encode(),
    envelope('x'*4097),
])
def test_bad_truncated_tool_or_oversize_response_is_redacted(response):
    module=api();config=module.EndpointConfig('https://model.example/v1/chat/completions','model.example','m','FAKE-KEY')
    provider=module.ChatSourceAdapter(config,token_counter=lambda text:10,transport=lambda *a,**k:response)
    with pytest.raises(module.ProviderUnavailable) as error:provider.select(payload(),deadline=time.monotonic()+1,authorized=lambda:True)
    assert 'FAKE-KEY' not in str(error.value)


def test_transport_error_has_no_retry_and_no_credential_leak():
    module=api();calls=[]
    def broken(*a,**k):calls.append(1);raise RuntimeError('FAKE-KEY-private')
    provider=module.ChatSourceAdapter(module.EndpointConfig('https://model.example/v1/chat/completions','model.example','m','FAKE-KEY'),
        token_counter=lambda text:10,transport=broken)
    with pytest.raises(module.ProviderUnavailable) as error:provider.select(payload(),deadline=time.monotonic()+1,authorized=lambda:True)
    assert len(calls)==1 and 'FAKE-KEY' not in str(error.value)

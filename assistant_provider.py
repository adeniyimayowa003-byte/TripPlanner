"""Server-only chat-JSON adapter; no default provider, key or live activation.

Wire-format reference: https://developers.openai.com/api/reference/resources/chat
This is NOT a claim of free OpenAI API access or third-party compatibility.
Supply the chosen model's verified tokenizer and approved no-billing/privacy
contract through server composition; never put credentials into native bundles.
"""
from dataclasses import dataclass,field
import http.client
import json
import re
import time
from urllib.parse import urlsplit

class ProviderUnavailable(RuntimeError):pass

@dataclass(frozen=True)
class EndpointConfig:
    endpoint:str
    allowed_host:str
    model:str
    api_key:str=field(repr=False)

    def __post_init__(self):
        try:
            url=urlsplit(self.endpoint)
            valid=(isinstance(self.allowed_host,str)
                and re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.[a-z]{2,}',self.allowed_host)
                and url.scheme=='https' and url.hostname==self.allowed_host
                and url.username is None and url.password is None
                and url.port in (None,443) and url.path in ('/v1/chat/completions','/openai/v1/chat/completions')
                and '?' not in self.endpoint and '#' not in self.endpoint
                and all(ord(c)>32 and ord(c)<127 for c in self.endpoint)
                and isinstance(self.model,str) and 0<len(self.model)<=100
                and isinstance(self.api_key,str) and 0<len(self.api_key)<=8192
                and all(32<ord(c)<127 for c in self.api_key))
        except (ValueError,TypeError,AttributeError):valid=False
        if not valid:raise ValueError('Configure an approved server-only HTTPS model endpoint.')

class ChatSourceAdapter:
    def __init__(self,config,*,token_counter,transport=None):
        if type(config) is not EndpointConfig or not callable(token_counter):raise ValueError('Model configuration and tokenizer required.')
        self.config=config;self.token_counter=token_counter;self.transport=transport or _post_json
    def count_tokens(self,text):return self.token_counter(text)
    def select(self,payload,*,deadline,authorized):
        try:
            def valid():return time.monotonic()<deadline and authorized()
            if not valid():raise ValueError('No current authority.')
            messages=[{'role':'system','content':payload['instructions']},
                {'role':'user','content':json.dumps({k:payload[k] for k in ('question','sources','trip')},ensure_ascii=False)}]
            count=self.count_tokens(json.dumps(messages,ensure_ascii=False))
            if type(count) is not int or not 0<=count<=5800:raise ValueError('Context limit.')
            body=json.dumps({'model':self.config.model,'messages':messages,'max_completion_tokens':600,'stream':False}).encode()
            raw=self.transport(self.config.endpoint,{'Authorization':'Bearer '+self.config.api_key,
                'Content-Type':'application/json'},body,deadline=deadline,authorized=valid)
            if not valid() or not isinstance(raw,bytes) or len(raw)>65536:raise ValueError('Response limit.')
            parsed=json.loads(raw)
            choices=parsed['choices']
            if not isinstance(choices,list) or len(choices)!=1:raise ValueError('Invalid choices.')
            choice=choices[0];message=choice['message'];content=message.get('content')
            usage=parsed.get('usage',{}).get('completion_tokens',0)
            if (choice.get('finish_reason')!='stop' or message.get('tool_calls') or message.get('function_call')
                    or message.get('refusal') or not isinstance(content,str) or len(content.encode())>4096
                    or type(usage) is not int or not 0<=usage<=600):raise ValueError('Unsupported model result.')
            output_count=self.count_tokens(content)
            if type(output_count) is not int or not 0<=output_count<=600:raise ValueError('Output limit.')
            return content
        except Exception:
            raise ProviderUnavailable('AI provider unavailable; use FAQs.') from None


def _post_json(endpoint,headers,body,*,deadline,authorized):
    """One HTTPS request, certificate checks on, no redirects and no retries.

    The pipeline enforces the user-facing wall deadline. DNS can outlive a
    socket timeout: the worker keeps its global reservation until it exits;
    it rechecks expiry/authority after connecting and before sending any data.
    It must NOT release a timed-out worker's slot while that worker still runs.
    """
    url=urlsplit(endpoint)
    connection=None
    def remaining():
        value=deadline-time.monotonic()
        if value<=0:raise TimeoutError('AI deadline exceeded.')
        return min(value,15)
    try:
        if not authorized():raise ValueError('Authorization expired.')
        connection=http.client.HTTPSConnection(url.hostname,443,timeout=remaining())
        connection.connect()
        if not authorized():raise ValueError('Authorization expired.')
        connection.sock.settimeout(remaining())
        connection.request('POST',url.path,body=body,headers=headers)
        connection.sock.settimeout(remaining())
        response=connection.getresponse()
        if response.status!=200:raise ValueError('Provider unavailable.')
        length=response.getheader('Content-Length')
        if length is not None and (not length.isdigit() or int(length)>65536):raise ValueError('Response limit.')
        chunks=[];size=0
        while True:
            if connection.sock is not None:connection.sock.settimeout(remaining())
            remaining()
            chunk=response.read1(min(1024,65537-size))
            if not chunk:break
            size+=len(chunk)
            if size>65536:raise ValueError('Response limit.')
            chunks.append(chunk)
        remaining()
        return b''.join(chunks)
    finally:
        if connection is not None:connection.close()

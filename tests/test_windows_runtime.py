"""Approved local Windows-runtime contracts, defined before feature implementation."""
from copy import deepcopy
from http.cookiejar import CookieJar
import json
from pathlib import Path
import socket
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlencode
from urllib.request import Request,build_opener,HTTPCookieProcessor,ProxyHandler,HTTPRedirectHandler

import pytest

from phase8_helpers import api_symbol


def runtime_api(name): return api_symbol('app_runtime',name)


def test_http_fixture_uses_no_user_proxy_or_browser_profile():
    opener = build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
    assert opener is not None


def test_default_profile_is_separate_from_app_and_requires_absolute_user_root(tmp_path):
    locate = runtime_api('default_data_dir')
    assert locate({'LOCALAPPDATA':str(tmp_path)}) == tmp_path/'TripPlanner'
    for env in ({},{'LOCALAPPDATA':''},{'LOCALAPPDATA':'relative'}):
        with pytest.raises(ValueError): locate(env)


def test_settings_have_stable_private_secret_and_fresh_copies(tmp_path):
    Settings = runtime_api('ProfileSettings')
    first = Settings(tmp_path).load()
    assert first['version']==1 and first['appearance']=='system'
    assert len(first['secret_key'])==64 and int(first['secret_key'],16)
    first['appearance']='dark'
    second = Settings(tmp_path).load()
    assert second['appearance']=='system'
    assert second['secret_key']==first['secret_key']
    assert Settings(tmp_path/'different').load()['secret_key']!=first['secret_key']


@pytest.mark.parametrize('mode',['light','dark','system'])
def test_settings_persist_only_valid_enum_and_keep_secret(tmp_path,mode):
    settings = runtime_api('ProfileSettings')(tmp_path)
    before = settings.load()
    settings.set_appearance(mode)
    assert runtime_api('ProfileSettings')(tmp_path).load()=={**before,'appearance':mode}


@pytest.mark.parametrize('mode',['Dark','',None,{},'../private','<script>'])
def test_invalid_appearance_cannot_modify_settings(tmp_path,mode):
    settings = runtime_api('ProfileSettings')(tmp_path)
    before = settings.load()
    with pytest.raises(ValueError): settings.set_appearance(mode)
    assert settings.load()==before


@pytest.mark.parametrize('text',['broken json','{}','{"version": true,"secret_key":"bad","appearance":"dark"}'])
def test_corrupt_settings_are_not_reset_or_overwritten(tmp_path,text):
    Settings = runtime_api('ProfileSettings')
    path = tmp_path/'settings.json'
    path.write_text(text,encoding='utf-8')
    with pytest.raises(ValueError): Settings(tmp_path).load()
    assert path.read_text(encoding='utf-8')==text


def test_profile_lock_prevents_double_launch_and_releases_after_error(tmp_path):
    Lock = runtime_api('ProfileLock')
    with pytest.raises(RuntimeError,match='QA exception'):
        with Lock(tmp_path):
            with pytest.raises(RuntimeError):
                with Lock(tmp_path): pytest.fail('Second profile owner acquired lock.')
            raise RuntimeError('QA exception')
    with Lock(tmp_path): pass


def test_native_factory_overrides_inherited_web_database_and_secret(tmp_path,monkeypatch):
    make = runtime_api('make_desktop_app')
    monkeypatch.setenv('TRIPPLANNER_DATABASE',str(tmp_path/'do-not-use.sqlite3'))
    monkeypatch.setenv('TRIPPLANNER_SECRET_KEY','do-not-copy-web-secret')
    app,settings = make(tmp_path/'native')
    assert Path(app.config['DATABASE'])==tmp_path/'native'/'trips.sqlite3'
    assert app.secret_key==settings.load()['secret_key'] and app.secret_key!='do-not-copy-web-secret'
    assert not app.debug and not (tmp_path/'do-not-use.sqlite3').exists()


@pytest.fixture
def desktop(tmp_path):
    # Resolve future APIs only when the test unpacks this value: missing code
    # is a test assertion at the red checkpoint, not a fixture/setup failure.
    owned=[]
    class LazyDesktop:
        def __iter__(self):
            app,settings=runtime_api('make_desktop_app')(tmp_path/'native')
            runtime=runtime_api('DesktopRuntime')(app,settings)
            runtime.start(timeout=5)
            owned.append(runtime)
            opener=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
            return iter((app,settings,runtime,opener))
    try:
        yield LazyDesktop()
    finally:
        for runtime in owned: runtime.stop()


def read(opener,url,**options):
    try:
        with opener.open(Request(url,**options),timeout=3) as response:
            return response.status,response.read(),dict(response.headers)
    except HTTPError as error:
        return error.code,error.read(),dict(error.headers)


def enter(runtime,opener):
    status,body,headers = read(opener,runtime.bootstrap_url)
    assert status==200 and b'TripPlanner' in body
    return body.decode('utf-8')


@pytest.mark.parametrize('path',['/','/plan','/trips','/trips/1','/credits','/static/css/style.css','/_desktop/health'])
def test_all_native_routes_require_launch_cookie(desktop,path):
    _,_,runtime,opener = desktop
    status,body,_ = read(opener,runtime.origin+path)
    assert status==403 and runtime.access_token.encode() not in body


def test_bootstrap_is_single_use_and_tokens_are_not_rendered(desktop):
    _,_,runtime,opener = desktop
    html = enter(runtime,opener)
    assert runtime.access_token not in html
    assert read(opener,runtime.bootstrap_url)[0]==403
    assert read(opener,runtime.origin+'/trips')[0]==200
    assert read(opener,runtime.origin+'/_desktop/health')[0]==200


def test_bad_bootstrap_does_not_grant_access(desktop):
    _,_,runtime,opener = desktop
    assert read(opener,runtime.origin+'/_desktop/open?token=wrong')[0]==403
    assert read(opener,runtime.origin+'/')[0]==403
    assert 'token=' in runtime.bootstrap_url


def test_private_cookie_and_foreign_host_origin_protection(desktop):
    _,_,runtime,opener = desktop
    enter(runtime,opener)
    cookie_handler = next(x for x in opener.handlers if isinstance(x,HTTPCookieProcessor))
    cookie = next(x for x in cookie_handler.cookiejar if x.name=='tripplanner_desktop')
    assert cookie.has_nonstandard_attr('HttpOnly')
    assert cookie.get_nonstandard_attr('SameSite')=='Strict'
    assert read(opener,runtime.origin+'/',headers={'Host':'foreign.example'})[0] in (400,403)
    assert read(opener,runtime.origin+'/_desktop/appearance',method='POST',data=b'{}',
                headers={'Origin':'https://foreign.example','Content-Type':'application/json'})[0]==403


def test_native_html_form_origin_survives_referrer_policy_and_trip_can_be_saved(desktop,parse_page):
    from phase8_helpers import CITY_PROFILES
    from phase8_form_helpers import form_for,context_fields
    _,_,runtime,opener=desktop
    enter(runtime,opener)
    _,body,headers=read(opener,runtime.origin+'/plan')
    # Fetch standard: no-referrer makes a non-CORS HTML form's Origin null.
    # Model that browser rule independently rather than giving every POST a
    # hand-written good Origin and missing the packaged-browser regression.
    browser_origin='null' if headers.get('Referrer-Policy')=='no-referrer' else runtime.origin
    form=form_for(CITY_PROFILES[0])
    form.update(context_fields(body.decode('utf-8'),parse_page))
    post_headers={'Content-Type':'application/x-www-form-urlencoded','Origin':browser_origin}
    status,ideas,_=read(opener,runtime.origin+'/plan',method='POST',
                        data=urlencode(list(form.items(multi=True))).encode(),headers=post_headers)
    assert status==200 and 'matching ideas' in ideas.decode('utf-8')
    status,body,headers=read(opener,runtime.origin+'/itinerary')
    assert status==200
    page=parse_page(body.decode('utf-8'))
    save=page.find('form',action='/itinerary/save')
    assert save is not None
    fields={name:save.find('input',name=name).attrs['value'] for name in ('csrf_token','snapshot_fingerprint')}
    fields['trip_name']='Native form regression'
    status,saved,_=read(opener,runtime.origin+'/itinerary/save',method='POST',data=urlencode(fields).encode(),headers=post_headers)
    assert status==200 and 'Native form regression' in saved.decode('utf-8')


def test_sensitive_bootstrap_keeps_no_referrer_but_clean_pages_use_same_origin(desktop):
    _,_,runtime,opener=desktop
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs): return None
    direct=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()),NoRedirect())
    status,_,headers=read(direct,runtime.bootstrap_url)
    assert status==303 and headers['Referrer-Policy']=='no-referrer'
    status,_,headers=read(direct,runtime.origin+'/plan')
    assert status==200 and headers['Referrer-Policy']=='same-origin'


@pytest.mark.parametrize('path',['/plan','/_desktop/appearance'])
def test_opaque_null_origin_is_still_rejected(desktop,path):
    _,_,runtime,opener=desktop
    enter(runtime,opener)
    assert read(opener,runtime.origin+path,method='POST',data=b'',headers={'Origin':'null'})[0]==403


def test_appearance_endpoint_needs_csrf_and_rejects_extra_fields(desktop,parse_page):
    _,_,runtime,opener = desktop
    html = enter(runtime,opener)
    meta = parse_page(html).find('meta',name='desktop-csrf')
    assert meta and meta.attrs['content']
    url = runtime.origin+'/_desktop/appearance'
    payload = json.dumps({'appearance':'dark'}).encode()
    assert read(opener,url,method='POST',data=payload,headers={'Content-Type':'application/json'})[0]==400
    headers = {'Content-Type':'application/json','X-CSRF-Token':meta.attrs['content'],'Origin':runtime.origin}
    for payload in ({'appearance':'Dark'},{'appearance':'dark','path':'elsewhere'},[],{'appearance':None}):
        assert read(opener,url,method='POST',data=json.dumps(payload).encode(),headers=headers)[0]==400


def test_appearance_survives_restart_on_another_origin_without_trip_changes(tmp_path,parse_page):
    make = runtime_api('make_desktop_app')
    Runtime = runtime_api('DesktopRuntime')
    app,settings = make(tmp_path)
    runtime = Runtime(app,settings)
    runtime.start(timeout=5)
    first_origin=runtime.origin
    try:
        opener=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
        html=enter(runtime,opener)
        token=parse_page(html).find('meta',name='desktop-csrf').attrs['content']
        status,_,_=read(opener,runtime.origin+'/_desktop/appearance',method='POST',
                       data=b'{"appearance":"dark"}',headers={'Content-Type':'application/json','X-CSRF-Token':token,'Origin':runtime.origin})
        assert status==200 and settings.load()['appearance']=='dark'
        assert not Path(app.config['DATABASE']).exists()
    finally: runtime.stop()
    app2,settings2=make(tmp_path)
    with socket.socket() as occupied:
        occupied.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        occupied.bind(('127.0.0.1',int(urlsplit(first_origin).port)))
        occupied.listen()
        second=Runtime(app2,settings2)
        second.start(timeout=5)
        try:
            assert second.origin!=first_origin
            html=enter(second,build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar())))
            assert 'data-native-appearance="dark"' in html
        finally: second.stop()


def test_stop_releases_only_owned_service_and_is_idempotent(desktop):
    _,_,runtime,opener = desktop
    port=urlsplit(runtime.origin).port
    runtime.stop()
    runtime.stop()
    with socket.socket() as probe:
        probe.settimeout(.3)
        assert probe.connect_ex(('127.0.0.1',port))!=0


def test_failed_readiness_stops_owned_service_without_resetting_settings(tmp_path):
    from flask import request
    make=runtime_api('make_desktop_app')
    app,settings=make(tmp_path)
    before=deepcopy(settings.load())
    @app.before_request
    def unavailable_health():
        if request.path=='/_desktop/health': return 'QA startup unavailable',503
    runtime=runtime_api('DesktopRuntime')(app,settings)
    with pytest.raises(RuntimeError): runtime.start(timeout=.15)
    runtime.stop()
    assert settings.load()==before
    with socket.socket() as probe:
        probe.settimeout(.3)
        assert probe.connect_ex(('127.0.0.1',urlsplit(runtime.origin).port))!=0


@pytest.mark.parametrize('url,expected',[
    ('http://127.0.0.1:12345/plan','internal'),
    ('http://127.0.0.1:12345/credits#photo','internal'),
    ('https://www.google.com/maps/search/?api=1&query=Tokyo','external'),
    ('https://commons.wikimedia.org/wiki/File:Photo.jpg','external'),
    ('http://127.0.0.1:5000/trips','blocked'),('http://foreign.example','blocked'),
    ('https://user:secret@example.com','blocked'),('file:///C:/private','blocked'),
    ('javascript:alert(1)','blocked'),('data:text/html,bad','blocked'),
    ('https://127.0.0.1/private','blocked'),('https://localhost/private','blocked'),
    ('https://example.com/\nprivate','blocked'),('https://example.com\\@localhost','blocked'),
])
def test_window_navigation_stays_local_or_opens_safe_external_https(url,expected):
    decide=api_symbol('windows_app','navigation_action')
    assert decide(url,'http://127.0.0.1:12345')==expected

"""Additional failure/authority regressions; synthetic cloud data only."""
import importlib
import hashlib
import sqlite3

import pytest


def api():
    return importlib.import_module('account_sessions')


@pytest.mark.parametrize('issuer', ['https://issuer.example:bad',
    'https://issuer.example:99999', 'https://@issuer.example',
    'https://issuer.example/?', 'https://issuer.example/#', 'https://issuer.example/\x7f'])
def test_malformed_issuer_is_not_trusted(issuer):
    with pytest.raises(ValueError):
        api().VerifiedIdentity(issuer,'A',True,100000)


@pytest.fixture
def state(tmp_path):
    module=api()
    clock=[100000]
    path=tmp_path/'accounts.sqlite3'
    module.create_store(path)
    store=module.SessionStore(path,clock=lambda:clock[0])
    ident=module.VerifiedIdentity('https://issuer.example','A',True,clock[0])
    return module,clock,store,ident,store.issue(ident)


def test_failed_rotation_keeps_old_authority_and_account_count(state):
    module,clock,store,_,issued=state
    stale=module.VerifiedIdentity('https://issuer.example','B',True,clock[0]-300)
    with pytest.raises(ValueError):
        store.issue(stale,previous_token=issued.token)
    assert store.resolve(issued.token) is not None
    with sqlite3.connect(store.database) as db:
        assert db.execute('SELECT count(*) FROM accounts').fetchone()==(1,)


def test_rotation_transaction_failure_keeps_old_authority(state):
    # A locked store must fail without clearing the previous session or
    # creating a new account. This is bounded SQLite contention, not a load test.
    module,_,store,ident,issued=state
    with sqlite3.connect(store.database,isolation_level=None) as lock:
        lock.execute('BEGIN IMMEDIATE')
        with pytest.raises(module.AccountStoreUnavailable):
            store.issue(ident,previous_token=issued.token)
        lock.rollback()
    assert store.resolve(issued.token) is not None
    with sqlite3.connect(store.database) as db:
        assert db.execute('SELECT count(*) FROM account_sessions').fetchone()==(1,)


@pytest.mark.parametrize('sql', [
    'UPDATE accounts SET active=0',
    'UPDATE accounts SET generation=generation+1',
    'UPDATE account_sessions SET absolute_expires_at=absolute_expires_at+1',
    'UPDATE account_sessions SET idle_expires_at=idle_expires_at+1',
    'UPDATE account_sessions SET authenticated_at=created_at+1',
    'UPDATE account_sessions SET last_seen=created_at-1',
])
def test_corrupt_or_revoked_session_state_fails_closed(state,sql):
    _,_,store,_,issued=state
    with sqlite3.connect(store.database) as db:
        db.execute(sql)
    assert store.resolve(issued.token) is None
    assert not store.authorize(issued.token,owner_kind='account',owner_id=issued.principal.account_id)


def test_inactive_account_cannot_issue_new_session(state):
    _,_,store,ident,_=state
    with sqlite3.connect(store.database) as db:
        db.execute('UPDATE accounts SET active=0')
    with pytest.raises(ValueError):
        store.issue(ident)
    with sqlite3.connect(store.database) as db:
        assert db.execute('SELECT count(*) FROM account_sessions').fetchone()==(1,)


def test_corrupt_schema_is_not_repaired_silently(state):
    module,_,store,ident,_=state
    with sqlite3.connect(store.database) as db:
        db.execute('ALTER TABLE accounts ADD COLUMN unexpected TEXT')
    before=store.database.read_bytes()
    with pytest.raises(module.AccountStoreUnavailable):
        store.issue(ident)
    assert store.database.read_bytes()==before


def test_opaque_account_token_cannot_impersonate_guest_collection(tmp_path):
    from hosted import create_hosted_app,VISITOR_COOKIE
    directory=tmp_path/'guest'
    directory.mkdir()
    application=create_hosted_app({'TRIPPLANNER_SECRET_KEY':'ab'*32,
        'TRIPPLANNER_PUBLIC_HOST':'planner.example','TRIPPLANNER_STORAGE_DIR':str(directory)})
    raw='A'*43
    database=directory/'hosted-trips.sqlite3'
    with sqlite3.connect(database) as db:
        db.execute('INSERT INTO saved_trips(owner,title,created_at,fingerprint,snapshot_json) VALUES(?,?,?,?,?)',
            (hashlib.sha256(raw.encode()).hexdigest(),'private-guest-sentinel','2026-11-09','a'*64,' {} '))
        before=db.execute('SELECT * FROM saved_trips').fetchall()
    browser=application.test_client()
    browser.set_cookie('__Host-tripplanner_account',raw,domain='planner.example')
    browser.set_cookie(VISITOR_COOKIE,raw,domain='planner.example')
    assert browser.get('/trips/1',base_url='https://planner.example').status_code==404
    listing=browser.get('/trips',base_url='https://planner.example')
    assert listing.status_code==200
    assert 'private-guest-sentinel' not in listing.text
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT * FROM saved_trips').fetchall()==before

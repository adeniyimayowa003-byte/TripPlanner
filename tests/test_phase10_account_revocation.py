"""Revocation and effective-owner checks with separate real store objects."""
import importlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest


@pytest.fixture
def state(tmp_path):
    module = importlib.import_module('account_sessions')
    clock = [100000]
    path = tmp_path/'accounts.sqlite3'
    module.create_store(path)
    store = module.SessionStore(path, clock=lambda:clock[0])
    def issue(subject='A'):
        return store.issue(module.VerifiedIdentity('https://issuer.example',subject,True,clock[0]))
    return module, clock, store, issue


def test_revoke_one_leaves_other_device_and_other_account(state):
    module, clock, store, issue = state
    one,two,foreign = issue(),issue(),issue('B')
    store.revoke(one.token)
    store.revoke(one.token)
    restarted = module.SessionStore(store.database,clock=lambda:clock[0])
    assert restarted.resolve(one.token) is None
    assert restarted.resolve(two.token) is not None
    assert restarted.resolve(foreign.token) is not None


@pytest.mark.parametrize('age,allowed', [(299,True),(300,False),(301,False)])
def test_all_device_logout_requires_recent_authentication(state, age, allowed):
    _, clock, store, issue = state
    one,two = issue(),issue()
    clock[0]+=age
    assert store.revoke_all(one.token) is allowed
    assert (store.resolve(two.token) is None) is allowed


def test_all_device_revocation_survives_restart_and_allows_new_login(state):
    module, clock, store, issue = state
    one,two,foreign = issue(),issue(),issue('B')
    assert store.revoke_all(one.token)
    restarted = module.SessionStore(store.database,clock=lambda:clock[0])
    assert restarted.resolve(one.token) is None
    assert restarted.resolve(two.token) is None
    assert restarted.resolve(foreign.token) is not None
    assert restarted.resolve(issue().token) is not None


def test_internal_recovery_hook_invalidates_exact_identity(state):
    _, _, store, issue = state
    one,two,foreign=issue(),issue(),issue('B')
    assert store.invalidate_identity('https://issuer.example','A')
    assert not store.invalidate_identity('https://unrelated.example','A')
    assert store.resolve(one.token) is None
    assert store.resolve(two.token) is None
    assert store.resolve(foreign.token) is not None
    assert store.resolve(issue().token) is not None


def test_authorization_checks_current_account_and_ownership_kind(state):
    _, _, store, issue = state
    one,other=issue(),issue('B')
    owner=one.principal.account_id
    assert store.authorize(one.token,owner_kind='account',owner_id=owner)
    assert not store.authorize(other.token,owner_kind='account',owner_id=owner)
    assert not store.authorize(one.token,owner_kind='anonymous',owner_id=owner)
    assert not store.authorize('forged',owner_kind='account',owner_id=owner)
    store.revoke(one.token)
    assert not store.authorize(one.token,owner_kind='account',owner_id=owner)


def test_purge_expired_records_preserves_accounts_and_active_sessions(state):
    _, clock, store, issue=state
    expired=issue()
    clock[0]+=1800
    current=issue('B')
    assert store.purge_expired()==1
    assert store.resolve(expired.token) is None
    assert store.resolve(current.token) is not None
    with sqlite3.connect(store.database) as db:
        assert db.execute('SELECT count(*) FROM accounts').fetchone() == (2,)
        assert db.execute('SELECT count(*) FROM account_sessions').fetchone() == (1,)


def test_issue_vs_recovery_has_a_serializable_result(state):
    module, clock, store, issue=state
    old=issue()
    def new_session():
        second=module.SessionStore(store.database,clock=lambda:clock[0])
        return second.issue(module.VerifiedIdentity('https://issuer.example','A',True,clock[0]))
    with ThreadPoolExecutor(max_workers=2) as workers:
        new=workers.submit(new_session)
        invalidated=workers.submit(store.invalidate_identity,'https://issuer.example','A')
        issued=new.result()
        assert invalidated.result()
    assert store.resolve(old.token) is None
    # A new login serialized after recovery may remain valid; one serialized
    # before recovery must be removed. No session can survive on an old epoch.
    with sqlite3.connect(store.database) as db:
        assert db.execute('SELECT count(*) FROM account_sessions s JOIN accounts a ON a.id=s.account_id WHERE s.generation != a.generation').fetchone()==(0,)
    principal=store.resolve(issued.token)
    assert principal is None or principal.account_id==old.principal.account_id


def test_storage_loss_fails_closed_instead_of_recreating(state):
    module, _, store, issue=state
    one=issue()
    store.database.unlink()
    with pytest.raises(module.AccountStoreUnavailable):
        store.authorize(one.token,owner_kind='account',owner_id=one.principal.account_id)
    assert not store.database.exists()

"""Session lifetimes: deterministic time, durable store, no clock sleeps."""
import importlib

import pytest


@pytest.fixture
def state(tmp_path):
    module = importlib.import_module('account_sessions')
    clock = [100000]
    path = tmp_path/'accounts.sqlite3'
    module.create_store(path)
    store = module.SessionStore(path, clock=lambda:clock[0])
    issued = store.issue(module.VerifiedIdentity('https://issuer.example', 'user-A', True, clock[0]))
    return module, clock, store, issued


def test_session_resolves_across_store_restart(state):
    module, clock, store, issued = state
    assert store.resolve(issued.token).account_id == issued.principal.account_id
    second = module.SessionStore(store.database, clock=lambda:clock[0])
    assert second.resolve(issued.token).account_id == issued.principal.account_id


@pytest.mark.parametrize('age,allowed', [(0, True),(1799, True),(1800, False),(1801, False)])
def test_idle_expiry_exact_boundary(state, age, allowed):
    _, clock, store, issued = state
    clock[0] += age
    assert (store.resolve(issued.token) is not None) is allowed


def test_touch_never_exceeds_absolute_lifetime(state):
    _, clock, store, issued = state
    start = clock[0]
    for age in range(1700,43200,1700):
        clock[0] = start + age
        current = store.resolve(issued.token)
        assert current is not None
        assert current.absolute_expires_at == start + 43200
        assert current.idle_expires_at <= current.absolute_expires_at
    clock[0] = start + 43199
    assert store.resolve(issued.token) is not None
    clock[0] = start + 43200
    assert store.resolve(issued.token) is None


def test_read_without_touch_does_not_extend_lifetime(state):
    _, clock, store, issued = state
    clock[0] += 1700
    assert store.resolve(issued.token, touch=False) is not None
    clock[0] += 100
    assert store.resolve(issued.token) is None


def test_backwards_clock_denies_session(state):
    _, clock, store, issued = state
    clock[0] += 30
    assert store.resolve(issued.token) is not None
    clock[0] -= 1
    assert store.resolve(issued.token) is None


@pytest.mark.parametrize('token', [None, '', 'x', 'A'*42, 'A'*44, '<script>'*10, 'é'*43, 'A'*43])
def test_invalid_or_unknown_tokens_never_resolve(state, token):
    _, _, store, _ = state
    assert store.resolve(token) is None


def test_rotate_revokes_old_session_only_after_new_issue_succeeds(state):
    module, clock, store, issued = state
    replacement = store.issue(module.VerifiedIdentity('https://issuer.example', 'user-A', True, clock[0]),
                              previous_token=issued.token)
    assert replacement.token != issued.token
    assert store.resolve(issued.token) is None
    assert store.resolve(replacement.token) is not None

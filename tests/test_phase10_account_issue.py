"""Issuance integration: actual isolated SQLite, trusted synthetic identities."""
import importlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest


def api():
    return importlib.import_module('account_sessions')


@pytest.fixture
def store(tmp_path):
    module = api()
    path = tmp_path / 'accounts.sqlite3'
    module.create_store(path)
    return module.SessionStore(path, clock=lambda: 100000)


def identity(subject='user-A', issuer='https://issuer.example', authenticated_at=100000):
    return api().VerifiedIdentity(issuer, subject, True, authenticated_at)


def test_issue_persists_only_digest_and_reuses_immutable_identity(store):
    import re
    one = store.issue(identity())
    two = store.issue(identity())
    assert re.fullmatch(r'[A-Za-z0-9_-]{43}', one.token)
    assert one.token != two.token
    assert one.principal.account_id == two.principal.account_id
    assert one.token not in repr(one)
    with sqlite3.connect(store.database) as db:
        assert db.execute('SELECT count(*) FROM accounts').fetchone() == (1,)
        assert db.execute('SELECT count(*) FROM account_sessions').fetchone() == (2,)
        rows = repr(db.execute('SELECT * FROM account_sessions').fetchall())
        assert one.token not in rows
        assert two.token not in rows
    assert one.token.encode() not in store.database.read_bytes()


@pytest.mark.parametrize('subject,issuer', [
    ('user-B', 'https://issuer.example'), ('user-A', 'https://another.example'),
    ('USER-A', 'https://issuer.example'), ('user-A', 'https://issuer.example/Tenant')])
def test_provider_subject_namespace_is_exact(store, subject, issuer):
    one = store.issue(identity())
    two = store.issue(identity(subject, issuer))
    assert one.principal.account_id != two.principal.account_id


@pytest.mark.parametrize('when', [100001, 99700, 0])
def test_stale_or_future_authentication_cannot_create_account(store, when):
    with pytest.raises(ValueError):
        store.issue(identity(authenticated_at=when))
    with sqlite3.connect(store.database) as db:
        assert db.execute('SELECT count(*) FROM accounts').fetchone() == (0,)


def test_plain_dict_cannot_be_used_as_verified_identity(store):
    with pytest.raises(ValueError):
        store.issue({'issuer': 'https://issuer.example', 'subject': 'user-A', 'email_verified': True})


def test_concurrent_registration_has_one_account(tmp_path):
    module = api()
    path = tmp_path/'accounts.sqlite3'
    module.create_store(path)
    def issue(_):
        return module.SessionStore(path, clock=lambda:100000).issue(identity())
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(issue, range(2)))
    assert results[0].token != results[1].token
    assert results[0].principal.account_id == results[1].principal.account_id
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM accounts').fetchone() == (1,)


def test_no_secrets_in_unavailable_store_errors(store):
    module = api()
    store.database.unlink()
    with pytest.raises(module.AccountStoreUnavailable) as error:
        store.issue(identity())
    assert str(store.database) not in str(error.value)
    assert 'user-A' not in str(error.value)
    assert not store.database.exists()

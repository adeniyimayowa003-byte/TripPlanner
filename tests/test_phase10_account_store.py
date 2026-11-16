"""Store/identity contracts, separate from authentication or production DBs."""
import importlib
from pathlib import Path
import sqlite3

import pytest


def api():
    return importlib.import_module('account_sessions')


@pytest.mark.parametrize('changes', [
    {'issuer': ''}, {'issuer': 'http://issuer.example'},
    {'issuer': 'https://user:pass@issuer.example'}, {'issuer': 'https://issuer.example/#x'},
    {'issuer': 'https://issuer.example/?secret=x'}, {'issuer': None},
    {'subject': ''}, {'subject': 'x' * 256}, {'subject': 'bad\nsubject'},
    {'subject': None}, {'email_verified': False}, {'email_verified': 'true'},
    {'email_verified': 1}, {'authenticated_at': True},
    {'authenticated_at': -1}, {'authenticated_at': float('nan')},
])
def test_identity_rejects_unverified_or_malformed_values(changes):
    values = dict(issuer='https://issuer.example', subject='user-A',
                  email_verified=True, authenticated_at=100000)
    with pytest.raises(ValueError):
        api().VerifiedIdentity(**(values | changes))


def test_identity_is_immutable_and_keeps_exact_provider_key():
    from dataclasses import FrozenInstanceError
    value = api().VerifiedIdentity('https://issuer.example/Tenant', 'CaseSensitive', True, 100000)
    assert value.issuer == 'https://issuer.example/Tenant'
    assert value.subject == 'CaseSensitive'
    with pytest.raises(FrozenInstanceError):
        value.subject = 'replacement'


def test_create_only_separate_store_with_private_permissions(tmp_path):
    module = api()
    path = tmp_path / 'accounts.sqlite3'
    module.create_store(path)
    assert path.is_file()
    assert path.stat().st_mode & 0o077 == 0
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA application_id').fetchone()[0] != 0
        assert db.execute('PRAGMA user_version').fetchone()[0] > 0
        assert db.execute('SELECT count(*) FROM accounts').fetchone() == (0,)
        assert db.execute('SELECT count(*) FROM account_sessions').fetchone() == (0,)
    before = path.read_bytes()
    with pytest.raises(module.AccountStoreUnavailable):
        module.create_store(path)
    assert path.read_bytes() == before


def test_existing_guest_database_cannot_be_reset_or_opened(tmp_path):
    import hosted_saved_trips
    module = api()
    path = tmp_path / 'hosted.sqlite3'
    hosted_saved_trips.initialize_store(path)
    before = path.read_bytes()
    with pytest.raises(module.AccountStoreUnavailable):
        module.create_store(path)
    with pytest.raises(module.AccountStoreUnavailable):
        module.SessionStore(path)
    assert path.read_bytes() == before


def test_missing_file_parent_and_relative_paths_never_create_implicitly(tmp_path):
    module = api()
    missing = tmp_path / 'missing' / 'accounts.sqlite3'
    with pytest.raises(module.AccountStoreUnavailable):
        module.SessionStore(missing)
    with pytest.raises(module.AccountStoreUnavailable):
        module.create_store(missing)
    with pytest.raises(ValueError):
        module.create_store(Path('relative-account-file.sqlite3'))
    assert not missing.parent.exists()


def test_symlink_and_incompatible_marker_fail_without_reset(tmp_path):
    module = api()
    path = tmp_path / 'real.sqlite3'
    module.create_store(path)
    link = tmp_path / 'link.sqlite3'
    link.symlink_to(path)
    with pytest.raises(module.AccountStoreUnavailable):
        module.SessionStore(link)
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA user_version=999')
    before = path.read_bytes()
    with pytest.raises(module.AccountStoreUnavailable):
        module.SessionStore(path)
    assert path.read_bytes() == before


def test_factories_do_not_activate_account_sessions(client, tmp_path, monkeypatch):
    # Real existing factory, never a substitute Flask test app or login backdoor.
    import app
    target = tmp_path / 'must-not-exist.sqlite3'
    monkeypatch.setenv('TRIPPLANNER_ACCOUNT_DATABASE', str(target))
    application = app.create_app({'TESTING': True, 'DATABASE': str(tmp_path/'trips.sqlite3')})
    browser = application.test_client()
    browser.set_cookie('__Host-tripplanner_account', 'A' * 43)
    assert browser.get('/help').status_code == 200
    for path in ['/account', '/account/sign-in', '/account/register', '/account/recovery']:
        assert browser.get(path).status_code == 404
    assert not target.exists()

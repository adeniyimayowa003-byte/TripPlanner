"""Dormant development adapter; NEVER the hosted PostgreSQL account store.

Only a future cryptographically verifying OIDC adapter may supply identities.
This module neither authenticates OIDC tokens nor exposes an HTTP login path.
No app factory imports it, no environment variable activates it, and existing
guest/snapshot databases must never be passed to this separate store.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import math
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit

_APPLICATION_ID = 0x54504131
_VERSION = 1
_ERROR = 'Account sessions are temporarily unavailable.'
_IDLE_SECONDS = 30 * 60
_ABSOLUTE_SECONDS = 12 * 60 * 60
_RECENT_SECONDS = 5 * 60
_DDL = (
    ('accounts', 'CREATE TABLE accounts (id TEXT PRIMARY KEY NOT NULL, issuer TEXT NOT NULL, subject TEXT NOT NULL, generation INTEGER NOT NULL CHECK(generation >= 0), active INTEGER NOT NULL CHECK(active IN (0,1)), created_at INTEGER NOT NULL, UNIQUE(issuer, subject))'),
    ('account_sessions', 'CREATE TABLE account_sessions (token_hash TEXT PRIMARY KEY NOT NULL, account_id TEXT NOT NULL REFERENCES accounts(id), generation INTEGER NOT NULL, authenticated_at INTEGER NOT NULL, created_at INTEGER NOT NULL, last_seen INTEGER NOT NULL, idle_expires_at INTEGER NOT NULL, absolute_expires_at INTEGER NOT NULL)'),
    ('account_sessions_expiry', 'CREATE INDEX account_sessions_expiry ON account_sessions(idle_expires_at, absolute_expires_at)'),
)


class AccountStoreUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str
    email_verified: bool
    authenticated_at: int

    def __post_init__(self):
        try:
            parts = urlsplit(self.issuer)
            valid_issuer = (isinstance(self.issuer, str) and 0 < len(self.issuer) <= 2048
                            and all(ord(c) > 32 and ord(c) != 127 for c in self.issuer)
                            and parts.scheme == 'https' and parts.hostname
                            and parts.username is None and parts.password is None
                            and '@' not in parts.netloc
                            and (parts.port is None or 1 <= parts.port <= 65535)
                            and '?' not in self.issuer and '#' not in self.issuer)
        except (ValueError, TypeError, AttributeError):
            valid_issuer = False
        if (not valid_issuer or not isinstance(self.subject, str)
                or not 0 < len(self.subject) <= 255
                or any(not 32 <= ord(c) < 127 for c in self.subject)
                or self.email_verified is not True
                or type(self.authenticated_at) is not int or self.authenticated_at < 0):
            raise ValueError('A verified provider identity is required.')


def _path(database):
    path = Path(database)
    if not path.is_absolute():
        raise ValueError('Choose an absolute, separate account database path.')
    if path.is_symlink() or not path.parent.is_dir():
        raise AccountStoreUnavailable(_ERROR)
    return path


def _validate(connection):
    if (connection.execute('PRAGMA application_id').fetchone()[0] != _APPLICATION_ID
            or connection.execute('PRAGMA user_version').fetchone()[0] != _VERSION
            or set(connection.execute("SELECT name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()) != set(_DDL)):
        raise AccountStoreUnavailable(_ERROR)


@contextmanager
def _connection(database, *, validate=True, transaction=False):
    connection = None
    try:
        path = _path(database)
        connection = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True,
                                     timeout=2.0, isolation_level=None)
        connection.execute('PRAGMA foreign_keys=ON')
        if transaction:
            connection.execute('BEGIN IMMEDIATE')
        if validate:
            _validate(connection)
        yield connection
    except (sqlite3.Error, OSError):
        raise AccountStoreUnavailable(_ERROR) from None
    finally:
        if connection is not None:
            try:
                connection.rollback()
                connection.close()
            except sqlite3.Error:
                raise AccountStoreUnavailable(_ERROR) from None


def create_store(database):
    """Explicit create-only development setup; never migrate/repair/reset data."""
    path = _path(database)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
    except OSError:
        raise AccountStoreUnavailable(_ERROR) from None
    with _connection(path, validate=False, transaction=True) as connection:
        for _, sql in _DDL:
            connection.execute(sql)
        connection.execute(f'PRAGMA application_id={_APPLICATION_ID}')
        connection.execute(f'PRAGMA user_version={_VERSION}')
        connection.commit()


@dataclass(frozen=True)
class Principal:
    account_id: str
    authenticated_at: int
    created_at: int
    idle_expires_at: int
    absolute_expires_at: int


@dataclass(frozen=True)
class IssuedSession:
    token: str = field(repr=False)
    principal: Principal


def _token_hash(token):
    if not isinstance(token, str) or re.fullmatch(r'[A-Za-z0-9_-]{43}', token) is None:
        return None
    return hashlib.sha256(b'tripplanner-account-session-v1:' + token.encode('ascii')).hexdigest()


def _lookup(connection, token_hash, now, *, touch=False):
    row = connection.execute(
        'SELECT s.account_id,s.authenticated_at,s.created_at,s.last_seen,'
        's.idle_expires_at,s.absolute_expires_at,s.generation,a.generation,a.active '
        'FROM account_sessions s JOIN accounts a ON a.id=s.account_id WHERE s.token_hash=?',
        (token_hash,)).fetchone()
    if row is None:
        return None
    account_id, authenticated, created, seen, idle, absolute, generation, current_generation, active = row
    if (not isinstance(account_id, str) or re.fullmatch(r'[0-9a-f]{64}', account_id) is None
            or any(type(value) is not int for value in row[1:])
            or active != 1 or generation != current_generation or generation < 0
            or not 0 <= created - authenticated < _RECENT_SECONDS
            or not 0 <= created <= seen <= now
            or absolute != created + _ABSOLUTE_SECONDS
            or idle != min(seen + _IDLE_SECONDS, absolute)
            or now >= idle or now >= absolute):
        return None
    if touch:
        idle = min(now + _IDLE_SECONDS, absolute)
        connection.execute('UPDATE account_sessions SET last_seen=?,idle_expires_at=? WHERE token_hash=?',
                           (now, idle, token_hash))
    return Principal(account_id, authenticated, created, idle, absolute)


class SessionStore:
    def __init__(self, database, *, clock=None):
        self.database = _path(database)
        self._clock = clock or time.time
        if not callable(self._clock):
            raise ValueError('A valid session clock is required.')
        with _connection(self.database):
            pass

    def _now(self):
        value = self._clock()
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('A valid session clock is required.')
        return int(value)

    def issue(self, identity, *, previous_token=None):
        """Server-internal only: caller must have verified a real OIDC response."""
        now = self._now()
        if type(identity) is not VerifiedIdentity:
            raise ValueError('A verified provider identity is required.')
        identity.__post_init__()
        if not 0 <= now - identity.authenticated_at < _RECENT_SECONDS:
            raise ValueError('Recent verified authentication is required.')
        token = secrets.token_urlsafe(32)
        token_hash = _token_hash(token)
        with _connection(self.database, transaction=True) as connection:
            connection.execute(
                'INSERT INTO accounts(id,issuer,subject,generation,active,created_at) '
                'VALUES(?,?,?,0,1,?) ON CONFLICT(issuer,subject) DO NOTHING',
                (secrets.token_hex(32), identity.issuer, identity.subject, now))
            account_id, generation, active = connection.execute(
                'SELECT id,generation,active FROM accounts WHERE issuer=? AND subject=?',
                (identity.issuer, identity.subject)).fetchone()
            if active != 1:
                raise ValueError('This account is unavailable.')
            connection.execute(
                'INSERT INTO account_sessions VALUES(?,?,?,?,?,?,?,?)',
                (token_hash, account_id, generation, identity.authenticated_at,
                 now, now, now + _IDLE_SECONDS, now + _ABSOLUTE_SECONDS))
            previous_hash = _token_hash(previous_token)
            if previous_hash:
                connection.execute('DELETE FROM account_sessions WHERE token_hash=?', (previous_hash,))
            connection.commit()
        return IssuedSession(token, Principal(account_id, identity.authenticated_at, now,
                                             now + _IDLE_SECONDS, now + _ABSOLUTE_SECONDS))

    def resolve(self, token, *, touch=True):
        """Revalidate authority on each operation; never trust a cached principal."""
        token_hash = _token_hash(token)
        if token_hash is None:
            return None
        now = self._now()
        with _connection(self.database, transaction=True) as connection:
            principal = _lookup(connection, token_hash, now, touch=touch)
            connection.commit()
        return principal

    def authorize(self, token, *, owner_kind, owner_id):
        """Check DB-derived ownership metadata, never a client-requested owner.

        This does not retrieve trips; a future repository must enforce ownership
        in every actual row query too. Anonymous digests are a distinct kind.
        """
        if (owner_kind != 'account' or not isinstance(owner_id, str)
                or re.fullmatch(r'[0-9a-f]{64}', owner_id) is None):
            return False
        principal = self.resolve(token)
        return principal is not None and secrets.compare_digest(principal.account_id, owner_id)

    def revoke(self, token):
        token_hash = _token_hash(token)
        if token_hash is None:
            return False
        with _connection(self.database, transaction=True) as connection:
            removed = connection.execute('DELETE FROM account_sessions WHERE token_hash=?',
                                         (token_hash,)).rowcount
            connection.commit()
        return removed == 1

    def revoke_all(self, token):
        token_hash = _token_hash(token)
        if token_hash is None:
            return False
        now = self._now()
        with _connection(self.database, transaction=True) as connection:
            principal = _lookup(connection, token_hash, now)
            if principal is None or not 0 <= now - principal.authenticated_at < _RECENT_SECONDS:
                return False
            _invalidate(connection, principal.account_id)
            connection.commit()
        return True

    def invalidate_identity(self, issuer, subject):
        """Server-internal hook, NOT an event receiver or event verification.

        A future caller MUST independently verify provider authenticity/replay
        protections before using this; it is never available to HTTP callers.
        """
        VerifiedIdentity(issuer, subject, True, 0)  # Validate key shape only.
        with _connection(self.database, transaction=True) as connection:
            row = connection.execute('SELECT id FROM accounts WHERE issuer=? AND subject=?',
                                     (issuer, subject)).fetchone()
            if row is None:
                return False
            _invalidate(connection, row[0])
            connection.commit()
        return True

    def purge_expired(self):
        """Explicit maintenance primitive; no scheduler/retention promise yet."""
        now = self._now()
        with _connection(self.database, transaction=True) as connection:
            count = connection.execute(
                'DELETE FROM account_sessions WHERE idle_expires_at<=? OR absolute_expires_at<=?',
                (now, now)).rowcount
            connection.commit()
        return count


def _invalidate(connection, account_id):
    connection.execute('UPDATE accounts SET generation=generation+1 WHERE id=?', (account_id,))
    connection.execute('DELETE FROM account_sessions WHERE account_id=?', (account_id,))

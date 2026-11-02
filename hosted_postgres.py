"""Persistent, owner-scoped PostgreSQL storage for the free public demo.

All snapshots/fingerprints use the existing contract. No local collection is
uploaded or migrated. Public credentials are validated by the hosted factory;
repository functions also support explicitly isolated local integration tests.
"""
from contextlib import contextmanager
import math
import re
from urllib.parse import parse_qsl, urlsplit

import certifi
import psycopg
from psycopg.conninfo import conninfo_to_dict

from saved_trips import (SavedTripUnavailableError, StorageUnavailableError,
                         _content_key, _record, _timestamp, _MAX_TRIP_ID)
from snapshots import dump_snapshot, load_snapshot, normalize_trip_name

SCHEMA = "tripplanner_hosted_v1"
_TABLE = SCHEMA + ".saved_trips"
_META = SCHEMA + ".metadata"
_COLUMNS = "id, title, created_at, fingerprint, snapshot_json"
_MESSAGE = "Saved trips are temporarily unavailable."


def validate_database_url(value):
    """Production accepts one credentialed TLS URL, never libpq overrides."""
    message = "Set a private PostgreSQL URL with credentials, database and sslmode=verify-full."
    try:
        if not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 33 for c in value):
            raise ValueError(message)
        parts = urlsplit(value)
        pairs = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
        query = dict(pairs)
        if (parts.scheme not in {"postgresql", "postgres"} or not parts.username or not parts.password
                or not parts.hostname or not re.fullmatch(r"[A-Za-z0-9.-]+", parts.hostname)
                or parts.path in {"", "/"} or parts.fragment
                or len(pairs) != len(query) or set(query) - {"sslmode", "channel_binding"}
                or query.get("sslmode") != "verify-full"
                or query.get("channel_binding", "prefer") not in {"require", "prefer"}
                or (parts.port is not None and not 1 <= parts.port <= 65535)):
            raise ValueError(message)
        conninfo_to_dict(value)  # Driver also checks its own URI syntax.
    except (ValueError, TypeError, psycopg.Error):
        raise ValueError(message) from None
    return value


def _owner(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("A verified collection owner is required.")
    return value


def _validate(connection):
    if connection.execute(f"SELECT id, version FROM {_META}").fetchall() != [(1, 1)]:
        raise StorageUnavailableError(_MESSAGE)
    columns = connection.execute(
        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = 'saved_trips' ORDER BY ordinal_position", (SCHEMA,)
    ).fetchall()
    expected = [("id", "bigint", "NO"), ("owner", "text", "NO"), ("title", "text", "NO"),
                ("created_at", "text", "NO"), ("fingerprint", "text", "NO"), ("snapshot_json", "text", "NO")]
    if columns != expected:
        raise StorageUnavailableError(_MESSAGE)
    constraints = connection.execute(
        "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
        "JOIN pg_class t ON t.oid = c.conrelid JOIN pg_namespace n ON n.oid = t.relnamespace "
        "WHERE n.nspname = %s AND t.relname = 'saved_trips' AND c.contype = 'u'", (SCHEMA,)
    ).fetchall()
    if constraints != [("UNIQUE (owner, fingerprint)",)]:
        raise StorageUnavailableError(_MESSAGE)


@contextmanager
def _connection(database, *, timeout=5.0, validate=True):
    connection = None
    try:
        options = {"connect_timeout": max(2, math.ceil(timeout))}
        if conninfo_to_dict(database).get("sslmode") == "verify-full":
            options["sslrootcert"] = certifi.where()
        connection = psycopg.connect(database, **options)
        milliseconds = str(max(1, math.ceil(timeout * 1000)))
        connection.execute("SELECT set_config('statement_timeout', %s, true)", (milliseconds,))
        connection.execute("SELECT set_config('lock_timeout', %s, true)", (milliseconds,))
        if validate:
            _validate(connection)
        yield connection
    except (psycopg.Error, OSError):
        # Driver exceptions can contain connection details; suppress the chain.
        raise StorageUnavailableError(_MESSAGE) from None
    finally:
        if connection is not None:
            try:
                try:
                    connection.rollback()
                finally:
                    connection.close()
            except psycopg.Error:
                raise StorageUnavailableError(_MESSAGE) from None


def initialize_store(database, *, timeout=5.0):
    """Create only an absent namespace, atomically; never migrate/reset one."""
    with _connection(database, timeout=timeout, validate=False) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(1414547513)")
        exists = connection.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", (SCHEMA,)).fetchone()
        if exists is None:
            connection.execute(f"CREATE SCHEMA {SCHEMA}")
            connection.execute(f"CREATE TABLE {_META} (id INTEGER PRIMARY KEY, version INTEGER NOT NULL)")
            connection.execute(f"INSERT INTO {_META} VALUES (1, 1)")
            connection.execute(
                f"CREATE TABLE {_TABLE} (id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY CHECK(id > 0), "
                "owner TEXT NOT NULL, title TEXT NOT NULL, created_at TEXT NOT NULL, "
                "fingerprint TEXT NOT NULL, snapshot_json TEXT NOT NULL, UNIQUE(owner, fingerprint))"
            )
            connection.execute(f"CREATE INDEX owner_order ON {_TABLE}(owner, created_at DESC, id DESC)")
        _validate(connection)
        connection.commit()
    check_store(database, timeout=timeout)


def check_store(database, *, timeout=5.0):
    with _connection(database, timeout=timeout) as connection:
        connection.execute(f"UPDATE {_META} SET version = version WHERE id = 1")
        # Rollback-only probe; no schema creation or reset on readiness.
        connection.rollback()


def save_trip(database, title, payload, *, owner, created_at=None, timeout=5.0):
    owner = _owner(owner)
    raw = dump_snapshot(payload)
    snapshot = load_snapshot(raw)
    title = normalize_trip_name(title, snapshot["preferences"])
    timestamp = _timestamp(created_at)
    fingerprint = _content_key(title, raw)
    with _connection(database, timeout=timeout) as connection:
        cursor = connection.execute(
            f"INSERT INTO {_TABLE} (owner, title, created_at, fingerprint, snapshot_json) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT(owner, fingerprint) DO NOTHING",
            (owner, title, timestamp, fingerprint, raw),
        )
        created = cursor.rowcount == 1
        row = connection.execute(f"SELECT {_COLUMNS} FROM {_TABLE} WHERE owner = %s AND fingerprint = %s",
                                 (owner, fingerprint)).fetchone()
        if row is None:
            raise StorageUnavailableError(_MESSAGE)
        record = _record(row)
        if not record["available"]:
            raise SavedTripUnavailableError(record["id"])
        connection.commit()
        return record, created


def list_trips(database, *, owner, timeout=5.0):
    owner = _owner(owner)
    with _connection(database, timeout=timeout) as connection:
        rows = connection.execute(f"SELECT {_COLUMNS} FROM {_TABLE} WHERE owner = %s ORDER BY created_at DESC, id DESC",
                                  (owner,)).fetchall()
        return [_record(row) for row in rows]


def get_trip(database, trip_id, *, owner, timeout=5.0):
    owner = _owner(owner)
    if type(trip_id) is not int or not 1 <= trip_id <= _MAX_TRIP_ID:
        return None
    with _connection(database, timeout=timeout) as connection:
        row = connection.execute(f"SELECT {_COLUMNS} FROM {_TABLE} WHERE owner = %s AND id = %s",
                                 (owner, trip_id)).fetchone()
        return None if row is None else _record(row)

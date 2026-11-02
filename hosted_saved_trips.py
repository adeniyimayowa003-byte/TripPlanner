"""Owner-scoped hosted snapshots; deliberately incompatible with local storage.

The immutable title/snapshot fingerprint remains the original contract. Only
the enclosing storage adds ownership. Never migrate/import a local collection.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import sqlite3

from saved_trips import (
    SavedTripUnavailableError, StorageUnavailableError, _content_key, _record,
    _timestamp, _MAX_TRIP_ID,
)
from snapshots import dump_snapshot, load_snapshot, normalize_trip_name

APPLICATION_ID = 0x54504839
_COLUMNS = "id, title, created_at, fingerprint, snapshot_json"
_MESSAGE = "Saved trips are temporarily unavailable."


def _owner(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("A verified collection owner is required.")
    return value


def _validate(connection):
    if (connection.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
            or connection.execute("PRAGMA user_version").fetchone()[0] != 1):
        raise StorageUnavailableError(_MESSAGE)
    expected = [("id", "INTEGER", 0, 1), ("owner", "TEXT", 1, 0),
                ("title", "TEXT", 1, 0), ("created_at", "TEXT", 1, 0),
                ("fingerprint", "TEXT", 1, 0), ("snapshot_json", "TEXT", 1, 0)]
    columns = connection.execute("PRAGMA table_info(saved_trips)").fetchall()
    if [(row[1], row[2].upper(), row[3], row[5]) for row in columns] != expected:
        raise StorageUnavailableError(_MESSAGE)
    if connection.execute("SELECT id, version FROM hosted_metadata").fetchall() != [(1, 1)]:
        raise StorageUnavailableError(_MESSAGE)
    unique_indexes = []
    for index in connection.execute("PRAGMA index_list(saved_trips)"):
        if index[2]:
            if index[4]:
                raise StorageUnavailableError(_MESSAGE)
            unique_indexes.append(connection.execute(
                "SELECT name FROM pragma_index_info(?) ORDER BY seqno", (index[1],)
            ).fetchall())
    if unique_indexes != [[("owner",), ("fingerprint",)]]:
        raise StorageUnavailableError(_MESSAGE)


@contextmanager
def _connection(database, *, writable=False, timeout=5.0, validate=True):
    connection = None
    try:
        # mode=rw/ro is essential: loss of a mount/file must never create a DB.
        uri = Path(database).resolve().as_uri() + ("?mode=rw" if writable else "?mode=ro")
        connection = sqlite3.connect(uri, uri=True, timeout=timeout, isolation_level=None)
        if validate:
            _validate(connection)
        yield connection
    except (sqlite3.Error, OSError) as error:
        raise StorageUnavailableError(_MESSAGE) from error
    finally:
        if connection is not None:
            try:
                connection.rollback()
                connection.close()
            except sqlite3.Error as error:
                raise StorageUnavailableError(_MESSAGE) from error


def initialize_store(database, *, timeout=5.0):
    """Startup only: create an absent file, otherwise validate without migration."""
    path = Path(database)
    created = False
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        created = True
    except FileExistsError:
        pass
    except OSError as error:
        raise StorageUnavailableError(_MESSAGE) from error
    with _connection(path, writable=created, timeout=timeout, validate=not created) as connection:
        if created:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE saved_trips (id INTEGER PRIMARY KEY CHECK(id > 0), "
                "owner TEXT NOT NULL, title TEXT NOT NULL, created_at TEXT NOT NULL, "
                "fingerprint TEXT NOT NULL, snapshot_json TEXT NOT NULL, UNIQUE(owner, fingerprint))"
            )
            connection.execute("CREATE INDEX owner_order ON saved_trips(owner, created_at DESC, id DESC)")
            connection.execute("CREATE TABLE hosted_metadata (id INTEGER PRIMARY KEY, version INTEGER NOT NULL)")
            connection.execute("INSERT INTO hosted_metadata VALUES (1, 1)")
            connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
            connection.execute("PRAGMA user_version = 1")
            connection.commit()
    check_store(path, timeout=timeout)


def check_store(database, *, timeout=5.0):
    """Readiness: validate then probe the persistent write path, rolling back."""
    with _connection(database, writable=True, timeout=timeout) as connection:
        if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise StorageUnavailableError(_MESSAGE)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("UPDATE hosted_metadata SET version = version WHERE id = 1")
        connection.rollback()


def save_trip(database, title, payload, *, owner, created_at=None, timeout=5.0):
    owner = _owner(owner)
    raw = dump_snapshot(payload)
    snapshot = load_snapshot(raw)
    title = normalize_trip_name(title, snapshot["preferences"])
    timestamp = _timestamp(created_at)
    fingerprint = _content_key(title, raw)
    with _connection(database, writable=True, timeout=timeout) as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            "INSERT INTO saved_trips (owner, title, created_at, fingerprint, snapshot_json) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(owner, fingerprint) DO NOTHING",
            (owner, title, timestamp, fingerprint, raw),
        )
        created = cursor.rowcount == 1
        row = connection.execute(
            f"SELECT {_COLUMNS} FROM saved_trips WHERE owner = ? AND fingerprint = ?",
            (owner, fingerprint),
        ).fetchone()
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
        rows = connection.execute(
            f"SELECT {_COLUMNS} FROM saved_trips WHERE owner = ? ORDER BY created_at DESC, id DESC",
            (owner,),
        ).fetchall()
        return [_record(row) for row in rows]


def get_trip(database, trip_id, *, owner, timeout=5.0):
    owner = _owner(owner)
    if type(trip_id) is not int or not 1 <= trip_id <= _MAX_TRIP_ID:
        return None
    with _connection(database, timeout=timeout) as connection:
        row = connection.execute(
            f"SELECT {_COLUMNS} FROM saved_trips WHERE owner = ? AND id = ?", (owner, trip_id)
        ).fetchone()
        return None if row is None else _record(row)

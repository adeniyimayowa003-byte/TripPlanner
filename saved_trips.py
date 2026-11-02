"""Durable, local saved snapshots using short-lived SQLite connections.

This module knows nothing about Flask, sessions, or today's travel catalog.
Each save is a transaction: the unique content key selects one immutable row,
and callers only receive success after that transaction has committed.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time

from snapshots import (
    SnapshotValidationError,
    dump_snapshot,
    load_snapshot,
    normalize_trip_name,
)


_SCHEMA_VERSION = 1
_MAX_TRIP_ID = 2**63 - 1
_COLUMNS = "id, title, created_at, fingerprint, snapshot_json"
_STORAGE_MESSAGE = "Saved trips are temporarily unavailable."


class StorageUnavailableError(Exception):
    """The collection cannot safely be read or written."""


class SavedTripUnavailableError(Exception):
    """An identical save already exists, but that stored row is damaged."""

    def __init__(self, trip_id):
        super().__init__("This saved trip is unavailable.")
        self.trip_id = trip_id


def _content_key(title, raw_snapshot):
    """Use a structured value, not ambiguous concatenated strings, for equality."""
    canonical = json.dumps(
        {"title": title, "snapshot": json.loads(raw_snapshot)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _timestamp(created_at):
    value = datetime.now(timezone.utc) if created_at is None else created_at
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() != timedelta(0)
    ):
        raise ValueError("Creation time must be an aware UTC datetime.")
    # Fixed precision and offset make SQLite's text ordering chronological.
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _valid_timestamp(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
        return _timestamp(parsed) == value
    except (TypeError, ValueError, OverflowError):
        return False


def _valid_title(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        # A nonblank title needs no preferences to generate a default.
        return normalize_trip_name(value, {}) == value
    except (TypeError, ValueError, KeyError):
        return False


def _record(row):
    """Decode one row; damage in it must not hide other readable snapshots."""
    trip_id, title, created_at, fingerprint, raw_snapshot = row
    title_ok = _valid_title(title)
    time_ok = _valid_timestamp(created_at)
    result = {
        "id": trip_id,
        "title": title if title_ok else "Unavailable saved trip",
        "created_at": created_at if time_ok else None,
        "snapshot": None,
        "available": False,
    }
    if (
        type(trip_id) is not int
        or not 1 <= trip_id <= _MAX_TRIP_ID
        or not title_ok
        or not time_ok
        or not isinstance(fingerprint, str)
        or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None
    ):
        return result
    try:
        snapshot = load_snapshot(raw_snapshot)
        # A changed but otherwise valid JSON document is not the saved content
        # its duplicate key identifies. Do not silently repair either value.
        if fingerprint != _content_key(title, dump_snapshot(snapshot)):
            return result
    except (SnapshotValidationError, TypeError, ValueError):
        return result
    result.update(snapshot=snapshot, available=True)
    return result


def _validate_schema(connection):
    """Inspect existing storage without rewriting or automatically migrating it."""
    if connection.execute("PRAGMA user_version").fetchone()[0] != _SCHEMA_VERSION:
        raise StorageUnavailableError(_STORAGE_MESSAGE)
    kind = connection.execute(
        "SELECT type FROM sqlite_master WHERE name = ?", ("saved_trips",)
    ).fetchone()
    if kind != ("table",):
        raise StorageUnavailableError(_STORAGE_MESSAGE)
    columns = connection.execute("PRAGMA table_info(saved_trips)").fetchall()
    expected = [
        ("id", "INTEGER", 1),
        ("title", "TEXT", 0),
        ("created_at", "TEXT", 0),
        ("fingerprint", "TEXT", 0),
        ("snapshot_json", "TEXT", 0),
    ]
    if [(row[1], row[2].upper(), row[5]) for row in columns] != expected:
        raise StorageUnavailableError(_STORAGE_MESSAGE)
    if any(not row[3] for row in columns[1:]):
        raise StorageUnavailableError(_STORAGE_MESSAGE)
    # A UNIQUE single-column fingerprint index is the concurrency guarantee.
    unique_fingerprint = False
    for index in connection.execute("PRAGMA index_list(saved_trips)"):
        if not index[2] or index[4]:
            continue
        # The table-valued pragma accepts a bound value rather than assembling
        # a statement from an index name read out of an existing database.
        names = connection.execute(
            "SELECT name FROM pragma_index_info(?) ORDER BY seqno", (index[1],)
        ).fetchall()
        if names == [("fingerprint",)]:
            unique_fingerprint = True
    if not unique_fingerprint:
        raise StorageUnavailableError(_STORAGE_MESSAGE)


def _initialize_or_validate(connection, *, may_initialize):
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    if version == 0 and not tables:
        if not may_initialize:
            # Another first writer may have just created this file but not
            # initialized its schema. Only the creator may initialize it.
            return False
        connection.execute(
            "CREATE TABLE saved_trips ("
            "id INTEGER PRIMARY KEY CHECK (id > 0), "
            "title TEXT NOT NULL, "
            "created_at TEXT NOT NULL, "
            "fingerprint TEXT NOT NULL UNIQUE, "
            "snapshot_json TEXT NOT NULL)"
        )
        connection.execute("PRAGMA user_version = 1")
    _validate_schema(connection)
    return True


def _begin_save(connection, *, may_initialize, timeout):
    """Wait briefly for an in-progress first save without resetting any file.

    Release the SQL lock while waiting so the creator can initialize. This also
    works across processes; a Python-only thread lock would not cover that case.
    A pre-existing empty/incompatible file is never automatically initialized.
    """
    deadline = time.monotonic() + max(0, timeout)
    while True:
        connection.execute("BEGIN IMMEDIATE")
        if _initialize_or_validate(connection, may_initialize=may_initialize):
            return
        connection.rollback()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise StorageUnavailableError(_STORAGE_MESSAGE)
        time.sleep(min(0.01, remaining))


def _rollback(connection):
    if connection is not None:
        try:
            connection.rollback()
        except sqlite3.Error:
            # Preserve the original operation's failure, never claim success.
            pass


def _close(connection):
    if connection is not None:
        try:
            connection.close()
        except sqlite3.Error as error:
            raise StorageUnavailableError(_STORAGE_MESSAGE) from error


def save_trip(database_path, title, payload, *, created_at=None, timeout=5.0):
    """Commit a new snapshot, or return its existing immutable duplicate.

    Input validation happens before even creating the parent directory. An
    immediate transaction serializes writers, while the UNIQUE key remains the
    final authority for duplicate detection, including concurrent requests.
    """
    raw_snapshot = dump_snapshot(payload)
    snapshot = load_snapshot(raw_snapshot)
    normalized_title = normalize_trip_name(title, snapshot["preferences"])
    timestamp = _timestamp(created_at)
    fingerprint = _content_key(normalized_title, raw_snapshot)
    connection = None
    try:
        path = Path(database_path)
        existed = path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=timeout, isolation_level=None)
        _begin_save(connection, may_initialize=not existed, timeout=timeout)
        # This conflict target ignores only this precise unique-key conflict.
        # Triggers and other constraints still raise, and no row is replaced.
        cursor = connection.execute(
            "INSERT INTO saved_trips (title, created_at, fingerprint, snapshot_json) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(fingerprint) DO NOTHING",
            (normalized_title, timestamp, fingerprint, raw_snapshot),
        )
        created = cursor.rowcount == 1
        row = connection.execute(
            f"SELECT {_COLUMNS} FROM saved_trips WHERE fingerprint = ?",
            (fingerprint,),
        ).fetchone()
        if row is None:
            raise StorageUnavailableError(_STORAGE_MESSAGE)
        record = _record(row)
        if not record["available"]:
            raise SavedTripUnavailableError(record["id"])
        connection.commit()
        return record, created
    except (sqlite3.Error, OSError) as error:
        _rollback(connection)
        raise StorageUnavailableError(_STORAGE_MESSAGE) from error
    except (StorageUnavailableError, SavedTripUnavailableError):
        _rollback(connection)
        raise
    finally:
        _close(connection)


def _read(database_path, *, trip_id=None, timeout=5.0):
    connection = None
    try:
        path = Path(database_path)
        if not path.exists():
            return []
        # Read mode avoids creating a new empty database in a read/delete race.
        connection = sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro", uri=True, timeout=timeout,
            isolation_level=None,
        )
        connection.execute("BEGIN")
        _validate_schema(connection)
        if trip_id is None:
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM saved_trips ORDER BY created_at DESC, id DESC"
            ).fetchall()
        else:
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM saved_trips WHERE id = ?", (trip_id,)
            ).fetchall()
        return [_record(row) for row in rows]
    except (sqlite3.Error, OSError) as error:
        raise StorageUnavailableError(_STORAGE_MESSAGE) from error
    finally:
        _rollback(connection)
        _close(connection)


def list_trips(database_path, *, timeout=5.0):
    """Return newest-first records, leaving absent storage completely absent."""
    return _read(database_path, timeout=timeout)


def get_trip(database_path, trip_id, *, timeout=5.0):
    """Return one row or None, without opening storage for out-of-range IDs."""
    if type(trip_id) is not int or not 1 <= trip_id <= _MAX_TRIP_ID:
        return None
    records = _read(database_path, trip_id=trip_id, timeout=timeout)
    return records[0] if records else None

"""Executable SQLite contract for Phase 6, using only test-local files.

Imports of the not-yet-built repository happen inside helpers. Discovery must
succeed before implementation; a missing feature is a test failure, not a
collection error. Fixtures construct snapshots from the working Phase 5 APIs.
The optional created_at test seam accepts an aware UTC datetime; returned
creation metadata is ISO UTC text, rather than a machine-local naive time.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import importlib
import importlib.util
import json
import re
import sqlite3
import sys
from threading import Barrier, Event, current_thread

import pytest


def repository():
    return importlib.import_module("saved_trips")


def utc(value):
    """Accept either conventional ISO spelling of UTC, but not naive times."""
    assert isinstance(value, str)
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(0)
    return result


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_rows(path):
    with closing(sqlite3.connect(path)) as connection, connection:
        return connection.execute(
            "SELECT id, title, created_at, fingerprint, snapshot_json "
            "FROM saved_trips ORDER BY id"
        ).fetchall()


def change_raw_snapshot(path, trip_id, transform):
    with closing(sqlite3.connect(path)) as connection, connection:
        raw = connection.execute(
            "SELECT snapshot_json FROM saved_trips WHERE id = ?", (trip_id,)
        ).fetchone()[0]
        changed = transform(raw)
        connection.execute(
            "UPDATE saved_trips SET snapshot_json = ? WHERE id = ?",
            (changed, trip_id),
        )
    return changed


def every_money_value(payload):
    """Inspect all documented money locations without trusting production code."""
    values = [payload["preferences"]["budget"], payload["daily_budget"]]
    items = list(payload["recommendations"]) + list(payload["itinerary"]["unused_items"])
    for day in payload["itinerary"]["days"]:
        values.append(day["estimated_cost"])
        items.extend(entry["item"] for entry in day["slots"] if entry["item"] is not None)
    for item in items:
        values.extend([item["estimated_cost"], item["place"]["estimated_cost"]])
    values.extend([
        payload["itinerary"]["estimated_cost"],
        payload["itinerary"]["unallocated_allowance"],
    ])
    return values


@pytest.fixture
def database_path(tmp_path):
    return tmp_path / "saved-collection" / "trips.sqlite3"


def test_absent_database_reads_are_empty_and_do_not_create_parent(database_path):
    store = repository()

    assert store.list_trips(database_path) == []
    assert store.get_trip(database_path, 1) is None
    assert not database_path.exists()
    assert not database_path.parent.exists()


def test_import_does_not_create_database(tmp_path, monkeypatch):
    store = repository()
    connect_calls = []

    def forbidden_connect(*args, **kwargs):
        connect_calls.append((args, kwargs))
        raise AssertionError("Importing the repository must not connect to storage.")

    monkeypatch.setattr(store.sqlite3, "connect", forbidden_connect)
    monkeypatch.chdir(tmp_path)
    # Execute a separate module namespace, never reload the shared module that
    # Flask may already reference (which would replace its exception classes).
    module_spec = importlib.util.spec_from_file_location("phase6_saved_trips_import_probe", store.__file__)
    isolated_module = importlib.util.module_from_spec(module_spec)
    monkeypatch.setitem(sys.modules, module_spec.name, isolated_module)
    module_spec.loader.exec_module(isolated_module)

    assert connect_calls == []
    assert list(tmp_path.iterdir()) == []


def test_first_save_creates_only_the_requested_row_and_versioned_schema(
    database_path, snapshot_payload
):
    store = repository()
    before = datetime.now(timezone.utc) - timedelta(seconds=1)

    record, created = store.save_trip(database_path, "Paris weekend", snapshot_payload)

    after = datetime.now(timezone.utc) + timedelta(seconds=1)
    assert created is True
    assert type(record["id"]) is int and record["id"] > 0
    assert record["title"] == "Paris weekend"
    assert record["available"] is True
    assert before <= utc(record["created_at"]) <= after
    assert database_path.is_file()
    with closing(sqlite3.connect(database_path)) as connection, connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        columns = {row[1]: row[2].upper() for row in connection.execute("PRAGMA table_info(saved_trips)")}
        assert columns["id"] == "INTEGER"
        for name in ("title", "created_at", "fingerprint", "snapshot_json"):
            assert columns[name] == "TEXT"
        assert connection.execute("SELECT COUNT(*) FROM saved_trips").fetchone()[0] == 1
    assert store.get_trip(database_path, record["id"]) == record
    assert store.list_trips(database_path) == [record]


def test_database_json_keeps_every_money_value_as_two_decimal_text(
    database_path, snapshot_payload
):
    store = repository()
    record, _ = store.save_trip(database_path, "Exact estimate", snapshot_payload)

    with closing(sqlite3.connect(database_path)) as connection, connection:
        row = connection.execute(
            "SELECT typeof(id), typeof(title), typeof(created_at), "
            "typeof(fingerprint), typeof(snapshot_json), snapshot_json FROM saved_trips"
        ).fetchone()
    assert row[:5] == ("integer", "text", "text", "text", "text")
    raw = json.loads(row[5])
    assert raw == snapshot_payload
    assert all(isinstance(value, str) and re.fullmatch(r"[0-9]+\.[0-9]{2}", value)
               for value in every_money_value(raw))
    assert all(isinstance(value, Decimal) for value in every_money_value(record["snapshot"]))
    assert record["snapshot"]["itinerary"]["estimated_cost"] == Decimal("103.00")
    assert record["snapshot"]["itinerary"]["unallocated_allowance"] == Decimal("197.00")
    assert len(record["snapshot"]["recommendations"]) == 7
    assert record["snapshot"]["itinerary"]["filled_slots"] == 6


def test_saved_inputs_and_loaded_records_are_independent_copies(database_path, snapshot_payload):
    store = repository()
    original = deepcopy(snapshot_payload)
    record, _ = store.save_trip(database_path, "Original", snapshot_payload)

    assert snapshot_payload == original
    snapshot_payload["recommendations"][0]["place"]["name"] = "Input mutation"
    record["snapshot"]["recommendations"][0]["place"]["name"] = "Returned mutation"
    loaded = store.get_trip(database_path, record["id"])
    assert loaded["snapshot"]["recommendations"][0]["place"]["name"] == original["recommendations"][0]["place"]["name"]


def test_identical_save_reuses_original_id_creation_time_and_complete_row(
    database_path, snapshot_payload
):
    store = repository()
    first_time = datetime(2026, 1, 2, 12, 30, tzinfo=timezone.utc)
    later = first_time + timedelta(days=4)
    first, created_first = store.save_trip(
        database_path, "Paris weekend", snapshot_payload, created_at=first_time
    )
    original_rows = read_rows(database_path)

    second, created_second = store.save_trip(
        database_path, "Paris weekend", deepcopy(snapshot_payload), created_at=later
    )

    assert created_first is True
    assert created_second is False
    assert second == first
    assert utc(second["created_at"]) == first_time
    assert read_rows(database_path) == original_rows


def test_title_normalization_is_part_of_duplicate_equality(database_path, snapshot_payload):
    store = repository()
    first, _ = store.save_trip(database_path, "  Paris weekend  ", snapshot_payload)
    second, created = store.save_trip(database_path, "Paris weekend", snapshot_payload)

    assert first["title"] == "Paris weekend"
    assert second == first
    assert created is False
    assert len(read_rows(database_path)) == 1


def test_canonical_key_order_and_decoded_money_do_not_create_duplicates(
    database_path, snapshot_payload
):
    store = repository()
    first, _ = store.save_trip(database_path, "Paris", snapshot_payload)
    reordered = {key: snapshot_payload[key] for key in reversed(snapshot_payload)}

    second, created_second = store.save_trip(database_path, "Paris", reordered)
    third, created_third = store.save_trip(database_path, "Paris", first["snapshot"])

    assert second["id"] == third["id"] == first["id"]
    assert created_second is created_third is False
    assert len(read_rows(database_path)) == 1


@pytest.mark.parametrize("second_title", ["Another name", "paris", "Paris!"])
def test_different_literal_titles_create_distinct_rows_without_overwriting(
    database_path, snapshot_payload, second_title
):
    store = repository()
    first, _ = store.save_trip(database_path, "Paris", snapshot_payload)
    original_row = read_rows(database_path)[0]

    second, created = store.save_trip(database_path, second_title, snapshot_payload)

    assert created is True
    assert first["id"] != second["id"]
    assert read_rows(database_path)[0] == original_row
    assert len(store.list_trips(database_path)) == 2


def test_changed_full_snapshot_creates_a_separate_version(
    database_path, snapshot_payload, snapshot_factory, normalized_preferences
):
    store = repository()
    first, _ = store.save_trip(database_path, "Paris", snapshot_payload)
    first_row = read_rows(database_path)[0]
    changed = snapshot_factory({**normalized_preferences, "budget": Decimal("301.00")})
    assert changed["itinerary"]["estimated_cost"] == "103.00"
    assert changed != snapshot_payload

    second, created = store.save_trip(database_path, "Paris", changed)

    assert created is True
    assert second["id"] != first["id"]
    assert read_rows(database_path)[0] == first_row
    assert second["snapshot"]["preferences"]["budget"] == Decimal("301.00")
    assert store.get_trip(database_path, first["id"])["snapshot"]["preferences"]["budget"] == Decimal("300.00")


def test_duplicate_fingerprint_is_hash_of_title_and_complete_canonical_snapshot(
    database_path, snapshot_payload
):
    store = repository()
    store.save_trip(database_path, "Paris été", snapshot_payload)
    row = read_rows(database_path)[0]

    expected = hashlib.sha256(
        canonical({"title": "Paris été", "snapshot": snapshot_payload}).encode("utf-8")
    ).hexdigest()
    assert row[3] == expected
    assert re.fullmatch(r"[0-9a-f]{64}", row[3])
    with closing(sqlite3.connect(database_path)) as connection, connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO saved_trips (title, created_at, fingerprint, snapshot_json) "
                "VALUES (?, ?, ?, ?)",
                ("Different text", row[2], row[3], row[4]),
            )


@pytest.mark.parametrize("title", [
    "L'été à Paris — 京都",
    "Robert'); DROP TABLE saved_trips;--",
    '<script>alert("trip")</script>',
    "x" * 80,
])
def test_unicode_sql_and_html_names_are_stored_as_literal_values(
    database_path, snapshot_payload, title
):
    store = repository()
    record, _ = store.save_trip(database_path, title, snapshot_payload)
    later, _ = store.save_trip(database_path, "The table still works", snapshot_payload)

    assert record["title"] == title
    assert store.get_trip(database_path, record["id"])["title"] == title
    assert later["id"] != record["id"]
    assert len(read_rows(database_path)) == 2


def test_newest_first_uses_creation_time_then_descending_id(database_path, snapshot_payload):
    store = repository()
    early = datetime(2026, 2, 1, 8, tzinfo=timezone.utc)
    later = early + timedelta(hours=1)
    newest_first_id, _ = store.save_trip(database_path, "Later first", snapshot_payload, created_at=later)
    oldest, _ = store.save_trip(database_path, "Earlier but inserted second", snapshot_payload, created_at=early)
    newest_second_id, _ = store.save_trip(database_path, "Later second", snapshot_payload, created_at=later)

    ordered = store.list_trips(database_path)

    assert [record["id"] for record in ordered] == [newest_second_id["id"], newest_first_id["id"], oldest["id"]]
    assert utc(ordered[0]["created_at"]) == utc(ordered[1]["created_at"]) == later


def test_closed_database_can_be_reopened_through_fresh_connections(database_path, snapshot_payload):
    store = repository()
    original, _ = store.save_trip(database_path, "Persistent trip", snapshot_payload)

    # This independent connection sees durable data, not a pending transaction.
    # Fresh Flask app/secret persistence is covered by the route integration test.
    assert read_rows(database_path)[0][0] == original["id"]
    assert store.get_trip(database_path, original["id"]) == original
    assert store.list_trips(database_path) == [original]
    assert store.get_trip(database_path, original["id"] + 999) is None


@pytest.mark.parametrize(
    ("budget", "interests", "days", "filled", "scheduled", "remaining"),
    [
        ("60.00", ["food", "history"], 3, 3, "0.00", "60.00"),
        ("1.00", ["food"], 14, 0, "0.00", "1.00"),
        ("100.01", ["food", "history"], 3, 6, "85.00", "15.01"),
    ],
)
def test_partial_empty_and_exact_cent_snapshots_survive_reopening(
    database_path, snapshot_factory, normalized_preferences,
    budget, interests, days, filled, scheduled, remaining,
):
    store = repository()
    payload = snapshot_factory({
        **normalized_preferences, "budget": Decimal(budget),
        "interests": interests, "days": days,
    })
    assert payload["itinerary"]["filled_slots"] == filled
    record, _ = store.save_trip(database_path, "Boundary sample", payload)

    loaded = store.get_trip(database_path, record["id"])["snapshot"]

    assert loaded["itinerary"]["filled_slots"] == filled
    assert loaded["itinerary"]["total_slots"] == days * 2
    assert loaded["itinerary"]["estimated_cost"] == Decimal(scheduled)
    assert loaded["itinerary"]["unallocated_allowance"] == Decimal(remaining)
    assert loaded["itinerary"]["notices"] == payload["itinerary"]["notices"]
    assert len(loaded["itinerary"]["days"]) == days


@pytest.mark.parametrize("start_with_existing", [False, True])
def test_equivalent_concurrent_saves_use_separate_connections_and_one_unique_row(
    database_path, snapshot_payload, start_with_existing
):
    store = repository()
    original = None
    if start_with_existing:
        original, _ = store.save_trip(database_path, "Concurrent trip", snapshot_payload)
    rendezvous = Barrier(2)

    def save(index):
        # Wait before opening a repository transaction, never while holding a lock.
        rendezvous.wait(timeout=10)
        return store.save_trip(
            database_path, "Concurrent trip", deepcopy(snapshot_payload),
            created_at=datetime(2026, 3, index + 1, tzinfo=timezone.utc), timeout=5.0,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, (0, 1)))

    records = [record for record, _ in results]
    assert records[0] == records[1]
    assert sum(created for _, created in results) == (0 if start_with_existing else 1)
    assert len(read_rows(database_path)) == 1
    if original is not None:
        assert records == [original, original]


def test_second_writer_cannot_reject_the_first_writers_new_uninitialized_file(
    database_path, snapshot_payload, monkeypatch,
):
    """Force the interleaving that the ordinary concurrent test may not hit."""
    store = repository()
    real_connect = store.sqlite3.connect
    file_opened = Event()
    release_first = Event()
    first_thread = []

    def delayed_connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        if current_thread().ident == first_thread[0] and not file_opened.is_set():
            # SQLite created the file, but this writer has not begun its SQL
            # transaction. A second writer must not treat it as broken storage.
            file_opened.set()
            if not release_first.wait(timeout=5):
                connection.close()
                raise AssertionError("The test must release its paused writer.")
        return connection

    def save_first():
        first_thread.append(current_thread().ident)
        return store.save_trip(database_path, "First-save race", snapshot_payload)

    monkeypatch.setattr(store.sqlite3, "connect", delayed_connect)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(save_first)
        try:
            assert file_opened.wait(timeout=5)
            second = pool.submit(store.save_trip, database_path, "First-save race", snapshot_payload)
            try:
                second.result(timeout=0.5)
            except (TimeoutError, store.StorageUnavailableError):
                # Correct code may wait for the first writer. The broken case
                # finishes with an error; the final result assertion exposes it.
                pass
        finally:
            release_first.set()
        first_result, second_result = first.result(timeout=5), second.result(timeout=5)
    assert first_result[0] == second_result[0]
    assert sum(created for _, created in (first_result, second_result)) == 1
    assert len(read_rows(database_path)) == 1


@pytest.mark.parametrize("damage", ["invalid-json", "unsupported-version", "money", "unsafe-url"])
def test_bad_row_is_unavailable_without_breaking_or_rewriting_other_records(
    database_path, snapshot_payload, damage
):
    store = repository()
    good, _ = store.save_trip(database_path, "Readable", snapshot_payload)
    bad, _ = store.save_trip(database_path, "Damaged", snapshot_payload)

    def corrupt(raw):
        if damage == "invalid-json":
            return "{broken"
        payload = json.loads(raw)
        if damage == "unsupported-version":
            payload["version"] = 99
        elif damage == "money":
            payload["preferences"]["budget"] = "NaN"
        else:
            payload["recommendations"][0]["place"]["source_url"] = "javascript:alert(1)"
        return canonical(payload)

    corrupted = change_raw_snapshot(database_path, bad["id"], corrupt)
    before = read_rows(database_path)

    records = {record["id"]: record for record in store.list_trips(database_path)}

    assert records[good["id"]] == good
    assert records[bad["id"]]["available"] is False
    assert records[bad["id"]]["snapshot"] is None
    assert store.get_trip(database_path, bad["id"])["available"] is False
    assert store.get_trip(database_path, good["id"]) == good
    assert read_rows(database_path) == before
    assert next(row[4] for row in before if row[0] == bad["id"]) == corrupted


def test_damaged_duplicate_raises_record_level_error_not_false_save_success(
    database_path, snapshot_payload
):
    store = repository()
    original, _ = store.save_trip(database_path, "Damaged duplicate", snapshot_payload)
    change_raw_snapshot(database_path, original["id"], lambda raw: "{broken")
    before = read_rows(database_path)

    with pytest.raises(store.SavedTripUnavailableError) as failure:
        store.save_trip(database_path, "Damaged duplicate", snapshot_payload)

    assert failure.value.trip_id == original["id"]
    assert not isinstance(failure.value, store.StorageUnavailableError)
    assert read_rows(database_path) == before
    assert store.get_trip(database_path, original["id"])["available"] is False


@pytest.mark.parametrize("bad_field", ["title", "created_at"])
def test_invalid_row_metadata_has_safe_unavailable_fallback_without_rewriting(
    database_path, snapshot_payload, bad_field
):
    store = repository()
    record, _ = store.save_trip(database_path, "Original", snapshot_payload)
    # The column identifier comes from the fixed parameterization, not user input.
    statement = {
        "title": "UPDATE saved_trips SET title = ? WHERE id = ?",
        "created_at": "UPDATE saved_trips SET created_at = ? WHERE id = ?",
    }[bad_field]
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(statement, ("\x00damaged", record["id"]))
    before = read_rows(database_path)

    loaded = store.get_trip(database_path, record["id"])
    listed = store.list_trips(database_path)

    assert loaded["id"] == record["id"]
    assert loaded["available"] is False
    assert loaded["snapshot"] is None
    assert isinstance(loaded["title"], str) and loaded["title"].strip()
    assert "\x00" not in loaded["title"]
    assert loaded["created_at"] is None or "\x00" not in loaded["created_at"]
    assert listed == [loaded]
    assert read_rows(database_path) == before


@pytest.mark.parametrize("operation", ["list", "get", "save"])
@pytest.mark.parametrize("damage", ["unsupported-version", "wrong-schema", "corrupt-bytes"])
def test_incompatible_or_corrupt_database_is_preserved_not_reinitialized(
    tmp_path, snapshot_payload, operation, damage
):
    store = repository()
    path = tmp_path / "existing.sqlite3"
    if damage == "corrupt-bytes":
        path.write_bytes(b"This is an existing non-SQLite file. Do not replace me.\x00")
    else:
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute("CREATE TABLE important_existing_data (note TEXT)")
            connection.execute("INSERT INTO important_existing_data VALUES (?)", ("Keep this",))
            connection.execute("PRAGMA user_version = 99" if damage == "unsupported-version" else "PRAGMA user_version = 1")
            if damage == "wrong-schema":
                connection.execute("CREATE TABLE saved_trips (id INTEGER PRIMARY KEY, unexpected TEXT)")
    original = path.read_bytes()

    with pytest.raises(store.StorageUnavailableError):
        if operation == "list":
            store.list_trips(path)
        elif operation == "get":
            store.get_trip(path, 1)
        else:
            store.save_trip(path, "Must not replace storage", snapshot_payload)

    assert path.read_bytes() == original


def test_invalid_parent_path_returns_storage_error_and_preserves_existing_file(
    tmp_path, snapshot_payload
):
    store = repository()
    parent_file = tmp_path / "not-a-directory"
    original = b"Keep the existing file"
    parent_file.write_bytes(original)
    path = parent_file / "trips.sqlite3"

    with pytest.raises(store.StorageUnavailableError):
        store.save_trip(path, "Cannot create here", snapshot_payload)

    assert parent_file.read_bytes() == original


def test_unrelated_integrity_failure_is_not_reported_as_duplicate_success(
    database_path, snapshot_payload
):
    store = repository()
    original, _ = store.save_trip(database_path, "Existing", snapshot_payload)
    before = read_rows(database_path)
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(
            "CREATE TRIGGER reject_new_saved_trip BEFORE INSERT ON saved_trips "
            "BEGIN SELECT RAISE(ABORT, 'test-only unrelated integrity failure'); END"
        )

    with pytest.raises(store.StorageUnavailableError):
        store.save_trip(database_path, "Not a duplicate", snapshot_payload)

    assert read_rows(database_path) == before
    assert store.get_trip(database_path, original["id"]) == original


@pytest.mark.parametrize("operation", ["list", "get", "save"])
def test_real_exclusive_lock_becomes_storage_error_and_preserves_existing_rows(
    database_path, snapshot_payload, operation
):
    store = repository()
    original, _ = store.save_trip(database_path, "Existing", snapshot_payload)
    before = read_rows(database_path)
    holder = sqlite3.connect(database_path, timeout=0.05)
    try:
        holder.execute("BEGIN EXCLUSIVE")
        with pytest.raises(store.StorageUnavailableError):
            if operation == "list":
                store.list_trips(database_path, timeout=0.01)
            elif operation == "get":
                store.get_trip(database_path, original["id"], timeout=0.01)
            else:
                store.save_trip(database_path, "Blocked", snapshot_payload, timeout=0.01)
    finally:
        holder.rollback()
        holder.close()

    assert read_rows(database_path) == before
    assert store.get_trip(database_path, original["id"]) == original


class TrackingCursor:
    def __init__(self, cursor, owner):
        self.cursor = cursor
        self.owner = owner

    def execute(self, statement, *args, **kwargs):
        self.owner.observe(statement)
        self.cursor.execute(statement, *args, **kwargs)
        self.owner.record_write(statement)
        return self

    def executemany(self, statement, *args, **kwargs):
        self.owner.observe(statement)
        self.cursor.executemany(statement, *args, **kwargs)
        self.owner.record_write(statement)
        return self

    def __iter__(self):
        return iter(self.cursor)

    def __getattr__(self, name):
        return getattr(self.cursor, name)


class TrackingConnection:
    """Delegate real SQL, optionally fault actual commit or saved-row reads."""

    def __init__(self, connection, *, fail_commit=False, fail_read=False):
        self.connection = connection
        self.fail_commit = fail_commit
        self.fail_read = fail_read
        self.inserted = False
        self.commit_attempted = False
        self.rolled_back = False
        self.closed = False

    def observe(self, statement):
        upper = statement.upper()
        if upper.strip().rstrip(";") in {"COMMIT", "END", "END TRANSACTION", "COMMIT TRANSACTION"}:
            self.commit_attempted = True
            if self.fail_commit and self.inserted:
                raise sqlite3.OperationalError("test-only commit failure after actual insert")
        if upper.strip().startswith("ROLLBACK"):
            self.rolled_back = True
        if self.fail_read and "SELECT" in upper and "SAVED_TRIPS" in upper:
            raise sqlite3.OperationalError("test-only saved row read failure")

    def record_write(self, statement):
        upper = statement.upper()
        if "INSERT" in upper and "SAVED_TRIPS" in upper:
            self.inserted = True

    def execute(self, statement, *args, **kwargs):
        self.observe(statement)
        result = self.connection.execute(statement, *args, **kwargs)
        self.record_write(statement)
        return result

    def executemany(self, statement, *args, **kwargs):
        self.observe(statement)
        result = self.connection.executemany(statement, *args, **kwargs)
        self.record_write(statement)
        return result

    def cursor(self, *args, **kwargs):
        return TrackingCursor(self.connection.cursor(*args, **kwargs), self)

    def commit(self):
        self.commit_attempted = True
        if self.fail_commit and self.inserted:
            raise sqlite3.OperationalError("test-only commit failure after actual insert")
        return self.connection.commit()

    def rollback(self):
        self.rolled_back = True
        return self.connection.rollback()

    def close(self):
        self.closed = True
        return self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        if exception_type is None:
            try:
                self.commit()
            except BaseException:
                # Match sqlite3.Connection: a failed context-manager commit
                # rolls back before propagating its error to the repository.
                self.rollback()
                raise
        else:
            self.rollback()
        return False

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def __setattr__(self, name, value):
        if name in {"row_factory", "isolation_level", "text_factory"}:
            setattr(self.connection, name, value)
        else:
            object.__setattr__(self, name, value)


@pytest.mark.parametrize("operation", ["list", "get", "save"])
def test_connection_close_failure_is_a_storage_error_not_a_raw_sqlite_exception(
    database_path, snapshot_payload, monkeypatch, operation,
):
    store = repository()
    original, _ = store.save_trip(database_path, "Already durable", snapshot_payload)
    real_connect = store.sqlite3.connect

    class CloseFault(TrackingConnection):
        def close(self):
            super().close()
            raise sqlite3.OperationalError("test-only private connection-close details")

    def connect(*args, **kwargs):
        return CloseFault(real_connect(*args, **kwargs))

    monkeypatch.setattr(store.sqlite3, "connect", connect)
    with pytest.raises(store.StorageUnavailableError):
        if operation == "list":
            store.list_trips(database_path)
        elif operation == "get":
            store.get_trip(database_path, original["id"])
        else:
            store.save_trip(database_path, "May already be committed", snapshot_payload)


def test_read_only_sqlite_uri_rejects_save_without_modifying_previous_rows(
    database_path, snapshot_payload, monkeypatch
):
    store = repository()
    original, _ = store.save_trip(database_path, "Existing", snapshot_payload)
    before = read_rows(database_path)
    real_connect = sqlite3.connect
    opened = []

    def readonly_connect(*args, **kwargs):
        kwargs["uri"] = True
        connection = TrackingConnection(real_connect(database_path.as_uri() + "?mode=ro", **kwargs))
        opened.append(connection)
        return connection

    with monkeypatch.context() as patch:
        patch.setattr(store.sqlite3, "connect", readonly_connect)
        with pytest.raises(store.StorageUnavailableError):
            store.save_trip(database_path, "Cannot write", snapshot_payload)

    assert opened and all(connection.closed for connection in opened)
    assert read_rows(database_path) == before
    assert store.get_trip(database_path, original["id"]) == original


def test_commit_failure_after_real_insert_rolls_back_before_reporting_failure(
    database_path, snapshot_payload, monkeypatch
):
    store = repository()
    original, _ = store.save_trip(database_path, "Existing", snapshot_payload)
    before = read_rows(database_path)
    real_connect = sqlite3.connect
    opened = []

    def failing_connect(*args, **kwargs):
        connection = TrackingConnection(real_connect(*args, **kwargs), fail_commit=True)
        opened.append(connection)
        return connection

    with monkeypatch.context() as patch:
        patch.setattr(store.sqlite3, "connect", failing_connect)
        with pytest.raises(store.StorageUnavailableError):
            store.save_trip(database_path, "Must not survive failed commit", snapshot_payload)

    assert any(connection.inserted and connection.commit_attempted for connection in opened)
    assert any(connection.rolled_back for connection in opened)
    assert all(connection.closed for connection in opened)
    # A new independent real connection, not the failed transaction, proves rollback.
    assert read_rows(database_path) == before
    assert store.get_trip(database_path, original["id"]) == original
    recovered, created = store.save_trip(database_path, "After recovery", snapshot_payload)
    assert created is True
    assert recovered["id"] != original["id"]


@pytest.mark.parametrize("operation", ["list", "get"])
def test_failed_row_reads_are_storage_errors_and_close_connections(
    database_path, snapshot_payload, monkeypatch, operation
):
    store = repository()
    original, _ = store.save_trip(database_path, "Existing", snapshot_payload)
    before = read_rows(database_path)
    real_connect = sqlite3.connect
    opened = []

    def failing_connect(*args, **kwargs):
        connection = TrackingConnection(real_connect(*args, **kwargs), fail_read=True)
        opened.append(connection)
        return connection

    with monkeypatch.context() as patch:
        patch.setattr(store.sqlite3, "connect", failing_connect)
        with pytest.raises(store.StorageUnavailableError):
            if operation == "list":
                store.list_trips(database_path)
            else:
                store.get_trip(database_path, original["id"])

    assert opened and all(connection.closed for connection in opened)
    assert read_rows(database_path) == before


def test_successful_save_list_detail_and_duplicate_close_each_connection(
    database_path, snapshot_payload, monkeypatch
):
    store = repository()
    real_connect = sqlite3.connect
    opened = []

    def tracking_connect(*args, **kwargs):
        connection = TrackingConnection(real_connect(*args, **kwargs))
        opened.append(connection)
        return connection

    with monkeypatch.context() as patch:
        patch.setattr(store.sqlite3, "connect", tracking_connect)
        record, _ = store.save_trip(database_path, "Closed resources", snapshot_payload)
        assert opened and all(connection.closed for connection in opened)
        assert store.list_trips(database_path) == [record]
        assert all(connection.closed for connection in opened)
        assert store.get_trip(database_path, record["id"]) == record
        assert all(connection.closed for connection in opened)
        duplicate, created = store.save_trip(database_path, "Closed resources", snapshot_payload)
        assert duplicate == record and created is False

    assert len(opened) >= 4
    assert all(connection.closed for connection in opened)
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError):
            connection.connection.execute("SELECT 1")


@pytest.mark.parametrize("bad_name", ["x" * 81, "\tParis", "Paris\n", "\x00Paris"])
def test_invalid_title_is_rejected_before_storage_is_initialized(
    database_path, snapshot_payload, monkeypatch, bad_name
):
    store = repository()

    def forbidden_connect(*args, **kwargs):
        raise AssertionError("Input validation must precede database access.")

    monkeypatch.setattr(store.sqlite3, "connect", forbidden_connect)
    with pytest.raises(ValueError):
        store.save_trip(database_path, bad_name, snapshot_payload)

    assert not database_path.parent.exists()


def test_invalid_payload_is_rejected_before_storage_is_initialized(
    database_path, snapshot_payload, monkeypatch
):
    store = repository()
    snapshots = importlib.import_module("snapshots")
    payload = deepcopy(snapshot_payload)
    payload["itinerary"]["estimated_cost"] = "999.00"

    def forbidden_connect(*args, **kwargs):
        raise AssertionError("Snapshot validation must precede database access.")

    monkeypatch.setattr(store.sqlite3, "connect", forbidden_connect)
    with pytest.raises(snapshots.SnapshotValidationError):
        store.save_trip(database_path, "Invalid snapshot", payload)

    assert not database_path.parent.exists()

"""Free-demo SDD contracts. Integration requires an actual disposable Postgres.

Never read production DATABASE_URL. Only an explicitly named loopback test
administrator DB can create fresh random databases used by these tests.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from decimal import Decimal
import importlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import uuid

import pytest


OWNER_A, OWNER_B = "a" * 64, "b" * 64
SCHEMA = "tripplanner_hosted_v1"
EXAMPLE_URL = "postgresql://demo:private-test-password@ep-example.eu-central-1.aws.neon.tech/neondb?sslmode=verify-full"


def repository():
    return importlib.import_module("hosted_postgres")


@pytest.fixture
def postgres_dsn():
    raw = os.environ.get("TRIPPLANNER_TEST_POSTGRES_DSN")
    if not raw:
        pytest.skip("Real PostgreSQL requires an explicit disposable loopback test DSN.")
    parts = urlsplit(raw)
    if parts.hostname not in {"127.0.0.1", "localhost"} or parts.path != "/tripplanner_test_admin":
        pytest.fail("Refusing PostgreSQL tests outside the named disposable loopback administrator database.")
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    name = "tripplanner_test_" + uuid.uuid4().hex
    with psycopg.connect(raw, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        yield make_conninfo(raw, dbname=name)
    finally:
        # Only the exact random database created by this fixture is removed.
        assert name.startswith("tripplanner_test_") and len(name) == 49
        with psycopg.connect(raw, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def payload():
    from catalog import load_catalog
    from snapshots import build_snapshot
    return build_snapshot({"destination": "Paris, France", "days": 3, "budget": Decimal("300.00"),
                           "currency": "EUR", "interests": ["food", "history"],
                           "pace": "relaxed", "family_friendly": True}, load_catalog())


def remote_settings():
    return {"TRIPPLANNER_SECRET_KEY": "ab" * 32, "TRIPPLANNER_PUBLIC_HOST": "planner.example",
            "TRIPPLANNER_STORAGE_BACKEND": "postgres", "TRIPPLANNER_DATABASE_URL": EXAMPLE_URL}


def sql_rows(dsn, query, args=()):
    import psycopg
    with psycopg.connect(dsn) as connection:
        return connection.execute(query, args).fetchall()


def test_valid_remote_config_selects_postgres_without_disk(monkeypatch):
    repo = repository()
    initialized = []
    monkeypatch.setattr(repo, "initialize_store", lambda dsn, **kwargs: initialized.append(dsn))
    from hosted import create_hosted_app
    application = create_hosted_app(remote_settings())
    assert application.config["HOSTED_STORAGE_BACKEND"] == "postgres"
    assert application.config["DATABASE"] == EXAMPLE_URL
    assert application.config["HOSTED_FREE_DEMO"] is True
    assert initialized == [EXAMPLE_URL]


@pytest.mark.parametrize("url", ["", "sqlite:///temp.db", "http://example.com/db",
    "postgresql://user:pass@example.com/db", "postgresql://user:pass@example.com/db?sslmode=disable",
    "postgresql://user:pass@example.com/db?sslmode=require", "postgresql://user@example.com/db?sslmode=verify-full",
    "postgresql://user:pass@/db?sslmode=verify-full", "postgresql://user:pass@example.com/?sslmode=verify-full",
    "postgresql://user:pass@example.com/db?sslmode=verify-full&sslmode=disable",
    "postgresql://user:pass@example.com/db?sslmode=verify-full&options=-csearch_path%3Dpublic",
    "postgresql://user:pass@example.com/db?sslmode=verify-full#fragment"])
def test_invalid_or_insecure_remote_settings_fail_before_connection(monkeypatch, url):
    repo = repository()
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid settings must be rejected before connecting.")
    monkeypatch.setattr(repo, "initialize_store", forbidden)
    from hosted import create_hosted_app
    settings = remote_settings()
    settings["TRIPPLANNER_DATABASE_URL"] = url
    with pytest.raises(ValueError) as error:
        create_hosted_app(settings)
    assert "pass@" not in str(error.value)


def test_ambiguous_or_unknown_backend_rejected_before_storage(monkeypatch, tmp_path):
    repo = repository()
    monkeypatch.setattr(repo, "initialize_store", lambda *a, **k: pytest.fail("Do not connect ambiguous configuration."))
    from hosted import create_hosted_app
    settings = remote_settings()
    settings["TRIPPLANNER_STORAGE_DIR"] = str(tmp_path)
    with pytest.raises(ValueError):
        create_hosted_app(settings)
    settings.pop("TRIPPLANNER_STORAGE_DIR")
    settings["TRIPPLANNER_STORAGE_BACKEND"] = "memory"
    with pytest.raises(ValueError):
        create_hosted_app(settings)


def test_remote_failure_never_falls_back_to_sqlite(monkeypatch, tmp_path):
    repo = repository()
    from saved_trips import StorageUnavailableError
    from hosted import create_hosted_app
    def unavailable(*args, **kwargs):
        raise StorageUnavailableError("Saved trips are temporarily unavailable.")
    monkeypatch.setattr(repo, "initialize_store", unavailable)
    with pytest.raises(StorageUnavailableError):
        create_hosted_app(remote_settings())
    assert not list(tmp_path.iterdir())


def test_real_repository_isolation_duplicates_and_exact_bytes(postgres_dsn, payload):
    repo = repository()
    from snapshots import dump_snapshot
    repo.initialize_store(postgres_dsn)
    first, created = repo.save_trip(postgres_dsn, "same", payload, owner=OWNER_A)
    assert created and first["available"]
    again, created = repo.save_trip(postgres_dsn, "same", payload, owner=OWNER_A)
    assert not created and again == first
    second, created = repo.save_trip(postgres_dsn, "same", payload, owner=OWNER_B)
    assert created and second["id"] != first["id"]
    assert repo.get_trip(postgres_dsn, first["id"], owner=OWNER_B) is None
    assert repo.list_trips(postgres_dsn, owner=OWNER_A) == [first]
    rows = sql_rows(postgres_dsn, f"SELECT fingerprint, snapshot_json FROM {SCHEMA}.saved_trips ORDER BY id")
    assert len(rows) == 2 and rows[0] == rows[1] and rows[0][1] == dump_snapshot(payload)
    repo.initialize_store(postgres_dsn)  # Process restart validates, never resets.
    assert repo.get_trip(postgres_dsn, first["id"], owner=OWNER_A) == first


def test_real_repository_supports_v1(postgres_dsn):
    payload = json.loads((Path(__file__).parent / "fixtures/phase7-paris-snapshot.json").read_text(encoding="utf-8"))
    from snapshots import dump_snapshot
    repo = repository()
    repo.initialize_store(postgres_dsn)
    record, _ = repo.save_trip(postgres_dsn, "Legacy", payload, owner=OWNER_A)
    assert record["available"] and record["snapshot"]["version"] == 1
    assert sql_rows(postgres_dsn, f"SELECT snapshot_json FROM {SCHEMA}.saved_trips")[0][0] == dump_snapshot(payload)


def test_real_concurrent_duplicate_saves(postgres_dsn, payload):
    repo = repository()
    repo.initialize_store(postgres_dsn)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: repo.save_trip(postgres_dsn, "same", payload, owner=OWNER_A), range(8)))
    assert sum(created for record, created in results) == 1
    assert len({record["id"] for record, created in results}) == 1


@pytest.mark.parametrize("owner", [None, "", "a", "x" * 64, "a" * 64 + "' OR 1=1 --"])
def test_owner_validation_before_network(owner):
    repo = repository()
    for function, args in [(repo.save_trip, ("not-a-connection", "title", {})),
                           (repo.list_trips, ("not-a-connection",)),
                           (repo.get_trip, ("not-a-connection", 1))]:
        with pytest.raises(ValueError):
            function(*args, owner=owner)


def test_quote_in_title_is_data_and_foreign_damage_is_private(postgres_dsn, payload):
    repo = repository()
    repo.initialize_store(postgres_dsn)
    title = "Paris'; DROP TABLE saved_trips; --"
    record, _ = repo.save_trip(postgres_dsn, title, payload, owner=OWNER_A)
    assert record["title"] == title
    sql_rows(postgres_dsn, f"UPDATE {SCHEMA}.saved_trips SET snapshot_json = 'broken' WHERE id = %s RETURNING id", (record["id"],))
    from saved_trips import SavedTripUnavailableError
    with pytest.raises(SavedTripUnavailableError):
        repo.save_trip(postgres_dsn, title, payload, owner=OWNER_A)
    second, created = repo.save_trip(postgres_dsn, title, payload, owner=OWNER_B)
    assert created and second["available"]
    assert repo.get_trip(postgres_dsn, record["id"], owner=OWNER_B) is None


def test_incompatible_namespace_refused_without_changes(postgres_dsn):
    import psycopg
    with psycopg.connect(postgres_dsn) as connection:
        connection.execute(f"CREATE SCHEMA {SCHEMA}")
        connection.execute(f"CREATE TABLE {SCHEMA}.keep_me (value TEXT)")
        connection.execute(f"INSERT INTO {SCHEMA}.keep_me VALUES ('preserve')")
    from saved_trips import StorageUnavailableError
    with pytest.raises(StorageUnavailableError):
        repository().initialize_store(postgres_dsn)
    assert sql_rows(postgres_dsn, f"SELECT value FROM {SCHEMA}.keep_me") == [("preserve",)]


def test_lost_schema_does_not_recreate_on_read_save_or_health(postgres_dsn, payload):
    import psycopg
    repo = repository()
    repo.initialize_store(postgres_dsn)
    with psycopg.connect(postgres_dsn) as connection:
        connection.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
    from saved_trips import StorageUnavailableError
    for function, args, kwargs in [
        (repo.check_store, (postgres_dsn,), {}),
        (repo.list_trips, (postgres_dsn,), {"owner": OWNER_A}),
        (repo.save_trip, (postgres_dsn, "same", payload), {"owner": OWNER_A}),
    ]:
        with pytest.raises(StorageUnavailableError):
            function(*args, **kwargs)
    assert sql_rows(postgres_dsn, "SELECT nspname FROM pg_namespace WHERE nspname = %s", (SCHEMA,)) == []


def test_write_lock_times_out_without_save(postgres_dsn, payload):
    import psycopg
    repo = repository()
    repo.initialize_store(postgres_dsn)
    from saved_trips import StorageUnavailableError
    with psycopg.connect(postgres_dsn) as lock:
        lock.execute(f"LOCK TABLE {SCHEMA}.saved_trips IN ACCESS EXCLUSIVE MODE")
        with pytest.raises(StorageUnavailableError):
            repo.save_trip(postgres_dsn, "same", payload, owner=OWNER_A, timeout=0.05)
    assert repo.list_trips(postgres_dsn, owner=OWNER_A) == []


def test_database_exception_redacts_connection_details(monkeypatch):
    repo = repository()
    import psycopg
    def fail(*args, **kwargs):
        raise psycopg.OperationalError(EXAMPLE_URL)
    monkeypatch.setattr(psycopg, "connect", fail)
    from saved_trips import StorageUnavailableError
    with pytest.raises(StorageUnavailableError) as error:
        repo.list_trips(EXAMPLE_URL, owner=OWNER_A)
    import traceback
    formatted = "".join(traceback.format_exception(error.value))
    assert EXAMPLE_URL not in formatted and "private-test-password" not in formatted


def test_real_database_flask_profiles_restart_and_free_notice(postgres_dsn, monkeypatch, parse_page, submit_trip):
    repo = repository()
    import psycopg
    original_connect = psycopg.connect
    # Only the network destination is replaced: SQL runs against actual PG.
    # Live Neon TLS/provider behavior remains external deployment acceptance.
    def connect(dsn, **kwargs):
        return original_connect(postgres_dsn if dsn == EXAMPLE_URL else dsn, **kwargs)
    monkeypatch.setattr(psycopg, "connect", connect)
    from hosted import create_hosted_app
    application = create_hosted_app(remote_settings())
    alice, bob = application.test_client(), application.test_client()
    assert b"Free demo" in alice.get("/").data
    assert "free" in alice.get("/about").text.lower()
    assert "365" in alice.get("/trips").text
    def save(browser):
        assert submit_trip(browser).status_code == 303
        page = parse_page(browser.get("/itinerary"))
        return browser.post("/itinerary/save", data={"trip_name": "Same trip",
            "csrf_token": page.find("input", name="csrf_token").attrs["value"],
            "snapshot_fingerprint": page.find("input", name="snapshot_fingerprint").attrs["value"]})
    first = save(alice)
    assert first.status_code == 303
    assert bob.get(first.location).status_code == 404
    second = save(bob)
    assert second.status_code == 303 and second.location != first.location
    cookie = alice.get_cookie("__Host-tripplanner_visitor", domain="planner.example").value
    before = sql_rows(postgres_dsn, f"SELECT * FROM {SCHEMA}.saved_trips ORDER BY id")
    restarted = create_hosted_app(remote_settings()).test_client()
    restarted.set_cookie("__Host-tripplanner_visitor", cookie, domain="planner.example")
    assert restarted.get(first.location).status_code == 200
    assert sql_rows(postgres_dsn, f"SELECT * FROM {SCHEMA}.saved_trips ORDER BY id") == before
    assert restarted.get("/healthz").json == {"status": "ok"}


def test_free_deploy_example_has_no_paid_disk_or_secret():
    path = Path(__file__).resolve().parents[1] / "hosting/render-free.yaml.example"
    assert path.exists(), "A free deployment must not use the prepared paid blueprint."
    text = path.read_text(encoding="utf-8")
    assert "plan: free" in text and "disk:" not in text
    assert "TRIPPLANNER_STORAGE_DIR" not in text and "TRIPPLANNER_DATABASE_URL" in text
    assert "TRIPPLANNER_STORAGE_BACKEND" in text and "postgres" in text
    assert EXAMPLE_URL not in text


def test_private_postgres_backup_and_real_disposable_restore(postgres_dsn, tmp_path):
    repo = repository()
    backup_tool = importlib.import_module("hosting.postgres_backup")
    bin_dir = os.environ.get("TRIPPLANNER_TEST_PG_BIN")
    if not bin_dir:
        pytest.skip("Actual pg_dump/pg_restore tools required for recovery verification.")
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    payload = json.loads((Path(__file__).parent / "fixtures/phase7-paris-snapshot.json").read_text(encoding="utf-8"))
    repo.initialize_store(postgres_dsn)
    record, _ = repo.save_trip(postgres_dsn, "Frozen", payload, owner=OWNER_A)
    destination = tmp_path / "private.dump"
    suffix = ".exe" if os.name == "nt" else ""
    backup_tool.backup_store(postgres_dsn, destination, pg_dump_path=Path(bin_dir) / ("pg_dump" + suffix))
    before = destination.read_bytes()
    assert before.startswith(b"PGDMP")
    with pytest.raises(FileExistsError):
        backup_tool.backup_store(postgres_dsn, destination, pg_dump_path=Path(bin_dir) / ("pg_dump" + suffix))
    assert destination.read_bytes() == before
    # The source already is a fresh per-test DB; create another fresh DB only.
    name = "tripplanner_test_restore_" + uuid.uuid4().hex
    source = conninfo_to_dict(postgres_dsn)
    admin_dsn = make_conninfo(postgres_dsn, dbname="tripplanner_test_admin")
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        restored = make_conninfo(postgres_dsn, dbname=name)
        import subprocess
        result = subprocess.run([str(Path(bin_dir) / ("pg_restore" + suffix)), "--exit-on-error", "--no-owner", "--no-acl", "--dbname", name, str(destination)],
            env=backup_tool.libpq_environment(restored), capture_output=True, timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        assert result.returncode == 0, "Disposable recovery failed."
        repo.initialize_store(restored)
        assert repo.get_trip(restored, record["id"], owner=OWNER_A) == record
        assert repo.get_trip(restored, record["id"], owner=OWNER_B) is None
        assert sql_rows(restored, f"SELECT * FROM {SCHEMA}.saved_trips") == sql_rows(postgres_dsn, f"SELECT * FROM {SCHEMA}.saved_trips")
    finally:
        assert name.startswith("tripplanner_test_restore_") and len(name) == 57
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def test_backup_does_not_put_database_credentials_in_command_or_error(tmp_path, monkeypatch):
    tool = importlib.import_module("hosting.postgres_backup")
    calls = []
    import subprocess
    def fail(arguments, **kwargs):
        calls.append((arguments, kwargs))
        return subprocess.CompletedProcess(arguments, 1, stderr=EXAMPLE_URL.encode())
    monkeypatch.setattr(subprocess, "run", fail)
    from saved_trips import StorageUnavailableError
    with pytest.raises(StorageUnavailableError) as error:
        tool.backup_store(EXAMPLE_URL, tmp_path / "failed.dump", pg_dump_path="pg_dump")
    assert "private-test-password" not in str(error.value)
    assert calls and all("private-test-password" not in str(arg) for arg in calls[0][0])
    assert calls[0][1]["env"]["PGPASSWORD"] == "private-test-password"

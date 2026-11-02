"""Phase 9 test-first public deployment contract; all storage is disposable.

Delayed imports let pytest collect tests before the implementation exists.
HTTPS here is Flask's simulated request scheme, not proof of public TLS.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from decimal import Decimal
import importlib
import json
from pathlib import Path
import sqlite3
import time

import pytest


ORIGIN = "https://planner.example"
OWNER_A = "a" * 64
OWNER_B = "b" * 64
VISITOR_COOKIE = "__Host-tripplanner_visitor"


def hosting():
    return importlib.import_module("hosted")


def repository():
    return importlib.import_module("hosted_saved_trips")


@pytest.fixture
def settings(tmp_path):
    directory = tmp_path / "durable"
    directory.mkdir()
    return {"TRIPPLANNER_SECRET_KEY": "a3" * 32,
            "TRIPPLANNER_STORAGE_DIR": str(directory),
            "TRIPPLANNER_PUBLIC_HOST": "planner.example"}


@pytest.fixture
def hosted_app(settings):
    class LazyApplication:
        application = None

        def __getattr__(self, name):
            if self.application is None:
                self.application = hosting().create_hosted_app(settings)
                self.application.config.update(TESTING=True, DATABASE_TIMEOUT=0.05)
            return getattr(self.application, name)

        def __setattr__(self, name, value):
            if name == "application":
                object.__setattr__(self, name, value)
            else:
                getattr(self, "config")  # Construct before forwarding mutations.
                setattr(self.application, name, value)
    return LazyApplication()


@pytest.fixture
def payload():
    from catalog import load_catalog
    from snapshots import build_snapshot
    return build_snapshot({"destination": "Paris, France", "days": 3,
                           "budget": Decimal("300.00"), "currency": "EUR",
                           "interests": ["food", "history"], "pace": "relaxed",
                           "family_friendly": True}, load_catalog())


def save_from_browser(browser, parse_page, submit_trip, title="Same trip"):
    assert submit_trip(browser).status_code == 303
    page = parse_page(browser.get("/itinerary"))
    data = {"trip_name": title}
    for name in ("csrf_token", "snapshot_fingerprint"):
        data[name] = page.find("input", name=name).attrs["value"]
    return browser.post("/itinerary/save", data=data)


@pytest.mark.parametrize("key", ["TRIPPLANNER_SECRET_KEY", "TRIPPLANNER_STORAGE_DIR", "TRIPPLANNER_PUBLIC_HOST"])
def test_missing_setting_fails_before_creating_database(settings, key):
    directory = Path(settings["TRIPPLANNER_STORAGE_DIR"])
    settings.pop(key)
    with pytest.raises(ValueError):
        hosting().create_hosted_app(settings)
    assert list(directory.iterdir()) == []


@pytest.mark.parametrize("secret", ["", "test", "x" * 64, "ab" * 31, " ab" * 32])
def test_weak_or_invalid_secret_rejected(settings, secret):
    settings["TRIPPLANNER_SECRET_KEY"] = secret
    with pytest.raises(ValueError):
        hosting().create_hosted_app(settings)
    assert not list(Path(settings["TRIPPLANNER_STORAGE_DIR"]).iterdir())


@pytest.mark.parametrize("host", ["", "*", ".example.com", "https://planner.example", "planner.example/path", "localhost", "127.0.0.1", "planner.example:443", "a\nb.example"])
def test_public_host_is_explicit_dns_name(settings, host):
    settings["TRIPPLANNER_PUBLIC_HOST"] = host
    with pytest.raises(ValueError):
        hosting().create_hosted_app(settings)


@pytest.mark.parametrize("kind", ["relative", "missing", "file", "checkout"])
def test_storage_directory_must_be_explicit_and_separate(settings, tmp_path, kind):
    if kind == "relative":
        directory = "data"
    elif kind == "missing":
        directory = str(tmp_path / "missing")
    elif kind == "file":
        target = tmp_path / "file"
        target.write_text("keep me")
        directory = str(target)
    else:
        directory = str(Path(__file__).resolve().parents[1])
    settings["TRIPPLANNER_STORAGE_DIR"] = directory
    with pytest.raises(ValueError):
        hosting().create_hosted_app(settings)


def test_production_flags_and_no_environment_mode_switch(hosted_app, monkeypatch, tmp_path):
    from app import create_app
    from app_runtime import make_desktop_app
    assert hosted_app.config["HOSTED_MODE"] is True
    assert hosted_app.debug is False
    assert hosted_app.config["SESSION_COOKIE_SECURE"] is True
    assert hosted_app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert hosted_app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert hosted_app.config["SESSION_COOKIE_NAME"].startswith("__Host-")
    monkeypatch.setenv("TRIPPLANNER_HOSTED", "1")
    monkeypatch.setenv("TRIPPLANNER_PUBLIC_HOST", "planner.example")
    local = create_app({"DATABASE": str(tmp_path / "local.sqlite3")})
    assert not local.config.get("HOSTED_MODE")
    native, _ = make_desktop_app(tmp_path / "native")
    assert not native.config.get("HOSTED_MODE")
    assert native.config["SESSION_COOKIE_SECURE"] is False
    assert native.config["DATABASE"] == str(tmp_path / "native" / "trips.sqlite3")


def test_secure_cookie_private_headers_and_host_checks(hosted_app):
    browser = hosted_app.test_client()
    response = browser.get("/plan")
    assert response.status_code == 200
    cookie = browser.get_cookie(VISITOR_COOKIE, domain="planner.example")
    assert cookie and cookie.secure and cookie.http_only and cookie.same_site == "Lax"
    assert cookie.max_age == 365 * 24 * 60 * 60
    assert cookie.path == "/" and cookie.origin_only
    assert response.headers["Cache-Control"] == "private, no-store"
    assert "Cookie" in response.vary
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert "max-age=" in response.headers["Strict-Transport-Security"]
    assert browser.get("/", base_url="https://attacker.example").status_code == 400
    assert browser.get("/", headers={"X-Forwarded-Host": "attacker.example"}).status_code == 200


def test_readiness_has_no_cookie_or_private_details_and_detects_lost_store(hosted_app):
    browser = hosted_app.test_client()
    result = browser.get("/healthz")
    assert result.status_code == 200 and result.json == {"status": "ok"}
    assert "Set-Cookie" not in result.headers
    database = Path(hosted_app.config["DATABASE"])
    database.rename(database.with_suffix(".unavailable"))
    result = browser.get("/healthz")
    assert result.status_code == 503 and result.json == {"status": "unavailable"}
    assert not database.exists(), "Never recreate a lost production collection."
    assert str(database) not in result.text
    assert browser.get("/trips").status_code == 503


def test_readiness_detects_write_lock(hosted_app):
    with closing(sqlite3.connect(hosted_app.config["DATABASE"])) as lock:
        lock.execute("BEGIN EXCLUSIVE")
        assert hosted_app.test_client().get("/healthz").status_code == 503
        lock.rollback()
    assert hosted_app.test_client().get("/healthz").status_code == 200


def test_separate_collections_scoped_duplicates_and_guessing(hosted_app, parse_page, submit_trip):
    alice, bob = hosted_app.test_client(), hosted_app.test_client()
    first = save_from_browser(alice, parse_page, submit_trip)
    assert first.status_code == 303
    alice_url = first.location
    assert alice.get(alice_url).status_code == 200
    foreign, absent = bob.get(alice_url), bob.get("/trips/999999")
    assert foreign.status_code == absent.status_code == 404
    assert foreign.data == absent.data
    assert b"Same trip" not in bob.get("/trips").data
    second = save_from_browser(bob, parse_page, submit_trip)
    assert second.status_code == 303 and second.location != alice_url
    assert b"Your trip has been saved." in bob.get(second.location).data
    again = save_from_browser(alice, parse_page, submit_trip)
    assert again.location == alice_url
    assert b"This trip is already saved." in alice.get(again.location).data
    assert alice.get(second.location).status_code == 404
    with closing(sqlite3.connect(hosted_app.config["DATABASE"])) as connection:
        rows = connection.execute("SELECT owner, fingerprint, snapshot_json FROM saved_trips ORDER BY id").fetchall()
    assert len(rows) == 2 and rows[0][0] != rows[1][0]
    assert rows[0][1:] == rows[1][1:], "Ownership must not alter reviewed snapshots/fingerprints."


def test_owner_query_and_form_fields_cannot_select_collection(hosted_app, parse_page, submit_trip):
    alice, bob = hosted_app.test_client(), hosted_app.test_client()
    saved = save_from_browser(alice, parse_page, submit_trip, "Alice hidden title")
    cookie = alice.get_cookie(VISITOR_COOKIE, domain="planner.example").value
    assert b"Alice hidden title" not in bob.get("/trips", query_string={"owner": OWNER_A, "visitor": cookie}).data
    assert submit_trip(bob).status_code == 303
    page = parse_page(bob.get("/itinerary"))
    data = {"trip_name": "Bob trip", "owner": OWNER_A, "visitor": cookie}
    for name in ("csrf_token", "snapshot_fingerprint"):
        data[name] = page.find("input", name=name).attrs["value"]
    bob_save = bob.post("/itinerary/save", data=data)
    assert bob_save.status_code == 303 and alice.get(bob_save.location).status_code == 404
    assert bob.get(saved.location).status_code == 404


@pytest.mark.parametrize("cookie_kind", ["tampered", "expired", "raw_owner", "wrong_secret"])
def test_invalid_identity_loses_access_safely(hosted_app, parse_page, submit_trip, monkeypatch, cookie_kind):
    browser = hosted_app.test_client()
    result = save_from_browser(browser, parse_page, submit_trip, "Hidden title")
    cookie = browser.get_cookie(VISITOR_COOKIE, domain="planner.example").value
    if cookie_kind == "expired":
        # itsdangerous timestamps use time.time; simulate more than one year later.
        then = time.time() + 366 * 86400
        monkeypatch.setattr(time, "time", lambda: then)
    elif cookie_kind == "wrong_secret":
        hosted_app.secret_key = "b4" * 32
    else:
        browser.set_cookie(VISITOR_COOKIE, cookie + "bad" if cookie_kind == "tampered" else OWNER_A, domain="planner.example")
    assert browser.get(result.location).status_code == 404
    assert b"Hidden title" not in browser.get("/trips").data


def test_restart_same_cookie_exact_snapshot_and_clear_draft(hosted_app, settings, parse_page, submit_trip):
    browser = hosted_app.test_client()
    result = save_from_browser(browser, parse_page, submit_trip)
    cookie = browser.get_cookie(VISITOR_COOKIE, domain="planner.example").value
    with closing(sqlite3.connect(hosted_app.config["DATABASE"])) as connection:
        before = connection.execute("SELECT * FROM saved_trips").fetchall()
    restarted = hosting().create_hosted_app(settings).test_client()
    restarted.set_cookie(VISITOR_COOKIE, cookie, domain="planner.example")
    assert restarted.get(result.location).status_code == 200
    assert submit_trip(restarted).status_code == 303
    token = parse_page(restarted.get("/itinerary")).find("input", name="csrf_token").attrs["value"]
    assert restarted.post("/draft/clear", data={"csrf_token": token}).status_code == 303
    assert b"Same trip" in restarted.get("/trips").data
    with closing(sqlite3.connect(hosted_app.config["DATABASE"])) as connection:
        assert connection.execute("SELECT * FROM saved_trips").fetchall() == before


def test_csrf_and_failed_save_preserve_draft(hosted_app, parse_page, submit_trip):
    browser = hosted_app.test_client()
    assert submit_trip(browser).status_code == 303
    page = parse_page(browser.get("/itinerary"))
    fingerprint = page.find("input", name="snapshot_fingerprint").attrs["value"]
    token = page.find("input", name="csrf_token").attrs["value"]
    assert browser.post("/itinerary/save", data={"trip_name": "keep", "snapshot_fingerprint": fingerprint}).status_code == 400
    with closing(sqlite3.connect(hosted_app.config["DATABASE"])) as connection:
        connection.execute("BEGIN EXCLUSIVE")
        failure = browser.post("/itinerary/save", data={"csrf_token": token, "trip_name": "keep", "snapshot_fingerprint": fingerprint})
        assert failure.status_code == 503 and b"keep" in failure.data
        connection.rollback()
    assert browser.get("/itinerary").status_code == 200
    assert b"No saved trips yet" in browser.get("/trips").data


def test_hosted_disclosure_on_personal_pages_and_local_unchanged(hosted_app, app, parse_page, submit_trip):
    browser = hosted_app.test_client()
    for path in ("/about", "/trips"):
        text = browser.get(path).text.lower()
        assert "365" in text and "cookie" in text and "no account recovery" in text
        assert "shared local collection" not in text
    assert submit_trip(browser).status_code == 303
    text = browser.get("/itinerary").text.lower()
    assert "cookie" in text and "shared local collection" not in text
    assert b"shared local collection" in app.test_client().get("/trips").data.lower()


@pytest.mark.parametrize("destination,budget,currency", [
    ("Paris, France", "300", "EUR"), ("Lagos, Nigeria", "300000", "NGN"),
    ("London, United Kingdom", "300", "GBP"), ("New York City, United States", "300", "USD"),
    ("Tokyo, Japan", "30000", "JPY"), ("Cape Town, South Africa", "3000", "ZAR"),
])
def test_hosted_flow_preserves_currencies_maps_photos(hosted_app, parse_page, submit_trip, destination, budget, currency):
    browser = hosted_app.test_client()
    form = {"destination": destination, "days": "2", "budget": budget,
            "interests": ["food", "history"], "pace": ""}
    assert submit_trip(browser, form).status_code == 303
    response = browser.get("/itinerary")
    assert response.status_code == 200 and currency in response.text
    page = parse_page(response)
    maps = [element for element in page.find_all("a") if "google.com/maps" in element.attrs.get("href", "")]
    assert maps and all(element.attrs["href"].startswith("https://www.google.com/maps/search/?api=1") for element in maps)
    assert page.find_all("img")
    for path in ("/static/js/appearance.js", "/static/css/style.css"):
        assert browser.get(path).status_code == 200


def test_repository_preserves_snapshot_and_legacy_database(settings, payload):
    from saved_trips import save_trip as local_save
    from snapshots import dump_snapshot
    repo = repository()
    directory = Path(settings["TRIPPLANNER_STORAGE_DIR"])
    local = directory / "old.sqlite3"
    local_save(local, "old", payload)
    before = local.read_bytes()
    with pytest.raises(Exception) as error:
        repo.initialize_store(local)
    from saved_trips import StorageUnavailableError
    assert isinstance(error.value, StorageUnavailableError)
    assert local.read_bytes() == before
    database = directory / "new.sqlite3"
    repo.initialize_store(database)
    record, created = repo.save_trip(database, "new", payload, owner=OWNER_A)
    assert created and record["available"]
    assert repo.get_trip(database, record["id"], owner=OWNER_B) is None
    assert repo.list_trips(database, owner=OWNER_B) == []
    with closing(sqlite3.connect(database)) as connection:
        raw = connection.execute("SELECT snapshot_json FROM saved_trips").fetchone()[0]
    assert raw == dump_snapshot(payload)


def test_foreign_damaged_duplicate_cannot_influence_save(settings, payload):
    database = Path(settings["TRIPPLANNER_STORAGE_DIR"]) / "hosted-trips.sqlite3"
    repo = repository()
    repo.initialize_store(database)
    record, _ = repo.save_trip(database, "same", payload, owner=OWNER_A)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("UPDATE saved_trips SET snapshot_json = 'broken' WHERE id = ?", (record["id"],))
    second, created = repo.save_trip(database, "same", payload, owner=OWNER_B)
    assert created and second["available"] and second["id"] != record["id"]
    from saved_trips import SavedTripUnavailableError
    with pytest.raises(SavedTripUnavailableError):
        repo.save_trip(database, "same", payload, owner=OWNER_A)
    assert len(repo.list_trips(database, owner=OWNER_B)) == 1


def test_concurrent_identical_saves_are_atomic_per_owner(settings, payload):
    database = Path(settings["TRIPPLANNER_STORAGE_DIR"]) / "hosted-trips.sqlite3"
    repo = repository()
    repo.initialize_store(database)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: repo.save_trip(database, "same", payload, owner=OWNER_A), range(8)))
    assert sum(created for record, created in results) == 1
    assert len({record["id"] for record, created in results}) == 1
    assert len(repo.list_trips(database, owner=OWNER_A)) == 1


@pytest.mark.parametrize("owner", [None, "", "a", "x" * 64, "a" * 64 + "' OR 1=1 --"])
def test_repository_owner_validation(settings, payload, owner):
    database = Path(settings["TRIPPLANNER_STORAGE_DIR"]) / "hosted-trips.sqlite3"
    repo = repository()
    repo.initialize_store(database)
    with pytest.raises(ValueError):
        repo.save_trip(database, "same", payload, owner=owner)
    with pytest.raises(ValueError):
        repo.list_trips(database, owner=owner)
    with pytest.raises(ValueError):
        repo.get_trip(database, 1, owner=owner)


def test_existing_empty_database_is_not_silently_reset(settings):
    from saved_trips import StorageUnavailableError
    database = Path(settings["TRIPPLANNER_STORAGE_DIR"]) / "hosted-trips.sqlite3"
    database.touch()
    with pytest.raises(StorageUnavailableError):
        hosting().create_hosted_app(settings)
    assert database.read_bytes() == b""


def test_backup_and_disposable_recovery_preserve_ownership_and_bytes(settings, tmp_path, payload):
    repo = repository()
    database = Path(settings["TRIPPLANNER_STORAGE_DIR"]) / "hosted-trips.sqlite3"
    repo.initialize_store(database)
    record, _ = repo.save_trip(database, "private", payload, owner=OWNER_A)
    backup = tmp_path / "private-backup.sqlite3"
    importlib.import_module("hosting.backup").backup_store(database, backup)
    assert backup.is_file()
    repo.initialize_store(backup)
    assert repo.get_trip(backup, record["id"], owner=OWNER_A) == record
    assert repo.get_trip(backup, record["id"], owner=OWNER_B) is None
    before = backup.read_bytes()
    with pytest.raises(FileExistsError):
        importlib.import_module("hosting.backup").backup_store(database, backup)
    assert backup.read_bytes() == before
    with closing(sqlite3.connect(database)) as original, closing(sqlite3.connect(backup)) as copied:
        assert original.execute("SELECT * FROM saved_trips").fetchall() == copied.execute("SELECT * FROM saved_trips").fetchall()


def test_historical_v1_snapshot_remains_byte_identical(settings):
    fixture = Path(__file__).parent / "fixtures" / "phase7-paris-snapshot.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    from snapshots import dump_snapshot
    database = Path(settings["TRIPPLANNER_STORAGE_DIR"]) / "legacy-hosted.sqlite3"
    repo = repository()
    repo.initialize_store(database)
    record, _ = repo.save_trip(database, "Original estimate", payload, owner=OWNER_A)
    assert record["available"] and record["snapshot"]["version"] == 1
    with closing(sqlite3.connect(database)) as connection:
        raw = connection.execute("SELECT snapshot_json FROM saved_trips").fetchone()[0]
    assert raw == dump_snapshot(payload)


def test_failed_transaction_never_reports_save_or_changes_other_owner(settings, payload):
    from saved_trips import StorageUnavailableError
    database = Path(settings["TRIPPLANNER_STORAGE_DIR"]) / "rollback.sqlite3"
    repo = repository()
    repo.initialize_store(database)
    original, _ = repo.save_trip(database, "Original", payload, owner=OWNER_A)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("CREATE TRIGGER reject_save BEFORE INSERT ON saved_trips BEGIN SELECT RAISE(ABORT, 'fail'); END")
    with pytest.raises(StorageUnavailableError):
        repo.save_trip(database, "second", payload, owner=OWNER_B)
    assert repo.get_trip(database, original["id"], owner=OWNER_A) == original
    assert repo.list_trips(database, owner=OWNER_B) == []


def test_public_500_and_logs_do_not_expose_request_or_exception(hosted_app, caplog):
    hosted_app.config["TESTING"] = False
    def fail():
        raise RuntimeError("private-path private-title " + hosted_app.secret_key)
    hosted_app.view_functions["home"] = fail
    response = hosted_app.test_client().get("/?private-query=hidden")
    assert response.status_code == 500
    combined = response.text + caplog.text
    for forbidden in ("private-path", "private-title", hosted_app.secret_key, "private-query", "Traceback"):
        assert forbidden not in combined
    assert "no-store" in response.headers["Cache-Control"]


def test_oversized_body_is_bounded_before_form_processing(hosted_app):
    response = hosted_app.test_client().post("/plan", data={"destination": "x" * 70000})
    assert response.status_code == 413

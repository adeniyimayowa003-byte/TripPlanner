"""Phase 6's approved server-rendered journey, defined before implementation.

These tests do not start a server or execute JavaScript. Real layout, keyboard
focus, and script-blocked browser checks remain implementation-stage work.
"""

from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlsplit

import pytest


@pytest.fixture
def forbid_storage(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Rejected requests and ordinary planning must not open storage.")

    monkeypatch.setattr(sqlite3, "connect", forbidden)


def database_path(app):
    return Path(app.config["DATABASE"])


def read_rows(app):
    path = database_path(app)
    if not path.exists():
        return []
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(
            "SELECT id, title, created_at, snapshot_json FROM saved_trips ORDER BY id"
        ).fetchall()


def review(client, parse_page):
    response = client.get("/itinerary")
    assert response.status_code == 200
    page = parse_page(response)
    form = page.find("form", action="/itinerary/save")
    assert form is not None, "The reviewed itinerary needs its real save form."
    assert form.attrs.get("method", "").casefold() == "post"
    data = {}
    for name in ("csrf_token", "snapshot_fingerprint"):
        node = form.find("input", name=name)
        assert node is not None and node.attrs.get("type") == "hidden"
        assert node.attrs.get("value")
        data[name] = node.attrs["value"]
    data["trip_name"] = "Paris weekend"
    return page, form, data


def save_reviewed(client, parse_page, *, name="Paris weekend"):
    _, _, data = review(client, parse_page)
    data["trip_name"] = name
    response = client.post("/itinerary/save", data=data)
    assert response.status_code == 303
    path = urlsplit(response.headers["Location"]).path
    assert re.fullmatch(r"/trips/[1-9][0-9]*", path)
    return path


def assert_draft(client, expected):
    with client.session_transaction() as session:
        assert session.get("trip_draft") == expected


def forbid_catalog(monkeypatch):
    """Cover aliases already imported by the app as well as module entry points."""
    import app as app_module
    import catalog
    import itinerary
    import recommendations

    def forbidden(*args, **kwargs):
        pytest.fail("Saved reads/error rendering must not load today's catalog or regenerate results.")

    for module, name in (
        (app_module, "load_catalog"), (catalog, "load_catalog"),
        (recommendations, "load_catalog"),
        (recommendations, "recommend_trip_ideas"),
        (itinerary, "recommend_trip_ideas"), (itinerary, "generate_itinerary"),
        (app_module, "recommend_trip_ideas"), (app_module, "generate_itinerary"),
    ):
        if hasattr(module, name):
            monkeypatch.setattr(module, name, forbidden)
    snapshot_module = sys.modules.get("snapshots")
    if snapshot_module is not None:
        for name in ("load_catalog", "build_snapshot", "recommend_trip_ideas", "generate_itinerary"):
            if hasattr(snapshot_module, name):
                monkeypatch.setattr(snapshot_module, name, forbidden)
    if hasattr(app_module, "build_snapshot"):
        monkeypatch.setattr(app_module, "build_snapshot", forbidden)


def replace_catalog(monkeypatch, tmp_path, places):
    import catalog

    path = tmp_path / "saved-flow-catalog.json"
    path.write_text(json.dumps({"places": places}), encoding="utf-8")
    monkeypatch.setattr(catalog, "CATALOG_FILE", path)


def corrupt_row(app, trip_path, value):
    with closing(sqlite3.connect(database_path(app))) as connection:
        connection.execute(
            "UPDATE saved_trips SET snapshot_json = ? WHERE id = ?",
            (value, int(trip_path.rsplit("/", 1)[1])),
        )
        connection.commit()


def assert_storage_error(response, parse_page, private_path):
    assert response.status_code == 503
    page = parse_page(response)
    assert "saved trips are temporarily unavailable" in page.text.casefold()
    assert page.find("a", href="/plan") or page.find("a", href="/itinerary")
    for leak in (str(private_path), "Traceback", "sqlite3.OperationalError", "SELECT ", "INSERT "):
        assert leak not in response.get_data(as_text=True)
    assert "saved successfully" not in page.text.casefold()
    return page


def test_default_storage_configuration_is_lazy(monkeypatch):
    from app import create_app

    monkeypatch.delenv("TRIPPLANNER_DATABASE", raising=False)

    def no_connection(*args, **kwargs):
        pytest.fail("App creation must not open storage.")

    monkeypatch.setattr(sqlite3, "connect", no_connection)
    fresh = create_app({"TESTING": True, "SECRET_KEY": "config-check"})
    assert Path(fresh.config["DATABASE"]) == Path(fresh.instance_path) / "tripplanner.sqlite3"
    assert 0 < fresh.config["DATABASE_TIMEOUT"] <= 5


def test_environment_and_test_config_can_choose_isolated_storage(monkeypatch, tmp_path):
    from app import create_app

    alternative = tmp_path / "environment" / "trips.sqlite3"
    override = tmp_path / "override" / "trips.sqlite3"
    monkeypatch.setenv("TRIPPLANNER_DATABASE", str(alternative))
    assert Path(create_app({"TESTING": True}).config["DATABASE"]) == alternative
    assert Path(create_app({"TESTING": True, "DATABASE": str(override)}).config["DATABASE"]) == override
    assert not alternative.parent.exists() and not override.parent.exists()


@pytest.mark.parametrize("path", ["/", "/plan", "/recommendations", "/itinerary"])
def test_ordinary_pages_never_initialize_storage(app, client, set_draft, path, forbid_storage):
    set_draft(client)
    assert client.get(path).status_code == 200
    assert not database_path(app).parent.exists()


def test_itinerary_save_form_is_labeled_protected_and_discloses_shared_collection(
    app, client, set_draft, parse_page,
):
    stored = set_draft(client)
    page, form, data = review(client, parse_page)
    field = form.find("input", name="trip_name")
    assert field is not None and field.attrs.get("id")
    assert form.find("label", **{"for": field.attrs["id"]}) is not None
    assert "required" not in field.attrs
    assert "optional" in form.text.casefold()
    assert any("save this itinerary" in button.text.casefold() for button in form.find_all("button"))
    assert "shared" in form.text.casefold() and "local" in form.text.casefold()
    assert re.fullmatch(r"[0-9a-f]{64}", data["snapshot_fingerprint"])
    assert data["snapshot_fingerprint"] != data["csrf_token"]
    assert "103.00" in page.text and "197.00" in page.text
    assert_draft(client, stored)
    assert not database_path(app).exists()


def test_save_redirects_to_complete_read_only_historical_detail(
    app, client, set_draft, parse_page, snapshot_payload,
):
    stored = set_draft(client)
    path = save_reviewed(client, parse_page)
    response = client.get(path)
    assert response.status_code == 200
    page = parse_page(response)
    assert len(page.find_all("h1")) == 1
    assert "Paris weekend" in page.text
    assert "saved snapshot" in page.text.casefold() and "UTC" in page.text
    for amount in ("300.00", "100.00", "103.00", "197.00", "50.00", "28.00", "25.00"):
        assert amount in page.text
    for item in snapshot_payload["recommendations"]:
        assert item["place"]["name"] in page.text
        assert item["reason"] in page.text
        assert item["place"]["description"] in page.text
        source = page.find("a", href=item["place"]["source_url"])
        assert source is not None
        if source.attrs.get("target") == "_blank":
            assert {"noopener", "noreferrer"} <= set(source.attrs.get("rel", "").split())
    for notice in snapshot_payload["itinerary"]["notices"]:
        assert notice in page.text
    assert re.search(r"\b6\s*(?:/|of|out of)\s*6\b", page.text)
    for number in (1, 2, 3):
        assert re.search(rf"\bDay\s+{number}\b", page.text)
    for word in ("flights", "accommodation", "transport", "opening", "travel", "illustrative"):
        assert word in page.text.casefold()
    assert page.find("a", href="/trips") is not None
    assert page.find("a", href="/plan") is not None
    assert page.find("form", action="/draft/clear") is None
    assert page.find("form", action="/itinerary/save") is None
    assert_draft(client, stored)
    rows = read_rows(app)
    assert len(rows) == 1 and rows[0][1] == "Paris weekend"
    assert json.loads(rows[0][3])["itinerary"]["estimated_cost"] == "103.00"


@pytest.mark.parametrize("name", ["", "   ", None, "  Voyage à Paris ✨  ", "旅" * 80])
def test_blank_unicode_and_boundary_titles_save_normally(app, client, set_draft, parse_page, name):
    set_draft(client)
    _, _, data = review(client, parse_page)
    if name is None:
        data.pop("trip_name")
    else:
        data["trip_name"] = name
    response = client.post("/itinerary/save", data=data)
    assert response.status_code == 303
    expected = name.strip() if name and name.strip() else "Paris, France — 3-day trip"
    assert read_rows(app)[0][1] == expected
    assert expected in parse_page(client.get(response.headers["Location"])).text


@pytest.mark.parametrize("name", ["x" * 81, "\tParis", "Paris\n", "Paris\r\ntrip", "\x00bad", "bad\x7f"])
def test_invalid_title_retains_input_and_associates_error_without_storage(
    app, client, set_draft, parse_page, name, forbid_storage,
):
    stored = set_draft(client)
    _, _, data = review(client, parse_page)
    data["trip_name"] = name
    response = client.post("/itinerary/save", data=data)
    assert response.status_code == 200
    page = parse_page(response)
    field = page.find("input", name="trip_name")
    assert field is not None and field.attrs.get("value") == name
    assert field.attrs.get("aria-invalid") == "true"
    described = field.attrs.get("aria-describedby", "").split()
    assert described and any(
        page.find(id=identifier) is not None
        and re.search(r"80|control|line|character|name", page.find(id=identifier).text, re.I)
        for identifier in described
    )
    assert "103.00" in page.text
    assert page.find("input", name="snapshot_fingerprint").attrs["value"] == data["snapshot_fingerprint"]
    assert_draft(client, stored)
    assert not database_path(app).parent.exists()


@pytest.mark.parametrize("name", ["<script>alert('trip')</script>", "'); DROP TABLE saved_trips;--"])
def test_titles_are_escaped_literal_text_and_parameterized_values(
    app, client, set_draft, parse_page, name,
):
    set_draft(client)
    path = save_reviewed(client, parse_page, name=name)
    for route in (path, "/trips"):
        page = parse_page(client.get(route))
        assert name in page.text
        assert not any("alert('trip')" in script.text for script in page.find_all("script"))
    assert read_rows(app)[0][1] == name
    assert len(read_rows(app)) == 1


def test_duplicate_save_preserves_id_timestamp_and_truthful_feedback(app, client, set_draft, parse_page):
    set_draft(client)
    path = save_reviewed(client, parse_page, name="  Paris weekend  ")
    first = read_rows(app)
    assert save_reviewed(client, parse_page) == path
    page = parse_page(client.get(path))
    assert "this trip is already saved" in page.text.casefold()
    assert read_rows(app) == first
    assert client.get(path).status_code == 200
    assert read_rows(app) == first


def test_different_title_or_changed_content_creates_new_immutable_versions(
    app, client, set_draft, parse_page, draft_data,
):
    set_draft(client)
    original_path = save_reviewed(client, parse_page)
    original = read_rows(app)[0]
    renamed_path = save_reviewed(client, parse_page, name="Paris alternatives")
    changed = deepcopy(draft_data)
    changed["preferences"]["budget"] = "60.00"
    set_draft(client, changed)
    changed_path = save_reviewed(client, parse_page)
    assert len({original_path, renamed_path, changed_path}) == 3
    assert len(read_rows(app)) == 3 and read_rows(app)[0] == original
    assert "103.00" in parse_page(client.get(original_path)).text
    assert "60.00" in parse_page(client.get(changed_path)).text


def test_collection_is_empty_truthful_and_does_not_create_database(app, client, parse_page):
    response = client.get("/trips")
    assert response.status_code == 200
    page = parse_page(response)
    assert "no saved trips yet" in page.text.casefold()
    assert "shared" in page.text.casefold() and "local" in page.text.casefold()
    assert any("start planning" in link.text.casefold() for link in page.find_all("a", href="/plan"))
    assert not any(re.fullmatch(r"/trips/[1-9][0-9]*", a.attrs.get("href", "")) for a in page.find_all("a"))
    assert not database_path(app).parent.exists()


@pytest.mark.parametrize("route", ["/", "/plan", "/recommendations", "/itinerary"])
def test_saved_trips_navigation_works_from_existing_pages(client, set_draft, parse_page, route):
    set_draft(client)
    page = parse_page(client.get(route))
    header = page.find("header")
    link = header.find("a", href="/trips")
    assert link is not None and "saved trips" in link.text.casefold()
    assert client.get(link.attrs["href"]).status_code == 200


def test_collection_has_summaries_newest_first_with_id_tie_break(
    app, client, set_draft, parse_page,
):
    set_draft(client)
    paths = [save_reviewed(client, parse_page, name=name) for name in ("Earlier", "Later", "Latest")]
    tied_timestamp = read_rows(app)[0][2]
    with closing(sqlite3.connect(database_path(app))) as connection:
        connection.execute("UPDATE saved_trips SET created_at = ?", (tied_timestamp,))
        connection.commit()
    page = parse_page(client.get("/trips"))
    links = [
        a for a in page.find_all("a")
        if a.attrs.get("href") in paths and "view saved trip" in a.text.casefold()
    ]
    assert list(dict.fromkeys(a.attrs["href"] for a in links)) == list(reversed(paths))
    assert all("view saved trip" in a.text.casefold() for a in links)
    for text in ("Earlier", "Later", "Latest", "Paris, France", "3", "300.00", "103.00", "UTC"):
        assert text in page.text


def test_clear_current_draft_keeps_saved_collection(app, client, set_draft, parse_page, csrf_token):
    set_draft(client)
    path = save_reviewed(client, parse_page)
    before = read_rows(app)
    response = client.post("/draft/clear", data={"csrf_token": csrf_token(client)})
    assert response.status_code == 303
    assert_draft(client, None)
    assert client.get("/itinerary").status_code in (302, 303)
    assert client.get("/trips").status_code == client.get(path).status_code == 200
    assert read_rows(app) == before


def test_saved_collection_is_shared_but_unsaved_drafts_are_not(
    client, client_factory, set_draft, parse_page,
):
    original = set_draft(client)
    path = save_reviewed(client, parse_page)
    other = client_factory()
    assert other.get("/itinerary").status_code in (302, 303)
    assert other.get("/trips").status_code == other.get(path).status_code == 200
    assert "Paris weekend" in parse_page(other.get("/trips")).text
    assert_draft(other, None)
    assert_draft(client, original)


def test_new_app_and_changed_secret_reopen_saved_trip_without_cookie(
    app, client, set_draft, parse_page,
):
    from app import create_app

    set_draft(client)
    path = save_reviewed(client, parse_page)
    restarted = create_app({
        "TESTING": True, "SECRET_KEY": "different-after-restart",
        "DATABASE": app.config["DATABASE"], "DATABASE_TIMEOUT": 0.05,
    }).test_client()
    assert restarted.get("/trips").status_code == 200
    detail = restarted.get(path)
    assert detail.status_code == 200 and "103.00" in parse_page(detail).text
    assert_draft(restarted, None)


@pytest.mark.parametrize("stored_draft", ["valid", "malformed", "none"])
@pytest.mark.parametrize("route_kind", ["list", "detail", "malformed-id", "unknown-id"])
def test_saved_views_and_404s_do_not_load_catalog_or_touch_draft(
    app, client, set_draft, parse_page, monkeypatch, stored_draft, route_kind,
):
    set_draft(client)
    path = save_reviewed(client, parse_page)
    expected = None
    if stored_draft == "valid":
        expected = set_draft(client)
    elif stored_draft == "malformed":
        expected = set_draft(client, {"version": 999, "preferences": "not a current draft"})
    else:
        with client.session_transaction() as session:
            session.pop("trip_draft", None)
    routes = {"list": "/trips", "detail": path, "malformed-id": "/trips/not-an-id", "unknown-id": "/trips/999999"}
    before = read_rows(app)
    forbid_catalog(monkeypatch)
    response = client.get(routes[route_kind])
    assert response.status_code == (200 if route_kind in {"list", "detail"} else 404)
    page = parse_page(response)
    assert page.find("a", href="/trips") is not None
    assert_draft(client, expected)
    assert read_rows(app) == before


@pytest.mark.parametrize("failure", ["removed-destination", "missing-file", "unreadable-file"])
def test_saved_pages_work_after_current_catalog_disappears(
    client, set_draft, parse_page, monkeypatch, tmp_path, failure,
):
    import catalog

    expected = set_draft(client)
    path = save_reviewed(client, parse_page)
    if failure == "removed-destination":
        replace_catalog(monkeypatch, tmp_path, [])
    elif failure == "missing-file":
        monkeypatch.setattr(catalog, "CATALOG_FILE", tmp_path / "absent-catalog.json")
    else:
        monkeypatch.setattr(catalog, "CATALOG_FILE", tmp_path)
    for route in ("/trips", path):
        response = client.get(route)
        assert response.status_code == 200
        assert "103.00" in parse_page(response).text
    assert_draft(client, expected)


def test_saved_detail_and_plan_another_do_not_replace_current_answers(
    client, set_draft, parse_page, draft_data,
):
    set_draft(client)
    path = save_reviewed(client, parse_page)
    changed = deepcopy(draft_data)
    changed["preferences"]["budget"] = "60.00"
    expected = set_draft(client, changed)
    page = parse_page(client.get(path))
    link = next((a for a in page.find_all("a", href="/plan") if "plan another trip" in a.text.casefold()), None)
    assert link is not None
    assert_draft(client, expected)
    form = parse_page(client.get(link.attrs["href"]))
    assert form.find("input", name="budget").attrs["value"] == "60.00"
    assert_draft(client, expected)


@pytest.mark.parametrize("route", ["/trips/0", "/trips/-1", "/trips/nope", "/trips/1.5", "/trips/999999", "/trips/9223372036854775808", "/trips/" + "9" * 100])
def test_invalid_unknown_and_overflow_ids_are_friendly_404s(app, client, parse_page, route):
    response = client.get(route)
    assert response.status_code == 404
    page = parse_page(response)
    assert page.find("a", href="/trips") is not None
    assert "Traceback" not in page.text
    assert not database_path(app).exists()


@pytest.mark.parametrize("token_kind", ["missing", "wrong", "another-session"])
def test_save_csrf_rejected_before_catalog_or_storage_and_preserves_draft(
    app, client, client_factory, set_draft, csrf_token, monkeypatch, token_kind, forbid_storage,
):
    csrf_token(client)
    expected = set_draft(client, {"version": 999, "preferences": "preserve on CSRF error"})
    data = {"trip_name": "Rejected", "snapshot_fingerprint": "0" * 64}
    if token_kind == "wrong":
        data["csrf_token"] = "wrong"
    elif token_kind == "another-session":
        data["csrf_token"] = csrf_token(client_factory())
    forbid_catalog(monkeypatch)
    response = client.post("/itinerary/save", data=data)
    assert response.status_code == 400
    assert_draft(client, expected)
    assert not database_path(app).parent.exists()


@pytest.mark.parametrize("fingerprint", [None, "", "a" * 63, "g" * 64, "A" * 64, "a" * 65, " a" * 32])
def test_missing_malformed_fingerprints_do_not_initialize_storage(
    app, client, set_draft, parse_page, fingerprint, forbid_storage,
):
    expected = set_draft(client)
    _, _, data = review(client, parse_page)
    if fingerprint is None:
        data.pop("snapshot_fingerprint")
    else:
        data["snapshot_fingerprint"] = fingerprint
    response = client.post("/itinerary/save", data=data)
    assert response.status_code == 400
    assert_draft(client, expected)
    assert not database_path(app).parent.exists()


@pytest.mark.parametrize("draft_kind", ["missing", "malformed", "unsupported-version", "expired-shape", "unsupported-destination"])
def test_save_requires_valid_current_draft_before_fingerprint_or_title(
    app, client, set_draft, csrf_token, draft_data, draft_kind, forbid_storage,
):
    token = csrf_token(client)
    variants = {
        "malformed": "not a draft", "unsupported-version": {"version": 999, "preferences": {}},
        "expired-shape": {"version": 1},
        "unsupported-destination": deepcopy(draft_data),
    }
    variants["unsupported-destination"]["preferences"]["destination"] = "Atlantis"
    if draft_kind != "missing":
        set_draft(client, variants[draft_kind])
    response = client.post("/itinerary/save", data={"csrf_token": token, "trip_name": "x" * 81})
    assert response.status_code in (302, 303)
    assert urlsplit(response.headers["Location"]).path == "/plan"
    assert not database_path(app).parent.exists()


def test_get_cannot_save_a_trip(app, client):
    assert client.get("/itinerary/save").status_code == 405
    assert not database_path(app).exists()


def test_another_tab_changing_draft_rejects_old_form_before_title_or_storage(
    app, client, set_draft, parse_page, draft_data, forbid_storage,
):
    set_draft(client)
    _, _, data = review(client, parse_page)
    changed = deepcopy(draft_data)
    changed["preferences"]["budget"] = "60.00"
    expected = set_draft(client, changed)
    data["trip_name"] = "x" * 81  # Stale result takes precedence over bad title.
    response = client.post("/itinerary/save", data=data)
    assert response.status_code == 409
    page = parse_page(response)
    assert "your trip has changed. review the updated itinerary before saving" in page.text.casefold()
    assert page.find("a", href="/itinerary") is not None
    assert_draft(client, expected)
    assert not database_path(app).parent.exists()


@pytest.mark.parametrize("change", ["cost", "description", "source", "tags"])
def test_changed_reviewed_catalog_content_rejects_stale_form(
    app, client, set_draft, parse_page, monkeypatch, tmp_path, change, forbid_storage,
):
    from catalog import load_catalog

    expected = set_draft(client)
    _, _, data = review(client, parse_page)
    places = load_catalog()
    target = next(p for p in places if p["id"] == "paris-le-procope")
    if change == "cost":
        target["estimated_cost"] = 51
    elif change == "description":
        target["description"] += " Changed after review."
    elif change == "source":
        target["source_url"] = "https://example.com/updated-source"
    else:
        target["preference_tags"].append("family-friendly")
    replace_catalog(monkeypatch, tmp_path, places)
    response = client.post("/itinerary/save", data=data)
    assert response.status_code == 409
    assert parse_page(response).find("a", href="/itinerary") is not None
    assert_draft(client, expected)
    assert not database_path(app).exists()


def test_unrelated_catalog_edit_does_not_invalidate_unchanged_snapshot(
    app, client, set_draft, parse_page, monkeypatch, tmp_path,
):
    from catalog import load_catalog

    set_draft(client)
    _, _, data = review(client, parse_page)
    places = load_catalog()
    unrelated = deepcopy(places[0])
    unrelated.update(id="kyoto-unrelated", destination="Kyoto, Japan", description="Unrelated new entry.")
    places.append(unrelated)
    replace_catalog(monkeypatch, tmp_path, places)
    response = client.post("/itinerary/save", data=data)
    assert response.status_code == 303
    assert len(read_rows(app)) == 1


def test_catalog_removing_current_destination_uses_draft_recovery_not_stale_save(
    app, client, set_draft, parse_page, monkeypatch, tmp_path, forbid_storage,
):
    set_draft(client)
    _, _, data = review(client, parse_page)
    replace_catalog(monkeypatch, tmp_path, [])
    response = client.post("/itinerary/save", data=data)
    assert response.status_code in (302, 303)
    assert urlsplit(response.headers["Location"]).path == "/plan"
    assert_draft(client, None)
    assert not database_path(app).parent.exists()


@pytest.mark.parametrize("change", ["cost", "description", "source", "tags", "unrelated"])
def test_staleness_examples_really_change_only_the_intended_snapshot(
    snapshot_factory, change,
):
    """Check adversarial data even while the future save form is still absent."""
    from catalog import load_catalog

    places = load_catalog()
    original = snapshot_factory(catalog=places)
    changed = deepcopy(places)
    target = next(p for p in changed if p["id"] == "paris-le-procope")
    if change == "cost":
        target["estimated_cost"] = 51
    elif change == "description":
        target["description"] += " Changed after review."
    elif change == "source":
        target["source_url"] = "https://example.com/updated-source"
    elif change == "tags":
        target["preference_tags"].append("family-friendly")
    else:
        unrelated = deepcopy(changed[0])
        unrelated.update(id="kyoto-unrelated", destination="Kyoto, Japan")
        changed.append(unrelated)
    result = snapshot_factory(catalog=changed)
    assert (result == original) is (change == "unrelated")
    assert result["itinerary"]["estimated_cost"] == ("104.00" if change == "cost" else "103.00")


def test_save_uses_one_catalog_read_and_ignores_submitted_totals_or_json(
    app, client, set_draft, parse_page, monkeypatch,
):
    import app as app_module
    import catalog as catalog_module
    import recommendations as recommendations_module
    from catalog import load_catalog

    set_draft(client)
    _, _, data = review(client, parse_page)
    places = load_catalog()
    calls = []

    def counted():
        calls.append(True)
        result = deepcopy(places)
        if len(calls) > 1:
            next(p for p in result if p["id"] == "paris-le-procope")["estimated_cost"] = 51
        return result

    for module in (app_module, catalog_module, recommendations_module, sys.modules.get("snapshots")):
        if module is not None and hasattr(module, "load_catalog"):
            monkeypatch.setattr(module, "load_catalog", counted)
    data.update(estimated_cost="0.00", budget="999999.00", snapshot_json='{"itinerary": "fake"}', itinerary="fake")
    response = client.post("/itinerary/save", data=data)
    assert response.status_code == 303
    assert len(calls) == 1
    payload = json.loads(read_rows(app)[0][3])
    assert payload["preferences"]["budget"] == "300.00"
    assert payload["itinerary"]["estimated_cost"] == "103.00"
    assert len(payload["recommendations"]) == 7


@pytest.mark.parametrize("budget,days,interests,total,remaining,filled,slots", [
    ("60.00", 3, ["food", "history"], "0.00", "60.00", 3, 6),
    ("1.00", 14, ["food"], "0.00", "1.00", 0, 28),
    ("100.01", 3, ["food", "history"], "85.00", "15.01", 6, 6),
])
def test_partial_empty_and_cent_boundary_results_survive_save_and_reload(
    app, client, set_draft, draft_data, parse_page, budget, days, interests, total, remaining, filled, slots,
):
    changed = deepcopy(draft_data)
    changed["preferences"].update(budget=budget, days=days, interests=interests)
    set_draft(client, changed)
    path = save_reviewed(client, parse_page)
    payload = json.loads(read_rows(app)[0][3])
    assert payload["itinerary"]["estimated_cost"] == total
    assert payload["itinerary"]["unallocated_allowance"] == remaining
    assert payload["itinerary"]["filled_slots"] == filled
    assert payload["itinerary"]["total_slots"] == slots
    page = parse_page(client.get(path))
    assert total in page.text and remaining in page.text
    assert re.search(rf"\b{filled}\s*(?:/|of|out of)\s*{slots}\b", page.text)
    for notice in payload["itinerary"]["notices"]:
        assert notice in page.text


@pytest.mark.parametrize("bad_payload", ["not JSON", '{"version":999}', '{"version":true}'])
def test_unreadable_saved_row_is_409_other_rows_survive_and_no_catalog_is_needed(
    app, client, set_draft, parse_page, monkeypatch, bad_payload,
):
    expected = set_draft(client)
    broken = save_reviewed(client, parse_page, name="Damaged trip")
    good = save_reviewed(client, parse_page, name="Good trip")
    corrupt_row(app, broken, bad_payload)
    before = read_rows(app)
    forbid_catalog(monkeypatch)
    response = client.get(broken)
    assert response.status_code == 409
    assert parse_page(response).find("a", href="/trips") is not None
    listing = parse_page(client.get("/trips"))
    assert "unavailable" in listing.text.casefold()
    assert "Good trip" in listing.text and listing.find("a", href=good) is not None
    assert client.get(good).status_code == 200
    assert_draft(client, expected)
    assert read_rows(app) == before


def test_damaged_duplicate_save_is_not_falsely_successful(app, client, set_draft, parse_page):
    expected = set_draft(client)
    path = save_reviewed(client, parse_page)
    client.get(path)  # Consume the first genuine success flash.
    corrupt_row(app, path, "broken JSON")
    before = read_rows(app)
    _, _, data = review(client, parse_page)
    response = client.post("/itinerary/save", data=data)
    assert response.status_code == 409
    page = parse_page(response)
    assert "already saved" not in page.text.casefold()
    assert "saved successfully" not in page.text.casefold()
    assert page.find("a", href="/trips") is not None
    assert_draft(client, expected)
    assert read_rows(app) == before


@pytest.mark.parametrize("problem", ["directory", "corrupt", "unsupported-schema"])
def test_unavailable_storage_has_catalog_independent_saved_page_errors(
    app, client, set_draft, parse_page, monkeypatch, problem,
):
    expected = set_draft(client, {"version": 999, "preferences": "do not discard"})
    path = database_path(app)
    path.parent.mkdir(parents=True)
    if problem == "directory":
        path.mkdir()
        before = None
    elif problem == "corrupt":
        path.write_bytes(b"This is not a SQLite database. Preserve me.")
        before = path.read_bytes()
    else:
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("PRAGMA user_version=99")
            connection.commit()
        before = path.read_bytes()
    forbid_catalog(monkeypatch)
    for route in ("/trips", "/trips/1"):
        assert_storage_error(client.get(route), parse_page, path)
    assert_draft(client, expected)
    if before is not None:
        assert path.read_bytes() == before
    else:
        assert path.is_dir()


def test_failed_save_preserves_name_draft_and_recovers_without_false_success(
    app, client, set_draft, parse_page,
):
    expected = set_draft(client)
    _, _, data = review(client, parse_page)
    data["trip_name"] = "Keep this submitted name"
    path = database_path(app)
    path.mkdir(parents=True)  # A directory cannot be opened as the database file.
    response = client.post("/itinerary/save", data=data)
    page = assert_storage_error(response, parse_page, path)
    field = page.find("input", name="trip_name")
    assert field is not None and field.attrs.get("value") == data["trip_name"]
    assert_draft(client, expected)
    assert path.is_dir()


@pytest.mark.parametrize("operation", ["list", "detail", "save"])
def test_real_locked_storage_returns_503_and_preserves_existing_rows_and_draft(
    app, client, set_draft, parse_page, monkeypatch, operation,
):
    expected = set_draft(client)
    trip_path = save_reviewed(client, parse_page)
    client.get(trip_path)  # Consume the genuine success message before faulting.
    _, _, data = review(client, parse_page)
    data["trip_name"] = "Pending named trip"
    before = read_rows(app)
    path = database_path(app)
    holder = sqlite3.connect(path, timeout=0.05)
    try:
        holder.execute("BEGIN EXCLUSIVE")
        if operation == "save":
            response = client.post("/itinerary/save", data=data)
        else:
            forbid_catalog(monkeypatch)
            response = client.get("/trips" if operation == "list" else trip_path)
        assert_storage_error(response, parse_page, path)
        assert_draft(client, expected)
    finally:
        holder.rollback()
        holder.close()
    assert read_rows(app) == before


def test_rejected_save_cannot_change_preexisting_saved_rows(
    app, client, set_draft, parse_page,
):
    expected = set_draft(client)
    save_reviewed(client, parse_page)
    _, _, data = review(client, parse_page)
    before = read_rows(app)
    data["csrf_token"] = "not the session token"
    response = client.post("/itinerary/save", data=data)
    assert response.status_code == 400
    assert read_rows(app) == before
    assert_draft(client, expected)


def test_unusable_database_does_not_disable_unsaved_planning(
    app, client, set_draft, parse_page, submit_trip,
):
    path = database_path(app)
    path.mkdir(parents=True)
    set_draft(client)
    for route in ("/", "/plan", "/recommendations", "/itinerary"):
        assert client.get(route).status_code == 200
    assert submit_trip(client).status_code == 303
    assert "103.00" in parse_page(client.get("/itinerary")).text
    assert path.is_dir()


def test_server_rendered_save_view_back_and_plan_another_flow_needs_no_script_execution(
    client, set_draft, parse_page,
):
    set_draft(client)
    path = save_reviewed(client, parse_page)
    detail = parse_page(client.get(path))
    back = next((a for a in detail.find_all("a", href="/trips") if "back to saved trips" in a.text.casefold()), None)
    assert back is not None
    collection = parse_page(client.get(back.attrs["href"]))
    view = collection.find("a", href=path)
    assert view is not None
    reopened = parse_page(client.get(view.attrs["href"]))
    another = next((a for a in reopened.find_all("a", href="/plan") if "plan another trip" in a.text.casefold()), None)
    assert another is not None
    assert parse_page(client.get(another.attrs["href"])).find("form", action="/plan") is not None

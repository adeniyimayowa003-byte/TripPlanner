"""Phase 7's server contracts, defined before the appearance implementation.

Flask's test client does not run JavaScript or render CSS. These checks prove
shared HTML structure and unchanged travel-data behavior, not an interactive
theme, actual visual visibility/contrast, keyboard behavior, or persistence in
a real browser. Tests use only the existing per-test SQLite database.
"""

from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

import pytest


def ancestry(root, wanted):
    """Return the parsed ancestors and node by identity, not dataclass equality."""
    if root is wanted:
        return [root]
    for child in root.children:
        if hasattr(child, "tag"):
            path = ancestry(child, wanted)
            if path:
                return [root, *path]
    return []


def hidden_in_initial_markup(root, node):
    """Inspect markup hiding/inertness; no CSS-cascade or rendering claim."""
    path = ancestry(root, node)
    assert path, "The node must actually belong to the parsed document."
    return any(
        "hidden" in ancestor.attrs
        or "inert" in ancestor.attrs
        or ancestor.attrs.get("aria-hidden", "").strip().casefold() == "true"
        or ancestor.tag in {"noscript", "template"}
        or "display:none" in re.sub(r"\s+", "", ancestor.attrs.get("style", "")).casefold()
        or "visibility:hidden" in re.sub(r"\s+", "", ancestor.attrs.get("style", "")).casefold()
        for ancestor in path
    )


def assert_appearance_header(response, parse_page):
    page = parse_page(response)
    header = page.find("header")
    assert header is not None
    controls = page.find_all("select", id="appearance")
    assert len(controls) == 1, "Every shared-layout page needs one native Appearance selector."
    select = controls[0]
    assert select in header.find_all("select")
    label = header.find("label", **{"for": "appearance"})
    assert label is not None and label.text == "Appearance"
    options = [(node.attrs.get("value"), node.text) for node in select.find_all("option")]
    assert options == [("system", "Use device setting"), ("light", "Light"), ("dark", "Dark")]
    assert "disabled" in select.attrs, "Do not expose a working-looking control before JS binds it."
    path = ancestry(page, select)
    assert any("hidden" in node.attrs for node in path[:-1]), "The selector wrapper starts hidden."
    assert not any(node.tag == "form" for node in path), "Appearance must not submit a trip form."

    fallback = header.find(id="appearance-fallback")
    assert fallback is not None and len(fallback.text) >= 20
    assert not hidden_in_initial_markup(page, fallback), "Fallback help cannot hide with the unavailable control."
    assert "device" in fallback.text.casefold()
    assert any(word in fallback.text.casefold() for word in ("appearance", "controls", "javascript", "scripts"))

    status = header.find(id="appearance-status")
    assert status is not None and not status.text
    assert status.attrs.get("aria-live") == "polite" or (
        status.attrs.get("role") == "status"
        and status.attrs.get("aria-live", "polite") == "polite"
    )
    assert status.attrs.get("aria-live") != "assertive"

    assert page.find("html").attrs.get("data-appearance") is None, "The server does not own this browser preference."
    assert header.find("a", href="/trips") is not None
    assert page.find("a", href="#main-content") is not None
    assert len(page.find_all("main", id="main-content")) == 1
    return page


def reviewed_form(client, parse_page):
    response = client.get("/itinerary")
    assert response.status_code == 200
    form = parse_page(response).find("form", action="/itinerary/save")
    assert form is not None, "The already implemented Phase 6 form must remain available."
    data = {"trip_name": "Paris weekend"}
    for name in ("csrf_token", "snapshot_fingerprint"):
        field = form.find("input", name=name)
        assert field is not None and field.attrs.get("value")
        data[name] = field.attrs["value"]
    return data


def seed_saved(app, payload):
    from saved_trips import save_trip

    record, created = save_trip(app.config["DATABASE"], "Paris weekend", payload)
    assert created
    return f"/trips/{record['id']}"


def corrupt_saved_snapshot(app, path):
    with closing(sqlite3.connect(app.config["DATABASE"])) as connection:
        connection.execute(
            "UPDATE saved_trips SET snapshot_json = ? WHERE id = ?",
            ("{}", int(path.rsplit("/", 1)[1])),
        )
        connection.commit()


def make_unreadable_database(app):
    path = Path(app.config["DATABASE"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"This test fixture is not a SQLite database.")


SAVED_VIEWS = [
    ("empty", 200), ("populated", 200), ("detail", 200),
    ("missing", 404), ("malformed", 404), ("unmatched-route", 404),
    ("damaged", 409), ("collection-unavailable", 503), ("detail-unavailable", 503),
]


def saved_view_path(case, app, snapshot_payload):
    if case in {"populated", "detail", "damaged"}:
        path = seed_saved(app, snapshot_payload)
        if case == "damaged":
            corrupt_saved_snapshot(app, path)
        return "/trips" if case == "populated" else path
    if case in {"collection-unavailable", "detail-unavailable"}:
        make_unreadable_database(app)
        return "/trips" if case == "collection-unavailable" else "/trips/1"
    return {
        "empty": "/trips", "missing": "/trips/999",
        "malformed": "/trips/not-an-id", "unmatched-route": "/trips/no/such/route",
    }[case]


def forbid_live_trip_access(monkeypatch):
    import app as app_module
    import catalog
    import drafts
    import itinerary
    import recommendations
    import snapshots

    def forbidden(*args, **kwargs):
        pytest.fail("Shared saved-page appearance must not load/validate/regenerate a live trip.")

    for module, names in (
        (app_module, ("load_catalog", "load_draft", "build_snapshot", "recommend_trip_ideas")),
        (catalog, ("load_catalog",)), (drafts, ("load_draft",)),
        (itinerary, ("load_catalog", "generate_itinerary", "recommend_trip_ideas")),
        (recommendations, ("load_catalog", "recommend_trip_ideas")),
        (snapshots, ("build_snapshot", "generate_itinerary", "recommend_trip_ideas")),
    ):
        for name in names:
            if hasattr(module, name):
                monkeypatch.setattr(module, name, forbidden)


@pytest.mark.parametrize(
    "html,wanted_hidden",
    [
        ('<header><p id="help">Device appearance</p></header>', False),
        ('<header hidden><p id="help">Device appearance</p></header>', True),
        ('<header><div hidden><p id="help">Device appearance</p></div></header>', True),
        ('<header><noscript><p id="help">Device appearance</p></noscript></header>', True),
        ('<header><div style="display: none"><p id="help">Device appearance</p></div></header>', True),
        ('<header><div style=" Visibility:\n HIDDEN "><p id="help">Device appearance</p></div></header>', True),
        ('<header inert><p id="help">Device appearance</p></header>', True),
        ('<header><div aria-hidden="true"><p id="help">Device appearance</p></div></header>', True),
        ('<header><div aria-hidden="false"><p id="help">Device appearance</p></div></header>', False),
        ('<header><div hidden>Control</div><p id="help">Device appearance</p></header>', False),
    ],
)
def test_initial_markup_helper_checks_ancestors_not_unrelated_hidden_nodes(parse_page, html, wanted_hidden):
    page = parse_page(html)
    assert hidden_in_initial_markup(page, page.find(id="help")) is wanted_hidden


@pytest.mark.parametrize("path", ["/", "/plan", "/recommendations", "/itinerary"])
def test_ordinary_shared_pages_offer_progressively_enhanced_appearance(
    client, set_draft, parse_page, path,
):
    set_draft(client)
    response = client.get(path)
    assert response.status_code == 200
    assert_appearance_header(response, parse_page)


@pytest.mark.parametrize("case,status", SAVED_VIEWS)
def test_saved_and_recovery_pages_share_appearance_without_live_catalog_access(
    app, client, set_draft, draft_data, parse_page, snapshot_payload, monkeypatch, case, status,
):
    # Deliberately retain an obsolete cookie: historical reads may not validate,
    # remove, restore, or replace it merely to render the shared header.
    stale = deepcopy(draft_data)
    stale["preferences"]["destination"] = "A destination removed from today's catalog"
    set_draft(client, stale)
    path = saved_view_path(case, app, snapshot_payload)
    forbid_live_trip_access(monkeypatch)
    response = client.get(path)
    assert response.status_code == status
    with client.session_transaction() as session:
        assert session["trip_draft"] == stale
    assert_appearance_header(response, parse_page)


@pytest.mark.parametrize(
    "case,status",
    [
        ("invalid-preferences", 200), ("invalid-title", 200),
        ("csrf", 400), ("incomplete-save", 400), ("changed-save", 409),
        ("save-unavailable", 503),
    ],
)
def test_validation_and_form_recovery_views_keep_the_appearance_control(
    app, client, set_draft, parse_page, csrf_token, valid_form, case, status,
):
    stored = set_draft(client)
    if case == "invalid-preferences":
        data = {**valid_form, "budget": "unfinished", "csrf_token": csrf_token(client)}
        data["currency_context"] = parse_page(client.get("/plan")).find("input", name="currency_context").attrs["value"]
        response = client.post("/plan", data=data)
        assert parse_page(response).find("input", name="budget").attrs["value"] == "unfinished"
    elif case == "csrf":
        response = client.post("/plan", data=valid_form)
    else:
        data = reviewed_form(client, parse_page)
        if case == "invalid-title":
            data["trip_name"] = "x" * 81
        elif case == "incomplete-save":
            data.pop("snapshot_fingerprint")
        elif case == "changed-save":
            old = data["snapshot_fingerprint"]
            data["snapshot_fingerprint"] = ("1" if old[0] == "0" else "0") + old[1:]
        elif case == "save-unavailable":
            make_unreadable_database(app)
        response = client.post("/itinerary/save", data=data)
        if case in {"invalid-title", "save-unavailable"}:
            assert parse_page(response).find("input", name="trip_name").attrs["value"] == data["trip_name"]
    assert response.status_code == status
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored
    assert_appearance_header(response, parse_page)


def test_shared_head_loads_one_local_early_appearance_script_before_styles(client, parse_page):
    page = parse_page(client.get("/"))
    scripts = [node for node in page.find_all("script") if urlsplit(node.attrs.get("src", "")).path == "/static/js/appearance.js"]
    assert len(scripts) == 1, "Load the actual local appearance script once on every shared page."
    script = scripts[0]
    head = page.find("head")
    assert ancestry(head, script), "The early appearance script belongs in head, not the end of body."
    assert "defer" not in script.attrs and "async" not in script.attrs
    assert script.attrs.get("type", "text/javascript") in {"text/javascript", "application/javascript"}
    nodes = head.find_all()
    style = head.find("link", rel="stylesheet", href="/static/css/style.css")
    assert style is not None
    position = lambda node: next(index for index, item in enumerate(nodes) if item is node)
    assert position(script) < position(style), "Read only the recognized preference before styled first paint."
    for node in [*page.find_all("script"), *head.find_all("link", rel="stylesheet")]:
        source = node.attrs.get("src", node.attrs.get("href", ""))
        assert not urlsplit(source).scheme and not urlsplit(source).netloc


def test_local_appearance_script_is_served_as_javascript(client):
    response = client.get("/static/js/appearance.js")
    assert response.status_code == 200, "The browser needs a real appearance asset, not an HTML 404."
    assert response.mimetype in {"application/javascript", "text/javascript"}
    assert response.get_data().strip()


def test_existing_planner_preview_script_and_noscript_help_remain(client, parse_page):
    page = parse_page(client.get("/plan"))
    assert page.find("script", src="/static/js/plan.js") is not None
    fallback = page.find("noscript")
    assert fallback is not None
    assert any(word in fallback.text.casefold() for word in ("daily", "allowance", "preview"))
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/static/js/plan.js").status_code == 200


@pytest.mark.parametrize("mode", ["system", "light", "dark", "<script>invalid()</script>"])
def test_extra_appearance_post_fields_never_enter_the_authoritative_draft(
    client, submit_trip, valid_form, draft_data, mode,
):
    response = submit_trip(client, {
        **valid_form, "appearance": mode, "tripplanner.appearance": mode,
        "customer_preferences": json.dumps({"theme": mode}), "data-appearance": mode,
    })
    assert response.status_code == 303
    with client.session_transaction() as session:
        expected = deepcopy(draft_data)
        expected["version"] = 2
        expected["preferences"]["currency"] = "EUR"
        assert session["trip_draft"] == expected
        assert set(session) <= {"trip_draft", "csrf_token", "currency_context_nonce", "_flashes"}
    assert all("appearance" not in value.casefold() for value in response.headers.getlist("Set-Cookie"))


@pytest.mark.parametrize("mode", ["system", "light", "dark"])
def test_appearance_post_extras_do_not_change_save_hash_snapshot_duplicate_or_schema(
    app, client, set_draft, parse_page, snapshot_payload, mode,
):
    from snapshots import dump_snapshot

    stored = set_draft(client)
    data = reviewed_form(client, parse_page)
    original_hash = data["snapshot_fingerprint"]
    first = client.post("/itinerary/save", data=data)
    assert first.status_code == 303
    with closing(sqlite3.connect(app.config["DATABASE"])) as connection:
        before = connection.execute("SELECT * FROM saved_trips").fetchall()
    repeated = client.post("/itinerary/save", data={
        **data, "appearance": mode, "tripplanner.appearance": mode,
        "customer_preferences": json.dumps({"theme": mode}),
    })
    assert repeated.status_code == 303 and repeated.headers["Location"] == first.headers["Location"]
    assert "already saved" in parse_page(client.get(repeated.headers["Location"])).text.casefold()
    assert reviewed_form(client, parse_page)["snapshot_fingerprint"] == original_hash
    with closing(sqlite3.connect(app.config["DATABASE"])) as connection:
        assert connection.execute("SELECT * FROM saved_trips").fetchall() == before
        columns = [row[1] for row in connection.execute("PRAGMA table_info(saved_trips)")]
        assert columns == ["id", "title", "created_at", "fingerprint", "snapshot_json"]
        raw = connection.execute("SELECT snapshot_json FROM saved_trips").fetchone()[0]
        expected = deepcopy(snapshot_payload)
        expected["version"] = 2
        expected["preferences"]["currency"] = "EUR"
        assert raw == dump_snapshot(expected)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [("saved_trips",)]
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored
        assert set(session) <= {"trip_draft", "csrf_token", "currency_context_nonce", "_flashes"}


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_server_does_not_choose_or_write_an_appearance_from_query_or_cookie(client, parse_page, mode):
    client.set_cookie("tripplanner.appearance", mode)
    response = client.get(f"/plan?appearance={mode}")
    assert response.status_code == 200
    page = parse_page(response)
    assert "data-appearance" not in page.find("html").attrs
    assert all("tripplanner.appearance=" not in value for value in response.headers.getlist("Set-Cookie"))


def test_complete_server_journey_remains_usable_without_executing_any_application_script(
    app, client, submit_trip, parse_page, csrf_token,
):
    assert submit_trip(client).status_code == 303
    recommendations = client.get("/recommendations")
    assert recommendations.status_code == 200
    assert parse_page(recommendations).find("a", href="/itinerary") is not None
    data = reviewed_form(client, parse_page)
    saved = client.post("/itinerary/save", data=data)
    assert saved.status_code == 303
    saved_path = saved.headers["Location"]
    assert "103.00" in parse_page(client.get(saved_path)).text
    assert client.get("/trips").status_code == 200
    assert parse_page(client.get("/plan")).find("input", name="budget").attrs["value"] == "300.00"
    cleared = client.post("/draft/clear", data={"csrf_token": csrf_token(client)})
    assert cleared.status_code == 303
    with client.session_transaction() as session:
        assert "trip_draft" not in session
    blank = parse_page(client.get("/plan"))
    assert blank.find("input", name="budget").attrs.get("value", "") == ""
    assert client.get("/itinerary").status_code == 302
    assert "103.00" in parse_page(client.get(saved_path)).text
    with closing(sqlite3.connect(app.config["DATABASE"])) as connection:
        assert connection.execute("SELECT count(*) FROM saved_trips").fetchone()[0] == 1

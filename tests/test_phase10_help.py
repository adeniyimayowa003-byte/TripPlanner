"""Phase 10A contracts: real Flask clients, no external services or user data."""
import importlib
from pathlib import Path
import sqlite3

import pytest


@pytest.mark.parametrize("path", ["/", "/plan", "/trips", "/about"])
def test_help_navigation(client, parse_page, path):
    page = parse_page(client.get(path))
    assert page.find("a", href="/help") is not None


def test_help_is_complete_without_javascript(client, parse_page):
    response = client.get("/help")
    assert response.status_code == 200
    page = parse_page(response)
    assert len(page.find_all("h1")) == 1
    for topic in ("cities", "allowance", "gaps", "estimates", "saving", "snapshots",
                  "maps", "hosting", "native", "unavailable", "themes", "support"):
        assert page.find("section", id=topic) is not None
        assert page.find("a", href="#" + topic) is not None
    assert page.find("label", **{"for": "help-query"}) is not None
    assert page.find("form", method="get", action="/help") is not None
    assert page.find("a", href="/help").text


@pytest.mark.parametrize("query,expected", [("cookie", "saving"), ("ALLOWANCE", "allowance"),
                                          ("  maps  ", "maps"), ("Tokyo", "cities")])
def test_server_search(client, parse_page, query, expected):
    response = client.get("/help", query_string={"q": query})
    assert response.status_code == 200
    assert parse_page(response).find("section", id=expected) is not None


def test_empty_search_and_escaped_input(client, parse_page):
    response = client.get("/help", query_string={"q": '<script>alert("x")</script>'})
    assert response.status_code == 200
    assert '<script>alert("x")</script>' not in response.text
    page = parse_page(response)
    assert "No matching questions" in page.text
    assert page.find("p", role="status") is not None
    assert page.find("input", name="q").attrs["value"] == '<script>alert("x")</script>'


def test_query_is_bounded(client, parse_page):
    response = client.get("/help", query_string={"q": "x" * 1000})
    assert response.status_code == 200
    assert len(parse_page(response).find("input", name="q").attrs["value"]) <= 200


def test_help_does_not_load_catalog_or_storage_or_change_draft(app, client, monkeypatch):
    import app as web
    def forbidden(*args, **kwargs):
        pytest.fail("Help must work independently of catalog and saved storage.")
    for name in ("load_catalog", "load_destinations", "list_trips", "save_trip", "get_trip"):
        monkeypatch.setattr(web, name, forbidden)
    with client.session_transaction() as session:
        session["trip_draft"] = {"private": "stale-draft-sentinel"}
    assert client.get("/help").status_code == 200
    with client.session_transaction() as session:
        assert session["trip_draft"] == {"private": "stale-draft-sentinel"}
    assert not Path(app.config["DATABASE"]).exists()


def test_help_switch_disables_route_and_link(app, client, parse_page):
    app.config["PHASE10_HELP_ENABLED"] = False
    assert client.get("/help").status_code == 404
    assert parse_page(client.get("/")).find("a", href="/help") is None


def test_allowance_and_current_feature_truth(client, parse_page):
    response = client.get("/help")
    assert response.status_code == 200
    text = parse_page(response).text.casefold()
    for phrase in ("per person", "total", "flights", "accommodation", "transport",
                   "missing meals", "not a payment", "365", "no account recovery",
                   "no integrated ai", "self-service", "not an emergency service"):
        assert phrase in text


def test_faq_unit_content_is_versioned_and_search_does_not_mutate():
    faq = importlib.import_module("help_content")
    before = faq.search_faq("")
    assert faq.FAQ_VERSION == 2
    assert len(before) == 12
    assert len({item.id for item in before}) == 12
    assert all(item.source and item.answer and item.question for item in before)
    assert [item.id for item in faq.search_faq("cookie")] == ["saving"]
    assert faq.search_faq("no-match-zzzz") == ()
    assert faq.search_faq("") == before


def test_native_source_staging_includes_help_without_building():
    import build_windows
    import build_android
    root = Path(__file__).resolve().parents[1]
    for builder in (build_windows, build_android):
        paths = builder.application_files(root)
        assert "help_content.py" in paths
        assert "templates/help.html" in paths


def test_hosted_help_preserves_snapshot_and_foreign_denial(tmp_path):
    from hosted import create_hosted_app
    directory = tmp_path / "durable"
    directory.mkdir()
    app = create_hosted_app({"TRIPPLANNER_SECRET_KEY": "ab" * 32,
                             "TRIPPLANNER_PUBLIC_HOST": "planner.example",
                             "TRIPPLANNER_STORAGE_DIR": str(directory)})
    owner = app.test_client()
    foreign = app.test_client()
    origin = "https://planner.example"
    assert owner.get("/help", base_url=origin).status_code == 200
    # Insert synthetic unavailable historical text directly: Help must never
    # deserialize, normalize or reset even a damaged legacy snapshot.
    import hashlib
    from hosted import _serializer, VISITOR_COOKIE
    token = _serializer(app).loads(owner.get_cookie(VISITOR_COOKIE, domain="planner.example").value)
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    database = directory / "hosted-trips.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("INSERT INTO saved_trips(owner,title,created_at,fingerprint,snapshot_json) VALUES(?,?,?,?,?)",
                   (digest, "private synthetic", "2026-11-01", "a" * 64, ' { "legacy": true } '))
        before = db.execute("SELECT * FROM saved_trips").fetchall()
    response = owner.get("/help", base_url=origin)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, no-store"
    assert foreign.get("/trips/1", base_url=origin).status_code == 404
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT * FROM saved_trips").fetchall() == before

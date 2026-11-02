"""Small shared fixtures for the approved TripPlanner restart tests."""

from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal
from html.parser import HTMLParser

import pytest


@pytest.fixture(autouse=True)
def frozen_phase7_catalog_for_regressions(request, monkeypatch):
    """Keep original seven-place regression math independent of release growth.

    New release tests read the real dataset. These original test modules retain
    their prices/tags/IDs and gain explicitly fictional QA location metadata so
    new v2 live-page tests can run without inventing real addresses.
    """
    legacy_files = {
        "test_catalog.py", "test_csrf.py", "test_drafts.py", "test_home.py",
        "test_itinerary.py", "test_itinerary_flow.py", "test_money.py",
        "test_plan_form.py", "test_preferences.py", "test_recommendations.py",
        "test_saved_trips.py", "test_saved_trip_flow.py", "test_snapshots.py",
        "test_trip_flow.py", "test_appearance_flow.py", "test_appearance_script.py",
        "test_appearance_styles.py",
    }
    if request.node.path.name not in legacy_files:
        return
    from pathlib import Path
    import catalog
    import app as app_module
    import recommendations
    monkeypatch.setattr(catalog, "CATALOG_FILE", Path(__file__).with_name("fixtures") / "phase7-paris-catalog.json")
    original_load = catalog.load_catalog

    def regression_catalog():
        places = original_load()
        for place in places:
            place.setdefault("currency", "EUR")
            place.setdefault("reviewed_on", "2026-11-01")
            place.setdefault("cost_note", "Illustrative QA estimate, not live prices.")
            place.setdefault("location", {"address": "1 QA Test Street, Paris, France",
                             "source_url": "https://example.com/qa-location", "reviewed_on": "2026-11-01"})
        return places
    for module in (catalog, app_module, recommendations):
        monkeypatch.setattr(module, "load_catalog", regression_catalog)
    if hasattr(request.module, "load_catalog"):
        monkeypatch.setattr(request.module, "load_catalog", regression_catalog)


@dataclass
class Element:
    """Enough parsed HTML to check labels, links, and fields without a browser."""

    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    @property
    def text(self):
        content = " ".join(
            child.text if isinstance(child, Element) else child
            for child in self.children
        )
        return " ".join(content.split())

    def find_all(self, tag=None, **attrs):
        matches = []
        for child in self.children:
            if isinstance(child, Element):
                if (tag is None or child.tag == tag) and all(
                    key in child.attrs and child.attrs[key] == value
                    for key, value in attrs.items()
                ):
                    matches.append(child)
                matches.extend(child.find_all(tag, **attrs))
        return matches

    def find(self, tag=None, **attrs):
        return next(iter(self.find_all(tag, **attrs)), None)


class PageParser(HTMLParser):
    """Use the standard-library parser rather than matching attribute order."""

    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        element = Element(tag, dict(attrs))
        self.stack[-1].children.append(element)
        if tag not in self.VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


@pytest.fixture
def parse_page():
    def parse(response_or_html):
        html = (
            response_or_html.get_data(as_text=True)
            if hasattr(response_or_html, "get_data")
            else response_or_html
        )
        parser = PageParser()
        parser.feed(html)
        return parser.root

    return parse


@pytest.fixture
def app(tmp_path):
    from app import create_app

    return create_app({
        "TESTING": True,
        "SECRET_KEY": "tripplanner-test-secret",
        "DATABASE": str(tmp_path / "storage" / "trips.sqlite3"),
        "DATABASE_TIMEOUT": 0.05,
    })


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def client_factory(app):
    return app.test_client


@pytest.fixture
def valid_form():
    return {
        "destination": "Paris, France",
        "days": "3",
        "budget": "300.00",
        "interests": ["food", "history"],
        "pace": "relaxed",
        "family_friendly": "on",
    }


@pytest.fixture
def normalized_preferences():
    return {
        "destination": "Paris, France",
        "days": 3,
        "budget": Decimal("300.00"),
        "interests": ["food", "history"],
        "pace": "relaxed",
        "family_friendly": True,
    }


@pytest.fixture
def draft_data():
    return {
        "version": 1,
        "preferences": {
            "destination": "Paris, France",
            "days": 3,
            "budget": "300.00",
            "interests": ["food", "history"],
            "pace": "relaxed",
            "family_friendly": True,
        },
    }


@pytest.fixture
def set_draft(draft_data):
    """Seed a documented session contract without calling missing feature code."""
    def seed(browser, data=None):
        stored = deepcopy(draft_data if data is None else data)
        with browser.session_transaction() as session:
            session["trip_draft"] = stored
        return stored

    return seed


@pytest.fixture
def csrf_token(parse_page):
    def get_token(browser, path="/plan"):
        response = browser.get(path)
        assert response.status_code == 200
        token = parse_page(response).find("input", name="csrf_token")
        assert token is not None, "The form must provide a session-bound CSRF token."
        assert token.attrs.get("type") == "hidden"
        assert token.attrs.get("value"), "The form token must not be empty."
        return token.attrs["value"]

    return get_token


@pytest.fixture
def submit_trip(csrf_token, valid_form):
    def submit(browser, data=None, *, follow_redirects=False):
        form = deepcopy(valid_form if data is None else data)
        form["csrf_token"] = csrf_token(browser)
        page = PageParser()
        page.feed(browser.get("/plan").get_data(as_text=True))
        context = page.root.find("input", name="currency_context")
        if context is not None:
            form["currency_context"] = context.attrs["value"]
        return browser.post("/plan", data=form, follow_redirects=follow_redirects)

    return submit


@pytest.fixture
def make_place():
    def make(
        *, id="sample-place", name="Sample Place", destination="Paris, France",
        interest_tags=("history",), preference_tags=(), estimated_cost=0,
        category="activity", description="An illustrative test place.",
        source_url="https://example.com/place",
    ):
        return {
            "id": id,
            "name": name,
            "destination": destination,
            "category": category,
            "interest_tags": list(interest_tags),
            "preference_tags": list(preference_tags),
            "estimated_cost": estimated_cost,
            "description": description,
            "source_url": source_url,
            "currency": "EUR", "reviewed_on": "2026-11-01",
            "cost_note": "Illustrative QA estimate, not live prices.",
            "location": {"address": "1 QA Test Street, " + destination,
                         "source_url": "https://example.com/qa-location", "reviewed_on": "2026-11-01"},
        }

    return make


@pytest.fixture
def sample_catalog(make_place):
    return [
        make_place(
            id="paris-garden", name="Sample Garden",
            interest_tags=("nature", "history"),
            preference_tags=("relaxed", "family-friendly"),
        ),
        make_place(
            id="paris-cafe", name="Sample Cafe", category="restaurant",
            interest_tags=("food", "culture"), estimated_cost=18,
        ),
        make_place(
            id="kyoto-temple", name="Sample Temple", destination="Kyoto, Japan",
            category="attraction", interest_tags=("history", "culture"),
            preference_tags=("active",), estimated_cost=5,
        ),
    ]


@pytest.fixture
def snapshot_factory(normalized_preferences):
    """Independent version-1 data, built only from the working Phase 5 APIs.

    This fixture deliberately does not import the future snapshot module.
    Convert catalog float costs via their text, never binary arithmetic.
    """
    from catalog import load_catalog
    from itinerary import generate_itinerary
    from money import daily_allowance
    from recommendations import recommend_trip_ideas

    def money_strings(value):
        if isinstance(value, Decimal):
            return format(value, ".2f")
        if isinstance(value, dict):
            result = {key: money_strings(item) for key, item in value.items()}
            if "estimated_cost" in value:
                result["estimated_cost"] = format(Decimal(str(value["estimated_cost"])), ".2f")
            return result
        if isinstance(value, list):
            return [money_strings(item) for item in value]
        return value

    def make(preferences=None, catalog=None):
        preferences = deepcopy(normalized_preferences if preferences is None else preferences)
        places = deepcopy(load_catalog() if catalog is None else catalog)
        items, notices = recommend_trip_ideas(preferences, catalog=places)
        return money_strings({
            "version": 1,
            "currency": "EUR",
            "cost_note": "Illustrative per-person estimates for a class project; these are not live prices.",
            "budget_note": "Activities and food allowance per person; excludes flights, accommodation, and transport.",
            "preferences": preferences,
            "daily_budget": daily_allowance(preferences["budget"], preferences["days"]),
            "recommendations": items,
            "recommendation_notices": notices,
            "itinerary": generate_itinerary(preferences, catalog=places),
        })

    return make


@pytest.fixture
def snapshot_payload(snapshot_factory):
    return snapshot_factory()

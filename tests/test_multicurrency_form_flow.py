"""Real server-form journeys with QA data; no JavaScript or real collection."""

from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest

from phase8_helpers import CITY_PROFILES, SCALE, amount_text, profile_for, synthetic_catalog
from phase8_form_helpers import (
    assert_visible_amount, context_fields, form_for, independent_draft,
    inspect_context, legacy_v1_draft,
)


@pytest.fixture
def city_browser(app, monkeypatch):
    import app as app_module

    places = synthetic_catalog()
    monkeypatch.setattr(app_module, "load_catalog", lambda: deepcopy(places))
    return app.test_client()


def post_form(browser, profile, fields, **changes):
    form = form_for(profile, **changes)
    for key, value in fields.items():
        form[key] = value
    return browser.post("/plan", data=form)


def start_trip(browser, profile, parse_page):
    fields = context_fields(browser.get("/plan"), parse_page)
    response = post_form(browser, profile, fields)
    assert response.status_code == 303 and urlsplit(response.headers["Location"]).path == "/recommendations"
    with browser.session_transaction() as browser_session:
        assert browser_session["trip_draft"] == independent_draft(profile)
        return deepcopy(browser_session["trip_draft"])


def assert_pending_form(app, browser, response, code, parse_page):
    fields = context_fields(response, parse_page)
    assert inspect_context(app, browser, fields["currency_context"]) == {
        "version": 1, "currency": code, "confirmation_required": True,
    }
    page = parse_page(response)
    control = page.find("input", name="confirm_currency_change")
    assert control is not None and control.attrs.get("type") == "checkbox"
    assert control.attrs.get("id") == "confirm-currency-change" and control.attrs.get("value") == "on"
    label = page.find("label", **{"for": "confirm-currency-change"})
    assert label is not None and code in label.text
    assert page.find(role="alert") is not None
    return fields, page


def test_form_token_reader_and_exact_amount_checker_have_independent_positive_and_negative_controls(parse_page):
    html = '<form action="/plan"><input type="hidden" name="csrf_token" value="csrf-example"><input type="hidden" name="currency_context" value="context-example"></form>'
    assert context_fields(html, parse_page) == {"csrf_token": "csrf-example", "currency_context": "context-example"}
    for broken in ('<form action="/plan"></form>', html.replace('value="context-example"', 'value="csrf-example"')):
        with pytest.raises(AssertionError):
            context_fields(broken, parse_page)
    assert_visible_amount("JPY 10,000 per day", "10000")
    with pytest.raises(AssertionError):
        assert_visible_amount("JPY 10000.00 per day", "10000")


def test_city_browser_fixture_exposes_qa_choices_with_isolated_absent_storage(city_browser, app, parse_page, tmp_path):
    page = parse_page(city_browser.get("/plan"))
    options = page.find("select", name="destination")
    assert options is not None
    assert {profile["name"] for profile in CITY_PROFILES} <= {
        option.attrs.get("value") for option in options.find_all("option")
    }
    database = Path(app.config["DATABASE"])
    assert database.is_relative_to(tmp_path) and not database.exists()
    assert len(synthetic_catalog()) == 48
    assert all(place["name"].startswith("QA ") for place in synthetic_catalog())


def test_initial_form_has_a_neutral_signed_currency_context_separate_from_csrf(city_browser, app, parse_page):
    response = city_browser.get("/plan")
    fields = context_fields(response, parse_page)
    assert inspect_context(app, city_browser, fields["currency_context"]) == {
        "version": 1, "currency": None, "confirmation_required": False,
    }
    help_text = parse_page(response).find(id="budget-help").text
    assert re.search(r"\b(?:EUR|NGN|GBP|USD|JPY|ZAR)\b", help_text) is None
    assert "destination" in help_text.casefold()


def test_currency_review_keeps_raw_two_decimal_currency_answers_before_acceptance(city_browser, app, parse_page):
    start_trip(city_browser, profile_for("JPY"), parse_page)
    fields = context_fields(city_browser.get("/plan"), parse_page)
    response = post_form(city_browser, profile_for("GBP"), fields, budget="300", days=" 3 ", pace=" RELAXED ")
    _, page = assert_pending_form(app, city_browser, response, "GBP", parse_page)
    assert page.find("input", name="budget").attrs["value"] == "300"
    assert page.find("input", name="days").attrs["value"] == " 3 "


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_first_city_submission_creates_v2_native_currency_draft_and_consistent_results(city_browser, profile, parse_page):
    fields = context_fields(city_browser.get("/plan"), parse_page)
    response = post_form(city_browser, profile, fields, currency="forged-label")
    assert response.status_code == 303
    assert urlsplit(response.headers["Location"]).path == "/recommendations"
    with city_browser.session_transaction() as browser_session:
        stored = deepcopy(browser_session["trip_draft"])
    assert stored == independent_draft(profile)
    assert "csrf_token" not in stored["preferences"] and "currency_context" not in stored["preferences"]
    page = parse_page(city_browser.get("/recommendations"))
    assert profile["name"] in page.text and profile["currency"] in page.text
    assert_visible_amount(page.text, amount_text(Decimal(300) * SCALE[profile["currency"]], profile["currency"]))
    assert_visible_amount(page.text, amount_text(Decimal(100) * SCALE[profile["currency"]], profile["currency"]))
    if profile["currency"] != "EUR":
        assert "EUR" not in page.text


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_edit_form_preserves_city_native_amount_bounds_and_rendered_currency_context(city_browser, app, profile, parse_page):
    with city_browser.session_transaction() as browser_session:
        browser_session["trip_draft"] = independent_draft(profile)
    response = city_browser.get("/plan")
    fields = context_fields(response, parse_page)
    assert inspect_context(app, city_browser, fields["currency_context"]) == {
        "version": 1, "currency": profile["currency"], "confirmation_required": False,
    }
    page = parse_page(response)
    budget = page.find("input", name="budget")
    assert budget.attrs["value"] == independent_draft(profile)["preferences"]["budget"]
    assert budget.attrs["min"] == budget.attrs["step"] == ("1" if profile["currency"] == "JPY" else "0.01")
    assert Decimal(budget.attrs["max"]) == Decimal(1000000 if profile["currency"] == "EUR" else 1000000000)
    assert profile["currency"] in page.find(id="budget-help").text
    assert "selected" in page.find("option", value=profile["name"]).attrs
    assert page.find("input", name="confirm_currency_change") is None


@pytest.mark.parametrize("premature_ack", ["", "on"])
def test_changing_currency_first_redisplays_review_and_does_not_accept_a_premature_checkbox(city_browser, app, parse_page, premature_ack):
    old = start_trip(city_browser, profile_for("EUR"), parse_page)
    fields = context_fields(city_browser.get("/plan"), parse_page)
    response = post_form(city_browser, profile_for("JPY"), fields, budget="300", confirm_currency_change=premature_ack)
    _, page = assert_pending_form(app, city_browser, response, "JPY", parse_page)
    assert page.find("input", name="budget").attrs["value"] == "300"
    assert "selected" in page.find("option", value="Tokyo, Japan").attrs
    with city_browser.session_transaction() as browser_session:
        assert browser_session["trip_draft"] == old


def test_pending_currency_change_requires_an_explicit_checkbox_and_keeps_other_answers(city_browser, app, parse_page):
    old = start_trip(city_browser, profile_for("EUR"), parse_page)
    fields = context_fields(city_browser.get("/plan"), parse_page)
    review = post_form(city_browser, profile_for("JPY"), fields, budget="300")
    pending, _ = assert_pending_form(app, city_browser, review, "JPY", parse_page)
    response = post_form(city_browser, profile_for("JPY"), pending, budget="300")
    _, page = assert_pending_form(app, city_browser, response, "JPY", parse_page)
    control = page.find("input", name="confirm_currency_change")
    assert control.attrs.get("aria-invalid") == "true"
    assert page.find("input", name="days").attrs["value"] == "3"
    assert "checked" in page.find("input", name="interests", value="food").attrs
    with city_browser.session_transaction() as browser_session:
        assert browser_session["trip_draft"] == old


def test_confirmed_matching_review_accepts_an_explicit_native_amount_without_conversion(city_browser, app, parse_page):
    start_trip(city_browser, profile_for("EUR"), parse_page)
    fields = context_fields(city_browser.get("/plan"), parse_page)
    review = post_form(city_browser, profile_for("JPY"), fields, budget="300")
    pending, _ = assert_pending_form(app, city_browser, review, "JPY", parse_page)
    response = post_form(city_browser, profile_for("JPY"), pending, budget="450", confirm_currency_change="on")
    assert response.status_code == 303 and urlsplit(response.headers["Location"]).path == "/recommendations"
    with city_browser.session_transaction() as browser_session:
        assert browser_session["trip_draft"]["version"] == 2
        assert browser_session["trip_draft"]["preferences"]["currency"] == "JPY"
        assert browser_session["trip_draft"]["preferences"]["budget"] == "450"


def test_changing_the_target_of_a_pending_review_requires_a_fresh_target_confirmation(city_browser, app, parse_page):
    old = start_trip(city_browser, profile_for("EUR"), parse_page)
    fields = context_fields(city_browser.get("/plan"), parse_page)
    review = post_form(city_browser, profile_for("JPY"), fields, budget="300")
    pending, _ = assert_pending_form(app, city_browser, review, "JPY", parse_page)
    response = post_form(city_browser, profile_for("GBP"), pending, budget="300", confirm_currency_change="on")
    assert_pending_form(app, city_browser, response, "GBP", parse_page)
    with city_browser.session_transaction() as browser_session:
        assert browser_session["trip_draft"] == old


def test_same_currency_edits_can_succeed_without_a_change_confirmation(city_browser, parse_page):
    start_trip(city_browser, profile_for("EUR"), parse_page)
    fields = context_fields(city_browser.get("/plan"), parse_page)
    response = post_form(city_browser, profile_for("EUR"), fields, budget="450.00")
    assert response.status_code == 303
    with city_browser.session_transaction() as browser_session:
        assert browser_session["trip_draft"]["preferences"]["currency"] == "EUR"
        assert browser_session["trip_draft"]["preferences"]["budget"] == "450.00"


def test_other_validation_errors_cannot_silently_clear_a_pending_currency_review(city_browser, app, parse_page):
    old = start_trip(city_browser, profile_for("EUR"), parse_page)
    fields = context_fields(city_browser.get("/plan"), parse_page)
    review = post_form(city_browser, profile_for("JPY"), fields, budget="300")
    pending, _ = assert_pending_form(app, city_browser, review, "JPY", parse_page)
    response = post_form(city_browser, profile_for("JPY"), pending, days="15", budget="300", confirm_currency_change="on")
    _, page = assert_pending_form(app, city_browser, response, "JPY", parse_page)
    assert page.find("input", name="days").attrs["value"] == "15"
    assert page.find("input", name="days").attrs["aria-invalid"] == "true"
    with city_browser.session_transaction() as browser_session:
        assert browser_session["trip_draft"] == old


def test_a_legacy_paris_edit_has_explicit_eur_context_without_rewriting_the_stored_v1_draft(city_browser, app, parse_page):
    old = legacy_v1_draft()
    with city_browser.session_transaction() as browser_session:
        browser_session["trip_draft"] = deepcopy(old)
    fields = context_fields(city_browser.get("/plan"), parse_page)
    assert inspect_context(app, city_browser, fields["currency_context"]) == {
        "version": 1, "currency": "EUR", "confirmation_required": False,
    }
    with city_browser.session_transaction() as browser_session:
        assert browser_session["trip_draft"] == old


@pytest.mark.parametrize("field,value", [("days", "15"), ("budget", "300.50"), ("pace", "not-available")])
def test_first_city_validation_errors_keep_raw_answers_and_show_correct_currency(city_browser, app, parse_page, field, value):
    fields = context_fields(city_browser.get("/plan"), parse_page)
    form = form_for(profile_for("JPY"), **{field: value})
    for name, token in fields.items():
        form[name] = token
    response = city_browser.post("/plan", data=form)
    updated = context_fields(response, parse_page)
    page = parse_page(response)
    assert "JPY" in page.find(id="budget-help").text
    control = page.find("input", name=field) or page.find("select", name=field)
    assert control.attrs.get("aria-invalid") == "true"
    assert page.find("input", name="budget").attrs["value"] == form["budget"]
    assert page.find("input", name="days").attrs["value"] == form["days"]
    assert "checked" in page.find("input", name="interests", value="food").attrs
    assert inspect_context(app, city_browser, updated["currency_context"])["currency"] == "JPY"
    with city_browser.session_transaction() as browser_session:
        assert "trip_draft" not in browser_session


@pytest.mark.parametrize("bad", [None, "forged-context", '<script>forged</script>'])
def test_missing_or_forged_context_is_rejected_even_with_valid_csrf_and_keeps_the_draft(city_browser, csrf_token, bad):
    old = legacy_v1_draft()
    with city_browser.session_transaction() as browser_session:
        browser_session["trip_draft"] = deepcopy(old)
    form = form_for(profile_for("EUR"), budget="400.00")
    form["csrf_token"] = csrf_token(city_browser)
    if bad is not None:
        form["currency_context"] = bad
    response = city_browser.post("/plan", data=form)
    assert response.status_code == 400
    with city_browser.session_transaction() as browser_session:
        assert browser_session["trip_draft"] == old


def test_invalid_context_is_checked_before_catalog_or_storage_access(city_browser, csrf_token, app, monkeypatch):
    import app as app_module

    token = csrf_token(city_browser)

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid currency context must be rejected before travel-data or storage access.")

    monkeypatch.setattr(app_module, "load_catalog", forbidden)
    monkeypatch.setattr(app_module, "save_trip", forbidden)
    form = form_for(profile_for("EUR"), csrf_token=token, currency_context="forged")
    assert city_browser.post("/plan", data=form).status_code == 400
    assert not Path(app.config["DATABASE"]).exists()


def test_a_valid_currency_context_cannot_replace_csrf_protection(city_browser, parse_page):
    fields = context_fields(city_browser.get("/plan"), parse_page)
    fields["csrf_token"] = fields["currency_context"]
    assert post_form(city_browser, profile_for("EUR"), fields).status_code == 400


def test_currency_context_cannot_be_replayed_in_another_browser_with_valid_csrf(city_browser, app, parse_page):
    first = context_fields(city_browser.get("/plan"), parse_page)
    other = app.test_client()
    second = context_fields(other.get("/plan"), parse_page)
    second["currency_context"] = first["currency_context"]
    assert post_form(other, profile_for("EUR"), second).status_code == 400
    with other.session_transaction() as browser_session:
        assert "trip_draft" not in browser_session

"""Form integration contracts, including real form tokens and error recovery."""

from urllib.parse import urlsplit
from decimal import Decimal

import pytest


def test_plan_page_shows_catalog_destinations_and_interests(client, parse_page):
    response = client.get("/plan")
    page = parse_page(response)

    assert response.status_code == 200
    assert page.find("option", value="Paris, France") is not None
    assert page.find("input", name="interests", value="food") is not None
    assert page.find("input", name="interests", value="history") is not None


def test_pace_options_follow_the_current_destination_catalog(client, parse_page):
    page = parse_page(client.get("/plan"))
    pace = page.find("select", name="pace")

    assert pace is not None
    assert {option.attrs.get("value") for option in pace.find_all("option")} == {"", "relaxed"}


def test_budget_meaning_and_input_bounds_are_clear(client, parse_page):
    page = parse_page(client.get("/plan"))
    text = page.text.casefold()
    budget = page.find("input", name="budget")

    assert "activities" in text and "food" in text and "per person" in text
    assert "eur" in text
    assert all(word in text for word in ("flights", "accommodation", "transport"))
    assert budget is not None
    assert budget.attrs.get("min") == "0.01"
    assert Decimal(budget.attrs.get("max", "0")) == Decimal("1000000.00")
    assert budget.attrs.get("step") == "0.01"


def test_preferences_use_a_real_server_form_and_clear_submit_action(client, parse_page):
    page = parse_page(client.get("/plan"))
    form = page.find("form", action="/plan")

    assert form is not None
    assert form.attrs.get("method", "").casefold() == "post"
    button = form.find("button", type="submit")
    assert button is not None and "find my trip ideas" in button.text.casefold()


def test_form_provides_a_nonempty_hidden_token(client, csrf_token):
    assert csrf_token(client)


def test_form_inputs_have_associated_labels(client, parse_page):
    page = parse_page(client.get("/plan"))

    for name in ("destination", "days", "budget", "pace", "family_friendly"):
        control = page.find("input", name=name) or page.find("select", name=name)
        assert control is not None
        label = page.find("label", **{"for": control.attrs.get("id")})
        assert label is not None and label.text
    interest_inputs = page.find_all("input", name="interests")
    assert interest_inputs
    labels = page.find_all("label")
    for control in interest_inputs:
        explicit = page.find("label", **{"for": control.attrs.get("id")})
        wrapped = any(control in label.find_all("input") and label.text for label in labels)
        assert wrapped or (explicit is not None and explicit.text)


def test_valid_submission_redirects_and_stores_only_normalized_draft(client, submit_trip):
    response = submit_trip(client)

    assert response.status_code == 303
    assert urlsplit(response.headers["Location"]).path == "/recommendations"
    with client.session_transaction() as session:
        stored = session["trip_draft"]
        assert stored["version"] == 2
        assert stored["preferences"]["currency"] == "EUR"
        assert stored["preferences"]["budget"] == "300.00"
        assert stored["preferences"]["days"] == 3
        assert stored["preferences"]["interests"] == ["food", "history"]
        assert stored["preferences"]["pace"] == "relaxed"
        assert stored["preferences"]["family_friendly"] is True
        assert "csrf_token" not in stored["preferences"]


def test_invalid_submission_associates_error_and_preserves_answers(
    client, valid_form, submit_trip, parse_page,
):
    valid_form["days"] = "15"
    response = submit_trip(client, valid_form)
    page = parse_page(response)

    assert response.status_code == 200
    assert page.find(role="alert") is not None
    days = page.find("input", name="days")
    assert days is not None and days.attrs.get("value") == "15"
    assert days.attrs.get("aria-invalid") == "true"
    described_ids = days.attrs.get("aria-describedby", "").split()
    assert described_ids
    assert any(
        page.find(id=error_id) is not None and page.find(id=error_id).text
        for error_id in described_ids
    )
    assert "selected" in page.find("option", value="Paris, France").attrs
    assert "selected" in page.find("option", value="relaxed").attrs
    assert page.find("input", name="budget").attrs.get("value") == "300.00"
    for interest in ("food", "history"):
        assert "checked" in page.find("input", name="interests", value=interest).attrs
    assert "checked" in page.find("input", name="family_friendly").attrs
    with client.session_transaction() as session:
        assert "trip_draft" not in session


def test_malformed_days_associates_the_error_rather_than_just_range_help(
    client, valid_form, submit_trip, parse_page,
):
    valid_form["days"] = "tomorrow"
    response = submit_trip(client, valid_form)
    page = parse_page(response)

    assert response.status_code == 200
    days = page.find("input", name="days")
    assert days is not None and days.attrs.get("aria-invalid") == "true"
    error_ids = (
        days.attrs.get("aria-describedby", "") + " "
        + days.attrs.get("aria-errormessage", "")
    ).split()
    associated_text = " ".join(
        page.find(id=node_id).text for node_id in error_ids
        if page.find(id=node_id) is not None
    ).casefold()
    assert "whole" in associated_text or "integer" in associated_text


@pytest.mark.parametrize("field,value", [("days", "0"), ("budget", "3e2"), ("pace", "active")])
def test_invalid_field_does_not_lose_other_answers(
    client, valid_form, submit_trip, parse_page, field, value,
):
    valid_form[field] = value
    page = parse_page(submit_trip(client, valid_form))

    assert page.find(role="alert") is not None
    assert "selected" in page.find("option", value="Paris, France").attrs
    assert "checked" in page.find("input", name="interests", value="food").attrs
    if field != "days":
        assert page.find("input", name="days").attrs.get("value") == "3"
    if field != "budget":
        assert page.find("input", name="budget").attrs.get("value") == "300.00"


def test_untrusted_submitted_values_are_escaped(client, valid_form, submit_trip):
    attack = '<script>alert("untrusted")</script>'
    valid_form["destination"] = attack
    response = submit_trip(client, valid_form)

    assert response.status_code == 200
    assert attack not in response.get_data(as_text=True)
    assert "&lt;script&gt;" in response.get_data(as_text=True)


def test_daily_preview_enhancement_has_local_script_and_nojs_explanation(client, parse_page):
    page = parse_page(client.get("/plan"))
    scripts = [
        node.attrs["src"] for node in page.find_all("script")
        if node.attrs.get("src", "").startswith("/static/")
    ]

    assert scripts, "Provide the local daily-preview enhancement."
    assert all(client.get(source).status_code == 200 for source in scripts)
    fallback = page.find("noscript")
    assert fallback is not None
    assert "daily" in fallback.text.casefold() or "allowance" in fallback.text.casefold()

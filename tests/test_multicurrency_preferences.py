"""Test-first destination-owned currency and raw-answer recovery contracts."""

from copy import deepcopy
from decimal import Decimal
import json

import pytest

from phase8_helpers import CITY_PROFILES, SCALE, profile_for, qa_preferences, synthetic_catalog
from phase8_form_helpers import form_for, independent_draft, legacy_v1_draft, raw_preferences


def validate(form, places=None, profiles=None):
    from preferences import validate_trip_preferences

    return validate_trip_preferences(
        form, catalog=synthetic_catalog() if places is None else places,
        profiles=deepcopy(list(CITY_PROFILES)) if profiles is None else profiles,
    )


def test_independent_form_and_draft_examples_have_native_money_and_frozen_legacy_shape():
    for profile in CITY_PROFILES:
        form = form_for(profile)
        stored = independent_draft(profile)
        assert form.getlist("interests") == ["food", "history"]
        assert stored["version"] == 2 and stored["preferences"]["currency"] == profile["currency"]
        assert json.loads(json.dumps(stored)) == stored
        amount = Decimal(stored["preferences"]["budget"])
        assert amount == Decimal(300) * SCALE[profile["currency"]]
        assert amount.as_tuple().exponent == (0 if profile["currency"] == "JPY" else -2)
        assert raw_preferences(form)["budget"] == stored["preferences"]["budget"]
    old = legacy_v1_draft()
    assert old["version"] == 1 and "currency" not in old["preferences"]
    old["preferences"]["interests"].append("mutated test copy")
    assert legacy_v1_draft()["preferences"]["interests"] == ["food", "history"]


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_each_city_normalizes_to_its_authoritative_currency_and_exact_native_budget(profile):
    form = form_for(profile, destination="  " + profile["name"].upper() + "  ")
    values, errors = validate(form)
    assert errors == {} and values == qa_preferences(profile)
    assert type(values["budget"]) is Decimal
    assert values["budget"].as_tuple().exponent == (0 if profile["currency"] == "JPY" else -2)


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
@pytest.mark.parametrize("forged", ["XXX", "USD", "<script>JPY</script>"])
def test_a_submitted_currency_label_cannot_override_the_city_profile(profile, forged):
    values, errors = validate(form_for(profile, currency=forged))
    assert errors == {} and values["currency"] == profile["currency"]
    assert set(values) == set(qa_preferences(profile))


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
@pytest.mark.parametrize("boundary", ["minimum", "maximum"])
def test_form_budget_boundaries_are_native_units(profile, boundary):
    code = profile["currency"]
    raw = ("1" if code == "JPY" else "0.01") if boundary == "minimum" else (
        "1000000.00" if code == "EUR" else "1000000000" if code == "JPY" else "1000000000.00"
    )
    values, errors = validate(form_for(profile, budget=raw))
    assert errors == {} and values["budget"] == Decimal(raw)
    assert values["currency"] == code


@pytest.mark.parametrize("code,raw", [("JPY", "300.00"), ("JPY", "300.50"), ("USD", "300.001"), ("NGN", "3e5"), ("EUR", "1000000.01")])
def test_native_amount_errors_keep_the_original_text_and_explain_the_currency(code, raw):
    form = form_for(profile_for(code), budget=raw)
    values, errors = validate(form)
    assert "budget" in errors and errors["budget"].strip()
    assert code in errors["budget"] or (code == "EUR" and "euro" in errors["budget"].casefold())
    assert values == raw_preferences(form)


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
@pytest.mark.parametrize("field,value", [("days", " 15 "), ("budget", "invalid amount"), ("pace", "unavailable-pace")])
def test_invalid_answers_preserve_every_raw_preference_without_mutating_inputs(profile, field, value):
    form = form_for(profile, **{field: value})
    places = synthetic_catalog()
    profiles = deepcopy(list(CITY_PROFILES))
    before = deepcopy((form, places, profiles))
    values, errors = validate(form, places, profiles)
    assert field in errors and values == raw_preferences(form)
    assert (form, places, profiles) == before


@pytest.mark.parametrize("case", ["unknown-city", "profile-without-places", "places-without-profile"])
def test_a_destination_needs_both_a_profile_and_real_available_catalog_records(case):
    profile = profile_for("JPY")
    places = synthetic_catalog()
    profiles = deepcopy(list(CITY_PROFILES))
    form = form_for(profile)
    if case == "unknown-city":
        form["destination"] = "Atlantis"
    elif case == "profile-without-places":
        places = [place for place in places if place["destination"] != profile["name"]]
    else:
        profiles = [item for item in profiles if item["id"] != profile["id"]]
    values, errors = validate(form, places, profiles)
    assert "destination" in errors and values == raw_preferences(form)


def test_interest_and_pace_choices_are_derived_from_the_selected_city_only():
    profile = profile_for("JPY")
    places = synthetic_catalog()
    for place in places:
        if place["destination"] == profile["name"]:
            place["interest_tags"] = ["nature"]
            place["preference_tags"] = ["active"]
    good = form_for(profile, interests=["nature"], pace="active")
    values, errors = validate(good, places)
    assert errors == {} and values["interests"] == ["nature"] and values["pace"] == "active"
    raw = form_for(profile, interests=["food"], pace="relaxed")
    values, errors = validate(raw, places)
    assert {"interests", "pace"} <= errors.keys() and values == raw_preferences(raw)

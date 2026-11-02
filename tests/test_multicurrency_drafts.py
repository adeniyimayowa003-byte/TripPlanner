"""Version-2 current drafts and explicit recovery of genuine v1 Paris data."""

from copy import deepcopy
from decimal import Decimal
import json

import pytest

from phase8_helpers import CITY_PROFILES, profile_for, qa_preferences, synthetic_catalog
from phase8_form_helpers import independent_draft, legacy_v1_draft


def load(stored, places=None):
    from drafts import load_draft

    return load_draft(stored, catalog=synthetic_catalog() if places is None else places,
                      profiles=deepcopy(list(CITY_PROFILES)))


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_new_currency_bearing_preferences_serialize_to_the_independent_v2_contract(profile):
    from drafts import serialize_draft

    preferences = qa_preferences(profile)
    before = deepcopy(preferences)
    stored = serialize_draft(preferences)
    assert stored == independent_draft(profile)
    assert json.loads(json.dumps(stored)) == stored and preferences == before
    stored["preferences"]["interests"].append("changed returned copy")
    assert preferences == before


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_independent_v2_draft_loads_exact_current_preferences_without_mutating_data(profile):
    stored = independent_draft(profile)
    places = synthetic_catalog()
    before = deepcopy((stored, places))
    restored = load(stored, places)
    assert restored == qa_preferences(profile) and type(restored["budget"]) is Decimal
    assert (stored, places) == before


@pytest.mark.parametrize("field,value", [
    ("currency", None), ("currency", "EUR"), ("currency", "XXX"),
    ("budget", "30000.00"), ("budget", "0"), ("budget", "1000000001"),
    ("budget", 30000), ("days", True), ("days", 15),
    ("family_friendly", "on"), ("interests", ["unknown-interest"]),
    ("pace", "unavailable-pace"), ("destination", "Atlantis"),
])
def test_bad_v2_fields_are_recoverable_only_after_a_valid_control_loads(field, value):
    stored = independent_draft(profile_for("JPY"))
    assert load(stored) == qa_preferences(profile_for("JPY"))
    stored["preferences"][field] = value
    before = deepcopy(stored)
    assert load(stored) is None and stored == before


@pytest.mark.parametrize("field", ["destination", "currency", "days", "budget", "interests", "pace", "family_friendly"])
def test_v2_draft_missing_a_required_field_is_recoverable(field):
    stored = independent_draft(profile_for("USD"))
    assert load(stored) is not None
    del stored["preferences"][field]
    assert load(stored) is None


@pytest.mark.parametrize("version", [None, True, 2.0, "2", 0, 3, 99])
def test_draft_version_is_a_supported_integer_not_a_coercion(version):
    stored = independent_draft(profile_for("GBP"))
    assert load(stored) is not None
    stored["version"] = version
    assert load(stored) is None


def test_genuine_v1_paris_draft_loads_explicit_eur_without_rewriting_original_data():
    stored = legacy_v1_draft()
    before = deepcopy(stored)
    assert load(stored) == qa_preferences(profile_for("EUR"))
    assert stored == before and stored["version"] == 1 and "currency" not in stored["preferences"]


@pytest.mark.parametrize("city", ["Tokyo, Japan", "Kyoto, Japan", "Atlantis"])
def test_v1_unknown_or_foreign_city_is_not_assigned_a_guessed_currency(city):
    stored = legacy_v1_draft()
    assert load(stored) is not None
    stored["preferences"]["destination"] = city
    assert load(stored) is None


def test_v2_draft_revalidates_current_city_options_instead_of_trusting_old_tags():
    profile = profile_for("JPY")
    stored = independent_draft(profile)
    places = synthetic_catalog()
    assert load(stored, places) is not None
    for place in places:
        if place["destination"] == profile["name"]:
            place["interest_tags"] = ["shopping"]
    assert load(stored, places) is None

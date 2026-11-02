"""A current draft must be safe to serialize and revalidate against today's catalog."""

from copy import deepcopy
from decimal import Decimal
import json

import pytest


def stored_draft(**changes):
    preferences = {
        "destination": "Paris, France",
        "days": 3,
        "budget": "300.00",
        "interests": ["food", "history"],
        "pace": "relaxed",
        "family_friendly": True,
    }
    preferences.update(changes)
    return {"version": 1, "preferences": preferences}


def load(stored, catalog):
    from drafts import load_draft

    return load_draft(stored, catalog=catalog)


def test_serialization_produces_only_versioned_json_safe_preferences(normalized_preferences):
    from drafts import serialize_draft

    stored = serialize_draft(normalized_preferences)

    assert stored == stored_draft()
    assert json.loads(json.dumps(stored)) == stored
    assert type(stored["version"]) is int
    assert type(stored["preferences"]["days"]) is int
    assert type(stored["preferences"]["family_friendly"]) is bool
    assert isinstance(stored["preferences"]["budget"], str)


@pytest.mark.parametrize("amount", [Decimal("0.01"), Decimal("300"), Decimal("300.5"), Decimal("1000000.00")])
def test_serialized_budget_always_preserves_two_decimal_places(normalized_preferences, amount):
    from drafts import serialize_draft

    stored = serialize_draft({**normalized_preferences, "budget": amount})

    assert stored["preferences"]["budget"] == format(amount, ".2f")


def test_json_round_trip_restores_decimal_preferences(normalized_preferences, sample_catalog):
    from drafts import serialize_draft

    encoded = json.dumps(serialize_draft(normalized_preferences))
    restored = load(json.loads(encoded), sample_catalog)

    assert restored == normalized_preferences
    assert isinstance(restored["budget"], Decimal)


def test_loaded_supported_names_are_canonical_and_interests_are_unique(sample_catalog):
    stored = stored_draft(
        destination="  PARIS, FRANCE  ",
        interests=[" FOOD ", "history", "food"],
        pace=" RELAXED ",
    )

    restored = load(stored, sample_catalog)

    assert restored["destination"] == "Paris, France"
    assert restored["interests"] == ["food", "history"]
    assert restored["pace"] == "relaxed"
    assert restored["budget"] == Decimal("300.00")


def test_loading_and_serializing_do_not_mutate_their_arguments(normalized_preferences, sample_catalog):
    from drafts import serialize_draft

    original_preferences = deepcopy(normalized_preferences)
    stored = stored_draft()
    original_stored = deepcopy(stored)
    original_catalog = deepcopy(sample_catalog)

    serialize_draft(normalized_preferences)
    load(stored, sample_catalog)

    assert normalized_preferences == original_preferences
    assert stored == original_stored
    assert sample_catalog == original_catalog


@pytest.mark.parametrize(
    "stored",
    [
        None, "invalid", [], 1, True, {},
        {"preferences": {}},
        {"version": 1},
        {"version": 1, "preferences": None},
        {"version": 1, "preferences": []},
        {"version": 1, "preferences": "invalid"},
        {"version": 1, "preferences": {}},
    ],
)
def test_malformed_or_absent_draft_is_recoverable(stored, sample_catalog):
    assert load(stored, sample_catalog) is None


@pytest.mark.parametrize("version", [None, True, False, 1.0, "1", 0, 2])
def test_draft_version_must_be_the_supported_integer(version, sample_catalog):
    stored = stored_draft()
    stored["version"] = version

    assert load(stored, sample_catalog) is None


@pytest.mark.parametrize("field", ["destination", "days", "budget", "interests", "pace", "family_friendly"])
def test_incomplete_stored_preferences_are_recoverable(field, sample_catalog):
    stored = stored_draft()
    del stored["preferences"][field]

    assert load(stored, sample_catalog) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("destination", None), ("destination", 123), ("destination", []),
        ("days", True), ("days", False), ("days", "3"), ("days", 3.0),
        ("budget", 300), ("budget", 300.0), ("budget", None), ("budget", True),
        ("interests", "food"), ("interests", None), ("interests", [1]),
        ("interests", ["food", None]),
        ("pace", None), ("pace", []),
        ("family_friendly", "on"), ("family_friendly", 1), ("family_friendly", None),
    ],
)
def test_stored_field_types_are_checked_before_normalization(field, value, sample_catalog):
    assert load(stored_draft(**{field: value}), sample_catalog) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("days", 0), ("days", 15),
        ("budget", "0"), ("budget", "-1"), ("budget", "1000000.01"),
        ("budget", "300.001"), ("budget", "3e2"), ("budget", "NaN"),
        ("budget", "Infinity"), ("budget", "€300"), ("budget", "1,000"),
        ("destination", "Unknown city"),
        ("interests", []), ("interests", ["food", "unknown"]),
        ("interests", ["nightlife"]),
        ("pace", "active"), ("pace", "unknown"),
    ],
)
def test_out_of_range_or_unsupported_draft_values_are_recoverable(field, value, sample_catalog):
    assert load(stored_draft(**{field: value}), sample_catalog) is None


@pytest.mark.parametrize(
    ("interests", "pace"),
    [(["food"], "active"), (["history"], "relaxed")],
)
def test_pace_and_interests_must_belong_to_stored_destination(sample_catalog, interests, pace):
    stored = stored_draft(destination="Kyoto, Japan", interests=interests, pace=pace)

    assert load(stored, sample_catalog) is None


def test_valid_draft_can_use_another_fixture_destination_and_its_tags(sample_catalog):
    stored = stored_draft(destination="Kyoto, Japan", interests=["history"], pace="active")

    restored = load(stored, sample_catalog)

    assert restored is not None
    assert restored["destination"] == "Kyoto, Japan"
    assert restored["interests"] == ["history"]
    assert restored["pace"] == "active"


def test_current_catalog_changes_can_make_a_previous_draft_unsupported(sample_catalog):
    # Destination removal, rather than a cookie failure, is a recoverable stale draft.
    changed_catalog = [place for place in sample_catalog if place["destination"] != "Paris, France"]

    assert load(stored_draft(), changed_catalog) is None


def test_empty_current_catalog_makes_a_previous_draft_recoverable():
    assert load(stored_draft(), []) is None


@pytest.mark.parametrize("days", [1, 14])
def test_boundary_days_and_unselected_optional_preferences_are_valid(days, sample_catalog):
    restored = load(stored_draft(days=days, pace="", family_friendly=False), sample_catalog)

    assert restored is not None
    assert restored["days"] == days
    assert restored["pace"] == ""
    assert restored["family_friendly"] is False

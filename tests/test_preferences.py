"""Validate raw form answers before they can replace a current draft."""

from decimal import Decimal

import pytest
from werkzeug.datastructures import MultiDict


def valid_form_data(
    *,
    destination="Paris, France",
    days="3",
    budget="250.00",
    interests=("food", "history"),
    pace="relaxed",
    family_friendly="on",
):
    """Build form-like input with repeated interest fields."""
    fields = [
        ("destination", destination),
        ("days", days),
        ("budget", budget),
        ("pace", pace),
        ("family_friendly", family_friendly),
    ]
    fields.extend(("interests", interest) for interest in interests)
    return MultiDict(fields)


def test_valid_preferences_are_normalized():
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(valid_form_data())

    assert errors == {}
    assert values == {
        "destination": "Paris, France",
        "days": 3,
        "budget": Decimal("250.00"),
        "interests": ["food", "history"],
        "pace": "relaxed",
        "family_friendly": True,
    }
    assert isinstance(values["budget"], Decimal)
    assert values["budget"].as_tuple().exponent == -2


def test_destination_is_matched_without_case_or_extra_spaces():
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(
        valid_form_data(destination="  PARIS, FRANCE  ")
    )

    assert errors == {}
    assert values["destination"] == "Paris, France"


@pytest.mark.parametrize("destination", ["", "Tokyo, Japan"])
def test_missing_or_unsupported_destination_is_rejected(destination):
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(
        valid_form_data(destination=destination)
    )

    assert "destination" in errors
    assert values["destination"] == destination


@pytest.mark.parametrize("days", ["", "0", "15", "-1", "2.5", "1.0", "1e1", "tomorrow"])
def test_trip_length_must_be_a_whole_number_from_one_to_fourteen(days):
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(valid_form_data(days=days))

    assert "days" in errors
    assert values["days"] == days


@pytest.mark.parametrize(("submitted", "expected"), [("1", 1), ("14", 14), (" 3 ", 3)])
def test_trip_length_accepts_both_boundaries_and_surrounding_spaces(submitted, expected):
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(valid_form_data(days=submitted))

    assert errors == {}
    assert values["days"] == expected
    assert type(values["days"]) is int


@pytest.mark.parametrize(
    "budget",
    ["", "abc", "0", "-10", "nan", "inf", "€300", "1,000.00", "3e2", "1.001", "1000000.01"],
)
def test_budget_must_follow_the_approved_amount_rules(budget):
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(valid_form_data(budget=budget))

    assert "budget" in errors
    assert values["budget"] == budget


@pytest.mark.parametrize("budget", ["0.01", "1000000.00", " 300.5 "])
def test_valid_budget_bounds_and_plain_decimal_formats_are_normalized(budget):
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(valid_form_data(budget=budget))

    assert errors == {}
    assert isinstance(values["budget"], Decimal)
    assert values["budget"] == Decimal(budget.strip())
    assert values["budget"].as_tuple().exponent == -2


@pytest.mark.parametrize("interests", [(), ("made-up-interest",), ("food", "made-up-interest")])
def test_at_least_one_supported_interest_is_required(interests):
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(
        valid_form_data(interests=interests)
    )

    assert "interests" in errors
    assert values["interests"] == list(interests)


def test_unknown_optional_pace_is_rejected():
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(valid_form_data(pace="hectic"))

    assert "pace" in errors
    assert values["pace"] == "hectic"


def test_interests_are_canonical_and_duplicates_do_not_survive_normalization():
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(
        valid_form_data(interests=(" FOOD ", "food", "History", " HISTORY "))
    )

    assert errors == {}
    assert values["interests"] == ["food", "history"]


def test_supported_pace_is_returned_in_canonical_form():
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(valid_form_data(pace="  RELAXED  "))

    assert errors == {}
    assert values["pace"] == "relaxed"


def test_active_pace_is_not_available_in_the_current_paris_catalog():
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(valid_form_data(pace="active"))

    assert "pace" in errors
    assert values["pace"] == "active"


def test_optional_pace_and_family_preference_may_be_omitted():
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(
        valid_form_data(pace="", family_friendly="")
    )

    assert errors == {}
    assert values["pace"] == ""
    assert values["family_friendly"] is False


def test_absent_optional_form_fields_mean_no_preferences():
    from preferences import validate_trip_preferences

    form_data = valid_form_data()
    form_data.poplist("pace")
    form_data.poplist("family_friendly")

    values, errors = validate_trip_preferences(form_data)

    assert errors == {}
    assert values["pace"] == ""
    assert values["family_friendly"] is False


def test_an_error_preserves_all_submitted_answers_before_normalization():
    from preferences import validate_trip_preferences

    form_data = valid_form_data(
        destination="  PARIS, FRANCE  ",
        days=" 0 ",
        budget=" 300.5 ",
        interests=(" FOOD ", "food", "History"),
        pace=" RELAXED ",
    )

    values, errors = validate_trip_preferences(form_data)

    assert "days" in errors
    assert all(isinstance(message, str) and message.strip() for message in errors.values())
    assert values == {
        "destination": "  PARIS, FRANCE  ",
        "days": " 0 ",
        "budget": " 300.5 ",
        "interests": [" FOOD ", "food", "History"],
        "pace": " RELAXED ",
        "family_friendly": True,
    }


def test_interest_must_exist_at_the_selected_destination(sample_catalog):
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(
        valid_form_data(destination="Kyoto, Japan", interests=("food",), pace=""),
        catalog=sample_catalog,
    )

    assert "interests" in errors
    assert values["interests"] == ["food"]


def test_pace_must_exist_at_the_selected_destination(sample_catalog):
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(
        valid_form_data(pace="active"), catalog=sample_catalog
    )

    assert "pace" in errors
    assert values["pace"] == "active"


def test_destination_specific_pace_can_be_accepted_where_explicitly_tagged(sample_catalog):
    from preferences import validate_trip_preferences

    values, errors = validate_trip_preferences(
        valid_form_data(
            destination=" kyoto, JAPAN ", interests=(" HISTORY ",), pace=" ACTIVE "
        ),
        catalog=sample_catalog,
    )

    assert errors == {}
    assert values["destination"] == "Kyoto, Japan"
    assert values["interests"] == ["history"]
    assert values["pace"] == "active"
    assert values["family_friendly"] is True

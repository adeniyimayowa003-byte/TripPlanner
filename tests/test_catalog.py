"""Unit tests for TripPlanner's sample destination catalog."""

import pytest


@pytest.fixture
def sample_catalog():
    """Provide a tiny catalog with two destinations for lookup tests."""
    return [
        {
            "id": "paris-garden",
            "name": "Sample Garden",
            "destination": "Paris, France",
            "category": "activity",
            "interest_tags": ["nature", "history"],
            "preference_tags": ["relaxed", "family-friendly"],
            "estimated_cost": 0,
            "description": "A sample outdoor place.",
            "source_url": "https://example.com/paris-garden",
        },
        {
            "id": "paris-cafe",
            "name": "Sample Cafe",
            "destination": "Paris, France",
            "category": "restaurant",
            "interest_tags": ["food", "culture"],
            "preference_tags": [],
            "estimated_cost": 18,
            "description": "A sample place to eat.",
            "source_url": "https://example.com/paris-cafe",
        },
        {
            "id": "kyoto-temple",
            "name": "Sample Temple",
            "destination": "Kyoto, Japan",
            "category": "attraction",
            "interest_tags": ["history", "culture"],
            "preference_tags": ["active"],
            "estimated_cost": 5,
            "description": "A sample historic place.",
            "source_url": "https://example.com/kyoto-temple",
        },
    ]


def test_destination_lookup_returns_only_matching_entries(sample_catalog):
    from catalog import get_places_for_destination

    places = get_places_for_destination("Paris, France", sample_catalog)

    assert [place["id"] for place in places] == ["paris-garden", "paris-cafe"]


def test_destination_lookup_ignores_case_and_surrounding_spaces(sample_catalog):
    from catalog import get_places_for_destination

    places = get_places_for_destination("  PARIS, FRANCE  ", sample_catalog)

    assert len(places) == 2
    assert all(place["destination"] == "Paris, France" for place in places)


def test_unknown_destination_raises_clear_error(sample_catalog):
    from catalog import UnsupportedDestinationError, get_places_for_destination

    with pytest.raises(UnsupportedDestinationError, match="Tokyo, Japan"):
        get_places_for_destination("Tokyo, Japan", sample_catalog)


def test_sample_catalog_has_required_fields_and_valid_values():
    from catalog import load_catalog

    places = load_catalog()
    required_fields = {
        "id",
        "name",
        "destination",
        "category",
        "interest_tags",
        "preference_tags",
        "estimated_cost",
        "description",
        "source_url",
    }
    allowed_categories = {"attraction", "activity", "restaurant"}

    assert places
    assert all(required_fields <= place.keys() for place in places)
    assert all(isinstance(place["id"], str) and place["id"].strip() for place in places)
    assert all(isinstance(place["name"], str) and place["name"].strip() for place in places)
    assert all(isinstance(place["destination"], str) for place in places)
    assert all(place["category"] in allowed_categories for place in places)
    assert all(
        isinstance(place["interest_tags"], list)
        and all(isinstance(tag, str) for tag in place["interest_tags"])
        for place in places
    )
    assert all(
        isinstance(place["preference_tags"], list)
        and all(isinstance(tag, str) for tag in place["preference_tags"])
        for place in places
    )
    assert all(
        isinstance(place["estimated_cost"], (int, float))
        and not isinstance(place["estimated_cost"], bool)
        and place["estimated_cost"] >= 0
        for place in places
    )
    assert all(isinstance(place["description"], str) for place in places)
    assert all(place["source_url"].startswith("https://parisjetaime.com/") for place in places)


def test_sample_catalog_uses_unique_ids_and_includes_each_category():
    from catalog import load_catalog

    places = load_catalog()
    ids = [place["id"] for place in places]
    categories = {place["category"] for place in places}

    assert len(ids) == len(set(ids))
    assert categories == {"attraction", "activity", "restaurant"}


def test_sample_catalog_can_be_looked_up_by_destination():
    from catalog import get_places_for_destination

    paris_places = get_places_for_destination("Paris, France")

    assert paris_places
    assert all(place["destination"] == "Paris, France" for place in paris_places)


def test_supported_destinations_and_interests_are_sorted_and_unique(sample_catalog):
    from catalog import get_supported_destinations, get_supported_interests

    assert get_supported_destinations(sample_catalog) == [
        "Kyoto, Japan",
        "Paris, France",
    ]
    assert get_supported_interests(sample_catalog) == [
        "culture",
        "food",
        "history",
        "nature",
    ]


def test_pace_and_family_tags_are_separate_from_interests():
    from catalog import load_catalog

    places = load_catalog()
    preference_tags = {"relaxed", "active", "family-friendly"}

    assert all(preference_tags.isdisjoint(place["interest_tags"]) for place in places)


def test_supported_interests_are_scoped_to_the_selected_destination(sample_catalog):
    from catalog import get_supported_interests

    assert get_supported_interests(sample_catalog, destination="Paris, France") == [
        "culture", "food", "history", "nature"
    ]
    assert get_supported_interests(sample_catalog, destination="Kyoto, Japan") == [
        "culture", "history"
    ]


def test_destination_scoped_options_ignore_case_and_surrounding_spaces(sample_catalog):
    from catalog import get_supported_interests, get_supported_paces

    assert get_supported_interests(sample_catalog, destination="  KYOTO, JAPAN  ") == [
        "culture", "history"
    ]
    assert get_supported_paces("  PARIS, FRANCE  ", sample_catalog) == ["relaxed"]


def test_pace_choices_come_from_destination_tags_without_family_tags(sample_catalog):
    from catalog import get_supported_paces

    assert get_supported_paces("Paris, France", sample_catalog) == ["relaxed"]
    assert get_supported_paces("Kyoto, Japan", sample_catalog) == ["active"]


def test_pace_options_are_unique_sorted_known_paces(sample_catalog):
    from catalog import get_supported_paces

    sample_catalog[0]["preference_tags"] = ["active", "relaxed", "active", "family-friendly", "unknown"]
    sample_catalog[1]["preference_tags"] = ["relaxed"]

    assert get_supported_paces("Paris, France", sample_catalog) == ["active", "relaxed"]


def test_current_paris_catalog_does_not_offer_active_pace():
    from catalog import get_supported_paces

    assert get_supported_paces("Paris, France") == ["relaxed"]

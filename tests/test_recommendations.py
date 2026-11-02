"""Executable rules for personalized ideas, independent of Flask and the browser."""

from copy import deepcopy
from decimal import Decimal

import pytest


def recommend(preferences, catalog):
    # Missing features should fail individual tests, not stop test collection.
    from recommendations import recommend_trip_ideas

    return recommend_trip_ideas(preferences, catalog=catalog)


def result_ids(items):
    return [item["place"]["id"] for item in items]


def test_eligibility_requires_destination_interest_and_individual_affordability(
    normalized_preferences, sample_catalog, make_place
):
    preferences = {**normalized_preferences, "budget": Decimal("54.00")}
    extra_places = [
        make_place(id="unrelated", interest_tags=["art"], estimated_cost=0),
        make_place(id="too-expensive", interest_tags=["history"], estimated_cost=18.01),
    ]

    items, _ = recommend(preferences, sample_catalog + extra_places)

    assert {item["place"]["id"] for item in items} == {
        place["id"] for place in sample_catalog if place["destination"] == "Paris, France"
    }
    assert all(item["estimated_cost"] * preferences["days"] <= preferences["budget"] for item in items)
    assert any(item["estimated_cost"] == 0 for item in items)
    assert any(item["estimated_cost"] == Decimal("18.00") for item in items)


def test_score_counts_distinct_interests_and_only_earned_preference_bonuses(
    normalized_preferences, make_place
):
    catalog = [
        make_place(id="two-interests", interest_tags=["food", "history", "history"], estimated_cost=40),
        make_place(id="both-bonuses", interest_tags=["history"], preference_tags=["relaxed", "family-friendly"]),
        make_place(id="pace-only", interest_tags=["history"], preference_tags=["relaxed"]),
        make_place(id="family-only", interest_tags=["food"], preference_tags=["family-friendly"]),
        make_place(id="no-bonuses", interest_tags=["history"]),
    ]

    items, notices = recommend(normalized_preferences, catalog)
    by_id = {item["place"]["id"]: item for item in items}

    assert {key: value["score"] for key, value in by_id.items()} == {
        "two-interests": 6,
        "both-bonuses": 5,
        "pace-only": 4,
        "family-only": 4,
        "no-bonuses": 3,
    }
    assert set(by_id["two-interests"]["matched_interests"]) == {"food", "history"}
    assert len(by_id["two-interests"]["matched_interests"]) == 2
    assert set(by_id["both-bonuses"]["preference_matches"]) == {"relaxed", "family-friendly"}
    assert by_id["no-bonuses"]["preference_matches"] == []
    assert result_ids(items)[:2] == ["two-interests", "both-bonuses"]
    assert not notices


@pytest.mark.parametrize(
    ("pace", "family_friendly", "expected_score", "expected_matches"),
    [
        ("", False, 3, set()),
        ("relaxed", False, 4, {"relaxed"}),
        ("", True, 4, {"family-friendly"}),
        ("relaxed", True, 5, {"relaxed", "family-friendly"}),
        ("active", False, 3, set()),
    ],
)
def test_optional_tags_only_score_when_that_preference_is_selected(
    normalized_preferences, make_place, pace, family_friendly, expected_score, expected_matches
):
    preferences = {**normalized_preferences, "pace": pace, "family_friendly": family_friendly}
    place = make_place(interest_tags=["history"], preference_tags=["relaxed", "family-friendly"])

    items, _ = recommend(preferences, [place])

    assert items[0]["score"] == expected_score
    assert set(items[0]["preference_matches"]) == expected_matches


def test_order_applies_score_then_cost_then_casefolded_name_then_stable_id(
    normalized_preferences, make_place
):
    catalog = [
        make_place(id="same-b", name="ALPHA", interest_tags=["history"], estimated_cost=2),
        make_place(id="last-name", name="zebra", interest_tags=["history"], estimated_cost=2),
        make_place(id="first-cost", name="Zulu", interest_tags=["history"], estimated_cost=0),
        make_place(id="highest-score", name="Zulu", interest_tags=["food", "history"], estimated_cost=50),
        make_place(id="same-a", name="alpha", interest_tags=["history"], estimated_cost=2),
        make_place(id="middle-name", name="Beta", interest_tags=["history"], estimated_cost=2),
    ]

    items, _ = recommend(normalized_preferences, catalog)

    assert result_ids(items) == [
        "highest-score", "first-cost", "same-a", "same-b", "middle-name", "last-name"
    ]


def test_affordability_uses_exact_total_instead_of_rounded_daily_preview(
    normalized_preferences, make_place
):
    preferences = {**normalized_preferences, "days": 3, "budget": Decimal("100.01")}
    catalog = [
        make_place(id="rounded-only", interest_tags=["history"], estimated_cost=33.34),
        make_place(id="exactly-affordable", interest_tags=["history"], estimated_cost=33.33),
        make_place(id="free", interest_tags=["history"], estimated_cost=0),
    ]

    items, _ = recommend(preferences, catalog)

    assert result_ids(items) == ["free", "exactly-affordable"]


def test_exact_budget_boundary_is_inclusive(normalized_preferences, make_place):
    preferences = {**normalized_preferences, "days": 3, "budget": Decimal("59.97")}
    place = make_place(interest_tags=["food"], estimated_cost=19.99)

    items, _ = recommend(preferences, [place])

    assert len(items) == 1
    assert isinstance(items[0]["estimated_cost"], Decimal)
    assert items[0]["estimated_cost"] == Decimal("19.99")


def test_explanations_name_actual_interests_and_earned_preferences(
    normalized_preferences, make_place
):
    catalog = [
        make_place(id="tagged", interest_tags=["food", "history"], preference_tags=["relaxed", "family-friendly"]),
        make_place(id="untagged", interest_tags=["food", "culture"]),
    ]

    items, _ = recommend(normalized_preferences, catalog)
    by_id = {item["place"]["id"]: item for item in items}
    tagged_reason = by_id["tagged"]["reason"].casefold().replace("-", " ")
    plain_reason = by_id["untagged"]["reason"].casefold().replace("-", " ")

    assert all(word in tagged_reason for word in ("food", "history", "relaxed", "family friendly"))
    assert "food" in plain_reason
    assert all(word not in plain_reason for word in ("history", "culture", "relaxed", "family friendly"))
    assert by_id["untagged"]["matched_interests"] == ["food"]
    assert by_id["untagged"]["preference_matches"] == []


def test_unmet_preference_notices_consider_only_eligible_results(
    normalized_preferences, make_place
):
    catalog = [
        make_place(id="eligible", interest_tags=["food"]),
        make_place(id="unrelated-tagged", interest_tags=["art"], preference_tags=["relaxed", "family-friendly"]),
        make_place(id="unaffordable-tagged", interest_tags=["history"], preference_tags=["relaxed", "family-friendly"], estimated_cost=101),
    ]

    items, notices = recommend(normalized_preferences, catalog)
    notice_text = " ".join(notices).casefold().replace("-", " ")

    assert result_ids(items) == ["eligible"]
    assert notices and all(isinstance(notice, str) and notice.strip() for notice in notices)
    assert "relaxed" in notice_text
    assert "family friendly" in notice_text


def test_no_selected_preferences_produces_no_unmet_preference_notice(
    normalized_preferences, make_place
):
    preferences = {**normalized_preferences, "pace": "", "family_friendly": False}

    items, notices = recommend(preferences, [make_place(interest_tags=["history"])])

    assert items
    assert not notices


def test_no_qualifying_food_idea_does_not_fall_back_to_unrelated_or_expensive_items(
    normalized_preferences, sample_catalog
):
    preferences = {**normalized_preferences, "interests": ["food"], "budget": Decimal("1.00")}

    items, _ = recommend(preferences, sample_catalog)

    assert items == []


def test_explicit_empty_catalog_does_not_fall_back_to_real_sample_data(normalized_preferences):
    items, _ = recommend(normalized_preferences, [])

    assert items == []


def test_returns_every_unique_qualifying_item_deterministically_without_mutation(
    normalized_preferences, make_place
):
    catalog = [
        make_place(id=f"place-{index:02d}", interest_tags=["history"], estimated_cost=index)
        for index in range(12)
    ]
    catalog.append(deepcopy(catalog[0]))
    original_catalog = deepcopy(catalog)
    original_preferences = deepcopy(normalized_preferences)

    first_items, first_notices = recommend(normalized_preferences, catalog)
    second_items, second_notices = recommend(normalized_preferences, list(reversed(catalog)))

    assert len(first_items) == 12
    assert len(set(result_ids(first_items))) == 12
    assert first_items == second_items
    assert first_notices == second_notices
    assert catalog == original_catalog
    assert normalized_preferences == original_preferences
    assert all(item["place"] in original_catalog for item in first_items)


def test_current_paris_catalog_matches_the_approved_acceptance_ranking(normalized_preferences):
    from recommendations import recommend_trip_ideas

    items, _ = recommend_trip_ideas(normalized_preferences)

    assert [item["place"]["name"] for item in items[:3]] == [
        "Le Procope", "Luxembourg Gardens", "Seine Riverside Walk"
    ]
    assert [item["score"] for item in items[:3]] == [6, 5, 4]

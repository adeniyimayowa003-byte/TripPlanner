"""Executable scheduling rules for the approved daily-itinerary increment.

Imports of the new generator deliberately happen inside a helper. Before
implementation, pytest can discover every case and report the missing feature
as an individual failure instead of aborting collection.
"""

from copy import deepcopy
from decimal import Decimal

import pytest

from catalog import load_catalog
from recommendations import recommend_trip_ideas


def generate(preferences, catalog=None):
    from itinerary import generate_itinerary

    return generate_itinerary(preferences, catalog=catalog)


@pytest.fixture
def scheduler_preferences(normalized_preferences):
    return {
        **deepcopy(normalized_preferences),
        "interests": ["food", "history", "culture"],
        "pace": "",
        "family_friendly": False,
    }


def slot(result, day, name):
    return next(
        entry for entry in result["days"][day - 1]["slots"]
        if entry["name"] == name
    )


def item_id(result, day, name):
    item = slot(result, day, name)["item"]
    return None if item is None else item["place"]["id"]


def scheduled_items(result):
    return [
        entry["item"]
        for day in result["days"]
        for entry in day["slots"]
        if entry["item"] is not None
    ]


def scheduled_ids(result):
    return [item["place"]["id"] for item in scheduled_items(result)]


def notices_text(result):
    assert all(isinstance(notice, str) and notice.strip() for notice in result["notices"])
    assert len(result["notices"]) == len(set(result["notices"]))
    return " ".join(result["notices"]).casefold()


def assert_money_integrity(result, preferences):
    """Independently sum scheduled records, rather than trusting result totals."""
    calculated_trip = Decimal("0.00")
    filled = 0
    for day in result["days"]:
        calculated_day = Decimal("0.00")
        for entry in day["slots"]:
            item = entry["item"]
            if item is None:
                assert isinstance(entry["empty_reason"], str)
                assert entry["empty_reason"].strip()
                continue
            assert entry["empty_reason"] is None
            assert isinstance(item["estimated_cost"], Decimal)
            calculated_day += item["estimated_cost"]
            filled += 1
        assert isinstance(day["estimated_cost"], Decimal)
        assert day["estimated_cost"] == calculated_day
        assert calculated_day * preferences["days"] <= preferences["budget"]
        calculated_trip += calculated_day
    assert isinstance(result["estimated_cost"], Decimal)
    assert result["estimated_cost"] == calculated_trip
    assert calculated_trip <= preferences["budget"]
    assert isinstance(result["unallocated_allowance"], Decimal)
    assert result["unallocated_allowance"] == preferences["budget"] - calculated_trip
    assert result["filled_slots"] == filled
    assert result["total_slots"] == sum(len(day["slots"]) for day in result["days"])


@pytest.mark.parametrize("days", [1, 14])
@pytest.mark.parametrize(
    ("pace", "expected_slots"),
    [
        ("relaxed", ["Morning", "Evening"]),
        ("", ["Morning", "Afternoon", "Evening"]),
        ("active", ["Morning", "Afternoon", "Evening"]),
    ],
)
def test_requested_day_boundaries_and_supported_paces_set_capacity(
    scheduler_preferences, make_place, days, pace, expected_slots
):
    preferences = {**scheduler_preferences, "days": days, "pace": pace}
    catalog = [make_place(id="one", preference_tags=[pace] if pace else [])]

    result = generate(preferences, catalog)

    assert [day["number"] for day in result["days"]] == list(range(1, days + 1))
    assert all([entry["name"] for entry in day["slots"]] == expected_slots for day in result["days"])
    assert result["total_slots"] == days * len(expected_slots)
    assert result["filled_slots"] == 1
    assert scheduled_ids(result) == ["one"]
    assert_money_integrity(result, preferences)


def test_slots_are_filled_across_days_before_moving_to_the_next_slot(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "days": 2}
    catalog = [make_place(id=letter, name=letter) for letter in ("C", "A", "B")]

    result = generate(preferences, catalog)

    assert item_id(result, 1, "Morning") == "A"
    assert item_id(result, 2, "Morning") == "B"
    assert item_id(result, 1, "Afternoon") == "C"
    assert item_id(result, 2, "Afternoon") is None
    assert result["filled_slots"] == 3
    assert_money_integrity(result, preferences)


def test_existing_score_cost_name_and_stable_id_order_is_preserved(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "budget": Decimal("3000.00")}
    catalog = [
        make_place(id="same-b", name="ALPHA", estimated_cost=2),
        make_place(id="last-name", name="zebra", estimated_cost=2),
        make_place(id="first-cost", name="Zulu", estimated_cost=0),
        make_place(id="highest-score", name="Zulu", interest_tags=["food", "history"], estimated_cost=50),
        make_place(id="same-a", name="alpha", estimated_cost=2),
        make_place(id="middle-name", name="Beta", estimated_cost=2),
    ]

    result = generate(preferences, catalog)

    allocation_order = [
        item_id(result, day, name)
        for name in ("Morning", "Afternoon") for day in (1, 2, 3)
    ]
    assert allocation_order == [
        "highest-score", "first-cost", "same-a", "same-b", "middle-name", "last-name"
    ]
    assert_money_integrity(result, preferences)


def test_evening_prefers_a_fitting_restaurant_over_a_higher_ranked_activity(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "days": 1, "pace": "relaxed"}
    catalog = [
        make_place(id="morning", interest_tags=["food", "history", "culture"]),
        make_place(id="higher-activity", interest_tags=["food", "history"]),
        make_place(id="restaurant", category="restaurant", estimated_cost=10),
    ]

    result = generate(preferences, catalog)

    assert item_id(result, 1, "Morning") == "morning"
    assert item_id(result, 1, "Evening") == "restaurant"
    assert [item["place"]["id"] for item in result["unused_items"]] == ["higher-activity"]
    assert_money_integrity(result, preferences)


@pytest.mark.parametrize("category", ["activity", "attraction"])
def test_evening_fallback_keeps_its_actual_category_when_there_is_no_restaurant(
    scheduler_preferences, make_place, category
):
    preferences = {**scheduler_preferences, "days": 1, "pace": "relaxed"}
    catalog = [
        make_place(id="morning", interest_tags=["food", "history"]),
        make_place(id="fallback", category=category),
    ]

    result = generate(preferences, catalog)

    evening = slot(result, 1, "Evening")["item"]
    assert evening["place"]["id"] == "fallback"
    assert evening["place"]["category"] == category
    assert any(word in notices_text(result) for word in ("meal", "restaurant"))
    assert_money_integrity(result, preferences)


def test_food_only_restaurants_never_fill_daytime_or_repeat(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "interests": ["food"]}
    catalog = [
        make_place(id=f"restaurant-{cost}", category="restaurant", interest_tags=["food"], estimated_cost=cost)
        for cost in (4, 2, 3, 1)
    ]

    result = generate(preferences, catalog)

    assert all(item_id(result, day, name) is None for day in (1, 2, 3) for name in ("Morning", "Afternoon"))
    assert [item_id(result, day, "Evening") for day in (1, 2, 3)] == ["restaurant-1", "restaurant-2", "restaurant-3"]
    assert [item["place"]["id"] for item in result["unused_items"]] == ["restaurant-4"]
    assert result["filled_slots"] == 3
    assert_money_integrity(result, preferences)


def test_restaurants_can_match_a_non_food_interest(scheduler_preferences, make_place):
    preferences = {**scheduler_preferences, "days": 1, "interests": ["history"]}
    catalog = [make_place(id="historic-restaurant", category="restaurant", interest_tags=["history"])]

    result = generate(preferences, catalog)

    assert item_id(result, 1, "Morning") is None
    assert item_id(result, 1, "Afternoon") is None
    assert item_id(result, 1, "Evening") == "historic-restaurant"
    assert slot(result, 1, "Evening")["item"]["matched_interests"] == ["history"]


def test_evening_searches_later_restaurants_before_using_an_affordable_activity(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "days": 1, "pace": "relaxed", "budget": Decimal("100.00")}
    catalog = [
        make_place(id="morning", estimated_cost=80, interest_tags=["food", "history", "culture"]),
        make_place(id="fallback", interest_tags=["food", "history"]),
        make_place(id="expensive-restaurant", category="restaurant", estimated_cost=30, interest_tags=["food", "history"]),
        make_place(id="affordable-restaurant", category="restaurant", estimated_cost=10),
    ]
    ranked, _ = recommend_trip_ideas(preferences, catalog)
    assert [item["place"]["id"] for item in ranked] == [
        "morning", "fallback", "expensive-restaurant", "affordable-restaurant"
    ]

    result = generate(preferences, catalog)

    assert item_id(result, 1, "Morning") == "morning"
    assert item_id(result, 1, "Evening") == "affordable-restaurant"
    assert result["estimated_cost"] == Decimal("90.00")
    assert [item["place"]["id"] for item in result["unused_items"]] == ["fallback", "expensive-restaurant"]
    assert_money_integrity(result, preferences)


def test_restaurant_skipped_for_one_day_can_still_fill_a_later_evening(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "days": 2, "pace": "relaxed", "budget": Decimal("20.00")}
    catalog = [
        make_place(id="A", estimated_cost=8, interest_tags=["food", "history", "culture"]),
        make_place(id="B", estimated_cost=2, interest_tags=["food", "history"]),
        make_place(id="restaurant", category="restaurant", estimated_cost=5),
    ]
    ranked, _ = recommend_trip_ideas(preferences, catalog)
    assert [item["place"]["id"] for item in ranked] == ["A", "B", "restaurant"]

    result = generate(preferences, catalog)

    assert item_id(result, 1, "Evening") is None
    assert item_id(result, 2, "Evening") == "restaurant"
    assert result["estimated_cost"] == Decimal("15.00")
    assert_money_integrity(result, preferences)


def test_skip_unaffordable_candidate_without_discarding_its_later_day_opportunity(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "days": 2, "budget": Decimal("20.00")}
    catalog = [
        make_place(id="A", estimated_cost=8, interest_tags=["food", "history", "culture"]),
        make_place(id="B", estimated_cost=2, interest_tags=["food", "history"]),
        make_place(id="C", estimated_cost=5, interest_tags=["food", "history"]),
        make_place(id="D", estimated_cost=2, interest_tags=["history"]),
    ]
    ranked, _ = recommend_trip_ideas(preferences, catalog)
    assert [item["place"]["id"] for item in ranked] == ["A", "B", "C", "D"]
    assert [item["score"] for item in ranked] == [9, 6, 6, 3]

    result = generate(preferences, catalog)

    assert [item_id(result, day, "Morning") for day in (1, 2)] == ["A", "B"]
    assert item_id(result, 1, "Afternoon") == "D"
    assert item_id(result, 2, "Afternoon") == "C"
    assert [day["estimated_cost"] for day in result["days"]] == [Decimal("10.00"), Decimal("7.00")]
    assert result["estimated_cost"] == Decimal("17.00")
    assert_money_integrity(result, preferences)


@pytest.mark.parametrize(("last_cost", "expected_day"), [("13.34", 2), ("13.33", 1)])
def test_cumulative_limit_uses_exact_daily_share_not_the_rounded_preview(
    scheduler_preferences, make_place, last_cost, expected_day
):
    preferences = {**scheduler_preferences, "budget": Decimal("100.01")}
    catalog = [
        make_place(id="A", estimated_cost=20, interest_tags=["food", "history", "culture"]),
        make_place(id="B", name="B", estimated_cost=0, interest_tags=["food", "history"]),
        make_place(id="C", name="C", estimated_cost=0, interest_tags=["food", "history"]),
        make_place(id="D", estimated_cost=last_cost, interest_tags=["history"]),
    ]
    ranked, _ = recommend_trip_ideas(preferences, catalog)
    assert len(ranked) == 4, "This fixture must test combined costs, not individual eligibility."
    assert [item["place"]["id"] for item in ranked] == ["A", "B", "C", "D"]
    assert [item["score"] for item in ranked] == [9, 6, 6, 3]
    assert all(item["estimated_cost"] * preferences["days"] <= preferences["budget"] for item in ranked)

    result = generate(preferences, catalog)

    assert [item_id(result, day, "Morning") for day in (1, 2, 3)] == ["A", "B", "C"]
    assert item_id(result, expected_day, "Afternoon") == "D"
    if expected_day == 2:
        assert item_id(result, 1, "Afternoon") is None
        assert result["days"][0]["estimated_cost"] == Decimal("20.00")
    else:
        assert result["days"][0]["estimated_cost"] == Decimal("33.33")
    assert_money_integrity(result, preferences)


def test_unused_daily_allowance_is_not_transferred_to_another_day(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "days": 2, "budget": Decimal("20.00")}
    catalog = [
        make_place(id="A", name="A", estimated_cost=6, interest_tags=["food", "history", "culture"]),
        make_place(id="B", name="B", estimated_cost=6, interest_tags=["food", "history", "culture"]),
        make_place(id="C", estimated_cost=5),
    ]

    result = generate(preferences, catalog)

    assert result["estimated_cost"] == Decimal("12.00")
    assert result["estimated_cost"] + Decimal("5.00") <= preferences["budget"]
    assert [item["place"]["id"] for item in result["unused_items"]] == ["C"]
    assert all(item_id(result, day, name) is None for day in (1, 2) for name in ("Afternoon", "Evening"))
    assert_money_integrity(result, preferences)


def test_greedy_daytime_choices_can_leave_a_restaurant_unaffordable_and_use_fallback(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "days": 1, "budget": Decimal("100.00"), "family_friendly": True}
    catalog = [
        make_place(id="A", estimated_cost=30, interest_tags=["food", "history", "culture"]),
        make_place(id="B", category="attraction", estimated_cost=30, interest_tags=["food", "history"]),
        make_place(id="C", category="restaurant", estimated_cost=50, preference_tags=["family-friendly"]),
        make_place(id="D", estimated_cost=10),
    ]
    ranked, _ = recommend_trip_ideas(preferences, catalog)
    assert [item["score"] for item in ranked] == [9, 6, 4, 3]

    result = generate(preferences, catalog)

    assert [item_id(result, 1, name) for name in ("Morning", "Afternoon", "Evening")] == ["A", "B", "D"]
    assert result["estimated_cost"] == Decimal("70.00")
    assert [item["place"]["id"] for item in result["unused_items"]] == ["C"]
    assert any(word in notices_text(result) for word in ("meal", "restaurant"))
    assert_money_integrity(result, preferences)


def test_eligible_ids_only_and_duplicate_catalog_records_never_repeat(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "days": 2, "budget": Decimal("100.00")}
    first = make_place(id="free", name="First copy")
    catalog = [
        first,
        {**deepcopy(first), "name": "Duplicate copy"},
        make_place(id="restaurant", category="restaurant", estimated_cost=20),
        make_place(id="boundary", category="attraction", estimated_cost=50),
        make_place(id="wrong-interest", interest_tags=["art"]),
        make_place(id="wrong-destination", destination="Kyoto, Japan"),
        make_place(id="too-expensive", estimated_cost="50.01"),
    ]

    result = generate(preferences, catalog)

    ids = scheduled_ids(result)
    assert len(ids) == len(set(ids)) == 3
    assert set(ids) == {"free", "restaurant", "boundary"}
    assert all(item["place"]["destination"] == preferences["destination"] for item in scheduled_items(result))
    assert result["unused_items"] == []
    assert_money_integrity(result, preferences)


def test_unused_alternatives_keep_the_original_recommendation_order(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "days": 1, "pace": "relaxed"}
    catalog = [make_place(id=letter, name=letter) for letter in ("D", "B", "C", "A")]
    ranked, _ = recommend_trip_ideas(preferences, catalog)

    result = generate(preferences, catalog)

    assert scheduled_ids(result) == ["A", "B"]
    assert [item["place"]["id"] for item in result["unused_items"]] == ["C", "D"]
    assert result["unused_items"] == [item for item in ranked if item["place"]["id"] in {"C", "D"}]
    assert any(word in notices_text(result) for word in ("unused", "alternative", "not scheduled"))


def test_scheduled_records_retain_recommendation_evidence_and_original_place_fields(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "days": 1, "pace": "relaxed", "family_friendly": True}
    catalog = [
        make_place(id="garden", preference_tags=["relaxed", "family-friendly"]),
        make_place(id="cafe", category="restaurant", interest_tags=["food"], estimated_cost="1.25"),
        make_place(id="alternative", category="attraction", estimated_cost=2),
    ]
    ranked, _ = recommend_trip_ideas(preferences, catalog)
    expected_by_id = {item["place"]["id"]: item for item in ranked}

    result = generate(preferences, catalog)

    for item in scheduled_items(result) + result["unused_items"]:
        assert item == expected_by_id[item["place"]["id"]]
        assert item["reason"]
        assert item["place"]["source_url"] == "https://example.com/place"
    assert_money_integrity(result, preferences)


def test_requested_tags_only_present_in_unused_ideas_need_scheduled_preference_notices(
    normalized_preferences, make_place
):
    preferences = {**normalized_preferences, "days": 1}
    catalog = [
        make_place(id="A", name="A", interest_tags=["food", "history"]),
        make_place(id="B", name="B", category="restaurant", interest_tags=["food", "history"]),
        make_place(id="C", name="C", preference_tags=["relaxed", "family-friendly"]),
    ]
    ranked, recommendation_notices = recommend_trip_ideas(preferences, catalog)
    assert [item["score"] for item in ranked] == [6, 6, 5]
    assert recommendation_notices == [], "The tags must exist among eligible alternatives."

    result = generate(preferences, catalog)

    assert scheduled_ids(result) == ["A", "B"]
    assert [item["place"]["id"] for item in result["unused_items"]] == ["C"]
    assert all(item["preference_matches"] == [] for item in scheduled_items(result))
    for preference in ("relaxed", "family-friendly"):
        relevant = [notice.casefold() for notice in result["notices"] if preference in notice.casefold()]
        assert relevant, f"An unscheduled {preference} alternative cannot confirm the itinerary's preference."
        assert any(any(word in notice for word in ("cannot", "not", "none", "unconfirmed")) for notice in relevant)
    notices_text(result)


def test_existing_recommendation_limitations_are_preserved(normalized_preferences, make_place):
    catalog = [make_place(id="untagged")]
    _, expected_notices = recommend_trip_ideas(normalized_preferences, catalog)
    assert len(expected_notices) == 2

    result = generate(normalized_preferences, catalog)

    for notice in expected_notices:
        assert notice in result["notices"]
    assert scheduled_items(result)[0]["preference_matches"] == []
    notices_text(result)


@pytest.mark.parametrize("empty_case", ["explicit-empty", "unmatched", "unaffordable"])
def test_empty_results_keep_all_days_and_honest_gaps_without_invented_items(
    normalized_preferences, make_place, empty_case
):
    preferences = {**normalized_preferences, "budget": Decimal("0.01")}
    catalogs = {
        "explicit-empty": [],
        "unmatched": [make_place(id="art-only", interest_tags=["art"])],
        "unaffordable": [make_place(id="costly", estimated_cost=1)],
    }

    result = generate(preferences, catalogs[empty_case])

    assert [day["number"] for day in result["days"]] == [1, 2, 3]
    assert all(entry["item"] is None for day in result["days"] for entry in day["slots"])
    assert all(day["estimated_cost"] == Decimal("0.00") for day in result["days"])
    assert result["estimated_cost"] == Decimal("0.00")
    assert result["unallocated_allowance"] == Decimal("0.01")
    assert result["filled_slots"] == 0
    assert result["total_slots"] == 6
    assert result["unused_items"] == []
    assert notices_text(result)
    assert_money_integrity(result, preferences)


def test_scarce_catalog_spreads_single_free_item_without_counting_gaps_as_items(
    normalized_preferences, make_place
):
    preferences = {**normalized_preferences, "days": 14}

    result = generate(preferences, [make_place(id="one-free-item")])

    assert item_id(result, 1, "Morning") == "one-free-item"
    assert scheduled_ids(result) == ["one-free-item"]
    assert result["filled_slots"] == 1
    assert result["total_slots"] == 28
    assert len(result["days"]) == 14
    assert result["days"][1]["estimated_cost"] == Decimal("0.00")
    assert_money_integrity(result, preferences)


def test_decimal_totals_do_not_accumulate_binary_float_artifacts(
    scheduler_preferences, make_place
):
    preferences = {**scheduler_preferences, "days": 1, "pace": "relaxed", "budget": Decimal("0.30")}
    catalog = [make_place(id="tenth", estimated_cost=0.1), make_place(id="fifth", estimated_cost=0.2)]

    result = generate(preferences, catalog)

    assert result["filled_slots"] == 2
    assert result["estimated_cost"] == Decimal("0.30")
    assert result["unallocated_allowance"] == Decimal("0.00")
    assert_money_integrity(result, preferences)


def test_deterministic_results_and_nested_input_data_remain_unchanged(
    normalized_preferences, make_place
):
    preferences = deepcopy(normalized_preferences)
    catalog = [
        make_place(id="garden", preference_tags=["relaxed", "family-friendly"]),
        make_place(id="restaurant", category="restaurant", interest_tags=["food"], estimated_cost=10),
        make_place(id="museum", category="attraction", estimated_cost=25),
    ]
    before_preferences = deepcopy(preferences)
    before_catalog = deepcopy(catalog)

    first = generate(preferences, catalog)
    second = generate(preferences, catalog)

    assert first == second
    assert preferences == before_preferences
    assert catalog == before_catalog
    assert_money_integrity(first, preferences)
    first_item = scheduled_items(first)[0]
    first_item["place"]["interest_tags"].append("result-only-marker")
    first_item["matched_interests"].append("result-only-marker")
    assert catalog == before_catalog
    assert preferences == before_preferences
    assert "result-only-marker" not in scheduled_items(second)[0]["place"]["interest_tags"]
    assert "result-only-marker" not in scheduled_items(second)[0]["matched_interests"]


def test_real_relaxed_sample_assignments_cost_103_with_197_unallocated(normalized_preferences):
    result = generate(normalized_preferences, load_catalog())

    assert [[item_id(result, day, name) for name in ("Morning", "Evening")] for day in (1, 2, 3)] == [
        ["paris-luxembourg-gardens", "paris-le-procope"],
        ["paris-seine-riverside-walk", "paris-cafe-de-flore"],
        ["paris-notre-dame", "paris-louvre-museum"],
    ]
    assert [day["estimated_cost"] for day in result["days"]] == [Decimal("50.00"), Decimal("28.00"), Decimal("25.00")]
    assert result["estimated_cost"] == Decimal("103.00")
    assert result["unallocated_allowance"] == Decimal("197.00")
    assert result["filled_slots"] == result["total_slots"] == 6
    assert [item["place"]["id"] for item in result["unused_items"]] == ["paris-eiffel-tower"]
    assert any(word in notices_text(result) for word in ("meal", "restaurant"))
    assert_money_integrity(result, normalized_preferences)


def test_real_no_pace_sample_uses_all_seven_ideas_and_costs_135(normalized_preferences):
    preferences = {**normalized_preferences, "pace": ""}

    result = generate(preferences, load_catalog())

    assert [[item_id(result, day, name) for name in ("Morning", "Afternoon", "Evening")] for day in (1, 2, 3)] == [
        ["paris-luxembourg-gardens", "paris-louvre-museum", "paris-le-procope"],
        ["paris-notre-dame", "paris-eiffel-tower", "paris-cafe-de-flore"],
        ["paris-seine-riverside-walk", None, None],
    ]
    assert result["filled_slots"] == 7
    assert result["total_slots"] == 9
    assert result["estimated_cost"] == Decimal("135.00")
    assert result["unallocated_allowance"] == Decimal("165.00")
    assert result["unused_items"] == []
    assert_money_integrity(result, preferences)


def test_real_60_allowance_sample_schedules_only_three_free_history_ideas(normalized_preferences):
    preferences = {**normalized_preferences, "budget": Decimal("60.00")}

    result = generate(preferences, load_catalog())

    assert [item_id(result, day, "Morning") for day in (1, 2, 3)] == [
        "paris-luxembourg-gardens", "paris-seine-riverside-walk", "paris-notre-dame"
    ]
    assert all(item_id(result, day, "Evening") is None for day in (1, 2, 3))
    assert result["estimated_cost"] == Decimal("0.00")
    assert result["unallocated_allowance"] == Decimal("60.00")
    assert result["filled_slots"] == 3
    assert result["total_slots"] == 6
    assert any(word in notices_text(result) for word in ("meal", "restaurant"))
    assert_money_integrity(result, preferences)


def test_real_food_only_sample_orders_cheaper_cafe_before_procope(normalized_preferences):
    preferences = {**normalized_preferences, "interests": ["food"]}

    result = generate(preferences, load_catalog())

    assert [item_id(result, day, "Morning") for day in (1, 2, 3)] == [None, None, None]
    assert [item_id(result, day, "Evening") for day in (1, 2, 3)] == [
        "paris-cafe-de-flore", "paris-le-procope", None
    ]
    assert result["filled_slots"] == 2
    assert result["estimated_cost"] == Decimal("78.00")
    assert_money_integrity(result, preferences)


def test_real_food_only_one_euro_sample_is_empty_without_invented_meals(normalized_preferences):
    preferences = {**normalized_preferences, "interests": ["food"], "budget": Decimal("1.00")}

    result = generate(preferences, load_catalog())

    assert result["filled_slots"] == 0
    assert result["total_slots"] == 6
    assert result["estimated_cost"] == Decimal("0.00")
    assert result["unallocated_allowance"] == Decimal("1.00")
    assert scheduled_items(result) == []
    assert_money_integrity(result, preferences)


def test_default_catalog_loading_matches_explicit_current_catalog(normalized_preferences):
    implicit = generate(normalized_preferences)
    explicit = generate(normalized_preferences, load_catalog())

    assert implicit == explicit
    assert implicit["estimated_cost"] == Decimal("103.00")

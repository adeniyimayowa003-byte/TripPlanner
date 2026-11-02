"""Predictable daily suggestions from the existing rule-based recommendations.

This module knows nothing about Flask or a browser session. The caller supplies
validated preferences, and the result keeps exact money values for presentation.
"""

from decimal import Decimal

from recommendations import recommend_trip_ideas


DAYTIME_CATEGORIES = {"attraction", "activity"}
RESTAURANT_CATEGORY = {"restaurant"}


def _first_fitting_item(items, categories, used_ids, day_cost, preferences):
    """Scan in recommendation order, skipping rather than discarding costly ideas."""
    for item in items:
        place = item["place"]
        if place["id"] in used_ids or place["category"] not in categories:
            continue

        # Comparing products avoids granting an extra cent from a rounded preview.
        proposed_cost = day_cost + item["estimated_cost"]
        if proposed_cost * preferences["days"] <= preferences["budget"]:
            return item
    return None


def _empty_reason(items, used_ids, slot_name):
    """Describe the actual category, catalog, or allowance limitation at this slot."""
    opening = "No additional matching idea could be scheduled. "
    if not items:
        return (
            opening
            + "The sample catalog has no eligible ideas for these preferences and "
            "allowance; try editing your interests or allowance."
        )

    categories = DAYTIME_CATEGORIES
    if slot_name == "Evening":
        categories = DAYTIME_CATEGORIES | RESTAURANT_CATEGORY
    compatible_unused = [
        item for item in items
        if item["place"]["id"] not in used_ids
        and item["place"]["category"] in categories
    ]
    if compatible_unused:
        # Selection already tried every compatible candidate before leaving a gap.
        return (
            opening
            + "The remaining compatible ideas exceed this day's remaining "
            "allowance; unspent allowance is not transferred between days."
        )
    if slot_name != "Evening":
        return (
            opening
            + "No unused matching attraction or activity remains in the limited "
            "catalog; restaurants are reserved for Evening."
        )
    return (
        opening
        + "No unused matching restaurant, attraction, or activity remains in the "
        "limited catalog; places are never repeated."
    )


def _limitation_notices(preferences, items, recommendation_notices, days,
                        scheduled_items, unused_items, total_slots):
    """Keep explanations tied to eligible data and, importantly, scheduled data."""
    notices = list(recommendation_notices)
    filled_slots = len(scheduled_items)
    if not filled_slots:
        notices.append(
            "No matching ideas could be scheduled. Edit your interests or allowance "
            "to explore other possibilities in the limited sample catalog."
        )
    elif filled_slots < total_slots:
        notices.append(
            f"This is a partial itinerary: {filled_slots} of {total_slots} slots "
            "have suggestions. Catalog limits, slot categories, or daily allowance "
            "can leave gaps; no places are repeated to fill them."
        )

    missing_restaurant_days = sum(
        not any(
            slot["item"] is not None
            and slot["item"]["place"]["category"] == "restaurant"
            for slot in day["slots"]
        )
        for day in days
    )
    if missing_restaurant_days:
        notices.append(
            "Meals are not fully covered. Restaurant suggestions are missing for "
            f"{missing_restaurant_days} of {len(days)} days. Missing meals and "
            "other unscheduled expenses are not included in the estimates."
        )

    if unused_items:
        alternative_label = (
            "alternative remains" if len(unused_items) == 1 else "alternatives remain"
        )
        notices.append(
            f"{len(unused_items)} matching {alternative_label} unused because "
            "of limited slots, category rules, or daily cost limits. Review all "
            "alternatives on the trip ideas page."
        )

    requested_tags = []
    if preferences["pace"]:
        requested_tags.append(preferences["pace"])
    if preferences["family_friendly"]:
        requested_tags.append("family-friendly")
    for tag in requested_tags:
        scheduled_match = any(tag in item["preference_matches"] for item in scheduled_items)
        eligible_match = any(tag in item["preference_matches"] for item in items)
        if not scheduled_match and eligible_match:
            # When no eligible idea has the tag, the inherited notice already
            # explains the limitation. Do not repeat it in different words.
            notices.append(
                f"None of the scheduled ideas is tagged {tag}; this itinerary "
                "cannot confirm that preference, even though a matching tagged "
                "alternative is available on the trip ideas page."
            )

    return list(dict.fromkeys(notices))


def generate_itinerary(preferences, catalog=None):
    """Allocate unique eligible ideas using exact equal daily limits.

    Fill Morning across all days, then Afternoon when present, then Evening.
    Evening prefers a fitting restaurant and otherwise tries an attraction or
    activity. This greedy rule does not backtrack or optimize a real-world route.
    """
    items, recommendation_notices = recommend_trip_ideas(preferences, catalog=catalog)
    slot_names = ["Morning", "Evening"]
    if preferences["pace"] != "relaxed":
        slot_names = ["Morning", "Afternoon", "Evening"]

    days = [
        {
            "number": number,
            "slots": [
                {"name": name, "item": None, "empty_reason": None}
                for name in slot_names
            ],
            "estimated_cost": Decimal("0.00"),
        }
        for number in range(1, preferences["days"] + 1)
    ]

    used_ids = set()
    for slot_index, slot_name in enumerate(slot_names):
        for day in days:
            categories = [DAYTIME_CATEGORIES]
            if slot_name == "Evening":
                categories = [RESTAURANT_CATEGORY, DAYTIME_CATEGORIES]

            selected = None
            for category_group in categories:
                selected = _first_fitting_item(
                    items, category_group, used_ids, day["estimated_cost"], preferences
                )
                if selected is not None:
                    break

            slot = day["slots"][slot_index]
            if selected is None:
                slot["empty_reason"] = _empty_reason(items, used_ids, slot_name)
            else:
                slot["item"] = selected
                used_ids.add(selected["place"]["id"])
                day["estimated_cost"] += selected["estimated_cost"]

    scheduled_items = [
        slot["item"] for day in days for slot in day["slots"]
        if slot["item"] is not None
    ]
    unused_items = [item for item in items if item["place"]["id"] not in used_ids]
    trip_cost = sum((day["estimated_cost"] for day in days), Decimal("0.00"))
    total_slots = len(days) * len(slot_names)

    return {
        "days": days,
        "estimated_cost": trip_cost,
        "unallocated_allowance": preferences["budget"] - trip_cost,
        "filled_slots": len(scheduled_items),
        "total_slots": total_slots,
        "unused_items": unused_items,
        "notices": _limitation_notices(
            preferences, items, recommendation_notices, days,
            scheduled_items, unused_items, total_slots
        ),
    }

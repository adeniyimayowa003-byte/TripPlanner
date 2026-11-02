"""Explainable, rule-based trip ideas from the local sample catalog."""

from copy import deepcopy
from decimal import Decimal

from catalog import load_catalog


def _join_labels(labels):
    """Write a short readable list without hiding the actual matching tags."""
    if len(labels) <= 2:
        return " and ".join(labels)
    return ", ".join(labels[:-1]) + ", and " + labels[-1]


def recommend_trip_ideas(preferences, catalog=None):
    """Return every eligible idea in stable score order and preference notices.

    Preferences have already passed server validation. Optional preferences add
    ranking points; they never bypass the destination, interest, or cost rules.
    """
    places = load_catalog() if catalog is None else catalog
    requested_destination = preferences["destination"].strip().casefold()
    selected_interests = list(dict.fromkeys(preferences["interests"]))
    selected_preferences = []
    if preferences["pace"]:
        selected_preferences.append(preferences["pace"])
    if preferences["family_friendly"]:
        selected_preferences.append("family-friendly")

    items = []
    seen_ids = set()
    for place in places:
        if place["destination"].strip().casefold() != requested_destination:
            continue

        interest_tags = {tag.strip().casefold() for tag in place["interest_tags"]}
        matched_interests = [
            interest for interest in selected_interests
            if interest.casefold() in interest_tags
        ]
        if not matched_interests:
            continue

        # JSON costs may be floats: converting their text avoids binary artifacts.
        cost = Decimal(str(place["estimated_cost"]))
        if cost * preferences["days"] > preferences["budget"]:
            continue
        if place["id"] in seen_ids:
            continue
        seen_ids.add(place["id"])

        preference_tags = {tag.strip().casefold() for tag in place["preference_tags"]}
        preference_matches = [
            preference for preference in selected_preferences
            if preference.casefold() in preference_tags
        ]
        score = 3 * len(matched_interests) + len(preference_matches)
        reason = "Matches " + _join_labels(matched_interests)
        if preference_matches:
            reason += "; tagged " + _join_labels(preference_matches)

        items.append({
            "place": deepcopy(place),
            "estimated_cost": cost,
            "score": score,
            "matched_interests": matched_interests,
            "preference_matches": preference_matches,
            "reason": reason,
        })

    items.sort(key=lambda item: (
        -item["score"],
        item["estimated_cost"],
        item["place"]["name"].casefold(),
        item["place"]["id"],
    ))

    notices = []
    for preference in selected_preferences:
        if not any(preference in item["preference_matches"] for item in items):
            notices.append(
                f"None of the eligible ideas is tagged {preference}; "
                "the sample catalog cannot confirm a match for that preference."
            )
    return items, notices


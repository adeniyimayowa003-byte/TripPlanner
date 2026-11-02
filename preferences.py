"""Validate and normalize preferences submitted in the trip form."""

import re

from catalog import (
    get_destination,
    get_supported_destinations,
    get_supported_interests,
    get_supported_paces,
)
from money import parse_budget


MIN_TRIP_DAYS = 1
MAX_TRIP_DAYS = 14


def validate_trip_preferences(form_data, catalog=None, *, profiles=None):
    """Return canonical preferences, or the original answers plus field errors."""
    submitted_destination = form_data.get("destination", "") or ""
    submitted_days = form_data.get("days", "") or ""
    submitted_budget = form_data.get("budget", "") or ""
    submitted_interests = form_data.getlist("interests")
    submitted_pace = form_data.get("pace", "") or ""
    family_friendly = form_data.get("family_friendly") == "on"

    submitted_values = {
        "destination": submitted_destination,
        "days": submitted_days,
        "budget": submitted_budget,
        "interests": submitted_interests,
        "pace": submitted_pace,
        "family_friendly": family_friendly,
    }
    values = dict(submitted_values)
    values["interests"] = list(submitted_interests)

    raw_destination = submitted_destination.strip()
    raw_days = submitted_days.strip()
    raw_budget = submitted_budget.strip()
    raw_interests = [interest.strip() for interest in submitted_interests]
    raw_pace = submitted_pace.strip().casefold()
    errors = {}

    destination_options = {
        destination.casefold(): destination
        for destination in get_supported_destinations(catalog)
    }
    canonical_destination = destination_options.get(raw_destination.casefold())
    if canonical_destination is None:
        errors["destination"] = "Choose one of the supported destinations."
    else:
        values["destination"] = canonical_destination

    currency = "EUR"
    if profiles is not None and canonical_destination is not None:
        try:
            currency = get_destination(canonical_destination, profiles=profiles)["currency"]
            values["currency"] = currency
        except ValueError:
            errors["destination"] = "Choose one of the supported destinations."

    if re.fullmatch(r"[0-9]+", raw_days) is None:
        errors["days"] = "Enter a whole number of trip days."
    else:
        # Check the range before converting, so very long submissions stay safe.
        significant_days = raw_days.lstrip("0") or "0"
        if len(significant_days) > 2:
            days = MAX_TRIP_DAYS + 1
        else:
            days = int(significant_days)
        if not MIN_TRIP_DAYS <= days <= MAX_TRIP_DAYS:
            errors["days"] = f"Choose between {MIN_TRIP_DAYS} and {MAX_TRIP_DAYS} days."
        else:
            values["days"] = days

    try:
        values["budget"] = parse_budget(raw_budget, currency=currency)
    except ValueError as error:
        errors["budget"] = str(error)

    interest_options = {
        interest.casefold(): interest
        for interest in get_supported_interests(catalog, destination=raw_destination)
    }
    normalized_interests = []
    has_unsupported_interest = False
    for interest in raw_interests:
        canonical_interest = interest_options.get(interest.casefold())
        if canonical_interest is None:
            has_unsupported_interest = True
        elif canonical_interest not in normalized_interests:
            normalized_interests.append(canonical_interest)

    if not normalized_interests:
        errors["interests"] = "Choose at least one interest from the list."
    elif has_unsupported_interest:
        errors["interests"] = "Choose interests from the list."
    else:
        values["interests"] = normalized_interests

    if raw_pace and raw_pace not in get_supported_paces(raw_destination, catalog):
        errors["pace"] = "Choose an available pace for this destination, or no preference."
    else:
        values["pace"] = raw_pace

    if errors:
        return submitted_values, errors

    return values, errors

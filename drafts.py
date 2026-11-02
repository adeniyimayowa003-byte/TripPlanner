"""Translate a valid current draft into JSON-safe data and revalidate it."""

from werkzeug.datastructures import MultiDict

from money import format_money
from currencies import get_currency
from preferences import validate_trip_preferences


DRAFT_VERSION = 1
PREFERENCE_FIELDS = {
    "destination", "days", "budget", "interests", "pace", "family_friendly",
}


def serialize_draft(preferences):
    """Copy normalized preferences into the documented browser-session format."""
    currency = preferences.get("currency", "EUR")
    get_currency(currency)
    result = {
        "version": 2 if "currency" in preferences else DRAFT_VERSION,
        "preferences": {
            "destination": preferences["destination"],
            "days": preferences["days"],
            "budget": format_money(preferences["budget"], currency=currency),
            "interests": list(preferences["interests"]),
            "pace": preferences["pace"],
            "family_friendly": preferences["family_friendly"],
        },
    }
    if result["version"] == 2:
        result["preferences"]["currency"] = currency
    return result


def load_draft(stored, catalog=None, *, profiles=None):
    """Return validated preferences, or None for malformed or stale session data."""
    if not isinstance(stored, dict):
        return None
    versions = {1, 2} if profiles is not None else {1}
    if type(stored.get("version")) is not int or stored["version"] not in versions:
        return None

    preferences = stored.get("preferences")
    if not isinstance(preferences, dict) or not PREFERENCE_FIELDS <= preferences.keys():
        return None

    if profiles is not None:
        if stored["version"] == 1 and (not isinstance(preferences.get("destination"), str)
                                     or preferences["destination"].strip().casefold() != "paris, france"):
            return None
        if stored["version"] == 2 and not isinstance(preferences.get("currency"), str):
            return None

    # bool subclasses int in Python, so days and flags need exact type checks.
    if (
        not isinstance(preferences["destination"], str)
        or type(preferences["days"]) is not int
        or not isinstance(preferences["budget"], str)
        or not isinstance(preferences["interests"], list)
        or not all(isinstance(interest, str) for interest in preferences["interests"])
        or not isinstance(preferences["pace"], str)
        or type(preferences["family_friendly"]) is not bool
    ):
        return None

    # Reuse exactly the form rules, including destination-specific current tags.
    form = MultiDict({
        "destination": preferences["destination"],
        "days": str(preferences["days"]),
        "budget": preferences["budget"],
        "pace": preferences["pace"],
        "family_friendly": "on" if preferences["family_friendly"] else "",
    })
    form.setlist("interests", preferences["interests"])
    values, errors = validate_trip_preferences(form, catalog=catalog, profiles=profiles)
    if not errors and stored["version"] == 2 and values.get("currency") != preferences["currency"]:
        return None
    return None if errors else values

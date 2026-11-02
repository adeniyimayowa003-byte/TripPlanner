"""Self-contained historical trip data, without Flask or database dependencies.

A saved snapshot owns its place details and explanations. Loading one validates
the stored values; it never asks today's catalog or algorithms to recreate it.
"""

from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import unicodedata
from urllib.parse import urlsplit

from itinerary import generate_itinerary
from money import CENT, MAX_BUDGET, daily_allowance
from currencies import get_currency
from maps import build_maps_url
from recommendations import recommend_trip_ideas


SNAPSHOT_VERSION = 2
MAX_TITLE_LENGTH = 80
CENT_TEXT = re.compile(r"[0-9]+\.[0-9]{2}")
COST_NOTE = "Illustrative per-person estimates for a class project; these are not live prices."
BUDGET_NOTE = "Activities and food allowance per person; excludes flights, accommodation, and transport."


class SnapshotValidationError(ValueError):
    """The saved data is unreadable, unsupported, or internally inconsistent."""


def _require(condition, message="The saved snapshot is inconsistent."):
    if not condition:
        raise SnapshotValidationError(message)


def _object(value):
    _require(isinstance(value, dict), "Expected a saved object.")


def _text(value, *, allow_blank=False):
    _require(isinstance(value, str), "Expected saved text.")
    _require(allow_blank or bool(value.strip()), "Saved text must not be empty.")


def _texts(value, *, allow_empty=True):
    _require(isinstance(value, list), "Expected a saved list of text.")
    _require(allow_empty or bool(value), "A saved list must not be empty.")
    for item in value:
        _text(item)


def _integer(value, minimum=0, maximum=None):
    # bool is an int subclass, but True is not a valid version, score, or count.
    _require(type(value) is int and value >= minimum, "Expected a saved integer.")
    _require(maximum is None or value <= maximum, "Saved integer is out of range.")


def _amount(value, allow_decimal, currency="EUR"):
    spec = get_currency(currency)
    pattern = r"[0-9]+" if spec.precision == 0 else CENT_TEXT
    if isinstance(value, str) and re.fullmatch(pattern, value):
        amount = Decimal(value)
    elif allow_decimal and type(value) is Decimal:
        amount = value
    else:
        raise SnapshotValidationError("Money must be exact two-decimal text.")
    _require(amount.is_finite() and amount >= 0, "Money must be finite and nonnegative.")
    _require(amount == amount.quantize(spec.quantum), "Money must use its currency's smallest unit.")
    return amount.quantize(spec.quantum)


def _money_field(record, key, allow_decimal, currency="EUR"):
    record[key] = _amount(record[key], allow_decimal, currency)


def _safe_source(value):
    _text(value)
    _require(not any(char.isspace() or unicodedata.category(char) == "Cc" for char in value),
             "Source links must not contain whitespace or controls.")
    parts = urlsplit(value)
    _require(parts.scheme.casefold() in {"http", "https"} and bool(parts.hostname),
             "Source links must be absolute HTTP or HTTPS references.")
    # Accessing port also detects malformed values such as ':not-a-port'.
    parts.port


def _validate_preferences(preferences, allow_decimal, currency="EUR", version=1):
    _object(preferences)
    _text(preferences["destination"])
    _integer(preferences["days"], 1, 14)
    if version == 2:
        _require(preferences["currency"] == currency, "Saved currency fields must agree.")
    spec = get_currency(currency)
    _money_field(preferences, "budget", allow_decimal, currency)
    _require(spec.minimum <= preferences["budget"] <= spec.maximum, "The saved allowance is out of range.")
    _texts(preferences["interests"], allow_empty=False)
    _require(len(preferences["interests"]) == len(set(preferences["interests"])))
    _text(preferences["pace"], allow_blank=True)
    _require(preferences["pace"] in {"", "relaxed", "active"}, "Unsupported saved pace.")
    _require(type(preferences["family_friendly"]) is bool, "Expected a saved preference flag.")


def _validate_recommendation(item, preferences, allow_decimal, currency="EUR", version=1):
    _object(item)
    place = item["place"]
    _object(place)
    for key in ("id", "name", "destination", "description"):
        _text(place[key])
    _require(place["destination"].strip().casefold() == preferences["destination"].strip().casefold())
    _require(place["category"] in {"attraction", "activity", "restaurant"}, "Unsupported saved category.")
    _texts(place["interest_tags"], allow_empty=False)
    _texts(place["preference_tags"])
    _safe_source(place["source_url"])
    if version == 2:
        _require(place["currency"] == currency)
        _text(place["cost_note"])
        _require(date.fromisoformat(place["reviewed_on"]).isoformat() == place["reviewed_on"])
        location = place["location"]
        _object(location)
        _text(location["address"])
        _safe_source(location["source_url"])
        _require(date.fromisoformat(location["reviewed_on"]).isoformat() == location["reviewed_on"])
        _require(build_maps_url(place["name"], place["destination"], location) is not None,
                 "The saved location is unusable.")
    _money_field(place, "estimated_cost", allow_decimal, currency)
    _money_field(item, "estimated_cost", allow_decimal, currency)
    _require(item["estimated_cost"] == place["estimated_cost"])
    _require(item["estimated_cost"] * preferences["days"] <= preferences["budget"])
    _integer(item["score"])
    _texts(item["matched_interests"], allow_empty=False)
    _texts(item["preference_matches"])
    _text(item["reason"])

    # These checks use only the stored tags and preferences, not today's choices.
    interest_tags = {tag.strip().casefold() for tag in place["interest_tags"]}
    expected_interests = [interest for interest in preferences["interests"]
                          if interest.casefold() in interest_tags]
    requested_tags = [preferences["pace"]] if preferences["pace"] else []
    if preferences["family_friendly"]:
        requested_tags.append("family-friendly")
    preference_tags = {tag.strip().casefold() for tag in place["preference_tags"]}
    expected_tags = [tag for tag in requested_tags if tag.casefold() in preference_tags]
    _require(item["matched_interests"] == expected_interests)
    _require(item["preference_matches"] == expected_tags)
    _require(item["score"] == 3 * len(expected_interests) + len(expected_tags))


def _validate_itinerary(itinerary, preferences, recommendations, allow_decimal, currency="EUR", version=1):
    _object(itinerary)
    days = itinerary["days"]
    _require(isinstance(days, list) and len(days) == preferences["days"])
    names = ["Morning", "Evening"] if preferences["pace"] == "relaxed" else ["Morning", "Afternoon", "Evening"]
    by_id = {item["place"]["id"]: item for item in recommendations}
    scheduled_ids = set()
    trip_cost = Decimal("0.00")
    for number, day in enumerate(days, start=1):
        _object(day)
        _integer(day["number"], 1)
        _require(day["number"] == number)
        slots = day["slots"]
        _require(isinstance(slots, list) and len(slots) == len(names))
        day_cost = Decimal("0.00")
        for name, slot in zip(names, slots):
            _object(slot)
            _require(slot["name"] == name)
            item = slot["item"]
            if item is None:
                _text(slot["empty_reason"])
                continue
            _require(slot["empty_reason"] is None)
            _validate_recommendation(item, preferences, allow_decimal, currency, version)
            place_id = item["place"]["id"]
            _require(place_id not in scheduled_ids and item == by_id.get(place_id))
            if name != "Evening":
                _require(item["place"]["category"] in {"attraction", "activity"})
            scheduled_ids.add(place_id)
            day_cost += item["estimated_cost"]
        _money_field(day, "estimated_cost", allow_decimal, currency)
        _require(day["estimated_cost"] == day_cost)
        # The rounded display allowance must never grant an extra spendable cent.
        _require(day_cost * preferences["days"] <= preferences["budget"])
        trip_cost += day_cost

    unused = itinerary["unused_items"]
    _require(isinstance(unused, list))
    for item in unused:
        _validate_recommendation(item, preferences, allow_decimal, currency, version)
    _require(unused == [item for item in recommendations if item["place"]["id"] not in scheduled_ids])
    for key in ("estimated_cost", "unallocated_allowance"):
        _money_field(itinerary, key, allow_decimal, currency)
    _require(itinerary["estimated_cost"] == trip_cost)
    _require(itinerary["unallocated_allowance"] == preferences["budget"] - trip_cost)
    _integer(itinerary["filled_slots"])
    _integer(itinerary["total_slots"])
    _require(itinerary["filled_slots"] == len(scheduled_ids))
    _require(itinerary["total_slots"] == len(days) * len(names))
    _texts(itinerary["notices"])


def _validated_copy(payload, *, allow_decimal):
    """Validate a new structure so decoding/encoding cannot mutate the caller."""
    try:
        result = deepcopy(payload)
        _object(result)
        _integer(result["version"], 1, SNAPSHOT_VERSION)
        version = result["version"]
        currency = result["currency"]
        get_currency(currency)
        _require(version != 1 or currency == "EUR", "Version 1 retains its original EUR semantics.")
        _text(result["cost_note"])
        _text(result["budget_note"])
        preferences = result["preferences"]
        _validate_preferences(preferences, allow_decimal, currency, version)
        _money_field(result, "daily_budget", allow_decimal, currency)
        _require(result["daily_budget"] == daily_allowance(preferences["budget"], preferences["days"], currency=currency))
        recommendations = result["recommendations"]
        _require(isinstance(recommendations, list))
        for item in recommendations:
            _validate_recommendation(item, preferences, allow_decimal, currency, version)
        ids = [item["place"]["id"] for item in recommendations]
        _require(len(ids) == len(set(ids)), "Saved recommendation IDs must be unique.")
        _texts(result["recommendation_notices"])
        _validate_itinerary(result["itinerary"], preferences, recommendations, allow_decimal, currency, version)
        return result
    except SnapshotValidationError:
        raise
    except (KeyError, TypeError, ValueError, InvalidOperation, OverflowError, RecursionError) as error:
        raise SnapshotValidationError("The saved snapshot is unreadable or inconsistent.") from error


def _money_fields(payload):
    """Yield only version 1's documented money paths, including copied records."""
    yield payload["preferences"], "budget"
    yield payload, "daily_budget"
    itinerary = payload["itinerary"]
    yield itinerary, "estimated_cost"
    yield itinerary, "unallocated_allowance"
    records = list(payload["recommendations"]) + list(itinerary["unused_items"])
    for day in itinerary["days"]:
        yield day, "estimated_cost"
        records.extend(slot["item"] for slot in day["slots"] if slot["item"] is not None)
    for item in records:
        yield item, "estimated_cost"
        yield item["place"], "estimated_cost"


def dump_snapshot(payload):
    """Return canonical JSON; both cent-text and decoded Decimal money are valid."""
    decoded = _validated_copy(payload, allow_decimal=True)
    for record, key in _money_fields(decoded):
        if isinstance(record[key], Decimal):
            precision = get_currency(decoded["currency"]).precision
            record[key] = format(record[key], f".{precision}f")
    try:
        return json.dumps(decoded, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise SnapshotValidationError("The snapshot cannot be serialized.") from error


def _reject_nonfinite(value):
    raise SnapshotValidationError("Non-finite JSON numbers are not supported.")


def load_snapshot(raw_json):
    """Read a historical snapshot and restore all monetary fields to Decimal."""
    try:
        _require(isinstance(raw_json, str), "Expected snapshot JSON text.")
        payload = json.loads(raw_json, parse_constant=_reject_nonfinite)
    except (ValueError, TypeError, RecursionError) as error:
        raise SnapshotValidationError("The saved snapshot is not readable JSON.") from error
    return _validated_copy(payload, allow_decimal=False)


def snapshot_fingerprint(payload):
    """Hash complete canonical content, excluding external save metadata/title."""
    return hashlib.sha256(dump_snapshot(payload).encode("utf-8")).hexdigest()


def build_snapshot(preferences, catalog):
    """Capture every idea and scheduled result from one explicit catalog list."""
    items, notices = recommend_trip_ideas(preferences, catalog=catalog)
    payload = {
        "version": SNAPSHOT_VERSION if "currency" in preferences else 1,
        "currency": preferences.get("currency", "EUR"),
        "cost_note": COST_NOTE,
        "budget_note": BUDGET_NOTE,
        "preferences": deepcopy(preferences),
        "daily_budget": daily_allowance(preferences["budget"], preferences["days"], currency=preferences.get("currency", "EUR")),
        "recommendations": items,
        "recommendation_notices": notices,
        "itinerary": generate_itinerary(preferences, catalog=catalog),
    }
    # Catalog amounts are JSON numbers. Convert their decimal text here only;
    # the public persistence encoder must reject arbitrary float money inputs.
    for record, key in _money_fields(payload):
        record[key] = Decimal(str(record[key]))
    return json.loads(dump_snapshot(payload))


def normalize_trip_name(raw, preferences):
    """Validate literal title text; reject controls before trimming whitespace."""
    if raw is None:
        raw = ""
    if not isinstance(raw, str):
        raise ValueError("Enter a trip name as text.")
    if any(unicodedata.category(char) == "Cc" for char in raw):
        raise ValueError("Use one line without tabs or control characters.")
    title = raw.strip()
    if not title:
        suffix = f" — {preferences['days']}-day trip"
        destination = preferences["destination"].strip()
        title = destination[:MAX_TITLE_LENGTH - len(suffix)].rstrip() + suffix
    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError("Use a trip name with at most 80 characters.")
    return title

"""Load city profiles, validate release data, and search the sample catalog."""

from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

from currencies import get_currency
from maps import build_maps_url


CATALOG_FILE = Path(__file__).parent / "data" / "places.json"
DESTINATIONS_FILE = Path(__file__).parent / "data" / "destinations.json"
_STABLE_ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
_INTEREST_TAGS = {
    "architecture", "art", "culture", "food", "history", "nature", "views",
    "shopping", "adventure",
}
_PREFERENCE_TAGS = {"relaxed", "active", "family-friendly"}


class UnsupportedDestinationError(ValueError):
    """Raised when the sample catalog has no entries for a destination."""


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonblank text.")
    if any(unicodedata.category(character) in {"Cc", "Cs", "Zl", "Zp"}
           for character in value):
        raise ValueError(f"{label} must not contain control characters.")


def _require_id(value, label):
    _require_text(value, label)
    if _STABLE_ID.fullmatch(value) is None:
        raise ValueError(f"{label} must use lowercase words or numbers separated by hyphens.")


def _profiles_by_name(profiles):
    """Validate supplied profiles without modifying or caching their records."""
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("Destination profiles must be a nonempty list.")
    ids = set()
    by_name = {}
    for profile in profiles:
        if not isinstance(profile, dict):
            raise ValueError("Each destination profile must be an object.")
        _require_id(profile.get("id"), "Destination ID")
        for field in ("name", "country"):
            value = profile.get(field)
            _require_text(value, f"Destination {field}")
            if value != value.strip():
                raise ValueError(f"Destination {field} must not have surrounding whitespace.")
        get_currency(profile.get("currency"))
        name = profile["name"].casefold()
        if profile["id"] in ids or name in by_name:
            raise ValueError("Destination IDs and names must be unique.")
        ids.add(profile["id"])
        by_name[name] = profile
    return by_name


def load_destinations(path=None):
    """Read fresh version-1 city profiles from the bundled or supplied file."""
    source = DESTINATIONS_FILE if path is None else Path(path)
    with source.open(encoding="utf-8") as destination_file:
        document = json.load(destination_file)
    if (not isinstance(document, dict)
            or type(document.get("version")) is not int
            or document["version"] != 1):
        raise ValueError("Destination data must use version 1.")
    profiles = document.get("destinations")
    _profiles_by_name(profiles)
    return profiles


def get_destination(name, profiles=None):
    """Return an owned canonical profile, ignoring input case and edge spaces."""
    _require_text(name, "Destination")
    choices = load_destinations() if profiles is None else profiles
    profile = _profiles_by_name(choices).get(name.strip().casefold())
    if profile is None:
        raise UnsupportedDestinationError("Choose one of the supported destinations.")
    return deepcopy(profile)


def _require_source(value):
    _require_text(value, "Source URL")
    if any(character.isspace() for character in value) or "\\" in value:
        raise ValueError("Source URLs must not contain whitespace or backslashes.")
    parts = urlsplit(value)
    if (parts.scheme != "https" or not parts.hostname
            or parts.username is not None or parts.password is not None):
        raise ValueError("Source URLs must be absolute HTTPS references without credentials.")
    # Accessing port also rejects malformed values such as ':not-a-port'.
    parts.port


def _require_review_date(value):
    _require_text(value, "Review date")
    if date.fromisoformat(value).isoformat() != value:
        raise ValueError("Review dates must use YYYY-MM-DD.")


def _require_tags(value, allowed, label, *, allow_empty=False):
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{label} must be a list of supported tags.")
    for tag in value:
        _require_text(tag, label)
        if tag not in allowed:
            raise ValueError(f"{label} contains an unsupported tag.")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} must not repeat a tag.")


def validate_release_catalog(places, profiles=None):
    """Reject malformed release records without changing the supplied data.

    This checks structure and consistency. Real source review and minimum
    released coverage per city remain separate requirements; QA fixtures are
    useful for validation tests but never establish real travel facts.
    """
    choices = load_destinations() if profiles is None else profiles
    by_name = _profiles_by_name(choices)
    if not isinstance(places, list) or not places:
        raise ValueError("Release places must be a nonempty list.")
    ids = set()
    for place in places:
        if not isinstance(place, dict):
            raise ValueError("Each release place must be an object.")
        _require_id(place.get("id"), "Place ID")
        if place["id"] in ids:
            raise ValueError("Place IDs must be unique across all destinations.")
        ids.add(place["id"])
        for field in ("name", "destination", "description", "cost_note"):
            _require_text(place.get(field), f"Place {field}")
        destination = by_name.get(place["destination"].casefold())
        if destination is None or place["destination"] != destination["name"]:
            raise ValueError("A place must use a known canonical destination.")
        spec = get_currency(place.get("currency"))
        if spec.code != destination["currency"]:
            raise ValueError("A place's currency must match its destination.")
        if place.get("category") not in ("attraction", "activity", "restaurant"):
            raise ValueError("A place must have a supported category.")
        _require_tags(place.get("interest_tags"), _INTEREST_TAGS, "Interests")
        _require_tags(place.get("preference_tags"), _PREFERENCE_TAGS, "Preferences", allow_empty=True)

        cost = place.get("estimated_cost")
        pattern = r"[0-9]+" if spec.precision == 0 else r"[0-9]+\.[0-9]{2}"
        if not isinstance(cost, str) or re.fullmatch(pattern, cost) is None:
            raise ValueError("Place costs must be exact nonnegative text at their currency precision.")
        amount = Decimal(cost)
        if not amount.is_finite() or amount < 0:
            raise ValueError("Place costs must be finite and nonnegative.")
        _require_source(place.get("source_url"))
        _require_review_date(place.get("reviewed_on"))

        location = place.get("location")
        if not isinstance(location, dict):
            raise ValueError("A release place needs a reviewed location object.")
        _require_text(location.get("address"), "Place address")
        _require_source(location.get("source_url"))
        _require_review_date(location.get("reviewed_on"))
        if build_maps_url(place["name"], destination["name"], location) is None:
            raise ValueError("A release place needs a usable address and valid optional coordinates.")


def load_catalog():
    """Return the sample places stored in the project's JSON data file."""
    with CATALOG_FILE.open(encoding="utf-8") as catalog_file:
        catalog_data = json.load(catalog_file)

    return catalog_data["places"]


def get_supported_destinations(catalog=None):
    """Return each destination in the catalog once, in alphabetical order."""
    places = load_catalog() if catalog is None else catalog
    destinations = {place["destination"].strip() for place in places}

    return sorted(destinations, key=str.casefold)


def get_supported_interests(catalog=None, *, destination=None):
    """Return sorted interest choices, optionally for one destination only."""
    places = load_catalog() if catalog is None else catalog
    if destination is not None:
        requested_destination = destination.strip().casefold()
        places = [
            place for place in places
            if place["destination"].strip().casefold() == requested_destination
        ]
    interests = {
        tag.strip()
        for place in places
        for tag in place["interest_tags"]
        if tag.strip()
    }

    return sorted(interests, key=str.casefold)


def get_supported_paces(destination, catalog=None):
    """Offer known pace choices only when this destination has matching tags."""
    places = load_catalog() if catalog is None else catalog
    requested_destination = destination.strip().casefold()
    known_paces = {"relaxed", "active"}
    paces = {
        tag.strip().casefold()
        for place in places
        if place["destination"].strip().casefold() == requested_destination
        for tag in place["preference_tags"]
        if tag.strip().casefold() in known_paces
    }
    return sorted(paces)


def get_places_for_destination(destination, catalog=None):
    """Return places for a destination, ignoring letter case and extra spaces."""
    if not isinstance(destination, str) or not destination.strip():
        raise UnsupportedDestinationError("Please provide a supported destination.")

    places = load_catalog() if catalog is None else catalog
    requested_destination = destination.strip().casefold()
    matches = [
        place
        for place in places
        if place["destination"].strip().casefold() == requested_destination
    ]

    if not matches:
        raise UnsupportedDestinationError(
            f"We don't have sample places for '{destination.strip()}' yet."
        )

    return matches

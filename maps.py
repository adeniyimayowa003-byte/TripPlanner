"""Build external Google Maps search links locally, without a key or request."""

from decimal import Decimal, InvalidOperation
import unicodedata
from urllib.parse import urlencode


_SEARCH_URL = "https://www.google.com/maps/search/"
_MAX_URL_LENGTH = 2048


def _clean_text(value):
    """Check controls before trimming; keep ordinary Unicode as query data."""
    if not isinstance(value, str) or len(value) > _MAX_URL_LENGTH:
        return None
    if any(unicodedata.category(character) in {"Cc", "Cs", "Zl", "Zp"}
           for character in value):
        return None
    return value.strip() or None


def _coordinate(value, limit):
    """Return exact finite decimal text, including zero and edge coordinates."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        return None
    try:
        text = str(value)
        if len(text) > _MAX_URL_LENGTH:
            return None
        amount = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not amount.is_finite() or not -limit <= amount <= limit:
        return None
    # A short input such as 1e-999999999 must not expand into a huge string.
    if abs(amount.as_tuple().exponent) > _MAX_URL_LENGTH:
        return None
    return format(amount, "f")


def build_maps_url(name, destination, location):
    """Return a safe search URL, or None when the supplied location is unusable.

    Callers own source review. This helper never verifies an address through a
    provider, guesses a missing location, or reads the current travel catalog.
    """
    name = _clean_text(name)
    destination = _clean_text(destination)
    if not name or not destination or not isinstance(location, dict):
        return None
    address = _clean_text(location.get("address"))
    if not address:
        return None

    query = f"{name}, {address}, {destination}"
    if "latitude" in location or "longitude" in location:
        latitude = _coordinate(location.get("latitude"), 90)
        longitude = _coordinate(location.get("longitude"), 180)
        if latitude is None or longitude is None:
            return None
        query = f"{latitude},{longitude}"

    parameters = {"api": "1", "query": query}
    if "place_id" in location:
        place_id = _clean_text(location["place_id"])
        if not place_id:
            return None
        parameters["query_place_id"] = place_id

    # The scheme/host/path are fixed. All supplied text stays encoded data.
    url = _SEARCH_URL + "?" + urlencode(parameters)
    return url if len(url) <= _MAX_URL_LENGTH else None

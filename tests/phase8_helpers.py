"""Independent Phase 8 examples, never production travel recommendations.

Synthetic foreign-city records deliberately use QA names/example.com addresses.
They test types, currencies and arithmetic, not real-world place verification.
The two frozen Paris files preserve the original pre-expansion example.
"""

from copy import deepcopy
from decimal import Decimal
import importlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).with_name("fixtures")
LEGACY_SHA256 = "faa80e3581949c832e06292142ee86c5125377fcc395b78b5b2171bab427cbfb"
CITY_PROFILES = (
    {"id": "paris-fr", "name": "Paris, France", "country": "France", "currency": "EUR"},
    {"id": "lagos-ng", "name": "Lagos, Nigeria", "country": "Nigeria", "currency": "NGN"},
    {"id": "london-gb", "name": "London, United Kingdom", "country": "United Kingdom", "currency": "GBP"},
    {"id": "new-york-us", "name": "New York City, United States", "country": "United States", "currency": "USD"},
    {"id": "tokyo-jp", "name": "Tokyo, Japan", "country": "Japan", "currency": "JPY"},
    {"id": "cape-town-za", "name": "Cape Town, South Africa", "country": "South Africa", "currency": "ZAR"},
)
SCALE = {"EUR": 1, "NGN": 1000, "GBP": 1, "USD": 1, "JPY": 100, "ZAR": 1}
MONEY_KEYS = {"budget", "daily_budget", "estimated_cost", "unallocated_allowance"}


def api_symbol(module_name, name):
    """Missing future code is an assertion inside a case, not discovery failure."""
    assert importlib.util.find_spec(module_name) is not None, f"Phase 8 requires the {module_name} module."
    module = importlib.import_module(module_name)
    assert hasattr(module, name), f"Phase 8 requires {module_name}.{name}."
    return getattr(module, name)


def legacy_catalog():
    return json.loads((FIXTURES / "phase7-paris-catalog.json").read_text(encoding="utf-8"))["places"]


def legacy_snapshot_text():
    return (FIXTURES / "phase7-paris-snapshot.json").read_text(encoding="utf-8").strip()


def canonical(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def amount_text(amount, code):
    return format(Decimal(str(amount)), ".0f" if code == "JPY" else ".2f")


def profile_for(code):
    return deepcopy(next(profile for profile in CITY_PROFILES if profile["currency"] == code))


def qa_location(profile, original_id):
    return {
        "address": f"10 QA Test Street, {profile['name']}",
        "source_url": f"https://example.com/fixtures/{profile['id']}/{original_id}",
        "reviewed_on": "2026-10-26",
    }


def synthetic_catalog(profiles=None):
    """Eight independent test records per city; never a pretend real catalog."""
    places = []
    for profile in CITY_PROFILES if profiles is None else profiles:
        for original in legacy_catalog():
            place = deepcopy(original)
            code = profile["currency"]
            place.update({
                "id": f"qa-{profile['id']}-{original['id']}",
                "name": f"QA {original['name']}",
                "destination": profile["name"], "currency": code,
                "estimated_cost": amount_text(Decimal(str(original["estimated_cost"])) * SCALE[code], code),
                "source_url": f"https://example.com/fixtures/{profile['id']}/{original['id']}",
                "reviewed_on": "2026-10-26",
                "cost_note": "Illustrative QA estimate, not a real local price.",
                "location": qa_location(profile, original["id"]),
            })
            places.append(place)
        extra = deepcopy(places[-1])
        extra.update({
            "id": f"qa-{profile['id']}-shopping", "name": "QA Shopping Example",
            "category": "activity", "interest_tags": ["shopping", "culture"],
            "preference_tags": [], "estimated_cost": amount_text(0, profile["currency"]),
        })
        places.append(extra)
    return places


def qa_preferences(profile):
    return {
        "destination": profile["name"], "currency": profile["currency"],
        "days": 3, "budget": Decimal(300) * SCALE[profile["currency"]],
        "interests": ["food", "history"], "pace": "relaxed", "family_friendly": True,
    }


def independent_v2_snapshot(profile):
    """Transform the frozen valid v1 math, without calling future builders."""
    code = profile["currency"]

    def copy_value(value, key=None):
        if key in MONEY_KEYS:
            return amount_text(Decimal(value) * SCALE[code], code)
        if isinstance(value, list):
            return [copy_value(item) for item in value]
        if isinstance(value, dict):
            result = {name: copy_value(item, name) for name, item in value.items()}
            if "destination" in result:
                result["destination"] = profile["name"]
            if {"id", "category", "interest_tags"} <= result.keys():
                old_id = result["id"]
                result.update({
                    "id": f"qa-{profile['id']}-{old_id}", "currency": code,
                    "name": f"QA {result['name']}",
                    "source_url": f"https://example.com/fixtures/{profile['id']}/{old_id}",
                    "reviewed_on": "2026-10-26",
                    "cost_note": "Illustrative QA estimate, not a real local price.",
                    "location": qa_location(profile, old_id),
                })
            return result
        return value

    payload = copy_value(json.loads(legacy_snapshot_text()))
    payload["version"] = 2
    payload["currency"] = code
    payload["preferences"]["currency"] = code
    return payload


def money_paths(value, path=()):
    """Enumerate the named money paths independently of a future serializer."""
    if isinstance(value, dict):
        for name, item in value.items():
            if name in MONEY_KEYS:
                yield (*path, name), item
            else:
                yield from money_paths(item, (*path, name))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from money_paths(item, (*path, index))


def at_path(value, path):
    for key in path:
        value = value[key]
    return value


def set_path(value, path, replacement):
    at_path(value, path[:-1])[path[-1]] = replacement

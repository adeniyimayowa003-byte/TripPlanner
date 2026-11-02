"""Phase 8 profile/data contracts, with explicit frozen and synthetic examples."""

from collections import Counter
from copy import deepcopy
from datetime import date
from decimal import Decimal
import hashlib
import json
from urllib.parse import urlsplit

import pytest

from phase8_helpers import (
    CITY_PROFILES, LEGACY_SHA256, ROOT, SCALE, api_symbol, canonical,
    independent_v2_snapshot, legacy_catalog, legacy_snapshot_text,
    money_paths, qa_preferences, synthetic_catalog,
)


def test_frozen_legacy_snapshot_bytes_hash_and_sample_are_independent():
    raw = legacy_snapshot_text()
    payload = json.loads(raw)
    assert canonical(payload) == raw
    assert hashlib.sha256(raw.encode("utf-8")).hexdigest() == LEGACY_SHA256
    assert payload["version"] == 1 and payload["currency"] == "EUR"
    assert len(payload["recommendations"]) == 7
    assert payload["itinerary"]["estimated_cost"] == "103.00"
    assert payload["itinerary"]["unallocated_allowance"] == "197.00"
    assert sum(slot["item"] is not None for day in payload["itinerary"]["days"] for slot in day["slots"]) == 6


def test_frozen_legacy_catalog_preserves_seven_ids_without_reading_the_live_catalog():
    places = legacy_catalog()
    assert len(places) == 7
    assert {place["id"] for place in places} == {
        "paris-eiffel-tower", "paris-louvre-museum", "paris-notre-dame",
        "paris-luxembourg-gardens", "paris-seine-riverside-walk",
        "paris-cafe-de-flore", "paris-le-procope",
    }
    places[0]["name"] = "mutated test copy"
    assert legacy_catalog()[0]["name"] == "Eiffel Tower"


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_synthetic_six_city_fixture_has_honest_structure_and_independent_sample_math(profile):
    from itinerary import generate_itinerary
    from recommendations import recommend_trip_ideas

    places = synthetic_catalog([profile])
    preferences = qa_preferences(profile)
    assert len(places) == 8
    assert sum(place["category"] == "restaurant" for place in places) == 2
    assert len({tag for place in places for tag in place["interest_tags"]}) >= 4
    assert all(place["name"].startswith("QA ") for place in places)
    assert all(urlsplit(place["source_url"]).hostname == "example.com" for place in places)
    items, _ = recommend_trip_ideas(preferences, catalog=places)
    itinerary = generate_itinerary(preferences, catalog=places)
    assert len(items) == 7
    assert itinerary["estimated_cost"] == Decimal(103) * SCALE[profile["currency"]]
    assert itinerary["unallocated_allowance"] == Decimal(197) * SCALE[profile["currency"]]
    assert len({slot["item"]["place"]["id"] for day in itinerary["days"] for slot in day["slots"] if slot["item"]}) == 6


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_independent_v2_snapshot_fixture_preserves_all_scaled_nested_money_and_locations(profile):
    payload = independent_v2_snapshot(profile)
    code = profile["currency"]
    assert payload["version"] == 2 and payload["currency"] == code
    assert payload["preferences"]["currency"] == code
    assert Decimal(payload["itinerary"]["estimated_cost"]) == Decimal(103) * SCALE[code]
    assert Decimal(payload["itinerary"]["unallocated_allowance"]) == Decimal(197) * SCALE[code]
    assert len(list(money_paths(payload))) == len(list(money_paths(json.loads(legacy_snapshot_text()))))
    assert all(Decimal(value).as_tuple().exponent == (0 if code == "JPY" else -2) for _, value in money_paths(payload))
    by_id = {item["place"]["id"]: item for item in payload["recommendations"]}
    for day in payload["itinerary"]["days"]:
        assert sum((Decimal(slot["item"]["estimated_cost"]) for slot in day["slots"] if slot["item"]), Decimal(0)) == Decimal(day["estimated_cost"])
        assert Decimal(day["estimated_cost"]) * 3 <= Decimal(payload["preferences"]["budget"])
        for slot in day["slots"]:
            if slot["item"]:
                assert slot["item"] == by_id[slot["item"]["place"]["id"]]
                assert "QA Test Street" in slot["item"]["place"]["location"]["address"]


def test_real_destination_profiles_file_has_exact_six_approved_canonical_choices():
    path = ROOT / "data" / "destinations.json"
    assert path.is_file(), "Phase 8 requires data/destinations.json, not a pretend worldwide dropdown."
    document = json.loads(path.read_text(encoding="utf-8"))
    assert type(document["version"]) is int and document["version"] == 1
    profiles = document["destinations"]
    assert len(profiles) == 6
    assert {tuple(profile[key] for key in ("id", "name", "country", "currency")) for profile in profiles} == {
        tuple(profile[key] for key in ("id", "name", "country", "currency")) for profile in CITY_PROFILES
    }


def test_profile_loader_reads_an_explicit_file_and_returns_fresh_data(tmp_path):
    load_destinations = api_symbol("catalog", "load_destinations")
    path = tmp_path / "destinations.json"
    path.write_text(canonical({"version": 1, "destinations": list(CITY_PROFILES)}), encoding="utf-8")
    first = load_destinations(path=path)
    assert {profile["name"] for profile in first} == {profile["name"] for profile in CITY_PROFILES}
    first[0]["name"] = "changed caller copy"
    assert load_destinations(path=path)[0]["name"] == CITY_PROFILES[0]["name"]


def test_default_city_helpers_use_the_published_profiles():
    load_destinations = api_symbol("catalog", "load_destinations")
    get_destination = api_symbol("catalog", "get_destination")
    profiles = load_destinations()
    assert {profile["id"] for profile in profiles} == {profile["id"] for profile in CITY_PROFILES}
    for expected in CITY_PROFILES:
        assert get_destination(expected["name"]) == expected


@pytest.mark.parametrize("bad_kind", ["invalid-json", "wrong-version", "bool-version", "empty", "duplicate-id", "duplicate-name", "unknown-currency", "missing-country"])
def test_profile_loader_rejects_malformed_or_ambiguous_choices(tmp_path, bad_kind):
    load_destinations = api_symbol("catalog", "load_destinations")
    document = {"version": 1, "destinations": deepcopy(list(CITY_PROFILES))}
    if bad_kind == "wrong-version":
        document["version"] = 99
    elif bad_kind == "bool-version":
        document["version"] = True
    elif bad_kind == "empty":
        document["destinations"] = []
    elif bad_kind == "duplicate-id":
        document["destinations"][1]["id"] = document["destinations"][0]["id"]
    elif bad_kind == "duplicate-name":
        document["destinations"][1]["name"] = "  PARIS, FRANCE  "
    elif bad_kind == "unknown-currency":
        document["destinations"][0]["currency"] = "XXX"
    elif bad_kind == "missing-country":
        document["destinations"][0].pop("country")
    path = tmp_path / "bad-profiles.json"
    path.write_text("{" if bad_kind == "invalid-json" else canonical(document), encoding="utf-8")
    with pytest.raises(ValueError):
        load_destinations(path=path)


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_destination_lookup_uses_supplied_canonical_profiles_not_a_submitted_currency(profile):
    get_destination = api_symbol("catalog", "get_destination")
    profiles = deepcopy(list(CITY_PROFILES))
    before = deepcopy(profiles)
    result = get_destination("  " + profile["name"].upper() + "  ", profiles=profiles)
    assert result == profile
    result["currency"] = "XXX"
    assert profiles == before


@pytest.mark.parametrize("destination", [None, True, "", "Atlantis", "<script>Tokyo</script>"])
def test_unknown_destination_is_rejected_not_mapped_to_a_default_currency(destination):
    get_destination = api_symbol("catalog", "get_destination")
    with pytest.raises(ValueError):
        get_destination(destination, profiles=list(CITY_PROFILES))


def test_release_catalog_validator_accepts_supplied_consistent_examples_without_mutation():
    validate_release_catalog = api_symbol("catalog", "validate_release_catalog")
    places = synthetic_catalog()
    profiles = deepcopy(list(CITY_PROFILES))
    before = deepcopy((places, profiles))
    assert validate_release_catalog(places, profiles=profiles) is None
    assert (places, profiles) == before


@pytest.mark.parametrize("field,value", [
    ("id", ""), ("name", ""), ("destination", "Unknown city"), ("currency", "JPY"),
    ("estimated_cost", None), ("estimated_cost", True), ("estimated_cost", "-1.00"),
    ("estimated_cost", "NaN"), ("estimated_cost", "1.001"),
    ("category", "hotel"), ("interest_tags", []), ("interest_tags", "history"),
    ("preference_tags", [True]), ("source_url", "javascript:alert(1)"),
    ("reviewed_on", "not-a-date"), ("cost_note", ""), ("location", None),
    ("location", {"address": ""}),
])
def test_release_catalog_validator_rejects_wrong_units_types_and_missing_provenance(field, value):
    validate_release_catalog = api_symbol("catalog", "validate_release_catalog")
    places = synthetic_catalog()
    places[0][field] = value
    with pytest.raises(ValueError, match=r".+"):
        validate_release_catalog(places, profiles=list(CITY_PROFILES))


@pytest.mark.parametrize("latitude,longitude", [("91", "0"), ("0", "-181"), ("NaN", "0"), (True, False), ("1", None)])
def test_release_catalog_validator_checks_optional_coordinate_pairs(latitude, longitude):
    validate_release_catalog = api_symbol("catalog", "validate_release_catalog")
    places = synthetic_catalog()
    places[0]["location"].update(latitude=latitude, longitude=longitude)
    with pytest.raises(ValueError):
        validate_release_catalog(places, profiles=list(CITY_PROFILES))


def test_release_catalog_validator_rejects_duplicate_ids_even_across_cities():
    validate_release_catalog = api_symbol("catalog", "validate_release_catalog")
    places = synthetic_catalog()
    places[8]["id"] = places[0]["id"]
    with pytest.raises(ValueError):
        validate_release_catalog(places, profiles=list(CITY_PROFILES))


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_actual_release_catalog_has_reviewed_variety_currency_and_location_for_each_city(profile):
    document = json.loads((ROOT / "data" / "places.json").read_text(encoding="utf-8"))
    places = [place for place in document["places"] if place["destination"] == profile["name"]]
    assert len(places) >= 8, f"{profile['name']} needs at least eight released places."
    assert Counter(place["category"] for place in places)["restaurant"] >= 2
    assert len({tag for place in places for tag in place["interest_tags"]}) >= 4
    assert any(Decimal(str(place["estimated_cost"])) == 0 for place in places)
    assert any(Decimal(str(place["estimated_cost"])) > 0 for place in places)
    for place in places:
        assert place["currency"] == profile["currency"]
        assert isinstance(place["estimated_cost"], str), "Release money is exact native-currency text."
        amount = Decimal(place["estimated_cost"])
        assert amount.is_finite() and amount >= 0
        assert amount.as_tuple().exponent == (0 if profile["currency"] == "JPY" else -2)
        assert date.fromisoformat(place["reviewed_on"])
        assert "illustrative" in place["cost_note"].casefold() and "live" in place["cost_note"].casefold()
        assert place["location"]["address"].strip()
        assert date.fromisoformat(place["location"]["reviewed_on"])
        for source in (place["source_url"], place["location"]["source_url"]):
            parts = urlsplit(source)
            assert parts.scheme == "https" and parts.hostname
            assert parts.hostname not in {"example.com", "localhost", "127.0.0.1"}
        assert not place["name"].startswith("QA "), "Test examples are never shipped as reviewed travel data."


def test_actual_release_keeps_original_paris_identifiers_and_no_unapproved_cities():
    places = json.loads((ROOT / "data" / "places.json").read_text(encoding="utf-8"))["places"]
    assert {place["id"] for place in legacy_catalog()} <= {place["id"] for place in places}
    assert len({place["id"] for place in places}) == len(places)
    assert {place["destination"] for place in places} <= {profile["name"] for profile in CITY_PROFILES}

"""Versioned snapshots: independently specified v2 data and frozen v1 history."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import sqlite3

import pytest

from phase8_helpers import (
    CITY_PROFILES, LEGACY_SHA256, canonical, independent_v2_snapshot,
    legacy_snapshot_text, money_paths, profile_for, qa_preferences, set_path,
    synthetic_catalog,
)


def forbid_replanning(monkeypatch):
    """Historical reads must not reconstruct a result using today's data."""
    import catalog
    import itinerary
    import recommendations
    import snapshots

    def forbidden(*args, **kwargs):
        pytest.fail("Reading historical content must not consult today's travel data or algorithms.")

    for module, names in (
        (catalog, ("load_catalog", "load_destinations", "get_destination")),
        (recommendations, ("recommend_trip_ideas",)),
        (itinerary, ("generate_itinerary",)),
        (snapshots, ("recommend_trip_ideas", "generate_itinerary")),
    ):
        for name in names:
            if hasattr(module, name):
                monkeypatch.setattr(module, name, forbidden)


def stored_rows(path):
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT id, title, created_at, fingerprint, snapshot_json FROM saved_trips ORDER BY id"
        ).fetchall()


def snapshot_records(payload):
    records = list(payload["recommendations"]) + list(payload["itinerary"]["unused_items"])
    records.extend(slot["item"] for day in payload["itinerary"]["days"] for slot in day["slots"] if slot["item"])
    return records


@pytest.fixture
def original_v1_database(tmp_path):
    """Seed exact historical bytes directly, never with a future serializer."""
    path = tmp_path / "old-paris.sqlite3"
    raw = legacy_snapshot_text()
    title = "Original Paris trip"
    digest = hashlib.sha256(canonical({"title": title, "snapshot": json.loads(raw)}).encode("utf-8")).hexdigest()
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE saved_trips (id INTEGER PRIMARY KEY CHECK (id > 0), "
            "title TEXT NOT NULL, created_at TEXT NOT NULL, "
            "fingerprint TEXT NOT NULL UNIQUE, snapshot_json TEXT NOT NULL)"
        )
        connection.execute("PRAGMA user_version = 1")
        connection.execute("INSERT INTO saved_trips VALUES (?, ?, ?, ?, ?)", (
            73, title, "2026-09-28T00:00:00.000000+00:00", digest, raw,
        ))
    return path, stored_rows(path)[0]


def test_frozen_v1_decodes_reencodes_and_hashes_identically_without_replanning(monkeypatch):
    from snapshots import dump_snapshot, load_snapshot, snapshot_fingerprint

    raw = legacy_snapshot_text()
    forbid_replanning(monkeypatch)
    decoded = load_snapshot(raw)
    assert decoded["version"] == 1 and decoded["currency"] == "EUR"
    assert all(isinstance(amount, Decimal) for _, amount in money_paths(decoded))
    assert dump_snapshot(decoded) == raw
    assert snapshot_fingerprint(decoded) == LEGACY_SHA256
    assert "location" not in decoded["recommendations"][0]["place"], "Do not invent today's location for an old trip."


def test_original_v1_repository_reads_preserve_every_stored_column(original_v1_database, monkeypatch):
    from saved_trips import get_trip, list_trips

    path, before = original_v1_database
    forbid_replanning(monkeypatch)
    record = get_trip(path, 73)
    assert record["available"] and record["id"] == 73
    assert record["snapshot"]["version"] == 1
    assert record["snapshot"]["itinerary"]["estimated_cost"] == Decimal("103.00")
    assert list_trips(path) == [record]
    assert stored_rows(path) == [before]


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_new_snapshot_freezes_v2_currency_locations_and_exact_money_without_mutating_inputs(profile):
    from snapshots import build_snapshot, dump_snapshot, load_snapshot, snapshot_fingerprint

    preferences = qa_preferences(profile)
    places = synthetic_catalog([profile])
    before = deepcopy((preferences, places))
    built = build_snapshot(preferences, places)
    assert built == independent_v2_snapshot(profile)
    assert (preferences, places) == before
    original = dump_snapshot(built)
    digest = snapshot_fingerprint(built)
    places[0]["location"]["address"] = "Changed after the original build"
    preferences["budget"] += 1
    assert dump_snapshot(built) == original and snapshot_fingerprint(built) == digest
    assert load_snapshot(original)["preferences"]["currency"] == profile["currency"]


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_independently_defined_v2_round_trips_all_nested_amounts_and_hash_without_live_data(profile, monkeypatch):
    from snapshots import dump_snapshot, load_snapshot, snapshot_fingerprint

    payload = independent_v2_snapshot(profile)
    raw = canonical(payload)
    forbid_replanning(monkeypatch)
    decoded = load_snapshot(raw)
    assert decoded["version"] == 2 and decoded["currency"] == profile["currency"]
    assert len(list(money_paths(decoded))) == len(list(money_paths(payload)))
    for _, amount in money_paths(decoded):
        assert type(amount) is Decimal and amount.is_finite()
        assert amount.as_tuple().exponent == (0 if profile["currency"] == "JPY" else -2)
    assert dump_snapshot(decoded) == raw
    assert snapshot_fingerprint(decoded) == hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert canonical(payload) == raw, "The decoder/encoder cannot mutate the independent oracle."


@pytest.mark.parametrize("path,value", [
    (("currency",), "XXX"), (("currency",), "USD"),
    (("preferences", "currency"), "USD"), (("preferences", "currency"), None),
    (("preferences", "budget"), "300.0"), (("preferences", "budget"), "0"),
    (("preferences", "budget"), "1000000001"),
    (("daily_budget",), "100.00"), (("daily_budget",), 100),
    (("recommendations", 0, "estimated_cost"), "1.5"),
    (("recommendations", 0, "place", "currency"), "EUR"),
    (("recommendations", 0, "place", "location"), None),
    (("recommendations", 0, "place", "location", "address"), ""),
    (("recommendations", 0, "place", "location", "source_url"), "javascript:bad()"),
    (("recommendations", 0, "place", "location", "reviewed_on"), "not-a-date"),
    (("itinerary", "days", 0, "estimated_cost"), "0.50"),
    (("itinerary", "estimated_cost"), "NaN"),
    (("itinerary", "unallocated_allowance"), "-1"),
])
def test_v2_rejects_inconsistent_currency_location_or_money_only_after_accepting_a_valid_control(path, value):
    from snapshots import SnapshotValidationError, load_snapshot

    payload = independent_v2_snapshot(profile_for("JPY"))
    # This acceptance assertion is essential: rejecting *every* v2 document
    # must fail the test, rather than falsely pass as corruption protection.
    assert load_snapshot(canonical(payload))["version"] == 2
    set_path(payload, path, value)
    with pytest.raises(SnapshotValidationError):
        load_snapshot(canonical(payload))


@pytest.mark.parametrize("field,value", [("address", "A different reviewed address"), ("latitude", "1.25")])
def test_v2_rejects_different_location_copies_for_the_same_scheduled_place(field, value):
    from snapshots import SnapshotValidationError, load_snapshot

    payload = independent_v2_snapshot(profile_for("GBP"))
    assert load_snapshot(canonical(payload))["version"] == 2
    item = next(slot["item"] for day in payload["itinerary"]["days"] for slot in day["slots"] if slot["item"])
    item["place"]["location"][field] = value
    with pytest.raises(SnapshotValidationError):
        load_snapshot(canonical(payload))


@pytest.mark.parametrize("location", [
    None, {}, {"address": ""},
    {"address": "10 QA Street", "source_url": "javascript:bad()", "reviewed_on": "2026-10-26"},
    {"address": "10 QA Street", "source_url": "https://example.com/qa", "reviewed_on": "not-a-date"},
    {"address": "10 QA Street", "source_url": "https://example.com/qa", "reviewed_on": "2026-10-26", "latitude": "91", "longitude": "0"},
    {"address": "10 QA Street", "source_url": "https://example.com/qa", "reviewed_on": "2026-10-26", "latitude": "1"},
])
def test_v2_rejects_invalid_reviewed_location_even_when_all_repeated_copies_agree(location):
    from snapshots import SnapshotValidationError, load_snapshot

    payload = independent_v2_snapshot(profile_for("EUR"))
    assert load_snapshot(canonical(payload))["version"] == 2
    place_id = payload["recommendations"][0]["place"]["id"]
    for item in snapshot_records(payload):
        if item["place"]["id"] == place_id:
            item["place"]["location"] = deepcopy(location)
    with pytest.raises(SnapshotValidationError):
        load_snapshot(canonical(payload))


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_v2_rejects_noncanonical_money_precision_even_with_the_same_numeric_value(profile):
    from snapshots import SnapshotValidationError, load_snapshot

    payload = independent_v2_snapshot(profile)
    assert load_snapshot(canonical(payload))["version"] == 2
    payload["daily_budget"] += ".0" if profile["currency"] == "JPY" else "0"
    with pytest.raises(SnapshotValidationError):
        load_snapshot(canonical(payload))


def test_v2_eur_preserves_the_original_ceiling_even_if_other_currencies_allow_more():
    from snapshots import SnapshotValidationError, load_snapshot

    payload = independent_v2_snapshot(profile_for("EUR"))
    assert load_snapshot(canonical(payload))["version"] == 2
    payload["preferences"]["budget"] = "1000000.01"
    payload["daily_budget"] = "333333.34"
    payload["itinerary"]["unallocated_allowance"] = "999897.01"
    with pytest.raises(SnapshotValidationError):
        load_snapshot(canonical(payload))


@pytest.mark.parametrize("code", ["NGN", "GBP", "USD", "JPY", "ZAR"])
def test_v2_native_currency_snapshot_can_exceed_the_old_eur_ceiling(code):
    from snapshots import dump_snapshot, load_snapshot

    payload = independent_v2_snapshot(profile_for(code))
    integer = code == "JPY"
    payload["preferences"]["budget"] = "2000000" if integer else "2000000.00"
    payload["daily_budget"] = "666667" if integer else "666666.67"
    remainder = Decimal(2000000) - Decimal(payload["itinerary"]["estimated_cost"])
    payload["itinerary"]["unallocated_allowance"] = format(remainder, ".0f" if integer else ".2f")
    raw = canonical(payload)
    assert dump_snapshot(load_snapshot(raw)) == raw


@pytest.mark.parametrize("profile", CITY_PROFILES, ids=lambda p: p["currency"])
def test_v2_repository_save_duplicate_and_read_do_not_rewrite_existing_v1(original_v1_database, profile, monkeypatch):
    from saved_trips import get_trip, list_trips, save_trip

    path, original = original_v1_database
    payload = independent_v2_snapshot(profile)
    first, created = save_trip(path, "New six-city example", payload,
                               created_at=datetime(2026, 10, 26, tzinfo=timezone.utc))
    duplicate, created_again = save_trip(path, "New six-city example", payload,
                                        created_at=datetime(2026, 10, 27, tzinfo=timezone.utc))
    assert created is True and created_again is False and duplicate == first
    assert first["id"] != original[0] and first["snapshot"]["version"] == 2
    assert first["snapshot"]["currency"] == profile["currency"]
    rows_before_reads = stored_rows(path)
    assert len(rows_before_reads) == 2 and rows_before_reads[0] == original
    assert rows_before_reads[1][4] == canonical(payload)
    forbid_replanning(monkeypatch)
    assert get_trip(path, first["id"]) == first
    assert [record["id"] for record in list_trips(path)] == [first["id"], 73]
    assert get_trip(path, 73)["available"]
    assert stored_rows(path) == rows_before_reads


def test_v2_fingerprint_changes_with_a_consistently_updated_reviewed_location():
    from snapshots import load_snapshot, snapshot_fingerprint

    payload = independent_v2_snapshot(profile_for("EUR"))
    assert load_snapshot(canonical(payload))["version"] == 2
    original = snapshot_fingerprint(payload)
    place_id = payload["recommendations"][0]["place"]["id"]
    # Update every content copy consistently; display manifests remain outside
    # the payload and are deliberately not supplied to the fingerprint API.
    for item in snapshot_records(payload):
        if item["place"]["id"] == place_id:
            item["place"]["location"]["address"] = "20 QA Updated Street, Paris, France"
    assert snapshot_fingerprint(payload) != original
    assert "images" not in payload and "maps_url" not in payload

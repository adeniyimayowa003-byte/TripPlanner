"""Phase 6's pure snapshot contract, defined before its implementation.

The independent fixture uses the working Phase 5 recommendation/scheduling APIs.
Future-module imports stay inside test bodies so pytest can collect the red suite.
"""

from copy import deepcopy
from decimal import Decimal
import hashlib
import importlib
import json
import re

import pytest

from catalog import load_catalog


MONEY_KEYS = {"budget", "daily_budget", "estimated_cost", "unallocated_allowance"}


def snapshot_api():
    return importlib.import_module("snapshots")


def money_values(value):
    """Visit nested place costs too, not just the prominent total on the page."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in MONEY_KEYS:
                yield child
            else:
                yield from money_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from money_values(child)


def money_by_path(value, path=()):
    """Match the same money field even if decoding rebuilds dictionary order."""
    found = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = (*path, key)
            if key in MONEY_KEYS:
                found[child_path] = child
            else:
                found.update(money_by_path(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.update(money_by_path(child, (*path, index)))
    return found


def replace_path(payload, path, value):
    current = payload
    for part in path[:-1]:
        current = current[part]
    current[path[-1]] = value


def replace_record_field(payload, path, value):
    """Keep saved copies equal so a field test cannot pass on a reference mismatch."""
    if path[0] != "recommendations" or len(path) < 3:
        replace_path(payload, path, value)
        return
    old_id = payload["recommendations"][path[1]]["place"]["id"]
    replace_path(payload, path, value)
    updated = payload["recommendations"][path[1]]
    for day in payload["itinerary"]["days"]:
        for slot in day["slots"]:
            if slot["item"] is not None and slot["item"]["place"]["id"] == old_id:
                slot["item"] = deepcopy(updated)
    for index, item in enumerate(payload["itinerary"]["unused_items"]):
        if item["place"]["id"] == old_id:
            payload["itinerary"]["unused_items"][index] = deepcopy(updated)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def reverse_object_keys(value):
    if isinstance(value, dict):
        return {key: reverse_object_keys(child) for key, child in reversed(list(value.items()))}
    if isinstance(value, list):
        return [reverse_object_keys(child) for child in value]
    return value


def test_independent_snapshot_fixture_really_contains_the_approved_sample(snapshot_payload):
    """A fixture error is not evidence that a future feature is missing."""
    assert snapshot_payload["version"] == 1
    assert len(snapshot_payload["recommendations"]) == 7
    itinerary = snapshot_payload["itinerary"]
    assert itinerary["filled_slots"] == itinerary["total_slots"] == 6
    assert [day["estimated_cost"] for day in itinerary["days"]] == ["50.00", "28.00", "25.00"]
    assert itinerary["estimated_cost"] == "103.00"
    assert itinerary["unallocated_allowance"] == "197.00"
    assert [item["place"]["id"] for item in itinerary["unused_items"]] == ["paris-eiffel-tower"]
    assert all(isinstance(value, str) and re.fullmatch(r"[0-9]+\.[0-9]{2}", value) for value in money_values(snapshot_payload))


def test_builder_preserves_every_original_idea_place_detail_and_notice(
    normalized_preferences, snapshot_factory
):
    api = snapshot_api()
    catalog = load_catalog()
    expected = snapshot_factory(normalized_preferences, catalog)

    result = api.build_snapshot(normalized_preferences, catalog)

    assert result["version"] == 1
    assert result["currency"] == "EUR"
    for key in ("preferences", "daily_budget", "recommendations", "recommendation_notices", "itinerary"):
        assert result[key] == expected[key]
    assert "illustrative" in result["cost_note"].casefold()
    assert "person" in result["cost_note"].casefold()
    assert "live" in result["cost_note"].casefold()
    for excluded in ("flight", "accommodation", "transport"):
        assert excluded in result["budget_note"].casefold()
    assert len(result["recommendations"]) == 7, "Save alternatives as well as the six scheduled ideas."
    assert all(isinstance(value, str) for value in money_values(result))
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    ("budget", "days", "pace", "interests", "estimate", "unallocated", "filled", "capacity"),
    [
        ("300.00", 3, "relaxed", ["food", "history"], "103.00", "197.00", 6, 6),
        ("300.00", 3, "", ["food", "history"], "135.00", "165.00", 7, 9),
        ("60.00", 3, "relaxed", ["food", "history"], "0.00", "60.00", 3, 6),
        ("100.01", 3, "relaxed", ["food", "history"], "85.00", "15.01", 6, 6),
        ("1.00", 14, "relaxed", ["food"], "0.00", "1.00", 0, 28),
        ("0.01", 1, "", ["food"], "0.00", "0.01", 0, 3),
    ],
)
def test_sample_boundaries_partial_and_empty_snapshots_round_trip(
    normalized_preferences, budget, days, pace, interests, estimate, unallocated, filled, capacity
):
    api = snapshot_api()
    preferences = {
        **deepcopy(normalized_preferences), "budget": Decimal(budget), "days": days,
        "pace": pace, "interests": interests,
    }

    built = api.build_snapshot(preferences, load_catalog())
    decoded = api.load_snapshot(api.dump_snapshot(built))

    assert decoded["preferences"] == preferences
    assert decoded["itinerary"]["estimated_cost"] == Decimal(estimate)
    assert decoded["itinerary"]["unallocated_allowance"] == Decimal(unallocated)
    assert decoded["itinerary"]["filled_slots"] == filled
    assert decoded["itinerary"]["total_slots"] == capacity
    assert len(decoded["itinerary"]["days"]) == days
    if filled < capacity:
        gaps = [slot for day in decoded["itinerary"]["days"] for slot in day["slots"] if slot["item"] is None]
        assert len(gaps) == capacity - filled
        assert all(isinstance(slot["empty_reason"], str) and slot["empty_reason"] for slot in gaps)
        assert decoded["itinerary"]["notices"]


@pytest.mark.parametrize("pace", ["relaxed", "", "active"])
@pytest.mark.parametrize("days", [1, 14])
def test_slot_structure_uses_saved_pace_and_day_count(
    normalized_preferences, snapshot_factory, make_place, pace, days
):
    api = snapshot_api()
    preferences = {**normalized_preferences, "pace": pace, "days": days}
    payload = snapshot_factory(preferences, [make_place(preference_tags=[pace] if pace else [])])

    decoded = api.load_snapshot(canonical(payload))

    names = ["Morning", "Evening"] if pace == "relaxed" else ["Morning", "Afternoon", "Evening"]
    assert [day["number"] for day in decoded["itinerary"]["days"]] == list(range(1, days + 1))
    assert all([slot["name"] for slot in day["slots"]] == names for day in decoded["itinerary"]["days"])


def test_all_money_paths_are_exact_text_on_disk_and_decimals_in_memory(snapshot_payload):
    api = snapshot_api()
    raw = api.dump_snapshot(snapshot_payload)
    on_disk = json.loads(raw)
    decoded = api.load_snapshot(raw)

    stored_values = money_by_path(on_disk)
    decoded_values = money_by_path(decoded)
    assert len(stored_values) > 30, "This must include recommendation, slot, unused, and nested place costs."
    assert all(type(value) is str and re.fullmatch(r"[0-9]+\.[0-9]{2}", value) for value in stored_values.values())
    assert all(type(value) is Decimal for value in decoded_values.values())
    assert decoded_values == {path: Decimal(value) for path, value in stored_values.items()}
    assert type(decoded["version"]) is int
    assert type(decoded["preferences"]["days"]) is int
    assert type(decoded["preferences"]["family_friendly"]) is bool
    assert type(decoded["recommendations"][0]["score"]) is int


def test_decimal_tenths_and_cents_survive_without_binary_artifacts(
    normalized_preferences, make_place, snapshot_factory
):
    api = snapshot_api()
    preferences = {**normalized_preferences, "days": 1, "budget": Decimal("0.30")}
    payload = snapshot_factory(preferences, [make_place(id="one", estimated_cost=0.1), make_place(id="two", estimated_cost=0.2)])

    decoded = api.load_snapshot(api.dump_snapshot(payload))

    assert decoded["itinerary"]["estimated_cost"] == Decimal("0.30")
    assert decoded["itinerary"]["unallocated_allowance"] == Decimal("0.00")
    assert api.dump_snapshot(decoded) == api.dump_snapshot(payload)


def test_canonical_dump_and_fingerprint_ignore_object_key_insertion_order(snapshot_payload):
    api = snapshot_api()
    reordered = reverse_object_keys(snapshot_payload)
    before = deepcopy(snapshot_payload)

    raw = api.dump_snapshot(snapshot_payload)
    digest = api.snapshot_fingerprint(snapshot_payload)

    assert raw == canonical(snapshot_payload)
    assert api.dump_snapshot(reordered) == raw
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert digest == hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert api.snapshot_fingerprint(reordered) == digest
    assert snapshot_payload == before


def test_loaded_decimal_payload_has_identical_dump_and_fingerprint(snapshot_payload):
    api = snapshot_api()
    raw = api.dump_snapshot(snapshot_payload)
    decoded = api.load_snapshot(raw)
    before = deepcopy(decoded)

    assert api.dump_snapshot(decoded) == raw
    assert api.snapshot_fingerprint(decoded) == api.snapshot_fingerprint(snapshot_payload)
    assert decoded == before


def test_each_decoded_snapshot_is_a_fresh_nested_structure(snapshot_payload):
    api = snapshot_api()
    raw = canonical(snapshot_payload)
    first, second = api.load_snapshot(raw), api.load_snapshot(raw)
    before = deepcopy(second)

    first["recommendations"][0]["place"]["interest_tags"].append("changed-in-memory")
    first["itinerary"]["notices"].append("changed-in-memory")

    assert second == before
    assert api.load_snapshot(raw) == before


def test_list_order_and_unicode_are_preserved_in_canonical_content(snapshot_payload):
    api = snapshot_api()
    payload = deepcopy(snapshot_payload)
    payload["recommendation_notices"] = ["Découverte à Paris", "東京の旅"]
    changed = deepcopy(payload)
    changed["recommendation_notices"].reverse()

    raw = api.dump_snapshot(payload)

    assert "Découverte à Paris" in raw and "東京の旅" in raw
    assert api.load_snapshot(raw)["recommendation_notices"] == payload["recommendation_notices"]
    assert api.snapshot_fingerprint(changed) != api.snapshot_fingerprint(payload)


@pytest.mark.parametrize("changed_field", ["description", "reason", "source_url", "notice"])
def test_complete_saved_content_not_only_ids_changes_the_form_hash(snapshot_payload, changed_field):
    api = snapshot_api()
    changed = deepcopy(snapshot_payload)
    # The unused alternative avoids accidentally making a scheduled reference inconsistent.
    alternative = changed["itinerary"]["unused_items"][0]
    record = next(item for item in changed["recommendations"] if item["place"]["id"] == alternative["place"]["id"])
    if changed_field == "notice":
        changed["itinerary"]["notices"].append("Original opening-hours limitation.")
    elif changed_field == "reason":
        record["reason"] = alternative["reason"] = "A different stored matching explanation."
    else:
        value = "https://example.org/updated-source" if changed_field == "source_url" else "Changed historical place details."
        record["place"][changed_field] = alternative["place"][changed_field] = value

    assert api.snapshot_fingerprint(changed) != api.snapshot_fingerprint(snapshot_payload)


def test_form_payload_contains_no_title_or_save_metadata(normalized_preferences):
    api = snapshot_api()
    result = api.build_snapshot(normalized_preferences, load_catalog())

    assert not {"title", "trip_name", "id", "created_at", "saved_at"}.intersection(result)
    before = api.snapshot_fingerprint(result)
    api.normalize_trip_name("First name", normalized_preferences)
    api.normalize_trip_name("Second name", normalized_preferences)
    assert api.snapshot_fingerprint(result) == before


def test_builder_uses_explicit_catalog_without_reading_disk_or_mutating_inputs(
    normalized_preferences, make_place, monkeypatch
):
    api = snapshot_api()
    import catalog as catalog_module
    import recommendations

    def forbidden(*args, **kwargs):
        raise AssertionError("An explicit catalog must not trigger another file read.")

    monkeypatch.setattr(catalog_module, "load_catalog", forbidden)
    monkeypatch.setattr(recommendations, "load_catalog", forbidden)
    if hasattr(api, "load_catalog"):
        monkeypatch.setattr(api, "load_catalog", forbidden)
    preferences = deepcopy(normalized_preferences)
    catalog = [make_place(id="garden", preference_tags=["relaxed", "family-friendly"])]
    before_preferences, before_catalog = deepcopy(preferences), deepcopy(catalog)

    first = api.build_snapshot(preferences, catalog)
    second = api.build_snapshot(preferences, catalog)

    assert first == second
    assert preferences == before_preferences and catalog == before_catalog
    first["recommendations"][0]["place"]["description"] = "Changed result only"
    assert second["recommendations"][0]["place"]["description"] != "Changed result only"
    assert catalog == before_catalog


@pytest.mark.parametrize("cost", [0.001, Decimal("0.001")])
def test_builder_does_not_round_fractional_cent_catalog_costs(
    normalized_preferences, make_place, cost,
):
    api = snapshot_api()
    catalog = [make_place(estimated_cost=cost)]
    original = deepcopy(catalog)

    with pytest.raises(api.SnapshotValidationError):
        api.build_snapshot(normalized_preferences, catalog)
    assert catalog == original


def test_loading_historical_data_never_calls_live_catalog_or_current_algorithms(
    normalized_preferences, make_place, snapshot_factory, monkeypatch
):
    api = snapshot_api()
    import catalog as catalog_module
    import itinerary
    import recommendations

    historical = {**normalized_preferences, "destination": "Historical City", "interests": ["archived-interest"]}
    payload = snapshot_factory(historical, [make_place(destination="Historical City", interest_tags=["archived-interest"])])
    payload["recommendation_notices"].append("Original saved recommendation limitation.")
    payload["itinerary"]["notices"].append("Original saved scheduling limitation.")
    before = deepcopy(payload)

    def forbidden(*args, **kwargs):
        raise AssertionError("Saved reads must use stored data, not today's catalog or rules.")

    for module, names in (
        (catalog_module, ["load_catalog", "get_supported_destinations", "get_supported_interests", "get_supported_paces"]),
        (recommendations, ["load_catalog", "recommend_trip_ideas"]),
        (itinerary, ["recommend_trip_ideas", "generate_itinerary"]),
        (api, ["load_catalog", "recommend_trip_ideas", "generate_itinerary", "build_snapshot"]),
    ):
        for name in names:
            if hasattr(module, name):
                monkeypatch.setattr(module, name, forbidden)

    decoded = api.load_snapshot(canonical(payload))

    assert decoded["preferences"]["destination"] == "Historical City"
    assert decoded["preferences"]["interests"] == ["archived-interest"]
    assert decoded["recommendation_notices"][-1] == "Original saved recommendation limitation."
    assert decoded["itinerary"]["notices"][-1] == "Original saved scheduling limitation."
    assert payload == before


@pytest.mark.parametrize("raw", [None, "", "   ", "Paris weekend", "  Paris weekend  ", "東京への旅 🌸", "é" * 80, "<script>alert('hi')</script>", "Robert'); DROP TABLE saved_trips;--"])
def test_trip_names_are_defaulted_trimmed_or_preserved_as_literal_text(normalized_preferences, raw):
    api = snapshot_api()
    expected = "Paris, France — 3-day trip" if raw is None or not raw.strip() else raw.strip()

    assert api.normalize_trip_name(raw, normalized_preferences) == expected


@pytest.mark.parametrize("raw", ["x" * 81, "é" * 81, "\t", "\n", "\rname", "name\n", "\tname\t", "first\tsecond", "first\x00second", "name\x1f", "name\x7f", "name\x85", 123, True, [], {}])
def test_invalid_names_reject_controls_before_trimming_and_wrong_types(normalized_preferences, raw):
    api = snapshot_api()

    with pytest.raises(ValueError):
        api.normalize_trip_name(raw, normalized_preferences)


def test_generated_default_name_respects_limit_even_for_a_long_saved_destination(normalized_preferences):
    api = snapshot_api()
    preferences = {**normalized_preferences, "destination": "A" * 200}

    name = api.normalize_trip_name("", preferences)

    assert isinstance(name, str) and name.strip()
    assert len(name) <= 80
    assert not any(ord(char) < 32 for char in name)


@pytest.mark.parametrize("field", ["version", "currency", "cost_note", "budget_note", "preferences", "daily_budget", "recommendations", "recommendation_notices", "itinerary"])
def test_missing_required_top_level_field_is_unavailable_data(snapshot_payload, field):
    api = snapshot_api()
    broken = deepcopy(snapshot_payload)
    del broken[field]

    with pytest.raises(api.SnapshotValidationError):
        api.load_snapshot(canonical(broken))


@pytest.mark.parametrize(
    ("path", "bad_value"),
    [
        (("version",), 2), (("version",), True), (("version",), "1"),
        (("currency",), "USD"), (("cost_note",), ""), (("budget_note",), None),
        (("preferences",), []), (("preferences", "destination"), ""),
        (("preferences", "days"), True), (("preferences", "days"), 0),
        (("preferences", "days"), 15), (("preferences", "days"), "3"),
        (("preferences", "family_friendly"), 1), (("preferences", "pace"), []),
        (("preferences", "interests"), "history"), (("preferences", "interests"), []),
        (("recommendations",), {}), (("recommendation_notices",), "warning"),
        (("recommendation_notices",), [None]), (("itinerary", "notices"), [""]),
        (("recommendations", 0, "score"), True), (("recommendations", 0, "score"), "5"),
        (("recommendations", 0, "score"), -1), (("recommendations", 0, "matched_interests"), []),
        (("recommendations", 0, "matched_interests"), ["unmatched-interest"]),
        (("recommendations", 0, "preference_matches"), ["unrequested-preference"]),
        (("recommendations", 0, "reason"), ""), (("recommendations", 0, "place", "id"), ""),
        (("recommendations", 0, "place", "name"), None),
        (("recommendations", 0, "place", "category"), "hotel"),
        (("recommendations", 0, "place", "destination"), "Another City"),
        (("recommendations", 0, "place", "estimated_cost"), "0.01"),
        (("recommendations", 0, "place", "description"), []),
        (("recommendations", 0, "place", "interest_tags"), "history"),
        (("recommendations", 0, "place", "interest_tags"), ["art"]),
        (("recommendations", 0, "place", "preference_tags"), [True]),
        (("recommendations", 1, "place", "preference_tags"), []),
        (("itinerary", "days"), []), (("itinerary", "days", 0, "number"), 2),
        (("itinerary", "days", 0, "number"), True),
        (("itinerary", "days", 0, "slots", 0, "name"), "Afternoon"),
        (("itinerary", "days", 0, "slots", 0, "empty_reason"), "Not actually empty"),
        (("itinerary", "filled_slots"), True), (("itinerary", "filled_slots"), 5),
        (("itinerary", "total_slots"), 7), (("itinerary", "unused_items"), []),
        (("itinerary", "days", 0, "estimated_cost"), "49.99"),
        (("itinerary", "estimated_cost"), "102.99"),
        (("itinerary", "unallocated_allowance"), "197.01"),
        (("daily_budget",), "100.01"),
        (("preferences", "budget"), "0.00"), (("preferences", "budget"), "1000000.01"),
    ],
    ids=lambda value: repr(value),
)
def test_invalid_stored_types_or_inconsistent_values_are_rejected(snapshot_payload, path, bad_value):
    api = snapshot_api()
    broken = deepcopy(snapshot_payload)
    replace_record_field(broken, path, bad_value)

    with pytest.raises(api.SnapshotValidationError):
        api.load_snapshot(canonical(broken))


@pytest.mark.parametrize("bad_case", ["integer", "float", "boolean", "none", "no-cents", "one-cent-digit", "three-cent-digits", "fractional-cent", "scientific", "nan", "infinity", "negative", "plus", "leading-space", "trailing-space", "unicode-digits", "comma"])
@pytest.mark.parametrize("path", [("preferences", "budget"), ("recommendations", 1, "place", "estimated_cost")])
def test_money_on_disk_must_be_finite_ascii_cent_text(snapshot_payload, path, bad_case):
    api = snapshot_api()
    broken = deepcopy(snapshot_payload)
    whole = "300" if path[0] == "preferences" else "0"
    invalid = {
        "integer": int(whole), "float": float(whole), "boolean": False, "none": None,
        "no-cents": whole, "one-cent-digit": whole + ".0",
        "three-cent-digits": whole + ".000", "fractional-cent": whole + ".001",
        "scientific": "3e2" if whole == "300" else "0e0",
        "nan": "NaN", "infinity": "Infinity", "negative": "-0.01",
        "plus": "+" + whole + ".00", "leading-space": " " + whole + ".00",
        "trailing-space": whole + ".00 ",
        "unicode-digits": "３００.００" if whole == "300" else "０.００",
        "comma": whole + ",00",
    }
    # Where possible the numeric value remains the original valid value. A
    # permissive parser must not pass merely because later sum checks reject it.
    bad_amount = invalid[bad_case]
    replace_record_field(broken, path, bad_amount)

    with pytest.raises(api.SnapshotValidationError):
        api.load_snapshot(canonical(broken))


@pytest.mark.parametrize("bad_amount", [Decimal("300.001"), Decimal("NaN"), Decimal("Infinity"), Decimal("-0.01"), 300.0, object()])
def test_dump_does_not_hide_wrong_money_types_or_silently_round(snapshot_payload, bad_amount):
    api = snapshot_api()
    broken = deepcopy(snapshot_payload)
    broken["preferences"]["budget"] = bad_amount

    # Rounding 300.001 or converting float 300.0 would recreate an otherwise
    # valid EUR 300 snapshot, so unrelated totals cannot hide an encoder defect.
    with pytest.raises(api.SnapshotValidationError):
        api.dump_snapshot(broken)


@pytest.mark.parametrize("unsafe", ["javascript:alert(1)", "data:text/html,test", "file:///C:/secret.txt", "//example.com/place", "/relative/path", "https:///missing-host", "", "https://example.com/\nscript"])
def test_unsafe_source_links_cannot_become_executable_saved_links(snapshot_payload, unsafe):
    api = snapshot_api()
    broken = deepcopy(snapshot_payload)
    replace_record_field(broken, ("recommendations", 0, "place", "source_url"), unsafe)

    with pytest.raises(api.SnapshotValidationError):
        api.load_snapshot(canonical(broken))


@pytest.mark.parametrize("source", ["https://example.org/place?q=Paris#details", "http://example.org/place"])
def test_safe_absolute_http_sources_remain_available(snapshot_payload, source):
    api = snapshot_api()
    payload = deepcopy(snapshot_payload)
    replace_record_field(payload, ("recommendations", 0, "place", "source_url"), source)

    decoded = api.load_snapshot(canonical(payload))

    assert decoded["recommendations"][0]["place"]["source_url"] == source


@pytest.mark.parametrize("path", [
    ("preferences", "budget"), ("preferences", "interests"), ("preferences", "family_friendly"),
    ("recommendations", 0, "reason"), ("recommendations", 0, "matched_interests"),
    ("recommendations", 0, "place", "source_url"),
    ("itinerary", "days", 0, "estimated_cost"),
    ("itinerary", "days", 0, "slots", 0, "item"),
    ("itinerary", "filled_slots"), ("itinerary", "unused_items"),
])
def test_missing_nested_required_fields_raise_the_documented_validation_error(snapshot_payload, path):
    api = snapshot_api()
    broken = deepcopy(snapshot_payload)
    current = broken
    for part in path[:-1]:
        current = current[part]
    del current[path[-1]]

    with pytest.raises(api.SnapshotValidationError):
        api.load_snapshot(canonical(broken))


@pytest.mark.parametrize("raw", ["", "{", "null", "[]", "true", "1", '"text"', '{"version": NaN}'])
def test_unreadable_or_non_object_json_is_a_snapshot_validation_error(raw):
    api = snapshot_api()

    with pytest.raises(api.SnapshotValidationError):
        api.load_snapshot(raw)


@pytest.mark.parametrize("corruption", ["duplicate-recommendation", "duplicate-scheduled", "unknown-scheduled", "changed-scheduled", "extra-slot", "missing-day", "missing-empty-reason", "nonempty-empty-reason", "wrong-unused-order"])
def test_structural_corruption_never_gets_repaired_by_regenerating(
    snapshot_payload, snapshot_factory, normalized_preferences, make_place, corruption
):
    api = snapshot_api()
    broken = deepcopy(snapshot_payload)
    if corruption == "duplicate-recommendation":
        broken["recommendations"].append(deepcopy(broken["recommendations"][0]))
    elif corruption == "duplicate-scheduled":
        broken["itinerary"]["days"][1]["slots"][0]["item"] = deepcopy(broken["itinerary"]["days"][0]["slots"][0]["item"])
    elif corruption == "unknown-scheduled":
        broken["itinerary"]["days"][0]["slots"][0]["item"]["place"]["id"] = "not-a-saved-recommendation"
    elif corruption == "changed-scheduled":
        broken["itinerary"]["days"][0]["slots"][0]["item"]["reason"] = "Changed only in the scheduled copy."
    elif corruption == "extra-slot":
        broken["itinerary"]["days"][0]["slots"].append({"name": "Night", "item": None, "empty_reason": "An extra slot."})
    elif corruption == "missing-day":
        broken["itinerary"]["days"].pop()
    elif corruption in {"missing-empty-reason", "nonempty-empty-reason"}:
        preferences = {**normalized_preferences, "interests": ["food"], "budget": Decimal("1.00")}
        broken = snapshot_factory(preferences, load_catalog())
        empty = broken["itinerary"]["days"][0]["slots"][0]
        if corruption == "missing-empty-reason":
            del empty["empty_reason"]
        else:
            empty["empty_reason"] = ""
    else:
        preferences = {**normalized_preferences, "days": 1}
        broken = snapshot_factory(preferences, [make_place(id=letter, name=letter) for letter in "ABCD"])
        assert len(broken["itinerary"]["unused_items"]) == 2
        broken["itinerary"]["unused_items"].reverse()

    with pytest.raises(api.SnapshotValidationError):
        api.load_snapshot(canonical(broken))


def test_loader_checks_actual_daily_cap_not_rounded_display_allowance(
    normalized_preferences, make_place, snapshot_factory
):
    api = snapshot_api()
    preferences = {**normalized_preferences, "budget": Decimal("100.01"), "pace": ""}
    catalog = [
        make_place(id="A", estimated_cost=20, interest_tags=["food", "history"]),
        make_place(id="B", name="B", estimated_cost=0),
        make_place(id="C", name="C", estimated_cost=0),
        make_place(id="D", estimated_cost="13.34"),
    ]
    broken = snapshot_factory(preferences, catalog)
    assert broken["daily_budget"] == "33.34"
    day_one, day_two = broken["itinerary"]["days"][:2]
    source = day_two["slots"][1]
    destination = day_one["slots"][1]
    assert source["item"]["place"]["id"] == "D" and destination["item"] is None
    destination["item"], source["item"] = source["item"], None
    source["empty_reason"], destination["empty_reason"] = destination["empty_reason"], None
    day_one["estimated_cost"], day_two["estimated_cost"] = "33.34", "0.00"
    assert broken["itinerary"]["estimated_cost"] == "33.34", "All sums/counts are still correct; only the true daily cap is broken."

    with pytest.raises(api.SnapshotValidationError):
        api.load_snapshot(canonical(broken))

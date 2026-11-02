"""Pure Google Maps URL contracts: no network, account, key or live geocoding."""

from copy import deepcopy
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest

from phase8_helpers import api_symbol


def maps_api():
    return api_symbol("maps", "build_maps_url")


def parsed_maps_url(url):
    assert isinstance(url, str) and len(url) <= 2048
    assert url.isascii(), "Unicode query text must be URL-encoded."
    assert not any(character in url for character in '<>"\r\n\t ')
    parts = urlsplit(url)
    assert parts.scheme == "https" and parts.netloc == "www.google.com"
    assert parts.path == "/maps/search/" and not parts.fragment
    query = parse_qs(parts.query, strict_parsing=True)
    assert query.get("api") == ["1"]
    assert len(query.get("query", [])) == 1 and query["query"][0]
    assert set(query) <= {"api", "query", "query_place_id"}, "No API key, tracking, arbitrary destination or route service."
    return query


@pytest.mark.parametrize("name,address,city", [
    ("Louvre Museum", "Rue de Rivoli, 75001 Paris", "Paris, France"),
    ("QA Café & Garden", "10 QA Street, Lagos", "Lagos, Nigeria"),
    ("QA Café de l'Île", "2 QA Avenue, Cape Town", "Cape Town, South Africa"),
    ("QA 東京の庭", "1 QA Test Road, Tokyo", "Tokyo, Japan"),
])
def test_map_link_uses_reviewed_place_address_and_destination_as_encoded_data(name, address, city):
    query = parsed_maps_url(maps_api()(name, city, {"address": address}))
    assert all(text in query["query"][0] for text in (name, address, city))


def test_optional_permitted_place_id_is_encoded_not_used_as_a_url():
    query = parsed_maps_url(maps_api()("QA Place", "Paris, France", {
        "address": "10 QA Street, Paris", "place_id": "ChIJ-qa_test",
    }))
    assert query["query_place_id"] == ["ChIJ-qa_test"]


@pytest.mark.parametrize("latitude,longitude", [("48.860611", "2.337644"), ("-90", "-180"), ("90", "180"), (0, 0)])
def test_valid_coordinate_pairs_can_target_the_reviewed_position(latitude, longitude):
    query = parsed_maps_url(maps_api()("QA Coordinate Example", "Paris, France", {
        "address": "10 QA Street, Paris", "latitude": latitude, "longitude": longitude,
    }))
    # Exact numeric comparison catches a swapped pair or incidental digits in
    # a place name; substrings such as "0" would not prove a valid position.
    coordinates = query["query"][0].split(",")
    assert len(coordinates) == 2
    assert tuple(Decimal(value.strip()) for value in coordinates) == (
        Decimal(str(latitude)), Decimal(str(longitude)),
    )


@pytest.mark.parametrize("location", [
    None, {}, "not a location", {"address": ""}, {"address": "  "},
    {"address": None}, {"address": "Street\nInjected header"},
    {"address": "x" * 3000},
    {"address": "QA Street", "latitude": "1"},
    {"address": "QA Street", "longitude": "1"},
    {"address": "QA Street", "latitude": "91", "longitude": "0"},
    {"address": "QA Street", "latitude": "0", "longitude": "181"},
    {"address": "QA Street", "latitude": "NaN", "longitude": "1"},
    {"address": "QA Street", "latitude": "1", "longitude": "Infinity"},
    {"address": "QA Street", "latitude": True, "longitude": False},
])
def test_missing_or_invalid_reviewed_location_has_no_misleading_map_link(location):
    assert maps_api()("QA Place", "Paris, France", location) is None


@pytest.mark.parametrize("name,city", [(None, "Paris, France"), ("", "Paris, France"), ("QA Place", ""), ("QA\nPlace", "Paris, France")])
def test_missing_or_control_character_identity_cannot_produce_a_claimed_location(name, city):
    assert maps_api()(name, city, {"address": "10 QA Street"}) is None


@pytest.mark.parametrize("text", ['<script>alert(1)</script>', 'A & api=999&key=secret', 'https://evil.example/redirect', 'javascript:alert(1)', '" onclick="bad()'])
def test_hostile_query_text_cannot_change_the_google_host_or_parameters(text):
    result = maps_api()(text, "Paris, France", {"address": "10 QA Street"})
    if result is not None:
        query = parsed_maps_url(result)
        assert text in query["query"][0]
        assert "key" not in query and query["api"] == ["1"]


def test_map_link_builder_does_not_mutate_location_or_use_network(monkeypatch):
    build_maps_url = maps_api()
    import socket
    import urllib.request

    def forbidden(*args, **kwargs):
        pytest.fail("Map links are local URL construction, not an API request.")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    location = {"address": "10 QA Street", "latitude": "1.25", "longitude": "2.5"}
    before = deepcopy(location)
    first = build_maps_url("QA Place", "Paris, France", location)
    assert build_maps_url("QA Place", "Paris, France", location) == first
    assert parsed_maps_url(first)
    assert location == before


def test_map_parser_helper_rejects_a_lookalike_host_and_arbitrary_parameters():
    with pytest.raises(AssertionError):
        parsed_maps_url("https://www.google.com.evil.example/maps/search/?api=1&query=place")
    with pytest.raises(AssertionError):
        parsed_maps_url("https://www.google.com/maps/search/?api=1&query=place&key=secret")

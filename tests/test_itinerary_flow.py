"""Approved Phase 5 journeys, defined before the itinerary is implemented.

These checks inspect server-rendered HTML, not browser layout or JavaScript.
Day and slot helpers deliberately use content/semantics rather than CSS names.
"""

from copy import deepcopy
import json
import re
from urllib.parse import urlsplit

import pytest


SLOT_NAMES = ("Morning", "Afternoon", "Evening")
RELAXED_ASSIGNMENTS = (
    ("paris-luxembourg-gardens", "paris-le-procope"),
    ("paris-seine-riverside-walk", "paris-cafe-de-flore"),
    ("paris-notre-dame", "paris-louvre-museum"),
)


def assert_redirect(response, path):
    assert response.status_code in (302, 303)
    assert urlsplit(response.headers["Location"]).path == path


def _walk(node, parents=()):
    yield node, parents
    for child in node.children:
        if hasattr(child, "tag"):
            yield from _walk(child, parents + (node,))


def _day_number(node):
    is_heading = node.tag in {"h2", "h3", "h4", "h5", "h6"}
    is_heading = is_heading or node.attrs.get("role") == "heading"
    if not is_heading:
        return None
    match = re.match(r"^Day\s+0?(\d+)\b", node.text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _slot_markers(region):
    """Accept visible slot labels, headings, or a slot's accessible name."""
    found = []
    for node, parents in _walk(region):
        label = node.attrs.get("aria-label", "").strip()
        name = next(
            (name for name in SLOT_NAMES if node.text == name or label == name),
            None,
        )
        if name is None:
            continue
        # A span inside a heading must not count as a second slot label.
        if any(parent.text == name or parent.attrs.get("aria-label") == name for parent in parents):
            continue
        found.append((name, node, parents))
    return found


def day_sections(page):
    """Find each numbered day through its heading and enclosing semantic region."""
    sections = []
    for node, parents in _walk(page):
        number = _day_number(node)
        if number is None:
            continue
        candidates = [
            parent for parent in reversed(parents)
            if parent.tag in {"section", "article"} or parent.attrs.get("role") == "region"
        ]
        section = next((
            candidate for candidate in candidates
            if len([n for n, _ in _walk(candidate) if _day_number(n) is not None]) == 1
            and {name for name, _, _ in _slot_markers(candidate)} >= {"Morning", "Evening"}
        ), None)
        assert section is not None, f"Day {number} needs a clearly headed section containing its slots."
        sections.append((number, section))
    assert sections, "The page must render numbered daily itinerary sections."
    return sections


def slot_regions(day):
    """Keep the whole single-slot branch, including content outside its header."""
    regions = []
    for name, marker, parents in _slot_markers(day):
        if marker.attrs.get("aria-label") == name and marker.text != name:
            region = marker
        else:
            region = next((
                parent for parent in parents
                if parent is not day
                and parent.text != name
                and len(_slot_markers(parent)) == 1
            ), None)
        assert region is not None, f"The {name} label needs its own identifiable slot content."
        regions.append((name, region))
    return regions


def itinerary_page(client, parse_page):
    response = client.get("/itinerary")
    assert response.status_code == 200
    return parse_page(response)


def itinerary_link(page):
    links = [
        node for node in page.find_all("a", href="/itinerary")
        if "build my daily itinerary" in node.text.casefold()
    ]
    assert links, "Recommendations need a real Build my daily itinerary link."
    return links[0]


def clear_form_and_token(page):
    form = page.find("form", action="/draft/clear")
    assert form is not None
    assert form.attrs.get("method", "").casefold() == "post"
    assert "clear this draft" in form.text.casefold()
    token = form.find("input", name="csrf_token")
    assert token is not None and token.attrs.get("type") == "hidden"
    assert token.attrs.get("value")
    return form, token.attrs["value"]


def assert_filled_count(text, filled, total):
    assert re.search(
        rf"\b{filled}\s*(?:/|of|out of)\s*{total}\b", text, re.IGNORECASE,
    ), "Show the count of filled slots out of all requested slots."


@pytest.fixture
def replace_catalog(monkeypatch, tmp_path):
    """Change a test-local JSON catalog, never the application's sample file."""
    import catalog

    def replace(places):
        path = tmp_path / "itinerary-flow-catalog.json"
        path.write_text(json.dumps({"places": places}), encoding="utf-8")
        monkeypatch.setattr(catalog, "CATALOG_FILE", path)

    return replace


@pytest.mark.parametrize("empty", [False, True], ids=["matching-ideas", "no-matches"])
def test_recommendations_link_opens_an_itinerary_even_with_no_matches(
    client, draft_data, set_draft, parse_page, empty,
):
    if empty:
        draft_data["preferences"].update(budget="1.00", interests=["food"])
    set_draft(client, draft_data)
    recommendations = client.get("/recommendations")
    assert recommendations.status_code == 200
    link = itinerary_link(parse_page(recommendations))

    response = client.get(link.attrs["href"])
    assert response.status_code == 200
    assert len(day_sections(parse_page(response))) == 3


def test_itinerary_get_is_read_only_navigation_without_a_submitted_csrf_token(
    client, set_draft, parse_page,
):
    stored = set_draft(client)
    with client.session_transaction() as session:
        assert "csrf_token" not in session

    page = itinerary_page(client, parse_page)
    assert len(page.find_all("h1")) == 1
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored


def test_real_relaxed_itinerary_has_exact_day_and_chronological_slot_assignments(
    client, set_draft, parse_page,
):
    from catalog import load_catalog

    places = {place["id"]: place for place in load_catalog()}
    set_draft(client)
    page = itinerary_page(client, parse_page)
    days = day_sections(page)

    assert [number for number, _ in days] == [1, 2, 3]
    for (_, section), expected_ids in zip(days, RELAXED_ASSIGNMENTS):
        slots = slot_regions(section)
        assert [name for name, _ in slots] == ["Morning", "Evening"]
        for (_, slot), expected_id in zip(slots, expected_ids):
            found_names = [place["name"] for place in places.values() if place["name"] in slot.text]
            assert found_names == [places[expected_id]["name"]]
    # Louvre's evening fallback is an attraction, not an invented restaurant.
    final_evening = slot_regions(days[2][1])[1][1]
    assert "attraction" in final_evening.text.casefold()


def test_scheduled_cards_preserve_original_details_reasons_prices_and_source_urls(
    client, set_draft, parse_page, normalized_preferences,
):
    from recommendations import recommend_trip_ideas

    items, _ = recommend_trip_ideas(normalized_preferences)
    by_id = {item["place"]["id"]: item for item in items}
    set_draft(client)
    page = itinerary_page(client, parse_page)

    for (_, day), expected_ids in zip(day_sections(page), RELAXED_ASSIGNMENTS):
        for (_, slot), expected_id in zip(slot_regions(day), expected_ids):
            item = by_id[expected_id]
            place = item["place"]
            assert place["description"] in slot.text
            assert place["category"] in slot.text.casefold()
            assert item["reason"] in slot.text
            assert slot.find("a", href=place["source_url"]) is not None
            assert "illustrative estimate" in slot.text.casefold()
            if item["estimated_cost"]:
                assert format(item["estimated_cost"], ".2f") in slot.text
            else:
                assert "free" in slot.text.casefold()


def test_summary_estimates_and_filled_count_describe_the_103_euro_sample(
    client, set_draft, parse_page,
):
    set_draft(client)
    page = itinerary_page(client, parse_page)
    text = page.text.casefold()

    assert "paris, france" in text and "3 days" in text
    assert all(word in text for word in ("food", "history", "relaxed", "family"))
    assert all(amount in text for amount in ("300.00", "100.00", "103.00", "197.00"))
    assert "per person" in text and "eur" in text
    assert "unallocated" in text or "not allocated" in text
    assert "estimate" in text
    assert_filled_count(text, 6, 6)
    for (_, day), amount in zip(day_sections(page), ("50.00", "28.00", "25.00")):
        assert amount in day.text
        assert "estimate" in day.text.casefold()


def test_itinerary_displays_half_up_daily_estimate_without_overspending_the_allowance(
    client, draft_data, set_draft, parse_page,
):
    draft_data["preferences"]["budget"] = "100.01"
    set_draft(client, draft_data)

    page = itinerary_page(client, parse_page)

    assert "100.01" in page.text
    assert "33.34" in page.text, "The approximate daily display must use half-up rounding."
    assert "85.00" in page.text and "15.01" in page.text
    assert "Le Procope" not in page.text
    assert len(day_sections(page)) == 3


def test_itinerary_explains_feasibility_meal_gaps_alternatives_and_greedy_limits(
    client, set_draft, parse_page,
):
    set_draft(client)
    page = itinerary_page(client, parse_page)
    text = page.text.casefold()

    assert "opening hours" in text
    assert "travel time" in text or "journey time" in text
    assert "illustrative" in text and "suggest" in text
    assert "meal" in text and any(word in text for word in ("not fully", "missing", "not cover", "not include"))
    assert "alternative" in text or "unused" in text
    assert "how this itinerary was built" in text
    assert "rank" in text or "score" in text
    assert "pace" in text and ("categor" in text or "restaurant" in text)
    assert "repeat" in text
    assert "equal" in text or "same daily" in text or "each day" in text
    assert "greedy" in text or "not optimal" in text or "does not optimize" in text
    assert "daytime" in text and ("budget" in text or "allowance" in text)
    assert "flight" in text and "accommodation" in text and "transport" in text


def test_no_pace_has_three_chronological_slots_seven_ideas_and_135_euro_total(
    client, draft_data, set_draft, parse_page,
):
    from catalog import load_catalog

    draft_data["preferences"]["pace"] = ""
    set_draft(client, draft_data)
    page = itinerary_page(client, parse_page)
    days = day_sections(page)
    assert len(days) == 3
    for _, day in days:
        assert [name for name, _ in slot_regions(day)] == list(SLOT_NAMES)
    for place in load_catalog():
        containing_slots = [
            slot for _, day in days for _, slot in slot_regions(day)
            if place["name"] in slot.text
        ]
        assert len(containing_slots) == 1
    assert "135.00" in page.text and "165.00" in page.text
    assert_filled_count(page.text, 7, 9)
    assert any(
        "no additional matching idea" in slot.text.casefold()
        for _, day in days for _, slot in slot_regions(day)
    )


def test_low_allowance_keeps_free_mornings_and_honest_empty_evenings(
    client, draft_data, set_draft, parse_page,
):
    draft_data["preferences"]["budget"] = "60.00"
    set_draft(client, draft_data)
    page = itinerary_page(client, parse_page)
    expected_names = ("Luxembourg Gardens", "Seine Riverside Walk", "Notre-Dame Cathedral")
    for (_, day), name in zip(day_sections(page), expected_names):
        slots = slot_regions(day)
        assert name in slots[0][1].text
        assert "free" in slots[0][1].text.casefold()
        evening = slots[1][1].text.casefold()
        assert "no additional matching idea" in evening
        assert "free activity" not in evening and "free meal" not in evening
        assert "0.00" in day.text
    assert "60.00" in page.text and "0.00" in page.text
    assert_filled_count(page.text, 3, 6)
    assert "meal" in page.text.casefold()
    assert "Le Procope" not in page.text and "Café de Flore" not in page.text


def test_no_matches_still_has_all_days_zero_estimates_and_recovery_actions(
    client, draft_data, set_draft, parse_page,
):
    from catalog import load_catalog

    draft_data["preferences"].update(budget="1.00", interests=["food"])
    set_draft(client, draft_data)
    page = itinerary_page(client, parse_page)
    days = day_sections(page)

    assert [number for number, _ in days] == [1, 2, 3]
    for _, day in days:
        assert "0.00" in day.text
        for _, slot in slot_regions(day):
            assert "no additional matching idea" in slot.text.casefold()
    assert not any(place["name"] in page.text for place in load_catalog())
    assert "1.00" in page.text and "0.00" in page.text
    assert_filled_count(page.text, 0, 6)
    text = page.text.casefold()
    assert "interest" in text and ("allowance" in text or "budget" in text)
    assert any("edit" in node.text.casefold() for node in page.find_all("a", href="/plan"))


def test_food_only_places_restaurants_only_in_evenings_in_ranked_order(
    client, draft_data, set_draft, parse_page,
):
    draft_data["preferences"].update(interests=["food"])
    set_draft(client, draft_data)
    page = itinerary_page(client, parse_page)
    days = day_sections(page)

    for _, day in days:
        morning = slot_regions(day)[0][1]
        assert "no additional matching idea" in morning.text.casefold()
        assert "Café de Flore" not in morning.text and "Le Procope" not in morning.text
    assert "Café de Flore" in slot_regions(days[0][1])[1][1].text
    assert "Le Procope" in slot_regions(days[1][1])[1][1].text
    assert "no additional matching idea" in slot_regions(days[2][1])[1][1].text.casefold()
    assert "78.00" in page.text and "222.00" in page.text
    assert_filled_count(page.text, 2, 6)


@pytest.mark.parametrize("days", [1, 14])
def test_day_sections_keep_requested_count_even_when_the_catalog_is_too_small(
    client, draft_data, set_draft, parse_page, days,
):
    draft_data["preferences"].update(days=days, budget="1.00", interests=["food"])
    set_draft(client, draft_data)
    page = itinerary_page(client, parse_page)
    assert [number for number, _ in day_sections(page)] == list(range(1, days + 1))
    assert_filled_count(page.text, 0, 2 * days)


def test_scheduled_preferences_not_confirmed_when_tagged_alternative_is_unused(
    client, draft_data, set_draft, make_place, replace_catalog, parse_page,
):
    places = [
        make_place(id="first", name="First daytime idea", interest_tags=("food", "history")),
        make_place(id="meal", name="Evening meal idea", category="restaurant", interest_tags=("food", "history")),
        make_place(id="unused", name="Unused tagged idea", preference_tags=("relaxed", "family-friendly")),
    ]
    replace_catalog(places)
    draft_data["preferences"].update(days=1)
    set_draft(client, draft_data)
    page = itinerary_page(client, parse_page)
    assert "First daytime idea" in page.text and "Evening meal idea" in page.text
    notice_regions = page.find_all("p") + page.find_all("li") + page.find_all(role="status")
    for preference in ("relaxed", "family friendly"):
        assert any(
            preference in region.text.casefold().replace("-", " ")
            and any(word in region.text.casefold() for word in (
                "cannot", "could not", "not confirm", "unconfirmed", "no scheduled", "none of the scheduled",
            ))
            for region in notice_regions
        ), f"The itinerary must explain that its scheduled items do not confirm {preference}."
    scheduled_text = " ".join(slot.text for _, day in day_sections(page) for _, slot in slot_regions(day))
    assert "Unused tagged idea" not in scheduled_text
    assert "tagged relaxed" not in scheduled_text.casefold()
    assert "tagged family-friendly" not in scheduled_text.casefold()


def test_back_edit_and_clear_are_real_navigation_links_and_a_protected_form(
    client, set_draft, parse_page,
):
    set_draft(client)
    page = itinerary_page(client, parse_page)
    back = [link for link in page.find_all("a", href="/recommendations") if "back to trip ideas" in link.text.casefold()]
    edit = [link for link in page.find_all("a", href="/plan") if "edit preferences" in link.text.casefold()]
    assert back and edit
    assert client.get(back[0].attrs["href"]).status_code == 200
    form_page = parse_page(client.get(edit[0].attrs["href"]))
    assert form_page.find("input", name="days").attrs.get("value") == "3"
    assert form_page.find("input", name="budget").attrs.get("value") == "300.00"
    clear_form_and_token(page)


def test_refresh_is_deterministic_and_does_not_store_generated_records_in_session(
    client, set_draft, csrf_token, parse_page,
):
    stored = set_draft(client)
    csrf_token(client)  # Initial rendering may create this legitimate form token.
    with client.session_transaction() as session:
        before = deepcopy(dict(session))
    first = itinerary_page(client, parse_page)
    second = itinerary_page(client, parse_page)

    assert first.text == second.text
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored
        assert dict(session) == before
        assert session.permanent is False


def test_valid_edit_changes_the_next_itinerary_and_keeps_the_recommendations_step(
    client, set_draft, valid_form, submit_trip, parse_page,
):
    set_draft(client)
    assert "103.00" in itinerary_page(client, parse_page).text
    valid_form["budget"] = "60.00"
    response = submit_trip(client, valid_form)
    assert response.status_code == 303
    assert_redirect(response, "/recommendations")
    ideas = parse_page(client.get("/recommendations"))
    updated = parse_page(client.get(itinerary_link(ideas).attrs["href"]))
    assert "60.00" in updated.text and "0.00" in updated.text
    assert "Le Procope" not in updated.text and "Café de Flore" not in updated.text
    assert_filled_count(updated.text, 3, 6)


def test_invalid_edit_preserves_the_last_valid_draft_and_computed_itinerary(
    client, set_draft, valid_form, submit_trip, parse_page,
):
    stored = set_draft(client)
    before = itinerary_page(client, parse_page)
    valid_form["days"] = "0"
    response = submit_trip(client, valid_form)
    assert response.status_code == 200
    form = parse_page(response)
    assert form.find(role="alert") is not None
    assert form.find("input", name="days").attrs.get("value") == "0"
    assert itinerary_page(client, parse_page).text == before.text
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored


def test_catalog_cost_changes_are_recomputed_without_replacing_the_valid_draft(
    client, set_draft, replace_catalog, parse_page,
):
    from catalog import load_catalog

    stored = set_draft(client)
    assert "Le Procope" in itinerary_page(client, parse_page).text
    places = deepcopy(load_catalog())
    for place in places:
        if place["id"] == "paris-le-procope":
            place["estimated_cost"] = 999
    replace_catalog(places)
    page = itinerary_page(client, parse_page)

    assert "Le Procope" not in page.text
    assert "Café de Flore" in page.text and "Eiffel Tower" in page.text
    assert "85.00" in page.text and "215.00" in page.text
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored


def test_catalog_tag_changes_recompute_eligibility_rank_and_original_reasons(
    client, set_draft, replace_catalog, parse_page,
):
    from catalog import load_catalog

    stored = set_draft(client)
    assert "Le Procope" in itinerary_page(client, parse_page).text
    places = deepcopy(load_catalog())
    for place in places:
        if place["id"] == "paris-le-procope":
            place["interest_tags"] = ["nature"]
        elif place["id"] == "paris-seine-riverside-walk":
            place["interest_tags"].append("food")
    replace_catalog(places)
    page = itinerary_page(client, parse_page)

    assert "Le Procope" not in page.text
    first_morning = slot_regions(day_sections(page)[0][1])[0][1]
    assert "Seine Riverside Walk" in first_morning.text
    assert "Matches food and history; tagged relaxed" in first_morning.text
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored


def test_missing_draft_redirects_to_the_planner_with_useful_feedback(client, parse_page):
    assert_redirect(client.get("/itinerary"), "/plan")
    page = parse_page(client.get("/plan"))
    assert page.find("form", action="/plan") is not None
    notices = page.find_all(role="status") + page.find_all(role="alert")
    assert any("draft" in notice.text.casefold() for notice in notices)


@pytest.mark.parametrize("bad_draft", [None, [], {}, "broken", {"version": 99, "preferences": {}}])
def test_malformed_or_obsolete_draft_recovers_instead_of_generating_an_itinerary(
    client, bad_draft, parse_page,
):
    with client.session_transaction() as session:
        session["trip_draft"] = bad_draft
    assert_redirect(client.get("/itinerary"), "/plan")
    page = parse_page(client.get("/plan"))
    assert page.find("form", action="/plan") is not None
    notices = page.find_all(role="status") + page.find_all(role="alert")
    assert any("draft" in notice.text.casefold() for notice in notices)
    with client.session_transaction() as session:
        assert "trip_draft" not in session


@pytest.mark.parametrize("field,value", [
    ("destination", "Unsupported City"),
    ("interests", ["space-tourism"]),
    ("pace", "active"),
    ("days", 0),
])
def test_no_longer_supported_or_invalid_preferences_use_existing_draft_recovery(
    client, draft_data, set_draft, parse_page, field, value,
):
    draft_data["preferences"][field] = value
    set_draft(client, draft_data)
    assert_redirect(client.get("/itinerary"), "/plan")
    page = parse_page(client.get("/plan"))
    assert page.find("input", name="days").attrs.get("value", "") == ""
    with client.session_transaction() as session:
        assert "trip_draft" not in session


def test_invalid_signed_cookie_behaves_like_no_draft(client, app):
    client.set_cookie(app.config["SESSION_COOKIE_NAME"], "not-a-valid-session-signature")
    assert_redirect(client.get("/itinerary"), "/plan")


def test_sessions_do_not_share_generated_itineraries_or_drafts(
    client, client_factory, draft_data, set_draft, parse_page,
):
    stored = set_draft(client)
    other = client_factory()
    assert_redirect(other.get("/itinerary"), "/plan")
    draft_data["preferences"]["budget"] = "60.00"
    other_stored = set_draft(other, draft_data)
    assert "103.00" in itinerary_page(client, parse_page).text
    other_page = itinerary_page(other, parse_page)
    assert "60.00" in other_page.text and "Le Procope" not in other_page.text
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored
    with other.session_transaction() as session:
        assert session["trip_draft"] == other_stored


def test_clearing_from_actual_itinerary_form_removes_access_but_preserves_other_data_and_session(
    client, client_factory, set_draft, parse_page,
):
    set_draft(client)
    other = client_factory()
    other_stored = set_draft(other)
    with client.session_transaction() as session:
        session["class_note"] = "keep this unrelated session value"
    page = itinerary_page(client, parse_page)
    form, token = clear_form_and_token(page)
    response = client.post(form.attrs["action"], data={"csrf_token": token})

    assert response.status_code == 303
    assert_redirect(response, "/plan")
    with client.session_transaction() as session:
        assert "trip_draft" not in session
        assert session["class_note"] == "keep this unrelated session value"
    assert_redirect(client.get("/itinerary"), "/plan")
    assert_redirect(client.get("/recommendations"), "/plan")
    assert "103.00" in itinerary_page(other, parse_page).text
    with other.session_transaction() as session:
        assert session["trip_draft"] == other_stored


@pytest.mark.parametrize("token_kind", ["missing", "empty", "invalid", "other-session"])
def test_unverified_clear_requests_preserve_the_valid_draft_and_itinerary(
    client, client_factory, set_draft, parse_page, token_kind,
):
    stored = set_draft(client)
    before = itinerary_page(client, parse_page)
    _, actual_token = clear_form_and_token(before)
    if token_kind == "other-session":
        other = client_factory()
        set_draft(other)
        _, submitted_token = clear_form_and_token(itinerary_page(other, parse_page))
        assert submitted_token != actual_token
        data = {"csrf_token": submitted_token}
    elif token_kind == "missing":
        data = {}
    else:
        data = {"csrf_token": "" if token_kind == "empty" else "incorrect-token"}

    response = client.post("/draft/clear", data=data)
    assert response.status_code == 400
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored
    assert itinerary_page(client, parse_page).text == before.text


def test_get_cannot_clear_a_draft(client, set_draft):
    stored = set_draft(client)
    assert client.get("/draft/clear").status_code == 405
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored


def test_itinerary_does_not_add_a_state_changing_post_endpoint(client, set_draft):
    stored = set_draft(client)
    assert client.post("/itinerary").status_code == 405
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored


def test_complete_journey_works_with_server_rendered_links_and_forms_without_javascript(
    client, valid_form, submit_trip, parse_page,
):
    response = submit_trip(client)
    assert response.status_code == 303
    assert_redirect(response, "/recommendations")
    ideas = parse_page(client.get(response.headers["Location"]))
    page = parse_page(client.get(itinerary_link(ideas).attrs["href"]))
    assert "103.00" in page.text

    edit = next(link for link in page.find_all("a", href="/plan") if "edit" in link.text.casefold())
    form_page = parse_page(client.get(edit.attrs["href"]))
    form = form_page.find("form", action="/plan")
    assert form is not None and form.attrs.get("method", "").casefold() == "post"
    token = form.find("input", name="csrf_token").attrs["value"]
    edited_values = {**valid_form, "budget": "60.00", "csrf_token": token}
    edited_values["currency_context"] = form.find("input", name="currency_context").attrs["value"]
    response = client.post(form.attrs["action"], data=edited_values)
    assert response.status_code == 303
    assert_redirect(response, "/recommendations")
    updated_ideas = parse_page(client.get(response.headers["Location"]))
    updated = parse_page(client.get(itinerary_link(updated_ideas).attrs["href"]))
    assert_filled_count(updated.text, 3, 6)
    clear, clear_token = clear_form_and_token(updated)
    cleared = client.post(clear.attrs["action"], data={"csrf_token": clear_token})
    assert cleared.status_code == 303
    assert_redirect(cleared, "/plan")
    assert_redirect(client.get("/itinerary"), "/plan")

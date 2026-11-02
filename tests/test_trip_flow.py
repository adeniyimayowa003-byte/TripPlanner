"""User journeys through results, editing, refresh, recovery, and clearing."""

from copy import deepcopy
import json
from urllib.parse import urlsplit

import pytest


def assert_redirect(response, destination):
    assert response.status_code in (302, 303)
    assert urlsplit(response.headers["Location"]).path == destination


def test_results_show_real_ranked_ideas_summary_and_matching_reasons(client, set_draft, parse_page):
    set_draft(client)
    response = client.get("/recommendations")
    page = parse_page(response)
    text = page.text.casefold()

    assert response.status_code == 200
    assert "Paris, France" in page.text
    assert "3 days" in text and "300.00" in text and "100.00" in text
    assert all(word in text for word in ("food", "history", "relaxed", "family"))
    assert "per person" in text
    assert text.index("le procope") < text.index("luxembourg gardens") < text.index("seine riverside walk")
    assert "match" in text and "chosen" in text
    assert "alternative" in text and "estimate" in text
    assert "combined" in text or "added together" in text
    assert "itinerary total" in text or "total cost" in text
    assert "free" in text
    assert page.find("a", href="/plan") is not None
    assert len(page.find_all("h1")) == 1


def test_every_real_recommendation_includes_details_category_cost_and_source(client, set_draft, parse_page):
    from catalog import load_catalog

    set_draft(client)
    response = client.get("/recommendations")
    page = parse_page(response)

    assert response.status_code == 200
    # All seven current Paris items match history and/or food and fit EUR 100/day.
    for place in load_catalog():
        assert place["name"] in page.text
        assert place["description"] in page.text
        assert place["category"] in page.text.casefold()
        assert page.find("a", href=place["source_url"]) is not None
        if place["estimated_cost"]:
            assert format(place["estimated_cost"], ".2f") in page.text


def test_missing_draft_redirects_to_a_useful_form_message(client, parse_page):
    response = client.get("/recommendations")
    assert_redirect(response, "/plan")
    page = parse_page(client.get("/plan"))
    feedback = page.find_all(role="status") + page.find_all(role="alert")

    assert any("draft" in region.text.casefold() for region in feedback)
    assert page.find("form", action="/plan") is not None


def test_refresh_keeps_the_same_current_draft_and_results(client, set_draft, parse_page):
    stored = set_draft(client)
    first = client.get("/recommendations")
    second = client.get("/recommendations")

    assert first.status_code == second.status_code == 200
    assert parse_page(first).text == parse_page(second).text
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored
        assert session.permanent is False


def test_edit_form_is_prefilled_with_every_current_preference(client, set_draft, parse_page):
    set_draft(client)
    page = parse_page(client.get("/plan"))

    assert page.find("input", name="days").attrs.get("value") == "3"
    assert page.find("input", name="budget").attrs.get("value") == "300.00"
    for value in ("Paris, France", "relaxed"):
        assert "selected" in page.find("option", value=value).attrs
    for value in ("food", "history"):
        assert "checked" in page.find("input", name="interests", value=value).attrs
    assert "checked" in page.find("input", name="family_friendly").attrs


def test_valid_edit_replaces_draft_and_changes_eligible_ideas(client, set_draft, valid_form, submit_trip):
    set_draft(client)
    valid_form["budget"] = "60.00"
    response = submit_trip(client, valid_form)

    assert response.status_code == 303
    assert_redirect(response, "/recommendations")
    results = client.get("/recommendations")
    assert results.status_code == 200
    text = results.get_data(as_text=True)
    assert "Le Procope" not in text
    assert "Café de Flore" not in text
    assert "Luxembourg Gardens" in text
    with client.session_transaction() as session:
        assert session["trip_draft"]["preferences"]["budget"] == "60.00"


def test_invalid_edit_preserves_previous_valid_results(client, set_draft, valid_form, submit_trip, parse_page):
    old_draft = set_draft(client)
    valid_form["days"] = "0"
    response = submit_trip(client, valid_form)

    assert response.status_code == 200
    page = parse_page(response)
    assert page.find(role="alert") is not None
    assert page.find("input", name="days").attrs.get("value") == "0"
    with client.session_transaction() as session:
        assert session["trip_draft"] == old_draft
    assert "Le Procope" in client.get("/recommendations").get_data(as_text=True)


def test_unchecked_optional_fields_replace_previous_selections(client, set_draft, valid_form, submit_trip):
    set_draft(client)
    valid_form.pop("family_friendly")
    valid_form["pace"] = ""
    response = submit_trip(client, valid_form)

    assert response.status_code == 303
    with client.session_transaction() as session:
        preferences = session["trip_draft"]["preferences"]
        assert preferences["pace"] == ""
        assert preferences["family_friendly"] is False


def test_no_matches_keeps_summary_and_offers_edit_instead_of_unrelated_places(
    client, draft_data, set_draft, parse_page,
):
    draft_data["preferences"].update(budget="1.00", interests=["food"])
    set_draft(client, draft_data)
    response = client.get("/recommendations")
    page = parse_page(response)
    text = page.text.casefold()

    assert response.status_code == 200
    assert "Paris, France" in page.text and "1.00" in page.text
    assert "no" in text and ("match" in text or "fit" in text)
    assert "budget" in text or "allowance" in text
    edit = [link for link in page.find_all("a", href="/plan") if "edit" in link.text.casefold()]
    assert edit
    assert "Café de Flore" not in page.text
    assert "Luxembourg Gardens" not in page.text


def test_unmatched_family_preference_is_explained_on_results(client, draft_data, set_draft, parse_page):
    draft_data["preferences"].update(interests=["food"], pace="")
    set_draft(client, draft_data)
    response = client.get("/recommendations")
    page = parse_page(response)
    text = page.text.casefold().replace("-", " ")

    assert response.status_code == 200
    assert "Café de Flore" in page.text
    assert "family friendly" in text
    assert any(word in text for word in ("cannot", "could not", "unconfirmed", "no matching", "not confirm"))


def test_separate_browser_sessions_do_not_share_drafts(client, client_factory, set_draft):
    stored = set_draft(client)
    other_browser = client_factory()

    assert_redirect(other_browser.get("/recommendations"), "/plan")
    with other_browser.session_transaction() as session:
        assert "trip_draft" not in session
    with client.session_transaction() as session:
        assert session["trip_draft"] == stored


def test_clear_is_a_real_post_form_and_returns_to_a_blank_planner(
    client, set_draft, csrf_token, parse_page,
):
    set_draft(client)
    with client.session_transaction() as session:
        session["class_note"] = "keep this unrelated value"
    results_page = parse_page(client.get("/recommendations"))
    clear_form = results_page.find("form", action="/draft/clear")

    assert clear_form is not None
    assert clear_form.attrs.get("method", "").casefold() == "post"
    assert "clear this draft" in clear_form.text.casefold()
    token = csrf_token(client, "/recommendations")
    response = client.post("/draft/clear", data={"csrf_token": token})

    assert response.status_code == 303
    assert_redirect(response, "/plan")
    with client.session_transaction() as session:
        assert "trip_draft" not in session
        assert session["class_note"] == "keep this unrelated value"
    page = parse_page(client.get("/plan"))
    assert page.find("input", name="days").attrs.get("value", "") == ""
    assert page.find("input", name="budget").attrs.get("value", "") == ""
    assert not any("checked" in node.attrs for node in page.find_all("input", name="interests"))
    assert "checked" not in page.find("input", name="family_friendly").attrs
    feedback = page.find_all(role="status") + page.find_all(role="alert")
    assert any("clear" in region.text.casefold() for region in feedback)
    assert parse_page(client.get("/")).find("a", href="/recommendations") is None


def test_clearing_one_draft_does_not_clear_another_session(client, client_factory, set_draft, csrf_token):
    set_draft(client)
    other_browser = client_factory()
    other_draft = set_draft(other_browser)
    response = client.post("/draft/clear", data={"csrf_token": csrf_token(client)})

    assert response.status_code == 303
    with other_browser.session_transaction() as session:
        assert session["trip_draft"] == other_draft


@pytest.mark.parametrize("bad_draft", [None, [], {}, {"version": 99, "preferences": {}}, "broken"])
def test_corrupt_or_obsolete_draft_recovers_without_crashing(client, bad_draft, parse_page):
    with client.session_transaction() as session:
        session["trip_draft"] = bad_draft
    response = client.get("/recommendations")

    assert_redirect(response, "/plan")
    page = parse_page(client.get("/plan"))
    assert page.find("form", action="/plan") is not None
    with client.session_transaction() as session:
        assert "trip_draft" not in session


def test_unsupported_stored_preferences_are_not_used_for_resume_or_prefill(client, draft_data, set_draft, parse_page):
    draft_data["preferences"]["destination"] = "Unsupported City"
    set_draft(client, draft_data)

    home = parse_page(client.get("/"))
    form = parse_page(client.get("/plan"))
    assert home.find("a", href="/recommendations") is None
    assert form.find("input", name="days").attrs.get("value", "") == ""
    with client.session_transaction() as session:
        assert "trip_draft" not in session


def test_invalid_signed_cookie_is_handled_like_a_missing_draft(client, app):
    client.set_cookie(app.config["SESSION_COOKIE_NAME"], "invalid-session-signature")

    assert_redirect(client.get("/recommendations"), "/plan")


def test_results_are_recomputed_from_changed_catalog_costs(client, set_draft, monkeypatch, tmp_path):
    import catalog

    set_draft(client)
    first = client.get("/recommendations")
    assert first.status_code == 200
    assert "Le Procope" in first.get_data(as_text=True)

    changed_places = deepcopy(catalog.load_catalog())
    for place in changed_places:
        if place["id"] == "paris-le-procope":
            place["estimated_cost"] = 999
    catalog_file = tmp_path / "changed-catalog.json"
    catalog_file.write_text(json.dumps({"places": changed_places}), encoding="utf-8")
    monkeypatch.setattr(catalog, "CATALOG_FILE", catalog_file)

    second = client.get("/recommendations")
    assert second.status_code == 200
    assert "Le Procope" not in second.get_data(as_text=True)
    assert "Luxembourg Gardens" in second.get_data(as_text=True)


def test_core_journey_uses_server_forms_without_executing_javascript(client, submit_trip, csrf_token, parse_page):
    response = submit_trip(client)
    assert response.status_code == 303
    page = parse_page(client.get("/recommendations"))
    assert "Le Procope" in page.text
    edit_links = [node for node in page.find_all("a", href="/plan") if "edit" in node.text.casefold()]
    assert edit_links
    assert client.get(edit_links[0].attrs["href"]).status_code == 200
    clear_response = client.post("/draft/clear", data={"csrf_token": csrf_token(client)})
    assert clear_response.status_code == 303

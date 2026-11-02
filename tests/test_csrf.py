"""Changing either preferences or the draft requires a session-bound token."""

from copy import deepcopy

import pytest


@pytest.mark.parametrize("route", ["/plan", "/draft/clear"])
@pytest.mark.parametrize("token", [None, "", "invalid-token"])
def test_rejected_tokens_do_not_change_existing_draft(
    client, valid_form, set_draft, parse_page, route, token,
):
    original = set_draft(client)
    data = deepcopy(valid_form) if route == "/plan" else {}
    if token is not None:
        data["csrf_token"] = token
    response = client.post(route, data=data)

    assert response.status_code == 400
    with client.session_transaction() as session:
        assert session["trip_draft"] == original
    page = parse_page(response)
    assert page.find("a", href="/plan") is not None
    assert any(word in page.text.casefold() for word in ("form", "token", "try again"))


@pytest.mark.parametrize("route", ["/plan", "/draft/clear"])
def test_another_sessions_token_is_rejected(
    client, client_factory, csrf_token, valid_form, set_draft, route,
):
    original = set_draft(client)
    own_token = csrf_token(client)
    other_token = csrf_token(client_factory())
    assert own_token != other_token
    data = deepcopy(valid_form) if route == "/plan" else {}
    data["csrf_token"] = other_token

    response = client.post(route, data=data)

    assert response.status_code == 400
    with client.session_transaction() as session:
        assert session["trip_draft"] == original


def test_page_views_cannot_clear_a_draft(client, set_draft):
    original = set_draft(client)

    assert client.get("/draft/clear").status_code == 405
    with client.session_transaction() as session:
        assert session["trip_draft"] == original


def test_opening_another_form_does_not_invalidate_the_first_token(client, csrf_token, valid_form, parse_page):
    first_token = csrf_token(client)
    currency = parse_page(client.get("/plan")).find("input", name="currency_context").attrs["value"]
    csrf_token(client)

    response = client.post("/plan", data={**valid_form, "csrf_token": first_token, "currency_context": currency})

    assert response.status_code == 303


def test_valid_token_allows_clearing_a_draft(client, csrf_token, set_draft):
    set_draft(client)

    response = client.post("/draft/clear", data={"csrf_token": csrf_token(client)})

    assert response.status_code == 303
    with client.session_transaction() as session:
        assert "trip_draft" not in session


def test_local_session_configuration_is_http_only_and_same_site(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] in ("Lax", "Strict")

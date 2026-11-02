"""Signed displayed-currency/review state, separate from CSRF and trip data."""

from copy import deepcopy

from flask import session
from itsdangerous import URLSafeSerializer
import pytest

from phase8_helpers import CITY_PROFILES
from phase8_form_helpers import context_functions, legacy_v1_draft


SALT = "tripplanner.currency-context.v1"
VALID_STATES = [(None, False)] + [
    (profile["currency"], pending) for profile in CITY_PROFILES for pending in (False, True)
]


@pytest.mark.parametrize("currency,pending", VALID_STATES)
def test_context_round_trip_has_signed_session_bound_typed_state_and_preserves_trip_data(app, currency, pending):
    issue_context, read_context = context_functions()
    with app.test_request_context("/plan"):
        session["trip_draft"] = legacy_v1_draft()
        session["csrf_token"] = "independent-csrf-example"
        before = deepcopy(dict(session))
        token = issue_context(currency, confirmation_required=pending)
        expected = {"version": 1, "currency": currency, "confirmation_required": pending}
        assert isinstance(token, str) and token != session["csrf_token"]
        assert read_context(token) == expected
        signed = URLSafeSerializer(app.secret_key, salt=SALT).loads(token)
        assert set(signed) == {*expected, "nonce"}
        assert signed["nonce"] == session["currency_context_nonce"]
        assert isinstance(signed["nonce"], str) and signed["nonce"]
        assert {key: signed[key] for key in expected} == expected
        assert session["trip_draft"] == before["trip_draft"] and session["csrf_token"] == before["csrf_token"]


@pytest.mark.parametrize("token", [None, True, 1, "", "forged", '<script>JPY</script>', "x" * 5000])
def test_invalid_context_tokens_raise_a_useful_error_after_a_valid_control_works(app, token):
    issue_context, read_context = context_functions()
    with app.test_request_context("/plan"):
        assert read_context(issue_context("EUR"))["currency"] == "EUR"
        with pytest.raises(ValueError, match=r".+"):
            read_context(token)


@pytest.mark.parametrize("field,value", [
    ("version", True), ("version", 2), ("version", "1"),
    ("currency", "XXX"), ("currency", True), ("confirmation_required", "on"),
    ("confirmation_required", 1), ("nonce", "wrong-browser"), ("nonce", None),
])
def test_even_signed_payloads_must_have_valid_schema_currency_and_session_binding(app, field, value):
    issue_context, read_context = context_functions()
    with app.test_request_context("/plan"):
        serializer = URLSafeSerializer(app.secret_key, salt=SALT)
        token = issue_context("JPY", confirmation_required=True)
        assert read_context(token)["confirmation_required"] is True
        payload = serializer.loads(token)
        payload[field] = value
        with pytest.raises(ValueError):
            read_context(serializer.dumps(payload))


@pytest.mark.parametrize("field", ["version", "currency", "confirmation_required", "nonce"])
def test_missing_signed_context_fields_are_rejected(app, field):
    issue_context, read_context = context_functions()
    with app.test_request_context("/plan"):
        serializer = URLSafeSerializer(app.secret_key, salt=SALT)
        token = issue_context("GBP")
        assert read_context(token)["currency"] == "GBP"
        payload = serializer.loads(token)
        del payload[field]
        with pytest.raises(ValueError):
            read_context(serializer.dumps(payload))


def test_a_pending_confirmation_needs_a_real_currency_not_neutral_context(app):
    issue_context, read_context = context_functions()
    with app.test_request_context("/plan"):
        assert read_context(issue_context())["currency"] is None
        with pytest.raises(ValueError):
            issue_context(None, confirmation_required=True)


@pytest.mark.parametrize("currency,pending", [("XXX", False), (True, False), ("EUR", "on"), ("EUR", 1)])
def test_issuing_context_requires_known_currency_and_an_actual_boolean(app, currency, pending):
    issue_context, _ = context_functions()
    with app.test_request_context("/plan"):
        with pytest.raises(ValueError):
            issue_context(currency, confirmation_required=pending)


def test_tokens_do_not_cross_browser_session_or_secret_boundaries(app):
    issue_context, read_context = context_functions()
    with app.test_request_context("/plan"):
        token = issue_context("EUR")
        first_nonce = session["currency_context_nonce"]
    with app.test_request_context("/plan"):
        issue_context("EUR")
        assert session["currency_context_nonce"] != first_nonce
        with pytest.raises(ValueError):
            read_context(token)
        session["currency_context_nonce"] = first_nonce
        assert read_context(token)["currency"] == "EUR"
        original_secret = app.secret_key
        app.secret_key = "another-qa-application-secret"
        try:
            with pytest.raises(ValueError):
                read_context(token)
        finally:
            app.secret_key = original_secret


def test_another_open_tab_does_not_invalidate_a_same_session_context(app):
    issue_context, read_context = context_functions()
    with app.test_request_context("/plan"):
        old = issue_context("EUR")
        pending = issue_context("JPY", confirmation_required=True)
        issue_context("USD")
        assert read_context(old) == {"version": 1, "currency": "EUR", "confirmation_required": False}
        assert read_context(pending)["currency"] == "JPY"


def test_signature_changes_and_wrong_token_purposes_cannot_be_accepted(app):
    issue_context, read_context = context_functions()
    with app.test_request_context("/plan"):
        token = issue_context("EUR")
        assert read_context(token)["currency"] == "EUR"
        head, signature = token.rsplit(".", 1)
        tampered = head + "." + ("A" if signature[0] != "A" else "B") + signature[1:]
        wrong_purpose = URLSafeSerializer(app.secret_key, salt="another-form-purpose").dumps(
            URLSafeSerializer(app.secret_key, salt=SALT).loads(token)
        )
        for bad in (tampered, wrong_purpose, "independent-csrf-token", "a" * 64):
            with pytest.raises(ValueError):
                read_context(bad)

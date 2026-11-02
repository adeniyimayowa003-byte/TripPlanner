"""Session-bound signed notes describing the currency shown by a trip form."""

import secrets

from flask import current_app, session
from itsdangerous import BadData, URLSafeSerializer

from currencies import get_currency


_SALT = "tripplanner.currency-context.v1"


def _validate_state(currency, confirmation_required):
    if currency is not None:
        get_currency(currency)
    if type(confirmation_required) is not bool or (currency is None and confirmation_required):
        raise ValueError("Invalid currency review state.")


def _serializer():
    return URLSafeSerializer(current_app.secret_key, salt=_SALT)


def issue_currency_context(currency=None, *, confirmation_required=False):
    _validate_state(currency, confirmation_required)
    nonce = session.get("currency_context_nonce")
    if not isinstance(nonce, str) or not nonce:
        nonce = secrets.token_urlsafe(32)
        session["currency_context_nonce"] = nonce
    return _serializer().dumps({"version": 1, "currency": currency,
                                "confirmation_required": confirmation_required, "nonce": nonce})


def read_currency_context(token):
    if not isinstance(token, str) or not token or len(token) > 4096:
        raise ValueError("Open the planner again to verify its currency.")
    try:
        payload = _serializer().loads(token)
        if (not isinstance(payload, dict)
                or set(payload) != {"version", "currency", "confirmation_required", "nonce"}
                or type(payload["version"]) is not int or payload["version"] != 1):
            raise ValueError("Invalid currency form context.")
        _validate_state(payload["currency"], payload["confirmation_required"])
        expected = session.get("currency_context_nonce")
        nonce = payload["nonce"]
        if (not isinstance(expected, str) or not isinstance(nonce, str) or not expected
                or not secrets.compare_digest(expected.encode("utf-8"), nonce.encode("utf-8"))):
            raise ValueError("This currency form belongs to another session.")
        return {key: payload[key] for key in ("version", "currency", "confirmation_required")}
    except (BadData, KeyError, TypeError, UnicodeError) as error:
        raise ValueError("Open the planner again to verify its currency.") from error

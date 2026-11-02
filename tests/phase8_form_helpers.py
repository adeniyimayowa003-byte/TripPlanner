"""Independent form examples; no future validator or serializer supplies truth."""

from copy import deepcopy
import json
import re

from werkzeug.datastructures import MultiDict

from phase8_helpers import (
    amount_text, api_symbol, legacy_snapshot_text, qa_preferences,
)


def form_for(profile, **changes):
    preferences = qa_preferences(profile)
    fields = {
        "destination": profile["name"], "days": "3",
        "budget": amount_text(preferences["budget"], profile["currency"]),
        "interests": ["food", "history"], "pace": "relaxed",
        "family_friendly": "on",
    }
    fields.update(changes)
    return MultiDict(fields)


def raw_preferences(form):
    return {
        "destination": form.get("destination", ""), "days": form.get("days", ""),
        "budget": form.get("budget", ""), "interests": form.getlist("interests"),
        "pace": form.get("pace", ""), "family_friendly": form.get("family_friendly") == "on",
    }


def independent_draft(profile):
    preferences = qa_preferences(profile)
    preferences["budget"] = amount_text(preferences["budget"], profile["currency"])
    return {"version": 2, "preferences": preferences}


def legacy_v1_draft():
    return {"version": 1, "preferences": json.loads(legacy_snapshot_text())["preferences"]}


def context_functions():
    return (
        api_symbol("currency_context", "issue_currency_context"),
        api_symbol("currency_context", "read_currency_context"),
    )


def context_fields(response_or_html, parse_page):
    if hasattr(response_or_html, "status_code"):
        assert response_or_html.status_code == 200
    page = parse_page(response_or_html)
    form = page.find("form", action="/plan")
    assert form is not None
    fields = {}
    for name in ("csrf_token", "currency_context"):
        node = form.find("input", name=name)
        assert node is not None, f"The planner requires a separate {name} field."
        assert node.attrs.get("type") == "hidden" and node.attrs.get("value")
        fields[name] = node.attrs["value"]
    assert fields["csrf_token"] != fields["currency_context"]
    return fields


def inspect_context(app, browser, token):
    from flask import session

    _, read_context = context_functions()
    with browser.session_transaction() as browser_session:
        copied = deepcopy(dict(browser_session))
    with app.test_request_context("/plan"):
        session.update(copied)
        return read_context(token)


def assert_visible_amount(text, expected):
    # Ignore grouping separators, but do not accept 100.00 as whole-yen 100.
    assert re.search(r"(?<![0-9.])" + re.escape(expected) + r"(?![0-9.])", text.replace(",", ""))

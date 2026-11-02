# Phase 4 — Understand the working TripPlanner flow

This guide explains the implementation of the approved personalized trip ideas increment.
Use it alongside the source code and your own experiments. Test and browser verification
results are reported separately; this guide explains the design and the expected behavior.

## What you are building

The traveler chooses details, receives relevant ideas, understands each match, and edits
the details to get different results. A current draft lets them return to those choices
within the same browser session.

The allowance covers **activities and food per person** for the requested days.
Flights, accommodation, and transport are excluded. Each result is an alternative idea:
several individually affordable ideas may cost too much when combined into an itinerary.
Daily itinerary generation and permanent saving belong to later increments.

## Where the responsibilities live

| File | Its job |
| --- | --- |
| `app.py` | Receive requests, check the draft, call the domain functions, and choose a response. |
| `catalog.py` | Load local place data and derive destination-specific choices. |
| `preferences.py` | Validate submitted answers and normalize valid answers. |
| `money.py` | Parse exact EUR amounts and calculate display values. |
| `recommendations.py` | Filter ideas, calculate scores, sort, and explain matches. |
| `drafts.py` | Convert preferences into session-safe data and validate them when read. |
| `csrf.py` | Issue and check a token for actions that change the current draft. |
| `templates/` | Turn prepared values into readable HTML pages. |
| `static/js/plan.js` | Enhance the form with an immediate daily allowance preview. |

Keeping these jobs separate makes a problem easier to find. A wrong score belongs in
recommendation logic; a confusing result label belongs in the template. The scoring and
money functions can be tested without opening a browser or starting Flask.

## Follow one submission through the application

1. **Open the form.** A `GET /plan` request asks Flask for the preferences page.
   Flask prepares catalog choices, any valid draft values, and a form token.
2. **Submit answers.** The browser sends `POST /plan`. Ordinary form fields arrive as
   text; several interest checkboxes arrive under the same field name.
3. **Check the form token.** Flask rejects an unverified submission before changing
   the current draft. A rejected form gives the traveler a route back to the planner.
4. **Validate and normalize.** `validate_trip_preferences()` returns `(values, errors)`.
   Errors lead back to the form with the original answers; success produces typed values.
5. **Store the successful draft.** `serialize_draft()` converts decimal money into a
   plain two-decimal string and stores one versioned draft in the browser session.
6. **Redirect to results.** Flask returns a `303` response pointing at `/recommendations`.
   The browser then requests that page with `GET`.
7. **Build the result.** Flask reloads and validates the draft, calculates recommendations
   from the current catalog, and passes the summary and results into the template.

This is the **POST–redirect–GET** pattern. Refreshing the results repeats a read request,
so it does not ask the browser to submit the form again. Editing follows the same process;
only another successful submission replaces the last valid draft.

## Why validation happens on the server

Browser controls help people enter sensible answers, but a request can bypass them.
The server independently checks days, the amount, destination, interests, and pace.
It accepts only choices supported by the selected destination's catalog data.

Normalization makes equivalent answers consistent. For example, `"  PARIS, FRANCE  "`
becomes `"Paris, France"`, `" HISTORY "` becomes `"history"`, and duplicate interests
are removed. Valid days become an integer, the allowance becomes a `Decimal`, and the
family preference becomes a Boolean (`True` or `False`).

An invalid answer returns all original values for correction. If the traveler already
has a valid draft, an invalid edit does not replace it. This separates a temporary form
mistake from the last usable set of preferences.

## Why money uses Decimal

Binary floating-point numbers can introduce tiny inaccuracies in decimal calculations.
`Decimal`, constructed from text, represents amounts such as `0.10` exactly.
`parse_budget()` accepts plain positive amounts with at most two decimal places and
enforces the EUR 0.01–1,000,000.00 range. Text such as `3e2` or `300.001` is rejected.

The daily preview divides the total by the days and rounds half up to two places.
With **EUR 100.01 over 3 days**, it displays approximately **EUR 33.34 per day**.
Affordability uses the original total instead:

```text
EUR 33.34 × 3 = EUR 100.02 → excluded
EUR 33.33 × 3 = EUR 99.99  → eligible if destination and interests also match
```

Rounding is for display. It does not increase the money available for an idea.

## How the personalized recommendations work

The recommender first checks three conditions: the destination matches, at least one
selected interest matches, and `item cost × days <= total allowance`.
It calculates points only for items that pass all three conditions.

- Each distinct matching interest earns **3 points**.
- An explicitly tagged selected pace earns **1 point**.
- An explicitly tagged family-friendly preference earns **1 point** when selected.

For food and history, with relaxed pace and family-friendly selected:

| Idea | Matching evidence | Score |
| --- | --- | ---: |
| Le Procope | Food and history: 3 + 3 | 6 |
| Luxembourg Gardens | History, relaxed, family-friendly: 3 + 1 + 1 | 5 |
| Seine Riverside Walk | History and relaxed: 3 + 1 | 4 |

Equal scores are ordered by lower cost, then name without case differences, then stable ID.
The result is deterministic: the same validated choices and catalog produce the same order.
Reasons name the actual matching tags. A missing family tag does not establish suitability,
and a selected preference that no eligible item matches produces a useful notice.

This is **rule-based AI**: human-written rules rank content according to a person's inputs.
It uses dictionaries, lists, sets, conditions, and sorting. It does not call a language model,
train a model, or invent destinations. All ideas come from the local sample catalog.

## What a current draft means

Flask stores the small draft in a signed browser-session cookie. Signing lets Flask detect
changes to its contents; it does not encrypt them. The app stores only trip preferences.
`drafts.py` converts the budget to text for serialization and restores `Decimal` on loading.
The version number and strict type checks help reject malformed or obsolete draft data.

The draft supports prefill, resume, and refreshed results. It is not a permanently saved trip,
and continuation after a browser session ends or a server restart is not guaranteed.
Different browser sessions have separate drafts. Clearing uses an explicit protected POST
and removes the current draft without removing unrelated session values.

The hidden CSRF token connects a submitted form to that browser's session. `csrf.py`
creates a random token and checks submissions with a constant-time comparison. Opening
another form keeps the same token usable, so multiple tabs can work together.

## What JavaScript adds

The browser preview gives immediate feedback while the traveler changes days or allowance.
It uses validated cents and shows a placeholder for incomplete or invalid values.
The server always checks the actual submission and recalculates the displayed result.

This is **progressive enhancement**: the server-rendered forms provide the core flow,
and JavaScript adds a convenience. With JavaScript disabled, submit, results, edit, resume,
and clear still use links and forms. The instant preview is replaced by explanatory text.

## Small tasks to complete and explain

1. Submit Paris, 3 days, EUR 300, food and history, relaxed, and family-friendly.
   Explain the top three scores using the table above.
2. Change only the allowance to EUR 60. Predict which paid ideas disappear before submitting.
3. Submit 0 days. Correct the error and check that the other answers remain.
   Confirm that the previous valid results remain available during the invalid edit.
4. Edit a draft, refresh results, return home to resume it, and then clear it.
   Try a separate browser session and explain why it has no copy of that draft.
5. Run tests and identify one unit test and one integration test. Explain which needs Flask.
6. Disable JavaScript and repeat a submission. Describe which convenience disappears.

From the project folder, use these PowerShell commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -q tests/test_money.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_recommendations.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_trip_flow.py
```

The money and recommendation tests check small rules directly. The trip-flow tests use
Flask's test client to check requests, redirects, sessions, and rendered pages. Those checks
do not replace browser checks for mobile layout, keyboard use, or JavaScript behavior.

## A short presentation talk track

“TripPlanner takes preferences and uses an explainable rule-based recommender to rank local
catalog ideas. Flask validates the form, uses exact decimal money, and stores one current
draft. Interest matches earn three points; optional tagged preferences earn one each.
Every result explains its evidence. The allowance filters each idea individually, and the
results are alternatives rather than a completed itinerary. I used specification-driven
development: approved behavior, a plan, tests defined first, and then implementation.”

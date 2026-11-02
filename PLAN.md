# TripPlanner — Implementation and Test Plans

**Selected hosting revision:** The user approved a free public demo with sleep/usage limits. Use the [free-demo plan](plans/phase-09-free-demo-plan.md), [approved amendment](specs/phase-09-free-demo.md) and [current setup guide](docs/free-demo-hosting.md). All **1,688 tests pass**, including real PostgreSQL and backup/restore. Render and Neon accounts are ready; a new Frankfurt Neon project exists. Public website/HTTPS acceptance remains pending; no paid plan/disk is authorized.

**Current approved increment:** [Phase 9 — public website availability](specs/phase-09-public-availability.md), approved 2 November 2026. Its [implementation and test plan](plans/phase-09-public-availability-plan.md) covers production configuration, separate anonymous collections, durable storage, and deployment verification. Hosting/account and paid-plan decisions remain pending; there is no public URL yet.

**Current SDD step:** Local implementation and verification complete after the validated test-first checkpoint; public deployment/account/cost decision and external HTTPS acceptance remain pending. The [implementation report](docs/phase-09-implementation.md) records the new hosting checks and remaining actions. The delivered local/native artifacts remain intact.

**Completed Phase 8:** [Six-city local-first release](specs/phase-08-expanded-release.md): suitable photos, destination currencies, external Google Maps buttons without API keys, and both Windows/Android downloadable targets. The following paragraph records that historical handoff.

**Current step:** The classroom handoff is complete within the recorded platform limits. All **1,596 pytest cases pass**. The Windows demo.2 keeps its verified extracted-app journey. The Android debug APK passes an actual-tap offline journey, saved-row/theme persistence after process restart, device Light/Dark, and manual Light over device Dark on an Android 15 x86_64 emulator. See the [Android report](docs/phase-08-android.md), [final checks](docs/final-release-checks.md), and [presentation walkthrough](docs/presentation-walkthrough.md). The handoff includes a 17-slide PowerPoint and 16-page Word guide. Physical ARM64 phones, other Windows hosts, a deliberately disconnected Windows journey, and public release signing/store approval remain unverified. GitHub preparation is local only; no repository has been uploaded. The main port-5000 collection remains untouched.

**Completed Phase 7:** Appearance is implemented with **943 passing cases**, including all 676 earlier cases unchanged. See the [verification report](docs/phase-07-implementation.md) for browser evidence, the test-first animation fix, and the explicit device-switch verification limit, and the [student guide](docs/phase-07-learning.md) for explanations/tasks. Its [plan](plans/phase-07-appearance-plan.md) is complete and [red checkpoint](docs/phase-07-testing.md) remains history. That increment's QA did not change real browser preferences or populate the default database.

**Completed Phase 6:** Durable saved trips are implemented with all 676 cases passing and browser checks covering responsive/keyboard flows, scripts blocked, restarts, and catalog independence. See its [verification report](docs/phase-06-implementation.md), [student guide](docs/phase-06-learning.md), [completed plan](plans/phase-06-saved-trips-plan.md), and [historical red checkpoint](docs/phase-06-testing.md).

**Completed Phase 5:** All 322 pytest cases pass; real-browser checks cover responsive layouts, keyboard navigation, edits, empty results, clearing, and application scripts blocked. See the [verification report](docs/phase-05-implementation.md), [learning guide](docs/phase-05-learning.md), and [completed implementation/test plan](plans/phase-05-itinerary-plan.md). The [red testing checkpoint](docs/phase-05-testing.md) remains as history.

**Verified Phase 6 baseline:** Before implementation, all 322 existing cases passed and 670 cases were defined/discovered at the red checkpoint. The verification report documents two narrow test-path corrections and six additional review checks. Tests/browser checks used isolated storage; the real default database remains absent and was not populated or reset.

## Completed restart plan — reference

The remaining sections preserve the completed personalized trip ideas plan. They describe the previous increment, not the current Phase 8 planning/testing status.

**Approved scope:** [Revised Phase 1 specification](specs/phase-01-restart.md)

**Completed checkpoint:** SDD step 4 — implementation complete for the approved personalized trip ideas increment. All 244 pytest cases pass, with browser checks recorded in the [implementation report](docs/phase-04-implementation.md). Read the [learning guide](docs/phase-04-learning.md) for explanations and practice tasks.

**Product increment:** Revised Phase 1 — personalized trip ideas. The SDD steps below describe how we build this increment; they are different from the product phases.

**History:** The [previous roadmap](plans/previous-roadmap.md) is preserved for reference. Its completed phase numbers and test counts belong to the previous build. This plan replaces it for current work and introduces no fixed timeline.

## 1. What we will deliver

The traveler moves through a complete flow:

**Home → preferences → personalized recommendations → edit and regenerate.**

A current draft also supports resuming from the home page and explicitly clearing the draft. Every recommendation comes from the existing Paris catalog and includes an explanation. The budget is an activities and food allowance per person, excluding flights, accommodation, and transport.

The first implementation will reuse the existing Flask app factory, JSON catalog, form, and CSS. It will replace the current confirmation-only submission with a result page. Daily itineraries and durable saved trips remain later increments.

## 2. The SDD sequence and current checkpoint

1. **Specification — complete:** The user approved the revised Phase 1 spec.
2. **Planning — complete:** Responsibilities, data contracts, routes, test coverage, and implementation order are defined below.
3. **Testing — complete before implementation:** The previous suite passed all 35 cases. At the red checkpoint, the revised suite discovered 244 cases: 45 passed and 199 failed for expected missing behavior, with no collection/setup errors or skipped cases. The [testing checkpoint](docs/phase-03-testing.md) preserves that history.
4. **Implementation — complete:** All 244 cases now pass. The approved flow, responsive layouts, keyboard controls, budget preview, and operation with app scripts blocked have been checked in the browser. The [implementation report](docs/phase-04-implementation.md) records the method and results.

The testing step may change test files and shared fixtures. Application modules, templates, styles, and scripts must not be changed to implement the restart until the tests have been defined and the expected failing results reviewed.

The [Phase 4 guide](docs/phase-04-learning.md) explains each implemented slice and supplies small practice tasks. Later increments, including daily itineraries and durable saved trips, are still separate work.

## 3. Files and responsibilities

| File or area | Responsibility |
| --- | --- |
| `app.py` | Create/configure the app, handle routes, read or replace a draft, redirect, and pass prepared values to templates. Keep scoring and money rules outside route functions. |
| `catalog.py` | Retain catalog loading and destination lookup. Add destination-specific interest and pace options. Preserve existing catalog behavior where it still matches the approved spec. |
| `preferences.py` | Validate raw form values, preserve them on errors, and return canonical preferences only when valid. Use the selected destination's available tags. |
| `money.py` — new | Parse allowed EUR amounts, preserve decimal cents, calculate the displayed daily allowance with half-up rounding, and format two-decimal amounts. |
| `recommendations.py` — new | Filter and rank eligible items, return matching evidence and explanations, and identify selected preferences that could not be matched. No Flask or session dependency. |
| `drafts.py` — new | Convert normalized preferences to session-safe data and validate stored drafts before reuse. No scoring and no database. |
| `csrf.py` — new | Create and validate session-bound form tokens for both POST actions. Keep this small and directly tested. |
| `templates/base.html` — new | Shared page structure, navigation, local/system fonts, and feedback messages. |
| Existing home/form templates | Show current capabilities, supported options, preserved answers, error associations, and useful actions. |
| `templates/recommendations.html` — new | Render the trip summary, ranked cards, explanations, empty-state recovery, and edit/clear controls. |
| `templates/error.html` — new | Render a useful recovery message when a form token is invalid. |
| `static/css/style.css` | Consistent responsive layouts, readable results, clear selection states, and visible keyboard focus. |
| `static/js/plan.js` — new | Enhance the form with a daily allowance preview. It does not authorize submissions or generate recommendations. |
| `tests/conftest.py` — new | Shared app/client factories, deterministic catalog fixtures, and helpers that obtain real form tokens. |
| `README.md` | Describe setup, the current flow, allowance meaning, draft lifetime, scoring rules, tests, and demonstration tasks after implementation. |

Use the existing Flask and pytest dependencies. Python's standard library supplies decimal arithmetic, random tokens, token comparison, and environment configuration; no external AI service or new framework is necessary.

## 4. Data and logic contracts

### 4.1 Catalog options

- Keep `get_supported_destinations(catalog=None)` and the existing destination lookup.
- Extend interest lookup with an optional destination keyword while preserving the existing positional catalog argument used by tests.
- Add a helper for supported pace tags for a selected destination. Recognize only known pace tags such as relaxed and active; family-friendly is a separate preference.
- Derive displayed choices and server validation from the same catalog. The current Paris form offers relaxed and no preference; it does not offer active.
- Allow small catalogs to be supplied to domain functions during testing. Do not require tests to edit the real JSON file.

### 4.2 Preference representations

Keep two clearly separated representations:

| Value | During validation and recommendation | In the browser-session draft |
| --- | --- | --- |
| Destination | Canonical supported string | Same string |
| Days | Integer from 1 to 14 | Same integer |
| Budget | `Decimal`, normalized to cents | Plain string with two decimals, for example `300.00` |
| Interests | Unique canonical strings | List of those strings |
| Pace | Supported canonical string, or empty string | Same string |
| Family-friendly | Boolean | Same boolean |

Use a small versioned draft envelope so malformed or obsolete session data can be rejected predictably. Store only normalized preferences, not rendered HTML or a growing list of previous results.

The validator continues to return `(values, errors)`. On error, `values` contains the raw submitted answers for redisplay. On success, it contains normalized values. Never replace a current valid draft with invalid submitted values.

The tests now name the money interfaces `parse_budget(raw)`, `daily_allowance(budget, days)`, and `format_money(amount)` in `money.py`. Invalid budget parsing raises `ValueError` with a useful message. Formatting returns a two-decimal numeric string; templates add the EUR label or symbol.

### 4.3 Budget rules

- Accept stripped plain decimal input with at most two decimal places and enforce EUR 0.01–1,000,000.00.
- Reject separators, currency symbols, scientific notation, extra decimal places, non-finite values, and out-of-range amounts before generating a result.
- Construct monetary decimals from strings. For the existing JSON numbers, use their string representation rather than passing a binary float directly into `Decimal`.
- Calculate the daily display with `ROUND_HALF_UP`; display all EUR amounts to two decimal places.
- Filter eligibility with `cost × days <= budget`. Do not filter against a rounded daily display.
- Build the live browser preview from validated integer cents. Keep its parsing limits and rounding consistent with the server. Show a placeholder for incomplete or invalid inputs, and make the server authoritative.

### 4.4 Recommendation result

The recommendation function accepts validated preferences and a supplied catalog or the loaded catalog. It returns an ordered list of results plus any unmet-preference notices.

Each result contains the catalog item, exact estimated cost, score, distinct matched interests, earned preference bonuses, and a plain-language explanation. Build new result data rather than changing catalog records in place.

The executable test contract is `recommend_trip_ideas(preferences, catalog=None) -> (items, notices)`. Each item has `place`, `estimated_cost`, `score`, `matched_interests`, `preference_matches`, and `reason` keys. Preference matches use the actual tag names; notices are readable strings. These names define the interface without implementing the algorithm.

Apply the approved rules in this order:

1. Keep only the selected destination's items.
2. Require at least one selected-interest match.
3. Apply exact per-item affordability.
4. Add 3 points per distinct matching interest, 1 for a matching selected pace, and 1 for an explicitly tagged family-friendly match when requested.
5. Sort by `(-score, cost, name.casefold(), id)`.
6. Return every qualifying item once, with reasons that describe only evidence present in its tags.

Unmet-preference notices depend on the eligible results. A family-friendly selection must not make an untagged restaurant appear verified as suitable. Empty results remain a valid outcome with a useful explanation and edit action.

### 4.5 Current draft and form protection

- Use Flask's signed, non-permanent browser-session cookie with one `trip_draft` entry.
- Validate the stored envelope, field types, ranges, destination, and available tags before using a draft for prefill, resume, or results.
- Missing drafts show the specified recovery message. Malformed or unsupported drafts are discarded with a useful message instead of causing an exception.
- Recompute recommendations from current catalog data each time results are requested.
- Keep the signing secret outside source code. Use `TRIPPLANNER_SECRET_KEY` when configured, a process-local random fallback for the local demo, and an explicit stable test secret in test fixtures. Document that drafts are not guaranteed across browser-session end or server restart.
- Keep cookies HTTP-only and use a same-site setting appropriate for the local flow.
- Generate a random session token for forms and compare submitted tokens using a constant-time comparison. Keep a valid token usable across tabs; do not invalidate another open form on every page view.
- Reject missing or invalid tokens before validating or replacing a draft. Return an understandable 400 error page with a link back to the form.
- Clearing removes only the current draft; it does not clear unrelated session data or another client's draft.

The draft tests name `serialize_draft(preferences)` and `load_draft(stored, catalog=None)`. The envelope is `{"version": 1, "preferences": ...}`. Loading returns normalized preferences or `None` for invalid/stale data, including explicitly empty catalogs.

## 5. Routes and response behavior

| Request | Expected behavior |
| --- | --- |
| `GET /` | Return 200 with current feature copy, Paris coverage, Start planning, and a resume link only when a valid draft exists. |
| `GET /plan` | Return 200 with a blank form or valid draft values, supported options, and a form token. |
| `POST /plan` with a valid token and valid preferences | Replace the draft, then return 303 to `/recommendations`. |
| `POST /plan` with a valid token and invalid preferences | Return 200 with associated errors and submitted answers. Preserve the previous valid draft. |
| `GET /recommendations` with a valid draft | Return 200 with a summary, recomputed ranked results or a useful no-match state, and edit/clear actions. |
| `GET /recommendations` without a valid draft | Redirect to `/plan` with a useful message; do not attempt scoring. |
| `POST /draft/clear` with a valid token | Clear the current draft, then return 303 to a blank `/plan` form with confirmation. |
| Either POST with an absent or invalid token | Return 400 with recovery and leave the draft unchanged. |
| `GET /draft/clear` | Return 405; viewing a link must not clear data. |

Use the POST–redirect–GET pattern for successful changes. The results URL is safe to refresh. Use ordinary links for navigation and actual forms/buttons for the two state-changing actions.

## 6. Pytest coverage defined before implementation

The following responsibilities are now covered by the revised suite. Passing the testing checkpoint means the tests are defined and their current failures understood; it does not mean the new application behavior already passes. Current per-file results are in the [testing checkpoint](docs/phase-03-testing.md).

| Test area | Verified coverage | Spec acceptance examples |
| --- | --- | --- |
| `tests/test_catalog.py` | Existing data integrity and destination lookup; destination-specific interests; supported pace options; no active choice for current Paris data. | 10 |
| `tests/test_preferences.py` | Valid normalization and duplicate interests; days 1/14 boundaries and invalid days; selected-destination validation; valid/omitted optional fields; canonical pace; raw-answer retention; invalid unknown choices. | 5, 6, 10 |
| `tests/test_money.py` — new | Accepted amount formats and boundary values; rejected formats/ranges; cent precision; half-up daily rounding; two-decimal formatting. | 1, 8 |
| `tests/test_recommendations.py` — new | Destination and interest eligibility; paid/free eligibility; exact affordability; scores and bonuses; every tie-break; deterministic order; unique items; truthful reasons; unmet preferences; empty result; no catalog mutation. | 1–4, 8, 10 |
| `tests/test_drafts.py` — new | Lossless serialization; strict field types and envelope version; malformed data; unsupported choices; valid data round-trip; normalization with current catalog. | 5, 6, 9, 11 |
| `tests/test_plan_form.py` | Actual form token; displayed options and budget meaning; successful 303/results flow; accessible invalid feedback; raw answers and checkboxes retained; edit prefill. | 1, 5, 6, 10, 12 |
| `tests/test_trip_flow.py` — new | Refresh; valid edit replacement; invalid edit preservation; resume; clear; separate-client isolation; missing/corrupt/unsupported draft recovery; results recomputed after a catalog change. | 3–7, 9, 11, 12 |
| `tests/test_csrf.py` — new | Both POST routes reject absent, invalid, and other-session tokens; rejected requests preserve the draft; valid tokens succeed; GET cannot clear a draft. | 9, 12 and spec section 7 |
| `tests/test_home.py` and result-page assertions | Working links; honest current journey; supported coverage; summaries; cost/free/estimate labels; source links; explanations; alternative-ideas notice; no-match recovery; semantic labels and error associations. | 1, 4, 10–13 |

Test user-visible behavior and stable domain results. Avoid tying tests to incidental CSS class names, a decorative phrase, or the exact layout of a template.

### 6.1 Fixtures and test setup

- An application factory fixture supplies `TESTING=True` and a fixed test signing secret.
- A client factory creates truly separate sessions for isolation and token checks.
- A token helper first requests a real form and extracts its hidden token; normal route tests do not globally disable CSRF.
- A raw valid-form fixture uses strings and repeated interests like an actual submitted form.
- A normalized-preferences fixture uses decimal money and canonical values.
- A tiny two-destination catalog proves destination scoping independently of the Paris-only sample.
- A ranking catalog forces equal scores, equal costs, case-insensitive name ties, and the final ID tie-break.
- An affordability fixture includes EUR 33.34: for EUR 100.01 over 3 days, the displayed daily allowance is EUR 33.34 but that item is excluded.
- Free, unmatched-interest, tagged, and untagged records cover useful results and empty cases.
- A limited real-catalog acceptance test verifies the documented Le Procope → Luxembourg Gardens → Seine Riverside Walk ordering for the sample inputs.
- Keep all automated checks offline and deterministic. Do not follow source links or depend on live travel information.

### 6.2 Migrate the old tests deliberately

- Keep useful catalog, input-validation, and semantic-page tests.
- Replace the old successful `POST /plan` expectation of a 200 confirmation banner with a 303 redirect, stored draft, and useful result assertions.
- Add valid tokens to existing integration submissions so they reach the behavior under test.
- Assert decimal values and canonical cent strings instead of treating floats as the money contract.
- Change active-pace assumptions to derive availability from destination data.
- Replace home copy tests that require an available itinerary with checks for the current choose/find/refine journey.
- Preserve invalid-input coverage while adding new decimal formats, exact bounds, and destination-specific tag checks.
- Treat historical test counts as history. Record a fresh baseline before changing tests, then report actual discovery and results for the revised suite.

## 7. Testing gate — completed before coding

1. Run the existing pytest suite to record its present state. Investigate any pre-existing failure separately from the new feature.
2. Write or revise the fixtures and tests described above without adding feature implementation.
3. Run `python -m pytest --collect-only -q`. All intended tests must be discoverable. Keep imports of intentionally missing feature modules inside the relevant tests so missing features do not prevent discovery of the rest of the suite.
4. Run the affected tests and inspect the failures. Missing functions/routes, old response behavior, unsupported rules, or absent result content may be expected. A syntax mistake, invalid fixture, accidental network call, or environment problem is not proof of missing functionality.
5. Check that each requirement has an assertion capable of catching the relevant defect. In particular, use the EUR 100.01 rounding case rather than one where exact and rounded filtering give the same outcome.
6. Record the expected red results and their connection to the specification. Only then begin implementing the application changes.

Some retained tests will already pass. The requirement is to demonstrate the missing behavior with meaningful failing tests, not to make every test fail.

## 8. Implementation slices — completed after the testing gate

### Slice A — Trustworthy input and money

Add the money helpers and destination-scoped options, then update preference validation. Keep raw erroneous input separate from normalized values. Run the relevant catalog, money, and validation tests.

**Learning focus:** Strings versus numbers, validation, canonical values, `Decimal`, and why monetary display rounding must not change eligibility.

**Practice:** Predict which of `300.50`, `3e2`, and `300.001` the validator accepts, then explain the EUR 100.01 / 3 boundary.

### Slice B — Explainable trip ideas

Implement eligibility, score calculation, stable sorting, reasons, and unmet-preference notices as ordinary Python functions. Run the recommendation tests and manually calculate the sample ranking from tags.

**Learning focus:** Sets for matching interests, conditions, dictionaries, sorting, pure functions, and rule-based AI.

**Practice:** Calculate why Le Procope scores 6 while Luxembourg Gardens scores 5 for the sample preferences.

### Slice C — Valid drafts and protected actions

Add draft serialization/validation, session configuration, and form-token helpers. Check round-trips, malformed data, client isolation, and token behavior before connecting successful submissions to the result flow.

**Learning focus:** Stateless requests, cookies and sessions, serialization, type checking, and why changes use POST with a form token.

**Practice:** Explain why a current draft differs from a permanently saved trip and why another browser session should not inherit it.

### Slice D — Complete server-rendered flow

Connect the planned routes, shared layout, preferences page, and recommendation page. Add the resume, edit, and clear actions; replace obsolete home claims. Run route, session, security, and page-content checks. All core actions must work before the optional browser enhancement is added.

**Learning focus:** Flask request/response handling, templates, conditional rendering, and POST–redirect–GET.

**Practice:** Trace one food-interest selection through validation, scoring, a result card, and the prefilled edit form.

### Slice E — Live preview, visual checks, and handoff

Add the daily preview script and responsive styling. Supply useful placeholders and a no-JavaScript explanation. Check the core flow at both viewport sizes, update the README, run the full pytest suite, and demonstrate the acceptance examples.

**Learning focus:** Browser events, progressive enhancement, accessible forms, regression checks, and explaining what the tests do and do not prove.

**Practice:** Disable JavaScript, submit the same trip, and explain which convenience disappears and why the recommendations still work.

## 9. Browser and accessibility verification

Pytest establishes server behavior and domain rules; it cannot establish actual layout or live browser interaction by inspecting HTML strings alone. After implementation, verify:

- At 360px and 1280px widths, forms and result cards remain readable without horizontal page scrolling.
- Tab, Shift+Tab, Space, and Enter support the full submit, review, edit, and clear journey with visible focus.
- Every input has an associated label; errors identify the field and remain understandable without color.
- Valid preview inputs update the daily amount; incomplete, malformed, and out-of-range values show the placeholder. Check rounding and both bounds.
- With JavaScript disabled, submission, results, edit, resume, and clearing still work; the server provides the daily estimate.
- The main flow works offline using local assets and system font fallbacks. Source links may remain outbound references but are not needed to obtain a result.
- Every planning control performs its label's action. Example content is visibly an example, and no enabled control promises an unimplemented itinerary or permanent saving.

If a browser check finds a logic defect, add an appropriate regression test before fixing it. Use manual/browser checks for visual issues that pytest cannot meaningfully verify.

## 10. Completion and handoff

The revised Phase 1 is complete only when:

- The approved submit → recommendations → edit flow works, including empty results and invalid edits.
- All required pytest tests pass, and the actual results are recorded.
- Session isolation, refresh, recovery, and form protection work as specified.
- The browser checks pass at both viewport sizes and with JavaScript disabled.
- Budget wording, estimates, alternative-item costs, and recommendation reasons are accurate.
- The README provides verified setup/run/test instructions and a plain-language explanation of scoring and draft lifetime.
- The student receives a short demonstration and the practice tasks from the approved spec.

Choose the next product increment only after this one is working and understood. Do not mark the restart complete merely because its specification or plan is finished.

# Phase 8 — Server Form and Draft Test Checkpoint

**Status:** Historical server-form test checkpoint, recorded before implementation. The form/draft/context and subsequent full web flow are now implemented, with **1,477 passing cases**. See the [three-phase implementation guide](phase-08-three-phases.md). The observations and red results below preserve the earlier test-first stage. Photo/native work remains.

**Scope:** [Approved Phase 8 specification](../specs/phase-08-expanded-release.md) and the new form/draft contracts in the [implementation/test plan](../plans/phase-08-expanded-release-plan.md). This checkpoint does not complete the actual planner-JavaScript, full save/detail/Maps HTTP, photo, native, or old-test-migration gates.

## What we are preparing

The form needs to choose the correct currency for each destination, preserve answers after errors, and save a draft that includes its currency. It also needs an explicit review when an entered amount changes currency.

For example, a traveler editing a Paris trip might select Tokyo. EUR 300 cannot silently become JPY 300. The future form will show the new unit, keep the entered details, and ask the traveler to review the amount in JPY. This is not currency conversion.

The form will include a signed note describing the currency it displayed and whether a review is pending. Signing makes alterations detectable; browser-session binding prevents mixing another browser's context into the form. This note remains separate from CSRF protection and from the trip's content/fingerprint. The plan uses [ItsDangerous URL-safe serialization](https://itsdangerous.palletsprojects.com/en/stable/url_safe/), already available with Flask, with no new dependency installation.

## Intended server behavior

| Situation | Required behavior |
| --- | --- |
| New form, no city selected | Neutral currency context; choose a destination to establish the unit. Do not imply an EUR amount. |
| First city submission | Validate in that city's currency and store v2 normalized draft data. Ignore a submitted currency label. |
| Edit an amount without changing currency | Ordinary validation; no currency-change acknowledgement needed. |
| Change an EUR form to JPY | Redisplay raw answers with a signed pending JPY review; preserve the last valid draft. |
| Submit pending JPY review without checking its acknowledgement | Show an associated error and keep the last valid draft. |
| Check the acknowledgement under the matching pending context | Accept the explicit native amount if all other fields are valid. |
| Change a pending JPY review to GBP | Create a fresh GBP review; an old checked JPY box cannot complete it. |
| Missing/altered/wrong-browser currency context | HTTP 400 with useful recovery; preserve the draft and avoid travel-data/storage access. |

The ordinary HTML POST workflow supports the no-JavaScript path. It does not need an additional confirmation API. Future JavaScript must enhance this workflow and will get actual execution tests before its code changes.

## Observed results

The fresh pre-edit baseline contained **1,270 cases: 1,206 passed and 64 expected unfinished-feature failures**, no errors/skips, in 16.76 seconds.

Final discovery found **1,451 cases**. The full run produced **1,209 passed, 242 inspected expected failures, 0 errors, and 0 skipped in 17.96 seconds**. Exit status 1 is expected while the newly specified behavior and previously unfinished requirements remain unimplemented.

| Area | Cases | Passed | Expected failures |
| --- | ---: | ---: | ---: |
| Retained suite, including completed helpers and older unfinished requirements | 1,270 | 1,206 | 64 |
| [Currency-aware preference tests](../tests/test_multicurrency_preferences.py) | 64 | 1 | 63 |
| [Versioned draft tests](../tests/test_multicurrency_drafts.py) | 44 | 0 | 44 |
| [Signed currency-context tests](../tests/test_currency_context.py) | 41 | 0 | 41 |
| [Real server-form flow tests](../tests/test_multicurrency_form_flow.py) | 32 | 2 | 30 |
| **Total** | **1,451** | **1,209** | **242** |

The new files add **181 parameterized cases**, not 181 product features. Their three passing checks establish independent fixtures/helpers. All **1,206 previously passing cases** are still present and passing, including all **943 original Phase 7 cases**. No prior assertions were removed or weakened, and no skip/`xfail` markers hide missing behavior.

## Every failure group was inspected

| Missing behavior | Failures |
| --- | ---: |
| Preferences do not yet accept the supplied profile seam or produce the new currency-aware contract. | 63 |
| Draft loading does not yet accept supplied profiles/version-2 native currency data. | 38 |
| New currency-bearing preferences still serialize as v1 without the currency field/native precision. | 6 |
| The signed `currency_context` module is absent. | 41 |
| The actual form has no separate hidden currency-context field yet. | 26 |
| Missing/forged context is currently ignored under otherwise valid existing form submissions. | 3 |
| Context is not checked before catalog access. | 1 |
| Previously unfinished real-place release checks. | 6 |
| Previously unfinished v2 snapshot/storage checks. | 58 |
| **Total** | **242** |

There were no collection, fixture, environment, or unrelated application errors. Missing-API/control assertions run inside test bodies. Assertions after those missing features remain requirements to execute during implementation; the red run does not prove their downstream behavior already works.

## What the tests cover

### Currency-aware preferences

All six cities are checked for canonical destination/currency and native budget precision/bounds. A posted currency label cannot override the profile. A destination needs both a profile and available catalog records; an unsupported city does not get a guessed currency. Interests and pace come from the selected city's records. Errors preserve raw answers, and validation cannot mutate supplied data.

### Draft compatibility

Independent v2 draft examples must serialize/load with exact native money and owned copies. Wrong currency, precision, types, versions, required fields, destinations, or stale choices are recoverable. Negative load tests first require a valid draft to load, so rejecting all v2 data cannot falsely pass them.

A genuine frozen v1 Paris draft loads explicitly as EUR into current normalized preferences without rewriting its original object. Arbitrary foreign/unknown v1 destinations do not acquire guessed currencies. Historical saved snapshots remain a separate unchanged compatibility contract.

### Signed currency context

Tests define `issue_currency_context` and `read_currency_context`, using the app secret, a dedicated signing purpose, and a separate browser-session nonce. They cover known/neutral/pending states, exact types, malformed/signed-bad payloads, signature tampering, wrong purposes, cross-browser/secret boundaries, and multiple open tabs. Issuing/reading contexts must preserve draft and CSRF data.

The signed note is not encryption, an exchange rate, or proof of human intent. Its purpose is to preserve the form's displayed-unit/review state and reject invalid substitutions.

### Real Flask forms

The tests use the actual app factory, request/session handling, rendered HTML, and `/plan` and `/recommendations` routes with isolated QA data. They check initial neutral labels, six-city submissions and v2 session content, code/amount/bounds on edit/results, currency-change review, associated acknowledgement errors, raw-answer recovery, same-currency edits, legacy Paris reads, and separate CSRF/context checks.

These are ordinary HTTP journeys: no script or browser automation submits answers. The actual planner JavaScript still needs its own execution tests. Full itinerary/save/list/detail/Maps HTTP flows are not claimed by this batch.

## Independent helpers and isolation

[phase8_form_helpers.py](../tests/phase8_form_helpers.py) supplies raw forms, independent draft examples, signed-field extraction, and an exact visible-amount checker. It does not call a future validator or serializer to generate expected data. Helper checks prove JSON/native-money shape, frozen v1 copies, rejection of missing/duplicate-purpose fields, and rejection of decimal text as a whole-yen amount.

The server fixture uses synthetic QA place names and `example.com` references from the earlier test-only catalog. It establishes behavior, not actual foreign locations, prices, or suitability. It must not become the released dataset.

All **56 pre-edit fingerprinted application/asset/data/test/dependency files** retain their SHA-256 values. New files are the four test modules, their helper, and this report; specification/plan/report status text was updated. No production Python, template, CSS, JavaScript, travel data, dependency, real saved-trip database, browser preference, active form, or native artifact was changed.

Runs used fresh validated project-local temporary directories and per-test databases. Ignored evidence:

- `.tmp/phase8-form-baseline.xml`
- `.tmp/phase8-form-health.xml` — three independent helper/fixture checks pass.
- `.tmp/phase8-form-red.xml`
- `.tmp/phase8-form-source-baseline.json`

## Remaining gates and next action

1. Implement only the directly tested profile-aware preference/draft and signed-context helpers first. Preserve existing live/default contracts until their integration is tested and migrated.
2. Before changing default normalized shapes, v1 serialization expectations, or mandatory form tokens, prepare legitimate old-test migrations. Separate historical v1 fixtures from new v2 creation assertions; update normal POST helpers to submit real currency-context fields. Preserve exact-money, recovery, CSRF, duplicate, transaction, historical-read, and appearance checks.
3. Define/validate actual planner-JavaScript execution tests for dynamic city choices, native preview precision, and pending amount-change feedback before client code changes. The browser page-data/harness contract remains undecided by this batch.
4. Define the remaining full itinerary/save/list/detail/Maps HTTP checks before integrating those flows. Reviewed release-place data and real-spot Maps verification remain required.
5. Define photo/native tests and perform actual browser/installed-artifact checks before claiming either polish or Windows/Android downloads complete.

## Worked example for learning

Suppose the saved draft is Paris with EUR 300. You switch to Tokyo and enter `450`. The first changed-unit submission should keep the Paris draft and show a JPY review. Checking “Use this amount in JPY” under that review then accepts **JPY 450**, if the other answers are valid. The software did not calculate an equivalent value for EUR 300.

An invalid day count should keep your entered `450`, selected Tokyo, interests, and previous valid Paris draft. That is the difference between raw form answers and an accepted draft.

The programming concepts here are validation, versioned data, session state, signed context, and integration tests. The existing recommendation scores and greedy scheduling remain the AI-related behavior. The practice examples are optional; continuing does not depend on answering a quiz.

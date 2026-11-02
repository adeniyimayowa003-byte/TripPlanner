# SDD Step 3 — Test Definition and Validation

**Scope:** [Approved revised Phase 1 specification](../specs/phase-01-restart.md)

**Status:** Testing checkpoint complete. Application implementation is the next step.

This checkpoint defines what the restarted application must do. The tests run against the earlier application, so failures are expected. No feature stubs were added, and failing tests were not hidden with skip or expected-failure markers.

## Observed results

- Before changing tests: **35 passed** in the existing suite.
- After defining and reviewing the revised tests: **244 collected**, with no collection errors.
- Execution: **45 passed, 199 failed, 0 errors, 0 skipped**.
- Existing Python application files, templates, CSS, catalog data, and dependencies retain their original SHA-256 hashes. Only tests and supporting documentation changed.

The 244 cases include parameterized variations, such as different invalid amounts or malformed drafts. They are not 244 separate features.

| Area | Cases | Passed | Expected failures |
| --- | ---: | ---: | ---: |
| Catalog lookup and supported options | 13 | 8 | 5 |
| Money parsing, precision, and formatting | 39 | 0 | 39 |
| Preference validation | 42 | 30 | 12 |
| Recommendation rules | 17 | 0 | 17 |
| Draft serialization and validation | 77 | 0 | 77 |
| Home navigation and current coverage | 8 | 5 | 3 |
| Preferences form integration | 14 | 2 | 12 |
| Results, edit, refresh, and recovery | 22 | 0 | 22 |
| Form-token protection | 12 | 0 | 12 |
| **Total** | **244** | **45** | **199** |

## Why the failures are expected

- `money.py`, `recommendations.py`, and `drafts.py` do not exist yet. Their local imports fail inside individual tests, while the full suite still collects successfully.
- Catalog helpers lack destination-specific option arguments and pace lookup.
- Preference validation still uses floats, accepts formats/ranges now excluded by the spec, and does not normalize a supplied pace consistently.
- `/recommendations` and `/draft/clear` do not exist, so their requests currently return 404.
- The earlier `/plan` implementation has no form token, current-draft storage, or successful POST redirect to recommendations.
- The home page does not display actual destination coverage or a resume action, and its sample illustration lacks a visible example label.
- The daily preview enhancement and its no-JavaScript explanation have not been added.

All failure messages were inspected. They identify absent interfaces, routes, or behavior; there were no fixture/setup errors or syntax problems. Missing feature imports are recorded as ordinary test failures rather than collection errors.

Several integration checks currently stop at the missing form token. Once form protection is implemented, their later assertions will exercise redirects, preservation, and editing. Likewise, domain assertions will run beyond their imports after the missing modules exist. This checkpoint establishes executable expectations; implementation must still pass them.

## Test contracts and fixtures

The [active plan](../PLAN.md) records the interfaces now used by the tests. Core test files are:

- [conftest.py](../tests/conftest.py): isolated Flask clients, a fixed test-only secret, form token extraction, raw/normalized preferences, draft data, small catalogs, and a standard-library HTML parser.
- [test_money.py](../tests/test_money.py) and [test_preferences.py](../tests/test_preferences.py): raw answers, canonical values, and exact money rules.
- [test_recommendations.py](../tests/test_recommendations.py): eligibility, scores, all tie-breaks, reasons, preference notices, and deterministic output.
- [test_drafts.py](../tests/test_drafts.py): JSON-safe round-trips and recovery from malformed or stale data.
- [test_plan_form.py](../tests/test_plan_form.py), [test_trip_flow.py](../tests/test_trip_flow.py), and [test_csrf.py](../tests/test_csrf.py): the HTTP flow, actual form tokens, draft isolation, and recovery.
- Existing catalog and home tests are retained or revised to match the approved outcome.

Tests supply small, known catalogs rather than modifying real travel data. The catalog-change integration check uses a temporary JSON file. No test starts a server, contacts the internet, calls an AI service, or follows source links.

The HTML checks parse elements and attributes, so they do not depend on attribute ordering or decorative CSS classes. Interest labels may wrap their checkbox or use a matching `for`/`id` pair. Numeric bounds are compared by value.

## A key example to explain in class

For a total allowance of EUR 100.01 over 3 days, the displayed daily allowance rounds to EUR 33.34. An idea costing EUR 33.34 must still be excluded because `33.34 × 3 = 100.02`, which exceeds EUR 100.01.

The recommendation test uses this boundary to catch filtering against the rounded display. Another check uses EUR 19.99 over 3 days with a EUR 59.97 allowance to confirm that the exact equality boundary is included.

## How to reproduce this checkpoint

From the project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest -q --tb=no -rN
```

The first command should discover the suite successfully. At this pre-implementation checkpoint, the second command exits with status 1 because the required new behavior is absent. Use `--tb=short` instead of `--tb=no` to read failure details, or run a single test file to study one area.

The machine-readable result from validation is in the ignored temporary file `.tmp/phase-3-red.xml`; it can be regenerated using pytest's `--junitxml` option. The summary in this document is the retained checkpoint record.

## Browser checks remaining for implementation

Pytest's Flask client sends HTTP requests without executing JavaScript. The server-form tests establish that the core flow does not depend on running a script, but they do not establish visual accessibility or browser interaction.

During implementation, still check:

- 360px and 1280px layouts without horizontal scrolling.
- Full keyboard navigation, visible focus, and usable error feedback.
- Live daily-preview updates, invalid-input placeholders, and half-up rounding.
- Submission, results, editing, resuming, and clearing with JavaScript disabled.
- An offline flow using local assets and readable system-font fallbacks.
- Visible example labels, honest combined-cost notices, and useful empty states.

Do not report these browser checks as passed until they have actually been performed.

## Student practice and the next step

1. Find the exact-affordability test and explain why EUR 33.34 is excluded in the EUR 100.01 example.
2. Compare a unit test in `test_money.py` with an integration test in `test_trip_flow.py`: which one needs Flask, and why?
3. Read the `valid_form` and `normalized_preferences` fixtures. Explain why the budget changes from text to a decimal value.
4. Run one file and distinguish an absent-feature failure from a test setup problem.

SDD step 4 is implementation: add the approved behavior in the planned slices and turn these expected failures into passing tests. No application feature has been implemented as part of this testing step.

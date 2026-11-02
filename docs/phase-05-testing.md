# Phase 5 — Test Definition and Validation

**Scope:** [Approved daily itinerary specification](../specs/phase-05-itinerary.md) and [implementation/test plan](../plans/phase-05-itinerary-plan.md).

**Status:** Historical SDD step 3 checkpoint, completed before itinerary implementation. The results below describe that red checkpoint, not the current application. Implementation is now complete with all 322 tests passing; see the [verification report](phase-05-implementation.md).

## Why tests come first

This stage turns the approved behavior into executable expectations before adding the itinerary engine or page. A unit test will ask whether ideas are assigned to the correct days and costs stay within the allowance. An integration test will ask whether a traveler can reach the page and use the existing edit/clear journey safely.

The new feature is intentionally absent while these tests are defined. Expected failures identify missing itinerary functionality; they do not mean the already-working recommendation feature has broken.

## Starting point

Before the new tests were added, all **244 existing pytest cases passed** on a fresh run. The Windows default temporary-folder restriction was avoided with a new isolated directory inside the project's ignored `.tmp` folder.

Application source, templates, static assets, catalog data, and dependencies were fingerprinted before this testing stage so accidental feature changes can be detected separately from test edits.

## Observed results

- **322 cases collected**, with no collection errors.
- **245 passed, 77 expected failures, 0 errors, 0 skipped** in the full suite.
- The 244 retained cases all still pass. The new files add **78 cases**, including one already-passing regression check that GET cannot clear a draft.
- SHA-256 comparisons confirm that all **16 application/data/asset/dependency files** are unchanged. No itinerary module, route, template, stub, or dependency was added. Existing tests and shared fixtures were not weakened or rewritten.

| Area | Cases | Passed | Expected failures |
| --- | ---: | ---: | ---: |
| Retained recommendation/form/security suite | 244 | 244 | 0 |
| [Scheduling unit tests](../tests/test_itinerary.py) | 37 | 0 | 37 |
| [Itinerary integration tests](../tests/test_itinerary_flow.py) | 41 | 1 | 40 |
| **Total** | **322** | **245** | **77** |

Parameterized cases exercise input variations; these counts are not numbers of separate features.

### Why these failures are expected

All failure messages were inspected from the full-run JUnit report:

| Missing behavior | Failures |
| --- | ---: |
| `itinerary.generate_itinerary` does not exist; local test-body imports report `ModuleNotFoundError` without interrupting collection. | 37 |
| `GET /itinerary` is absent: returns 404 where the new page must return 200. | 24 |
| The itinerary route cannot yet recover missing/invalid drafts: returns 404 instead of redirecting to the planner. | 12 |
| Recommendations lack the **Build my daily itinerary** link, including the no-match journey. | 3 |
| The new GET-only route is absent, so POST currently returns 404 rather than the required 405. | 1 |

There were no syntax, fixture-setup, temporary-folder, or unexpected application failures. Failures are not hidden with `skip`, `xfail`, or import-suppression markers. Adversarial fixture ranking/eligibility assertions run successfully before the missing generator import, confirming that the cost and scheduling examples are set up meaningfully.

The machine-readable full-run evidence is the ignored local file `.tmp/phase5-testing-red.xml`. It is temporary run evidence; this document preserves the durable checkpoint summary.

### Test review and helper checks

The tests were reviewed against the approved specification and plan before this checkpoint was marked complete. Review corrected a helper that could select a slot heading's wrapper instead of its full contents, and removed a weak assertion that could accept a false permanent-saving claim. Synthetic HTML checks pass for multiple valid layouts, including headings, plain labels, nested headers, and accessible slot labels. These are tests of the parser helper, not an implementation of the itinerary page.

The integration suite also checks the EUR 100.01 / 3 display boundary: EUR 33.34 is only an approximation. Under the real current catalog, that input should produce an EUR 85.00 scheduled estimate and EUR 15.01 unallocated allowance, without Le Procope. Domain fixtures separately exercise exact combined-cost rejection.

## What the new tests cover

| Approved behavior | Test focus |
| --- | --- |
| Requested days and pace | Exact day count, two or three slots, and honest empty slots. |
| Stable allocation | Morning across days before Afternoon/Evening; recommendation order retained within categories. |
| Appropriate categories | Restaurants in Evening only; a fitting restaurant takes priority; an activity fallback keeps its real category. |
| No repeated ideas | Each stable ID appears at most once, with no invented or unrelated places. |
| Combined affordability | Exact running daily totals, trip totals, unallocated allowance, and no transfer between days. |
| Skip rather than discard | An idea that does not fit one day can still fit a later day. |
| Truthful explanations | Matching reasons come from actual tags; unused tagged alternatives cannot confirm a scheduled preference. |
| Current catalog examples | The relaxed sample costs EUR 103.00; the no-pace sample costs EUR 135.00; low allowance produces useful gaps. |
| Web journey and recovery | Build/back/edit/refresh, no matches, missing or stale drafts, and catalog recomputation. |
| Privacy and protected changes | Separate sessions, unchanged draft on page views, no stored itinerary payload, and CSRF-protected clearing. |

Small catalog fixtures exercise these rules independently of the real Paris example. Tests do not need an internet connection, API key, server process, live price, or source-link visit.

## A boundary case to explain in class

For EUR 100.01 over 3 days, the displayed daily allowance is approximately EUR 33.34. An idea costing EUR 20.00 and another costing EUR 13.34 are each eligible individually, but they cannot share a day: `33.34 × 3 = 100.02` exceeds the total allowance.

The test deliberately fills the first Morning with the EUR 20.00 idea before trying the EUR 13.34 candidate. Otherwise the two ideas could fall on separate days and the test would fail to check combined affordability. A EUR 13.33 variant checks the allowed side of the same boundary.

## What this checkpoint does not prove yet

Successful collection means pytest can discover the tests. An expected missing-feature failure demonstrates an unmet requirement, not a working implementation. Assertions after a missing import or route must still run and pass during implementation.

HTML integration checks establish server-rendered content, links, and form behavior. They do not establish real mobile layout, visible keyboard focus, or browser operation with scripts disabled. Those browser checks remain required after implementation.

## Safe reproduction

From the project directory, collect tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
```

For execution, use a fresh temporary base directory under the project; pytest may clear an existing base directory, so never point it at a workspace root or an existing evidence folder:

```powershell
$phase5Project = (Resolve-Path -LiteralPath '.').Path
$phase5Base = [System.IO.Path]::GetFullPath((Join-Path $phase5Project ('.tmp\phase5-check-' + [guid]::NewGuid().ToString('N'))))
if (-not $phase5Base.StartsWith(($phase5Project + '\.tmp\'), [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected test directory.' }
if (Test-Path -LiteralPath $phase5Base) { throw 'Choose a fresh test directory.' }
.\.venv\Scripts\python.exe -m pytest -q --tb=short -rN --basetemp $phase5Base
```

At the recorded red checkpoint, execution exited with status 1 for the 77 missing-feature failures, not a collection or setup problem. Collection succeeded. Running these commands against the current implemented checkout now passes all 322 cases; the approved tests were not removed or weakened.

## Student practice

1. Open one scheduling test and identify its input, action, and expected result.
2. Explain why the EUR 13.34 candidate can be rejected for one day without being removed from the whole trip.
3. Explain the difference between a missing-feature failure, a broken test fixture, and a regression in existing behavior.

The test-definition and expected-failure validation gate was satisfied before coding began. The [implementation report](phase-05-implementation.md) now records the passing assertions and separate browser verification.

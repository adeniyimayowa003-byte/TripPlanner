# TripPlanner — Phase 7 Test Definition and Validation

**Scope:** [Approved appearance specification](../specs/phase-07-appearance.md) and [implementation/test plan](../plans/phase-07-appearance-plan.md).

**Status:** Historical SDD step 3 checkpoint, recorded before production implementation. Phase 7 is now implemented with **943 passing cases**; see the [verification report](phase-07-implementation.md) for browser evidence, a test-first animation regression, and verification limits, and the [learning guide](phase-07-learning.md). The red results below preserve the pre-implementation state, not the current application result.

## What this means in plain language

We have written a checklist the appearance feature must pass before we call it finished. It covers a working selector, remembered choices, readable colors, and keeping your trip intact.

The new feature checks currently fail because the selector, appearance script, and semantic palettes have not been built. This is the **red** stage of test-first development. We checked that these are meaningful failures, not broken test setup. The already-working planner and saved trips still pass all their tests.

## Starting point and observed results

Before test edits, all **676 existing cases passed** in 21.97 seconds. Production files and retained tests were fingerprinted before editing.

Final discovery found **942 cases** in 0.23 seconds. The full run produced **766 passed, 176 expected missing-feature failures, 0 errors, and 0 skipped** in 28.41 seconds. Exit status 1 is expected at this checkpoint. There are no skip or `xfail` markers hiding missing behavior.

| Area | Cases | Passed | Expected failures |
| --- | ---: | ---: | ---: |
| Retained Phase 6 suite | 676 | 676 | 0 |
| [Appearance HTTP integration tests](../tests/test_appearance_flow.py) | 42 | 21 | 21 |
| [Actual-script unit tests and harness checks](../tests/test_appearance_script.py) | 72 | 8 | 64 |
| [Styles, contrast, and CSS-reader checks](../tests/test_appearance_styles.py) | 152 | 61 | 91 |
| **Total** | **942** | **766** | **176** |

The new files add **266 parameterized cases**, not 266 separate features. Their 90 passing checks establish independent test-helper behavior and existing contracts that appearance must preserve. They do not prove that an interactive theme already works.

Ignored machine-readable evidence is in `.tmp/phase7-testing-red.xml`; the before-edit fingerprints are in `.tmp/phase7-testing-source-baseline.json`. This report preserves the durable summary.

### All failure groups were inspected

| Missing behavior | Failures |
| --- | ---: |
| The actual future `static/js/appearance.js` asset is absent. Checks fail inside tests, not during collection. | 64 |
| Shared ordinary, saved, validation, and recovery pages have no Appearance selector yet. | 19 |
| The shared head does not load the early local appearance script. | 1 |
| Requesting the absent script returns 404 rather than JavaScript. | 1 |
| The stylesheet lacks complete semantic palettes in Light, manual Dark, and automatic Dark contexts. | 3 |
| Manual/automatic Dark declarations and native color schemes are absent or cannot be compared yet. | 4 |
| A deliberately darker page palette is not defined. | 1 |
| Semantic ordinary-text and essential-boundary color pairs are not defined yet. | 52 |
| Representative components still use existing literals/old variables instead of the agreed semantic roles. | 30 |
| The explicit hidden-control display guard is absent. | 1 |
| **Total** | **176** |

There were no collection, fixture, runtime-setup, temporary-directory, or unrelated application failures. Assertions after a missing asset/control/palette remain requirements to execute during implementation; this red run does not validate their downstream behavior.

## What the checks cover

### 1. JavaScript behavior

Pytest runs the **real future production script** through a small [test-only Node harness](../tests/appearance_harness.cjs). Each case gets fresh document/control/storage stand-ins. The harness observes behavior; it does not choose themes on the script's behalf.

The checks cover recognized/missing/invalid stored values, early application before the header exists, DOM-ready binding, immediate explicit choices, exact stored enum values, and no writes merely on visiting a page. They also cover failures of the storage getter, reads, and writes, honest page-only feedback, and clearing a stale warning after a later successful write.

Other checks protect unfinished trip/name fields, unrelated storage keys, focus, scrolling, navigation, forms, and external requests. The selector must remain unavailable until its handler is attached. Missing optional header nodes must not crash ordinary page execution. Invalid stored text must not become attributes, HTML, or CSS classes.

Eight independent harness checks run small synthetic probe files. They establish actual file execution, early-versus-ready lifecycle, boolean-attribute reflection, detectable unrelated page/navigation changes, observable storage faults, and bounded callback execution. The probes are test fixtures, not production appearance stubs.

### 2. Shared pages and protected travel data

Flask's test client checks the real rendered HTML and local assets: one labeled native selector, three descriptive choices, initial hidden/disabled state, ordinary fallback help outside hidden ancestors, polite empty status, and an early script before the stylesheet.

Coverage includes home, planner, recommendations, current itinerary, saved collection/details, and application-rendered validation/recovery views. Saved views are exercised with live catalog/draft/generation access forbidden, including malformed drafts and unavailable storage.

Passing protection checks already show that extra appearance POST fields do not enter the authoritative draft or saved snapshot. Fingerprints, duplicate row reuse, schema version/columns, original preview behavior, and ordinary server form/save/list/view/clear journeys are unchanged. Query parameters and cookies do not make Flask own this browser preference.

These are server checks, not proof of clicking the eventual selector on an existing save form. That browser journey remains required.

### 3. Semantic colors and contrast

The CSS tests read actual stylesheet declarations. They require complete palettes, matching manual/automatic Dark values, positive device-dark queries excluding both manual modes, native control color schemes, representative component wiring, and explicit support for hidden controls.

Contrast arithmetic checks named foreground/background pairs at the approved 4.5:1 ordinary-text and 3:1 essential-boundary targets. Focus comparisons use the surrounding page/surface/control backgrounds; decorative separators do not receive an invented essential-boundary requirement.

The reader's independent checks cover comments, quotes, nested rules, aliases, malformed/cyclic/missing/nonopaque colors, known contrast endpoints, and adversarial selectors/media queries. Review specifically tightened descendant exclusions, inverted device queries, and `:not([hidden])` guards that could otherwise falsely pass. Existing reduced-motion, Light color-scheme, no-inversion, and no-whole-page-transition checks pass.

The reader deliberately supports simple palette declarations, opaque sRGB colors, and simple positive dark-device queries. It is **not a full CSS cascade or browser engine**. Actual computed colors, layout, keyboard behavior, device changes, storage/reload, first paint, and script-blocked fallback still need the planned browser audit after coding.

## Isolation and unchanged application

- All **25 fingerprinted production/data/asset/dependency files** and **15 retained test/fixture files** are unchanged. No previous assertion was weakened or migrated.
- Only the three new pytest files, their test-only JavaScript harness, and checkpoint documentation were added/updated. No production script, template, stylesheet, route, stub, dependency, or database migration was added.
- SQLite writes use per-test temporary databases. The real default `instance/tripplanner.sqlite3` remains absent.
- The production appearance script is still absent. The existing preview was not restarted, and real browser preferences/storage were not changed.

Node is a **development-test prerequisite**, not a production server dependency. Version v24.22.1 was verified on this machine, and the independent harness checks actually ran. Tests resolve `node` from PATH or an optional `TRIPPLANNER_NODE` executable path; no machine-specific runtime path is committed. A missing runtime is a setup problem to fix, not an expected feature failure or reason to skip tests.

## Safe reproduction

From the project directory, discover the suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
```

For a full run, choose a fresh project-local temporary base. Pytest may clear an existing base, so never use the project root, a real database folder, or earlier evidence:

```powershell
$phase7Project = (Resolve-Path -LiteralPath '.').Path
$phase7Base = [System.IO.Path]::GetFullPath((Join-Path $phase7Project ('.tmp\phase7-check-' + [guid]::NewGuid().ToString('N'))))
if (-not $phase7Base.StartsWith(($phase7Project + '\.tmp\'), [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected test directory.' }
if (Test-Path -LiteralPath $phase7Base) { throw 'Choose a fresh test directory.' }
.\.venv\Scripts\python.exe -m pytest -q --tb=short -rN --basetemp $phase7Base
```

At the historical checkpoint, these checks produced the recorded missing-feature failures. The commands above now run the implemented **943-case green suite** against current source; they do not recreate the earlier source state. Keep the existing virtual environment and make Node available for the script tests; no npm packages are needed.

## Learning task and next step

Pick one test in `test_appearance_script.py`. Explain its starting situation, the action taken, and the expected result. Then explain why a missing-script failure is useful now, but would be unacceptable when we deliver the feature.

At this historical checkpoint, implementation was next: semantic palettes and device fallback → safe appearance script → shared accessible control → regression tests and real-browser verification. That work is now complete; use the linked implementation report and student guide for the current result. There is no new timeline or extra approval gate.

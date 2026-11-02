# TripPlanner — Phase 6 Test Definition and Validation

**Scope:** [Approved saved-trips specification](../specs/phase-06-saved-trips.md) and [implementation/test plan](../plans/phase-06-saved-trips-plan.md).

**Status:** Historical SDD step 3 checkpoint, recorded before feature implementation. The red results below are history, not the current application result. Phase 6 is now implemented with all **676 cases passing**; see the [verification report](phase-06-implementation.md) for browser results, narrow test-path corrections, and additional review checks, and the [student guide](phase-06-learning.md) for explanations.

## What this means in plain language

We have written the checks that saved trips must eventually pass. They describe what should happen when someone saves, reopens, or accidentally resubmits a trip, and what should happen when storage fails.

Failing now is expected: the save form, storage modules, and saved pages do not exist yet. This is the **red** part of test-first development. It is not a claim that saving works, and it is not a broken-test allowance: discovery, fixtures, and the already-working application must still work.

## Starting point and observed results

Before test edits, all **322 existing cases passed** on a fresh run in 3.24 seconds. Application modules, templates, assets, catalog data, dependencies, and `.gitignore` were fingerprinted before edits.

Final discovery found **670 cases** with no collection errors. The full run produced **333 passed, 337 expected missing-feature failures, 0 errors, and 0 skipped** in 11.27 seconds. Exit status 1 is expected for this red checkpoint. There are no `xfail` or skip markers hiding missing behavior.

| Area | Cases | Passed | Expected failures |
| --- | ---: | ---: | ---: |
| Retained Phase 5 suite | 322 | 322 | 0 |
| [Snapshot unit tests](../tests/test_snapshots.py) | 192 | 1 | 191 |
| [SQLite repository tests](../tests/test_saved_trips.py) | 55 | 0 | 55 |
| [Saved-trip integration tests](../tests/test_saved_trip_flow.py) | 101 | 10 | 91 |
| **Total** | **670** | **333** | **337** |

The new files add **348 parameterized cases**, not 348 separate features. Their eleven passing checks establish the independent sample fixture, adversarial catalog changes, and existing planning behavior that must not require storage.

The ignored machine-readable full-run evidence is `.tmp/phase6-testing-red.xml`. This document preserves the durable summary.

### All failure groups were inspected

| Missing behavior | Failures |
| --- | ---: |
| The future `snapshots` module is absent; imports occur inside tests rather than breaking discovery. | 191 |
| The future `saved_trips` module is absent. | 55 |
| The itinerary does not yet provide its save form. | 65 |
| Saved-ID 404 pages do not yet provide friendly recovery navigation. | 7 |
| The save route cannot yet redirect missing/invalid drafts to the planner. | 5 |
| Existing headers do not yet provide Saved trips navigation. | 4 |
| The absent POST route returns 404 rather than rejecting invalid CSRF with 400. | 3 |
| Saved routes are absent instead of returning storage-unavailable 503 views. | 3 |
| Default/environment database configuration is not implemented. | 2 |
| The empty Saved trips collection route is absent. | 1 |
| GET save returns 404 rather than the required 405. | 1 |
| **Total** | **337** |

There were no syntax, missing-fixture, setup, temporary-directory, or unrelated application failures. Assertions beyond a missing module/form remain expectations to execute and pass during implementation; they are not already proven by this run.

## Coverage and important examples

### 1. Snapshot unit tests

A snapshot stores the complete reviewed result rather than just catalog IDs. Tests cover all seven eligible ideas, the six-slot EUR 103.00 sample, EUR 197.00 remaining, source links, matching evidence, unused alternatives, gaps, and original notices.

Tests check every monetary path, including nested place costs: two-decimal text in JSON and exact `Decimal` values after loading. They cover free suggestions, the EUR 100.01 boundary, partial/empty results, one/fourteen days, and saved pace choices.

Canonical JSON and SHA-256 checks distinguish object-key order from list order. Decoded and serialized money must yield the same hash. Changing saved content changes the fingerprint, while editable titles and generated save metadata stay outside the form's content fingerprint.

Invalid versions/types, missing fields, unsafe URLs, duplicate IDs, inconsistent scheduled copies, sums/counts, and an exact daily-cap violation must be rejected without regeneration. Money-corruption cases preserve the original numeric value where possible so unrelated sum failures cannot hide a permissive parser.

Title checks cover defaults, trimming, Unicode, the 80-character boundary, literal HTML/SQL-looking text, and control characters rejected before trimming.

### 2. Storage tests

Tests use actual temporary SQLite files and separate connections. They cover lazy creation, explicit schema versioning, TEXT money payloads, durable reads, newest-first sorting with the ID tie-break, independent returned copies, and parameterized values.

Duplicate protection must preserve the original row, ID, and timestamp. Concurrent saves start on separate threads before opening their transactions; one unique database row, not a disabled button, enforces equality. Different titles/content create separate rows without overwriting.

One damaged snapshot is isolated from valid records; a damaged duplicate cannot be reported as a successful save. Unsupported database schema and corrupt files must remain untouched, not silently reset.

Failure checks include a real exclusive lock, SQLite read-only URI mode, invalid parent paths, read failures, and an injected commit failure **after an actual insert**. Rollback is checked through a fresh independent connection. Tracking connections also verify closure. The fault proxy mirrors SQLite's rollback-on-failed-context-manager-commit behavior.

The optional `created_at` test seam supplies an aware UTC `datetime`; returned metadata is ISO UTC text. Fresh-import checks execute an isolated module namespace rather than globally reloading exception classes already used by Flask.

### 3. Page-flow tests

Tests parse the real server-rendered form and navigate save → detail → collection → reopen → planner. They check labels, separate CSRF/content tokens, retained names, associated errors, literal title display, original preferences/ideas/costs/notices, snapshot/UTC labels, shared-local disclosure, and read-only navigation.

Restart checks use a new Flask app with the same temporary database and a different secret. Separate browser clients must share saved trips but not their unsaved drafts. Clearing or viewing a draft must not delete or restore saved content.

Saved list/detail and their 404/409/503 pages are tested with live catalog and generation calls forbidden. They must preserve even a malformed current draft. Additional cases remove the destination or make the catalog file missing/unreadable.

Stale-form cases change the draft, price, description, source URL, or tags after review. An unrelated Kyoto entry must leave the reviewed snapshot unchanged. Independent passing checks establish that these examples actually have the intended effect before the new route exists. A catalog change that invalidates the draft uses ordinary planner recovery instead.

Rejected names/tokens/fingerprints/drafts and stale forms must not open storage. Submitted totals/JSON are untrusted. Save requests count all available catalog-loader aliases to ensure one consistent catalog read. Locked/unusable storage must preserve rows, drafts, and useful recovery without leaking SQL, paths, or tracebacks.

## Test isolation and intentional existing-test edits

- The shared app fixture now supplies a unique `tmp_path` database and short timeout. Restart tests explicitly reuse that test-local path. No test writes to the user's default collection.
- Snapshot fixtures use the already-working Phase 5 APIs, not either missing module. They serialize monetary fields explicitly rather than hiding arbitrary objects behind a generic encoder.
- One home-test name/expectation was clarified: allow the approved read-only Saved trips navigation, but still forbid a direct home-page save action or draftless itinerary action. All eight home cases still pass. No retained assertion was removed to accommodate missing functionality.
- All **19 fingerprinted production/data/asset/dependency files are unchanged**. No snapshot/storage implementation, route, template, style, stub, dependency, or `.gitignore` change was added.
- The real default `instance/tripplanner.sqlite3` does not exist and was not created by these checks. The running preview was not restarted or changed.

## Safe reproduction

From the project directory, collect tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
```

For a full run, use a fresh project-local temporary base. Pytest may clear an existing base, so never use the project root, a real database folder, or an earlier evidence folder:

```powershell
$phase6Project = (Resolve-Path -LiteralPath '.').Path
$phase6Base = [System.IO.Path]::GetFullPath((Join-Path $phase6Project ('.tmp\phase6-check-' + [guid]::NewGuid().ToString('N'))))
if (-not $phase6Base.StartsWith(($phase6Project + '\.tmp\'), [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected test directory.' }
if (Test-Path -LiteralPath $phase6Base) { throw 'Choose a fresh test directory.' }
.\.venv\Scripts\python.exe -m pytest -q --tb=short -rN --basetemp $phase6Base
```

At this checkpoint, expect the recorded missing-feature failures, not an all-green suite.

## What comes next

The test-definition gate is complete. Implementation can now follow the approved slices: snapshot handling → SQLite persistence → protected routes → saved pages and browser verification.

Pytest HTML checks cannot establish real mobile layout, keyboard focus, or actual script-blocked browser behavior. Those checks, the README update, and the beginner-friendly implementation guide remain required after coding. No browser verification or successful saved-trip persistence is claimed yet.

**Small student task:** Open one new test and point to its input, action, and expected result. Then explain why a missing-feature failure is different from a broken test fixture or a regression in an existing feature.

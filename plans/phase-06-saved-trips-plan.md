# TripPlanner — Phase 6 Implementation and Test Plan

**Approved scope:** [Save and reopen trips specification](../specs/phase-06-saved-trips.md), approved by the user before this plan was prepared.

**Current checkpoint:** SDD step 4 — implementation complete. All **676 pytest cases pass**; required browser checks passed. The [verification report](../docs/phase-06-implementation.md) records actual results and the [student guide](../docs/phase-06-learning.md) explains the feature. The [red checkpoint](../docs/phase-06-testing.md) preserves the 670-case test-first run as history, with later narrow corrections/additions documented in the implementation report.

**Verified baseline before implementation:** The existing 322 cases passed on a fresh run using a validated, unique project-local temporary directory. No application, test, dependency, or database changes were needed for planning. Implementation/testing/browser checks did not create or reset the user's real default collection.

## 1. Outcome and boundaries

The user can name and save a reviewed itinerary, browse Saved trips, and reopen an unchanged historical snapshot after restarting the app. Saving does not retrain an AI model: it stores the result of the existing explainable rules.

**Current itinerary → Save this itinerary → saved detail → Saved trips → reopen.**

Keep the current recommendation/scheduling rules and browser draft behavior. Saved data belongs to a shared local, single-user collection, not private accounts. Do not add delete, rename, overwrite, restore-to-draft, exports, authentication, extra destinations, live data, or new AI behavior.

## 2. SDD sequence

1. **Specification — approved:** Use the linked Phase 6 specification.
2. **Planning — complete:** This document defines contracts, coverage, and implementation order.
3. **Testing — complete:** Tests/fixtures are defined, collection succeeds, and expected missing-feature failures have been inspected; see the linked red checkpoint.
4. **Implementation — complete after the testing gate:** Modules/routes/pages, the full passing suite, actual browser verification, and the student guide are delivered.

During testing, change only tests, supporting fixtures, and checkpoint documentation. Do not add implementation stubs, database schema code, templates, or skip/xfail markers to get past missing functionality. Changes required by the approved feature are not new scope approvals; material behavior changes still require a revised specification.

## 3. Responsibilities and planned files

| Area | Responsibility |
| --- | --- |
| `snapshots.py` — new | Build a self-contained saved payload, serialize exact monetary values, validate/decode without the live catalog, normalize trip names, and compute content fingerprints. No Flask or database dependency. |
| `saved_trips.py` — new | SQLite schema, short-lived connections, transactions, atomic duplicate protection, ordered reads, and storage-error normalization. No Flask/session dependency. |
| `app.py` | Configure storage without opening it; protect and handle save POST; serve saved list/detail/recovery independently of the catalog and current draft. |
| `templates/itinerary.html` | Add the labeled optional name, hidden content fingerprint, CSRF token, save action, and associated feedback. Preserve the working daily-plan UI. |
| `templates/saved_trips.html` — new | Shared-local collection, snapshot summaries, newest-first cards, unavailable entries, and a truthful empty state. |
| `templates/saved_trip.html` — new | Read-only stored preferences, all ranked ideas, itinerary, estimates, notices, and navigation. |
| `templates/saved_error.html` — new | Friendly saved-route 404/409/503 views with recovery, without loading the live catalog or exposing exception details. |
| `templates/base.html` and stylesheet | Add Saved trips navigation and scoped responsive saved-page/form styles; retain visible focus and usable mobile navigation. |
| `.gitignore` | During implementation, ignore `instance/`, including SQLite files and journals. Do not delete existing files. |
| New snapshot/storage/saved-flow tests | Exercise the contracts and approved behaviors below. |
| `README.md`, learning guide, verification report | Document storage location, local/shared scope, the algorithm boundary, setup/test commands, actual results, limitations, and practice tasks after implementation. |

Prefer small functions and plain dictionaries. Standard-library `sqlite3`, `json`, `decimal`, `hashlib`, `datetime`, and URL parsing are enough; no new package is planned.

## 4. Snapshot and title contracts

### 4.1 Public interfaces in `snapshots.py`

| Interface | Contract |
| --- | --- |
| `build_snapshot(preferences, catalog)` | Accept validated preferences and an explicit catalog list; return a new JSON-safe version-1 payload. Use existing recommendation and itinerary functions with that same catalog list. |
| `dump_snapshot(payload)` | Accept a builder payload or a decoded payload with Decimal money; validate and normalize documented monetary paths to two-decimal strings, then return canonical JSON with sorted object keys, compact separators, preserved list order/Unicode, and no non-finite numbers. |
| `load_snapshot(raw_json)` | Return a validated render-ready payload with monetary values restored to `Decimal`; raise `SnapshotValidationError` for unreadable, unsupported, or inconsistent data. Do not consult current catalog data or regenerate a plan. |
| `snapshot_fingerprint(payload)` | Accept either supported payload representation and return the lowercase 64-character SHA-256 digest of the same canonical snapshot JSON. Exclude title, ID, and creation time by keeping them outside the payload. |
| `normalize_trip_name(raw, preferences)` | Return trimmed text or the generated default; raise `ValueError` for invalid input. |

The builder uses the existing `recommend_trip_ideas()` and `generate_itinerary()` APIs without changing their rules. Both receive the same already-loaded catalog. The scheduler internally scores the supplied list too; repeating this small deterministic calculation is preferable to changing its tested public interface. It must not cause another catalog-file read or inconsistent result.

### 4.2 Version-1 payload

```text
version: 1
currency: "EUR"
cost_note: illustrative per-person estimates; not live prices
budget_note: activities/food per person; excludes flights, accommodation, transport
preferences: destination, days, budget, interests, pace, family_friendly
daily_budget: rounded approximate daily allowance
recommendations: every eligible record in its original rank order
recommendation_notices: original recommendation limitations
itinerary: the existing days/slots/totals/counts/unused_items/notices result
```

Persist every monetary field as a two-decimal string: preference budget, approximate daily allowance, every place's nested catalog estimate, recommendation costs, day/trip estimates, and unallocated allowance. Keep scores/counts/days as integers, optional flags as booleans, and empty slot items as `None`/JSON null. Never convert all numbers indiscriminately to money or use SQLite REAL for amounts.

On loading, restore all monetary fields, including nested place costs, to exact decimals in fresh result structures. `dump_snapshot(load_snapshot(raw_json))` reproduces canonical JSON, and both representations have the same fingerprint. Normalize only known monetary paths; do not use a generic `default=str` encoder that could conceal wrong types. Decimal values with fractional cents or non-finite values remain invalid rather than being silently rounded. Templates use the existing money filter. Snapshot content and notices remain stored data; viewing does not run current validation, ranking, or scheduling.

### 4.3 Stored-data validation

- Require supported integer version 1 and documented field types. Reject booleans where integer version/days/counts/scores are expected.
- Validate required strings/lists/categories and safe absolute HTTP/HTTPS source links. Reject unsafe stored links as invalid snapshot data rather than rendering an executable URL.
- Money text uses ASCII digits and exactly two decimals, is finite/nonnegative, and the positive budget stays within the original supported limit. Preserve cents rather than accepting scientific notation or rounding malformed stored values.
- Verify the approximate allowance from stored budget/days using the original half-up rule, without loading today's catalog.
- Verify day numbers 1 through the saved day count, the saved pace's expected slot names/order, unique scheduled IDs, and truthful empty-slot structure.
- Require recommendation IDs to be unique. Each scheduled item must equal its referenced saved recommendation; unused items must be the ordered complement. Place and recommendation costs must agree.
- Independently verify day sums, exact daily caps, trip total, unallocated amount, and filled/total counts. Validate matching interests/preferences against stored preferences and tags, not today's available choices.
- Do not try to repair corruption by regenerating a result. An unsupported snapshot version or invalid record becomes unavailable; it is not deleted or silently rewritten.

### 4.4 Titles and equality

Treat a missing name as blank. Check for control characters before trimming; reject tabs, line breaks, and other control characters even at the edges. Strip surrounding whitespace after that check. Blank/ordinary-spaces input produces `Paris, France — 3-day trip` for the sample; generated defaults must also fit 80 characters. Normal Unicode and punctuation are allowed as literal text, using character length rather than UTF-8 byte length.

The form content fingerprint is the hash of the snapshot only. The database duplicate fingerprint is a separate SHA-256 digest of canonical JSON containing **normalized title plus complete snapshot**. This avoids ambiguous string concatenation and excludes generated IDs/timestamps. Case changes in a title can create a separate record. Sort JSON object keys, not lists: this is exact content equality, not semantic deduplication of reordered preferences.

## 5. SQLite persistence contract

### 5.1 Configuration and schema

- `app.config["DATABASE"]` defaults to `instance/tripplanner.sqlite3`; allow `TRIPPLANNER_DATABASE` or test configuration to supply an alternative path. Resolve/document paths clearly.
- `app.config["DATABASE_TIMEOUT"]` defaults to a short bounded SQLite wait, proposed 5 seconds; tests can use a smaller value for deterministic lock failures.
- Do not connect to or initialize storage in `create_app()`, shared navigation, or ordinary home/preferences/recommendations/itinerary rendering. Generating a fingerprint needs no database.
- If the database file does not exist, collection reads return an empty list and detail reads return no record. The first valid save creates its directory/schema. Rejected saves do not initialize storage.
- Use one `saved_trips` table: positive integer primary key `id`, `title` TEXT, `created_at` TEXT, `fingerprint` TEXT UNIQUE, and `snapshot_json` TEXT. Store UTC times in one fixed ISO format, with the UTC label visible in the UI.
- Track database schema version 1 separately from snapshot version 1. Validate an existing schema; incompatible/corrupt storage is unavailable, not permission to drop or recreate it. Do not add automatic migrations in this increment.

### 5.2 Public repository interfaces in `saved_trips.py`

```text
save_trip(database_path, title, payload, *, created_at=None, timeout=5.0)
    -> (record, created)
list_trips(database_path, *, timeout=5.0)
    -> ordered list of records
get_trip(database_path, trip_id, *, timeout=5.0)
    -> record or None
```

A record has `id`, `title`, `created_at`, `snapshot`, and `available`. Its snapshot is decoded/render-ready when valid; an unreadable row has `available=False` and no invented costs. Use safe fallback metadata if a stored title/time is invalid. Keep invalid rows identifiable without modifying them. A missing ID returns `None`; invalid URL IDs are rejected before querying. Bound IDs to SQLite's positive integer range to avoid conversion/overflow errors.

For deterministic tests, the optional `created_at` seam accepts an aware UTC `datetime`. Returned creation metadata is ISO UTC text; callers do not depend on one particular equivalent UTC suffix spelling.

Use `StorageUnavailableError` for unusable storage, not for a legitimate empty collection. Snapshot parsing failures are isolated per row. Database schema incompatibility/read corruption is a whole-storage 503; one unsupported/bad snapshot is a record-level 409. If `save_trip()` encounters a duplicate-fingerprint row that is unreadable, raise `SavedTripUnavailableError` with its known trip ID; the route maps this to a friendly 409, distinct from storage-wide 503. Normal list/get reads represent an unreadable row with `available=False` rather than failing unrelated entries.

### 5.3 Atomic writes and duplicates

- Normalize/validate inputs before connecting. Use parameterized values and one explicit transaction for insert-or-reuse and its record lookup.
- The UNIQUE duplicate fingerprint is authoritative. Equivalent concurrent saves must return one row and the same original metadata, with at most one `created=True` result. Do not rely on a pre-insert SELECT alone.
- Ignore only the known duplicate-fingerprint conflict; do not turn unrelated integrity or commit failures into success. Never use replace/upsert logic that overwrites the existing snapshot, title, ID, or timestamp.
- Commit before returning success. Roll back and close on failure; close connections after reads too. A connection context manager alone does not guarantee the connection is closed.
- If a matching duplicate row is unreadable, do not report a successful reused trip or overwrite it. Raise the record-level `SavedTripUnavailableError`, preserve the row, and map it to 409 recovery.
- No module function deletes, truncates, repairs, or replaces stored data as error recovery.

## 6. Flask integration and validation order

### 6.1 Save form

On `GET /itinerary`, build the reviewed snapshot using the current validated draft and request-local catalog, and render its snapshot fingerprint as a hidden `snapshot_fingerprint` field. Keep `csrf_token` separate. Add a labeled optional `trip_name`, the shared-local warning, and the actual **Save this itinerary** POST button. Existing displayed itinerary values must correspond to that same snapshot.

Extend the existing CSRF-protected endpoint set to include the new save endpoint. Process save requests in this order:

1. Validate CSRF before draft/catalog/storage processing. Missing, invalid, or another session's token returns 400, preserving the draft and database.
2. Validate/load the current draft using the existing request-local catalog. Missing/invalid drafts follow the existing planner recovery; no write occurs.
3. Check fingerprint syntax: exactly 64 lowercase hexadecimal characters. Missing/malformed values return 400 without opening storage.
4. Build the fresh snapshot from that same catalog and compare fingerprints. A valid but different fingerprint returns 409 with review guidance; no database access or write occurs.
5. Validate/normalize the name. Return 200 with the itinerary, associated errors, raw name retained, and a current form fingerprint on invalid input. No database access occurs.
6. Save atomically. A created or valid reused record redirects with 303 to `/trips/<id>` and truthful feedback. A damaged duplicate does not receive an already-saved success message.

A storage failure returns 503 with a useful save error and recovery while preserving the draft and submitted name. Do not show raw exception/SQL/path details. Ignore client-supplied prices or itinerary JSON; they are never authoritative.

### 6.2 Saved pages must bypass the live catalog

The existing shared context always calls `current_draft()`, which loads the catalog even when there is no draft. Simply making the new route independent of the catalog is not enough.

For `/trips` and `/trips/...`, including saved 404/409/503 recovery, explicitly bypass shared draft loading without popping or revalidating the stored draft. Provide only the values the saved templates need; a CSRF helper can remain callable/lazy, but saved reads do not need to create a form token. Do not query storage globally for a navigation badge/count.

Use a bounded positive-integer ID check and friendly saved-page errors. Account for malformed paths that do not resolve to a Flask endpoint: recovery rendering for saved paths must still avoid catalog-dependent shared context. Preserve valid and malformed draft envelopes unchanged when only browsing saved pages. Consuming an existing flash message is not the same as replacing the draft.

### 6.3 Route behavior

| Route | Behavior |
| --- | --- |
| `POST /itinerary/save` | Ordered validation above; success 303; invalid title 200; invalid token/fingerprint 400; stale result 409; unavailable storage 503. |
| `GET /itinerary/save` | 405; it cannot create a record. |
| `GET /trips` | 200 collection or empty state; readable malformed rows are isolated, not allowed to break other cards. |
| `GET /trips/<trip_id>` | 200 valid read-only snapshot; 404 unknown/invalid ID; 409 unavailable stored snapshot; 503 unavailable storage. |

Saved detail shows **Saved snapshot**, UTC save time, original preferences, every original recommendation, the original itinerary and estimates, and original limitations. Links go back to saved trips or to `/plan` as **Plan another trip**, which may prefill an existing draft without clearing it. Do not add ambiguous saved-record Save/Edit/Clear controls.

## 7. Pytest architecture and isolation

Before adding any storage-enabled HTTP test, update the shared `app` fixture to supply a unique `tmp_path` database and a short test timeout. Existing clients and factories then share that test's database only. A second app for restart tests deliberately reuses that same test-local file with a different secret, never the real default path.

Retain the 322-case baseline. Reuse current preference/catalog/token/parser helpers. Add independent snapshot fixture data derived from the already-working Phase 5 contracts, with explicit money serialization and static note fields. Do not make fixtures call the missing snapshot/storage implementation: missing imports belong inside test bodies/helpers so collection succeeds and setup errors are not mistaken for missing features.

Planned files are `tests/test_snapshots.py`, `tests/test_saved_trips.py`, and `tests/test_saved_trip_flow.py`, with small shared helper additions where useful. The testing step must record actual discovered counts, not a predetermined target.

### 7.1 Snapshot/name/fingerprint unit tests

- Build the complete seven-recommendation/six-slot sample with EUR 103.00/EUR 197.00 and all original metadata/notices.
- Parameterize exact cent amounts, free estimates, the EUR 100.01 boundary, 1/14 days, pace choices, partial/empty results, and Unicode names.
- Verify every monetary path is a two-decimal string on disk and a `Decimal` after loading, including nested place estimates; booleans/integers retain their types.
- Check canonical object-key order independence, preserved list order, stable content hashes, title/time exclusion from form hashes, and identical dump/hash results for serialized versus Decimal-decoded payloads. Changed result data changes its hash.
- Cover blank/default names, trimming, 80/81-character boundaries, control characters before trimming, normal Unicode, and literal SQL/HTML text. Generated defaults also respect the limit.
- Reject bad versions, wrong types, invalid/non-finite/non-cent money, missing fields, unsafe URLs, bad day/slot structure, duplicate IDs, inconsistent referenced records, wrong complements/counts/totals/caps, and invalid JSON.
- Patch live catalog/recommender/scheduler access to raise during loading; valid stored snapshots must still decode. Compare deep-copied inputs to prove building/decoding does not mutate them.

### 7.2 SQLite repository tests

- Initial absent-path list/detail behavior; first valid save creates schema, a stable positive ID, and UTC metadata without demo records.
- Round-trip the full sample, same-title/content duplicate reuse, changed title/content separation, original ID/time preservation, newest-first and ID tie-break ordering.
- Inspect raw SQLite column/value types: money is inside TEXT JSON, never REAL; SQL-looking names are literal values and do not alter tables.
- Use two separate connections/threads to save equivalent data concurrently. Coordinate before entering the save operation, not after taking a write lock. Assert one row and one original ID/time.
- Reopen the file through a fresh repository/app; test empty, partial, and exact-cent snapshots.
- Corrupt one test-local payload or set an unsupported snapshot version. Other records remain readable; the bad row is unavailable and not changed/deleted. A save colliding with its duplicate fingerprint raises `SavedTripUnavailableError`, not false success or a storage-wide error. Unsupported database schema is unavailable, not reinitialized.
- Verify rollback using a connection proxy that fails at actual commit after executing an insert. A fresh independent connection must see existing rows intact and no new row. Raising from a mocked whole save function is not proof of transaction rollback.
- Test read-only storage using SQLite's read-only connection mode on a prepared test file, rather than unreliable Windows permission changes. Test locks with a separate real exclusive transaction and a short timeout; release it in `finally`.
- Cover an invalid parent path, corrupt database bytes, failed reads, and closed connections. Never reset or remove an existing database to make a test pass.

### 7.3 HTTP integration tests

- Parse the actual itinerary save form, title label, CSRF token, fingerprint, shared-local notice, and action/method; submit through that form.
- Check first save's 303/detail, truthful duplicate feedback, refresh without duplicates, collection summaries/order, default names, all seven saved ideas, original six slots, counts, costs, notices, UTC time, and snapshot label.
- View after clearing the draft and from a separate client. Prove shared saved collection versus isolated unsaved drafts.
- Create a new app with a different signing secret and the same test database; reopen snapshots without the old cookie.
- Change/remove catalog records, remove the saved destination, and make the catalog unreadable or loader raise. List/detail, malformed-ID 404, invalid-snapshot 409, and storage 503 rendering must not call the catalog or mutate the session draft.
- Change a draft in another tab or change relevant catalog content after obtaining a fingerprint: 409, no write. A harmless unrelated catalog change with identical snapshot content remains saveable.
- Cover CSRF failure variants, missing/malformed/changed fingerprints, missing/stale draft recovery, GET save 405, title errors with raw retention and associations, and client-supplied price/JSON tampering. Assert rejected saves do not initialize an absent database.
- Simulate database write/read failures and damaged payloads; assert statuses, useful recovery, no false success, no raw SQL/path/traceback, and preserved rows/drafts. Unsaved planning must still work with an unusable configured database.
- Verify literal HTML/SQL title display without injected script elements, no saved-record mutation controls, working navigation, and the ordinary server-rendered save/list/view journey without running browser JavaScript.

The existing home test describes unbuilt features and prohibits a direct “save trip” action. During test definition, revise that intent narrowly to allow the approved, working **Saved trips** navigation while still rejecting nonexistent or mutating home save controls. Keep all other valid home/form/itinerary/security assertions. Document this legitimate expectation update and the fixture-path change; do not silently weaken tests during implementation.

## 8. Testing gate before coding

1. Record the fresh 322-passing baseline and fingerprint application files before test edits.
2. Define the new fixtures/tests and the minimal approved existing-test migrations without adding feature code or creating the real database.
3. Run collection for the entire suite. Missing future modules must fail inside relevant tests, not abort discovery. Fix syntax, fixture, parser, and environment errors first.
4. Run affected tests and inspect all failure groups. Missing snapshot/storage APIs, routes, save forms, or saved navigation are expected. Broken fixture data, mistaken money/order expectations, unsupported test locking, or temp-folder failures are not acceptable missing-feature evidence.
5. Verify fixtures are adversarial: prices change while the draft stays valid; a genuinely unrelated catalog edit leaves the hash unchanged; saved reads are tested with catalog calls forbidden; commit faults occur after an attempted write; concurrent requests use independent connections.
6. Run retained tests and record actual passed/failed/error/skipped counts, explaining any intentional expectation changes separately from new missing functionality.
7. Record the Phase 6 red checkpoint and confirm the real database is untouched. Only then begin implementation.

Use a fresh, validated pytest base directory inside the ignored project `.tmp` folder. Pytest can clear an existing base directory, so never point it at the project root, a real database folder, or earlier evidence. All storage fixtures live below test-specific temporary paths.

## 9. Implementation slices after the testing gate

### A. Snapshots, titles, and exact persisted values

Implement the new pure data layer and pass serialization, validation, name, and fingerprint tests without a database or Flask route.

**Learning focus:** Dictionaries/lists, serialization, type checks, decimal strings, canonical content, and why snapshots are historical results rather than live references.

### B. SQLite collection and atomic writes

Implement lazy schema creation, safe queries, duplicate uniqueness, ordered reads, transactions, per-record validation, and failure behavior. Run real file/connection tests before adding web saving.

**Learning focus:** Tables/rows, primary and unique keys, parameterized queries, commit/rollback, resource cleanup, and concurrency.

### C. Protected save and catalog-independent reads

Add config, the save form/POST, fingerprint checks, saved endpoints, and the shared-context bypass. Test failures before successes: CSRF, stale forms, invalid names/drafts, unavailable storage, and corrupt records. Keep current unsaved flows working.

**Learning focus:** GET versus POST, POST–redirect–GET, validation order, browser sessions versus database persistence, and honest error recovery.

### D. Responsive saved pages and student handoff

Complete saved navigation/list/detail, scoped styling, real-browser checks, README, the learning guide, and the verification report. Run the full suite after final changes.

**Learning focus:** Accessible forms, clear saved-versus-current labels, progressive enhancement, and explaining the limits of tests and local shared storage.

These are implementation slices for one approved increment, not a fixed schedule or additional approval gates.

## 10. Browser verification after implementation

- Use an isolated browser-check database, never delete or reset the user's collection. Start a temporary local preview with that configured file if needed; clean up only owned processes/tabs.
- At 360px and 1280px widths, inspect navigation, form feedback, cards, long 80-character titles, original recommendations, slots, notices, and estimates for readability and no horizontal overflow.
- Use real controls for save → detail → collection → detail → plan another. Check blank title, named title, invalid long name, duplicate feedback, partial/empty results, and stale save guidance.
- Check keyboard tab order, labels, visible focus, Enter submission/navigation, and associated errors.
- Check the flow with application scripts blocked or JavaScript disabled and document the exact method. The live preview may disappear; authoritative save/list/view must work.
- Restart the temporary app with the same test database and a changed secret; reopen from a fresh client. Test catalog removal/unavailability only in the isolated preview, not by damaging the live sample file.
- Confirm current draft clearing does not remove saved trips, and saved viewing does not replace a current draft.
- Confirm snapshot/shared-local labels and UTC times are visible, no script execution occurs from title text, no false save success appears, and ordinary-flow console errors are absent.

Python HTML tests establish route/content behavior, not actual layout, browser keyboard operation, or accessibility-tree quality. Add a regression test before fixing an observed logic defect; use browser checks for visual defects.

## 11. Completion and learning handoff

Complete this increment only after new and retained tests pass, required browser checks pass, restart/catalog independence is demonstrated, no real saved data was reset, and documentation reflects the actual behavior.

The guide must explain the exact changed files and request flow in beginner-friendly language, distinguish draft/snapshot/database/session, explain the AI boundary, and include the specification's six small practice tasks and a presentation explanation. Report actual verification results and any limitation, not a promised or assumed test count.

**Student task at this planning checkpoint:** Explain why saving only catalog IDs would not preserve the EUR 103 plan after prices change, and why displaying “Saved successfully” before a database commit would be misleading.

**Completed handoff:** Read the [student guide](../docs/phase-06-learning.md), try its six practice tasks, and consult the [verification report](../docs/phase-06-implementation.md). Any later feature begins a new specification-approval cycle; no fixed timeline is introduced.

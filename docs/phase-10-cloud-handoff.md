# Phase 10 cloud handoff — Help increment only

Date: 9 November 2026, Asia/Shanghai. This is an isolated source candidate, **not a deployment**. The approved full accounts/Help/optional-AI scope remains in force; this bundle implements its small provider-independent Help boundary (10A), not all of Phase 10.

## Source review and reconciliation

The attached `TripPlanner-submission-source-2026-11-06-final.zip` was readable: 234 archive entries. Work used its extracted managed-cloud copy, not the user's laptop or a live repository checkout. The ZIP has no Git history proving either supplied SHA; this report does not identify it as an independently verified checkout of `b7d2ee2988930db9e0f755be75ea6bff035c9668` or deployed `b969af3b575b3827ec08b51976e812044f38e100`. Input file hashes are recorded in `phase-10-evidence/input-manifest.json`; bundle provenance records the archive hash.

Reviewed product/planning/privacy/readme and relevant saved-trip, itinerary, expanded-release and free-hosting contracts; traced app construction, Jinja context, money/scheduler behavior, hosted identity, snapshot storage, test fixtures and shared Windows/Android staging allowlists. Relevant exact seams:

| Verified source | Finding and implication |
| --- | --- |
| `app.create_app(test_config)` | Actual Flask factory; `tests/conftest.py` provides isolated client/database and HTML-parser fixtures. No replacement app was invented. |
| `templates/trip_preferences.html`, `money.daily_allowance`, `itinerary._first_fitting_item` | Allowance is total activities/food per person for all days in destination currency; display rounding does not loosen exact daily checks. Flights/accommodation/transport/missing meals are excluded. |
| `app.shared_page_values` | Shared template context normally loads/validates the catalog/draft. Help must bypass that path so broken catalog data or a stale draft cannot prevent self-service guidance or alter the draft. |
| `hosted.create_hosted_app` | Explicit hosted factory, stable configured secret, renewable signed visitor authority, SHA-256 owner digest and private/no-store responses. Help reuses these hooks. No live configuration read/changed. |
| `hosted_postgres`, `hosted_saved_trips` | Owner-scoped save/list/read; immutable `snapshot_json` is TEXT. Exact stored text can remain untouched by future ownership changes. Namespace/metadata/schema validation rejects unexpected layouts. An additive account column is therefore not automatically compatible. |
| Same adapters | `UNIQUE(owner,fingerprint)` and strict 64-hex owner syntax need deliberate account-ownership design. Simply putting email/account IDs into `owner`, or adding a column without revising compatibility checks, is unsafe. Duplicate fingerprints across collections need atomic collision handling without losing snapshot IDs; future claim tests must cover this. |
| `saved_trips`, local/native factories | Independent SQLite collections; no account migration or upload. No delete/export/account endpoints exist in this source. Future account scope will require new endpoints rather than protecting imagined existing ones. |
| `build_windows.MODULES/TEMPLATES`, `build_android` | Both use explicit shared resource allowlists. New Help module/template must be listed even though no binary is built. |
| `tests/test_hosted_postgres.py` | Nine real-PostgreSQL cases require a guarded disposable loopback administrator DSN. It was not configured; no production database was contacted. |
| `PRIVACY.md` | Cookie expiry does not delete anonymous rows; no cleanup policy is currently implemented. Phase 10A adds no retention change. |

Earlier documentation contains historical statements superseded by later hosting notes. The approved Phase 10 spec governs the new optional scope; older “no accounts” wording remains accurate for this candidate because accounts remain absent. Full original SPEC/PLAN/README/PRIVACY and historical artifacts are preserved; this report identifies the new increment without rewriting historical release claims.

## Test-first sequence actually completed

The implementation/test plan was already recorded before this source work. Source-dependent mapping above now replaces its source-unavailable assumptions for the reviewed ZIP. No further approval of unchanged scope or plan is requested.

1. Read archive and source. Initial test attempt found no installed pytest; that environment failure was not counted as red evidence. Installed cloud development dependencies only; repository requirement files were not modified.
2. An initial relevant baseline subset passed 197 tests. Then the full original baseline, excluding the new test file, passed **1,679 tests, 9 skipped**. Log: `phase-10-evidence/baseline.txt`.
3. Wrote `tests/test_phase10_help.py` before changing application code. Actual Flask tests collected and ran: **16 failed, 1 passed**. Missing route/navigation/search/staging/FAQ functionality explains the failures. This was not a collection failure or unconditional failure. The module unit test also exposed the absent `help_content` module; the real HTTP integration tests independently exposed missing behavior. The disable-Help preservation case already passed. Logs: `help-red.txt` and `help-red-pinned.txt`.
4. Implemented Help only after the red checkpoint. The unchanged 17 tests then passed. Log: `help-green.txt`. Final whole-suite output is in `final-regression.txt`; **1,696 passed, 9 skipped in 32.00 seconds**, exit code 0.

Cloud runtime: Linux, Python 3.12 (not the historical Python 3.14 classroom runtime). Pinned final pytest 9.1.1 and hosted dependencies are recorded in `environment.json`. The first preliminary red/subset checks used pytest 9.2.0; red was repeated with pinned pytest 9.1.1 before implementation. No browser/desktop control, native build, emulator, stress test, provider call, email send, account creation or paid resource was used. Existing bounded runtime tests may start their own cloud loopback test services; they do not control or run anything on the user's computer.

## Implemented behavior

- `/help`: server-rendered, no-JavaScript FAQ/category-style topic index with stable anchors, bounded 200-character plain-text search, useful empty results and a reset link.
- Twelve frozen versioned FAQ entries, with project-source provenance. Correct allowance scope, six-city limit, honest missing meals/slots, immutable snapshots, hosted cookie limits, Maps, free-host wake-up, independent native saves, themes and self-service support limits.
- Persistent Help navigation using existing shared layout/theme. Semantic heading/label/status structure; wrapped controls, responsive text sizes, existing focus/theme tokens and no added animation.
- `PHASE10_HELP_ENABLED` switch controls both route and navigation. It defaults on in this candidate source; no live site is changed. Disable through app configuration to remove the new Help route/link.
- Help does not access saved storage or catalog loading, invalidate stale drafts, contact identity/AI providers or rewrite snapshots. Query text is escaped by Jinja. No new credentials or provider dependency.
- Shared native source resource allowlists include the new module/template so future staging is complete. Existing downloadable binaries are unchanged and have not been rebuilt.

## Limits and remaining Phase 10 work

**10B accounts/recovery/claiming: not implemented; no executable tests defined or run for that increment in this bundle.** The plan's account cases remain planned. Generic account development can continue in later small test-first slices without repeating scope approval; actual identity/email activation needs separately chosen, officially verified free-only services and recovery/revocation/delivery terms. Current adapters require deliberate schema/ownership compatibility design and real PostgreSQL transaction/race tests before changing ownership behavior.

**10C native online access: not implemented.** No external account-launch or system-browser OAuth integration was added. No local saves upload. Wrapper platform authentication/storage remains unverified.

**10D integrated AI: not implemented.** Help honestly states there is no integrated AI or current account feature. No external-AI button was added. Future provider-free context/quota/citation/fallback tests and later provider contract verification are still required. ChatGPT Plus is not API access. Identity/model provider accounts, terms, credentials and billing decisions remain separate; no payment method, paid trial, automatic upgrade or paid API is authorized.

**Accessibility:** pytest checks semantic markup, labels, all FAQ anchors, no-script responses and escaped search. Existing theme styles are reused. Actual rendered 200% zoom layout, screen-reader behavior and interactive keyboard/contrast checks have not been performed in a browser. AC-02 is therefore only partially validated; this is a tested source candidate, not an accessibility-certified release. New Help has no animation or script dependency. OS/native verification is also pending.

**PostgreSQL:** nine existing real-DB tests skipped because the disposable test DSN was absent. No real PostgreSQL, cloud backup/restore or production restart was tested in this run. Existing owner-scoped hosted SQLite integration did run, including a synthetic historical row with intentionally unavailable payload text and foreign denial. This is not substituted for PostgreSQL evidence.

## Protection, review and rollback

Original archive remains unchanged. No repository credentials were used, main branch was not changed, no service was deployed, and no production namespace/data/secret/TLS settings were edited. Windows/Android downloads and presentation PPTX/DOCX/intro video remain unchanged. The source ZIP contains no real saved rows or credentials introduced by this work. Logs use synthetic data only.

Review the machine-readable changed-file list and unified patch inside the bundle. Only app Help integration, the new content/template/test, styles and shared source staging allowlists change application behavior. No schema/storage/scoring/scheduling modules are modified. This candidate must not be confused with the live presentation release.

For this Help-only source slice, rollback is removing the patch or disabling `PHASE10_HELP_ENABLED` in application configuration; no data rollback is needed. This is not the rollback procedure for a future account-owning release, where old binaries could violate ownership. Deployment remains separately gated.

## Beginner explanation

The FAQ content is a tuple of frozen records, so searching selects answers without changing them. The Flask route reads a short search string, chooses matching records and renders escaped HTML. Jinja inheritance gives Help the same navigation and themes as the rest of the app. The shared context deliberately avoids loading a trip for Help, so help still works when the catalog is unavailable.

The red tests showed the feature was missing; the same tests passing after implementation demonstrate this small slice works in the cloud test environment. A skipped database test means it was not checked, not that it passed. Accounts and AI require additional test-first slices and their provider decisions before activation.

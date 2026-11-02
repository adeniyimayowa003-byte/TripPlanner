# TripPlanner — Phase 8 Foundation Test Checkpoint

**Scope:** [Approved six-city release specification](../specs/phase-08-expanded-release.md) and [implementation/test plan](../plans/phase-08-expanded-release-plan.md).

**Status:** Historical foundation red checkpoint. The three web phases are now implemented with **1,477 passing cases**; see the [current implementation/demo guide](phase-08-three-phases.md). The original results below remain historical evidence and retain their original case count. Photos and native package/device gates remain.

## What this means

We wrote a checklist for the next pieces of the app: correct currencies, credible city data, safe Maps links, and preserving saved trips. At this checkpoint, the new feature checks failed because those pieces had not been built. That was the **red** stage of test-first development.

The current website still has the original Paris data and its working features. All 943 existing tests remain passing and unchanged. A failing new requirement is not evidence that we broke an existing page.

## Observed results

Before adding tests, a fresh isolated run passed **943 cases in 16.41 seconds**. The final expanded run collected **1,269 cases** and produced **962 passed, 307 expected missing-feature failures, 0 errors, and 0 skipped in 17.17 seconds**. Exit status 1 is expected at this checkpoint. No `skip` or `xfail` marker hides missing behavior.

| Area | Cases | Passed | Expected failures |
| --- | ---: | ---: | ---: |
| Retained Phase 7 suite | 943 | 943 | 0 |
| [Currency contracts](../tests/test_currencies.py) | 164 | 1 | 163 |
| [City profiles and catalog contracts](../tests/test_expanded_catalog.py) | 67 | 15 | 52 |
| [Maps URL contracts](../tests/test_maps.py) | 35 | 1 | 34 |
| [Versioned snapshots and storage](../tests/test_multicurrency_snapshots.py) | 60 | 2 | 58 |
| **Total** | **1,269** | **962** | **307** |

There are **326 new parameterized cases**, not 326 distinct product features. Their 19 passing checks protect independent examples/helpers and existing compatibility. They do not prove that the six-city interface or Maps buttons exist.

A separate selected helper/legacy run passes **18 cases**; the other 53 cases in that selected file set were deselected, not skipped. The full run above exercises every case.

Ignored machine-readable evidence:

- `.tmp/phase8-testing-baseline.xml` — fresh original-suite baseline.
- `.tmp/phase8-helper-health.xml` — independently checked fixtures/helpers and v1 reads.
- `.tmp/phase8-foundation-red.xml` — final full red checkpoint.
- `.tmp/phase8-testing-source-baseline.json` — before-edit fingerprints.

## Every failure group was inspected

| Missing behavior | Failures |
| --- | ---: |
| The six-currency registry module is absent. | 16 |
| Budget parsing has no explicit currency argument. | 129 |
| Daily allowance has no explicit currency argument. | 9 |
| Money formatting has no explicit currency argument. | 9 |
| Profile loading, canonical destination lookup, and release-catalog validation APIs are absent. | 45 |
| `data/destinations.json` is absent. | 1 |
| The actual catalog still has seven Paris places and no released records for the other cities. | 6 |
| The pure Maps URL module is absent. | 34 |
| New snapshot builds still produce version 1 with EUR formatting. | 6 |
| Snapshot decoding/storage does not support valid version-2 documents yet. | 52 |
| **Total** | **307** |

There were no collection/setup errors or unrelated application failures. Assertions beyond a missing API or unsupported version remain requirements to exercise during implementation. The red result does not establish that those later branches already work.

## Independent test examples

[Frozen fixture notes](../tests/fixtures/README.md) describe the original seven-place [Paris catalog](../tests/fixtures/phase7-paris-catalog.json) and [canonical v1 saved trip](../tests/fixtures/phase7-paris-snapshot.json). They were captured before any catalog expansion or serializer changes.

The saved example contains seven recommendations, six filled slots, EUR 103.00 scheduled, and EUR 197.00 unallocated. Its canonical JSON, excluding the final file newline, has SHA-256:

`faa80e3581949c832e06292142ee86c5125377fcc395b78b5b2171bab427cbfb`

The first helper run caught damaged accented characters in the captured snapshot. Explicit Unicode handling restored the original characters, matching the previously recorded hash and the unchanged Phase 7 serializer. The final helper run passes. This correction only affected the new test fixture.

[Test-only helpers](../tests/phase8_helpers.py) create eight synthetic QA records for each city and derive independent v2 examples from the frozen sample arithmetic. QA names, addresses, `example.com` references, and cost scale factors are deliberate examples. The scale factors are **not exchange rates**. These records must never be shipped as researched travel data.

Fixture health checks verify counts, tag variety, independent expected totals, scheduled-copy equality, and money-path precision without asking a future serializer to generate its own expected output. Frozen v1 storage is seeded directly into a temporary SQLite database; future save code does not create that historical oracle.

## What this batch covers

### Money and city data

- Six approved currency codes, immutable precision/limits, exact Decimal money, whole-yen input, boundary values, malformed input, and explicit rejection of unknown codes.
- Daily display rounding at the correct minor unit, with preserved legacy EUR helper defaults.
- Six canonical city profiles, fresh-copy loading/lookup, malformed profile rejection, unique place IDs, matching city/currency, reviewed location/source fields, and invalid-value rejection.
- Actual release-data checks for eight places, two food options, four interests, free/paid variety, exact cost text, dated provenance, and retained original Paris IDs.
- Existing recommendation/scheduling logic exercised with each synthetic city and independent expected totals. This is arithmetic regression evidence, not proof of realistic local recommendations or complete destination-aware form behavior.

Actual addresses, prices, factual descriptions, suitability tags, and redistribution permissions still require source review during data preparation. A well-formed URL/date does not prove its claim is true.

### Google Maps

The future helper must construct a fixed HTTPS Google Maps search URL locally, encode Unicode/query data, preserve exact reviewed coordinate pairs, and reject unusable locations. Tests check optional Place IDs, length, controls, hostile query text, nonmutation, and absence of network calls. The independent URL checker also rejects lookalike hosts and unwanted parameters.

These tests do not render a button, open Google Maps, or establish that a named real-world spot is correct. HTTP link markup and actual external-navigation checks remain separate gates.

### Saved trips

- Canonical v1 bytes, hash, amounts, IDs, timestamps, and repository columns remain unchanged. Historical reads are tested with current travel-data/generation access forbidden.
- New v2 builds must freeze destination currency and reviewed locations without mutating supplied preferences/catalog records.
- Independently defined v2 documents must round-trip every nested money value and hash, without the current catalog or algorithms.
- Corruption checks first require a valid v2 document to load. Rejecting every v2 document cannot falsely pass those negative tests.
- Invalid money precision, inconsistent currency, malformed locations even when every copy agrees, and mismatched repeated location copies are rejected.
- New-currency snapshots can exceed the old EUR ceiling; EUR preserves its original ceiling.
- New v2 saves and duplicate reads coexist with the original v1 row without rewriting it. A consistent reviewed-address change changes the content fingerprint.

## What remains before integration

1. **Form/draft/server tests:** Define version-2 preference/draft contracts, server-owned city currency, signed currency-change context/acknowledgement, raw-answer recovery, real six-city submit/recommend/itinerary/save/reopen flows, CSRF/stale-save behavior, consistent labels, map markup, and genuine v1 fallbacks.
2. **Actual planner JavaScript tests:** Execute the production options/preview behavior through a bounded harness, with independent integer/minor-unit expectations and explicit amount-change confirmation. Check the no-script flow separately.
3. **Legitimate old-test migrations:** Before activating the expanded dataset or changing new-save defaults, move original seven-place/sample assertions onto the frozen fixture and update new-draft/new-build shape expectations. Keep historical v1 tests historical. Do not delete security, exact-money, transaction, duplicate, or appearance checks to make the suite green.
4. **Photos:** Define manifest/file/credit/license/alt/dimension/fallback and both-theme checks before adding assets and image markup. This checkpoint contains no licensed-photo verification.
5. **Downloads:** Define staging/runtime/external-navigation/storage tests before native launchers or packaging. Toolchain setup, actual Windows builds, Android SDK/device checks, installation, and restart/offline verification remain undone.

The directly covered pure currency and Maps helpers have since been [implemented and verified](phase-08-currency-maps.md). Snapshot-default changes, live-data activation, and form integration still need the corresponding tests and old-fixture migrations above. Both Windows and Android downloads remain in scope.

## Isolation and unchanged application

At this historical test-definition checkpoint, all **45 originally fingerprinted files**—production code, templates/static assets, data, dependencies/ignore configuration, and retained tests—matched their before-edit SHA-256 values. New files were tests, fixture notes, and this report; specification/plan documents recorded the checkpoint. Later helper implementation changes are recorded separately in the [implementation report](phase-08-currency-maps.md).

Runs used fresh validated project-local `.tmp` directories and per-test databases. No app source, production dataset, image asset, dependency file, real saved-trip database, browser preference, active form, native installation, or running preview was changed for this work.

## Small student tasks

1. Open the frozen saved-trip example and find `version`, `currency`, and the EUR 103.00 total. Explain why an old saved trip should not change when the catalog changes.
2. Calculate JPY 100 divided over three days: its displayed daily amount is JPY 33. EUR 100.00 displays EUR 33.33. Explain why the currency's smallest unit affects display rounding.
3. Explain why building a Maps link needs no API request, while opening the external map needs connectivity.

The AI concepts remain the existing explainable recommendation scores and greedy daily scheduling. Currency rules, URL building, and saved-data versioning are supporting programming concepts; this increment introduces no trained model or chatbot.

# Three completed web phases — 1 November 2026

The requested three connected phases are implemented and verified. **All 1,477 pytest cases pass**, with no failures/errors/skips, in 48.13 seconds. This includes the earlier regression cases with documented fixture/version migrations, the real production planner script, the six-city dataset, versioned storage, and full save/reopen/Maps journeys.

The verified local demonstration is [TripPlanner on port 5001](http://127.0.0.1:5001/). It uses an isolated QA database, containing a clearly named Tokyo demonstration snapshot. The user's main saved-trip database was not populated, deleted, migrated, or reset.

## Phase one: currency-aware validation and drafts

**What changed:** [preferences.py](../preferences.py) now accepts explicit city profiles, derives the destination currency on the server, validates native precision/bounds, and returns raw answers on errors. [drafts.py](../drafts.py) supports currency-bearing v2 drafts and explicit recovery of genuine v1 Paris drafts. Legacy helper interfaces remain for the original regression examples; the new live routes always supply profiles.

[currency_context.py](../currency_context.py) signs a small browser-session-bound note containing the form's displayed currency and pending review state. It is separate from CSRF and trip-content fingerprints. An altered/missing/cross-browser note is rejected before catalog/storage access.

**Why:** The same digits cannot silently change from euros to yen. An invalid day count must not erase the traveler's answers or their last valid draft.

**How:** Raw form values are strings. Accepted values use canonical city names, integers for days, Decimal money, and a trusted currency code. Session drafts store JSON-safe exact money strings. A currency-changing POST redisplays a review checkbox; only a checked submission under the matching pending context can accept the new unit. There is no exchange-rate conversion.

**Verification:** The focused baseline reproduced 148 missing-feature failures and 120 passes. After implementation, all **268 validation/draft/context/legacy helper cases passed**. The actual form review is also covered by HTTP tests and browser verification below.

## Phase two: working six-city planning and saved itineraries

**What changed:** The live [place catalog](../data/places.json) now contains **48 sourced records**, eight per city, including at least two food venues, free/paid activities, and four-plus interests for each city:

| Destination | Currency |
| --- | --- |
| Paris, France | EUR |
| Lagos, Nigeria | NGN |
| London, United Kingdom | GBP |
| New York City, United States | USD |
| Tokyo, Japan | JPY |
| Cape Town, South Africa | ZAR |

The original seven Paris IDs and names remain stable. Factual descriptions/addresses were reviewed against primary venue/official-tourism sources. All costs are explicitly illustrative per-person planning allowances, not live ticket/menu quotes. Zero estimates apply only to the described free entry/walk; optional purchases/facilities and required transport can cost extra. See the [Paris/London/Cape Town source notes](phase-08-sources-europe-africa.md) and [Lagos/Tokyo/NYC notes](phase-08-sources-world.md).

The form now updates available interests, pace, currency, input bounds, and daily preview. [plan.js](../static/js/plan.js) uses safe integer minor units for the preview, preserves compatible choices, clears unsupported choices, and invalidates a changed-currency preview pending server review. It never changes the signed token. JSON page data is safely rendered with Jinja's `tojson`; dynamic labels use text nodes.

Recommendations and itinerary/saved pages show the correct currency. [snapshots.py](../snapshots.py) builds v2 snapshots for new currency-bearing live preferences, freezing reviewed place locations and native money precision. Genuine v1 JSON/hashes remain unchanged. Historical reads use stored content, not today's catalog. The SQLite table/schema and duplicate/transaction guarantees remain unchanged.

**Why:** Another city needs usable sourced records, correct units, and an end-to-end save flow. Adding only a dropdown label would not provide those.

**How the AI works:** The existing explainable rule-based recommender adds three points for each matching interest and one for each matching pace/family tag. The scheduler greedily selects unique eligible records by category and exact daily allowance. It leaves honest gaps when data, categories, or budget are insufficient. It is not a trained model, booking system, opening-hours checker, or route optimizer.

**Verification:** New actual-script and full-journey tests were defined before integration: the bounded integration red run had **107 failures and 10 passes**. Snapshot/storage implementation then passed **313 cases**. Full HTTP journeys cover each city, exact currency, review acknowledgement, duplicate saves, frozen-address staleness, and historical reads.

## Phase three: visible Google Maps actions and final web checks

**What changed:** [_place_location.html](../templates/_place_location.html) shows the stored address and a visible **View on Google Maps** action on recommendations, itinerary entries, and saved recommendations/entries. It uses the previously tested pure URL helper, a separate browsing context, and opener protection. An old snapshot without location metadata shows an honest unavailable-location fallback.

**Why:** Travelers can find the recommended spot while keeping TripPlanner and their answers open. Building the URL locally needs no API key, embed, account setup, GPS, or provider request on page load. Opening the external map requires connectivity.

**Browser evidence:** On the isolated port-5001 preview, a real Tokyo trip with three days, JPY 30,000, and food/history interests displayed a **JPY 10,000 daily preview**, seven matching recommendations, a seven-of-nine-slot itinerary, and a **JPY 7,300 scheduled total**. Saving and reopening the Tokyo snapshot succeeded. Light and Dark both rendered correctly at the available browser width.

The Meiji Jingu action opened a separate Google Maps tab with the public venue/address query. Google's results included Meiji Jingu and the nearby garden; this is a search link, not a guaranteed unique pin. TripPlanner remained open. The Google tab was closed after verification; no Google results/coordinates/Place IDs were copied into the catalog.

Changing the live Tokyo draft to London showed an explicit GBP review with the last valid draft protected. That browser check exposed premature formatting of raw `300` into `300.00`: a new failing regression test was added before fixing the app to retain raw answers throughout review. All **1,477 tests then passed**.

Screenshots: [Light](../.tmp/tripplanner-tokyo-light.png), [Dark](../.tmp/tripplanner-tokyo-dark.png), and [final saved-trip view](../.tmp/tripplanner-completed.png). These are QA screenshots, not bundled travel photos.

## Original-test migrations

No tests were skipped or removed to obtain green results. The required migrations were:

- The original regression modules use the frozen seven-place Paris catalog, preserving the EUR 103.00 / EUR 197.00 example and scoring/affordability assertions. Their fixtures gain clearly fictional QA location metadata for v2 live-page checks; these addresses never enter the released catalog.
- Existing standalone v1 snapshot factories remain historical. New live-save expectations in appearance tests explicitly use v2 plus EUR, while immutable-byte/duplicate/schema assertions remain intact.
- Ordinary POST helpers and direct valid-form tests submit the real new currency-context field alongside CSRF. Missing/forged-context tests remain separate rejection checks.
- New live-draft creation expects version 2; existing genuine v1 read/recovery tests remain v1.
- The session-key allowlist adds only `currency_context_nonce`; appearance choices are still excluded from authoritative trip data.

The first full integration run found ten old fixture/version/token expectations requiring these migrations. Targeted follow-up checks passed before the final full run. Frozen v1 bytes/hash tests continue passing.

## Verification evidence and limits

Ignored machine-readable evidence: `.tmp/three-phase-helpers-red.xml`, `.tmp/three-phase-helpers.xml`, `.tmp/three-phase-integration-red.xml`, `.tmp/three-phase-snapshots.xml`, `.tmp/three-phase-regression.xml`, and `.tmp/three-phase-final.xml`.

All browser writes used `.tmp/three-phase-browser-qa.sqlite3` and the QA origin. The existing main tab and its user data/preferences were not changed. QA's Light/Dark checks were confined to that separate origin.

The viewport capability did not apply the requested 360px override: observed viewport width stayed about 738px, with 723px page width and no overflow. Its override was reset. This is not a verified phone/emulator result. Existing responsive/theme CSS checks pass, but actual 360px/native device verification remains required.

Automatic approval review rejected starting the normal port-5000 preview because it could affect the main server/data. That action was not retried or bypassed. The owned, isolated port-5001 preview was used instead and remains available for demonstration.

## What remains before the whole project is finished

These three web phases are complete; **all of Phase 8 is not yet complete**. Suitable licensed local photographs, image-credit/fallback checks, Windows and Android package runtimes/builds/install tests, and final presentation rehearsal remain. No executable, APK, installer, hosted deployment, or all-device readiness is claimed here.

## Quick presentation walkthrough

1. Open the local demo and choose Tokyo, three days, JPY 30,000, food/history.
2. Show the whole-yen daily preview and explain one recommendation's matching tags.
3. Build the itinerary; explain one empty slot and why prices are illustrative.
4. Open a venue in Google Maps, then return to TripPlanner.
5. Save the itinerary, reopen it from Saved trips, and switch Light/Dark without changing the trip.
6. Edit the draft to London and demonstrate explicit currency review rather than conversion.

For another short demonstration, try Paris EUR 300, London GBP 300, Lagos NGN 300,000, NYC USD 300, or Cape Town ZAR 3,000 for three days. These are demo inputs, not travel-spending recommendations.

The most useful class explanation is: **the data supplies the places; validation protects the inputs; explainable scores rank matches; a greedy scheduler fills days; a saved snapshot freezes the reviewed result.**

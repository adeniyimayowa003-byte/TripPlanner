# Phase 8 — City Profiles and Place Validation

**Completed slice, 2026-10-26:** The six approved city profiles and their loading, lookup, and place-validation helpers are implemented after validated failing tests. The website still uses its original Paris place catalog. Reviewed places for all six cities, form integration, visible Maps buttons, v2 saved trips, photos, and downloadable packages remain in progress.

**Later test checkpoint:** The [server-form/draft/currency-review tests](phase-08-form-testing.md) now add 181 cases before form implementation. Their full run has 1,209 passes and 242 inspected missing-feature failures. The counts below preserve this earlier city-data delivery's results.

## What we built

[data/destinations.json](../data/destinations.json) gives each city a stable ID, display name, country, and currency:

| City | Currency code |
| --- | --- |
| Paris, France | EUR |
| Lagos, Nigeria | NGN |
| London, United Kingdom | GBP |
| New York City, United States | USD |
| Tokyo, Japan | JPY |
| Cape Town, South Africa | ZAR |

A **city profile** describes a destination. A **place record** describes an attraction, activity, or restaurant within it. Having a city profile does not mean its attractions have already been researched or added.

These profiles give the future form an authoritative answer to “which currency belongs to this city?” The server will use this answer rather than trusting a currency label sent by the browser.

## How the helpers work

[catalog.py](../catalog.py) now provides three additional public functions. The existing sample-catalog functions keep their behavior.

1. `load_destinations(path=None)` reads a fresh list from the bundled JSON file or an explicit test file. It rejects unsupported data versions, missing fields, duplicate IDs/names, unknown currencies, and malformed profile records. Reading a fresh file avoids a caller accidentally changing a cached shared list.
2. `get_destination(name, profiles=None)` ignores surrounding spaces and letter case, finds the canonical profile, and returns a copy. An unsupported destination raises `UnsupportedDestinationError`, which is a `ValueError` subclass. Changing the returned copy does not change the supplied profiles.
3. `validate_release_catalog(places, profiles=None)` checks supplied place records and returns `None` when they pass. It raises `ValueError` for malformed data; it does not silently repair costs, change currencies, or mutate the records.

Validation checks stable unique IDs; known cities/categories/tags; matching currency; exact nonnegative cost text; nonblank descriptions/estimate notes; HTTPS source references; calendar-valid review dates; and reviewed location fields. It reuses the previously tested Maps helper to check that the address and optional coordinates can produce a usable link. It makes no network request.

“Validation” here means checking structure and consistency. A nonblank address and a valid source URL still require a person to review the source and confirm the real place. The separate release-data checks require eight reviewed places, two food options, and four interests per city. Passing schema validation does not satisfy those coverage or factual-review requirements.

## Worked examples

In the project's Python environment:

```python
from catalog import get_destination

get_destination("  tokyo, japan  ")
# {'id': 'tokyo-jp', 'name': 'Tokyo, Japan',
#  'country': 'Japan', 'currency': 'JPY'}

get_destination("Lagos, Nigeria")["currency"]
# 'NGN'

get_destination("Atlantis")
# raises UnsupportedDestinationError
```

The lowercase Tokyo example becomes the same canonical Tokyo profile. Atlantis is rejected because it has no supported profile; the app does not guess a currency or invent recommendations for it.

For a place in Tokyo, a record marked `currency: "EUR"` is rejected. A missing cost is also rejected; it does not become a free attraction. A properly recorded free JPY activity can use exact cost text `"0"`, while a free EUR activity uses `"0.00"`.

The previous practice question has the same underlying rule: USD has cents, so `300.50` is accepted. This project uses whole-yen JPY amounts, so `300.50` is rejected for JPY and `300` is accepted. You can use these worked answers while learning; they are not a gate to continuing the project.

## Verification and SDD order

Before application changes, the existing 80 catalog-related cases produced **28 passes and 52 expected failures**. One additional integration test was then added to exercise the default bundled-profile loading/lookup path for all six cities. It also failed before implementation: **28 passes and 53 failures across 81 cases**. Existing assertions were retained.

After implementation:

| Check | Result |
| --- | --- |
| City helpers and original catalog tests, excluding the unfinished real-place coverage checks | **75 passed**, 6 deselected, in 0.49 seconds. |
| Full suite, including those six coverage checks | **1,206 passed, 64 expected remaining failures**, no errors/skips, in 18.56 seconds. |
| Original Phase 7 tests | All **943 pass**. |
| Previously passing tests that regressed | **0**, compared with the prior helper implementation's full report. |
| Remaining real-place release checks | 6 failures: Paris still has seven original records; the other five cities still need their reviewed places. |
| Remaining v2 snapshot/storage checks | 58 failures for the unfinished versioned saved-trip feature. |

All remaining failure groups were inspected. The focused selection deselects future data checks only to describe this slice; the full run includes every case and still exits with status 1 for unfinished requirements. No skips or `xfail` markers were added. No prior tests were removed or weakened.

Ignored evidence: `.tmp/phase8-catalog-red.xml`, `.tmp/phase8-catalog-green.xml`, `.tmp/phase8-catalog-full.xml`, and `.tmp/phase8-catalog-source-baseline.json`.

Of 55 pre-edit fingerprinted application/data/asset/test/dependency files, only `catalog.py` and the intended test file changed. `data/destinations.json` is new. The original `data/places.json`, frozen Paris examples, existing form and templates, currency/Maps helpers, appearance behavior, and dependency files retain their hashes. Tests used fresh validated temporary directories and isolated databases. No real user data, browser preferences, native installation, or package artifact was changed.

## Concepts to understand

- **Data modeling:** Separate the city's shared information from the details of each place.
- **Canonicalization:** Different capitalization or edge spaces can identify the same city.
- **Validation:** Reject inconsistent data before it becomes a recommendation or cost total.
- **Copies and mutation:** Return an owned profile so one caller cannot accidentally alter shared data.
- **Unit and integration tests:** Supplied fixtures test the rules; the added default-loading check tests their connection to the bundled profile file.

The recommendation scores and greedy itinerary algorithm are unchanged. These city-data helpers support the AI-related flow; they do not train a model or prove restaurant suitability.

## Guided practice

Open [data/destinations.json](../data/destinations.json), find Tokyo, and look at its `currency` field: **JPY**. Then find Lagos: **NGN**. That is the exact information the future form will use to choose its allowance label and input rules.

If you want to try the Python example, call `get_destination("  tokyo, japan  ")` and compare the result with the worked answer above. Continuing the project does not depend on completing the exercise.

## Next step

Define and validate the remaining preferences/draft/server and actual planner-JavaScript tests, including explicit acknowledgement when an entered amount changes currency. Prepare legitimate old-test migrations onto the frozen Paris examples before activating the reviewed expanded dataset and new-save defaults. Then integrate the cities, form, saved content, and visible Maps actions. Photos and Windows/Android downloads retain their own tests and real-artifact checks.

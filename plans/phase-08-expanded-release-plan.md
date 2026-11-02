# TripPlanner — Phase 8 Implementation and Test Plan

**Approved scope:** [Six-city local-first release, photos, external Google Maps buttons, Windows and Android downloads](../specs/phase-08-expanded-release.md). The user selected Track A and no-key Maps links on 2026-10-26. Embedded maps, worldwide live discovery, API accounts/billing, hosting, and app-store submission are excluded.

**Current checkpoint:** Classroom handoff verified on 2026-11-01 with **1,596 passing pytest cases**, the previously verified Windows demo.2, and an Android debug APK with recorded Android 15 x86_64 offline/native-tap, restart, and appearance acceptance. See [final checks](../docs/final-release-checks.md), [Android evidence](../docs/phase-08-android.md), and [presentation walkthrough](../docs/presentation-walkthrough.md). The PowerPoint has 17 slides with notes; the Word guide has 16 rendered/reviewed pages. Physical ARM64 phones, other Windows hosts, and public release/store approval remain verification limits. No GitHub repository was uploaded.

**Verification history:** The test-definition baseline passed all **943 existing cases in 16.41 seconds**; the historical full red run had 307 failures in 17.17 seconds. The first implementation slice reproduced 197 failures/41 passes in its focused baseline, then passed all 238 focused cases in 0.27 seconds. Its full run has 1,159 passes/110 expected remaining failures in 16.57 seconds. Evidence is listed in the linked reports. Runs used fresh validated temporary directories and the existing Python environment; no tooling was installed.

**City-data verification:** After defining the default-profile integration case, 81 relevant cases produced 28 passes/53 failures before application changes. Implementation passes 75 relevant cases in 0.49 seconds; the six remaining release-data checks are included in that delivery's full run, which has 1,206 passes/64 expected remaining failures in 18.56 seconds. Evidence: `.tmp/phase8-catalog-red.xml`, `.tmp/phase8-catalog-green.xml`, `.tmp/phase8-catalog-full.xml`.

**Latest server-form test verification:** The fresh pre-edit run reproduced 1,206 passes/64 expected failures in 16.76 seconds. After defining 181 form/draft/context cases, discovery finds 1,451 cases and the full run produces 1,209 passes/242 inspected missing-feature failures, no errors/skips, in 17.96 seconds. Three independent fixture/helper checks pass separately. Evidence: `.tmp/phase8-form-baseline.xml`, `.tmp/phase8-form-health.xml`, `.tmp/phase8-form-red.xml`, `.tmp/phase8-form-source-baseline.json`.

## 1. What we will deliver

### Completed 1 November web deliveries

The user's request to move through three phases was implemented as validation/draft/context logic; complete multi-city web planning with frozen v2 saves; and visible Maps/external-navigation verification. The actual planner script is exercised by `tests/planner_harness.cjs` and `tests/test_planner_script.py`; full six-city save/reopen/Maps checks are in `tests/test_release_journey.py`. They were defined and observed red before the corresponding production edits. `tests/conftest.py` explicitly scopes the original regression modules to frozen seven-place math with QA-only location metadata. No test cases were skipped or removed. See the [detailed verification and migration report](../docs/phase-08-three-phases.md).

The browser data contract is the local `destination-data` JSON mapping canonical city names to currency, precision, maximum minor units, actual interests, and actual pace choices. The client uses integer minor units and DOM text nodes, never rewrites a signed context, and leaves confirmation authoritative on the server. Historical v1 JSON/hash tests remain unchanged. New live requests explicitly supply city profiles and create v2 snapshots. The photo-manifest/helper contracts and pre-implementation tests are complete in the linked bounded photo plan.

The earlier red checkpoints below remain history. The web/photos and native classroom demo gates, final regression, and presentation handoff are now recorded in the current checkpoint and final reports.

The traveler chooses Paris, Lagos, London, New York City, Tokyo, or Cape Town; sees interests and currency appropriate to that city; gets explained recommendations and a useful daily plan; views photographs; opens a spot in Google Maps; and saves/reopens the reviewed result.

The same web experience will be packaged for Windows and Android. Core planning uses bundled data and works offline; external Maps/source links need connectivity. Neither a worldwide search field nor a browser shortcut substitutes for the approved dataset or actual native package.

Build gradually. Keep the current runnable app available, do not expose half-configured cities using the wrong currency, and do not combine packaging success with feature correctness into one unsupported claim.

## 2. Sequence and gates

1. **Specification — approved:** Coverage and map mode are settled in the linked spec.
2. **Planning — complete:** This file defines architecture, responsibilities, tests, dependencies, and delivery order.
3. **Test definition — complete for the delivered slices:** Web, photos, Windows, and Android staging/runtime tests preceded their corresponding integration. The original Paris examples and v1 histories retain their assertion meanings. Native emulator instrumentation supplies separate installed-artifact evidence.
4. **Implementation — classroom handoff verified:** All 1,596 pytest cases pass. Windows has its named extracted-app acceptance journey. The Android debug APK passes the recorded emulator offline/restart/appearance gates. Presentation files and final checks are complete within the explicit physical-device, other-host, and public-release limits.

Later packaging slices also require their own tests defined before launcher/staging behavior is implemented. Ordinary tool permissions still apply to downloads, SDK setup, and agreements. No extra product-scope approval is needed for these approved slices, but material scope changes need a revised spec.

## 3. Main responsibilities

| Area | Planned responsibility |
| --- | --- |
| `data/destinations.json` — new | Stable city profiles: ID, canonical display name, country, currency. No live exchange rates. |
| `data/places.json`, `catalog.py` | At least eight reviewed places per city, stable legacy Paris IDs, validated city/currency/location/provenance fields, and derived supported choices. Preserve a supplied-catalog seam for unit tests. |
| `currencies.py` — new; `money.py` | Six allowed currencies, precision/ranges, exact parsing/formatting, integer minor-unit preview contract, and legacy EUR-compatible interfaces. |
| `preferences.py`, `drafts.py` | Server-owned destination currency, explicit amount acknowledgement when currency changes, supported interests/pace, and safe versioned drafts. |
| `recommendations.py`, `itinerary.py` | Existing explainable scores and greedy scheduling, operating on consistent exact destination-currency values. No network calls or map-based route claims. |
| `maps.py` — new | Pure validated location-to-Google-Maps URL helper; no provider API, geocoding, HTTP request, or credential. |
| `snapshots.py`, `saved_trips.py` | Versioned snapshot compatibility, frozen reviewed currency/location, preserved v1 data, immutable IDs/content, and unchanged duplicate/transaction guarantees. Avoid a repository schema change unless demonstrably needed. |
| `app.py` and templates | Join prepared data, consistent currency labels, map links, photos, useful errors, and shared layout. Saved reads stay catalog-independent. |
| `static/js/plan.js` | Destination-aware choices/currency preview and honest amount-change interaction; server forms remain authoritative. |
| `data/images.json`, `static/images/`, credits document — new | Local verified/licensed photos keyed by stable place/destination IDs, attribution, alt text, responsive dimensions, and fallback behavior. Separate display assets from snapshot fingerprints. |
| Shared CSS and templates | Image/card polish in both themes, readable captions, reserved image space, visible focus, responsive layout. Preserve appearance behavior. |
| `app_runtime.py`, launchers — new | Resource versus writable-data paths, stable per-install settings, owned service lifecycle/readiness, and safe native external navigation. |
| `packaging/` and platform requirements — new | Explicit bundle manifests, Windows build configuration, Android project, versioning, and reproducible artifact staging. Never package the working directory indiscriminately. |
| Tests and guides | Test-first evidence for each slice, installed-artifact evidence, student tasks, launch/download instructions, limitations, and demonstration fallback. |

Names for new small modules are implementation contracts, not a new framework or API service. Keep domain modules usable without Flask/native dependencies.

### Foundation API contracts fixed by the first test batch

- `currencies.get_currency(code)` returns immutable metadata with `code`, integer `precision`, and Decimal `quantum`, `minimum`, `maximum`; unsupported/noncanonical codes raise `ValueError` rather than guessing EUR.
- `money.parse_budget(raw, currency=code)`, `daily_allowance(amount, days, currency=code)`, and `format_money(amount, currency=code)` preserve existing EUR defaults. The parser accepts text only, with approved precision and limits.
- `catalog.load_destinations(path=None)` loads `{ "version": 1, "destinations": [...] }` and returns fresh profile records. Profiles have `id`, canonical `name`, `country`, and `currency`. `get_destination(name, profiles=None)` returns a canonical copy or raises `ValueError`; `validate_release_catalog(places, profiles=None)` returns `None` for valid supplied data or raises `ValueError`.
- Place records use `currency`, `reviewed_on`, `cost_note`, exact `estimated_cost` text, and `location` containing `address`, `source_url`, `reviewed_on`, plus optional valid paired `latitude`/`longitude`. Coverage/real-source review are separate release-data requirements.
- `maps.build_maps_url(name, destination, location)` returns a fixed HTTPS search URL or `None`. Address queries preserve name/address/city; coordinate queries use the exact `latitude,longitude` pair. An optional permitted `place_id` becomes `query_place_id`. URL construction is local and nonmutating.
- `snapshots.build_snapshot(preferences, catalog)` must produce self-contained v2 content for new currency-bearing preferences. Independent v2 oracles define currency/location and nested money precision; existing load/dump/fingerprint/repository interfaces preserve genuine historical v1 content.

The signed form-context contracts are defined below. Browser page-data/actual-JavaScript and asset-manifest gates have since been completed; their linked web/photo reports preserve evidence. Native-runtime and packaging contracts still need tests before their implementation. The [server-form checkpoint](../docs/phase-08-form-testing.md) is historical.

### Form/draft test-batch contracts

The next batch defines server-side behavior before form changes. It does not yet activate the live dataset or define the actual planner-JavaScript harness, photo, native, or complete save/detail/Maps HTTP tests.

- Extend `validate_trip_preferences(form, catalog=None, *, profiles=None)` with supplied profile data for isolated tests. New normalized preferences include server-derived `currency`; ignore a submitted currency label. Require an available catalog destination and matching profile, destination-specific interests/pace, native precision/range, and preserved raw answers on error.
- Extend `load_draft(stored, catalog=None, *, profiles=None)`. New currency-bearing preferences serialize as version 2 with exact native money text. Genuine v1 Paris drafts decode explicitly as EUR into current normalized preferences without mutating the input. Malformed, wrong-city/currency, stale-option, or unknown-version drafts return `None`; arbitrary old-city fixtures do not acquire guessed currencies.
- Add a session-bound `currency_context.py` helper. `issue_currency_context(currency=None, *, confirmation_required=False)` returns signed text. `read_currency_context(token)` returns `{version: 1, currency: code-or-None, confirmation_required: bool}` or raises `ValueError`. Use the existing ItsDangerous dependency, app secret, salt `tripplanner.currency-context.v1`, and a separate session `currency_context_nonce`. The signed payload includes that nonce. Validate types, known currency, signature, and browser-session binding. Keep it separate from CSRF, drafts, and snapshot fingerprints. Existing open-tab contexts remain valid in the same session.
- An initial form with no selected city has a neutral currency context (`None`, no pending confirmation), not an implied EUR amount. Selecting its first city establishes the unit. A prefilled/edit/error form carries the currency actually shown. Visible help explains the current code; native input bounds/step follow that code.
- POST the hidden `currency_context` with the ordinary CSRF token. Reject invalid/missing/cross-session context with HTTP 400 and preserve the valid draft. A currency-changing POST redisplays raw answers with a new signed target-currency context whose `confirmation_required` is true. It must not accept a checkbox forged on the earlier nonpending form.
- The review form contains a labeled `confirm_currency_change` checkbox (`id="confirm-currency-change"`, value `on`), with the target currency in its label/help. Only an explicit checked submission under the matching pending context can complete the change. A further change to another currency creates a new review state. A missing acknowledgement redisplays the error and preserves the previous valid draft. Editing the amount in the same reviewed currency is permitted; this is a unit acknowledgement, not a conversion.
- This bounded server workflow supports ordinary HTML posts without JavaScript and avoids an extra confirmation API. Future JavaScript must enhance the same server workflow; its actual execution tests remain a required gate before client code changes. No claim of detecting human intent or entry order is made by the signed token.
- Test six-city form/recommendation currency labels, v2 session content, native bounds, amount precision, explicit review/recovery, and separate CSRF/context protection using synthetic QA travel records and real Flask routes. These fixtures establish behavior, not reviewed travel facts or a released multi-city catalog.

Implementation detail uses [ItsDangerous URL-safe serialization](https://itsdangerous.palletsprojects.com/en/stable/url_safe/), already supplied with Flask; no new dependency or credential service is needed. Legitimate old-test migrations remain required before changing default normalized shapes, serializer versions, or form token requirements. Preserve historical v1 snapshot/read assertions separately.

## 4. Data and money contracts

### City profiles and catalog

Use these canonical choices and currencies: Paris, France — EUR; Lagos, Nigeria — NGN; London, United Kingdom — GBP; New York City, United States — USD; Tokyo, Japan — JPY; Cape Town, South Africa — ZAR. Stable machine IDs must not depend on translated labels or display ordering.

Keep `load_catalog()` returning place records so existing callers need not be rewritten around a new service. Introduce explicit profile/catalog validation with a supplied-data seam. Published data must have unique stable IDs, known city/category/tags, a matching currency, finite nonnegative exact cost text, reviewed source/provenance, and a usable verified address. Optional coordinates must come as a valid pair and pass finite/range checks. Do not silently make a malformed record free or move it to another city.

Research factual place/address details from appropriate primary sources during implementation. Record which cost is an illustrative estimate rather than an official admission/menu price; include review dates without suggesting a live-price feed. At least two restaurants/food options, four meaningful interests, and eight places per city are release-data checks, not randomly generated fixture expectations.

Retain the seven original Paris IDs. Freeze the original seven-place data as a test-only fixture **before** modifying the live catalog so the EUR 103.00 / EUR 197.00 sample and existing scoring/money/security expectations remain directly testable.

### Exact currencies

Create a small immutable registry for the six codes. EUR retains its current bounds; the other currencies use the approved 1,000,000,000-unit ceiling and one-minor-unit minimum. JPY has precision zero; the other five have precision two.

Extend money helpers with an optional currency argument while keeping existing EUR defaults where necessary for old callers/fixtures. New live paths always pass server-derived currency explicitly. Reject signs, exponent notation, separators, symbols, non-finite amounts, excess precision, booleans masquerading as numeric metadata, and out-of-range values. JPY form input uses whole digits, not an automatically rounded fractional amount.

Use Decimal constructed from text for Python and safe integer minor units for the optional browser preview. Preserve the eligibility and day-cost comparison `cost * days <= allowance`; rounded daily display must not grant an extra minor unit. Include code labels rather than ambiguous dollar/yen symbols alone.

### Changing destination and budget

The selected city profile—not a submitted `currency` field—determines the trip currency. Preserve raw invalid inputs and the existing valid draft until a valid form is accepted.

Track the currency in which the displayed amount was entered. A destination change with a different currency must invalidate the old preview and request explicit confirmation/re-entry. The no-script path must reject the first unacknowledged mismatch and render the newly labeled amount/confirmation clearly; it cannot simply relabel and accept it.

Use a server-verifiable form context for the previously rendered currency and any required confirmation state; keep it separate from the existing CSRF and snapshot-content tokens. A forged/missing context must not bypass the acknowledgement contract. It is not an exchange-rate service. Confirmation authorizes interpreting the user's chosen amount in the new currency, not a claim that it has equivalent value.

JavaScript can update available interests/pace and display rules from a small local page-data block. Preserve selections still supported, explain cleared unsupported choices, and never create guessed tags. Without JavaScript, the server redisplays destination-specific options and retains actionable answers/errors.

## 5. Draft and snapshot compatibility

- Introduce a version-2 normalized draft carrying canonical destination/currency. Handle genuine v1 Paris drafts as EUR explicitly; reject malformed/inconsistent versions rather than guessing. Do not treat an old unknown-city fixture as a new published currency profile.
- New snapshots use a version-2 contract with the reviewed currency, exact money text at its precision, and frozen valid place locations. Continue decoding genuine v1 snapshots as their original EUR data without rewriting stored JSON or fingerprints.
- Version-2 validation must use only stored data and the stable currency-format rules, not today's catalog, recommender, or scheduler. Validate consistency of repeated recommendation/scheduled items and their money/location copies.
- New saves are created under v2; repeated identical v2 title/content reuse the row. Existing v1 IDs/JSON/hashes/times remain unchanged. A deliberate v1-to-v2 new save is not a silent rewrite of the older row.
- Generate a map URL at display time from frozen location data. URL-format markup changes must not change the fingerprint. A genuine changed reviewed address/cost is content and still participates in stale-form protection.
- Store photo/credit selection in the display-asset manifest keyed by stable place ID, **not inside the travel-content fingerprint**. Saved rendering may use this manifest but must never load today's travel catalog; unavailable/retired assets get an honest fallback.
- A v1 record lacking location metadata shows location unavailable rather than looking up and silently adding today's coordinates. No migration may reset a corrupt file or discard an unreadable record.

If the existing SQLite table can store both JSON versions, retain it. Any necessary schema migration needs separately defined non-destructive tests and documented recovery before its implementation.

## 6. Maps and image presentation

### External Maps buttons

Add `build_maps_url(name, destination, location)` as a pure helper returning a safe URL or `None` for unavailable location data. Build a fixed HTTPS `www.google.com/maps/search/` URL with `api=1` and properly encoded reviewed place/address information; use verified coordinate pairs or permitted Place IDs when available. Never accept an arbitrary map URL or turn missing data into a vague claimed precise pin.

Test Unicode, punctuation, ampersands, newlines/unsafe input, invalid/missing coordinates, boundary coordinates, length limits, and malicious scheme/host-like text. Query text must remain encoded data, not executable HTML or a replacement URL.

Use visible **View on Google Maps** text with place-specific accessible naming, ordinary text addresses, and clear “opens separately” guidance. In browsers use a separate browsing context with opener protection. Native wrappers open external links through the OS; remote pages must not receive a privileged native bridge. No Google request occurs just because the page loads, and there is no SDK/key/iframe installation.

The documented contract is [Google Maps URLs](https://developers.google.com/maps/documentation/urls/get-started). Per-place location display is not route optimization, a live safety/availability check, or a GPS feature.

### Photos

Prepare a local manifest containing each asset's destination/place ID, filename, creator/source/license links, factual alt text, intrinsic dimensions, and whether it is a real-place or explicitly representative image. Verify the source image and redistribution terms per file; do not assume a search thumbnail grants package redistribution rights. Do not fetch/store Google Places photos as permanent bundled assets.

Reuse a suitable licensed destination image for its matching hero/card where appropriate. Representative restaurant/food imagery must be labeled as such. Prefer optimized WebP/JPEG with a practical initial budget of roughly 200 KB per main image and smaller thumbnails; investigate exceptions, do not blur an image to meet an arbitrary number. Reserve dimensions, lazy-load below-fold photos, and keep above-fold imagery useful without layout jumps.

Keep the form focused on answering questions. Apply semantic surfaces/borders/captions in both themes; no image inversion, large unrelated background collage, new external font service, tracking pixel, or decorative whole-page transition. Missing assets must leave names, map actions, estimates, and forms usable.

## 7. Pytest and test-definition strategy

### Baseline and isolation

Before test edits, fingerprint production/assets/dependency files and current tests. Use a fresh validated `.tmp` pytest base and per-test databases. Do not touch the current preview, its entered answers, the real collection, or its browser preferences to create evidence.

During test preparation, scope old live-data assertions to the frozen seven-place fixture where that preserves their original purpose. Add separate actual-release-catalog checks. Preserve existing security, decimal-boundary, duplicate, transaction, historical-read, and appearance assertions; document each legitimate fixture/shape migration. No skips, xfails, broad exception-catching, or silent assertion removals may stand in for missing behavior.

### Planned checks

| Test area | Important cases |
| --- | --- |
| Currency/domain | All six precision/range boundaries; wrong code; JPY fractional rejection; exact rounded-versus-affordable boundary; free costs; huge/malformed input. |
| Catalog/profile | Six real approved cities; eight places/two food choices/four interests each; stable Paris IDs; unique IDs; source/review metadata; currency mismatch; invalid locations; unknown prices never free. |
| Preferences/drafts | City-owned currency; forged submitted labels/context; currency-change acknowledgement; raw answer retention; dynamic options; v1 Paris compatibility; malformed/stale v2 recovery. |
| Recommendations/itinerary | Correct city/currency only; unchanged scores/ties; exact daily caps; no repeats; legitimate empty/partial results and missing-meal notices for each city. |
| Maps helper | Fixed HTTPS host/path/API version; proper encoding; exact reviewed location; optional coordinate pair handling; invalid/missing data; no network calls. |
| Snapshots/storage | v1 byte/hash preservation; v2 currency/location validation; nested money precision; new duplicate/stale behavior; image/markup changes not content changes; missing live catalog; unreadable records isolated. |
| HTTP/forms | Consistent currency everywhere; real form/save/list/detail flow per city; correct map links; external-link semantics; no Google embeds/credentials; CSRF; usable recovery; old snapshot fallbacks. |
| Actual planner JavaScript | Execute the production preview/options code through a bounded test-only Node context. Cross-check examples against independent integer/Decimal expectations; do not let the harness choose currency/amount results. |
| Images/style | Manifest-to-local-file integrity, dimensions/alt/credit/license metadata, no remote image dependency, missing-image fallback, both palettes, focus/reduced motion, no color-transition regression. |
| Native staging/runtime | Allowlisted bundle contents, writable data versus resource roots, owned startup/readiness/shutdown, port collisions, preserved settings, safe external URLs, and no private data/secrets/tests in release artifacts. |

Imports/asset reads for future modules belong inside tests or safe fixtures, not at discovery time where absent files break collection. Test helper health independently. Expected missing-feature failures must be distinguished from environment, setup, dependency, fixture, and unrelated application failures.

Record discovery and actual pass/fail/error/skip counts after inspecting every failure group. There is no promised new test count. Only then implement the corresponding slice. Native/platform tests complement pytest; they do not replace its unit/integration gate or get falsely claimed by it.

## 8. Small implementation deliveries after tests

### A. Six-city data, money, and historical compatibility

Implement the profiles/money contracts and versioned drafts/snapshots, verify the reviewed dataset, then integrate the destination-aware form, recommendations, itinerary, and saved views together. Do not expose the expanded selector while another layer still interprets every amount as EUR. Check legacy Paris examples and historical reads before considering the multi-city slice usable.

**Student focus:** Data versus logic, canonical validation, Decimal/minor units, versioned data, and preserving a working regression example.

### B. View on Google Maps

Integrate the pure helper, safe link markup, and frozen-location behavior on live/saved cards. Test actual spots opening separately without replacing the current page. Keep this a small complete enhancement, not an entry point to provider APIs.

**Student focus:** URL encoding, trusted structure/untrusted query data, external navigation, and offline fallbacks.

### C. Photos and finishing the web interface

Add reviewed local assets/credits, destination-aware home messaging and photos, thumbnails, and both-theme styling. Audit all remaining Paris/EUR-only copy, including meta descriptions, headings, field help, estimates, notices, empty states, and recovery messages. Keep historical Paris records' original words intact.

**Student focus:** Accessible images, responsive layout, licensed local resources, semantic colors, and data-driven presentation.

### D. Windows download

Preferred design: the Flask app hosted by a small owned local WSGI runtime inside a pywebview window, bundled with PyInstaller as a one-folder portable release first. One-file/installer polish is optional after the actual portable package works; it is not a substitute for clean launch/data tests.

Separate runtime/native/build requirements from `pytest` and Node development helpers. Use an isolated packaging environment and pin the tested versions; do not silently replace/downgrade the user's working Python. Check current Python 3.14 dependency support first; a separate compatible build interpreter requires normal installation approval if needed.

Use explicit data paths from the OS user's application-data folder, stable local secrets/profile settings, clear startup errors, and bounded readiness/shutdown. Add a per-launch local-service access guard for packaged mode, including private GET routes; loopback binding alone is not an account/security boundary. Keep the ordinary development website's expected workflow intact.

Use persistent native profile settings and, where a fallback port changes the origin, a narrowly scoped enum-only appearance persistence adapter. Do not copy arbitrary browser storage or expose generic file/command bridges. Open source/Maps links externally; restrict privileged rendering to the app's own trusted content.

**Student focus:** An application needs a runtime and writable data, not just an `.exe` filename. See [pywebview packaging](https://pywebview.flowrl.com/guide/freezing) and [PyInstaller](https://pyinstaller.org/en/stable/).

### E. Android download

Preferred candidate: a small Android WebView host with embedded Python through Chaquopy/Gradle, running the same local Flask/domain code on the phone. It is not a WebView pointing at the laptop. [Chaquopy documents a Gradle integration, available Python runtimes, ARM64/emulator ABIs, and bundled data files](https://chaquo.com/chaquopy/doc/current/android.html). Validate Flask/native dependency compatibility before selecting/pinning the final build matrix.

This candidate permits a Windows-hosted Gradle build without assuming WSL exists. A python-for-android WebView bootstrap is a documented alternative, but switching to its Linux/WSL toolchain must be deliberate, not a surprise installation or an excuse to claim the APK is complete. See [python-for-android](https://python-for-android.readthedocs.io/en/latest/quickstart.html).

Plan ARM64 for the intended device and an x86_64 emulator build when needed. Use Android 10+ as the initial verification target, with an updated System WebView; record the actual tested versions and adjust only after checking the presentation device. Do not advertise every Android/CPU version.

Bundle resources from an explicit staging manifest, set database/settings to Android app-private storage, guard the owned loopback service, handle lifecycle/back navigation, and keep external Maps/source pages outside the privileged WebView. Any loopback cleartext configuration must be narrow, not a global permission to load arbitrary insecure remote content. No GPS or broad file-storage permission is needed for this scope.

Build and identify a demo APK first; do not label it a public release. Release signing and keystore ownership are handled explicitly, outside source control and logs. SDK agreement acceptance and installation steps require their normal owner/permission handling.

**Student focus:** Phone binaries have their own runtime, CPU/OS constraints, storage, lifecycle, and signing. Sharing Python logic does not remove Android build/device tests.

### F. Final demonstration handoff

Run the final regression suite and real installed-app journeys, document actual support/limits, include image credits/privacy notes, prepare a short predictable demonstration, and provide a backup walkthrough/recording. Explain existing rule-based recommendation/scheduling clearly; do not add a chatbot or trained-model claim merely for presentation polish.

## 9. Toolchain preflight findings and limits

Read-only checks at this checkpoint found:

- The existing project environment runs Python **3.14.7** and passes the 943-case suite.
- pywebview, PyInstaller, Waitress, and Buildozer are not installed in that environment.
- Java, adb, Gradle, and PyInstaller commands were not found on the inspected PATH. This is not proof that no alternative installation exists anywhere.
- The conventional user Android SDK directory was absent and neither `ANDROID_HOME` nor `ANDROID_SDK_ROOT` was configured.
- `wsl.exe` exists but reports that WSL itself is not installed. Do not start installing WSL for the preferred Gradle candidate without a reason and permission.
- No Windows/Android package was built, no emulator was launched, and no phone's Android/CPU version was inspected.

Before native implementation, establish a supported interpreter/native-dependency/Java/Gradle/SDK matrix in isolated build state, check asset extraction and SQLite on the real target, and define corresponding runtime/staging tests. These prerequisites do not stop the web/data/Maps test-definition work. They do prevent a credible promise that both downloads will be finished today before setup/testing.

## 10. Real verification and release evidence

Use a separate QA origin and temporary databases, not the user's current filled form or collection. Reset viewport overrides and close only owned QA processes/tabs afterward.

- For each city, submit a short realistic trip; check native currency/precision, explanations, daily/trip costs, save/reopen, duplicate behavior, and historical independence.
- Exercise currency changes with an entered amount, invalid input, unsupported options, and application scripts blocked. Verify explicit acknowledgement works in both script/no-script flows.
- At 360px and desktop width, check both themes on home, form, recommendations, itinerary, collection/detail, and recovery. Inspect actual image crops, meaningful alt text, focus, selected/invalid fields, caption contrast, overflow, and image-failure fallbacks.
- Open representative named places in Google Maps on Windows and Android, including Unicode names; confirm correct identity/location, external behavior, and preserved TripPlanner state. Do not count a syntactically valid URL as proof of a correct place.
- Simulate unavailable internet without changing the user's global security/network settings; use controlled QA fixtures where possible. Planning/saving/photos must work locally, with honest external-link limitations.
- Check generated bundles for only allowlisted app/resources/dependencies. Verify no user's database, signing key, secret, virtual environment, test fixture, `.tmp`, or source-control state is redistributed.
- Launch Windows from an extracted clean folder/profile outside the checkout, with no development Python on PATH. Test start/save/close/relaunch, port occupation, settings persistence, safe external pages, and release/data-directory separation. Confirm the artifact's actual architecture and signing/test status.
- Install the actual APK on a recorded emulator/device. Test offline planning, app restart, SQLite data, System/Light/Dark, image assets, external Maps fallback, back navigation, and lifecycle. If physical-device evidence is unavailable, say so; an emulator-only demo is not a claim of all-device readiness.
- Keep native packages marked incomplete until their artifacts and checks exist. Building is not installing; installing is not proving save/restart works; a PWA shortcut is not an APK.

The final report records actual pytest counts, any legitimate old-fixture migrations, source/data changes, platform versions/architectures, artifact names/checksums, signing status, browser/native evidence, and remaining limits. No predetermined count or “works for everyone” claim is used.

## 11. Student handoff and next action

At each completed slice, explain what changed, why it exists, how the code works, and the relevant concept. Practice comparing two cities' currencies/interests, explaining one match and one itinerary gap, opening/recovering a map link offline, switching theme without changing a trip, and showing where each installed app keeps saved data.

**Next action:** Rehearse the recorded demo with the completed presentation materials. The Android emulator gate and final class-project handoff are recorded in the current checkpoint above. Preserve v1/v2 history and the passing 1,596-case suite. Do not infer public/all-Windows release readiness from one host. Port-5000 startup was previously rejected by automatic approval review; use the owned web QA preview on port 5001 without the main server/database.

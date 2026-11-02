# TripPlanner — Phase 8 Expanded Release Specification

**Status: APPROVED SCOPE — classroom handoff verified on the recorded platforms.** On 2026-11-01 the six-city web flow, v1/v2 history, external Maps, 18 licensed photos, Windows demo.2, and an Android debug APK are delivered with **1,596 passing pytest cases**. Windows retains its verified extracted-app journey on Windows 11. The Android 15 x86_64 emulator passes the actual-tap offline journey, unchanged saved row and Dark after restart, System Light/Dark, and manual Light override. The handoff includes a 17-slide PowerPoint and 16-page Word guide. See [final checks](../docs/final-release-checks.md), [Android evidence](../docs/phase-08-android.md), and [presentation walkthrough](../docs/presentation-walkthrough.md). Physical Android phones, other Windows hosts, a deliberately disconnected Windows journey, and public-store release remain verification limits. MIT/source preparation is local, with no GitHub upload. No worldwide or all-device completion is implied.

**User request:** Support both Windows and Android downloads; add suitable photographs and Google Maps locations; expand beyond Paris and make personalization useful to a wider audience. Presentation is next week. Same-day completion is a target, not a verified delivery promise.

**Existing foundation:** [Product specification](../SPEC.md), [Phase 7 verification](../docs/phase-07-implementation.md), and [learning guide](../docs/phase-07-learning.md). The planning checkpoint freshly verified all **943 existing cases passing in 18.74 seconds** using isolated temporary databases. No Phase 8 functionality is claimed by that baseline result.

## 1. Product direction and honest boundaries

TripPlanner should welcome travelers with different interests, budgets, paces, and destinations. It must not claim that every place, price, language, accessibility need, dietary requirement, or personal taste is supported merely because an app can be downloaded internationally.

Paris was the initial seven-record learning dataset, not a permanent geographic restriction in the recommendation architecture. Supporting another city requires credible places, estimates, location references, and usable interest coverage, not simply another item in a destination dropdown.

The worldwide product vision and the first verified release are different:

- **Selected first-release coverage (Track A):** A useful, explicitly listed multi-city catalog, bundled with the app. It works without a paid data service and supports offline core planning.
- **Not selected: worldwide discovery (Track B):** Search arbitrary destinations using an online place-data provider. This would require a provider, permitted storage/attribution behavior, credential ownership, funding limits where relevant, and a revised online/offline contract. It is excluded from this release and is not satisfied by a search box that returns no real data.

The user approved Track A. This does not authorize a claim of comprehensive worldwide coverage or a later unapproved switch to Track B.

An online place-data response is not automatically a redistributable offline catalog or permanent saved snapshot. For example, [Google Places policies](https://developers.google.com/maps/documentation/places/web-service/policies) impose storage and attribution requirements. Any Track B revision must reconcile its chosen provider's rules with TripPlanner's immutable historical snapshots before implementation.

## 2. Approved first-release destinations and interests

**Approved destinations:** Paris (France), Lagos (Nigeria), London (United Kingdom), New York City (United States), Tokyo (Japan), and Cape Town (South Africa). These are a starting set across regions, not a claim to represent every traveler or continent. Material coverage changes require a scope revision.

For Track A:

- Supply at least eight sourced places per approved city, with attractions/activities and at least two food options. Keep the existing seven Paris IDs stable.
- Each city must have meaningful coverage of at least four supported interests, with the actual available interests shown by the form. The global catalog should offer cultural/history/art, nature/views, food, and additional shopping/adventure options only where real records support them.
- Include free and paid choices where credible data supports them. Unsupported pace/preferences must not appear as working options.
- A typed destination search may filter the supported catalog, but an unsupported city must produce a clear coverage message, not invented recommendations. Display supported destinations before submission.
- Preserve deterministic explanations, interest/preference ranking, exact affordability checks, no repeated scheduled place IDs, and honest empty/partial itineraries.
- Do not duplicate attractions to make long trips look full. Limited data, missing meal options, and unused alternatives remain visible.
- Family-friendly is still a ranking preference, not a suitability guarantee. Do not infer dietary, medical, mobility, or safety suitability from photographs, popularity, or family tags.
- English is the release language. General translation and multilingual support require separate scope approval; do not advertise multilingual support.

### Required catalog information

Every released place must have a stable ID, destination/country, category, factual description, supported tags, a dated illustrative cost estimate, currency, source references, and a verified address/location reference. Where supplied, latitude must be within -90 to 90 and longitude within -180 to 180, finite, and reviewed against the named place.

Locations and factual descriptions must not be invented by an AI model. An unknown price is not zero/free. A location that cannot be verified must not receive a misleading map pin; omit it from the verified release set or explicitly show that its location is unavailable.

Source provenance and review dates must distinguish reviewed facts from illustrative estimates. Document data/image redistribution permissions. No scraping or unrestricted copying of Google Maps/Places content into the bundled catalog is assumed.

## 3. Budget and currency behavior

Global destinations must not silently retain an EUR label on local-currency prices or combine different currencies in a total.

- Destination currencies are EUR, NGN, GBP, USD, JPY, and ZAR respectively. Show the currency code on input, daily allowance, place costs, trip totals, errors, saved cards, and details.
- Use one destination currency per trip. Currency is derived from the selected destination, not trusted from a hidden form field.
- Do not implement live exchange rates, cross-currency conversion, or multi-city/multi-currency trips in Track A.
- Use exact decimal/minor-unit arithmetic and valid currency precision. EUR/NGN/GBP/USD/ZAR use two decimal places; JPY uses whole yen. Rounding must never make an unaffordable item eligible.
- Keep the existing Paris EUR 0.01–1,000,000.00 input range. For the new currencies, the software input ceiling is 1,000,000,000 native units; the minimum is one minor unit. These are validation limits, not exchange-rate conversions or travel-spending recommendations.
- If the destination/currency changes while an amount is entered, show the new currency and require explicit acknowledgement/re-entry before a successful submission. Never present relabeling the same number as a conversion.
- Existing saved EUR snapshots retain their original values, labels, fingerprints, IDs, and historical contents.

## 4. Google Maps locations

### Required baseline: no-key location links

Track A includes a visible **View on Google Maps** action for every place with verified location data, in recommendations and daily itinerary entries. New saved snapshots preserve enough reviewed location information to provide the same action without reading today's catalog.

- Use documented HTTPS Google Maps URLs with the required API version and properly encoded parameters. Prefer reviewed coordinates/address and place identity over an ambiguous bare name. Use a Place ID only when obtained through a permitted source.
- On Android, open the Google Maps app when supported/installed, otherwise the normal browser. On Windows, open the system browser. Do not replace the TripPlanner window or discard entered answers.
- Show the address in ordinary text so location information remains useful without loading a map.
- Clearly say that Google Maps opens separately. A link is not an in-app embedded map.
- Maps/navigation availability depends on connectivity, provider availability, region, and device behavior. If unavailable, the planner, budget, saved trip, and text address remain usable.
- No GPS permission, background location tracking, home address collection, or automatic sharing of a traveler's precise position is required. Opening a map sends the selected place request to Google; explain the external service briefly.
- A Maps view does not verify opening hours, accessibility, restaurant suitability, exact travel time, or optimal route order. Do not call a displayed itinerary route-optimized.

Google documents these cross-platform URLs as not requiring an API key: [Maps URLs](https://developers.google.com/maps/documentation/urls/get-started).

### Excluded map services

The user selected external Maps buttons. In-app embedded maps, custom multi-marker maps, Places discovery, geocoding APIs, route optimization, Cloud projects, API keys, and billing setup are **out of scope**. Do not add an iframe, request provider credentials, create an account, or install a Maps SDK for this release. A future embedded-map feature would need its own approved specification.

## 5. Photographs and visual polish

- Add a purposeful destination image on the home/discovery experience, place-specific photos on recommendation cards, and restrained thumbnails where useful in itineraries/saved cards. Keep input forms, cost summaries, and errors clear rather than decorating every surface.
- Real-place photographs must depict the named destination/place. Label representative food/atmosphere imagery explicitly instead of implying it depicts a particular restaurant. Do not pass generated landmark imagery off as photographic evidence.
- Use legally redistributable local assets with recorded source, creator, license, and required attribution. A license allowing website display does not automatically authorize redistribution in downloadable packages; verify both uses.
- Images must be optimized and sized responsively, with reserved dimensions, useful factual alt text where informative, and graceful missing-image fallbacks. Image failure must not break planning.
- Preserve the warm paper/forest identity. Use semantic surfaces/borders/captions in both themes; do not invert photographs or make body text depend on a busy image. Retain the existing contrast/focus/reduced-motion requirements.
- Bundle assets needed for the core experience. No third-party image requests, tracking pixels, or live image API dependency are required during ordinary planning.
- Historical snapshots must remain readable if an asset is retired. Saved reads must not regain a dependency on the live destination catalog just to render a picture.

## 6. Windows and Android downloadable applications

Both platforms are required targets. A mobile-friendly website or installed browser shortcut alone is not an Android APK, and a ZIP containing source files is not a packaged Windows application.

### Common application contract

- Preserve the current web app and reuse the understandable recommendation/scheduling core rather than maintain contradictory algorithms across devices.
- The selected Track A app is local-first on each device: bundled catalog, photos, core planner, and saved-trip storage. Google Maps and outbound source links remain online enhancements.
- Launch from an app icon without requiring a running development computer, a coding editor, a terminal, or a separately installed Python environment on the end-user device.
- If a local service is needed, start and stop only that app's owned service, bind it to loopback, handle startup readiness/failure clearly, and do not depend blindly on port 5000 being free or kill another process using it.
- Store saved trips and settings in an appropriate writable per-user/per-app location, outside bundled assets and temporary extraction folders. Preserve them across ordinary close/relaunch and supported updates. Uninstalling/clearing app data can remove them; do not promise otherwise.
- Keep appearance preferences consistent across relaunch. Packaging must account for browser-origin/profile changes instead of silently losing the user's choice when an internal port changes.
- Keep source links and Google Maps external; do not expose privileged native/Python bridges to untrusted remote pages. Do not disable OS/browser security protections to make packages run.
- Ship no user's existing SQLite collection, session cookies, signing secret, private key, or provider server credential. Separate installations must not share a public unprotected saved-trips database.
- Include version information, source/image credits, plain-language privacy/data limits, supported-platform details, and an honest offline/online feature description.

### Windows artifact

Provide a packaged Windows x64 application in a documented downloadable ZIP or installer. It must include the runtime/resources it needs, declare any browser-runtime prerequisite, and have a tested launch/save/close/reopen flow outside the development checkout.

Test a clean profile/environment without the development Python on PATH. Record the actual Windows version and architecture tested; do not claim all Windows versions. Disclose unsigned/test-build status if a trusted publisher signature is not available. Public-distribution trust/signing requirements remain a release gate, not an instruction to bypass warnings.

### Android artifact

Provide an installable, signed Android APK, with a documented supported Android/CPU range and WebView requirements. A debug/demo APK must be labeled as such; do not call it a verified public release.

The core planner must not point at the developer laptop's `127.0.0.1:5000`, require that laptop on the network, or pretend an offline screen cache runs the Python planner. The local-first runtime must operate on the Android device. A hosted-backend alternative is a material revision requiring HTTPS hosting, data isolation, operating costs, and privacy decisions before implementation.

Install and exercise the actual APK on an identified emulator/device, including launch, back navigation, safe external links, save/reopen, offline core behavior, both themes, startup failure, and restart persistence. Building an APK is not proof it installs or works. Record what physical-device testing remains if only an emulator is available.

The [plan](../plans/phase-08-expanded-release-plan.md) records candidate toolchains and actual preflight findings, not a validated native release. Official [pywebview distribution guidance](https://pywebview.flowrl.com/guide/freezing) documents packaging paths; [Buildozer](https://buildozer.readthedocs.io/en/latest/installation/) is an alternative requiring Linux/WSL setup, not an automatically chosen dependency. [Android signing](https://developer.android.com/studio/publish/app-signing) is required for installation. Tool downloads, SDK/license acceptance, signing-key ownership, compatibility, and available hardware still require their normal permission/testing gates.

## 7. Inclusive design, privacy, and honest availability

- Support keyboard navigation, readable text, clear labels/errors, screen-reader semantics, and responsive layouts on the website and packaged apps. Keep navigation/primary actions usable at 360px and desktop width.
- Personalize using the traveler's chosen destination, allowance, interests, pace, and supported travel preferences, not protected demographic guesses or assumptions about nationality/income.
- Show capability gaps instead of making safety, disability-access, dietary, price, or suitability guarantees that the data does not establish.
- Local-first saved trips are private to the OS/app data boundary, not an encrypted account service. Explain shared-device and uninstall/data-clear limits.
- No analytics, ad trackers, unnecessary Android permissions, GPS collection, booking/payment, or automatic upload of saved plans is added.
- Publicly downloadable packages do not require publishing the Flask demo as an unprotected shared internet service. No cloud deployment, Play Store/Microsoft Store submission, paid signing purchase, or new account is authorized by this scope approval alone.

## 8. Existing data and feature protection

- Keep historical version-1 Paris snapshots loadable and immutable. If new currency/location metadata needs a newer snapshot format, define versioned backward compatibility before tests/implementation. Do not rewrite old hashes, silently enrich old content from today's catalog, or discard records.
- A historical record without saved location metadata shows an honest location-unavailable fallback; it must not fabricate a map destination. New saved records retain their reviewed source/currency/location information.
- Saving identical title/content under the same reviewed format still reuses the existing row. Maps/photos/theme changes that do not change trip content must not make a form stale or create duplicates.
- Preserve CSRF protection, invalid-input retention, exact costs, honest itinerary gaps, safe external URLs, and catalog-independent historical reads.
- A currency/catalog selection must not mix items from another destination, reset an unrelated saved collection, or reinterpret existing saved money.
- Retain the meaning of the existing regression suite. Changes to hard-coded live-catalog counts must be defined during test preparation, with the original seven-place sample retained as an explicit regression fixture. Do not weaken assertions during implementation to conceal regressions.
- Production data is never used as a pytest base, packaging seed, or disposable browser-test database. Any migration needs non-destructive behavior and recovery documentation.

## 9. Acceptance and learning handoff

The selected release scope is delivered only when these observable outcomes hold:

1. Every approved destination is discoverable and has the agreed reviewed catalog coverage; unsupported locations are explained accurately.
2. Personalization and daily scheduling work for each destination, with deterministic reasons, correct currency/precision, free-item handling, and useful gaps.
3. A destination change cannot silently convert/relabel an entered budget or mix currencies in a result.
4. Each released location action opens the correct named place in Google Maps, handles Unicode/encoding safely, and leaves the current planner intact.
5. The UI accurately describes external Maps links only, and ordinary page loading makes no Maps/Places API, embedded-map, or geocoding request.
6. Photographs depict or clearly label their subjects, have documented redistribution rights/credits, work in both themes, and fail gracefully.
7. Existing saved records still load unchanged; new records preserve reviewed metadata; repeated saves and catalog-independent reads remain correct.
8. Both actual downloadable artifacts exist and pass their recorded platform launch/planning/save/restart checks. No claim of both-platform completion is made from source code or a single successful build.
9. Core Track A planning and saved trips work without internet on the tested installed apps; external maps/source links clearly need connectivity.
10. No real user records, private credentials, or other users' saved data appear in a distributed package or shared service.
11. Unit/integration tests are defined and validated before feature code; relevant pytest regressions pass, and browser/native/installed-artifact evidence is recorded separately. Pytest alone is not proof of an Android install.
12. The student has setup/run/download instructions, a known-limitations list, a presentation flow with a short sample trip, and a backup demonstration recording or walkthrough.

The learning guide must explain data-driven destination choices, exact multi-currency money, source verification, Maps links versus APIs, local asset licensing, offline boundaries, package runtime/data paths, and native testing. It must still describe the AI honestly as explainable recommendations/scheduling unless a separately approved model feature is introduced.

Small student tasks: compare two destinations' interests and currencies; explain one recommendation; locate a place in Maps and recover offline; switch themes without changing trip content; and install/relaunch each package while explaining where its saved data lives.

## 10. Approval record and next gate

On 2026-10-26, the user chose option 1 (the six-city first release) and **View on Google Maps** buttons without an API key, keeping this a focused class project. Those decisions close the coverage/Maps questions. Photos, destination currencies, and both downloadable application targets remain included from the preceding proposal.

The [implementation/test plan](../plans/phase-08-expanded-release-plan.md) records responsibilities, small delivery slices, compatibility contracts, test coverage, and native build prerequisites. New Phase 8 tests are next; no production feature integration may precede their definition/validation.

Scope approval does not authorize billing changes, external publication, SDK agreement acceptance, paid certificates, or a claim that an untested package is ready for everyone. Actual toolchain installation and installed-artifact verification still have their normal permission/testing gates. Continue explaining each slice; do not introduce another fixed multi-week timeline or promise same-day completion before the checks are satisfied.

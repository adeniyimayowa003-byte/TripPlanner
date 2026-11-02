# Photos and visual polish — completed 1 November 2026

TripPlanner now includes **18 real photographs**, three for each of its six cities. The home page has a Paris photo example and six destination cards. Trip ideas and saved alternatives have photo panels. Daily itinerary slots show compact images only where a photo of that exact place exists. Light and Dark change the surrounding surfaces while preserving the photograph's colors.

The [approved specification](../specs/phase-08-expanded-release.md) already included this work. The [bounded implementation/test contract](../plans/phase-08-photos.md) was written before production integration. Native packages are still separate work.

## What changed, and why

Pictures help a traveler understand what a destination feels like. They also make recommendations easier to scan. We use real, credited photographs rather than generated views of landmarks. A photograph is not evidence of current opening hours, conditions, accessibility, prices, or suitability.

Three places per city have exact photos. Other idea cards use the selected city's lead picture with the explicit note **“Destination view; a photo of this venue is not available.”** The caption and alt text describe the actual pictured landmark. Daily slots omit representative photos to avoid confusing another landmark with the scheduled place. Not every restaurant has an exact photo yet.

The photographs are bundled locally. Ordinary page loading does not contact Wikimedia, Google, an image API, or a tracking pixel. Clicking an external source, license, photographer, or Maps link needs internet. This prepares the assets for future offline-capable packages; those packages have not been built yet.

## How the code works

1. [data/images.json](../data/images.json) is a **manifest**: a list of image facts and credits. Stable place IDs connect pictures to the correct place. A separate destination mapping selects a city lead image. Width, height, description, photographer, license, source, and review date are recorded once.
2. [photos.py](../photos.py) reads and validates that manifest. It rejects external image paths, traversal paths, invalid dimensions, incomplete credits, and unsupported licenses. It returns a fresh exact-place image, a clearly marked destination fallback, or no image when the file is absent. It never consults the travel catalog or saved-trip database.
3. [app.py](../app.py) supplies a display helper to the templates and loads metadata once per request. A missing or invalid manifest produces usable text fallbacks. Saved pages and `/credits` work without loading today's catalog or validating an unrelated draft.
4. [templates/_photos.html](../templates/_photos.html) is a reusable Jinja **macro**: the same small template builds a photo frame, descriptive alt text, truthful caption, and credits link everywhere. The home lead loads eagerly; below-fold images use **lazy loading**, which lets the browser wait until they are useful.
5. [static/js/images.js](../static/js/images.js) listens for a failed image load. It hides only that image, revealing “Photo unavailable.” It handles cached failures as well. Place information, forms, and Maps links remain usable. This is **graceful degradation**: an optional visual failure does not break the core task.
6. [static/css/style.css](../static/css/style.css) reserves image space, crops the displayed frame with `object-fit: cover`, and uses the existing theme colors for captions and borders. Cropping is a display choice; the bundled JPEGs have no local edits.

Photo metadata stays outside saved JSON and fingerprints. Correcting a photographer credit cannot change a trip's cost, make its reviewed save form stale, or create a duplicate trip. A historic saved place can still be read when its image or today's catalog is unavailable. This is **separation of concerns**: display assets and trip content have different responsibilities.

The AI is unchanged: explainable interest/preference scoring and a greedy daily scheduler. Adding photos does not introduce a trained model or a live image recommendation service.

## Rights and file sizes

Every image's individual Wikimedia Commons file page was checked for subject, creator, license, and reuse warnings. Each downloaded JPEG was visually inspected and its real JPEG dimensions were read independently. Two bounded source tasks prepared the assets under the Sites skill's local-project workflow; their research did not edit the application.

The [standalone photo credits](../PHOTO_CREDITS.md), manifest, and in-app **Photo credits & licenses** page preserve attribution and license links for web and future native redistribution. Photographs retain their individual CC BY, CC BY-SA, or CC0 license. These licenses do not automatically license the rest of this project's code. Preserve credits when copying or distributing the images; altered BY-SA image derivatives retain the applicable share-alike terms.

All 18 photographs total **3,648,715 bytes**, about 3.48 MiB. The target was approximately 250 KB per image. Four useful published thumbnails are modest exceptions above 250 KiB: Luxembourg Gardens 261,943 bytes; White Tower 306,278; Company's Garden 286,651; Central Park 260,790. Every image is below 400 KiB. The lead Eiffel image is 108,659 bytes. Notre-Dame and Kirstenbosch use practical-sized published originals; the others use already-published Commons thumbnails. No image-processing or production dependency was added.

## Test-first evidence

- Initial retained baseline: 1,471 passes and six Windows-encoding failures in the existing planner-script tests. The same 17 planner-script cases passed under Python's UTF-8 mode. The harness now explicitly decodes Node's UTF-8 output; its assertions and production planner behavior were not changed.
- First new batch: **50 tests collected**, with one independent fixture/JPEG-reader pass and **49 inspected missing-feature failures**, no collection/setup errors or skips. Evidence: `.tmp/photos-red.xml`.
- First integration: 49 passes and one test-data problem. The synthetic helper's ZAR 300 allowance had no real Cape Town food/history matches. The new test now uses ZAR 3,000 and preserves both interests in its MultiDict. Production matching and costs were not changed to make photos appear.
- Focused integration: **50 passes** in 3.05 seconds, `.tmp/photos-focused.xml`.
- Regression review caught representative photo captions being mistaken for other places inside daily slots. A new exact-subject test reproduced the problem before the template refinement. Two malformed-manifest structure tests also failed before explicit string checks were added. Evidence: `.tmp/photos-caption-red.xml`, `.tmp/photos-structure-red.xml`.
- Final full run: **1,530 passes in 60.16 seconds**, with no failures/errors/skips, `.tmp/photos-final.xml`. This is all 1,477 retained cases plus 53 photo cases. No earlier regression was removed or weakened. No extra test libraries were installed.

Coverage includes actual JPEG signatures/dimensions and local file limits; six-city coverage/credits; metadata validation; exact/city/missing-file lookup; actual image-error JavaScript for loading/loaded/cached-failure states; six-city HTTP idea/itinerary pages; missing metadata fallbacks; historical v1 catalog-independent reads; unchanged snapshots/fingerprints/duplicate saves; and photo CSS/theme behavior.

Tests use fresh project-local temporary directories and isolated databases. The main server and user's saved-trip database were not started, reset, migrated, or populated for this phase.

## Browser evidence and limits

The owned QA preview on port 5001 used `.tmp/three-phase-browser-qa.sqlite3`. Its existing **Tokyo presentation check** still shows JPY 30,000 allowance, JPY 7,300 scheduled estimate, JPY 22,700 unallocated, and 7 of 9 slots filled.

Checked in the in-app browser:

- All seven home images loaded locally. The lead and six-city gallery render in both Light and Dark; the photographs keep the same colors.
- An image's credits link opens the correct per-photo anchor, with creator, source, license, change notes, and bundled dimensions. The shared footer credits link stays visible at this viewport.
- The existing saved Tokyo detail shows exact-place thumbnails only for Meiji Jingu, Sensoji, and Ueno Park. Other daily slots have no misleading landmark thumbnail. Saved alternatives show exact or explicitly representative photos. Fourteen existing Maps links remain present.
- A fresh Paris form was submitted with three days, EUR 300, food/history, and relaxed pace. Its daily preview shows EUR 100.00, and submission produces seven personalized photo cards with intact Maps actions. The QA browser's new draft is separate from the existing Tokyo snapshot and from the user's main server.
- The actual viewport was **738 CSS pixels wide**, with a 723-pixel page content width and no horizontal overflow. This phase does **not** claim a real 360-pixel or physical-phone browser check; narrow-layout CSS and existing automated theme/responsive rules pass. Actual phone/installed-app checks remain a later release gate.
- Broken/missing-image and cached-error cases were verified automatically, not simulated manually by editing the user's browser or deleting bundled files.

Screenshots: `.tmp/photos-light-gallery.png`, `.tmp/photos-dark-gallery.png`, `.tmp/photos-dark-hero.png`. Browser screenshots are verification artifacts, not new image assets.

## Your small tasks

1. Open the home page and identify all six destinations. Switch Light → Dark → Use device setting. Explain why the pictures keep their colors.
2. Plan Paris for three days with EUR 300 and food/history interests. Compare an exact landmark photo with a restaurant's explicitly labeled destination view.
3. Build the itinerary. Explain why a daily slot only gets a photo when we have one of that exact place. Compare its estimate with the result before switching themes.
4. Open **Credits & license** beside a picture. Identify the photographer, source, and license. Explain why “found on Google” is not a redistribution license.
5. Open a saved trip and confirm its saved amount is unchanged. Explain why correcting a photo credit must not change the saved trip's fingerprint.

For a short presentation explanation: “We keep image facts and licenses in a separate manifest. The server chooses an exact place photo or a labeled destination view. Our templates reuse one image component, images load locally, and a failed picture does not stop planning. Saved trip content and recommendation scores do not depend on the photos.”

## Next phases

1. **Windows packaging:** owned local runtime, resource/data paths, persistent appearance/storage, actual packaged launch/save/reopen outside the checkout.
2. **Android packaging:** a signed installable APK that runs the planner on the device, followed by emulator/device checks.
3. **Final presentation and release checks:** verified downloads, limitations, a clear demo, and backup walkthrough/recording.

No fixed weekly timeline has been reintroduced. Neither a native package nor a public release is claimed by this photo delivery.

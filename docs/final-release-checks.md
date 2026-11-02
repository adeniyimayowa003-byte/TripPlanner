# Final classroom release checks

**Version:** 0.8.0-demo.2. **Date:** 2026-11-01. The approved class-project handoff includes the six-city website, Windows portable demo, Android debug APK, and presentation materials. Verification applies to the recorded environments below.

## Automated results and source integrity

- Full pytest suite: **1,596 passed in 36.15 seconds**, with no failures, setup errors, or skips.
- Final native runtime/package subset: **59 passed in 6.24 seconds**.
- Android's five new staging/lifecycle cases first failed for intended missing behavior, then passed before main integration.
- Publication source review: **0 findings**. Real profiles, databases, keys, SDKs, virtual environments, build products, and private QA evidence remain excluded from source output.
- Windows' earlier extracted-source test run remains a historical checkpoint. The final complete source archive receives an independent extraction/check. Its artifact-specific result and hashes are recorded in the release-manifest.json sidecar outside the archive.

Private JUnit records: `.tmp/final-release-pytest.xml`, `.tmp/native-final-regression.xml`, and `.tmp/android-red.xml`. Historical reports retain their original counts and should not be read as the current total. There is no trained-model accuracy percentage to report: recommendations and scheduling use explicit deterministic rules.

## Windows artifact

`TripPlanner-0.8.0-demo.2-windows-x64.zip` is the previously inspected unsigned portable x64 demo, **20,827,585 bytes**, 244 files. The exact ZIP SHA256 is:

`c6218d44854fdae916797d685ca5595b00e2b6c7252851414c689fa26ecefc75`

The extracted app passed planning, saving, Light/Dark, close/reopen, and actual external Google Maps venue checks on the recorded Windows 11 25H2 x64 host, without development Python on PATH. Its saved row stayed identical. This turn adds Android and documentation without changing the Windows planning core or replacing that tested binary. See [the Windows report](phase-08-windows.md).

Other physical Windows computers and a deliberately disconnected-network Windows run remain untested. WebView2/.NET prerequisites and the unsigned-demo status remain explicit.

## Android artifact

`TripPlanner-0.8.0-demo.2-android-demo.apk` is **48,333,905 bytes**, debug-signed, minimum SDK 29, compile/target SDK 36, with ARM64 and x86_64 runtimes. Its exact SHA256 is:

`4efa651c55783b99922ead32d4617c8377ca99f59dff5017ec9bca25dfa71538`

The signing certificate's SHA256 fingerprint is `5992b9bd90255713d17c1a56c9bf4109a9e670142df63edfad38713e61afbbb8` (Android Debug, not public release signing). The package requests INTERNET only and contains no GPS or broad storage permission. Python runs on-device. Exact dependency versions and runtime notices are included.

The primary installed acceptance target is Android **15 / API 35 x86_64**, Pixel 5 emulator profile at 1080 × 2340, System WebView **124.0.6367.219**. With emulator Wi-Fi and mobile data disabled, the exact handed-over APK passes actual native-tap navigation/submission, recommendations, the EUR 135 itinerary, save, Dark, bundled photos, Back, and the Luxembourg Gardens external Maps intent. An instrumentation Activity monitor intercepts the Maps intent; a rendered Android Google Maps page is not claimed.

After a forced process restart, the saved trip and Dark preference reopen correctly. The one saved row retains digest `f65019670bd40d22896d6af2640d56d31d1c19844d0d0f36c3881e47f5173597`. System follows both emulator Light and Dark, and manual Light overrides a Dark device. The host computer's network and appearance were not changed. The final exact-APK journey is `.tmp/android35-exact-release-journey.txt`; restart and device-mode records are alongside it.

Physical ARM64 phones, every Android/WebView version, and app-store release signing/approval remain unverified. The supplied emulator WebView is a recorded version, not a claim to be the newest available. See [Android evidence](phase-08-android.md).

## Presentation artifacts

The PowerPoint has **17 slides** with editable text, photographs, app screenshots, and speaker notes. Every slide was rendered and inspected. Final package/layout/font/import checks report zero findings and zero layout warnings, with Georgia and Segoe UI as the selected fonts. This does not claim native PowerPoint execution or every Office version was tested.

The Word guide has **16 pages**, rendered with an isolated LibreOffice extraction and visually reviewed page by page. It includes the spec/plan summary, explanations of the code and rule-based AI, a demo script, Q&A, and all photo attributions. Temporary renders and validation records stay private; the requested PPTX and DOCX are the handoff files. See [the rehearsal walkthrough](presentation-walkthrough.md).

## Release and data limits

The six curated cities, 48 places, and 18 local photographs remain the actual coverage. Costs are illustrative per-person activities/food estimates. Flights, hotels, transport, missing meals, opening hours, routes, and suitability guarantees remain excluded. MIT applies to original code; photos and dependencies retain their own notices.

The main port-5000 database/profile has not been reset, copied into packages, or used for QA. This task does not create an account, public hosted service, GitHub repository, app-store listing, or cloud sync. Before classroom use on a different computer or physical phone, rehearse on that actual presentation device using its normal software policy.

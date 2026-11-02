# Android demo and learning report

The approved Android increment now has a real debug-signed APK with Python embedded on the device. It does not depend on the laptop's development server. This report distinguishes compilation, emulator checks, and the remaining physical-phone limits.

## Test-first implementation

The bounded [Android plan](../plans/phase-08-android.md) preceded implementation. Five new pytest cases first failed for missing Android staging/runtime behavior, then all five passed. They cover the shared-resource allowlist, excluding unknown/private data, failing missing resources before copying, no output overwrite, and the runtime's start/reuse/stop/settings behavior. The full suite now passes **1,596 cases**. The final native-focused rerun passes **59 cases**.

`android_runtime.py` shares the already-tested guarded loopback service, strict profile settings, local SQLite store, CSRF protection, one-use launch credential, and exact-origin restrictions. `MainActivity.java` handles the Android WebView, app-private directory, lifecycle, Back, and separate public HTTPS intents. A parent container applies Android 15 system-bar insets so the page stays out of the status/navigation bars. Native Light/night resources allow System appearance to follow the device. The Android 13+ Back dispatcher and older Back override both use WebView history.

## Build matrix and provenance

| Item | Recorded version |
| --- | --- |
| Chaquopy plugin | 17.2.0 |
| Embedded CPython | 3.14.8 |
| Host build Python | 3.14.7, same major/minor |
| JDK | Eclipse Temurin 17.0.20.1+1 |
| Gradle and Android plugin | 8.13 and 8.13.0 |
| Compile/target and minimum SDK | 36 and 29 (Android 10 minimum) |
| Native ABIs in the APK | arm64-v8a and x86_64 |
| Dependency versions | `requirements-android.lock.txt` |

The owner accepted Android SDK terms and authorized installation on 2026-11-01. Tools/caches are isolated from app/source output. The SDK/Gradle/JDK and large emulator images are not files shipped in the app. The first AVD's tool-created metadata resides in the normal user Android directory. The Android 15 AVD data uses the explicitly named project QA folder. Both are disposable test profiles, independent of the user's Windows and web collections.

The APK requests **INTERNET only**, needed for its local HTTP service. It requests no location or broad storage access. Cleartext is permitted only for 127.0.0.1. File/content access, mixed content, in-app downloads, WebView debugging, and JavaScript bridges are disabled. Demo APKs remain Android-debuggable because this is a debug build, despite WebView debugging being disabled. Do not describe that build as a hardened public release.

Upstream runtime notices ship as APK assets. The Python dependency archives retain distribution metadata and license files. See [third-party notices](../THIRD_PARTY_NOTICES.md) and the exact lock file. The app icon reuses the project's own Windows branding. No personal database, token, key, virtual environment, or development SDK is bundled.

## Real emulator evidence

The primary acceptance device is an **Android 15 / API 35 x86_64 emulator**, Pixel 5 profile at 1080 × 2340, with System WebView **124.0.6367.219**. This is the image's supplied WebView, not a claim that it is the newest available release. The emulator runs through the installed Windows Hypervisor Platform. An earlier Android 11 image with WebView 83.0.4103.120 established startup/domain behavior, but its older rendering support is not the primary visual acceptance baseline.

A separate instrumentation test APK exercises the actual Activity/WebView using native taps for navigation/form submission. Data fields are filled through the owned app's DOM. The test APK is separate from the downloadable application and adds no production JavaScript bridge. Programmatic link clicks alone did not create usable browser Back history; the corrected test uses real taps and waits for controls to be visible, with instant test scrolling to avoid measuring moving targets.

With **the emulator's Wi-Fi and mobile data disabled**, an external ping failed while the app passed launch, preference submission, recommendations, the EUR 135 itinerary, saving, Dark-mode persistence, bundled photos, native Back, and the external Maps intent handoff. The host computer's network was not disabled. Maps routing used an instrumentation Activity monitor to intercept the external ACTION_VIEW URL for Luxembourg Gardens with `api=1`; this verifies routing and state preservation, not a rendered Google Maps page on Android. Windows separately verified the actual public venue page.

The saved QA trip uses Paris, three days, EUR 300 total activity/food allowance per person, food/history interests, and no pace/family preference. Seven of nine slots schedule EUR 135; EUR 165 remains unallocated. After the refreshed final APK and a forced process restart, the saved result and Dark setting reopen correctly. The one stored row's digest stays:

`f65019670bd40d22896d6af2640d56d31d1c19844d0d0f36c3881e47f5173597`

The one-use launch URL remains private and is never included in published screenshots or logs. QA screenshots are in `docs/images/`; private JUnit, instrumentation, and database evidence remain under ignored `.tmp/`.

After reproducing the original forced-Light system-theme failure, the final native resources pass device-Dark and device-Light media-query checks. Manual Light also overrides a Dark device. These checks change only the isolated emulator's own mode. They do not change the host computer's appearance.

## Important verification limits

The APK contains ARM64 code but no physical ARM64 phone has been tested. Do not claim all-device support, a Play Store release, the newest WebView, or live Maps rendering on Android from these emulator checks. Flights, accommodation, transport, opening times, complete meals, live prices, and route feasibility remain outside the app's planning promise. The build is a debug-signed classroom demonstration, not a public release-signing setup.

## How to build and understand it

Use the [download/build guide](android-download.md). The preferred build is Windows-hosted Gradle with embedded Python; no WSL installation is required. `build_android.py` stages a fresh project and 62 shared app files from the reviewed manifest. Rebuild only in a new staging folder, retain a stable demo signing identity for updates, and keep keys outside source control. Compilation alone is not a substitute for the actual installed-app journey.

Practice task: explain why the Android app can plan without the laptop, why its data directory differs from packaged resources, why a Back test needs a genuine navigation gesture, and why building both CPU ABIs does not prove both have been physically tested.

Primary sources: [Chaquopy integration](https://chaquo.com/chaquopy/doc/current/android.html), [Chaquopy versions](https://chaquo.com/chaquopy/doc/current/versions.html), [Android/Gradle compatibility](https://developer.android.com/build/releases/agp-8-13-0-release-notes), and [SDK tool documentation](https://developer.android.com/tools/sdkmanager).

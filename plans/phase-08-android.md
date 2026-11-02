# Android implementation and acceptance plan

This bounded plan implements the already approved native Android portion of the expanded-release spec. The owner accepted the Android SDK terms and authorized installing build tools on 2026-11-01. Tool downloads and caches stay inside ignored build state. No accounts, public hosting, GPS, or remote backend are added.

## Test first

Before implementation, define pytest cases for explicit Android source staging, exclusion of Windows executables/private data, missing-resource failure before copying, no overwrites, and the Android runtime's start/reuse/stop lifecycle. Exercise the same guarded loopback application with a temporary Android-style private data folder and verify settings persistence across restart. Existing runtime tests cover authorization, CSRF, forms, and SQLite independently. Validate the red result before adding the new modules.

## Implementation

Use a Java Activity and Android WebView with Chaquopy 17.2.0, Python 3.14, Android Gradle Plugin 8.13.0, Gradle 8.13, JDK 17, compile/target SDK 36 and minimum SDK 29. Build ARM64 and x86_64 into a clearly marked debug demo APK. Share the unchanged Flask/domain code and guarded local runtime. Stage only named modules, templates, local catalog/photos, and notices. Application state belongs to Android filesDir, separate from extracted resources. A synchronized Python entry point owns one local service per application process. Keep the service through Activity recreation and stop on explicit application teardown; Android may kill the process, so durable saved snapshots/settings survive separately.

Allow cleartext only for 127.0.0.1. Disable file/content access, mixed content, downloads, debugging, JavaScript bridges, and WebView remote navigation. Route public HTTPS links through an external Activity. Keep own origin inside the app. Block other URLs and subresources. Handle target-blank links through an intercepted popup, Back navigation, cookie/session bootstrap on each Activity creation, visible startup failure, and System appearance through normal WebView media queries. No runtime storage/location permissions.

## Acceptance

Run full pytest and source review. Compile Java and APK, inspect package permissions, Python resources, ABIs, signing identity, and SHA256. Install the actual APK on a recorded local emulator if acceleration/resources permit. Test planning, images, exact money, saving/reopening, theme persistence, Back, process restart, and external Maps without changing the user's real collection. Run a controlled offline journey in the emulator without disabling the host network. Record actual evidence and any blocker. Compilation alone never completes the installed-artifact acceptance gate. A physical phone remains unverified unless one is available.

Sources: [Chaquopy](https://chaquo.com/chaquopy/doc/current/android.html), [AGP matrix](https://developer.android.com/build/releases/agp-8-13-0-release-notes), [SDK tools](https://developer.android.com/tools/sdkmanager).

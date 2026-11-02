# Android demo download and build guide

The Android artifact is `dist/release/TripPlanner-0.8.0-demo.2-android-demo.apk`, with a matching `.apk.sha256` file. It is a **debug-signed classroom demo**, minimum Android 10, containing ARM64 and x86_64 Python runtimes. Its primary recorded acceptance run is Android 15 x86_64 with System WebView 124.0.6367.219. A physical phone remains unverified.

## Use the demo

Keep the APK, notices, and source together for classroom distribution. Follow your device's normal software policy and use its normal package installer. A real phone may require its owner's normal approval to install a local demo. Do not disable device protections. Core planning, local photos, and saved trips run on the device without the laptop or internet. Google Maps and source/license websites need internet.

The app stores data in Android's app-private files directory. Reopening preserves saved trips and appearance. Uninstalling the app or clearing its app storage removes that local data. There is no account, cloud backup, or cross-device sync. An update installed with the same application ID and signing key can retain storage; a different signing identity cannot update the existing package normally.

## Build from source

Install a supported JDK 17, Gradle 8.13, Android SDK platform 36, build-tools 35.0.0, and platform-tools through official sources and the normal owner license acceptance flow. Configure their local paths according to your development environment. Keep `local.properties`, caches, signing keys, and SDK contents out of GitHub. The successful build used Chaquopy 17.2.0 and Android Gradle Plugin 8.13.0.

From the project root, stage a new project:

```powershell
python build_android.py --output .tmp/android-project-new
```

Create the staged project's `local.properties` with the SDK directory for your machine. Use forward slashes in the value on Windows. Then run your installed Gradle:

```powershell
gradle -p .tmp/android-project-new --no-daemon assembleDebug -PtripplannerBuildPython=C:/absolute/path/to/python.exe
```

The build Python must be 3.14, matching the embedded runtime's major/minor. `requirements-android.lock.txt` supplies the exact tested dependency versions, copied as the staged app's requirements file. The debug APK appears at `app/build/outputs/apk/debug/app-debug.apk` inside that project. Preserve its SHA256 and inspect the app resources, permissions, ABI list, and signing certificate before distributing it.

The standard Android debug signing key is local build state, not a public production key. Do not commit or redistribute it. Public-release signing and app-store submission remain separate decisions.

## Run the native test journey

The source includes a separate `androidTest` instrumentation runner. Build `assembleDebugAndroidTest`, install the application and test APK on an isolated emulator, and invoke `org.tripplanner.demo.test/org.tripplanner.demo.QaInstrumentation` with `am instrument -w`. The normal mode checks planning, costs, saving, Dark, photos, Back, and the external Maps intent. `-e resume true` checks saved data/theme after process restart. `-e system true` or `false` checks Android device appearance after changing only the emulator's own mode.

Use the source's pytest suite and release review as well. Keep the current user collection separate. Read [the Android report](phase-08-android.md) for actual evidence, test-driver corrections, and limits.

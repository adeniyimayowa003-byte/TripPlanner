# Windows download and build guide

The approved Windows slice uses the same planner in a pywebview EdgeChromium window and bundles it with PyInstaller. The build is an **unsigned Windows x64 class-project demo**. Actual artifact verification is recorded in the final evidence section when completed; source code alone is not a tested download.

## Run a portable download

Extract the entire versioned ZIP. Open `TripPlanner.exe` while keeping `_internal/`, `licenses/`, and its notices beside it. Microsoft Edge WebView2 Runtime and Windows .NET Framework are prerequisites; use [Microsoft's official WebView2 instructions](https://developer.microsoft.com/microsoft-edge/webview2/) if needed. No separate Python, coding editor, or development server is required by the end user.

Follow your device or school's policy for unsigned software. Do not bypass security, certificate, antivirus, or SmartScreen protections to make it run.

## Data and appearance

The app stores its own settings, signing secret, browser profile, and saved SQLite collection under `%LOCALAPPDATA%\TripPlanner`. Resources stay in the app folder. Closing/reopening preserves saved trips and the selected Light/Dark/System setting. Another Windows account or explicit profile has its own data. Clearing/deleting that profile can remove saved trips; keep backups before manual maintenance.

Advanced/QA users can run `TripPlanner.exe --data-dir C:\an-absolute-isolated-profile`. Do not use a real saved collection as disposable QA state. The OS profile boundary is not application-level encryption or a private account service.

## Build from source

Use 64-bit Python 3.14 on Windows. From a fresh checkout, create a separate `.venv-windows` environment. Install `setuptools` and `wheel`, then `requirements-windows.txt` from official PyPI. If a source dependency's isolated build cannot find its build support, the recorded build used the dedicated environment's installed support with `--no-build-isolation`; the working web environment was unchanged. The exact tested dependency lock is recorded after installation.

Run `.venv-windows\Scripts\python.exe build_windows.py`. The builder creates a new allowlisted staging folder under `.tmp`, runs PyInstaller there, includes supplied dependency notices, creates a versioned ZIP under `dist`, and writes its SHA-256 file and internal file inventory. It refuses to overwrite an existing ZIP of that version; choose a fresh `--output` folder for another build. Keep builds out of ordinary source commits; upload reviewed binaries as release assets when publication is explicitly requested.

Core planning, bundled photos, and local saves work from bundled data. Maps, sources, license deeds, and photographer profiles open externally and need internet. Coverage is six cities; costs and time slots remain illustrative.

## Verification evidence

The verified demo is `dist/release/TripPlanner-0.8.0-demo.2-windows-x64.zip`, 20,827,585 bytes. Its SHA-256 is `c6218d44854fdae916797d685ca5595b00e2b6c7252851414c689fa26ecefc75`. The ignored `dist/` output is a local artifact; after GitHub publication it should be supplied as a reviewed release asset rather than a committed binary. The earlier demo.1 is superseded because actual native testing found a form-origin issue, repaired and regression-tested in demo.2.

All **1,591 tests pass**. The ZIP's CRC, 243 inventory hashes, 18 photos, licenses, and x64 executable were inspected. The exact ZIP was extracted outside the checkout and launched with development Python removed from its child environment's PATH. Native planning, saving, explicit Light/Dark, close/reopen, unchanged saved amounts/row content, and external Google Maps were verified on Windows 11 x64 25H2 build 26200.9711. Installed WebView2 folders are 155.0.4283.62 and 156.0.4314.50.

The test trip “Windows Paris presentation” retains EUR 300 allowance, EUR 135 scheduled estimate, EUR 165 unallocated, and 7 of 9 filled slots after restart. Dark is retained even when the owned local service gets a new port. Luxembourg Gardens opens separately in Chrome at the correct Jardin du Luxembourg location, and the app keeps its saved page.

Other Windows versions, another clean physical computer, and a deliberately disconnected-network run have not been tested. Android is not included in this artifact. The build remains unsigned. See the [complete evidence and student guide](phase-08-windows.md).

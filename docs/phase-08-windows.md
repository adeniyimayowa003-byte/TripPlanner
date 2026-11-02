# Windows packaging and GitHub preparation — 1 November 2026

The Windows **0.8.0-demo.2** portable demonstration is built and its native planning/save/theme/restart/Maps journey has passed on the recorded Windows 11 host. The project also has GitHub setup instructions, screenshots, an MIT code license, separate dependency files, privacy/notices, a test workflow, and private-file exclusions. Android and the final presentation/release rehearsal remain separate phases.

## What we are building and why

The website normally needs Python and a running Flask server. A downloadable Windows app needs those pieces bundled and managed by the app itself. The packaged app starts its own loopback service, waits for it to be ready, opens a native WebView2 window, and stops only its own service when it closes. It does not depend on the developer's port 5000 or 5001.

The same recommendation, currency, scheduler, snapshot, and photo code runs inside the window. This keeps the class project understandable: we have one planner with two ways to launch it, rather than two contradictory algorithms.

## How the code works

| Part | Responsibility and concept |
| --- | --- |
| `version.py` | One version identifies the window, footer, executable properties, and ZIP. |
| `app_runtime.ProfileSettings` | Stores a stable signing secret and the appearance enum in per-user app data. Atomic file replacement prevents a half-written settings document. Invalid existing settings are not silently reset. |
| `app_runtime.ProfileLock` | An OS file lock prevents two windows from sharing the same browser profile simultaneously. The OS releases it when the process exits. |
| `app_runtime.make_desktop_app` | Configures the ordinary Flask factory with that profile's database/secret, overriding inherited development paths. Resources and user data have different lifetimes. |
| `app_runtime.DesktopRuntime` | Binds an allocated loopback port, authenticates every private route, waits for real HTTP readiness, and owns bounded shutdown. It never searches for or kills another server. |
| `windows_app.py` | Creates an EdgeChromium window and restricts navigation to its exact origin. Safe external HTTPS links open in the system browser. It supplies no general JavaScript/Python file or command bridge. |
| `static/js/appearance.js` | Keeps the normal website's browser-local behavior. In native mode, uses the server-injected preference and sends only a validated enum to a protected same-origin endpoint. A port change cannot erase that preference. |
| `build_windows.py` | Stages only named source/resources, packages with PyInstaller, includes the runtime/notices, renders the project's own icon, and writes a versioned ZIP, SHA-256, and file inventory. |
| `release_checks.py` | Reviews source candidates for missing publication files, unexpected local data/binaries, and recognizable credential patterns. Reports paths without exposing credential values. It is a useful check, not a proof against every possible secret. |

The native access token is random for each launch. A single-use bootstrap URL sets an HttpOnly SameSite=Strict cookie and redirects to a clean app URL. Private pages, saved collections, static resources, and health routes require it. Host/Origin checks, existing CSRF tokens, and a restrictive content policy remain separate protections. Loopback binding by itself would not provide this boundary.

The native theme endpoint accepts exactly `appearance: system/light/dark`; it cannot read arbitrary files, run commands, or copy unrelated browser storage. Its POST requires both the launch cookie and session CSRF token. Saved trip content, scores, and fingerprints remain independent of appearance.

## Test-first evidence

The [bounded plan and contracts](../plans/phase-08-windows.md) were written before native feature code. The approved [expanded specification](../specs/phase-08-expanded-release.md) already covers Windows packages; the user additionally requested GitHub preparation and selected MIT for the original code.

- Fresh retained web baseline: **1,530 passes in 69.41 seconds**, `.tmp/windows-web-baseline.xml`.
- First native/GitHub batch: **56 collected**, one independent HTTP-fixture pass and **55 inspected missing-feature failures**, no setup/collection errors or skips, `.tmp/windows-red.xml`.
- One extra readiness-failure case failed before runtime implementation, `.tmp/windows-readiness-red.xml`.
- Runtime/appearance integration: 110 relevant cases passed; 14 pure navigation cases still failed because the window module did not yet exist, `.tmp/windows-runtime-green.xml`.
- First complete focused run: 56 passes and one Git test-fixture issue. Windows text I/O translated newline-delimited Git stdin into carriage-return-bearing filenames. The fixture now uses Git's documented NUL-delimited mode; ignore assertions were retained.
- Final focused native/GitHub checks: **57 passes in 6.74 seconds**, `.tmp/windows-focused-final.xml`.
- Full retained/new suite: **1,587 passes in 76.45 seconds**, with no failures/errors/skips, `.tmp/windows-full.xml`.
- Source handoff check: an extracted GitHub source copy outside the checkout also passes **all 1,587 tests in 37.11 seconds**, `.tmp/github-source-tests.xml`. This checks that required fixtures, scripts, resources, and notices are included rather than accidentally borrowed from the working folder. The final source bundle also includes `.gitattributes` for consistent text/binary handling.

The native acceptance run subsequently caught a browser-specific form issue that those first tests had missed. A blanket `Referrer-Policy: no-referrer` causes non-CORS HTML form submissions to send `Origin: null`, while the JavaScript fetch used for appearance still sends its real origin. The native guard correctly rejected the opaque form origin. This is documented by [MDN's Origin reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Origin) and the [Fetch standard](https://fetch.spec.whatwg.org/#append-a-request-origin-header).

Four additional cases were defined before the repair: a native HTTP form-to-save journey using the browser's origin rule, distinct bootstrap/clean-page referrer assertions, and continued rejection of opaque origins on two POST routes. The red run had **two expected failures and two passes**, `.tmp/windows-native-form-red.xml`. The repair keeps `no-referrer` on the one-use credential bootstrap and uses `same-origin` on clean pages: internal forms keep their origin; external sites receive no referrer. It does not relax origin, launch-cookie, or CSRF validation.

The resulting focused suite has **61 passes in 5.29 seconds**, `.tmp/windows-native-form-green.xml`, and the full retained/new suite has **1,591 passes in 33.45 seconds**, with no failures/errors/skips, `.tmp/windows-v2-full.xml`. The executable was rebuilt as demo.2 and the actual native journey repeated successfully. Earlier 1,587-case figures above are verification history, not the current count.

Coverage includes isolated/stable settings; corrupt/invalid settings preservation; profile locks; inherited-path isolation; real HTTP bootstrap/cookies/Host/Origin/CSRF; private GET/static routes; startup failure and owned shutdown; changed-port appearance persistence; actual production appearance JavaScript; URL navigation decisions; allowlisted staging; independent real-Git ignore behavior; and source/publication requirements. No earlier regression assertion was removed or weakened.

## Build and package inspection

Build tools were installed from official PyPI into `.venv-windows`, leaving `.venv` unchanged. Versions: Python 3.14.7, pywebview 6.2.1, Python.NET 3.2.1, PyInstaller 6.22.3, and hooks 2026.9. The full installed build environment is pinned in `requirements-windows.lock.txt`. `proxy_tools` required ordinary setuptools/wheel build support inside that isolated environment; no system Python or global security setting was changed.

The verified download is `dist/release/TripPlanner-0.8.0-demo.2-windows-x64.zip`, **20,827,585 bytes**. Its SHA-256 is:

```
c6218d44854fdae916797d685ca5595b00e2b6c7252851414c689fa26ecefc75
```

ZIP integrity, all **243 inventory file hashes**, the x64 PE machine identifier, 18 photo assets, MIT license, and exact WebView2 SDK notices were independently checked. The ZIP contains 244 files including its inventory. No user's database, settings document, browser cookies/profile, `.env`, key, virtual environment, `.tmp`, source-control data, or project test files were found among its filenames.

The exact-version Microsoft WebView2 SDK 1.0.3856.49 `LICENSE.txt` and `NOTICE.txt` were copied unchanged from Microsoft's NuGet package into `third_party/webview2/` and the artifact's license directory. This is separate from the installed Evergreen WebView2 runtime. Supplied dependency copyright/license files, metadata, Python notices, and the PyInstaller application-distribution exception accompany the download.

PyInstaller emitted optional dependency/table warnings, including `pycparser.lextab`/`yacctab` and unused optional Bottle servers. A warning alone was not treated as proof of failure or success; actual extracted-app startup was checked separately.

## Native verification checkpoint

The final ZIP was extracted into a new temporary folder outside the checkout, with a fresh QA profile outside the app resources. Only that app copy was launched, with Python/PYTHONPATH/PYTHONHOME removed from its child environment's search configuration. It opened the expected native TripPlanner 0.8.0-demo.1 window.

Test host: **Windows 11 x64, 25H2, build 26200.9711**. Installed WebView2 folders: 155.0.4283.62 and 156.0.4314.50. The SDK DLL version is distinct: 1.0.3856.49. Another clean physical computer and other Windows releases have not been tested.

The actual packaged home page renders its photographs, six cities/48 ideas, navigation, credits, version, and About/privacy action. Its clean allocated loopback URL contains no bootstrap token. System appearance resolves to the host's Dark setting.

After the user made the desktop available, Computer Use checked the actual extracted demo.2 window:

- **Planning:** Paris, three days, EUR 300, food/history, no pace/family preference produces seven matching ideas. The real native preview shows EUR 100.00 per day.
- **Scheduling and saving:** The itinerary fills 7 of 9 slots, schedules EUR 135.00, and leaves EUR 165.00 unallocated. “Windows Paris presentation” saves successfully as a v2 snapshot in the isolated QA collection.
- **Light/Dark:** Explicit Light and Dark choices change the real app, while local photos retain their colors. Light persisted when the app was updated from the earlier candidate into a newly extracted demo.2 folder with the same QA profile.
- **Close/reopen:** Closing the window normally stops its owned service on port 52710. Reopening the same extracted executable, again without development Python on PATH, allocates port 57817 and restores Dark. The saved collection and reopened detail retain the same title, amounts, seven filled slots, and original save time.
- **Immutable storage:** A read-only comparison of the QA database row before close, after close, and after restart/Maps finds the exact same row digest: `46c69f8e673fc39129e0258132d79995dc4c18a15e56e183389ef4b3eed7fa1a`. Only this synthetic QA profile was inspected, not the user's collection.
- **External Maps:** Luxembourg Gardens opens in the system Google Chrome browser as **Jardin du Luxembourg**, with address **75006 Paris, France** and the official venue reference. The native app remains on its saved snapshot. Only the Maps tab created for the test was closed afterward.
- **Evidence:** `.tmp/windows-package-qa.json` records the artifact/profile/process checks without storing a signing secret or launch token. Screenshots include `.tmp/windows-native-light.png`, `.tmp/windows-native-saved-dark.png`, `.tmp/windows-native-reopened.png`, and `.tmp/windows-native-verified.png`.

The first source-window permission timeout and foreground interruptions were recovered with the user's coordination. These checks are no longer pending. This verifies the named journeys on this host; a second physical computer, other Windows releases, and a deliberately disconnected-network run have not been exercised. Core planning uses bundled data with no remote travel/image service, while external links require internet.

The main port-5000 service/database were not opened, reset, or used for QA. The separate web preview on port 5001 was refreshed with its existing QA database. The native QA profile contains only its own demonstration state.

## GitHub preparation

- The original code is MIT licensed, as explicitly selected by the user. Photo/dependency licenses remain separate.
- README now describes current six-city capabilities, setup, AI rules, screenshots, native build/data behavior, privacy, tests, and honest limits. Stale Paris-only structure claims were removed.
- `requirements.txt` is runtime-only; `requirements-dev.txt` supplies pytest; native build requirements and their exact lock are separate.
- `.gitignore` excludes environment secrets, local databases/journals, browser profiles, virtual environments, caches, keys, `.tmp`, and build outputs. Real Git checks exercise the rules in a temporary repository; the project itself was not initialized, committed, or uploaded.
- `.github/workflows/tests.yml` configures read-only test jobs on Windows and Ubuntu, with Python 3.14 and Node 24. Actions versions were checked against their official repositories. Hosted CI has not run because this project has not been uploaded.
- Contribution, privacy, code/photo/dependency notices, a favicon/native icon, version information, and a Windows usage guide are included. Source audit currently reports zero findings; current handoff document links resolve.
- The executable's embedded icon/product/file version information was inspected, and Windows reports its signature status as **NotSigned**, consistent with the demo label. A superseded pre-license ZIP was moved into ignored build scratch so it is not confused with the current `dist/release` download.

## Your presentation tasks

1. Explain why the app bundles Python and a browser window while retaining the same recommendation code.
2. Locate the app folder and the separate profile folder. Explain why updating resources must not delete saved trips.
3. Choose Dark, save a short trip, close, and reopen the extracted app. Check both the saved amount and theme.
4. Open a venue in Maps and verify it opens outside TripPlanner. Try the core planner without relying on external links; photographs and estimates use bundled data.
5. Explain the difference between MIT code licensing, individual photo licenses, and dependency notices.
6. Before a first GitHub push, run tests and the source audit, inspect the intended source files, and keep the ZIP as a reviewed release asset rather than a normal source commit.

Android and final presentation/release rehearsal remain separate phases. This is an unsigned demonstration, not a verified public release for every Windows computer.

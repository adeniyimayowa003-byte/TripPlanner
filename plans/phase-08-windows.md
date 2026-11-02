# Windows download and GitHub preparation

This records the approved Windows portion of the [expanded-release specification](../specs/phase-08-expanded-release.md). The user also requested GitHub readiness. Source/release preparation remains local, without publication to an unspecified account/repository. Android and the presentation handoff were subsequently completed within the limits recorded in the [final report](../docs/final-release-checks.md).

## Scope and decisions

- Build a Windows x64, one-folder portable ZIP using PyInstaller and pywebview with the installed Microsoft Edge WebView2 runtime. Reuse the existing Python 3.14 interpreter in an isolated build environment; do not change the working web environment. A modern WebView2 runtime is a stated prerequisite. Force EdgeChromium; do not silently fall back to obsolete Internet Explorer.
- Use the same Flask app and deterministic planner, bundled data, local pictures, templates, and scripts. No hosted service, login, analytics, remote image service, or privileged JavaScript/Python API is added.
- Start an owned loopback WSGI service on a dynamically allocated port. Wait for authenticated readiness before opening its window; bound startup/shutdown waits, close only owned resources, and report startup failure clearly. An occupied development port must be irrelevant.
- Each launch has a fresh random access token. A one-use bootstrap URL establishes an HttpOnly SameSite=Strict native access cookie, then redirects to a clean URL. Every private GET/POST/static route requires that cookie. Reject foreign Host/Origin headers. Keep the token out of logs and outgoing referrers. Existing CSRF protection remains; it is not replaced by this launch guard.
- The trusted app window renders its own exact loopback origin only. Open valid external HTTPS source/Maps/license links in the system browser; block script/file/data and credential-bearing navigation. Do not expose arbitrary native functions or load external pages inside the app window.
- Store settings, stable random cookie-signing secret, browser profile, and SQLite collection under `%LOCALAPPDATA%/TripPlanner` by default, separate from the executable/resources. A documented absolute `--data-dir` override allows isolated QA. A profile lock prevents simultaneous launches sharing one browser profile. Settings writes are atomic; corrupt settings fail clearly and are not silently overwritten.
- Persist only the native appearance enum (`system`, `light`, `dark`) through a guarded, CSRF-protected local endpoint. Inject its initial value before CSS to avoid origin-dependent loss. Keep normal website localStorage behavior intact. The native adapter has no generic file, command, or browser-storage bridge.
- Ship an unsigned, versioned demonstration build with instructions, source/photo/dependency notices, privacy/offline limits, inventory, and ZIP checksum. Do not bypass OS warnings or call it a signed public release.
- Prepare a clear README, environment example containing placeholders only, dependency separation/pins, a GitHub test workflow, contribution guidance, broader ignore rules, and an audit of source candidates. License choice belongs to the user; original code remains unlicensed unless they select a license. Photo/dependency licenses remain separate. Do not upload data, secrets, browser profiles, caches, virtual environments, or build scratch state.

## API contracts fixed before implementation

- `version.APP_VERSION`: a version string for app/footer/artifact metadata.
- `app_runtime.default_data_dir(environ=None) -> Path`: absolute per-user app-data location; no fallback to resources/current directory.
- `app_runtime.ProfileSettings(directory)`: `load()` creates or returns version-1 `{version, secret_key, appearance}`; `set_appearance(mode)` atomically updates the enum only; invalid/corrupt data raises `ValueError` without overwriting it. Each instance returns owned records.
- `app_runtime.ProfileLock(directory)`: context manager with nonblocking OS file lock, released even after exceptions. Does not kill processes or delete another profile.
- `app_runtime.make_desktop_app(directory) -> (Flask, ProfileSettings)`: overrides inherited database/signing environment settings with the profile. Web factory behavior stays unchanged.
- `app_runtime.DesktopRuntime(app, settings)`: `start(timeout=...)`, `origin`, `bootstrap_url`, `access_token`, `stop()`. Binds `127.0.0.1:0`, checks real HTTP readiness, guards routes, has single-use `/_desktop/open`, `/_desktop/health`, and CSRF-protected `POST /_desktop/appearance` accepting exactly `{appearance: enum}`. Stop is idempotent and leaves no listening owned service.
- `windows_app.navigation_action(url, origin) -> internal/external/blocked`: pure validated exact-origin decision. GUI imports are lazy so domain/runtime tests need no native dependencies. `main()` owns lock/runtime/window lifetime with finally cleanup.
- `build_windows.application_files(root)` returns an explicit list of safe source/resource paths, including every reviewed local photo and notices, independent of arbitrary other files. Reject missing/traversing/symlink resources. `stage_application(root, destination)` copies that list into a new staging folder; never stages a working checkout indiscriminately.
- `release_checks.check_source_tree(root)` returns a list of actionable relative-path findings without printing secret values. It checks source candidates and required publication files, not ignored user databases or third-party environment contents. Ignore-rule behavior is independently checked using Git in an isolated temporary fixture.

## Test and implementation order

1. Preserve the 1,530-case baseline. Define pytest cases for settings/atomic rejection, profile ownership, authenticated HTTP bootstrap/Host/Origin/CSRF, port allocation/readiness/shutdown, appearance retention across origins, safe external navigation, allowlisted staging, and GitHub hygiene. Define actual-script adapter checks before changing appearance integration. Collect and inspect meaningful missing-feature failures; fixture-only checks must independently pass.
2. Implement pure runtime/settings/navigation/staging first and pass focused tests. Install official PyPI native/build tools into isolated `.venv-windows`, with tested versions recorded, and inspect actual pywebview navigation hooks before integrating the window.
3. Add native appearance and app information, finish GitHub documents/CI, then run the full retained/new suite.
4. Build the actual ZIP. Inspect its contents for app/resources/runtime/licenses and absence of user data/secrets/tests. Extract a fresh copy outside the checkout, launch with Python absent from PATH and an isolated profile, exercise planning/save/close/reopen/theme persistence and external links, record actual Windows/WebView versions and architecture, and provide the artifact checksum.
5. Explain the result and limitations, with small student tasks. A successful PyInstaller run alone is not completion. If a concrete tool/runtime prerequisite blocks a platform check, preserve source/build work and identify that limit explicitly.

## Source references checked during preflight

### Native form regression gate — 1 November

The actual packaged browser rejected an ordinary trip form while fetch-based appearance saving worked. The global no-referrer policy causes a non-CORS HTML form's Origin to become `null` under the Fetch standard. Before changing production code, define a real HTTP form-to-save journey with that browser rule, separate bootstrap/clean-page header assertions, and continued rejection of opaque/foreign origins. Keep `no-referrer` on the credential-bearing bootstrap; use `same-origin` on clean app pages, which preserves internal form Origin while omitting referrers to external sites. Do not accept opaque origins or disable CSRF/launch guards. Rebuild as demo.2 and repeat the actual extracted-window acceptance checks.

References: [MDN Origin](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Origin) and [Fetch standard](https://fetch.spec.whatwg.org/#append-a-request-origin-header).

- [pywebview API and persistent profile options](https://pywebview.flowrl.com/api/)
- [pywebview packaging](https://pywebview.flowrl.com/guide/freezing)
- [pywebview 6.2.1 source](https://github.com/r0x0r/pywebview/tree/6.2.1)
- [PyInstaller supported Python and packaging](https://pypi.org/project/pyinstaller/)
- [Python.NET Python compatibility](https://pypi.org/project/pythonnet/)

Read-only preflight: current environment Python 3.14.7; native/build packages absent; x64 Windows build 26200.9711 / 25H2; Edge WebView2 version folders 155.0.4283.62 and 156.0.4314.50 present. Actual runtime/build success still needs verification.

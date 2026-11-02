# TripPlanner — Phase 7 Implementation and Verification

**Outcome:** Light, Dark, and Use device setting are implemented in the shared interface. All **943 pytest cases pass**. The next phase has not started.

**Scope:** [Approved specification](../specs/phase-07-appearance.md), [implementation/test plan](../plans/phase-07-appearance-plan.md), [historical red checkpoint](phase-07-testing.md), and [beginner learning guide](phase-07-learning.md).

## What changed

- [Shared header](../templates/base.html): one labeled native Appearance selector, an early local script, ordinary script-failure help, and a polite status region. The manual control starts hidden/disabled and becomes available only after its handler is attached.
- [Appearance script](../static/js/appearance.js): validates the three modes, applies the chosen root attribute, binds after DOM readiness, and safely remembers explicit choices using only `tripplanner.appearance`. Visiting a page does not write a preference. Failed writes keep the current selection and explain that it could not be remembered.
- [Stylesheet](../static/css/style.css): 27 semantic color roles in Light, manual Dark, and automatic Dark; component colors, fields, checked preferences, errors, warnings, emphasis cards, focus, native color scheme, hidden-state protection, and responsive header wrapping.
- [Styles regression test](../tests/test_appearance_styles.py): one additional check prevents filled-button background interpolation during a theme change.

The existing local Flask checkout was retained; no hosted Site, new framework, package, asset service, account, AI behavior, route, database column, or migration was introduced. Appearance is browser-local interface state, not a travel preference or saved-snapshot field.

Among the 25 fingerprinted baseline production files, only `templates/base.html` and `static/css/style.css` changed; the other 23 are unchanged. `static/js/appearance.js` is new. All 15 retained test/fixture files are unchanged. The real default `instance/tripplanner.sqlite3` remains absent.

## SDD and automated results

Specification approval, planning, and test-definition validation preceded production implementation. The historical red checkpoint discovered 942 cases with 766 passes and 176 inspected missing-feature failures. Implementation first passed those 942 cases; browser verification then found the narrow animation defect below.

Final run: **943 passed in 18.94 seconds**, with no errors, failures, or skipped cases. Evidence is the ignored `.tmp/phase7-final-green.xml`.

| Area | Passing cases |
| --- | ---: |
| Retained Phase 6 suite | 676 |
| Appearance HTTP integration | 42 |
| Actual-script unit/harness checks | 72 |
| Styles/contrast/helper checks, including the new regression | 153 |
| **Total** | **943** |

The script checks execute the actual asset through the test-only Node harness. HTTP checks protect shared markup, catalog-independent saved views, drafts, snapshots, fingerprints, duplicate saves, schema, and ordinary server flows. CSS checks read actual declarations and contrast pairs; they are not a browser engine.

### Browser-discovered regression, fixed test-first

An existing `.button` transition animated its background for 0.15 seconds. Theme changes updated the foreground immediately, briefly mixing Dark text with the old Light fill. The browser measured **1.776:1** in one direction and **2.780:1** in the other.

The new `test_filled_button_does_not_animate_background_during_theme_changes` failed **before** the fix: one failed case in 0.18 seconds. Removing only the background-color transition kept the existing transform movement. All 153 stylesheet cases then passed, followed by the final 943-case suite. Immediate Light-to-Dark and Dark-to-Light rendered checks passed afterward.

## Actual browser verification

Checks used a separate `127.0.0.1:5001` origin, a distinct test session cookie, and a new database under `.tmp/phase7-browser-59e04f43332e441cb37610c12b1878e4/`. No hidden browser-storage writes were used to manufacture results. Choices were made with the real selector; navigation/reload established persistence. Temporary viewport overrides were reset and owned QA servers/tabs were closed.

The restricted process could not initially expose its preview to the browser. A localhost-only preview was then run with the tool's approved sandbox escalation; no firewall, browser security setting, or OS preference was changed.

### Interactive behavior and data protection

- The browser reported a dark device preference. System resolved to Dark; manual Light overrode it; manual Dark worked; returning to System again resolved to Dark while the selector still said Use device setting.
- Choice survived navigation, reload, and an isolated-server restart with a changed signing secret. It also survived clearing the test draft.
- An unfinished `300.` allowance and selected preferences remained intact during switching. A server-rendered invalid `0` allowance, its error, and the valid existing draft remained separate.
- Keyboard Home/ArrowDown selected System/Light, focus stayed on the selector, a visible outline was present, and Tab continued to the following link. An entered 80-character name survived switching.
- Saving the EUR 103.00 sample after switching succeeded. Saving the same 80-character title/content again returned the original `/trips/1` with “already saved.” An independent SQL check found one row before later recovery fixtures were added; the five original columns and schema version 1 were unchanged.
- Saved collection/detail and genuine saved 404/409 recovery views rendered with the live catalog deliberately unavailable. A separately damaged temporary database produced a genuine 503 recovery view. Submitting an old form after changing only the isolated server's signing secret produced the genuine 400 recovery view.
- Ordinary-flow browser console errors were empty before intentional fault/asset/CSP checks. Expected 400/404/409/503 responses, the deliberately missing asset, and CSP blocks are separate intentional fixtures, not unexplained ordinary-flow errors.

### Layout and rendered contrast

The six main page families—home, planner, recommendations, current itinerary, saved collection, and saved detail—were inspected in both themes at **1280px and 360px**: 24 page/theme/width combinations. No horizontal document overflow or text-contrast failure was found after the animation fix. The long saved title wrapped instead of widening the page.

Saved collection/detail/unavailable-record and saved 404/409 recovery checks also covered both widths and themes with the catalog missing. The 503 view was checked at both actual measured widths; a viewport request that had not yet affected the background tab was not counted until a reload confirmed `innerWidth === 360`. The genuine 400 view was checked in both themes at desktop width. Validation errors were checked in both palettes on the planner.

The read-only DOM audit used actual computed foregrounds and composed ancestor backgrounds, with the stricter ordinary-text target unless computed size/weight qualified as large text. Minimum measured text ratios across the main-page matrix were **5.044:1 in Light** and **5.309:1 in Dark**. Decorative SVG/aria-hidden artwork, visually hidden content, fixture banners, and native popup-option rendering were not treated as ordinary page text. Native field/selector text and placeholders were measured separately:

| Actual rendered pair/state | Light | Dark | Target |
| --- | ---: | ---: | ---: |
| Native field text / field fill | 11.747 | 14.240 | 4.5 |
| Placeholder / field fill | 5.374 | 8.357 | 4.5 |
| Field boundary / least-contrasting field or surrounding surface | 3.938 | 5.490 | 3 |
| Appearance-selector boundary / least-contrasting field or page | 3.768 | 5.898 | 3 |
| Selected-interest text / selected fill | 8.650 | 8.170 | 4.5 |
| Selected-interest boundary / least-contrasting selected fill or surface | 4.578 | 5.041 | 3 |
| Keyboard outline / surrounding page | 5.477 | 9.718 | 3 |

These are computed-color measurements plus visual/keyboard checks, not a certification for every browser, popup, font renderer, or future component. Hover color pairs and reduced-motion rules are covered by the declared-style tests; a separate browser hover-state matrix was not automated. The fixed Paris illustration and subtle decorative shadows intentionally retain their artwork colors.

Ignored detailed evidence includes `.tmp/phase7-browser-color-audit.json`, `.tmp/phase7-browser-recovery-audit.json`, and `.tmp/phase7-browser-control-audit.json`.

### Storage failures and script fallback

The ignored, localhost-only `.tmp/phase7_preview.py` supplies visibly labeled, fixed server-injected fixtures. These simulate faults; they do not change actual browser security settings or inject choices through browser automation.

- Getter/read denial and an invalid hostile-looking value started in System with usable controls and no uncaught error.
- Getter/write denial applied a manual choice to the current page with honest non-persistence feedback; planner values remained unchanged.
- A failed write changing Light to Dark returned to the still-remembered Light on ordinary navigation, demonstrating that no false persistence was claimed.
- A first-write-only failure followed by a successful real selection cleared the stale warning.
- An unavailable appearance asset left the root without a chosen attribute, hid/disabled the manual control, displayed ordinary fallback guidance, and used device Dark through CSS—even though Light had previously been remembered at that origin.
- With response CSP `script-src 'none'`, application scripts were blocked, not globally disabled in browser settings. CSS still followed device Dark; the daily preview stayed unavailable as expected. Real server forms completed preferences → recommendations → itinerary → save → list/reopen → clear, retaining the EUR 103.00 sample. Normal scripts later recovered the browser-local Light choice.

### Explicit verification limit

The supported browser capabilities expose viewport testing but no safe device-color-scheme emulation. The user's OS settings were not changed. **A live device Light↔Dark switch and manual Dark against an actually Light device were not exercised in this browser.** The guarded CSS and manual/automatic equality are covered by tests; the current-device System/Light/Dark behavior was verified. Use the manual check below to exercise the remaining device-change scenario. No universal zero-flash claim is made.

## Screenshots and local handoff

- [Light desktop](images/phase-07-light-desktop.png)
- [Dark desktop](images/phase-07-dark-desktop.png)
- [Dark mobile with the long-title fixture](images/phase-07-dark-mobile.png)
- [Unavailable-asset fallback](images/phase-07-asset-fallback.png)
- [Updated ordinary preview](images/phase-07-main-preview.png)

The verified old TripPlanner preview process was refreshed so its cached base template includes the selector. The ordinary application is available at **http://127.0.0.1:5000/**. Its existing home tab was reloaded and showed a working System selector, effective Dark on the current device, and no overflow at its normal 904px viewport. No explicit choice was made at the real origin during QA, and the default saved collection was not created. Only the isolated QA server was stopped; the normal user-facing preview remains running.

## Reproduce tests safely

Use the existing Python environment and Node on PATH, or set `TRIPPLANNER_NODE` to an existing Node executable. Node is only a development-test prerequisite; the Flask app does not require a Node server or npm packages.

```powershell
$phase7Project = (Resolve-Path -LiteralPath '.').Path
$phase7Base = [System.IO.Path]::GetFullPath((Join-Path $phase7Project ('.tmp\phase7-check-' + [guid]::NewGuid().ToString('N'))))
if (-not $phase7Base.StartsWith(($phase7Project + '\.tmp\'), [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected test directory.' }
if (Test-Path -LiteralPath $phase7Base) { throw 'Choose a fresh test directory.' }
.\.venv\Scripts\python.exe -m pytest -q --basetemp $phase7Base
```

Never use the project root, a real collection folder, or an earlier evidence folder as pytest's base: pytest may clear an existing base.

## Small manual checks

For the remaining device scenario, choose System and change the device preference yourself. Confirm the effective palette changes while the selector remains System. Choose Light or Dark explicitly and confirm device changes no longer override it. Return your device setting to your own preference afterward; no automated OS-setting change is needed.

For the learning guide's script-blocked task, use only the isolated wrapper, not the real port/database:

```powershell
$appearanceQaFolder = Join-Path (Resolve-Path -LiteralPath '.').Path ('.tmp\appearance-practice-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $appearanceQaFolder -ErrorAction Stop
$appearanceQaDatabase = Join-Path $appearanceQaFolder 'trips.sqlite3'
.\.venv\Scripts\python.exe .tmp/phase7_preview.py --database $appearanceQaDatabase --port 5001 --revision practice
```

Open `http://127.0.0.1:5001/`, choose an appearance opposite to your device, then stop only that practice server with Ctrl+C. Rerun the same command with `--no-scripts` appended. Confirm ordinary device-fallback help, no fake working selector, and usable server forms. Stop the practice server afterward. Do not clear real browser storage or remove your real database. Temporary fixture files stay under `.tmp`; the wrapper is not production functionality.

Use the [five learning tasks and presentation explanation](phase-07-learning.md) to practice. Phase 7 ends here; selection and specification of the next phase wait for the user.

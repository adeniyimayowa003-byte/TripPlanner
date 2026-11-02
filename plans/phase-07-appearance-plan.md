# TripPlanner — Phase 7 Implementation and Test Plan

**Approved scope:** [Light and dark appearance specification](../specs/phase-07-appearance.md), approved by the user before this plan was prepared.

**Current checkpoint:** SDD step 4 complete — appearance implemented and verified. All **943 cases pass**; the [implementation report](../docs/phase-07-implementation.md) records browser results, one test-first animation regression, isolation, and the explicit device-switch verification limit. The [student guide](../docs/phase-07-learning.md) explains the feature. The next phase has not started.

**Baselines:** All **676 existing pytest cases passed** in 16.60 seconds at planning and again in 21.97 seconds before test edits, each using a fresh validated project-local temporary directory. The default saved-trip database is still absent. Node is already available for development tests (verified version v24.22.1); it is not a new production dependency.

## 1. Outcome and boundaries

Give the customer a labeled **Appearance** selector with **Use device setting**, **Light**, and **Dark**. Remember an explicit choice for this browser/origin, apply it without losing work, and keep every current application page readable.

Keep Flask, the existing design, and ordinary CSS/JavaScript. No new route, server preference, cookie, database column, account, frontend framework, package, extra AI behavior, or change to recommendation/scheduling rules is planned.

The chosen mode is not always the effective palette: **System + a dark device = a dark page, while the selector still says Use device setting.**

## 2. SDD delivery sequence

1. **Specification — approved:** The linked specification is the behavior contract.
2. **Planning — complete:** This file defines boundaries, responsibilities, testing, and implementation order.
3. **Testing — complete:** Added 266 cases and a test-only actual-script harness; discovery succeeds, helper checks run, expected failure groups are inspected, and all retained cases pass. See the [results and limitations](../docs/phase-07-testing.md).
4. **Implementation — complete:** Shared accessible control, safe script, semantic palettes, 943 passing cases, actual browser checks with documented device-emulation limits, and the learning guide are delivered. One browser-discovered regression was defined and failed before its fix.

During step 3, edit only tests/helpers and checkpoint documents. Do not add production script stubs, CSS palettes, header controls, skips, or xfails to avoid missing functionality. Planning is not permission to bypass the testing gate. Material behavior changes still require a revised specification and approval.

## 3. Planned files and responsibilities

| File/area | Responsibility |
| --- | --- |
| `templates/base.html` | One local early script; shared labeled selector, fallback guidance, and concise status region. All pages inheriting this layout receive the feature. |
| `static/js/appearance.js` — new | Validate/read the chosen enum, apply it early, bind after DOM readiness, persist explicit choices safely, and explain failed persistence. No travel-data access. |
| `static/css/style.css` | Semantic light/dark palettes, device-based fallback, all affected component colors, native control color scheme, responsive header, focus, and reduced-motion compatibility. |
| `tests/test_appearance_script.py` — new | Pytest-controlled execution of the actual production script in isolated JavaScript contexts. |
| `tests/appearance_harness.cjs` — new, tests only | Small standard-library Node `vm` harness with DOM/storage stand-ins; no replacement implementation of theme logic. |
| `tests/test_appearance_flow.py` — new | Shared-page HTML/assets, control semantics, error views, and unchanged draft/snapshot/storage contracts through Flask's test client. |
| `tests/test_appearance_styles.py` — new | Declared palette/selector coverage and contrast arithmetic from actual stylesheet values; not a substitute for rendered browser checks. |
| Documentation | Test-first checkpoint, final verification, README test/runtime notes, and beginner-friendly guide with the five approved practice tasks. |

`app.py`, `plan.js`, the recommender/scheduler, snapshot/storage modules, database schema, and existing travel data do not need feature changes. Do not refactor them merely to add appearance.

## 4. Minimal appearance architecture

### 4.1 Chosen mode and CSS state

Use one recognized root attribute: **`data-appearance="system|light|dark"`** on the document element. It records the **chosen mode**, not a guessed effective palette. A page initially has no such attribute; that means automatic CSS fallback.

- Light is the CSS default when a dark preference is not reported.
- Explicit `light` uses the light palette regardless of the device.
- Explicit `dark` uses the dark palette regardless of the device.
- A dark device media query applies the dark palette only when the root is **neither manual Light nor manual Dark**. This includes `system` and an absent attribute.
- CSS supplies the appropriate `color-scheme` for native controls.

CSS media queries automatically respond to device changes. Do not add a second JavaScript device-state machine or unnecessary `matchMedia` listeners. JavaScript stores/changes only the chosen mode; CSS resolves the effective appearance. This also makes device-based fallback work when the appearance script cannot run.

Use a simple, explicit stylesheet structure. If the dark palette is declared in both manual and automatic selector contexts, test that their semantic token maps agree. Do not duplicate independent palettes that drift, rely on a global inversion filter, or put dark rules only on the home page.

### 4.2 Early script and DOM readiness

Load `/static/js/appearance.js` once as an ordinary local script in the shared `<head>`, before the main stylesheet. It is intentionally not deferred/async/module-loaded: the small recognized root choice should be applied before the styled page is shown where possible.

The script has two small stages:

1. **Early:** Safely read/normalize the remembered choice and set only a recognized root value. This stage cannot assume the header exists yet.
2. **DOM ready:** Find/bind the selector, select the chosen value, install its change handler, and only then reveal/enable the working control and hide fallback help. Handle both a still-loading document and an already-ready document.

The script must not fetch, navigate, submit forms, rewrite page content, focus controls, scroll, read travel fields, or touch Flask/SQLite. Use ordinary attributes, control values, and `textContent` for fixed messages, never `innerHTML` or stored text interpolation.

### 4.3 Header contract

- A native select with ID **`appearance`**, associated visible **Appearance** label, and three options: `system` → Use device setting, `light` → Light, `dark` → Dark.
- Put the selector outside all planner/save/clear forms. It does not submit a preference to Flask and needs no CSRF token.
- Use **`appearance-control`** as the wrapper ID. Keep the wrapper hidden and the select disabled in initial HTML. Targeted styles must respect `[hidden]`, rather than accidentally showing it because another rule uses flex/grid.
- Include ordinary fallback help with ID **`appearance-fallback`**, outside the initially hidden control wrapper. It remains available if scripts are disabled, blocked, missing, or fail to initialize; it must not depend only on `noscript`. Test hidden ancestors too, not just whether the fallback node exists.
- Include a concise **`appearance-status`** region using polite status semantics, initially empty. Do not announce the whole page or show a fake persistence confirmation on startup.
- Preserve all existing navigation, skip links, labels, feedback, and page headings. Let the header wrap into an intentional second row when necessary rather than compressing or hiding important actions.

Prefer ordinary fallback text rather than adding a new header `noscript`. The existing daily-preview test currently inspects the first `noscript`; that must continue to describe its actual daily preview.

## 5. Storage and event contracts

Use only **`tripplanner.appearance`**, with the enum strings `system`, `light`, and `dark`. Treat all other/missing/unreadable values as System.

| Event | Root/control state | Storage/status behavior |
| --- | --- | --- |
| Initial page load | Recognized remembered choice, otherwise System | Read safely; no writes or false Saved status. |
| Explicit valid selection | Apply immediately; retain selector focus/current values | Attempt to write just the enum to this key. |
| Storage write succeeds | Keep the selected mode | Clear an earlier failure notice; concise honest feedback may confirm the choice. |
| Storage read fails | System, with working manual controls once initialized | No uncaught exception or raw details. |
| Storage write fails | Keep the newly selected mode for this document | Explain that the browser could not remember it; do not claim persistence. |
| Choose System after any state | Root/control say System; CSS follows the device | Attempt to store `system`, just like the other explicit choices. |

Guard **access to `window.localStorage` itself**, not only `getItem`/`setItem`: the getter can throw. Do not use `clear`, remove unrelated keys, serialize travel data, or write automatically during initial recovery from invalid storage.

Read and write failures are independent. For example, an initial read can fail but a later write can succeed; a later successful selection must clear stale non-persistence feedback. A malformed/unknown selection value must never reach the root attribute; normalize safely rather than interpolating arbitrary text.

No live cross-tab synchronization is added. Another loaded page reads the latest value when it loads; the current page may retain its selection until changed/reloaded. Clearing a draft, saving/reusing a snapshot, changing the signing secret, or restarting the server does not own this browser-local key.

## 6. Palette and component audit

The existing stylesheet has shared variables **and many literal colors**. `--green` currently serves text accents, filled buttons, skip links, the brand mark, and the itinerary cost card. One brightened variable cannot safely do all these jobs in Dark mode.

Introduce understandable semantic roles, retaining aliases where that makes existing styles clearer:

- Page, raised/alternate surfaces, ordinary/muted text, text accents, and decorative separators.
- Action background/foreground/hover, native field background/text/border/placeholder, selected-field background/text/border, and keyboard focus.
- Notice/warning/error background/text and essential error border.
- Emphasis-card background/foreground/muted text, separate from ordinary green text accents.
- Relevant artwork/label colors where text-bearing category or example cards require them.

Audit actual usages: home example cards and their captions; header/footer; form/native controls and checked interests; optional/help/invalid text; daily previews; recommendation/category/score/reason cards; tags; save/local notices; saved empty/unavailable cards; days/slots/gaps; and every nested text color in the filled cost card. Decorative SVG artwork may keep intentional colors, but text-bearing cards cannot remain unreadable light hardcodes.

Use the approved **4.5:1 ordinary-text** and **3:1 large-text/essential-control/focus** targets. Test actual declared token pairs, not copies of palette constants embedded only in tests. Default to the stricter text target where the size/weight classification is uncertain. Essential interactive boundaries are not the same as decorative card separators; do not demand 3:1 for every decorative line.

Do not redesign spacing, typography, icons, or illustrations beyond what the selector and readable palettes require. Retain reduced-motion behavior, avoid whole-page color-flash animations, and verify hover, checked, invalid, focused, disabled, and active-navigation states in both themes.

## 7. Pytest strategy and environment

### 7.1 Retained suite and isolation

Retain the 676-case baseline, existing temporary database fixture, catalog independence, CSRF, exact money, and snapshot/duplicate coverage. Tests must not touch the default collection or the user's browser preferences.

Before test edits, fingerprint production/assets and retained tests. Use a new validated `.tmp` base directory for pytest; never reuse the real collection folder, workspace root, or earlier evidence as its base.

No existing-test migration is currently required if the ordinary header fallback is used. If implementation genuinely requires another earlier `noscript`, narrow the daily-preview test during **test definition** to find the daily/allowance fallback among all `noscript` elements, keeping its original meaning. Do not silently weaken that assertion during implementation. Keep page-feedback assertions scoped correctly if a new status region is present.

### 7.2 Execute the real JavaScript through pytest

Pytest will invoke the already-available Node executable with a **test-only** standard-library `vm` harness. This runs the actual future `static/js/appearance.js`; the harness supplies minimal document/control/storage stand-ins but does not reimplement appearance decisions.

Resolve Node from an explicit optional `TRIPPLANNER_NODE` executable path or the `node` command on PATH. Do not commit this machine's absolute runtime path. No npm, package install, browser driver, or production Node server is involved. Document this development-test prerequisite in the final README.

Bound subprocess/VM execution, capture a small structured result, and surface actionable failures. An absent runtime is an environment problem to resolve, **not** a skipped test or an expected missing-feature failure. Test collection must not import/read the missing production file at module import time.

The harness exercises the script in a fresh context per case, including loading-before-header and already-ready documents. Cover:

- Missing, recognized, invalid, HTML-like, wrong-case, and whitespace-padded stored values; only the three supported enum strings reach root/control state.
- Early root application before DOM readiness; safe binding after readiness; missing control/helper nodes do not break ordinary page execution.
- No writes on initial load, including invalid data/read failure; no operations on other keys.
- Explicit Light/Dark/System selections and persistence of exactly the chosen enum.
- Getter, `getItem`, and `setItem` failures; selected state remains accurate, feedback is honest, and a later successful write clears an earlier failure notice.
- No trip/name field changes, form submissions, navigation, focus calls, scroll calls, external requests, or mutation of unrelated state. Sentinel values make unintended writes detectable.
- The selector remains unavailable until binding works. Fallback/status changes match initialization and persistence outcomes without unsafe HTML.

These are JavaScript logic/DOM-contract unit tests, **not** a real browser or CSS engine. They cannot establish media-query response, rendered contrast, actual keyboard behavior, or a flash-free first paint.

### 7.3 HTTP integration coverage

Use Flask's existing temporary app/client fixtures and actual parsed HTML to check:

- The header contract on home, planner, recommendations, current itinerary, saved empty/populated collection, saved detail, validation pages, and app-rendered 400/404/409/503 views.
- Associated label/three option values, initial hidden/disabled state, ordinary fallback/status, no containing trip form, and one script asset in the head before the stylesheet, without async/defer/module attributes.
- Local script/stylesheet serving, no external assets/services added, and existing daily-preview script/fallback still available.
- No theme fields in the draft, snapshot, fingerprint, duplicate key, database schema, or request processing. Existing rejected-name/token/fingerprint behaviors remain unchanged.
- Saved list/detail/recovery rendering with live catalog/generator access forbidden and drafts preserved. Adding shared appearance markup must not introduce a hidden catalog/storage dependency.
- Ordinary server form/save/list/view/clear journeys without executing application JavaScript.

Use real saved records only in test-local SQLite files. Client-supplied extra appearance fields never become authoritative travel data. Browser tests, not a fabricated Python theme engine, establish that switching on an existing save form does not make it stale.

### 7.4 Styles and contrast checks

Check declared light/manual-dark/automatic-dark palette coverage, native `color-scheme`, manual-override exclusion in the device media query, hidden-control styles, reduced-motion retention, and the absence of a blanket inversion filter.

A small test-only reader may extract the intentionally simple palette rule declarations and compare their semantic values. Do not pretend it resolves the full cascade/layout. Contrast arithmetic must read the production palette and validate named foreground/background pairs independently; missing/malformed tokens fail clearly. No duplicated test-only palette or pre-approved screenshot is a correctness oracle.

Real computed colors, ancestor backgrounds, transparency, font sizing, focus outlines, native selects, and overridden hardcoded rules still require the browser audit below. Passing token ratios alone does not prove a card is using those tokens.

### 7.5 Concrete test-definition contracts

The tests make the planned semantic roles explicit. Declare all of these in the Light/default, manual-Dark, and automatic-Dark palette contexts; aliases may refer to shared root values:

| Purpose | CSS properties |
| --- | --- |
| Page/surfaces/text | `--page-bg`, `--surface-bg`, `--text`, `--text-muted`, `--accent-text`, `--line` |
| Filled actions | `--action-bg`, `--action-text`, `--action-hover-bg` |
| Native fields/focus | `--control-bg`, `--control-text`, `--control-border`, `--placeholder-text`, `--focus-ring` |
| Selected preferences | `--selected-bg`, `--selected-text`, `--selected-border` |
| Notices/warnings | `--notice-bg`, `--notice-text`, `--warning-bg`, `--warning-text` |
| Errors | `--error-bg`, `--error-text`, `--error-border` |
| Filled estimate/emphasis card | `--emphasis-bg`, `--emphasis-text`, `--emphasis-muted` |

These are naming/implementation contracts for approved roles, not extra product features. Existing names may remain aliases, but representative component declarations must actually reference the intended role. Manual/automatic Dark resolve to the same 27 role values. Decorative `--line` has no essential-boundary contrast threshold.

The test-only CSS reader intentionally supports simple opaque sRGB colors/aliases and positive `(prefers-color-scheme: dark)` media queries (optionally `screen`/`all` with `and`). It rejects inverted queries, unrelated exclusions, and descendant selectors masquerading as root/manual guards. Use this simple stylesheet structure; more elaborate CSS grammar is not needed for the approved feature. Browser auditing still checks real computed results.

Independent helper checks validate actual JavaScript execution, lifecycle/boolean attributes, observable storage/page side effects, bounded execution, CSS parsing, selector/media guards, and contrast arithmetic. No implementation stub or test-only theme engine is provided.

## 8. Test-definition gate before implementation

1. Record the fresh 676-case baseline and source/test fingerprints.
2. Add the new pytest files and harness only; resolve Node/test-environment issues first.
3. Collect the entire suite successfully, with no missing-file imports during discovery or fixture errors mistaken for feature failures.
4. Run the suite and inspect all failure groups. Missing header/script/CSS is expected; broken helpers, inaccurate contrast fixtures, and unrelated regressions are not.
5. Prove helper behavior independently where necessary, including real script execution in isolated contexts rather than a harness that substitutes its own theme implementation.
6. Record actual pass/fail/error/skipped counts, legitimate existing-test changes if any, and unchanged production files/default database. Do not promise a predetermined test count.
7. Only after this gate, implement the approved feature.

**Gate result:** Complete. All 942 cases collect; the full run is 766 passed/176 expected failures in 28.41 seconds, with no errors/skips. All 676 retained cases pass; all 25 fingerprinted production files and 15 retained test/fixture files are unchanged. The [testing report](../docs/phase-07-testing.md) records each failure group, isolation, runtime prerequisites, and verification limits.

## 9. Implementation slices after the testing gate

### A. Semantic palettes and automatic fallback

Replace affected literal colors with semantic roles, add explicit and device-based palettes and `color-scheme`, preserve readable Light mode, and audit both themes. **Learning focus:** CSS variables, selectors, media queries, contrast, and chosen versus effective appearance.

### B. Small appearance script

Implement the early recognized root state, DOM-ready binding, explicit-change persistence, and graceful storage failures against the actual-script tests. **Learning focus:** Events, finite state, `try`/`catch`, local storage, and progressive enhancement.

### C. Shared accessible control

Add the labeled native selector, unavailable-until-ready state, fallback/status, early script loading, and responsive header. Run all shared-page and retained tests. **Learning focus:** Semantic controls, keyboard usability, page lifecycle, and not losing form state.

### D. Browser audit and handoff

Check the full appearance journey in actual browser pages, fix observed defects with regression coverage where applicable, run the final suite, and update verification/learning docs. These are slices of one approved feature, not new phases or additional approval gates.

## 10. Real-browser verification

Use a separate localhost test origin/port and temporary database. Existing browser preferences on port 5000 and the user's real collection remain untouched. Start/stop only owned test processes/tabs and reset temporary viewport overrides afterward.

- Select modes using the actual control; check root chosen state and **computed** palette/`color-scheme`, navigation, reload, and a restarted server with a different secret.
- Compare System's effective palette with the browser's actual reported device preference. Verify explicit Light and Dark overrides and returning to System.
- Use a documented safe color-scheme emulation capability for simulated device changes if available; never silently change the user's OS/browser settings. If unavailable, record the current-device check and the remaining dynamic-switch verification limit, providing a manual check rather than falsely marking it passed.
- At 360px and 1280px, inspect header/navigation, all major page families, errors/notices, native controls, long saved titles, and card/body overflow in both palettes.
- Check keyboard Tab/selection/focus, entered invalid values, selected interests, unfinished trip names/budgets, and that switching neither submits nor reloads nor unexpectedly moves focus/scroll.
- Switch appearance on a reviewed itinerary and save the EUR 103 sample. Repeating title/content must still reuse the row, with no theme-caused stale form or draft mutation.
- Audit computed foreground/background pairs on body, muted text, buttons, preview/emphasis cards, form fields/placeholders, selected interests, errors, saved/unavailable cards, links, and focus boundaries. Document contrast measurements and any decorative exclusions.
- Test both an unavailable appearance asset and application scripts blocked. In the latter, use a documented isolated-preview CSP such as `script-src 'none'`, not a claim that global browser JavaScript was disabled. Device CSS still applies; manual controls remain unavailable with fallback help, and ordinary server journeys still work.
- Exercise storage-denied/invalid-value cases through isolated test fixtures where supported. Clearly distinguish simulated storage faults from actual browser settings. Do not use hidden browser-state writes or clear the user's storage to manufacture evidence.
- Reopen saved list/detail/recovery with the test preview's catalog unavailable. Appearance must not undo the existing catalog-independent behavior.
- Check ordinary-flow console errors and capture representative Light/Dark screenshots. Intentional CSP blocks/fault fixtures are recorded separately, not counted as unexplained ordinary-flow failures.

A test-only preview wrapper may supply controlled failure fixtures; it must not add production routes, ship a preference backdoor, or change real data. Any unavailable required browser evidence is reported explicitly rather than replaced with a static source assertion or invented success.

## 11. Completion and student handoff

Finish after new/retained tests pass, required usable-browser/contrast checks are established (with any remaining verification limit clearly reported), default storage/preferences are untouched, and docs match the actual feature.

The learning guide explains the changed files, CSS tokens/media queries, mode versus palette, DOM readiness/events, safe local persistence versus session/SQLite, failure handling, and progressive enhancement. Appearance is a customer convenience, not a new AI model or account system.

Include the specification's five small practice tasks and a short presentation explanation. Report actual results, not a promised count or a claim of universal zero-flash behavior.

**Student handoff:** Complete the [five practice tasks](../docs/phase-07-learning.md) and explain why browser appearance is separate from the trip draft, saved snapshot, and AI behavior.

**Next action:** None for this increment beyond the documented student/manual device-switch checks. Phase 7 is delivered; wait for the user before selecting/specifying the next phase.

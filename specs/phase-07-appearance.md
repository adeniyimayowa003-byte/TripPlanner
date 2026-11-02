# TripPlanner — Phase 7: Light and Dark Appearance

**Status:** Implemented after approval, planning, and validated test definition. All **943 pytest cases pass**, including all 676 retained cases and one browser-discovered regression added test-first. See the [verification report](../docs/phase-07-implementation.md) for real-browser results and the explicit device-switch verification limit, and the [learning guide](../docs/phase-07-learning.md). The [red checkpoint](../docs/phase-07-testing.md) remains historical evidence. The next phase has not started.

**Related documents:** [Product specification](../SPEC.md), [completed Phase 6 verification](../docs/phase-06-implementation.md), and [project status](../PLAN.md).

## 1. What we are building and why

Give travelers a choice of **Light**, **Dark**, or **Use device setting**. The appearance should be comfortable to read and remain consistent as they move between TripPlanner pages.

This starts a small customer-preferences feature: appearance only. It does not add customer accounts or change travel preferences, recommendations, budgets, scheduling, or saved snapshots.

Preserve the current warm paper/forest-green identity in Light mode. Dark mode uses dark surfaces, readable light text, and compatible green accents; it is a deliberately designed palette, not a blanket inversion of the page.

## 2. Scope

- Add an accessible appearance selector to the shared header, available on every application page using the shared layout.
- Support three choices: **Use device setting** (the default), **Light**, and **Dark**.
- Apply a choice immediately without navigation, reloading, submitting a form, or losing entered answers.
- Remember an explicit choice in browser-local storage when available.
- Theme the existing home, preferences, recommendation, current-itinerary, saved-list, saved-detail, empty, validation, and application-rendered recovery views.
- Keep all core planner and saved-trip behavior usable when application scripts cannot run.
- Keep Flask, the existing templates, and ordinary CSS/JavaScript. No frontend framework, new package, external asset, paid service, or database migration is needed.

**Out of scope:** Customer accounts, server-side customer profiles, cross-device/cross-browser preference synchronization, extra accessibility settings, custom colors, maps, exports, new AI behavior, and a general settings dashboard. Framework-generated responses without the shared layout (such as the current default 405), debugger pages, and browser connection-error pages are not redesigned in this increment.

## 3. User journey

1. Open TripPlanner. With no recognized preference, its appearance follows the device/browser light-or-dark setting.
2. Find a visible control labeled **Appearance** in the header.
3. Select Light or Dark. The current page changes immediately; the selector continues to show the chosen mode.
4. Continue planning, save a trip, or open Saved trips. The same remembered choice applies across these pages and after reload/restarting the app.
5. Choose Use device setting to return to automatic appearance.

The control is a real preference selector, not an unexplained moon/sun icon. A decorative icon may supplement its text but never replaces its accessible label.

## 4. Selection and precedence

The **chosen mode** and **effective appearance** are different. Use device setting can be chosen while the page effectively looks Light or Dark.

| Chosen/remembered mode | Device preference | Effective appearance |
| --- | --- | --- |
| Light | Either | Light |
| Dark | Either | Dark |
| Use device setting, absent preference, or unrecognized preference | Light/no dark preference | Light |
| Use device setting, absent preference, or unrecognized preference | Dark | Dark |

- A manual Light/Dark choice overrides the device preference.
- With Use device setting selected, a device preference change updates the current page while it remains open, where the browser provides that notification.
- Device changes must not override a manual choice or change what the selector says was chosen.
- If the browser cannot report a device appearance preference, automatic mode falls back to Light.
- Selecting a mode changes appearance only. It must not submit any trip form, move focus unexpectedly, reset the scroll position deliberately, or replace a draft.

## 5. Remembering the preference safely

- Use one local-storage key, **`tripplanner.appearance`**, with recognized values **`system`**, **`light`**, or **`dark`**.
- Read the recognized choice when a page loads. Do not create/write the preference merely because someone visits a page; persist a value only after an explicit selection.
- Treat a missing, invalid, unknown, or unreadable value as System. Never insert an arbitrary stored string into HTML, CSS, a class name, or an attribute.
- Store only the appearance enum. Do not copy travel preferences, itinerary data, titles, identity, or personal information into this key. Do not clear or modify other browser-storage keys.
- The choice belongs to the **browser profile and origin**, not to a customer account or a saved trip. Another browser can choose differently despite seeing the same shared saved-trip collection.
- The origin includes scheme, host, and port: `127.0.0.1:5000`, `localhost:5000`, and a test preview on another port do not share this preference automatically.
- The remembered choice is independent of Flask's signing secret and SQLite. Clearing a draft, saving a trip, or browsing saved pages must not reset it.
- Clearing site/browser storage can remove the preference. Do not promise persistence across private-browsing sessions, cleared storage, or browser restrictions.
- Immediate synchronization between already-open tabs is **not required**. Each newly loaded page reads the latest remembered choice. An already-open tab may retain its current mode until reloaded or changed there.

### Storage failures

Storage is an enhancement, not a requirement for using the site:

- If reading storage fails, automatic appearance still works without an uncaught error.
- If writing fails, apply the selected mode to the current document and keep the control accurate. Do not undo the visible selection or disable planning.
- Explain calmly that the choice applies to this page but the browser could not remember it. Do not claim it was saved, display raw exception details, or guarantee it survives navigation/reload.
- If the user chooses System in this temporary state, follow current device appearance for that document.

## 6. When scripts are unavailable

- CSS alone follows the device appearance when possible, with Light as the fallback.
- A previous manual choice in local storage cannot be recovered by CSS alone. If the appearance script is blocked/unavailable, device appearance wins for that visit. Do not claim the saved manual choice is still applied.
- The manual selector must not look usable when it cannot work. Keep it hidden or disabled until the appearance behavior initializes successfully.
- Provide understandable fallback guidance where needed, including when a script fails to load despite JavaScript otherwise being enabled. Do not rely solely on a `noscript` message for that case.
- Preferences submission, recommendations, itinerary generation, saving, listing, reopening, editing, and draft clearing continue through their existing server-rendered forms and links.

## 7. Appearance coverage and readability

Apply a coherent palette across the whole current interface, not only the body background:

- Page backgrounds, raised surfaces, headers, footer, headings, ordinary/muted text, links, borders, and separators.
- Primary/secondary buttons, hover/active/disabled states, native inputs/selects, placeholders, checkboxes, selected interests, and family preferences.
- Budget previews, recommendation categories and match reasons, tags, day/slot cards, empty slots, estimates, source links, and explanatory notes.
- Save forms, local/shared notices, collection cards, unavailable records, UTC labels, historical-snapshot notices, empty states, and read-only saved details.
- Field errors, associated error text, feedback/status messages, warning notices, and the existing application-rendered 400/404/409/503 recovery views.
- Skip links, keyboard focus, and active navigation indicators.

Use reusable semantic colors so text accents and filled-button surfaces can have different appropriate foregrounds. The current stylesheet contains both variables and hard-coded colors; all affected components need an audit. Do not apply a global invert/filter to fix dark mode. Decorative Paris artwork may retain intentional illustration colors, provided its surrounding labels/cards remain readable and it does not become a bright full-page surface.

**Project readability targets:** At least 4.5:1 contrast for ordinary text and 3:1 for large text and essential control/focus boundaries against their backgrounds. Check actual rendered combinations, including text on green buttons, muted notes, invalid fields, and selected options. Color is never the only error/selection indicator.

Expose the effective light/dark `color-scheme` so browser-rendered controls can match. Apply the resolved preference early enough to minimize a wrong-theme flash on navigation; do not promise a zero-flash guarantee on every browser/network. Do not add decorative transitions that flash the whole page; respect reduced-motion preferences.

## 8. Accessibility and layout

- Provide a programmatically associated Appearance label and descriptive option text.
- Support keyboard focus, selection, and visible focus in both palettes. Do not force a mouse-only toggle or a custom widget when a native selector suffices.
- Keep the chosen mode discoverable; an icon or color alone is insufficient.
- If announcing a preference/storage change, use concise non-disruptive status feedback. Do not steal focus or announce the entire page on every change.
- Keep navigation, selector, and main actions usable at 360px and 1280px widths without horizontal overflow or obscured controls.
- Preserve form labels, error associations, entered invalid values, current selections, headings, and existing navigation semantics.

## 9. Data and existing-feature protection

- Appearance never changes recommendation scores, eligibility, schedule allocation, monetary calculations, or source links.
- Do not add appearance to the trip draft, snapshot payload, content fingerprint, duplicate key, saved-trip row, or database schema. Switching theme must not make a save form stale or create another identical saved trip.
- Switching while a trip/name field contains unsaved text must retain that text and all other current form values.
- Clearing a draft must leave appearance and saved trips alone; viewing a saved trip must not restore or replace a draft.
- Shared theme rendering must not add a catalog/draft/database lookup. Saved list/detail and saved recovery pages retain their catalog independence.
- No new tracking, analytics, external requests, or customer data collection is introduced.

## 10. Concrete acceptance examples

1. **Default:** No stored choice + dark device preference produces a dark page with Use device setting selected. With no supported device preference, the page is Light.
2. **Manual override:** Select Light while the device prefers Dark. The page becomes Light and stays Light through navigation and reload, with Light selected.
3. **Dark override:** Select Dark while the device prefers Light. Home, form, recommendations, itinerary, saved pages, and app recovery views use the dark palette with readable controls/notes.
4. **Return to automatic:** Choose Use device setting. The page follows the current device preference; later device changes affect automatic mode, not a manual mode.
5. **Preserve work:** Type an unfinished budget/name, or show a server-side validation error, then switch appearance. Input, errors, selections, and the current draft do not change or disappear.
6. **Saving is unchanged:** Review an itinerary, switch appearance, and save it. There is no stale-form rejection caused by theme; repeating the same title/content still reuses the existing row.
7. **Storage denied:** Reading/writing browser storage throws. The app still loads; a manual selection works for this page, with honest non-persistence feedback and no uncaught exception.
8. **Unknown stored value:** Invalid text falls back to System, is not executed/interpolated, and does not alter other keys. A later explicit valid choice can replace this app's preference value.
9. **Script blocked:** CSS follows the device, even if a manual choice was stored earlier. No fake working selector appears, and the ordinary planner/save/list/view flow still works.
10. **Independent storage:** Restart the server/change its signing secret or clear a draft. The recognized browser choice remains available when scripts/storage work. Another browser/origin may have a different preference.
11. **Historical reads:** With today's catalog unavailable, saved list/detail and saved 404/409/503 pages still render their applicable appearance without catalog access or a changed draft.
12. **Usability:** At 360px/1280px, keyboard and pointer users can select modes and reach existing actions. Text, focus, errors, warnings, selected fields, and long saved titles remain readable in both palettes.

## 11. Verification and learning handoff

After approval, the implementation/test plan must distinguish what pytest can establish from real browser evidence. Pytest unit/integration tests cover the applicable rendered structure, safe defaults/contracts, protected data behavior, and retained routes. Browser checks are required for actual palette changes, keyboard behavior, storage/reload, device-preference precedence, denied storage, script-blocked fallback, contrast, and responsive layout. A static HTML/string check is not proof that interactive appearance works.

Retain the currently passing 676-case baseline unless an explicitly documented expectation must change for the approved UI. Any discovered defect gets a regression check before its implementation fix where applicable. Tests use isolated origins/storage and temporary databases; do not clear the user's real preferences or saved collection for testing.

The student guide must explain semantic CSS variables, chosen versus effective state, device media queries, browser-local persistence versus SQLite/session data, events, safe storage access, progressive enhancement, and why appearance is not an AI feature.

Provide these small practice tasks after implementation:

1. Choose Dark, navigate to Saved trips, reload, and explain why the choice remains.
2. Choose Use device setting and explain how it differs from choosing Light or Dark explicitly.
3. Type a trip name, switch appearance, and show that saving/duplicate behavior is unchanged.
4. Test the documented script-blocked fallback and explain why it cannot read a stored manual choice.
5. Locate one semantic color and one persistence/error-handling check; explain their jobs during the presentation.

## 12. Approval gate

The user approved this scope. Specification, [planning](../plans/phase-07-appearance-plan.md), [test definition/validation](../docs/phase-07-testing.md), and [implementation](../docs/phase-07-implementation.md) are complete in that order. All 943 cases pass; browser evidence and its remaining device-emulation limit are recorded, with explanations/practice tasks in the student guide. Real browser preferences and the default saved collection were not changed for QA. The user requested leaving the next phase for later.

No fixed timeline is introduced. Material scope changes require a specification revision and approval.

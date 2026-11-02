# Phase 7 explained: Appearance preferences

TripPlanner now has an **Appearance** selector with **Use device setting**, **Light**, and **Dark**. It changes the interface immediately and can remember an explicit choice in the customer's browser.

This finishes the appearance feature only; it does not start the next phase. For the actual verification results and any remaining browser-check limitations, see the [implementation report](phase-07-implementation.md). The [approved specification](../specs/phase-07-appearance.md) explains the full behavior contract.

## 1. What we built, and why

Customers do not all prefer the same screen appearance. Light preserves TripPlanner's warm paper-and-green design; Dark uses darker surfaces and readable light text. Use device setting follows the preference reported by the browser.

The selector belongs to the shared header, so the same feature appears on the planner, recommendations, itinerary, saved trips, and application-rendered recovery pages. We did not need a separate implementation on every page.

This is a customer convenience, not a new AI feature. It does not train a model, change recommendation scores, or generate a different itinerary. It also does not create customer accounts or a server-side preferences profile.

## 2. Your choice and the visible result are different

The **chosen mode** is what the selector says. The **effective appearance** is the palette the browser actually displays.

| Chosen mode | Device prefers Light | Device prefers Dark |
| --- | --- | --- |
| Light | Light | Light |
| Dark | Dark | Dark |
| Use device setting | Light | Dark |

For example, Use device setting can produce a dark page while the selector still correctly says Use device setting. It has not silently changed your choice to Dark.

JavaScript puts the chosen mode on the document's outermost element:

```html
<html lang="en" data-appearance="system">
```

Only `system`, `light`, and `dark` are accepted. Missing or unrecognized stored values become `system`; arbitrary stored text is never inserted into the page.

## 3. CSS chooses the colors

The [stylesheet](../static/css/style.css) uses **semantic CSS variables**: names describing what a color does, rather than simply what it looks like.

Examples include:

- `--page-bg`: the page background.
- `--text` and `--text-muted`: ordinary and supporting text.
- `--action-bg` and `--action-text`: a filled button and its readable text.
- `--control-border` and `--focus-ring`: input boundaries and keyboard focus.
- `--error-bg` and `--error-text`: validation feedback.

There are 27 palette roles across page/surface/text, actions, fields/focus, selected preferences, notices, warnings, errors, the estimate card, and separators. You do not need to memorize them. Understand that a component asks for a role, and the current palette supplies its value.

For example, a primary button uses:

```css
.button-primary {
  background: var(--action-bg);
  color: var(--action-text);
}
```

The button code stays the same in both themes. Only the variables change. Keeping button fill separate from green accent text matters: a color that makes readable text on a dark page may need a different foreground when used as a filled button.

Light is the default palette. An explicit `data-appearance="dark"` selects Dark. Automatic Dark uses this guarded media query:

```css
@media (prefers-color-scheme: dark) {
  :root:not([data-appearance="light"]):not([data-appearance="dark"]) {
    /* Dark palette values */
  }
}
```

Read this as: “If the device prefers Dark, apply these colors only when the customer has not manually chosen Light or Dark.” This includes System and a missing attribute. Without a reported dark preference, the Light defaults remain.

CSS responds to device-preference changes in automatic mode; JavaScript does not need a second device-tracking system. The `color-scheme` property also tells the browser which native control appearance to use. This is a designed palette, not an inversion filter.

## 4. JavaScript has two small jobs

Read the [appearance script](../static/js/appearance.js) in two stages.

First, it runs early in the page's `head`, before the stylesheet. It safely reads a remembered choice, validates the value, and sets the root attribute. This helps reduce a wrong-theme flash during navigation, but is not a universal zero-flash guarantee.

Second, it waits until the header is available. When the document is still loading, `DOMContentLoaded` is the event saying the initial HTML has been parsed. If the document is already ready, setup runs immediately.

Setup finds the appearance nodes, sets the selector to the chosen value, installs one `change` handler, and then enables/reveals the control. A **handler** is simply a function that runs in response to an event.

When the customer changes the selector, that handler:

1. Checks that the value is one of the three supported modes.
2. Updates the root attribute immediately.
3. Tries to remember that same enum value.
4. Shows calm feedback if remembering fails, or clears an earlier failure notice after success.

It does not reload the page, submit a form, move focus, or read and replace trip fields. Therefore, unfinished budget or trip-name text stays where the customer left it.

## 5. Where the preference lives

The browser stores one key: `tripplanner.appearance`. Its value is only `system`, `light`, or `dark`.

Keep these three storage responsibilities separate:

| Information | Where it belongs |
| --- | --- |
| Appearance choice | Browser-local storage for this profile and origin |
| Current trip draft | Existing Flask session |
| Saved itinerary snapshot | Existing SQLite collection |

An **origin** includes scheme, host, and port. `127.0.0.1:5000`, `localhost:5000`, and a preview on another port are different origins. A different browser profile can also have a different choice. This is not cross-device account synchronization; already-open tabs are not immediately synchronized either.

Changing appearance must not change a snapshot or its fingerprint. The same title and trip content still represent the same saved trip, whether viewed in Light or Dark. Clearing a draft does not own the appearance key. Clearing site storage, private-browsing restrictions, or browser policy can prevent persistence.

## 6. Why the script uses `try` / `catch`

Browsers can deny storage access. Even accessing `window.localStorage` can throw before `getItem` or `setItem` runs.

A `try` block attempts an operation. Its `catch` block handles failure without stopping the rest of the page.

The initial read and each later write are guarded independently. A failed read does not prove that all later writes will fail. There are no writes merely because a customer visits a page.

If a write fails, the selected appearance still works for the current page. The status explains that the browser could not remember it; it does not expose technical exception details or promise that the choice survives reload. A later successful selection clears the stale warning.

## 7. The site still works without the appearance script

This is **progressive enhancement**: start with usable HTML and CSS, then add JavaScript convenience.

In the [shared template](../templates/base.html), the selector begins disabled inside a hidden wrapper. Ordinary fallback text remains outside that wrapper. Only successful setup reveals the working control and hides the fallback.

If the asset is blocked or unavailable, customers do not see a fake working selector. CSS can still follow the device, and the existing server-rendered planning, saving, listing, and reopening flow remains available.

CSS alone cannot read a previously stored manual choice. Therefore, with the script unavailable, device-based appearance wins for that visit. See the isolated script-blocked procedure in the [implementation report](phase-07-implementation.md); do not clear real browser preferences or saved trips to test it.

## 8. How the tests relate to the feature

The tests were defined and validated before production implementation, following the project's SDD workflow.

- [Script checks](../tests/test_appearance_script.py) execute the real JavaScript with isolated DOM/storage stand-ins. They cover remembered modes, events, denied storage, invalid values, and unwanted effects on trip fields or page actions.
- [HTTP checks](../tests/test_appearance_flow.py) inspect the shared HTML and protect existing draft, snapshot, duplicate-save, database, and no-script server behavior.
- [Style checks](../tests/test_appearance_styles.py) read the real palette declarations, compare manual/automatic Dark, and calculate named color-pair contrast.

These checks do not replace a real browser. Actual layout, keyboard usability, rendered colors, and device response need browser evidence. The verification report separates those results from automated assertions.

## 9. Five small practice tasks

1. Choose Dark, open Saved trips, and reload. Explain why the choice can remain even though appearance is not in the saved itinerary.
2. Choose Use device setting. Explain why the selector can say this while the page looks Light or Dark, and how that differs from a manual choice.
3. Type a trip name, switch appearance, and check that the text remains. Save the same title/content twice and confirm that appearance does not create another identical saved trip.
4. Follow the documented isolated script-blocked check. Explain why planning still works but a stored manual theme cannot be recovered by CSS alone.
5. Find one semantic color role and one persistence/error-handling test. Describe the responsibility of each without reading the whole file aloud.

## 10. A short presentation explanation

“I added an appearance preference using shared HTML, semantic CSS variables, and a small JavaScript event handler. Customers can choose Light, Dark, or their device setting. The browser remembers only that choice, separately from the trip draft and saved SQLite snapshots. Storage failures do not prevent planning, and CSS still provides automatic appearance if the script cannot run. I defined tests before implementation and checked browser behavior separately. This feature improves usability; it does not change the app's AI recommendations.”

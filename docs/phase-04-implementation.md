# SDD Step 4 — Implementation and Verification

**Scope:** [Approved personalized trip ideas specification](../specs/phase-01-restart.md)

**Status:** Complete for this increment. Daily itineraries and permanent saving are later work.

## What now works

- A refreshed home page explains actual Paris coverage and opens the planner.
- The form collects preferences, previews the daily allowance, and preserves invalid answers with associated errors.
- Valid submissions produce real catalog recommendations with costs, categories, source links, matching reasons, and a stable ranking.
- A browser-session draft supports refreshing results, editing, resuming, and explicit clearing.
- Missing, malformed, unsupported, and no-match states have useful recovery behavior.
- Both state-changing forms require a valid session-bound token.
- Local assets and system fonts keep the core flow independent of internet access or a paid AI service.

## Automated verification

The original testing gate was recorded before implementation: 244 cases collected, with 45 passing and 199 expected failures. Implementation then made the same approved tests pass; no assertions were removed or disabled to obtain green results.

The full suite passed **244 cases**. After the final recommendation-template readability cleanup, the affected 56 route/page/security cases also passed; the 188 domain cases had already passed against unchanged domain code.

| Area | Passing cases |
| --- | ---: |
| Catalog | 13 |
| Money | 39 |
| Preferences | 42 |
| Recommendations | 17 |
| Drafts | 77 |
| Home | 8 |
| Form integration | 14 |
| Trip flow | 22 |
| Form protection | 12 |
| **Total** | **244** |

Run from the project folder:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The full green machine-readable result is in the ignored temporary file `.tmp/phase4-green.xml`. The earlier red report remains in `.tmp/phase-3-red.xml`; the retained checkpoint explanation is [here](phase-03-testing.md).

## Browser verification

The actual Flask application was checked in the in-app browser, using sample data only.

| Check | Observed result |
| --- | --- |
| Normal sample submission | Paris, 3 days, EUR 300, food/history, relaxed/family preference produces 7 ideas, with Le Procope, Luxembourg Gardens, and Seine Riverside Walk first. |
| Budget edit | EUR 60 over 3 days gives approximately EUR 20/day and leaves the 3 eligible free history ideas. |
| Invalid edit | 0 days shows an error summary and field message while retaining the other submitted answers; the prior valid draft remains available. |
| No matches | Food only with EUR 1 over 3 days displays the preference summary, a useful no-match explanation, and Edit preferences. |
| Keyboard flow | Native selection, text entry, Space on checkboxes, Enter on submit/edit/resume/clear, and Tab navigation work. The focused interest checkbox had a visible solid outline. |
| Draft clearing | A confirmation appears and the form becomes blank; the next valid submission creates a new current draft. |
| Daily rounding | EUR 100.01 / 3 displays EUR 33.34. EUR 0.01 / 2 displays EUR 0.01. |
| Invalid preview and bounds | `3e2` and EUR 1,000,000.01 show the placeholder. EUR 1,000,000 over one day displays correctly. |
| Local scripts | No application console errors were observed in the normal preview. |

### Responsive layout

Home, form, and results were rendered in fixed-width browser frames at 360px and 1280px. Screenshots were inspected. Each page's scroll width equaled its available document width, showing no horizontal overflow. The measured content widths were 345px and 1265px because the frames also had vertical scrollbars.

The browser's viewport override did not resize the existing embedded tab, so these explicit frames were used to establish the actual test dimensions. They loaded the real app pages and stylesheet, not recreated screenshots.

### Server-only operation

A temporary second local instance supplied `Content-Security-Policy: script-src 'none'`, with a separate session-cookie name. This blocked the application's scripts without changing the user's browser settings.

The browser's live daily preview stayed at its placeholder, confirming the app script did not run. Submission still produced the correct server-calculated daily amount and recommendations. Edit, regenerate, home/resume, and clear all worked through normal forms and links. The no-script explanatory markup is also covered by the HTML checks.

This is a focused application-script blocking check, not a change to the browser's global JavaScript setting. The temporary instance is not part of the shipped app.

## Preview and 30-second model

The local app is available at [TripPlanner](http://127.0.0.1:5000/). A sample current draft is ready in the checked browser session.

The separate playable 30-second model illustrates the same preferences → ideas → lower-budget journey. It has play/pause, replay, a seek control, and editable sample allowance. It shows three sample matches for clarity; the actual application returns every eligible catalog item.

Playback was checked in the browser, including stopping at 30 seconds. The editable model also correctly excludes a EUR 50 idea for a EUR 149.99 allowance over 3 days, even though the daily display rounds to EUR 50.

The [verified app screenshot](images/tripplanner-results.png) records the actual recommendation page.

## Understand and demonstrate it

Use the [Phase 4 learning guide](phase-04-learning.md) to understand the code, practice calculations, and prepare a presentation explanation.

A short demonstration:

1. Start with Paris, 3 days, EUR 300, and food/history.
2. Explain the interest points and the optional preference bonuses.
3. Lower the total allowance to EUR 60 and predict which paid ideas disappear.
4. Edit one invalid value, correct it, then resume or clear the draft.

The current system is an explainable rule-based recommender using seven illustrative Paris entries. A current draft is session-based; it is not durable SQLite storage. Choosing the next product increment remains separate from completing this implementation step.

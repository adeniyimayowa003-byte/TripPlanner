# TripPlanner — Revised Phase 1 Specification

**Status:** Implemented and verified after specification approval, planning, and test definition/expected-failure validation. All 244 pytest cases pass. See the [implementation report](../docs/phase-04-implementation.md) and [learning guide](../docs/phase-04-learning.md).

**Related specification:** [Product specification](../SPEC.md)

**Requested change:** Restart from Phase 1 with a better, more functional application, continuing in small phases without a fixed timeline.

## 1. The outcome of this phase

A traveler can enter trip preferences, receive personalized place and food ideas from the sample catalog, understand why each idea matched, and edit the preferences to generate different results.

The first phase must deliver a complete working interaction. A successful submission must lead to useful recommendations rather than stopping at a confirmation message.

The existing Flask application, catalog, validation, and styles are the starting point. Restarting the phases does not require deleting the existing project or repeating work that is already useful. The previous completion notes remain historical; the revised Phase 1 is complete only when its new acceptance criteria are satisfied.

## 2. The user journey

1. Open the home page and see what TripPlanner currently helps with and which destination it supports.
2. Select **Start planning** to open the trip preferences form.
3. Choose a destination, number of days, activities and food allowance, interests, and optional preferences.
4. See an approximate daily allowance while entering valid days and budget values.
5. Select **Find my trip ideas**.
6. Review actual catalog recommendations, their illustrative costs, and explanations of the matches.
7. Select **Edit preferences**, change an answer, and submit again to update the results.
8. Return to the home page and use **Resume my trip ideas** while a current draft exists in the same browser session.
9. Optionally select **Clear this draft** to remove the current draft and return to a blank form.

## 3. Scope and data

- Keep Python, Flask, server-rendered HTML, CSS, modest vanilla JavaScript, and pytest.
- Use the existing Paris, France catalog for the first phase. Show this coverage clearly; do not offer destinations absent from the catalog.
- Reuse the existing catalog's stable IDs, categories, interest and preference tags, descriptions, source links, and illustrative EUR costs.
- A recommendation may be an attraction, activity, or restaurant. Its category must be visible.
- New real-world destination research or additional cities are not prerequisites for this phase.
- The main flow must work without internet access, an API key, or an external AI service. Use local/system font fallbacks so external fonts are not necessary for a readable page.

## 4. Page and action requirements

### 4.1 Home page

- Explain the available outcome: find trip ideas based on destination, interests, and budget.
- Give **Start planning** a prominent, working link to `/plan`.
- Show **Resume my trip ideas** when the current browser session contains a valid draft. It opens `/recommendations`.
- Clearly distinguish explanatory content from controls. The **How it works** link may scroll to an explanation section; its wording must not suggest it starts the planner.
- Explain the currently available journey: choose details, find ideas, and refine choices.
- Example content must be labeled as an example and must not look like the user's generated result.
- Every visible planning button or link must perform its labeled action. Unavailable itinerary and saved-trip actions are not shown as enabled controls.

### 4.2 Preferences page: `/plan`

Collect the following information with visible labels and short help text:

| Field | Required behavior |
| --- | --- |
| Destination | Choose from destinations present in the sample catalog. Initially Paris, France. |
| Number of days | A whole number from 1 through 14. |
| Activities and food allowance per person | A total amount in EUR for all requested days, from EUR 0.01 through EUR 1,000,000.00, with at most two decimal places. |
| Interests | At least one interest available for the selected destination. |
| Preferred pace | Optional. Offer no preference and pace choices supported by that destination's tags. The current catalog supports relaxed; active is offered only after matching data exists. |
| Family-friendly preference | Optional checkbox. It boosts explicitly tagged ideas and does not guarantee that every result is suitable for children. |

- Explain that the allowance covers example activities and food ideas. Flights, accommodation, and transport are excluded.
- Update the daily allowance preview when valid day and budget values change. Invalid or incomplete inputs show a helpful placeholder instead of a misleading number.
- The preview is a convenience; the server independently validates and recalculates all submitted values.
- Show selected interest controls clearly and make both the checkbox and its label usable.
- If a valid draft exists, prefill its values when the user returns to the form.
- The submit button says **Find my trip ideas** and sends the form to the server.
- On invalid submission, show a clear error summary and field-specific messages while retaining the submitted answers.
- On valid submission, replace the current draft with the normalized preferences and redirect to `/recommendations`. Refreshing the results must not resubmit the form.

### 4.3 Recommendation page: `/recommendations`

- Show the destination, number of days, total allowance, approximate daily allowance, selected interests, and optional preferences.
- Display matching ideas in the deterministic order defined in section 6.
- For each idea, show its name, category, description, illustrative cost in EUR, matched interests, a plain-language matching reason, and the existing source link.
- Identify a zero-cost catalog estimate as **Free — illustrative estimate**. Other costs are also labeled as estimates.
- Explain that these are alternative ideas. Their costs are not an itinerary total, and listing several affordable items does not mean their combined cost fits the allowance.
- Provide **Edit preferences** and **Clear this draft** actions.
- If no ideas qualify, retain the preference summary and explain how to recover, such as increasing the allowance or changing interests. Do not silently replace the results with unrelated or unaffordable items.
- If no draft exists, redirect to the preferences form with a useful message.

## 5. Validation and money rules

- Validate every submission on the server, including submissions that bypass browser controls.
- Normalize supported destination and interest names without case or surrounding-space differences; store canonical catalog values and remove duplicate interests.
- Validate interests and optional pace against the selected destination's available data. Unknown choices are errors rather than silently accepted values.
- Normalize valid pace values consistently. An absent pace means no preference; an unchecked family-friendly field means false.
- Days must be a whole number in the stated range. Empty, nonnumeric, fractional, and out-of-range values are rejected.
- Budget input accepts plain decimal amounts such as `300`, `300.5`, or `300.50`, ignoring surrounding spaces. Currency symbols, comma separators, scientific notation, more than two decimal places, zero, negatives, non-finite numbers, and values above the stated maximum are rejected with useful messages.
- Monetary calculations must preserve decimal cents. Display EUR values to two decimal places, using decimal half-up rounding for the daily preview.
- Daily allowance is total allowance divided by days. For example, EUR 300 over 3 days displays approximately EUR 100.00 per day; EUR 100 over 3 days displays approximately EUR 33.33.
- Affordability comparisons use the exact total allowance and day count, not the rounded display value. For EUR 100.01 over 3 days, the preview rounds to EUR 33.34, but an idea costing EUR 33.34 is excluded because `33.34 × 3 = 100.02`, which exceeds the allowance.
- Changing form values without successfully submitting does not overwrite the last valid draft. An invalid edit leaves the previous valid results available.

## 6. Personalized recommendation rules

This phase uses an explainable, rule-based recommender. It is a simple AI technique based on human-written rules, without a trained model or language model.

### 6.1 Eligibility

An item qualifies only if all of the following are true:

1. It belongs to the selected destination.
2. It matches at least one selected interest.
3. Its illustrative individual cost fits the daily allowance. Equivalently, `item cost × trip days` must be less than or equal to the total allowance.

Free items can qualify. Pace and family preferences affect ranking after eligibility; they do not introduce unmatched items or override the budget rule.

### 6.2 Score

For every eligible item:

- Add 3 points for each distinct matching interest.
- Add 1 point if the selected pace matches an explicit preference tag.
- Add 1 point if family-friendly was selected and the item has an explicit family-friendly tag.

Multiple interest matches take priority over the two optional bonuses. Missing tags earn no bonus and must not be described as a confirmed preference match.

### 6.3 Stable order and explanations

- Sort by score, highest first.
- For equal scores, sort by illustrative cost, lowest first.
- Then sort by name alphabetically without case differences, followed by stable catalog ID.
- Return every qualifying item from the small catalog, each at most once.
- The same normalized preferences and catalog produce the same ordered results.
- Each explanation names the actual matching interests and any preference bonuses earned. For example: **Matches food and history** or **Matches nature; tagged relaxed and family-friendly**.
- The page includes a brief **How these ideas were chosen** explanation covering the interest score, preference bonuses, and per-item budget filter.
- If no qualifying item carries a selected preference tag, explain that the catalog cannot confirm a match for that preference; do not claim a suitability guarantee.

## 7. Current draft behavior

- Keep one last successfully submitted draft per browser session, including its normalized preferences.
- The draft survives refresh and navigation between the home page, preferences page, and recommendation page within that session.
- Recompute results from the stored preferences and current catalog, so the result remains consistent with the data used by the application.
- Separate browser sessions must not share a current draft.
- **Clear this draft** is an explicit POST action. It clears only that browser session's draft, displays a confirmation message, and returns to a blank form. Ordinary page views never clear a draft.
- Form submissions and draft-clearing actions use CSRF protection. An invalid or absent token must not change the draft.
- Treat an expired, malformed, or no-longer-supported draft as recoverable: show a message and return to the form without crashing.
- Call this a **current draft**, not a permanently saved trip. Resuming after the browser session ends or after server restart is not a Phase 1 guarantee. Durable SQLite saving belongs to a later phase.
- Do not request or store names, email addresses, payment information, or other unnecessary personal details.

## 8. Interface and accessibility requirements

- Use a consistent travel-oriented design with readable typography, clear spacing, and visible primary actions.
- Keep navigation and button labels consistent across pages.
- Make the form and result cards usable at a narrow mobile viewport of 360 pixels and a desktop viewport of 1280 pixels, without horizontal page scrolling.
- Provide semantic page landmarks, one clear main heading per page, visible focus styles, and labels associated with inputs.
- Support the full submit, review, edit, and clear flow using a keyboard.
- Associate errors with their inputs and do not communicate validation or selection using color alone.
- Core form submission, recommendation generation, editing, and draft clearing must also work with JavaScript disabled. The live daily preview may be replaced by explanatory text in that case; the server-calculated result remains available after submission.
- Include working messages for no draft, invalid input, and no recommendations. Empty states must provide a useful next action.

## 9. Concrete acceptance examples

1. **Useful first result:** Choose Paris, 3 days, EUR 300, food and history, relaxed pace, and family-friendly. Submission opens recommendations drawn from the Paris catalog, with reasons and an approximately EUR 100.00 daily allowance.
2. **Ranking matters:** With those preferences, Le Procope earns 6 interest points, Luxembourg Gardens earns 3 interest points plus 2 preference points, and Seine Riverside Walk earns 3 interest points plus 1 pace point. They appear in that order ahead of lower-scoring items.
3. **Budget changes results:** Change the total allowance to EUR 60 for 3 days. No returned item may cost more than EUR 20.00 individually; suitable free items remain eligible.
4. **No matches has a recovery:** Choose food only and EUR 1 for 3 days. The page explains that no food ideas fit this allowance and offers **Edit preferences**; it does not pretend that a restaurant matched.
5. **Editing preserves choices:** Select **Edit preferences** from results. Every saved preference is prefilled, including the checkboxes. A valid edit replaces the draft and changes the displayed results as appropriate.
6. **Invalid edits preserve the valid draft:** Submit 0 days while editing a valid draft. The form shows an associated error and retains the submitted answers. The previously valid draft is not replaced.
7. **Refresh is safe:** Refresh the recommendation page after submission. It displays the current result without a form-resubmission prompt or creating another draft.
8. **Daily rounding is honest:** With EUR 100.01 over 3 days, show approximately EUR 33.34 per day. A fixture item costing EUR 33.34 is nevertheless excluded because its cost multiplied by 3 exceeds EUR 100.01. This checks that display rounding never changes eligibility.
9. **Draft is isolated and clearable:** One browser session's draft is absent from a separate session. Clearing it returns that session to a blank form and removes its resume action.
10. **Unavailable data is honest:** Do not offer active pace while no active-tagged Paris item exists. Selecting family-friendly must not label untagged restaurants as verified family-friendly choices.
11. **Direct navigation is recoverable:** Open `/recommendations` without a valid draft. The application takes the user to the form with a useful message.
12. **Controls work as labeled:** Home, Start planning, Resume my trip ideas, Find my trip ideas, Edit preferences, and Clear this draft all perform the documented action when present.
13. **Accessible and progressively enhanced:** The core flow works by keyboard and with JavaScript disabled; mobile layout and validation feedback remain usable.

Acceptance examples involving catalog names refer to the current sample data. Rule checks must also use small deterministic fixtures so expected matches and ordering can be explained independently of the size of the Paris catalog.

## 10. What comes after this phase

Daily itinerary generation, total itinerary cost checks, durable saved trips, additional destinations, accounts, maps, live travel data, and optional language-model features remain later work. We will choose the next small outcome after this phase works and is understood.

An autonomous tool-using AI agent is not required for Phase 1. The student should first be able to explain how inputs become validated preferences, how catalog items earn scores, and how those scores become visible recommendations.

## 11. Learning and handoff requirements

After implementation, explain:

- What each page does and how a form moves data between the browser and Flask.
- Why server validation remains necessary when the browser already validates inputs.
- How dictionaries, catalog tags, conditions, and sorting implement the recommendation rule.
- Why decimal calculations are used for money and why displayed rounding differs from affordability checks.
- How a browser-session draft supports review and editing, and how that differs from a durable saved trip.
- What the pytest checks prove and how to reproduce a matching or no-match result.

Provide these small practice tasks:

1. Submit a valid trip and explain one recommendation using the point rules.
2. Change only the budget and predict which paid items will disappear.
3. Submit an invalid trip length, correct it, and check that the other answers remain.
4. Edit a draft, refresh results, and clear the draft.
5. Run the tests and identify one unit test and one route integration test.

## 12. Approval and SDD gate

This file defines the implemented personalized trip ideas increment. The completed implementation and test plan is tracked in [PLAN.md](../PLAN.md); verification is recorded in the [implementation report](../docs/phase-04-implementation.md). Future behavior changes still follow the same approval and testing gates.

With specification approval recorded, outline the Phase 1 implementation and test plan. Then define the pytest unit and integration tests and validate that they are discovered and fail for the expected missing behavior. Only after that gate is satisfied may the feature be implemented and integrated. Complete the phase by passing the relevant checks and demonstrating the acceptance flow.

No fixed week count or delivery dates are introduced by this restart.

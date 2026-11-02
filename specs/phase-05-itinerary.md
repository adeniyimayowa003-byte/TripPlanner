# TripPlanner — Phase 5: Daily Itinerary Specification

**Status:** Implemented after user approval, planning, and test-first validation. All 322 pytest cases pass, and the required browser checks are complete. See the [verification report](../docs/phase-05-implementation.md), [learning guide](../docs/phase-05-learning.md), and [historical red checkpoint](../docs/phase-05-testing.md).

**Related documents:** [Product specification](../SPEC.md), [implemented trip ideas specification](phase-01-restart.md), and [Phase 4 verification](../docs/phase-04-implementation.md).

## 1. What we are building and why

TripPlanner already answers **“Which ideas match my trip?”** This increment will answer **“How could I spread those ideas across my days?”**

A traveler can open a suggested daily itinerary from their recommendations. The itinerary will distribute matching catalog items into simple time slots, avoid repeated places, and check the combined cost of each day rather than only the cost of individual ideas.

This is one small product increment, without a fixed timeline. The earlier four steps completed the personalized recommendations feature. This new feature starts its own specification → planning → testing → implementation cycle.

## 2. User journey

1. Enter preferences and open the existing recommendations page as before.
2. Select **Build my daily itinerary** to open `/itinerary`.
3. Review Day 1 through the requested final day, suggested time slots, matching reasons, and estimated costs.
4. See any unfilled slots and explanations of catalog, budget, or preference limitations.
5. Select **Back to trip ideas** to return to `/recommendations`, or **Edit preferences** to change the trip.
6. Submit valid changes, then build the updated itinerary from the new recommendations.
7. Optionally use the existing protected **Clear this draft** action. After clearing, neither recommendations nor an itinerary is available until another valid trip is submitted.

The itinerary action remains available when recommendations are empty. It produces an honest empty itinerary with recovery advice, not an error or invented suggestions.

## 3. Scope and existing behavior

- Reuse the current Paris catalog, validated preferences, rule-based recommendations, exact decimal money calculations, browser-session draft, and visual design.
- Keep the recommendation eligibility, scoring, tie-breaks, and explanations unchanged. The recommendations page still lists alternatives, not a combined itinerary cost.
- Use only eligible recommendations. Do not add unrelated places, unaffordable items, or invented catalog records to fill gaps.
- Keep all requested day sections, including days with no scheduled ideas.
- Never schedule the same stable catalog ID more than once in the entire trip. A small catalog produces gaps, not repeated places.
- The core flow works offline and with JavaScript disabled. No external AI service or API key is required.
- Existing forms, validation, CSRF protection, draft isolation, and recovery behavior must continue working.

This increment does **not** add permanent saving, SQLite storage, accounts, maps, extra destinations, bookings, manual itinerary editing, drag-and-drop, downloads, or an autonomous AI agent. The earlier 30-second walkthrough remains a separate demonstration, not the itinerary engine.

## 4. Scheduling rules

### 4.1 Pace sets the number of slots

| Validated pace | Suggested slots per day |
| --- | --- |
| Relaxed | Morning and Evening: at most 2 ideas |
| No preference | Morning, Afternoon, and Evening: at most 3 ideas |
| Active, only where destination data already supports it | Morning, Afternoon, and Evening: at most 3 ideas |

Relaxed leaves the afternoon open intentionally; this is not counted as a missing slot. Current Paris data still offers only relaxed or no preference. This feature does not enable an unsupported active option.

Slots are suggestions, not appointments. The catalog has no durations, opening hours, dates, or travel times. The page must prominently explain that the order is illustrative and travelers must check opening hours, suitability, and journey times before using it. Do not show invented start times or claim that a venue is open in its assigned slot.

### 4.2 Deterministic selection order

Start with the existing ordered recommendations. A selected item becomes unavailable for every later slot in the trip.

1. Visit each day in numerical order and fill its **Morning** slot with the first unused attraction or activity that fits that day's remaining allowance.
2. For three-slot days, visit each day in numerical order again and fill **Afternoon** using the same rule.
3. Visit each day in numerical order again and fill **Evening** with the first unused restaurant that fits. If no restaurant fits, try the first unused attraction or activity that fits instead.
4. If no compatible item fits a slot, leave it unfilled with explanatory text.

“First” means the existing recommendation order, preserved within each category group. Skip a candidate that cannot fit the current day without removing it from consideration for later days. Do not stop searching just because the highest-ranked unused item is too expensive.

Restaurants are evening suggestions only in this simple model; there is at most one restaurant per day. An evening fallback is labeled as its actual attraction/activity category, never as a meal. Restaurants can qualify through any selected matching interest, not only food.

Filling a slot across all days before moving to the next slot helps spread the small catalog across the trip. It does not guarantee equal numbers or costs on every day. This greedy rule is predictable and explainable, not an optimal route or budget optimizer: daytime choices may use money that would otherwise fit a restaurant, and food-only preferences can leave daytime slots empty.

Do not shuffle results or modify the input preferences, catalog, or recommendation records during scheduling. The same validated preferences and catalog must produce the same itinerary.

## 5. Combined costs and allowance

The existing allowance remains a total **activities and food allowance per person in EUR**, excluding flights, accommodation, and transport.

- A day's estimate is the sum of only its scheduled catalog items. The trip estimate is the sum of all day estimates.
- Before adding an item, require `(current day estimate + item cost) × number of days <= total allowance` using exact decimal arithmetic.
- This gives every day the same exact allowance. Unspent allowance is **not** transferred between days in this increment.
- The trip estimate must also remain at or below the total allowance. Never use the rounded daily preview as a spending limit.
- Show the total allowance, approximate daily allowance, each day's estimate, the trip estimate, and **allowance not allocated to scheduled ideas** (`total allowance − trip estimate`).
- The unallocated amount is not “savings” or a guarantee that the full real trip fits the allowance. Unscheduled meals, extra activities, and excluded expenses are not costed.
- Display EUR amounts to two decimal places. Preserve the existing half-up rounding for the approximate daily allowance.
- Free items retain the **Free — illustrative estimate** label. An empty slot contributes no scheduled cost but must not be described as a free activity or a free meal.

Example: EUR 100.01 over 3 days displays approximately EUR 33.34 per day. Two eligible ideas costing EUR 20.00 and EUR 13.34 must not share one day, because `33.34 × 3 = 100.02`. A pair costing EUR 20.00 and EUR 13.33 can share one day.

## 6. Itinerary page

The page must provide:

- One main heading and a summary of destination, days, interests, pace, family-friendly preference, and allowance.
- One clearly headed section for every requested day, in numerical order.
- Slots in chronological display order within each day, regardless of the order used to allocate items.
- For each scheduled item: name, category, description, illustrative EUR cost, original matching reason, and existing source link.
- A clearly labeled estimate for each day and the whole trip, plus the unallocated allowance.
- A plain-language **How this itinerary was built** explanation covering ranking, pace, category choices, no repeats, equal daily limits, and the greedy limitation.
- **Back to trip ideas**, **Edit preferences**, and the existing protected **Clear this draft** action.

Use the existing responsive, travel-oriented design. At 360px and 1280px widths, keep all content readable without horizontal page scrolling. Controls must work by keyboard, have visible focus, and use semantic links for navigation and a form/button for clearing.

Do not label this as a permanently saved plan or promise that all slots are feasible in the real world.

## 7. Sparse data and honest explanations

- Unfilled slots say that no additional matching idea could be scheduled; provide useful context about the limited catalog, slot categories, or remaining daily allowance where applicable.
- Report the number of filled slots out of the requested slots. Do not call a partial itinerary complete.
- With zero eligible ideas, still render the requested days, zero scheduled estimates, the full unallocated allowance, and advice to edit interests or allowance.
- If any day has no restaurant suggestion, explain that meals are not fully covered by the itinerary. Do not invent meals or their costs.
- Explain that matching items may remain unused because the itinerary has limited slots, category rules, or daily cost limits; the user can still review all alternatives on the recommendations page.
- Preserve relevant recommendation limitations. In addition, if none of the **scheduled** items carries a requested pace or family-friendly tag, explain that the itinerary cannot confirm that preference.
- Keep reasons tied to actual tags. Selecting family-friendly never makes an untagged item verified as suitable for children.

## 8. Refresh, editing, and session behavior

- `GET /itinerary` is read-only navigation: compute from the current validated draft and current catalog, without storing generated items or HTML in the session.
- Refreshing produces the same result when inputs and catalog have not changed, without resubmitting a form or creating a saved trip.
- A valid preference edit changes the next generated itinerary. An invalid edit preserves the last valid draft and its itinerary.
- If an eligible item's cost or tags change in the catalog, the next page request recomputes recommendations and the itinerary from that updated catalog.
- Without a valid draft, redirect to `/plan` with a useful message. Malformed or unsupported drafts use the existing recovery behavior rather than causing a server error.
- Separate browser sessions must not see each other's draft or itinerary.
- Clearing the draft removes access to its computed itinerary as well as its recommendations. No extra persistent itinerary data remains.
- No new state-changing endpoint is needed. Existing CSRF protections must remain intact; opening an itinerary does not require submitting a form token.

## 9. Concrete acceptance examples

1. **Real sample, relaxed:** Paris, 3 days, EUR 300, food/history, relaxed, family-friendly produces the following six unique suggestions using the current catalog:

   | Day | Morning | Evening | Scheduled estimate |
   | --- | --- | --- | ---: |
   | 1 | Luxembourg Gardens | Le Procope | EUR 50.00 |
   | 2 | Seine Riverside Walk | Café de Flore | EUR 28.00 |
   | 3 | Notre-Dame Cathedral | Louvre Museum | EUR 25.00 |

   Trip estimate: **EUR 103.00**. Unallocated allowance: **EUR 197.00**. Eiffel Tower remains an alternative. Explain the missing restaurant on Day 3 and that evening opening hours are not checked.

2. **Pace changes capacity:** The same trip without a pace preference has three slots per day. All seven matching items are scheduled once; two slots remain empty. Trip estimate: EUR 135.00. Allocation follows Morning across days, then Afternoon, then Evening.
3. **Small allowance:** Change the relaxed sample to EUR 60. The three free history ideas occupy Morning on Days 1–3. Evening slots remain unfilled, the trip estimate is EUR 0.00, and EUR 60.00 is unallocated. Do not claim meals are provided.
4. **No matches:** Food only, 3 days, EUR 1 produces three day sections, no scheduled items, and a useful edit action; no restaurant is invented.
5. **Food-only category rule:** Paris, 3 days, EUR 300, food only, relaxed schedules Café de Flore then Le Procope in the first two Evening slots. Both earn 3 interest points, so the cheaper restaurant ranks first. There are no daytime restaurant placements or repeated restaurants.
6. **Cumulative budget boundary:** For EUR 100.01 over 3 days, eligible fixture items of EUR 20.00 and EUR 13.34 cannot share a day; EUR 20.00 and EUR 13.33 may. Display rounding does not authorize an overspend.
7. **Skip, do not discard:** In a small fixture, a higher-ranked item that cannot fit one day's remaining allowance is still considered for a later day. A lower-ranked affordable item can fill the earlier day's slot.
8. **Exact day count and uniqueness:** Trips of 1 and 14 days have exactly the requested number of sections. Scarce data produces visible gaps, never repeated IDs, unrelated items, or costs above the daily or trip limit.
9. **Determinism and input safety:** Repeating generation with identical inputs returns the same day/slot/item assignments and estimates without altering the input data.
10. **Draft lifecycle:** Refresh, back navigation, valid edits, invalid edits, catalog changes, missing/corrupt drafts, separate sessions, and clearing behave as specified in section 8.
11. **Truthful preferences:** Missing requested tags among scheduled items produce a notice. Untagged items are not described as verified preference matches.
12. **Usable flow:** Navigation, editing, and clearing work by keyboard and with JavaScript disabled; the itinerary is readable at both required viewport sizes.

Catalog examples describe the current illustrative project data, not verified live travel information. General rule checks also require small deterministic fixtures so they do not depend solely on this Paris example.

## 10. Learning and practice

After implementation, explain what the new page does, how a request reaches the itinerary logic, and why that logic stays separate from web presentation. Cover loops, lists and dictionaries, sets for avoiding repeats, greedy selection, exact decimal totals, pure functions, and unit versus integration tests.

Explain the AI boundary: the recommender scores matching ideas; the itinerary engine applies explicit scheduling constraints. Neither is a trained model, an autonomous agent, or a real-world travel feasibility checker.

Provide these small practice tasks:

1. Predict the relaxed sample's six assignments and EUR 103.00 total before running it.
2. Remove the pace preference and explain why the slot count changes.
3. Lower the allowance and explain why visible gaps are safer than invented or repeated items.
4. Calculate the EUR 100.01 boundary and explain why two individually affordable ideas might not fit together.
5. Edit, refresh, and clear a draft; describe which data is stored and which is recomputed.
6. Run the tests and identify one scheduling unit test and one itinerary route integration test.

## 11. Approval and delivery gate

The user approved this behavior specification. The [implementation and test plan](../plans/phase-05-itinerary-plan.md) records delivery, and the [red checkpoint](../docs/phase-05-testing.md) records the test-definition and expected-failure validation completed before any feature implementation. The [implementation report](../docs/phase-05-implementation.md) records the final green suite and browser verification. No approval or testing gate was bypassed.

Required sequence, with specification approval now recorded:

1. Outline the implementation and test plan for this increment.
2. Define pytest unit/integration tests and validate discovery and expected missing-feature failures.
3. Only after that testing gate, implement and integrate the feature.
4. Verify the full regression suite and browser flow, then provide the explanation and practice tasks.

No fixed week count or deadline is introduced.

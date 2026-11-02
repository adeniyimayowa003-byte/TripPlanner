# TripPlanner — Phase 5 Implementation and Test Plan

**Approved scope:** [Daily itinerary specification](../specs/phase-05-itinerary.md). The user approved this specification before this plan was prepared.

**Current checkpoint:** SDD step 4 — implementation and verification complete. All 322 pytest cases pass with unchanged tests, and required real-browser checks are complete. See the [implementation report](../docs/phase-05-implementation.md) and [learning guide](../docs/phase-05-learning.md). The [testing report](../docs/phase-05-testing.md) preserves the earlier 245-passing/77-expected-failure checkpoint.

**Verified starting point:** All 244 existing pytest cases pass. The baseline was rerun on 2026-10-23 using a fresh project-local temporary directory after Windows blocked pytest's default temporary-folder setup. This was an environment issue, not a failing application assertion. No test was removed or skipped.

## 1. The outcome in plain language

The existing recommendations answer **“What matches my interests?”** The itinerary will answer **“What could I do on each day, within my allowance?”**

The new journey is:

**Preferences → trip ideas → Build my daily itinerary → review days → edit preferences or return to ideas.**

We will keep the existing recommendations, scoring, session draft, and protected forms intact. This increment adds scheduling, combined cost checks, and one results page, not a database or external AI service.

## 2. SDD sequence and boundaries

1. **Specification — approved:** Use the behavior in the linked specification without silently expanding it.
2. **Planning — complete:** This file defines responsibilities, data contracts, coverage, and verification.
3. **Testing — complete:** Added 37 domain and 41 integration cases, validated successful collection, reviewed fixtures and helper behavior, and recorded meaningful missing-feature failures in the [checkpoint](../docs/phase-05-testing.md).
4. **Implementation — complete after the testing gate:** Added the scheduler, route, page, and navigation; all 322 tests pass, browser checks are recorded, and the learning guide supplies explanations and practice tasks.

The testing step can change test files, fixtures, and checkpoint documentation. It must not add a stub itinerary engine, route, template, or other application implementation just to make tests import or pass. No extra specification approval is needed for the behavior already approved; a material scope change requires a revised spec first.

## 3. Files and responsibilities

| Area | Planned responsibility |
| --- | --- |
| `itinerary.py` — new | Reuse recommendations, allocate unique ideas to slots, enforce exact cumulative daily limits, calculate totals, and report limitations. No Flask, request, session, or HTML dependency. |
| `app.py` | Add a read-only `GET /itinerary` route using the existing validated draft and one current-catalog snapshot. Pass the generated result to the template. |
| `templates/itinerary.html` — new | Render the summary, numbered days, chronological slots, estimates, gaps, explanation, and working back/edit/clear actions. |
| `templates/recommendations.html` | Add the ordinary **Build my daily itinerary** link, including when there are no eligible ideas. Retain the alternative-ideas cost disclaimer. |
| `static/css/style.css` | Extend the current visual system for day sections, slot cards, totals, and responsive stacking. Retain visible focus styles. |
| `tests/test_itinerary.py` — new | Exercise allocation, categories, pace, exact money, uniqueness, determinism, input safety, notices, and the actual Paris examples. |
| `tests/test_itinerary_flow.py` — new | Exercise navigation, server-rendered content, refresh, edit, recovery, isolation, catalog changes, and protected clearing. |
| `tests/conftest.py` | Reuse existing fixtures and parser; add only shared fixture helpers that genuinely reduce duplication. |
| `README.md` and Phase 5 learning/report documents | After implementation, document current behavior, the scheduling rule, limitations, test results, and practice tasks. |

No new dependency is needed. Keep `recommendations.py`, `preferences.py`, `money.py`, `drafts.py`, `csrf.py`, and the catalog unchanged unless a demonstrated integration defect requires a separately explained fix. Do not add itinerary data to the session envelope.

Home-page controls and its existing resume link remain unchanged in this increment; the itinerary is reached from trip ideas. This keeps the current draft journey and home tests intact. If later implementation genuinely needs a shared-navigation adjustment, test that adjustment explicitly without weakening the prohibition on permanent-saving actions.

## 4. Planned domain interface

Use `generate_itinerary(preferences, catalog=None)` in `itinerary.py`.

- `preferences` has already passed the existing validator: canonical destination, integer days, `Decimal` total allowance, interests, supported pace, and family-friendly boolean.
- `catalog` can be supplied directly for deterministic tests. `None` uses current catalog loading through the existing recommender; an explicitly empty list stays empty.
- The function obtains eligible ordered ideas and recommendation notices using `recommend_trip_ideas(preferences, catalog=...)`.
- With supplied preferences and catalog, the result is deterministic and independent of a browser or session.
- Build fresh output structures; never add scheduling fields to input records or mutate their nested lists/dictionaries.

The test-defined result contract is a small dictionary:

```text
days: list of day dictionaries, exactly as long as requested
  number: integer, beginning at 1
  slots: ordered list of slot dictionaries
    name: "Morning", "Afternoon", or "Evening"
    item: existing recommendation-shaped record, or None
    empty_reason: useful text for an empty slot, otherwise None
  estimated_cost: Decimal sum of that day's scheduled items
estimated_cost: Decimal sum of all day estimates
unallocated_allowance: Decimal total allowance minus trip estimate
filled_slots: number of slots containing an item
total_slots: days multiplied by the pace's slot count
unused_items: remaining eligible records in original recommendation order
notices: readable strings describing relevant limitations
```

Recommendation-shaped records retain `place`, `estimated_cost`, `score`, `matched_interests`, `preference_matches`, and `reason`. A missing slot uses `None`, not a fake catalog record or a zero-cost activity. Keep money as `Decimal` until the template formats it with the existing filter. No computed result needs cookie-safe serialization.

## 5. Allocation and money implementation approach

Prepare all requested day sections first, including their empty slot structures. Relaxed has Morning/Evening; no preference or a validated supported active pace has Morning/Afternoon/Evening.

Maintain a set of used stable IDs and a separate exact running cost for each day. Visit slots in the approved allocation order:

1. Morning for Day 1 through the final day: scan unused attractions/activities in recommendation order.
2. Afternoon across all days, only for three-slot pace: use the same selection rule.
3. Evening across all days: scan unused restaurants first, then unused attractions/activities if no restaurant fits.

For each candidate, compare `(day estimate + item cost) × requested days <= total allowance`. Do not compare against the rounded daily preview. When a candidate cannot fit, keep searching; do not mark that candidate used. Mark an ID used only when an item is actually scheduled.

After allocation, calculate trip totals and remaining allowance from the scheduled items. Count filled and total slots, and find unused eligible ideas. Display slots in chronological order inside each day even though allocation used multiple passes across days.

Create useful, non-duplicated notices for unfilled slots, missing restaurant coverage, unused alternatives, and requested tags absent from scheduled items. Preserve relevant recommendation notices. Scheduled-item notices must not rely only on eligible alternatives: a tagged alternative might remain unused. A slot-level gap reason should describe the available data, category rule, or remaining allowance without inventing a cause.

This is a greedy scheduling algorithm: it chooses the first currently suitable idea and does not backtrack to optimize the trip. The explanation must disclose that daytime choices can consume a restaurant's budget and that categories are a simple suggestion, not confirmed opening hours.

## 6. Route and page integration

| Request/action | Planned response |
| --- | --- |
| Existing valid `POST /plan` | Keep the current 303 redirect to `/recommendations`; do not bypass the ideas page. |
| **Build my daily itinerary** | Ordinary link to `/itinerary`, present for both matching and empty recommendations. |
| `GET /itinerary` with a valid draft | Return 200, regenerate from that draft and the current request's catalog snapshot, and render the itinerary. |
| `GET /itinerary` without a valid draft | Redirect to `/plan` with existing useful missing/recovered-draft messaging. Do not generate from invalid values. |
| Refresh or **Back to trip ideas** | Safe GET navigation, no resubmission or permanently saved result. |
| **Edit preferences** | Existing `/plan` form with current values. Valid edits replace the draft; invalid edits preserve the previous one. |
| **Clear this draft** from the itinerary | Existing POST form to `/draft/clear` with the actual session-bound CSRF token. Keep its 303 redirect and isolation behavior. |

The route must use `current_draft()` and `current_catalog()` rather than create a second validation/session path. `/itinerary` is not added to token-protected POST endpoints: it is a read-only GET, not a state change. First page rendering may legitimately create a CSRF token for the clear form; it must not store generated itinerary records or replace the draft.

The template must show all preference fields, approximate daily allowance, every requested day, category and source details, original reasons, honest free/estimate labels, daily and trip totals, unallocated allowance, and filled-slot count. Put the opening-hours/travel-time caveat near the itinerary, not only in a footer. Empty results still provide days and recovery actions.

## 7. Unit-test coverage and fixture designs

Reuse `make_place`, `normalized_preferences`, and exact decimal helpers from the existing tests. Use small supplied catalogs to prove rules independently of the seven Paris records.

| Coverage | Meaningful fixture/assertion |
| --- | --- |
| Day count and capacity | Parameterize days 1 and 14 and relaxed/no-preference/fixture-supported active pace. Assert numbered days, the correct slot names, and correct total-slot count even for empty data. |
| Slot-major distribution | Two days with no pace and three ranked free activities A/B/C: mornings A/B, then Day 1 afternoon C. A day-first implementation must fail this assertion. |
| Ranking and category priority | Force scores and tie-breaks with tags/costs/names. Preserve the recommender's order within categories; a fitting restaurant wins Evening over a higher-ranked unused activity. |
| Food-only and fallback | Restaurants never occupy Morning/Afternoon. Evening can use an attraction/activity only when no unused restaurant fits; preserve its actual category. |
| Skip, do not discard | Two days, EUR 20 total, no pace; ranked activities A: EUR 8/score 9, B: EUR 2/score 6, C: EUR 5/score 6, D: EUR 2/score 3. Mornings A/B; Day 1 Afternoon skips C and uses D; Day 2 Afternoon still uses C. |
| Exact cumulative boundary | Three days, EUR 100.01, no pace; rank A: EUR 20/score 9, B and C: free/score 6, D: EUR 13.34/score 3. Mornings fill A/B/C; D cannot share Day 1 Afternoon and remains available for Day 2. A EUR 13.33 variant fits Day 1. All candidates individually qualify. |
| No daily allowance transfer | Even if another day has spare money and the trip-wide total would fit, reject a placement exceeding that day's exact equal share. |
| Restaurant too expensive after daytime | One day, EUR 100, no pace: A activity EUR 30/score 9, B attraction EUR 30/score 6, C restaurant EUR 50/score 4, D activity EUR 10/score 3. Daytime uses A/B; Evening skips C and uses D. Total EUR 70, with an honest missing-meal notice. |
| Total integrity | Derive expected day sums, trip sum, and unallocated amount independently. Assert `Decimal` values, zero for empty days, and exact daily/trip inequalities. Free suggestions are still real items. |
| Uniqueness and eligibility | No repeated stable IDs, unrelated interests, other destinations, or individually unaffordable places. Unused eligible alternatives remain in original order. |
| Scheduled preference evidence | One relaxed day, family selected: A activity and B restaurant each match food/history (score 6); C activity matches history and carries both requested tags (score 5). A/B fill slots, C remains unused, and the itinerary reports both unconfirmed scheduled preferences even though recommendations have no such notice. |
| Determinism and input safety | Generate twice; compare assignments, estimates, notices, and unused IDs. Deep-copy inputs beforehand and verify all nested data remains unchanged. |
| Sparse and empty data | Supply `[]`, one item, no matching interests, low allowance, and food-only data. Keep exact day/slot counts, useful gap reasons and edit guidance, without duplicates or fake items. |
| Actual catalog examples | Assert the exact relaxed six-item assignments, EUR 103 total/EUR 197 unallocated, no-pace EUR 135 total, EUR 60 free-only result, and food-only Café-then-Procope evenings. |

Scores in fixture descriptions are produced by the existing interest/optional-tag rules, not injected as a replacement ranking algorithm. For example, three selected matching interests produce 9 points; two produce 6. Where a score of 4 is needed, use one matching interest plus the selected family-friendly tag.

## 8. Integration-test coverage

Use the current Flask app/client fixtures, `set_draft`, `submit_trip`, `csrf_token`, and standard-library HTML parser. Do not globally disable CSRF.

- Follow the actual recommendation link to the itinerary for both matching and no-match drafts.
- Check summary values, one `h1`, correctly labeled day sections, chronological slots, categories, matching reasons, source URLs, estimate/free labels, filled count, totals, caveats, and recovery actions.
- Inspect day/slot sections rather than raw whole-page name order: the allocation order is not the final display order.
- Verify Back/Edit links and the clear form use the real routes and correct HTTP methods.
- Refresh and confirm stable visible results plus unchanged draft data. Check that generated records/HTML are absent from the session. Initialize the CSRF token first if comparing the entire session.
- Make a valid budget edit and assert the next itinerary changes; make an invalid day edit and assert the prior valid itinerary stays available.
- Change catalog costs/tags through a temporary test catalog and assert recomputation. Keep enough destination, interest, and pace support for the stored draft to remain valid; separately test truly unsupported draft recovery.
- Cover missing, malformed, obsolete, unsupported, and invalid-signed-cookie drafts; expect form recovery without a server error.
- Use two clients to prove isolation. Clear one draft using a token obtained from the actual itinerary form; preserve unrelated session data and the other client's draft.
- Check missing/invalid/other-session clear tokens preserve the draft and computed itinerary. Retain `GET /draft/clear` returning 405.
- Request `/itinerary` without a submitted CSRF token and expect success with a valid draft. Normal read-only navigation must not become a token-gated action.
- Exercise the complete journey with the Flask client, which runs no browser JavaScript. This proves server-rendered controls exist and work, not actual visual layout.

Keep all existing recommendation, form, catalog, money, session, and security tests. No broad test rewrite is planned. In particular, keep successful submission's redirect to recommendations, its alternative-cost disclaimer, and the home page's prohibition on unbuilt permanent-saving actions.

## 9. Testing gate before application changes

1. Preserve the recorded 244-case baseline; rerun it if application or fixture inputs change before the new tests are added.
2. Write the new domain and integration tests and minimal shared fixture additions.
3. Collect the whole suite successfully. Import the intentionally missing `itinerary` module inside the relevant test/helper body so one missing feature does not prevent test discovery. Do not hide it with `importorskip`, `xfail`, or a stub implementation.
4. Run the new tests. Expected failures include a missing generator, `/itinerary` returning 404, or a missing itinerary link. A syntax error, invalid fixture, mistaken expected order, temporary-folder error, or broken parser is not an acceptable feature failure.
5. Check that adversarial fixtures really exercise the behavior: occupied days for cumulative costs, a later-day opportunity for skipped ideas, and tags present only in unused alternatives for scheduled-preference notices.
6. Run the retained tests and separate any regression/setup error from expected new-feature failures. Record discovered/passed/failed/error/skipped counts accurately rather than inventing a target count.
7. Write a Phase 5 testing checkpoint mapping failures to approved requirements. Begin application implementation only after collection and intended failures have been validated.

Use the virtual environment's Python and a fresh temporary directory inside the project's ignored `.tmp` folder. Validate its absolute path stays there before supplying it as pytest's base directory, because pytest can clear an existing base directory. Do not reuse a broad folder or delete earlier checkpoint evidence. Record concise results in documentation; do not commit temporary catalogs or generated caches.

## 10. Implementation slices — completed after the testing gate

### A. Standalone scheduler and exact totals

Implement the domain interface, pace slots, slot-major allocation, unique IDs, category handling, skip-not-discard behavior, and exact money calculations. Run the domain cases before connecting Flask.

**Learning focus:** Loops, lists/dictionaries, sets, greedy algorithms, and why several individually affordable ideas can still be too expensive together.

### B. Honest limitations and explanations

Add gap reasons, meal-coverage and unused-alternative notices, scheduled-tag checks, and counts. Ensure output stays deterministic and all input structures remain unchanged.

**Learning focus:** Evidence-based explanations, partial results, and the difference between ranking, scheduling, and real-world feasibility.

### C. Read-only route and server-rendered journey

Connect the validated draft/catalog to `/itinerary`, add the recommendation link and itinerary template, and reuse existing edit/clear controls. Run route, lifecycle, and security tests, then the full regression suite.

**Learning focus:** Request/response handling, templates, GET versus POST, recomputation versus storage, and integration tests.

### D. Responsive verification and student handoff

Add scoped styling, check the actual browser journey, update current-capability documentation, and provide the Phase 5 explanation and practice tasks. Run the complete suite again after final edits.

**Learning focus:** Progressive enhancement, accessibility, regression checks, and explaining what automated tests do and do not prove.

These are implementation slices inside this single approved increment, not new dated phases or additional scope approvals.

## 11. Browser verification after implementation

Pytest HTML assertions cannot establish visual quality or actual keyboard interaction. Check the real running app:

- At 360px and 1280px content widths, day headings, slot cards, totals, notices, and actions are readable with no horizontal page overflow.
- Follow preferences → recommendations → itinerary → back/edit using real controls. Test both a populated sample and a sparse/no-match itinerary.
- Use Tab/Shift+Tab/Enter for links and the clear action; confirm visible focus and useful semantic headings. Clearing remains an intentional button action.
- With JavaScript disabled or application scripts blocked, generation, back navigation, editing, and clearing still work. Document the exact verification method.
- Confirm EUR 103.00/EUR 197.00 for the relaxed sample, EUR 135.00 without pace, and zero scheduled cost for the low-allowance sample.
- Confirm notices visibly distinguish empty suggestions, uncosted meals, unused allowance, illustrative time slots, and unavailable preference evidence.
- Check normal-flow browser errors and local assets. No source-link visit or live travel lookup is needed to generate the result.

If a check exposes a logic defect, add a meaningful regression test before fixing it. Use browser checks for layout defects that Python tests cannot establish.

## 12. Completion and beginner-friendly handoff

The feature is complete only when the new tests and retained regression tests pass, required browser checks pass, the approved sample assignments and totals are correct, all controls perform their labels' actions, and the limitations are accurate. Record actual results and any unresolved limitation; do not call a specified or partially implemented feature complete.

After implementation, deliver a short guide explaining what each changed file does, how a request becomes a daily plan, and where the recommendation rules stop and scheduling begins. Include the spec's six practice tasks: predict the EUR 103 itinerary, change pace, lower the allowance, explain the rounding boundary, trace edit/refresh/clear, and identify unit versus integration tests.

**Student task at this planning checkpoint:** Read sections 4–5 and describe, without coding, why “first idea that fits” needs both a used-ID set and a per-day running total. Then predict what happens when a restaurant matches the interests but cannot fit after daytime suggestions.

**Next action:** Work through the learning guide's practice tasks and choose the next small product increment. Permanent saving is not implemented yet; it requires its own specification and test-first workflow. This increment is complete, not merely specified or tested against missing code.

# TripPlanner — Phase 6: Save and Reopen Trips

**Status:** Implemented after user approval, planning, and test-first validation. All **676 pytest cases pass**, including all 322 retained cases. Browser verification covers responsive/keyboard flows, scripts blocked, restarts, and catalog-independent saved reads. See the [verification report](../docs/phase-06-implementation.md), [student guide](../docs/phase-06-learning.md), [completed plan](../plans/phase-06-saved-trips-plan.md), and [historical red checkpoint](../docs/phase-06-testing.md).

**Related documents:** [Product specification](../SPEC.md), [implemented itinerary specification](phase-05-itinerary.md), and [Phase 5 verification](../docs/phase-05-implementation.md).

## 1. What we are building and why

TripPlanner currently keeps a browser-session draft and regenerates its recommendations and itinerary. That draft is not guaranteed to survive a browser-session end or application restart.

This increment adds **Save this itinerary**, a **Saved trips** collection, and a read-only saved-trip page. Saved trips persist in a local SQLite database and remain available after restarting the app, without requiring the original browser cookie.

The important distinction is:

| Current draft | Saved trip |
| --- | --- |
| One last valid set of preferences per browser session. | Multiple deliberately saved trips in the local database. |
| Results regenerate from the current catalog. | Results are a snapshot of the reviewed plan. |
| Editing replaces the current draft. | Editing a draft does not overwrite an existing saved trip. |
| Clearing removes the current draft. | Clearing a draft does not delete saved trips. |

No fixed timeline is introduced. This feature starts a new specification → planning → testing → implementation cycle.

## 2. Scope and privacy model

- Keep Flask, server-rendered HTML/CSS, the existing recommendation/scheduling rules, exact decimal money, and pytest.
- Use Python's standard-library SQLite support; no external database service or paid API is required.
- Save valid generated results, including partial or empty itineraries, with their original limitations. An empty saved itinerary is not presented as a complete or free holiday.
- Support saving, listing, and viewing only. Deleting, renaming, overwriting, restoring a saved trip into the draft, exports, accounts, maps, and new AI features remain later work.
- This remains a **single-user local demonstration without accounts**. The saved collection is shared by browsers using the same app/database. It is not a private per-browser vault or a multi-user account system.
- Current unsaved drafts remain isolated between browser sessions as before.
- Clearly disclose the shared local collection near saving and on the Saved trips page. Do not ask for personal names, emails, payment details, or other unnecessary personal information; a trip title is not a request for personal identity.
- The local database is not encrypted or an authorization mechanism. Keep the demo bound to localhost; public deployment and user-account privacy require separate work.

## 3. User journey

1. Enter preferences, review trip ideas, and build a daily itinerary as in Phase 5.
2. On the itinerary page, see an optional **Trip name** field and a **Save this itinerary** button.
3. Leave the name blank to use a sensible default, or enter a short name.
4. Save the reviewed trip and open its saved-trip detail page, with a confirmation and a visible **Saved snapshot** label.
5. Select **Saved trips** from navigation to see the collection, even without a current draft.
6. Open a saved trip to review its original preferences, ranked ideas, itinerary, estimates, and limitations.
7. Restart the app or clear the current draft, then reopen the saved trip from the collection. The saved content remains unchanged.

**Plan another trip** opens the existing `/plan` journey, which may prefill the current draft if one exists. It does not discard those answers. Viewing a saved trip never silently loads it into, replaces, or clears the current draft.

## 4. Saving a reviewed itinerary

### 4.1 Form and title

- Add the save form to the current `/itinerary` page. Saving is an explicit POST, not a navigation link.
- Use an associated label, helpful text, the existing session-bound CSRF token, and server-side validation.
- The name is optional. Empty input or ordinary spaces alone uses a default such as **Paris, France — 3-day trip**.
- A supplied name is trimmed, contains at most 80 characters, and is plain text. Reject control characters, including tabs and line breaks, before trimming; do not silently turn a multiline name into a valid title.
- Allow normal Unicode names, punctuation, quotes, and angle brackets as literal text. Escape them when displayed; never interpret a name as HTML or SQL.
- Generated default names also respect the title length limit.
- Invalid names redisplay the current itinerary with an associated error and the submitted name retained. Do not replace the draft or write a saved record.

### 4.2 Current data and stale forms

The save endpoint must not trust submitted prices, day totals, catalog records, or itinerary JSON. Generate recommendations and the itinerary on the server from the current validated draft and one consistent catalog snapshot.

Saving must capture the trip the user reviewed, not silently save different results after another tab edits the draft or a catalog change alters the reviewed snapshot:

- The itinerary save form carries a server-generated content fingerprint representing its preferences, recommendations, and itinerary, excluding the editable title and save metadata.
- On POST, compare that fingerprint with the regenerated current result. A missing/malformed fingerprint is an invalid request; a different fingerprint is a stale form.
- For a stale form, do not write or overwrite any saved trip. Show **Your trip has changed. Review the updated itinerary before saving**, with a working link to the current itinerary.
- Unrelated catalog changes that do not alter the reviewed snapshot need not invalidate the form. If a change makes the current draft unsupported, use the existing invalid-draft recovery instead of attempting a save.
- A content fingerprint is a consistency check, not login or CSRF protection. Keep the existing CSRF token requirement separately.
- With a valid unchanged form, store the server-generated snapshot atomically, then redirect to its saved detail page. Refreshing that page does not submit another save.
- A missing, malformed, unsupported, or expired current draft cannot be saved. Use the existing planner recovery behavior and make no database write.

### 4.3 Repeated saves

- Saving the same normalized title and identical complete snapshot again returns the existing saved trip, rather than creating duplicate records.
- Preserve the existing trip ID and original creation timestamp. Explain **This trip is already saved** instead of claiming a second record was created.
- Enforce this atomically, including equivalent double-click/concurrent requests, not just by hiding or disabling the browser button.
- Different titles or different snapshot content create separate records. Neither operation updates an older saved trip.
- Equality excludes database IDs and creation times. It uses canonical serialized content, not a claim that differently ordered preferences are semantically equivalent.

## 5. What a saved snapshot contains

Each saved trip has a stable positive-integer ID, normalized title, UTC creation timestamp, and a versioned snapshot containing:

- The original normalized preferences: destination, days, total allowance, interests, pace, and family-friendly preference.
- Currency and the illustrative-price/budget-scope explanation.
- All eligible recommendations in their saved rank order, not only the scheduled subset: place metadata, categories, descriptions, IDs, source links, scores, matching interests/tags, reasons, and recommendation limitations.
- All requested itinerary days and slots, selected recommendation records, empty-slot explanations, and itinerary notices.
- The approximate daily allowance, exact daily estimates, trip estimate, unallocated allowance, and filled/total slot counts.
- The snapshot format version, so unsupported or damaged data is detected rather than misread.

Preserve the place details, not only IDs referring to today's catalog. Serialize every monetary amount as a two-decimal string, including nested place estimates; restore exact decimal values for validation and formatting. Do not store money as binary floating point or SQLite REAL values.

When loading, check the snapshot's supported version, required fields/types, money values, and internal consistency, including day/slot structure, unique scheduled IDs, totals, and counts. Validate against the stored data, **not** today's destination/interest choices. Do not repair an invalid snapshot by running the current recommender or scheduler.

Saved content remains a historical estimate, not live travel information. Source links must be safe HTTP/HTTPS references; unsafe stored link schemes are not rendered as executable links.

## 6. Saved trips collection

`GET /trips` must work without a current draft or original session cookie.

- Add a working **Saved trips** navigation link on the existing pages, including the home page.
- Show each trip's name, destination, day count, UTC save time, total allowance, scheduled trip estimate, and a clear **View saved trip** link.
- Order newest first by UTC creation time, then highest ID first for equal timestamps.
- Identify the collection as local/shared and the values as saved illustrative estimates.
- When no trips exist, show **No saved trips yet** and a working **Start planning** link. Do not display demonstration cards as real saved data.
- The collection is not gated on a valid session draft, and browsing it does not change a draft.
- One malformed stored snapshot must not prevent unrelated valid trips from being listed. Show an unavailable entry without inventing its missing costs or deleting it.

## 7. Saved-trip detail

`GET /trips/<trip_id>` shows the stored snapshot, without recomputing it from the current catalog.

- Clearly show **Saved snapshot**, its title, UTC creation time, and a notice that the content and illustrative estimates reflect the save, not live/current results.
- Display its stored preferences, original ranked ideas and matching reasons, day-by-day itinerary, gaps, notices, daily/trip estimates, and unallocated allowance.
- Retain honest category, free/estimate, meal-coverage, budget-exclusion, and opening-hours/travel-time explanations. A full set of slots still does not prove a real trip is feasible.
- Provide **Back to saved trips** and **Plan another trip** links. The latter opens `/plan` and may prefill an existing current draft; it is not a hidden clear action.
- Do not show working save/clear/edit controls that apply ambiguously to the read-only saved record. No saved-trip mutation is introduced here.
- Saved list/detail pages must work after the current draft is cleared, the signing secret changes on restart, or saved destinations/places are removed from the current catalog.
- They must also work if the current catalog file is unavailable or unreadable: loading a saved snapshot must not depend on loading or revalidating today's catalog or current draft through shared page rendering.

## 8. Persistence, failures, and safety

- Default storage is `instance/tripplanner.sqlite3` inside the project. Support a configured alternative path for isolated testing and local setup.
- Create initial storage when needed without overwriting existing files. A new installation with no saved records has an empty collection, not an error. Schema initialization must not create trip records.
- Data survives a fresh Flask app instance, application restart, and changed browser-session signing secret when the same database is used.
- Keep the database and its temporary journal/WAL files out of source control. Document where it lives and that deleting it removes the saved collection; never delete it as automatic recovery.
- Use parameterized database queries and transactions. Return success only after a successful commit. Roll back a failed save without damaging existing saved trips or replacing the current draft.
- Locked, unwritable, corrupt, or unavailable storage produces a useful **Saved trips are temporarily unavailable** message and recovery navigation, not a traceback, raw SQL, or filesystem details.
- Do not reset, truncate, replace, or silently delete a damaged database or unreadable saved record.
- A storage failure must not prevent the existing unsaved preferences/recommendations/itinerary flow from working. Avoid making every page depend on a successful database read.
- Pytest uses separate temporary database files; it must never write to or reset the user's actual saved collection.

## 9. Requests and outcomes

| Request | Required outcome |
| --- | --- |
| `POST /itinerary/save`, valid unchanged result and title | Commit a new snapshot or reuse the identical existing one, then 303 redirect to its saved detail with truthful feedback. |
| Save with an invalid name | Return 200 with the itinerary form, useful associated errors, and retained input; no saved write or draft replacement. |
| Save with a missing/invalid CSRF token | 400 recovery page, before storage changes; preserve the draft and saved records. |
| Save without a valid current draft | Redirect to `/plan` with useful recovery and no write. |
| Save with a missing/malformed content fingerprint | 400 recovery, no write. |
| Save from a changed/stale result | 409 recovery explaining the change, with a link to review `/itinerary`; no write. |
| `GET /itinerary/save` | 405; viewing a link cannot save a record. |
| `GET /trips` with readable storage | 200 collection or truthful empty state, independent of a current draft/catalog. |
| `GET /trips/<trip_id>` with a valid saved snapshot | 200 read-only saved detail. |
| Unknown/nonpositive/malformed trip ID | Friendly 404 with a link back to saved trips. |
| Existing record with unreadable/unsupported snapshot | Friendly 409 unavailable view with recovery; preserve that record and other trips. |
| Save/list/detail when storage cannot be used | Friendly 503, no false save confirmation or destructive recovery. |

Valid snapshots may be partial or empty. Invalid stored data and unavailable storage are different from a legitimate itinerary with no suggestions.

## 10. Interface and accessibility

- Extend the existing green-and-paper design without rebuilding the planner or adding a new frontend framework.
- Use semantic forms, labels, headings, links, error associations, visible focus, and messages that do not rely on color alone.
- Saved cards, titles, costs, and detail sections remain readable at 360px and 1280px widths without horizontal scrolling, including an 80-character title.
- Keep the main header usable with the new navigation link rather than squeezing overflowing controls into narrow screens.
- Save/list/view/back/plan-another actions work by keyboard and with application JavaScript unavailable. No browser-side script is responsible for persistence or authoritative validation.
- The Saved snapshot label and shared-local-collection notice must be easy to find, not hidden in a footer.

## 11. Concrete acceptance examples

1. **Save the working sample:** Paris, 3 days, EUR 300, food/history, relaxed, family-friendly; save as **Paris weekend**. The detail contains all seven original recommendations, the six scheduled suggestions, EUR 50/28/25 day estimates, EUR 103.00 scheduled total, and EUR 197.00 unallocated. Its limitations remain visible.
2. **Restart persistence:** Start another app instance using the same database and a different signing secret, without a draft cookie. Saved trips lists **Paris weekend** and its detail still shows the original content.
3. **Catalog independence:** After saving, remove Paris or change current costs/tags, then make the current catalog unavailable. Saved list/detail still show the saved values without running today's validation or scheduler.
4. **Clear is not delete:** Clear the current draft. The planner is blank and `/itinerary` recovers as before, but the saved collection and saved detail still work.
5. **Duplicate protection:** Double-submit the same valid save, then repeat it after reopening the unchanged draft. At most one identical record exists; its ID and creation time are preserved. Equivalent concurrent requests have the same result.
6. **Separate versions:** Save under another name or successfully change preferences/results and save again. The original snapshot remains unchanged and a distinct record appears.
7. **Stale form:** Open a save form, change the draft in another tab or update the catalog in a way that changes the reviewed snapshot, then submit the old form. For an otherwise valid draft, saving is rejected with 409 review guidance, not a silently different stored plan. Unrelated catalog changes need not reject an unchanged result; unsupported drafts follow existing recovery.
8. **Names and safety:** Blank names get a sensible default; 80-character names work, longer names/control characters produce retained-input errors, and HTML/SQL-looking names are displayed literally without executing markup or database statements.
9. **Partial/empty results:** Save the EUR 60 relaxed sample and a food-only EUR 1 sample. Their original gaps, counts, zero scheduled estimates, and missing-meal explanations survive reload; no fake activities or free full-trip claims appear.
10. **Protected writes:** Missing/invalid/other-session CSRF tokens, malformed fingerprints, GET save requests, and missing/invalid drafts cannot add or change a saved row. Existing records and valid current drafts remain intact on rejected requests. Existing recovery may discard a malformed or no-longer-supported draft; it must not discard saved trips.
11. **Recoverable storage problems:** Simulate a locked/unwritable database and an unsupported or malformed snapshot using test-local files. No false success, data loss, raw traceback, or automatic database reset occurs. Other valid snapshots remain viewable where storage itself is readable.
12. **Collection behavior:** Empty state, newest-first ordering with ID tie-break, default titles, snapshot labels, and all list/detail navigation work without a current draft. Another browser can see the shared local saved collection but not another browser's unsaved draft.
13. **Accessible complete flow:** Save → collection → detail → plan another trip works by keyboard and without application scripts. Mobile/desktop layout, long titles, validation feedback, and recovery controls are checked in a real browser as well as pytest.

## 12. Learning and handoff

After implementation, explain what each new page does, why durable storage differs from a cookie draft, and how a save request becomes a database row and then a read-only snapshot.

Cover database tables/rows and stable IDs, parameterized queries, transactions/commit/rollback, JSON serialization and schema versions, exact decimal persistence, content fingerprints, duplicate protection, POST–redirect–GET, and isolated unit/integration tests. Explain that a snapshot preserves an earlier rule-based AI result; saving does not retrain or improve the model.

Provide these small practice tasks:

1. Save the EUR 103 sample, restart the app, and explain why it remains available without the old draft cookie.
2. Clear the draft and explain why the saved trip is unaffected.
3. Save the same title/results twice, then a different title; predict the collection count.
4. Change a catalog price in a test fixture and explain why an existing saved detail must not change.
5. Explain a stale save form, one title validation error, and why failed commits must not show success.
6. Identify a storage unit test, a route integration test, and a real-browser check that pytest cannot establish.

## 13. Approval and SDD gate

The user approved the Phase 6 behavior. Specification, planning, test definition/validation, and implementation are complete in that order. The [implementation report](../docs/phase-06-implementation.md) records actual test/browser results and the [student guide](../docs/phase-06-learning.md) supplies explanations and practice tasks.

The [test-definition checkpoint](../docs/phase-06-testing.md) remains historical evidence, not the current suite result. No real saved data was reset or mixed with test records.

Any material scope change follows the same specification-approval gate. No fixed week count or deadline is introduced.

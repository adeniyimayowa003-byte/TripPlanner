# Phase 6 — Understand saved trips

This guide explains how saving works and how to describe the feature in class.
The [approved specification](../specs/phase-06-saved-trips.md) defines the behavior;
the [plan](../plans/phase-06-saved-trips-plan.md) separates the responsibilities.
Saving preserves a reviewed result. It does not make the recommendations smarter.

## What changes for the user

The current itinerary now has an optional **Trip name** and **Save this itinerary**.
Leave the name blank for a title such as **Paris, France — 3-day trip**.
After saving, the app opens a read-only detail page labeled **Saved snapshot**.

**Saved trips** in navigation opens the collection, newest first. Each readable card
shows the destination, days, save time, allowance, estimate, and a link to its detail.
An empty collection says **No saved trips yet**; it does not invent sample records.

The detail shows the original preferences, all matching ideas and their reasons,
daily slots, gaps, estimates, and limitations. **Back to saved trips** returns to
the collection. **Plan another trip** opens the normal planner; if a current draft
exists, it may still prefill those answers. Viewing a snapshot never restores it
into, replaces, or clears that draft. Saved records have no edit or delete action.

## Three things that sound similar but are different

| Thing | What it contains | What happens when current data changes |
| --- | --- | --- |
| Browser draft | The last valid preferences in this browser session. | Opening ideas or an itinerary uses the current catalog. |
| Snapshot | A self-contained copy of preferences, places, results, and explanations. | Its saved values stay the same. |
| SQLite database | The durable file holding multiple named snapshot rows. | Rows remain after an app restart. |

The draft is not a permanent saved trip. A snapshot is structured data, not a screenshot
or just a list of place IDs. SQLite stores that snapshot as JSON text alongside its title,
ID, save time, and duplicate key. JSON represents dictionaries and lists as portable text.

The default file is `instance/tripplanner.sqlite3` inside the project. The application
can use another path through `TRIPPLANNER_DATABASE` or its `DATABASE` configuration.
Database connections are opened when needed, not simply because the app starts.
Reading a collection before its first save does not create a database file.

The file and its journal files belong outside source control. Deleting the database
removes the saved collection; never delete it to fix an error or to run a test.
The app does not automatically reset damaged storage.

## Where the responsibilities live

| File | Its job |
| --- | --- |
| [snapshots.py](../snapshots.py) | Build, validate, serialize, and decode snapshots; validate titles; calculate content fingerprints. |
| [saved_trips.py](../saved_trips.py) | Read and write SQLite rows, enforce duplicates, handle transactions and storage failures. |
| [app.py](../app.py) | Handle requests, apply validation in order, and choose a response or page. |
| [templates/itinerary.html](../templates/itinerary.html) | Add the labeled save form to the current itinerary. |
| [templates/saved_trips.html](../templates/saved_trips.html) | Show the shared local collection or its empty state. |
| [templates/saved_trip.html](../templates/saved_trip.html) | Present one historical snapshot without mutation controls. |
| [templates/saved_error.html](../templates/saved_error.html) | Explain saved-page problems with recovery links. |
| [tests/test_snapshots.py](../tests/test_snapshots.py) | Check snapshot contents, names, money, consistency, and fingerprints. |
| [tests/test_saved_trips.py](../tests/test_saved_trips.py) | Check real temporary databases, duplicates, persistence, and failures. |
| [tests/test_saved_trip_flow.py](../tests/test_saved_trip_flow.py) | Check the protected save and saved-page request journeys. |

Templates display prepared data; they do not choose activities or run database queries.
Separating these jobs makes a bug easier to locate and each part easier to test.

## Follow one save request

**Current itinerary → protected POST → fresh snapshot → database commit → saved detail.**

1. The itinerary page displays a server-generated result. Its form includes a CSRF token
   and a fingerprint identifying that result, plus the optional name.
2. On POST, the server checks CSRF first. This token helps stop another site from
   submitting a state-changing form using the user's browser session.
3. The server loads the current valid draft and one consistent current catalog.
   It does not trust submitted prices, day totals, or itinerary JSON.
4. It checks the fingerprint's format, rebuilds the snapshot, and compares fingerprints.
   If another tab changed the draft or a relevant catalog edit changed the result,
   the form is stale. The server asks the user to review instead of saving a surprise.
5. It validates the name. Invalid input redisplays the itinerary with the original text
   and an associated error; it does not replace the draft or write a saved row.
6. The repository saves a new row or finds the identical existing one, then commits.
   Only after success does the route redirect to the saved detail.

This is **POST–redirect–GET**: POST changes state, a 303 redirect leads to a GET page,
and refreshing that detail page does not submit another save. Ordinary links only read.
The core save/list/view flow uses server-rendered forms and works without app JavaScript.

CSRF and fingerprints solve different problems. CSRF checks the form's session token;
a fingerprint checks which content was reviewed. Neither is a login system.

Names are trimmed and limited to 80 characters. Blank names get a default. Control
characters, including tabs and newlines, are rejected before trimming. Normal Unicode,
quotes, and angle brackets remain literal text; HTML output escapes them.

## A fingerprint is a content label, not encryption

SHA-256 produces a 64-character hexadecimal fingerprint from canonical JSON.
**Canonical** means object keys are sorted and spacing is consistent. Lists retain their
order, because recommendation rank and itinerary order are part of the saved result.

The form fingerprint covers the snapshot, excluding the editable name and save time.
The database duplicate key covers **normalized title plus complete snapshot**.
Identical keys reuse the original row, ID, and creation time: **This trip is already saved**.
A different title or changed content creates another row without overwriting the first.
This is exact equality, not an attempt to infer that reordered preferences mean the same trip.

SQLite's **UNIQUE constraint** enforces the duplicate key. Hiding or disabling a button
would not be enough: two clicks or concurrent requests can reach the server together.
Hashing does not hide the stored title or JSON; this database is not encrypted.

## Tables, safe queries, and transactions

A table is a collection of rows with named columns. The `saved_trips` table contains
`id`, `title`, `created_at`, `fingerprint`, and `snapshot_json`. Its integer primary key
gives each row a stable ID used in a URL such as `/trips/1`.

Save times use aware UTC timestamps, not an unexplained machine-local time. The collection
sorts by creation time descending, then ID descending when times are equal.

**Parameterized SQL** sends values separately from the SQL statement. A name that looks
like SQL is stored as text, not executed. This is different from HTML escaping: one
protects the database query, and the other protects the rendered page.

A **transaction** groups the insert-or-reuse work into one operation. **Commit** makes
the operation durable. **Rollback** cancels an unsuccessful operation. The app must not
say “Saved” before commit succeeds: an insert can run successfully and still fail at commit.
Connections are closed after reading or writing so files and locks are not left open.

Locked, unwritable, corrupt, or incompatible storage gets useful recovery rather than
a raw traceback. One damaged row is shown as unavailable without hiding healthy rows
or inventing missing costs. It is not silently repaired, overwritten, or deleted.
The ordinary unsaved planner does not require a working database.

## Exact money and independent historical data

Calculations use `Decimal`. In saved JSON, money uses two-decimal strings such as
`"103.00"`, including the costs nested inside every place. Loading converts these
specific fields back to `Decimal`; it does not turn counts or scores into money.
This avoids binary floating-point rounding changes during persistence.

The snapshot stores its format version, preferences, all eligible recommendations,
complete place details and source links, reasons, notices, day slots, gaps, totals,
and counts. The database schema has a separate version describing its table structure.

Loading checks the saved version, types, safe HTTP/HTTPS links, exact money, unique
scheduled IDs, slot structure, sums, allowances, and counts against the saved data.
It does not call today's recommender or scheduler to “repair” old information.
The shared rendering path for saved pages also avoids loading today's catalog or draft.
That is why a saved trip can still open after the catalog changes or becomes unavailable.

The saved EUR 300 sample keeps seven matching recommendations and six scheduled ideas.
Its day estimates are EUR 50.00, EUR 28.00, and EUR 25.00: EUR 103.00 scheduled and
EUR 197.00 unallocated. Unallocated money is not guaranteed savings. Gaps, missing meals,
illustrative prices, and excluded flights/accommodation/transport remain visible.
Opening hours, travel times, bookings, and real-world feasibility are not verified.

## Privacy and the AI boundary

This is a single-user localhost demonstration with a **shared local collection**.
Another browser using the same app/database can see saved trips, but does not receive
the other browser's unsaved draft. There are no accounts, per-person authorization,
or encrypted storage. Do not collect sensitive information or publicly deploy it as-is.

The existing recommender is rule-based personalization; the scheduler uses allocation
rules. Saving stores their output. It does not train, retrain, call a language model,
or create an autonomous travel agent. A saved estimate is historical, not a live quote.

## Six small practice tasks

1. Save the Paris/3-day/EUR 300/food-history/relaxed/family sample as **Paris weekend**.
   Restart using the same database. Explain why the EUR 103 plan survives without its old cookie.
2. Clear the current draft. Reopen the saved trip and explain why clearing is not deletion.
3. Save identical results with the same title twice, then a different title. Predict the
   number of new rows and explain why the first row's ID and timestamp should not change.
4. In a test fixture, change a catalog price. Explain why a new result may change but
   an already saved detail must retain its original values. Do not damage the live catalog.
5. Open an itinerary, change the draft in another tab, and submit the older form. Explain
   the stale-form message. Also explain an overlong-name error and why a failed commit
   must never show success; use the automated fault test rather than damaging real storage.
6. Find one repository unit test, one route integration test, and one real-browser check.
   Explain how their evidence differs: stored rows, HTTP behavior, and actual usable layout.

Tests use separate temporary databases, never the real collection. A browser layout check
does not prove transaction safety, and an HTML response test does not prove keyboard usability.

## A short presentation explanation

“My draft stores current preferences in a browser session. Saving creates a complete
historical JSON snapshot in SQLite, so it survives restarting and catalog changes.
I validate the form and reviewed content, use exact decimal money, parameterized SQL,
transactions, and a unique content key to avoid duplicates. Saved pages read the original
snapshot without recalculating it. This preserves rule-based AI output; it is not training
or live travel advice. I followed specification, planning, tests first, then implementation.”

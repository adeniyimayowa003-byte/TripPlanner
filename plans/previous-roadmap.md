# TripPlanner Previous Roadmap — Historical Reference

**Based on:** The earlier approved [SPEC.md](../SPEC.md)  
**Status:** Archived roadmap from before the restart. Its phase numbers, completion notes, and historical test results do not describe the current increment. Use the active [PLAN.md](../PLAN.md) and [restart specification](../specs/phase-01-restart.md) for new work.

## How to use this plan

The phases show a sensible order based on what each feature needs. They are not a schedule: we can pause, reorder independent work, or adjust the scope as the class project develops. The first phase is already complete. Before starting each later phase, we will choose its small feature and follow the approved Spec-Driven Development workflow:

1. **Specification:** Confirm the approved spec covers the behavior. If it does not, draft a spec change and wait for approval.
2. **Planning:** Decide the implementation boundary, files or components involved, and expected behavior.
3. **Testing:** Write the pytest unit and integration tests first. Confirm they are discovered and fail for the expected missing behavior.
4. **Implementation:** Build only that feature, run its tests, and keep the app runnable.

After each phase, explain what was built, why it is useful, how the code works, and the related programming or AI concepts. Finish with small practice tasks so the student can explain and modify the feature independently. Tests for later phases are added when we reach them.

## Phased roadmap

### Phase 1 — Project foundation and home page (complete)

**Goal:** Establish a runnable Flask app and a welcoming introduction page.

**Built:** The Flask app factory and home route, a semantic HTML template, responsive CSS, dependency instructions, and the project README.

**Checks:** The home route returns successfully; the page shows TripPlanner's purpose, a planning action, and the three steps; key page landmarks and viewport metadata are present.

**Concepts and practice:** Flask routes, templates, semantic HTML, CSS, and an integration test using Flask's test client. Practice by changing a short piece of page text and identifying which test checks the page response.

### Phase 2 — Travel catalog and destination lookup (complete)

**Goal:** Give the application a small, trustworthy set of sample places to plan with.

**Build:** Add a documented sample catalog for a manageable initial set of supported destinations. Give each entry a stable ID, name, destination, category, interest tags, illustrative cost, and short description. Add a small lookup function to find entries for a destination. Keep restaurant entries distinguishable from attractions and activities.

**Tests:** Check that catalog entries contain required fields, IDs are unique, destination lookup returns only matching entries, and an unsupported destination is reported clearly. Use a small fixture in tests rather than relying on live travel data.

**Concepts and practice:** Data modeling, lists or dictionaries, IDs, categories, tags, and test fixtures. Practice by adding one catalog entry and writing down which fields make it useful to the planner.

**Current slice plan:** Start with Paris, France as the first sample destination, using EUR for illustrative per-person cost estimates. Store the catalog as JSON in `data/places.json`; keep loading and destination lookup in a small `catalog.py` module. Include the required spec fields and a source link for each real place. Prices and descriptions are sample planning data, not live offers. `get_places_for_destination` will match destination names without case or surrounding-space differences, and raise a clear `UnsupportedDestinationError` when there is no match.

**Current slice tests:** `tests/test_catalog.py` uses a tiny pytest fixture to check destination filtering and normalization, and the clear error for an unknown destination. It also checks the sample JSON's required fields and types, unique IDs, non-negative estimated costs, supported categories, source links, and lookup by the real sample destination.

**Validation:** All six catalog tests were collected and failed before the catalog existed, then passed after implementation. The full suite now passes all ten tests.

### Phase 3 — Trip preference form and validation (complete)

**Goal:** Collect the information needed to personalize a trip and catch mistakes early.

**Build:** Add a `/plan` page and a separate preferences/validation module. Populate destination choices from the catalog. For this initial version, allow 1–14 days and collect a total estimated budget in EUR per person. Collect one or more interests supported by the current catalog, plus optional relaxed/active pace and a family-friendly preference. Separate those preference tags from interest tags in the sample data. Show actionable validation messages while preserving submitted values. A valid submission displays a simple confirmation; recommendations are integrated in Phase 5.

**Tests:** Unit tests check normalized valid answers, required and unsupported destinations, day values (missing, malformed, non-whole, below 1, above 14), budgets (missing, malformed, zero, negative, and non-finite), interests (missing or unsupported), and optional pace/family-friendly values. Flask integration tests check the form page and its available choices, successful submission confirmation, accessible validation feedback, preserved form values after an error, and the home page's start-planning link.

**Concepts and practice:** HTML forms, HTTP GET and POST requests, server-side validation, data types, normalized data, and helpful error handling. Practice by submitting one valid trip, then changing one value at a time to an invalid value and explaining how the page responds.

**Validation:** Pytest collected the Phase 3 tests and they failed before the form and validation behavior existed. After implementation, the full suite passes all 35 tests.

### Phase 4 — Recommendation scoring

**Goal:** Rank catalog entries according to the user's interests and supported preferences.

**Build:** Write recommendation logic in a Python module separate from the web routes. Before coding, document a simple deterministic scoring rule, how budget compatibility affects results, and how the app explains each recommendation. The same catalog and preferences should always produce the same ranking.

**Tests:** Check destination filtering, interest and preference matches, ranking and ties, budget handling, explanation text, and the no-match case. Use a tiny known catalog so the expected order is easy to calculate by hand.

**Concepts and practice:** Functions, sorting, rule-based recommendation, scoring, and explainability. Practice by calculating the scores for two sample places, then predicting which one should rank first.

### Phase 5 — Submit preferences and show recommendations

**Goal:** Connect the form and recommendation logic so a traveler can see personalized results on the site.

**Build:** Add a Flask route that accepts valid preferences, calls the recommendation function, and renders a results page. Keep invalid-input messages understandable. Show recommendation details and the reason each item matched.

**Tests:** Use Flask's test client to submit valid and invalid forms. Check that valid choices appear in the response with explanations, and invalid submissions show feedback without losing the user's answers.

**Concepts and practice:** How browser forms, Flask routes, Python functions, and templates work together. Practice by tracing one submitted interest from the form field to the recommendation reason shown on screen.

### Phase 6 — Daily itinerary generator

**Goal:** Turn recommendations into a simple schedule for the requested number of days.

**Build:** Write a testable Python function that arranges suitable places into morning, afternoon, and evening slots. Avoid repeating an item unless the catalog is too small, and explain when the schedule is partial. Use a documented scheduling rule; do not imply that suggested slots are confirmed opening hours.

**Tests:** Check the requested number of day sections, valid time slots, duplicate prevention, handling of too few recommendations, and the empty-data case. Check that the function still returns a useful explanation instead of crashing when it cannot fill every day.

**Concepts and practice:** Loops, grouping data, scheduling rules, edge cases, and separating business logic from presentation. Practice by scheduling a few sample activities on paper before comparing your result with the function.

### Phase 7 — Budget totals and itinerary quality

**Goal:** Help the traveler understand estimated costs and whether a plan fits their budget.

**Build:** Calculate estimated daily and trip costs from catalog entries, display the agreed currency and budget meaning, and explain when a plan exceeds the chosen budget. Apply available pace or duration preferences where the sample data supports them.

**Tests:** Check cost arithmetic, daily and trip totals, currency labels, under-budget and over-budget plans, missing cost data, and pace or duration rules. Keep all amounts clearly labeled as estimates.

**Concepts and practice:** Numeric calculations, aggregation, units and currency, and testing boundary cases. Practice by totaling the costs in a small itinerary by hand and comparing the daily and whole-trip totals.

### Phase 8 — Save and reopen trips

**Goal:** Let the user keep a generated plan and view it again later.

**Build:** Add a small SQLite data layer to save trip preferences, recommendations, itinerary details, and estimates. Add a saved-trip view suited to the local single-user demonstration. Keep database operations separate from routes and recommendation code.

**Tests:** Use a temporary database to check saving and loading a trip, persistence after creating a fresh app or database connection, and useful handling for missing or malformed records. Tests must not use a personal database file.

**Concepts and practice:** Tables, records, SQL basics, persistence, and separating storage from application logic. Practice by describing which pieces of a trip need to be stored so the results page can be reconstructed.

### Phase 9 — Accessibility, reliability, and project handoff

**Goal:** Make the core planning flow easier to use, maintain, and demonstrate.

**Build:** Review mobile layout, keyboard navigation, visible focus, labels, contrast, validation messages, error handling, and setup instructions. Improve the README with the catalog assumptions and a plain-language description of the recommendation rule. Prepare one sample end-to-end trip for the class demonstration.

**Tests and checks:** Run the full pytest suite; add regression tests for any bug found. Manually check the main flow at desktop and narrow widths, using only a keyboard for a basic navigation pass. Verify that setup and test instructions match the project.

**Concepts and practice:** Accessibility, regression testing, debugging, documentation, and explaining design decisions. Practice a short demo: enter preferences, explain a recommendation, review a day's schedule, and show how the estimate was calculated.

### Phase 10 — Optional AI enhancement or scope decisions

**Goal:** Consider optional extensions only after the core planner works reliably.

**Current approved scope:** The spec permits an optional language-model summary of an existing plan. If selected, first define its behavior and test the core flow without a model, accurate use of catalog facts, service errors, and protection of API secrets. The application must remain useful when the service is unavailable.

**AI agent boundary:** A tool-using agent that independently searches data or takes actions is not part of the current approved spec. If we decide to add one, first draft a spec revision describing its role, allowed tools and data, safety limits, and fallback behavior; wait for approval before planning its tests or implementation.

**Concepts and practice:** Difference between deterministic recommendations, generated text, and an AI agent; grounding generated answers in known data; and handling optional-service failures. Practice by identifying which sentences in a sample trip summary come from the catalog and which are generated narration.

Accounts, maps, and other optional ideas can be considered separately if they fit the course scope. They need their own spec coverage and tests before implementation.

## Test strategy across phases

- Use pytest unit tests for validation, catalog lookup, recommendation scoring, itinerary rules, and cost calculations.
- Use Flask's test client for integration tests of routes and form flows without opening a browser.
- Use temporary SQLite databases for persistence tests so personal trip data is not changed.
- Keep fixtures small and deterministic so expected results are understandable and repeatable.
- Cover successful input, invalid input, and insufficient-data cases when relevant to a feature.
- Run the feature's tests during development and the full suite when completing a regression or handoff phase.
- Keep tests independent of paid services, internet access, live prices, opening hours, and real-time travel conditions.

# TripPlanner Product Specification

**Status:** Approved; fixed timeline removed at the user's request  
**Project:** TripPlanner, an AI Programming class project  
**Audience:** Student developer, instructor, and final presentation audience

**Current hosting choice:** The user selected the [free-demo amendment](specs/phase-09-free-demo.md): sleeping free website + separate persistent free database, no paid upgrades. This supersedes the earlier paid always-on proposal. Existing planning/snapshot/privacy contracts remain in force.

**Implemented hosting increment:** [Public website availability](specs/phase-09-public-availability.md), approved on 2 November 2026 with the [free-demo amendment](specs/phase-09-free-demo.md), provides a public HTTPS address, persistent PostgreSQL saves and separate anonymous visitor collections. The [restart verification](docs/hosted-restart-check-2026-11-06.md) records an actual Render restart with unchanged saved data and visitor access controls. See the [current submission review](docs/submission-status-2026-11-06.md) for platform limits. The verified local release below remains the historical classroom checkpoint; no paid hosting is authorized.

**Implemented restart foundation:** [Revised Phase 1 specification](specs/phase-01-restart.md) defines the working preferences-to-recommendations flow. Its 244 cases remain part of the passing suite; see the [earlier verification report](docs/phase-04-implementation.md) and [PLAN.md](PLAN.md). The [previous roadmap](plans/previous-roadmap.md) is retained as history.

**Completed itinerary increment:** [Phase 5](specs/phase-05-itinerary.md) adds day-by-day scheduling and combined cost limits. Its 322 cases remain green; see the [verification report](docs/phase-05-implementation.md) and [learning guide](docs/phase-05-learning.md).

**Completed saved-trips increment:** [Phase 6](specs/phase-06-saved-trips.md) adds durable SQLite snapshots, a collection, and read-only historical details. Its **676 cases remain passing**, with browser verification recorded in the [implementation report](docs/phase-06-implementation.md). See its [learning guide](docs/phase-06-learning.md), [completed plan](plans/phase-06-saved-trips-plan.md), and [historical red checkpoint](docs/phase-06-testing.md).

**Completed appearance increment:** [Phase 7 appearance preference](specs/phase-07-appearance.md) provides Light, Dark, and Use device setting, remembered per browser/origin without changing trip data. SDD is complete in order, and all **943 retained cases pass**. See the [verification report](docs/phase-07-implementation.md) for browser results and the explicit device-switch verification limit, [student guide](docs/phase-07-learning.md), [completed plan](plans/phase-07-appearance-plan.md), and [historical red checkpoint](docs/phase-07-testing.md).

**Delivered Phase 8 checkpoint — classroom handoff verified:** Six-city planning, native currency, v2 saves, external Maps, and 18 credited photos are implemented. All **1,596 pytest cases pass**. Windows demo.2 has the recorded extracted-app journey on Windows 11. The Android debug APK passes the recorded offline/native-tap, restart, and appearance checks on an Android 15 x86_64 emulator. See the [final checks](docs/final-release-checks.md), [Android report](docs/phase-08-android.md), and [presentation walkthrough](docs/presentation-walkthrough.md). The PowerPoint and Word materials explain the actual rule-based AI and limits. Physical Android phones, other Windows hosts, and public-store release remain outside recorded verification. Source preparation and MIT code licensing are local; no GitHub upload has occurred.

## 1. Product summary

TripPlanner is a beginner-friendly travel planning website. A user provides a destination, trip length, budget, interests, and travel preferences. The application uses curated sample travel data to recommend places, activities, and restaurants, then creates a simple day-by-day itinerary. Users can review and save trip plans.

The project is developed incrementally, one small feature at a time, without a fixed timeline. Each stage should leave the application in a runnable state and teach the programming concepts used in that stage. The recommendation and itinerary behavior must be understandable and explainable in a class presentation.

## 2. Goals

- Let a user create a personalized trip plan from a small set of clear preferences.
- Show relevant destinations, attractions, activities, and restaurants from project data.
- Generate a practical daily itinerary from the recommendations.
- Explain why recommendations were selected and how the itinerary was assembled.
- Provide a polished, responsive interface suitable for a student project demonstration.
- Build and validate the system incrementally, with tests introduced before each feature is integrated.

## 3. Out of scope

- Booking, payment, reservation, or real-time availability features.
- Guaranteed live prices, opening hours, traffic, or travel times.
- Comprehensive worldwide travel coverage. Initial data may cover a small number of sample destinations.
- Production-grade identity verification, social networking, or administrative dashboards.
- A claim that a simple scoring algorithm is a trained machine-learning model.
- Dependence on a paid generative-AI service for the core application to function.

## 4. Intended users and primary flow

The primary user is a traveler or class-project evaluator using the website in a desktop or mobile browser.

1. The user opens the TripPlanner home page and starts a plan.
2. The user enters a destination, number of days, approximate budget, interests, and travel preferences.
3. The application validates the inputs and presents recommendations for the selected destination.
4. The application generates a daily itinerary using suitable recommendations.
5. The user reviews the plan, sees its estimated cost and recommendation explanations, and may save it for later viewing.

## 5. Functional requirements

### 5.1 Home page and navigation

- Present the TripPlanner name, purpose, and a clear action to start planning.
- Explain the basic planning flow in plain language.
- Provide navigation to start a trip and view saved trips when those features exist.
- Work at common desktop and mobile viewport widths.

### 5.2 Trip preferences

The trip form must collect:

- Destination, chosen from or matched against supported destinations.
- Number of days, a positive whole number within a documented application limit.
- Total or per-day budget, with its meaning and currency shown clearly.
- One or more interests, such as food, culture, history, nature, shopping, or adventure.
- Optional travel preferences, such as relaxed or active pace, family-friendly, indoor/outdoor, and dietary needs where data supports them.

The application must reject missing or malformed required values, out-of-range trip lengths, and invalid budget values with actionable messages. Submitted values must be preserved when the user corrects an error.

### 5.3 Destination and activity data

- Store a documented, curated sample catalog for supported destinations.
- Each place or activity must have a stable identifier, name, destination, category, interest tags, estimated cost, and a short description.
- Where useful, records may also include duration, indoor/outdoor status, family suitability, dietary tags, and location coordinates.
- Restaurants must be distinguishable from attractions and activities.
- Sample data must be identified as illustrative estimates, not live travel information.
- Unsupported destinations must produce a clear message instead of an empty or misleading plan.

### 5.4 Personalized recommendations

- Recommend items only from the selected destination.
- Consider selected interests, budget compatibility, and supported travel preferences.
- Rank suitable items using a deterministic, documented scoring rule.
- For each recommendation, show a brief reason based on matching interests or preferences.
- Handle no matches by explaining the situation and offering a reasonable recovery, such as broadening interests or budget.
- Keep recommendation generation independent of any external AI service.

### 5.5 Automatic itinerary

- Produce one section per requested trip day.
- Select recommended items without scheduling the same item more than once, unless the catalog is too small and the application clearly reports that limitation.
- Organize items into simple time slots such as morning, afternoon, and evening.
- Respect item duration or pace metadata when available; otherwise use a documented, simple scheduling rule.
- Include places to visit, activities, and food options when enough suitable data exists.
- Show an estimated daily and trip cost based on catalog estimates.
- Clearly label estimates and explain when the selected budget cannot accommodate the generated plan.
- Return a useful empty/partial result with an explanation when data is insufficient; do not crash.

### 5.6 Saving and viewing plans

- A user can save a generated trip and later view its preferences, recommendations, itinerary, and estimates.
- Saved data must persist across application restarts.
- The initial project may support a single-user/local demonstration without accounts.
- If accounts are added later, one user must not be able to view another user's private saved plans.

### 5.7 Optional AI-generated enhancement

- The core recommendations and itinerary must work without a language model.
- If a generative-AI integration is added, it may summarize or narrate an already-generated plan; it must not invent catalog places, prices, schedules, or availability.
- External AI usage must be optional, handle service errors, and protect secrets outside source control.
- The user interface must distinguish generated prose from verified catalog data.

## 6. Quality requirements

- Use semantic, keyboard-accessible forms and visible focus states.
- Provide labels and useful validation feedback; do not rely on color alone.
- Use responsive layouts and readable contrast.
- Keep the application understandable to a beginner: small modules, clear names, comments for non-obvious logic, and setup documentation.
- Keep secrets out of committed source code.
- Handle invalid input, missing data, and expected storage or external-service failures with user-facing messages.
- Provide a README with setup, run, test, data assumptions, and a high-level explanation of the recommendation algorithm.

## 7. Technical direction

Unless revised during approval, the proposed stack is:

- Python with Flask for server routes and page rendering.
- HTML, CSS, and modest vanilla JavaScript for the browser interface.
- SQLite for persistent trip storage.
- JSON or Python data fixtures for the initial destination catalog.
- pytest for unit and integration tests.

The application should separate input validation, recommendation/scoring logic, itinerary generation, persistence, and web presentation so these behaviors can be tested and explained independently.

## 8. Acceptance criteria for the completed project

The project is considered complete when:

1. A user can submit valid preferences for a supported destination and receive recommendations relevant to those preferences.
2. Recommendation results are deterministic for the same inputs and catalog, and each result includes an understandable reason.
3. The user can generate a day-by-day itinerary for the requested number of days, with time slots and estimated costs.
4. Invalid input, unsupported destinations, insufficient catalog data, and budget mismatches produce understandable outcomes.
5. A generated trip can be saved and loaded after restarting the app.
6. The site is usable on desktop and mobile and supports keyboard operation for the main flow.
7. pytest unit and integration tests cover validation, recommendation scoring, itinerary behavior, and saving/loading.
8. The README enables a classmate to set up, run, test, and explain the application.
9. The student can explain the request flow, data model, recommendation score, itinerary rules, and key test cases in the final presentation.

## 9. Incremental delivery boundaries

The full acceptance criteria describe the end-state, not the first build. Work progresses in small features chosen as we go, based on learning needs, priorities, and dependencies. There are no fixed dates or scheduled stages, and the existing application should remain runnable after each feature.

For each feature, follow the Spec-Driven Development sequence strictly: use an approved specification, outline the implementation and test plan, write and validate pytest unit/integration tests for the relevant behavior, and only then implement and integrate the feature. If a feature requires a specification change, draft that change and wait for approval before planning or coding it.

Each feature should include an explanation of what is being built, why it is needed, how the code works, and the relevant programming or AI concepts, plus small practice and testing tasks for the student.

## 10. Open assumptions for approval

- The initial experience is a local class-project demo, not a deployed commercial travel service.
- The first data catalog covers a small set of destinations selected during planning.
- Budget values are estimates in one clearly stated currency for the initial version.
- Accounts and generative-AI integration are optional later milestones, not prerequisites for the core trip planner.
- Flask, SQLite, vanilla JavaScript, and pytest are acceptable defaults unless the course requires another stack.

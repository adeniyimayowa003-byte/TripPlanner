# Phase 9 — validated test-first checkpoint

On 2 November 2026 the user approved the [public availability spec](../specs/phase-09-public-availability.md). The [implementation/test plan](../plans/phase-09-public-availability-plan.md) was written next. At this checkpoint no hosted application, production runner, repository, or template behavior has been implemented.

- Unchanged baseline: **1,596 passed in 66.49 seconds** (`.tmp/phase09-baseline.xml`).
- New contracts: **56 tests collected** in the two new modules, with **56 expected failures in 0.71 seconds**, zero collection/setup errors and zero skips (`.tmp/phase09-red.xml`). Failures are the missing `hosted`, `hosted_saved_trips`, and `serve_hosted` modules, imported inside tests.
- Cases cover invalid/missing production settings, native/local boundaries, cookie lifetime/protection, two-browser isolation and deduplication, owner spoofing, guessed IDs, cookie tampering/expiry/secret changes, restart and exact snapshot preservation, CSRF, failed-save recovery, six-city currencies/photos/Maps, legacy DB refusal, damaged foreign rows, concurrent saves, backup recovery, and real production WSGI HTTP startup/quiet logs.

Commands use the workspace `.venv` Python and pytest. Tests use isolated temporary storage, not the main/local/native databases. The sandbox cannot reliably create all Windows temporary test fixtures or open test sockets; these test runs used the approved external execution context. This is not a claim of public deployment or real HTTPS verification.

The expected failures establish the red checkpoint. Implementation may now begin; later results belong in the implementation report. Preserve this checkpoint as history.

# Phase 9 — hosting preparation and verification

**Status, 2 November 2026:** Approved specification, plan and test-first checkpoint completed in order. Production-mode code is implemented and locally checked. **Public deployment acceptance is pending.** No provider account, paid resource, public URL, GitHub repository or public deployment has been created by this work.

## What changed and why

The existing Flask app can now run through an explicit production factory (`hosted.create_hosted_app`) and the Waitress runner (`python serve_hosted.py`). Hosted startup requires an independently configured stable signing secret, public DNS hostname and an existing durable storage directory outside the checkout. Missing/invalid settings fail before creating a database. Debug/reloader remain disabled; the runner validates the provider port, bounds requests and trusts no forwarded host/client headers.

Saved trips use a separate hosted schema. A protected signed cookie selects one anonymous browser collection; only its digest is stored as owner metadata. Owner conditions are included in list/detail/deduplication queries, so identical saves in two browsers stay separate. Foreign and missing IDs return the same 404. Ownership is never read from a submitted form/query. Snapshots, fingerprint meanings, currencies and AI rules remain unchanged; historical v1 snapshots are checked too.

Cookies last 365 days without a valid page visit and renew on visits. Privacy and personal pages explain clearing cookies/changing device, shared-profile access, no account recovery/sync, and server storage. The local/native collection paths and behavior remain unchanged; the existing packaging allowlists do not need hosted modules at runtime. The already delivered ZIP/APK/PPTX/DOCX files were not overwritten or repackaged.

Health/readiness tests the existing schema/integrity and a rollback-only persistent write path. A missing/locked store returns 503 and is not recreated during requests. Failed saves preserve the draft and entered name. Dynamic pages use private/no-store headers and protected cookies; unexpected application errors produce a generic response and fixed operational log message, excluding request/exception contents.

The private backup tool uses SQLite's online backup API, refuses existing destinations and validates the copy. The test restores only a disposable copy and verifies exact rows and owner access. No actual local/native collection is uploaded, migrated, reset or restored. Regular off-service backup scheduling remains an operator task; no automatic backup service was secretly provisioned.

## Verification evidence

- Historical baseline before implementation: **1,596 passed**, 66.49 seconds.
- Validated red checkpoint: **56 expected missing-feature failures**, 0.71 seconds, no collection/setup errors/skips. See the [test-first record](phase-09-testing.md).
- First complete implemented run: **1,652 passed**, 65.50 seconds. Four additional review cases then checked historical v1 bytes, rollback, public 500/log privacy and oversized form rejection.
- Hosted subset including those review cases: **60 passed**, 3.56 seconds (`.tmp/phase09-hosted-tests.xml`).
- Final complete run: **1,656 passed in 65.57 seconds**, zero failures/errors/skips (`.tmp/phase09-final-tests.xml`). This retains all 1,596 earlier cases and includes the 60 hosting checks.
- Source review: **0 findings**; changed Python files compile successfully.

The production smoke test starts the actual Waitress runner in a separate process, uses disposable external temporary storage and an allocated loopback port, makes real HTTP readiness/planner requests, checks secure-cookie/private headers, rejects an untrusted host and verifies a private query marker is absent from runner logs. It terminates its own server afterward. It does not claim public TLS or a live hosting provider was tested.

Two issues were found in the first implemented subset: the new New York test used `USA` instead of the existing canonical `United States`, and backup destination conflicts were being wrapped as generic storage failures. The test fixture now uses the real catalog value without changing the catalog; the backup tool preserves `FileExistsError` and never overwrites the file. The corrected contracts pass. No existing monetary/scoring assertion was weakened.

## What remains before a real public link

1. Resolve the pending provider/cost decision and account/payment/terms prerequisites. The reviewed proposal is Render Starter + 1 GB disk, Frankfurt, approximately US$7.25/month base before taxes/overages. Approval of the feature spec does not authorize those charges.
2. Publish reviewed source/public assets only and configure the actual host, private stable secret, empty durable store and health/restart settings. The [Render example](../hosting/render.yaml.example) is deliberately inert.
3. Verify the actual HTTPS URL externally, full flow and both browsers' isolation, provider restart/redeploy with unchanged cookie/snapshot access, themes/photos/Maps and behavior while the local preview is stopped. Record real evidence and observed limits.
4. Arrange private off-service backups, retain recovery configuration and update the presentation guidance with the real URL after acceptance. Do not present this preparation as an already deployed service.

See the [operator guide](public-hosting.md), [approved plan](../plans/phase-09-public-availability-plan.md) and [privacy explanation](../PRIVACY.md).

## Explain it in class

“The local app ran on my laptop, so it stopped with the Python process. Public hosting moves that job to a provider's computer. The production WSGI server hands requests to Flask. Persistent storage keeps saved snapshots across restarts, and a signed cookie keeps different browsers' anonymous collections separate. The personalization still uses the same explainable rules; hosting does not turn it into a trained model.”

Practice with two profiles: save the same title/trip, try the other profile's direct link, restart with the same store/secret, and explain why deleting the cookie loses anonymous access. Describe public availability as pending until the external checks above are recorded.

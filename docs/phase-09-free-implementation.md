# Free-demo implementation and deployment evidence

**6 November submission review:** Public deployment and source publication are complete. Actual public saving/reopening, photos, Light/Dark and separate-visitor denial were checked today; hosted restart/redeploy persistence remains pending. See the [current review](submission-status-2026-11-06.md) for the distinction between verified behavior and remaining acceptance.

**2 November 2026:** User selected Free with sleep/usage limits, created their own Render/Neon accounts, accepted their terms and authorized Chrome use for setup. Paid plans/disks/upgrades remain unauthorized. The [approved amendment](../specs/phase-09-free-demo.md), [plan](../plans/phase-09-free-demo-plan.md) and [red checkpoint](phase-09-free-testing.md) record SDD in order.

## Verified code

An explicit PostgreSQL backend now lets the website run without a persistent web-service disk. The hosted factory requires a credentialed PostgreSQL URL with `sslmode=verify-full`, verifies certificates/hostname through a pinned Certifi CA bundle, refuses ambiguous/local fallback settings and masks driver exceptions. It initializes a fresh versioned namespace transactionally; existing incompatible schemas are not modified. Per-owner SQL queries and compound uniqueness preserve browser isolation, deduplication and immutable v1/v2 snapshots.

The production runner/common CSRF/secure-cookie/privacy behavior remain checked. Free-demo pages explain sleep and quota delays. The optional durable SQLite adapter and local/native modes remain available without implicit remote uploads or environment-based mode switches.

Logical backup uses compatible `pg_dump`, credentials only in a private child environment, a new private file and sanitized errors. Recovery was actually tested by `pg_restore` into a different fresh disposable database, comparing exact rows and owner access. A successful archive header alone is not represented as a full recovery guarantee. Regular private off-service backups remain an operator task.

## Results

- Red checkpoint: **32 expected failures**, 2.94 seconds; no setup/collection errors or skips.
- PostgreSQL + retained hosting subset: **92 passed in 16.85 seconds** (`.tmp/phase09-free-first-green.xml`).
- Complete suite with real PostgreSQL/client tools enabled: **1,688 passed in 48.95 seconds**, zero failures/errors/skips (`.tmp/phase09-free-full-tests.xml`).
- Real database: official portable PostgreSQL **18.6**, allocated loopback port, newly created random per-test databases. No system service, production credentials or actual visitor/local/native collections used. PostgreSQL 18 client tools performed the backup/restore.
- Actual [GitHub Actions run](https://github.com/adeniyimayowa003-byte/TripPlanner/actions/runs/41381620794) passed on Windows, Linux and the real PostgreSQL 18 job. This followed a correction to service-container context placement in the workflow.

Local Flask HTTPS simulations and actual Waitress loopback HTTP do not prove live Neon TLS, public HTTPS, provider sleep/wake or cloud restart persistence. Those remain deployment acceptance items below.

## Deployment state

A PostgreSQL-only `tripplanner-demo` Neon project and the `tripplanner-mayowa` Render Free service were created in **Frankfurt** from the user's accounts. No additional Auth/Functions/AI Gateway services or paid resources were selected. [The public website](https://tripplanner-mayowa.onrender.com/) passed HTTPS readiness and serves the planning flow. The configured WSGI entry point, private stable signing secret, PostgreSQL backend, hostname and `/healthz` were checked before deployment. Live client-to-Neon TLS used `verify-full`; server version reported PostgreSQL 18.6. A browser reload is not evidence of a provider restart.

Reviewed code/public assets were published to [adeniyimayowa003-byte/TripPlanner](https://github.com/adeniyimayowa003-byte/TripPlanner). The deployed application source commit is `b969af3b575b3827ec08b51976e812044f38e100`; documentation updates may follow without changing application behavior. No existing local/native databases, private configuration or credentials were included in the source upload.

The older [SQLite preparation report](phase-09-implementation.md) and paid [proposal](public-hosting.md) are historical and superseded by the free choice. Delivered local ZIP/APK/PPTX/DOCX binaries remain unchanged. Use the [current free guide](free-demo-hosting.md).

## External acceptance still required

Record the actual GitHub source URL/commit and CI result, actual Free Render URL/configuration, Neon plan/region/version, live TLS and readiness, full flow and two-browser privacy, cloud restart/redeploy with stable secret/rows, themes/photos/Maps, and independence from the laptop preview. Do not mark completion or revise presentation claims until these checks actually pass. Any billing, OAuth/security permission or authentication action requiring the user is reported at that step without exposing credentials.

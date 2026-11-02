# Phase 9 amendment — free public demo

**Status:** Availability/budget revision approved by the user's explicit free-demo selection on 2 November 2026. This amendment controls availability and cost wherever the earlier Phase 9 documents describe a paid always-on service. It preserves the previously approved durable saves, visitor isolation and local/native boundaries. Provider account creation/terms remain user actions.  
**Parent:** [Public website specification](phase-09-public-availability.md).

## Outcome and limits

Deliver a public HTTPS classroom demo independent of the laptop on **free plans only**. Idle sleeping, cold starts, limited monthly usage and suspension at free limits are acceptable. Do not claim continuous uptime, add a payment method, create paid disks/databases, accept a paid trial, auto-upgrade, or send artificial keepalive traffic. If account verification requires billing or a paid choice, stop that action and explain it.

The selected web-service target is Render Free, one instance, Frankfurt, provider `onrender.com` address. Render sleeps after 15 minutes idle and normally takes about a minute to wake. Its local filesystem is temporary and cannot hold durable SQLite saves. Render Free Postgres expires after 30 days and is not the proposed storage solution. The user's accepted free limits do not authorize silently deleting their saved trips.

Use a separate **Neon Free PostgreSQL** project as the proposed durable store, preferably Frankfurt to match the app. Current published free allowances are 1 GB storage and 100 CU-hours per project/month, with scale-to-zero after five inactive minutes, limited transfer/history, no uptime SLA and no credit card required. Quotas and provider policy can interrupt service. Check actual plan/region/terms in the user's account before creating resources. Remain on Free without payment or automatic paid upgrades.

## Data, functionality and configuration

- Keep the full current six-city planning flow, currencies, photos, appearance, external Maps, CSRF, protected browser identification and per-visitor saves. The AI/domain algorithms and snapshot/fingerprint meanings do not change.
- The free web service must use a remote TLS-protected PostgreSQL connection from private environment configuration. Missing/insecure/ambiguous settings must fail before writing any local DB. Never fall back to temporary SQLite or memory on a database error or quota limit.
- A separate, version-marked hosted PostgreSQL namespace is initialized transactionally in a fresh project. Reject incompatible pre-existing schemas rather than resetting or migrating them. No existing local/native/QA database is uploaded. Ownership stays outside frozen snapshot JSON, with parameterized owner-scoped queries and `UNIQUE(owner, fingerprint)`.
- Maintain the existing 365-day renewable browser-cookie contract and no account recovery/sync. A Render restart/redeploy or Neon compute sleep must not change the stable signing secret, visitor ownership or committed saved snapshots.
- `/healthz` retains readiness checks with bounded database timeouts and generic 503 on unavailable required storage. Database failures must preserve the reviewed draft/name and never claim a successful save. No periodic artificial traffic is introduced to prevent either service sleeping.
- Protect the connection string as a credential: no repository commits, browser rendering, screenshots, exceptions, access logs or process command-line arguments containing it. The public app never exposes DB credentials to client-side JavaScript.
- Keep the prepared durable SQLite hosting adapter as an optional tested configuration for a future approved disk-backed host, not the free Render configuration. Local/native repositories, paths, signatures and delivered release artifacts remain independent.
- Free demo limitations must be visible before the traveler plans: a concise notice about first-load delay and free-tier availability, with About/Privacy explaining cloud database storage and anonymous-access limits.

## Backup and recovery

Document a private PostgreSQL logical backup using `pg_dump`, with credentials passed through a private child environment rather than command-line arguments. Refuse overwriting destinations and sanitize errors. Test restoration only into a fresh disposable database, verifying exact saved bytes/fingerprints and visitor separation. No destructive restore, cloud-data migration or paid automated-backup service is authorized. Provider limited history is not presented as an independently verified disaster-recovery backup.

## SDD and acceptance

Update the implementation/test plan first. Define and validate failing pytest contracts before adding the PostgreSQL adapter or changing the app. Include config/TLS/fail-closed checks, real PostgreSQL transactions/concurrency/owner isolation, two Flask browser profiles, restart, immutable v1/v2 snapshots, quota/unavailable-store behavior, safe backup/restore and free configuration. Keep existing tests passing. Report a missing real DB test dependency as unverified rather than substituting mocks for database integration evidence.

Completion still requires the actual public HTTPS URL, external requests/full journey, two-browser privacy, real host restart/redeploy and saved-row persistence, themes/photo/Maps checks and accurate status documentation. Account/terms actions or absent access can leave deployment pending while code preparation continues. No public URL is invented.

## Sources checked 2 November 2026

[Render Free limits](https://render.com/docs/free) · [Neon Free pricing](https://neon.com/pricing) · [Neon plan limits](https://neon.com/docs/introduction/plans) · [Render with Neon](https://neon.com/docs/guides/render).

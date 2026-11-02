# Phase 9 — public availability implementation and test plan

**Specification:** [Approved 2 November 2026](../specs/phase-09-public-availability.md).  
**SDD order:** Approved spec → this plan → collected/validated failing pytest cases → implementation → regression and deployment checks. No application files change before the red checkpoint.  
**Delivery status:** Preparation only until actual public HTTPS acceptance passes. No public URL or hosting purchase exists yet.

**Progress:** Specification approved; this plan completed; 56-case red checkpoint validated before implementation; production mode and 60-case hosting subset now pass locally. Final regression evidence and remaining deployment actions are in the [implementation report](../docs/phase-09-implementation.md). The provider/cost decision and real public acceptance remain pending.

## 1. What this phase teaches

Your laptop currently plays the role of server. A hosting provider runs that role on its computer instead. A WSGI server receives web requests and passes them to Flask. Durable storage keeps saves when the running application is replaced. A protected cookie identifies a browser's anonymous collection; it is not an account or a password recovery system.

We retain the existing catalog, money validation, explainable ranking, scheduler, immutable snapshots, photos, Maps links, and appearance controls. Hosting changes where the app runs and who may read a saved trip, rather than changing the AI rules.

## 2. Architecture and boundaries

| Area | Planned responsibility |
| --- | --- |
| `hosted.py` | Explicit production app factory; required environment validation, signed visitor cookies, readiness, private response headers, narrow hostname handling, generic errors. |
| `hosted_saved_trips.py` | Separate hosted SQLite repository with owner-scoped queries/deduplication and a distinct database identity. Reuse snapshot validation/record decoding from `saved_trips.py`; leave the original repository's schema and behavior unchanged. |
| `app.py` | Choose the repository only from server configuration. Pass the verified request owner to hosted save/list/detail. Make hosted/local disclosure available to templates. |
| `serve_hosted.py` and `requirements-hosted.txt` | Waitress production WSGI entry point, one process with four threads, bounded requests, no request-content/access logs. Runs on Windows for verification and Linux for hosting. |
| `hosting/render.yaml.example` | Inert example for the proposed paid single-instance service and disk. It is not an automatic provision operation. |
| `hosting/backup.py` | SQLite online-backup API and validation; never replace an existing destination. Recovery is tested on disposable files. |
| Templates, `PRIVACY.md`, README and presentation walkthrough | Clearly distinguish cloud saves from local/native saves. Keep existing layouts/themes. |
| New pytest modules | Configuration, ownership, snapshots, errors, backup/restart, and actual production-server requests. |

Use `hosted.create_hosted_app()` explicitly. `app.create_app()` stays local by default, and native factories continue calling it with their existing profile paths. An inherited `TRIPPLANNER_HOSTED` variable does not silently enable hosting. Hosted creation explicitly overrides the local defaults and validates settings before creating Flask or any database file.

## 3. Configuration contract

Production requires these private/server settings:

- `TRIPPLANNER_SECRET_KEY`: independently generated at least 64 hexadecimal characters, retained securely across restarts. No default/example working secret.
- `TRIPPLANNER_STORAGE_DIR`: existing absolute durable disk mount directory, separate from the checkout. No parent directory creation, relative paths, temporary default, or existing local database import.
- `TRIPPLANNER_PUBLIC_HOST`: one explicit DNS hostname, without scheme/path/port/wildcards; use only that hostname in Flask `TRUSTED_HOSTS`.
- `PORT`: provider port, integer 1–65535, used only by the production runner. Do not expose the desktop runtime.

The hosted database has the fixed basename `hosted-trips.sqlite3` inside the configured mount. New deployments create only this fresh hosted schema. If a file exists, verify its identity and structure before using it; reject a local v1 database, blank pre-existing file, incompatible schema, corruption, or read-only/unavailable store. No automatic migration/reset.

Flask debug/reloader are disabled. Configure secure `__Host-` cookies (`Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`, no Domain), bounded form size, and no shared caching for dynamic responses. Use no blanket ProxyFix or wildcard trusted forwarding. Render terminates HTTPS; Waitress does not trust forwarded host/client headers. Generated internal redirects are relative, and production sessions are secure regardless of backend HTTP. Readiness may use internal HTTP but no visitor identity is needed for it.

## 4. Anonymous ownership and lifetime

- A separate `__Host-tripplanner_visitor` cookie holds a server-signed, unpredictable 32-byte random token. Validate its signature, token structure and age using `itsdangerous`, already a Flask dependency.
- The cookie expires after **365 days without a valid page visit** and is renewed on dynamic page responses. A malformed/expired/tampered cookie creates a new empty collection; never recover access by accepting a submitted owner field.
- Store only a SHA-256 digest of the random token as owner metadata. Do not put ownership inside snapshot JSON/fingerprints. This digest is not logged or shown in HTML.
- Deduplicate on `UNIQUE(owner, fingerprint)`; the fingerprint remains the unchanged canonical title/snapshot hash. Identical saves from different owners produce different rows. Queries must contain the owner predicate in SQL, including duplicates and damaged-record handling.
- Direct URLs for someone else's row and a nonexistent row return the same 404 body/status. Read/list do not reveal other owners' damaged rows. Query/form `owner` parameters are ignored.
- Session cookies keep the current draft/CSRF behavior separate from collection ownership. Clearing a draft does not clear a collection. Server restart with the same secret/store preserves cookie access.
- Clearing cookies, private browsing, another device/profile, or expiration can lose anonymous access. There is no recovery or cross-device sync. People sharing a browser profile share access. No automated deletion/retention job is introduced; unreachable hosted rows remain until an operator establishes an approved cleanup policy. Explain this in privacy text.

## 5. Hosted storage contract

Use a separate application-marked SQLite schema with `id`, `owner`, `title`, UTC `created_at`, unchanged `fingerprint`, and unchanged `snapshot_json`. A schema/metadata table records hosted version. SQL uses parameters for identifiers supplied as values; an immediate transaction serializes writes and the compound unique key handles concurrent duplicate submissions. Return success only after commit.

One instance and one WSGI process, four threads, short-lived connections, bounded lock timeout. No replicated SQLite file, multi-instance scaling or network-filesystem claims. List newest first. Stored snapshots are decoded/verified using existing validators; retain v1/v2 historical meaning and damaged-row behavior within the owner's collection.

At startup create/validate the store and test access. `/healthz` checks schema and a rollback-only persistent write probe; return only `{"status":"ok"}` / `{"status":"unavailable"}` with 200/503, no secrets, identities or paths. Do not recreate a missing database during a running health/read/save request. A lost mount must fail rather than creating a replacement collection. Generic public 500/storage errors preserve drafts and do not print submitted data or exception traces.

## 6. Backup and recovery

Use `sqlite3.Connection.backup()` on the live hosted database, not a filesystem copy or disk-level snapshot as a database recovery guarantee. Backups contain private trips and must be access-restricted, kept outside Git/source/deployment bundles and transferred securely. Make the source read-only, require a new destination, validate identity/schema/integrity before reporting success. Test an independent copy opened by a new app and cookie; compare exact stored snapshot bytes/fingerprints and owner access.

Document a manual scheduled-operations task: backup regularly and before releases, keep at least two verified copies off the service, retain the stable signing secret separately. A backup on the same disk is not disaster recovery. Restore only after stopping writes, preserving the current database, verifying the backup, and obtaining approval for replacing actual user data. This phase tests a disposable restore only; it never replaces the user's local/native database.

## 7. Test-first sequence

1. Retain the existing 1,596-case suite. Discover new tests without import/fixture errors; delayed imports yield ordinary missing-feature failures before implementation.
2. Unit/integration tests: missing/invalid config fails before storage; local database is rejected byte-for-byte unchanged; startup/readiness storage failures; protected and tampered cookies; two independent browsers; guessed IDs; repeated saves per owner; same content across owners; no owner override; damaged foreign duplicates; CSRF/missing draft; failed save keeps draft/name; cookie expiration; fresh app same secret/file; changed secret loses access safely; exact legacy snapshot compatibility; concurrency and rollback; new destination backups and recovery.
3. HTTP tests: both themes' assets available, all six cities keep currency/recommendation/itinerary behavior, safe Maps links and licensed photos remain, hostile hosts rejected, private cache/security headers, errors reveal no paths/identifiers. Local/native defaults remain unchanged even with hosted-related environment values.
4. Validate expected red results and record them in `docs/phase-09-testing.md`, then implement the smallest slices until green. Do not weaken existing tests or change monetary/scoring expectations to make hosting pass.
5. Run full pytest, source-disclosure checks and compile checks. Run the actual production WSGI server on a disposable loopback port/storage and check HTTP responses; this proves startup/WSGI integration, not public reachability or real TLS.

## 8. Provider decision and external acceptance

**Proposed, not provisioned:** Render Starter web service, Hobby workspace, one instance, Frankfurt region, 1 GB persistent disk at `/var/data`, provider `onrender.com` domain. Estimate US$7/month compute plus US$0.25/GB/month disk, before tax, bandwidth/build overages or pricing changes. User must approve this recurring service, confirm account/payment prerequisites and actual checkout total before provisioning. Choosing a free service requires explicitly revising the availability/storage target rather than silently treating it as always-on.

Render supports paid persistent disks across restarts/redeployments, with a short outage during disk-backed redeploys. Its free service sleeps and cannot attach a disk. A paid service is independent of the laptop but cannot guarantee zero downtime. Region selection is proposed for the classroom audience, not a claim of universal low latency.

After the user chooses a provider and account access is available: publish only reviewed source/public assets, configure an independently generated private stable secret, empty durable store, hostname, production command and `/healthz`; disable automatic deploys until acceptance; inspect provider status. No current DB/`.tmp`/SDKs/ZIPs go into deployment.

Acceptance uses the actual URL: external HTTPS request, separate browser contexts, full flow, cross-visitor 404 and duplicate privacy, restart/redeploy with same cookies and byte-identical saved row, mobile/desktop theme/photo/Maps review. Stop the local preview to show the public site does not depend on it; distinguish that evidence from physically powering down the laptop or testing a real phone. Update presentation guidance with the real URL only after verification. Until then mark deployment acceptance pending.

## 9. Student practice and handoff

1. Explain why `127.0.0.1` points to the person opening it.
2. Use two browser profiles: save the same trip/title, then compare collections and guessed URLs.
3. Restart the hosted test app: explain which settings preserve access.
4. Explain why a signed cookie is not encryption, why anonymous saves have no recovery, and why persistent files are different from deployment files.
5. Present the same existing rule-based AI with the new public delivery model, its ongoing cost and honest limits.

The final report records exact passing checks, remaining external actions, provider configuration/cost and backup instructions. Do not mark this increment complete before public acceptance.

## Sources checked 2 November 2026

- [Flask deployment](https://flask.palletsprojects.com/en/stable/deploying/) and [Waitress](https://flask.palletsprojects.com/en/stable/deploying/waitress/).
- [Waitress 3.0.2](https://pypi.org/project/waitress/3.0.2/), production WSGI server with Windows/Linux support.
- [Render persistent disk behavior and limitations](https://render.com/docs/disks), [free service limits](https://render.com/docs/free), [pricing](https://render.com/pricing), [Starter compute reference](https://render.com/articles/render-vs-railway), and [Python version selection](https://render.com/docs/python-version).

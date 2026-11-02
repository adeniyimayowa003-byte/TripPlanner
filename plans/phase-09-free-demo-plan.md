# Phase 9 — free demo implementation/test plan

**Scope:** [User-approved free-demo revision](../specs/phase-09-free-demo.md), 2 November 2026. This replaces the paid Render/disk proposal; the durable SQLite implementation remains optional. **Budget: US$0; no paid upgrade/payment setup.**

## Implementation decisions

1. Keep `serve_hosted.py`/Waitress, the common hosted factory and cookie/security hooks. Add explicit `TRIPPLANNER_STORAGE_BACKEND=postgres` and required private `TRIPPLANNER_DATABASE_URL`. Validate TLS (`sslmode=verify-full`), hostname, scheme, credentials, database and ambiguous settings before connecting. SQLite remains the default only when explicitly configured with its durable directory and no remote URL; no fallback on remote failure.
2. Add a small `hosted_postgres.py` repository with the same save/list/get/check/initialize interface as the SQLite hosted repository. Reuse frozen snapshot serialization/record validation. Use Psycopg 3 binary wheels only in web/development dependencies; never native app packages.
3. Use the fixed `tripplanner_hosted_v1` namespace, a metadata version table, immutable snapshot text, integer IDs, owner digest and compound owner/fingerprint uniqueness. Initialize a missing namespace inside a transaction/advisory lock. An existing incompatible namespace is refused; ordinary reads/health/saves never create schema. Use SQL parameters, bounded connection/statement/lock timeouts and short connections.
4. Route all hosted storage operations and readiness to the configured backend only. Use the same owner digest/CSRF flow; don't accept an owner from a client. Mask DB exceptions, including connection URLs, and do not log SQL parameters or trip contents.
5. Add an inert `hosting/render-free.yaml.example` with Free, no disk, one instance, manual deploys, Python 3.14.7, `/healthz` and secret prompts. Never use the paid example for this selected path. Pin Psycopg plus required packages and preserve license notices.
6. Add private `hosting.postgres_backup`: `pg_dump` custom archive of only the hosted namespace, child libpq environment, new private destination, error redaction, no automatic destructive restore. Verify a disposable `pg_restore` and exact records. Document private off-service backups, limited provider history and unavailable Render Free shell access.
7. Show a small free-demo notice in hosted PostgreSQL mode using existing layout/theme classes, and update About/Privacy/setup/presentation guidance. Explain why moving storage to another server preserves saves even when the app sleeps.

## Tests before implementation

- Config unit cases: missing URL, wrong backend, both directory/URL, missing/weak secret, invalid/insecure URL/query options, wrong host; fail before creating files or attempting connections. Valid remote settings select only PostgreSQL. Invalid timeout/port and local/native behavior stay covered.
- Repository integration against an actual disposable PostgreSQL server: owner-specific duplicate keys and queries, SQL-injection strings as data, two owners, concurrent identical saves, rollback, corrupt foreign snapshot, exact v1/v2 bytes, old/incompatible namespace refusal, lost schema/no silent recreation and readiness/write-lock failure.
- Flask integration using that same real DB: two HTTPS-simulated profiles, foreign/missing identical 404, tampered cookies/owner fields, restart with stable secret/store, save failure preserving draft/name, selected free notice/privacy copy. Reuse the existing 60 hosting checks for common behavior.
- Backup integration: private new file, no credential in process args/output, refuse overwrite, bad source/error masking, fresh disposable DB restore and byte/owner access equality. A tool/mock contract alone is not proof of actual PostgreSQL/restore behavior.
- Validate red failures before application edits. Portable official PostgreSQL test tools may run under ignored `.tmp` on loopback with disposable data, no system service. Do not use cloud credentials or existing databases. Tests use `TRIPPLANNER_TEST_POSTGRES_DSN` only for an explicitly named disposable database, never production `DATABASE_URL`.
- Run all tests and source audit afterward. PostgreSQL integration is a separately recorded command/environment; if tools are unavailable, record skips and the reason without calling that work verified. CI can run real PostgreSQL as a Linux service; keep native/matrix regression coverage.

## Cloud actions and handoff

The user has GitHub but still needs Render and Neon accounts. User signs in/accepts their terms; no passwords or raw DB URLs in chat. After accounts are ready, create an empty Free Neon project/database and Free Render web service in the agreed region, connect reviewed source, enter private settings directly in the provider, and verify actual limits/no paid choices. Prefer PostgreSQL 18 for compatibility with the recorded backup tools. Refuse billing/upgrade prompts until separately authorized.

External acceptance remains mandatory: real HTTPS URL, independent retrieval, two-browser flow/privacy, provider sleep/wake/redeploy persistence, photos/themes/Maps and private backup verification. The public link cannot exist until these account/resources steps succeed. Existing PPTX/DOCX/ZIP/APK remain the earlier verified local release; add the real link to presentation guidance only after verification.

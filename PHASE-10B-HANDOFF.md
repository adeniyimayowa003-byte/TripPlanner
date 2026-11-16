# TripPlanner — Phase 10B session foundation candidate

**9 November 2026 · Cloud-only · Not deployed · Accounts remain unavailable.**

This source bundle continues the approved accounts/Help/optional-AI specification and implementation/test plan. It retains the tested Phase 10A Help increment and adds a dormant provider-independent account/session service with a separate **development SQLite adapter**. It is not a completed sign-in system or the production PostgreSQL adapter. No repeat approval of unchanged scope is requested.

## What changed

`account_sessions.py` adds strict post-verification identity values, exact issuer/subject account keys, random opaque session issuance, server-side token digests, expiry, rotation, revocation, maintenance and account-owner policy primitives. Five new pytest files exercise these rules using real isolated SQLite transactions, plus actual existing Flask/hosted factories to verify the dormant feature cannot activate or impersonate a guest collection.

**Every existing file from the previous Phase 10A bundle is byte-for-byte unchanged.** No Flask/hosted/native factory imports this service. No login route, provider callback, account cookie middleware, database migration or account feature switch was enabled. Native source staging does not include the dormant service. Existing signed draft sessions and anonymous hosted cookies keep their original meaning.

The new plan addendum is `plans/phase-10B-session-foundation.md`. Actual failure/pass logs, runtime versions, provenance and the incremental patch are under `docs/phase-10B-evidence/`. Previous Phase 10A logs remain historical evidence, not fresh PostgreSQL/browser verification.

## Test-first record — actually run

All invocations used `python -m pytest -q` against the actual extracted project in an isolated cloud copy. Short tracebacks were retained for red checkpoints. Test filenames appear in each log. No unconditional failing assertions or blanket xfail markers were used.

| Evidence file | Actual result | Meaning |
| --- | --- | --- |
| `01-module-absence.txt` | 21 failed, 1 passed | Module missing; an absence checkpoint only, not sufficient validation of its security behavior |
| `02-store-red.txt` | 20 failed, 2 passed | Minimal API scaffold allowed collection; missing validation/store behavior failed before it was implemented |
| `03-store-green.txt` | 22 passed | Identity validation and separate-store initialization/refusal rules implemented |
| `04-issue-red.txt` | 11 failed | Issuance operations explicitly unimplemented; working initialized-store fixtures |
| `05-issue-green.txt` | 33 passed | Store plus issuance suites pass |
| `06-lifetime-red.txt` | 17 failed | Session resolution explicitly unimplemented; real issuance fixture worked |
| `07-lifetime-green.txt` | 17 passed | Lifetime/rotation checks pass |
| `08-revocation-red.txt` | 10 failed | Revocation, authorization and cleanup explicitly unimplemented; real store/session fixtures worked |
| `09-foundation-green.txt` | 60 passed | All first four new suites pass |
| `10-hardening-red.txt` | 6 failed, 11 passed | Six malformed issuer inputs were incorrectly accepted; other failure/tampering regressions already passed |
| `11-foundation-green.txt` | 77 passed in 2.58s | Five account-foundation suites pass after issuer hardening |
| `12-final-regression.txt` | **1,773 passed, 9 skipped in 33.81s; exit 0** | Full current suite, including Phase 10A and all 77 new cases |

There were no collection/setup errors in the recorded red stages after the module-absence probe. Minimal `NotImplementedError` scaffolding existed only to expose meaningful operation failures before implementing each slice; there are no remaining unimplemented methods in the new module. This does not mean the rest of the approved product scope is implemented.

The final runtime was Linux/Python 3.12.14, pytest 9.1.1 and Flask 3.1.3. Exact installed versions are recorded in `environment.json`. The original classroom runtime is Python 3.14; it was not rerun here. All cases used synthetic identities, temporary cloud databases and fake clocks. Two bounded worker connections and a two-second lock-timeout case test SQLite serialization/failure, not service load. Existing runtime tests run only their cloud loopback fixtures; no laptop, desktop app, browser control, build or emulator was used.

The **nine skips** are existing real PostgreSQL repository/restore cases that require `TRIPPLANNER_TEST_POSTGRES_DSN` pointing to an explicitly guarded disposable loopback administrator database. No such server/DSN was configured. Neither `postgres` nor `pg_ctl` is available on the cloud runtime PATH. SQLite tests are not substituted for real PostgreSQL evidence; no production database was contacted. Original historical PostgreSQL/restart evidence is not claimed as a new run.

## Implemented internal behavior

| Area | Current implementation and tests |
| --- | --- |
| Identity boundary | Immutable server-internal `VerifiedIdentity`: HTTPS issuer with no credentials/query/fragment/control characters and valid port, bounded exact subject, literal boolean verified-email status and integer provider authentication time. Issuance requires authentication less than five minutes old and not in the future. |
| Account identity | Exact issuer+subject uniqueness, case sensitive. Different issuer/subject combinations are different accounts. No password or email table; no email-based merging. |
| Token storage | Fresh 256-bit opaque tokens; only domain-separated SHA-256 digests persist. Issued token is excluded from object repr. Tests inspect stored rows and database bytes for raw tokens. |
| Lifetime | 30-minute idle, 12-hour absolute; exact expiry instant denied. Activity renews idle only within original absolute lifetime. Backwards clock and inconsistent persisted timing values fail closed. |
| Rotation | New token generated on each issuance; optional previous token revoked in the same transaction. Invalid authentication or a locked-store failure does not revoke the previous session or create a partial new identity. |
| Single/all-session revocation | Single-device revocation is idempotent. All-session revocation requires authentication under five minutes old. Generation update and session deletion are atomic and survive new store instances. Other accounts remain valid; later freshly verified sign-in is allowed. |
| Recovery foundation | Internal exact-identity invalidation primitive, tested against concurrent issuance. This is not recovery email, a provider event receiver or event verification. Future callers must authenticate provider signals independently. |
| Ownership policy | Re-resolves the current token on every check, requires account-kind ownership metadata and exact account ID. Foreign, forged, anonymous-kind and revoked authority denied. It does not read/claim actual trips. |
| Persistence safety | Explicit absent-file-only setup with POSIX private permissions; noncreating mode for all operations; separate application/schema identity; existing guest store, unexpected schema, missing path and direct symlink refused. Errors exclude path/identity details. No automatic repair/reset. |
| Cleanup primitive | Explicit expired-session deletion preserves active sessions and account records. No scheduler or production retention guarantee is introduced. |
| Current-app isolation | Real existing factories ignore account database environment settings and opaque account cookies; account routes stay absent. A raw account token cannot serve as a signed guest cookie or reveal a synthetic foreign trip. |

## Security boundaries and remaining work

Constructing `VerifiedIdentity` **does not verify an OIDC signature or prove a person's identity**. It is an internal type for the future trusted OIDC adapter, not a substitute for it. No HTTP endpoint accepts these fields. A future integration must use maintained protocol components to verify the issuer/audience/signature, Authorization Code + PKCE, state/nonce, callback destinations, expiry, replay and actual verified ownership. The adapter and its tests are still outstanding.

This is development SQLite storage only. Production account persistence requires a PostgreSQL adapter and actual transaction/concurrency tests in an isolated cloud database. Do not point this module at existing trip databases or wire it to Render's temporary filesystem. Before a future production release, add account ownership mapping and atomic guest-claim behavior without changing stored snapshot text, IDs, timestamps, existing namespace or guest signing authority. Duplicate fingerprint collisions and strict legacy schema validation need explicit handling and tests.

No account registration/sign-in/sign-out UI or HTTP flow is available. No secure account-cookie transport, CSRF integration, authentication/recovery quotas, provider recovery event verification, recovery mail, account deletion, tombstone/backup restoration policy, cleanup scheduling or per-endpoint trip authorization has been implemented in this slice. The internal primitive tests therefore do not establish completed acceptance criteria AC-03–AC-06, AC-08–AC-12 or AC-17 for the hosted product. Claiming, offline collection import/sync, native online access and integrated AI remain absent. Prior Help browser accessibility checks remain unverified.

Managed identity/email/model providers remain unselected and unconfigured. No contemporary free quota, delivery allowance or no-billing capability is assumed. Provider terms/account creation, credentials and any live release remain separate gates. No passwords/keys/connection strings are requested in chat. No new payment method, upgrade, paid trial, API usage, email send or service provisioning occurred.

## What stays protected

The original uploaded archive and previous tested bundle are unchanged. Every previous Phase 10A project file remains unchanged in this candidate. No repository write/main-branch change, deployment, production connection/migration, stable-secret rotation, TLS change or anonymous-trip reassignment occurred. Current native downloads, PPTX/DOCX and introductory video are untouched. No real user collection or credential was copied into tests, logs or deliverables.

Removing the new dormant module/tests/plan/report returns the Phase 10A source candidate; there is no application/data rollback to execute for this slice. A future release containing real account-owned rows must use the compatibility-safe rollback rules from the approved specification, not an old binary that could restore guest access.

## Beginner explanation and next step

An account identifier says which user owns something. A session token is a temporary random pass held by a browser; the server stores its digest and expiry so it can revoke that pass. Signing out one device removes one session. Signing out all devices changes the account's session generation and removes all its old sessions. This is different from storing a password or trusting a name supplied in a form.

The next development slices are the real PostgreSQL account adapter, verified OIDC callback/session transport and rate-limit contracts, followed by deliberate trip claiming and recovery/deletion integration. Each still needs its own actual red pytest evidence before implementation. Provider-dependent activation stays off until the free-only service contracts and secure configuration are genuinely satisfied. No new approval of the unchanged specification or plan is needed to continue isolated development.

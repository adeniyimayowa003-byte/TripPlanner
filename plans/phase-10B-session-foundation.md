# Phase 10B small slice — dormant identity/session foundation

9 November 2026. Subordinate to the approved Phase 10 specification and implementation/test plan. No new product scope or approval checkpoint.

## Exact boundary

Build the provider-independent rules and a durable **development SQLite adapter** for verified account identities and opaque revocable sessions. This is an internal service used by tests, not a usable sign-in service. It is not imported, configured or instantiated by the current Flask/native/hosted factories. There is no fake login route, built-in password, unsigned identity callback, account UI or way for request parameters to turn it on.

Production is PostgreSQL. Do not wire this SQLite adapter to hosted saving or Render's temporary filesystem. A PostgreSQL adapter with actual database/race tests, real OIDC verification, quotas, email/recovery contracts, deletion/retention/restore behavior and activation gates are still required before enabling accounts. Provider choice remains unresolved. This slice can be implemented and tested without those provider decisions.

## Reviewed seams

Existing `app.create_app` uses a signed draft session, and `hosted.create_hosted_app` separately verifies a signed guest cookie and hashes its owner identifier. Leave both unchanged. Existing owner-scoped adapters permit only 64-hex owner digests and validate their schemas strictly. Leave `saved_trips`, `hosted_saved_trips`, `hosted_postgres`, snapshot bytes, namespace, database TLS and signing secret unchanged. Native packages must not acquire account persistence automatically.

## Planned API and responsibilities

`account_sessions.py` is not authentication protocol implementation. `VerifiedIdentity` is a server-internal post-verification value, with exact issuer/subject, strict boolean verified-email status and provider authentication timestamp. Constructing it does not cryptographically validate an OIDC token. Only a future maintained OIDC adapter may supply it in real use. No route accepts it from a form, JSON body, cookie, JWT decoding without verification or query string.

`create_store(absolute_path)` creates an absent separate database with restrictive permissions and an application/schema marker; it refuses existing files without changing their bytes. `SessionStore(absolute_path, clock=...)` opens only an existing compatible store without environment fallbacks, network or parent-directory creation. Fake clocks are for deterministic tests. All changes are transactional with bounded timeouts and separate connections per operation. Two store objects sharing the file must see the same identities and revocations.

`issue(identity, previous_token=None)` atomically finds/creates an account by exact issuer+subject, generates a fresh 256-bit opaque token, stores only its domain-separated digest, and invalidates any supplied prior application-session token. Verified recent authentication is required: age under five minutes, no future time, no truthy string accepted as verification. No email storage/password database or email-based account linking. It returns an issued token (hidden in repr) and a principal containing only account/session timing identifiers.

`resolve(token, touch=True)` verifies shape, active account/generation, 30-minute idle and 12-hour absolute lifetimes. At the exact expiry instant access is denied. Activity can renew idle expiry only within the original absolute lifetime. Backwards clock movement denies access rather than extending it. `authorize(token, owner_kind, owner_id)` resolves current authority on every call; it accepts only this account's **account-kind** ownership metadata, never an anonymous owner digest or stale cached principal. Actual trip row ownership must come from the database, not a client field. No trip is claimed or queried by this helper.

`revoke(token)` invalidates just that opaque session; repeating it is harmless. `revoke_all(token)` requires authentication under five minutes old, invalidates every account session atomically and does not lock out a future sign-in. `invalidate_identity(issuer, subject)` is an internal server hook for a future independently verified provider recovery/revocation event; this slice has no HTTP event endpoint or provider-event verification and does not claim full recovery support. Generation changes and session deletion are transactional so concurrent issuance cannot preserve an old generation.

`purge_expired()` explicitly deletes expired session records without deleting accounts or active sessions. No cleanup scheduler or retention guarantee is claimed yet. Account-wide deletion, trip ownership and backup tombstones remain later slices.

## Test-first sequence

1. Write pytest cases with imports delayed until test execution so absent modules do not break collection. Run a missing-feature behavioral probe through the real Flask app to verify no account feature is being enabled; existing guest/Help behavior is the integration baseline.
2. Run all new policy/store cases before implementation. The absent module will be an expected feature absence, but that alone cannot certify the actual unit/integration behaviors. Record it as a module-level absence checkpoint, then implement only the minimal module/API scaffold raising `NotImplementedError`, run every case again, and require meaningful missing-operation failures with working fixture setup before implementing the behavior. The scaffold must not implement security behavior.
3. Validate fixtures/setup after the scaffold so setup errors are not called behavioral red evidence. Cases whose prerequisites need implemented earlier behavior are validated red in their own subsequent slice: identity/issuance first, then resolution/lifetime, then revocation/authorization/purge. Implement a slice only after its own assertions reach expected failure. Preserve logs for each gate.
4. Run deterministic tests against real SQLite transactions, then the unchanged full existing suite. Add bounded two-connection contention cases; no stress tests. No provider network, email, native build, emulator or production database connection.

## Required cases

- Strict verified-identity validation, exact issuer/subject separation and case sensitivity; invalid identity has no persistence effects; no email-based merging.
- Create-only/no-reset behavior, missing/foreign store refusal, restrictive permissions, redacted errors, raw token absent from persistent tables/files and object representation.
- Fresh unpredictable tokens, duplicate verified identity stable account, concurrent registration one account, rotation old-session denial, shared-file restart survival.
- Idle/absolute/recent-auth boundary values; touch cannot extend absolute life; backwards-clock denial; malformed/forged tokens cannot access anything.
- One-device logout, all-device logout, account-scoped recovery invalidation, restart persistence and bounded concurrent issuance versus revocation; invalidation affects no other account and does not ban future verified sign-in.
- Current-session account-owner authorization; foreign/account-ID tampering, anonymous ownership and stale/revoked authority rejected; no snapshot or existing DB changes.
- Expired-row purge preserves active sessions/accounts; unavailable or incompatible storage fails closed.
- Actual Flask/hosted factories keep account routes absent and cannot use an opaque account token as guest proof; no implicit account-file creation or trip upload. A pytest-only invented app is not used.

## Honest outcome

This can establish tested internal rules and a development adapter only, not AC-03/04/05/06 completion for hosted accounts. Cookie flags, OIDC signature/callback/PKCE/replay protection, CSRF, auth/recovery rate limits, durable PostgreSQL concurrency, account deletion and native/AI integration remain outside this slice. No live switches, account-provider terms, credentials or billing actions are authorized here.

# TripPlanner Phase 10 — Implementation and test plan

**Date:** 9 November 2026, Asia/Shanghai. **Status:** plan recorded; source review and executable test stage blocked by cloud source access. **No fixed weekly timeline.**

## 1. Authority, scope and current status

The user explicitly approved `phase-10-accounts-help-ai.md` with “i approve”. This plan is subordinate to that exact specification: [approved specification](https://chatgpt.com/library?file_id=libfile_e6a2629802548191b417d253dc19b321&account_id=personal), Library ID `libfile_e6a2629802548191b417d253dc19b321`. Its full 230 lines were read during this planning stage. The original document's awaiting-approval wording is historical; the subsequent explicit approval satisfies that checkpoint. No repeat specification approval or additional plan-approval requirement is introduced.

Required order remains: approved specification → recorded implementation/test plan → actual pytest unit/integration tests written and their expected failures validated against reviewed source → implementation/integration. Work can proceed through these gates without a new plan approval when resources are available. A material scope change requires an explicit specification amendment; choosing ordinary internal names does not.

This document defines the implementation approach, test cases and evidence requirements. It contains no application implementation or executable tests. No pytest collection or execution has occurred. No feature, integration, schema or deployment has been changed. Provider terms, account creation, credentials, any spending and switching the live presentation release remain separate gates.

Everything here is cloud-only. No laptop access, local terminal, browser/desktop control, builds, emulator, heavy process or parallel agent work is used. Only this downloadable Markdown artifact is created in the managed cloud workspace and saved for the user. No production database connection, public-demo request that mutates data, main-branch change, secret rotation, native-download update or PPTX/DOCX/video edit is permitted.

## 2. Evidence register and precise source blocker

| Item | Evidence status | Consequence |
| --- | --- | --- |
| Approved Phase 10 requirements | Read directly from the named Library file, full content | Authoritative for this plan |
| Flask/Python, Jinja/CSS/vanilla JS, curated catalog and scheduler | Supplied verified context; source not read | Preserve architecture; do not rewrite planner |
| Hosted Render Free/Neon Free Frankfurt, TLS verification, signed anonymous cookie and owner digest | Supplied context | Preserve boundaries; exact implementation unknown |
| Snapshot v1/v2 immutability, six cities, 48 venues, 18 photos | Supplied context | Use synthetic compatible fixtures after source inspection |
| Source/documentation commit | Supplied `b7d2ee2988930db9e0f755be75ea6bff035c9668` | Must resolve exact tree before mapping edits/tests |
| Deployed application commit | Supplied `b969af3b575b3827ec08b51976e812044f38e100` | Must compare compatibility without changing deployment |
| Existing 1,688 tests, CI, restore/restart, Windows and emulator evidence | Historical supplied context | Not a fresh run and not evidence for new features |
| Repository paths, route names, app factory, DB driver, migration tools, wrapper callbacks and current dependencies | Unverified | Proposed names below are logical seams, not claims about existing files |
| Identity/email/AI vendor capabilities or free quotas | Unselected and unverified | No vendor-dependent feature may be enabled |

Source: https://github.com/adeniyimayowa003-byte/TripPlanner . Cloud-only attempts in this stage included GitHub commit-specific blob reads, raw README/SPEC/PLAN/PRIVACY reads and the GitHub contents API. GitHub/raw reads returned `DisabledError`; the API URL was inaccessible through the cloud reader. Two search engines did not return the requested repository; unrelated TripPlanner results were excluded. This is an access failure, not evidence that the repository is absent or private. Earlier attempts also failed on the specs directory/demo.

Capability discovery found an available GitHub plugin that is not installed; no account connection or installation was performed. A future available authorized cloud GitHub reader or public cloud fetch capable of returning the exact tree is sufficient. No laptop files, passwords, private clone or connection strings are requested as a workaround.

**Prerequisite for actual test work:** a read-only cloud-accessible copy of the exact repository tree and dependency metadata, plus a permitted lightweight cloud Python/pytest execution facility and isolated synthetic test storage. None is assumed merely because a documentation artifact can be written. Do not substitute a made-up Flask project or mocked replica and call its results repository validation.

## 3. Phase 0 — Reconcile source and establish the baseline

Once read-only cloud source access is available:

1. Resolve both supplied commit IDs and record the actual tree/commit hashes. Read SPEC.md, PLAN.md, PRIVACY.md, README.md, relevant phase specs, repository instructions, dependency/lock files and CI configuration. Discover relevant paths from the tree rather than guessing filenames.
2. Map the Flask application construction, configuration, request/session middleware, templates/theme controls, save/list/read/delete/download routes and catalog/scheduler entry points. Inventory every endpoint that can reveal a trip, including error pages and exports.
3. Read storage adapters and hosted/native mode selection. Document anonymous-cookie validation/renewal, digest generation, namespace filtering, ownership predicates, snapshot serialization and transaction handling. Determine whether exact stored snapshot bytes exist as text/blob or whether a database JSON representation has already normalized them. Claiming must leave the payload column untouched; do not invent byte-fidelity evidence if the source representation makes it undefined. Raise a narrow specification clarification if necessary.
4. Trace allowance from form validation through scoring and totals into results/snapshot rendering. Record per-day/per-trip semantics, currency and included/excluded expenses before authoring the allowance FAQ. Inventory approved FAQ/catalog source identifiers and existing attribution links.
5. Inspect SQLite and PostgreSQL schema management, backup/restore procedures, secret/TLS configuration and native launch/auth restrictions. Identify which existing tests are cloud-portable without builds or emulators. Confirm whether signing-key purposes need separate future secrets without rotating the existing anonymous signing key.
6. Record a source map of real path/symbol → proposed responsibility → existing tests → new test suite. Reconcile conflicts with the approved specification. This plan is useful now, but source-dependent edit locations and provider integration detail are not finalized until this record exists.

Exit evidence: pinned source manifest, architecture/endpoint/ownership map, reconciled allowance wording, synthetic fixture format, baseline test inventory and isolated execution details. Existing source failing a baseline check must be reported separately from Phase 10 expected failures.

## 4. Cloud test workspace and isolation

Use an isolated cloud-only development copy/branch when available. Never edit main or trigger automatic deployments. Before any future repository write, inspect automation/deploy triggers so an isolated branch cannot publish unexpectedly. If no safe remote write surface exists, keep changes as private cloud artifacts rather than pushing.

Use temporary SQLite files only inside the disposable cloud test environment for the relevant adapter, and a separate disposable PostgreSQL database/schema containing synthetic fixtures for hosted semantics. Never use `tripplanner_hosted_v1` or the production database as a test target. Add fail-closed guards on target identity: missing/unrecognized test configuration must abort before a connection or migration. A mere environment name containing “test” is insufficient proof of isolation. No new paid service, account or production migration is permitted. If isolated PostgreSQL cannot be supplied free within the authorized cloud environment, label PostgreSQL tests blocked; SQLite passes cannot replace them.

Test network access is denied by default. Identity, email and AI adapters use deterministic local-in-cloud fakes; no provider calls, email delivery or API credentials. Fake signing keys are test-only. Fake clocks avoid sleeps; controlled concurrent transactions demonstrate contention without load/stress tests. Unit tests are small; database integration tests are serial/bounded. No native binaries, builds or emulators are needed at this stage.

## 5. SDD red gate — write tests before implementation

After recording this plan and completing Phase 0, write actual pytest tests using the repository's existing conventions, real imports/app factory and actual routes. Candidate suite labels in this plan are provisional and must be mapped to real paths. Test setup may create synthetic data and provider fakes; it must not implement the missing production behavior.

For each new behavioral slice:

1. Collect the tests successfully against the reviewed baseline with all required dependencies and fixtures working. Collection/import errors, missing services or invalid fixture setup are infrastructure failures, not a valid red gate.
2. Run existing relevant baseline tests and keep their results distinct. Preservation tests may already pass, which is expected.
3. Run the new feature tests and record at least the missing-feature behavior failures they are intended to expose: for example a missing Help response or an absent ownership/claim behavior. A missing new module can demonstrate absence but is not sufficient evidence for the intended unit/integration assertions; resolve test collection design against existing seams without writing feature logic.
4. Save source SHA, test artifact/version, exact invocation, environment/dependency versions, collected/passed/failed/skipped counts, test IDs, sanitized failure excerpts and the expected cause. Do not mark skipped tests as validated. Never use unconditional `assert False`, blanket xfail, mocks of the entire production behavior, or assertions changed simply to get green.
5. Only after the applicable suite has meaningful expected failures, implement that slice. Preserve the red evidence, rerun the same tests to green, then relevant regression coverage. Later slice-specific tests may be added first, but no behavior is implemented ahead of its red gate. Provider-specific changes also need their own preimplementation tests once the contract is selected.

Evidence ledger states: **planned** (this document), **written**, **collected**, **expected failure validated**, **implemented**, **green**, **blocked**, **not applicable with reason**. A test run against a fake copy of the application never advances the real-source state.

## 6. Phase 10A — Help without identity or AI

Implementation sequence after its red gate:

1. Establish a versioned approved FAQ content structure with stable heading/source IDs, category, question, answer, source reference and feature availability. Reuse existing catalog provenance; do not add live venue claims.
2. Add server-rendered Help and persistent navigation from planning/results/saved views using the existing Jinja layout. Render all answers without requiring JavaScript. Add progressive search/category filtering, clear results count, empty-state reset and accessible disclosure controls only where useful.
3. Use existing theme tokens; verify focus, contrast, reduced motion, labels and status announcements. Keep device-theme preference per browser.
4. Publish only source-reconciled allowance text and all specification FAQ topics: six supported cities, illustrative estimates, missing meals/slots, immutable snapshots, guest cookie limits, Maps, free-host wake-up, offline versus cloud saves and honest support limitations. Gate account/AI guidance by actual availability.

Completion: AC-01/02/20 with no external service dependency. Help does not invent an inbox, staffed support team, ticketing or emergency help. Release remains a separately authorized future action.

## 7. Phase 10B — Accounts, access control and deliberate claiming

### B1. Separate identity protocol from application ownership

Plan small responsibilities rather than a framework rewrite: identity adapter, session/revocation store, principal/ownership policy, claim coordinator, quota store and deletion coordinator. Reuse maintained components compatible with the inspected dependencies. Choose the concrete OIDC library only after checking primary official documentation and source compatibility. No password table or custom credential-verification system.

The identity adapter exposes verified immutable issuer/subject, verification status, authentication time, validated callback state and revocation/recovery signals. OIDC Authorization Code plus PKCE, nonce/state and exact callbacks remain mandatory. Account identity uniqueness is issuer+subject; matching emails do not merge accounts. Managed registration, verification and recovery UX must satisfy the approved expiration/abuse/revocation contract before activation.

Proposed logical persistence (names are not existing schema claims): accounts with immutable provider key/status; opaque-session hashes and expiry/revocation state; single-use auth/claim challenges; minimal ownership/provenance metadata; shared rate counters/reservations; deletion jobs and protected tombstones. Never persist password material. Use constrained relationships/uniqueness, bounded expiry and explicit hosted/native routing.

For owned trips, prefer an additive exclusive ownership representation: exactly one effective anonymous owner or account owner. Preserve existing snapshot payload/ID/creation time and legacy namespace. Determine whether an account-reference column or separate ownership relation best preserves existing adapters after source review. All reads/writes must join/apply the same effective-owner rule; no fallback to legacy anonymous authorization for account-owned rows. Enforce exclusive ownership in both persistence constraints and service policy. No bulk backfill to user accounts.

### B2. Session and ownership enforcement

Create opaque server-side sessions, store only session-token hashes, set Secure/HttpOnly/SameSite cookies, rotate identifiers on authentication and use CSRF protection for state changes. Enforce 30-minute idle/12-hour absolute expiry and 5-minute recent-auth windows without relying on browser clocks. Validate session revocation/account state on every authenticated request. Keep guest cookies a separate authority.

Centralize authorized trip access for list/read/save/delete/export, claim preview/commit, context selection and any future native endpoint. Use neutral not-found responses and private/no-store authenticated responses. Audit template/error paths for incidental metadata leakage. Logout revokes first, then clears UI/session context; all-device logout increments or otherwise invalidates all account sessions. Preserve unclaimed guest access on ordinary account logout; provide separately confirmed guest-credential forgetting with its loss warning.

### B3. Claim transaction

Use server-derived exact preview membership/version, recent authentication, valid current guest authority, CSRF and a 10-minute one-use challenge. Preview identifies the destination verified account and shared-browser consequences. Confirmation revalidates all predicates inside one transaction.

Transaction design must serialize claims and guest-membership changes for the same anonymous collection, for example with an owner-level lock honored by guest saves/deletes and claim commits. Locking only existing trip rows does not prevent a newly inserted trip from creating a phantom membership change. Re-read/compare exact membership under that serialization boundary, lock eligible records, conditionally change ownership metadata, consume the challenge and record minimal provenance atomically. Changed membership returns to a new preview; foreign/account-owned rows never qualify. Roll back all changes on any error.

Repeat confirmation is harmless and does not perform a second transfer; concurrent account claimants have one winner. Preserve payload columns untouched and compare their before/after representation using the actual storage type. After committed ownership change, old guest authority must fail even if response delivery/cookie rotation fails; future guest access uses a new credential. A retry can show a safe completion result without granting new authority. Cancellation, invalid proof or transaction failure changes no ownership.

### B4. Rate limiting, recovery and deletion

Use atomic shared PostgreSQL counters/reservations if compatible with the current free stack; no new Redis dependency is assumed. Bound counter cardinality/expiry and fail closed for protected actions when enforcement is unavailable. Hash account identifiers used for anti-enumeration; trust forwarded network addresses only through the inspected trusted-proxy configuration. A fresh session must not bypass network/account/global ceilings.

Identity quotas: 10 sign-in starts/15 minutes per browser and address; 3 recovery/verification resends/hour per identifier and 10/hour per address; 5 claim/delete attempts/15 minutes per account; 100 authentication starts/minute globally and 100 recovery sends/day globally. Stricter provider caps prevail. Enforce checks before external effects; no permanent attacker-triggered account lockout. Use generic status and retry timing.

Provider recovery must issue expiring single-use links and make completed recovery revoke application sessions through a verified event or equivalent enforceable mechanism. Validate event signatures, age, replay and account binding. This must be proven in the provider contract, not guessed from an email feature.

Deletion first disables access/revokes sessions atomically, then erases account trips/profile/claim records within 24 hours. Retain only the protected minimal deletion marker needed through backup expiry; no snapshot/email/prompt content in it. Provider-account deletion is either verified supported behavior or an accurately disclosed separate procedure. Failed provider cleanup cannot reactivate the app account. Enforce 30-day expiry for backups containing new account data, expired-session cleanup within 24 hours and security-metadata maximum 30 days. No cleanup of existing anonymous trips is introduced. Restore must apply tombstones/revocation before serving requests.

Completion: AC-03 through AC-10, AC-12/17/18/19. Fake-provider contract tests may support code development; they do not certify a real service or permit enablement.

## 8. Phase 10C — Optional native online access

Implement only in a future compatible source slice after its tests reach red. The minimal scope is an explicit “Open my online account” system-browser launch with offline default. No local collection contents, credentials or hidden imports accompany that launch. No new native downloads or builds are produced by this work.

Inspect Windows/Android wrappers before proposing in-app OAuth. If later required and supported, use system browser, PKCE, exact platform callbacks, state/nonce, OS-protected storage and revocation. Never capture passwords in an embedded webview or include client secrets/bearer tokens in deep links. Server and launch-contract tests can be written without a build; actual OS callback/storage/UI behavior remains unverified until separately authorized platform validation. No physical-phone claim from emulator history. Sync/import/export remains excluded.

Completion: AC-10/11/20 for the enabled mode, with unsupported modes visibly disabled.

## 9. Phase 10D — Optional AI, guarded by local Help

### D1. Provider-free foundation

After red tests, implement an off-by-default server feature gate and local FAQ fallback. Version the approved FAQ/catalog corpus. Retrieve only approved IDs/excerpts; do not introduce arbitrary web retrieval or model-chosen fetch URLs. Resolve source links on the server.

Require verified account session, per-session AI consent and explicit per-trip selection. Build an allowlisted context projection from exactly one currently authorized trip; no selection means zero trip data. Exclude identities/tokens/other trips/unnecessary free text. Recheck ownership immediately before request dispatch, bind context to session and selected trip, and invalidate it on logout/expiry/deletion/ownership loss. Late responses after invalidation must not render. Session-memory history is bounded and expires; no persistent application transcript or browser storage. A process restart may lose history safely. Multiworker state must not mix principals; if secure shared ephemeral history is unavailable, send fewer/no previous turns rather than persist transcripts.

### D2. Bounded provider adapter

Build a narrow adapter taking approved context and returning bounded structured answer/citation identifiers. Only server-selected endpoints/models are permitted. No tools, booking, payments, account writes or planner mutation capability is passed to the model. Network timeout includes queue/setup/read time within 15 seconds. No automatic retries, paid failover or switching providers. Enforce the approved limits before sending; cancel/discard over-limit or timed-out output safely.

AI limits: 5/minute and 20/day per account; 100/day globally; one in-flight/account and two globally; 1,000 characters/question; at most four previous turns; total input ≤6,000 tokens including instructions/sources/history/trip; output ≤600 tokens. Use the selected model's documented tokenizer or a conservative proven bound; do not treat character count as token proof. Reject excessive context without dropping mandatory instructions. Reserve quota/concurrency atomically with expiring leases and a deadline; failures consume attempted-call budgets conservatively. Restart cannot reset daily limits or create unlimited abandoned leases. UTC daily reset is displayed understandably to users.

### D3. Grounding and rendering

Citation existence alone does not prove that a generated claim is supported. For the initial implementation, require each factual answer segment to reference approved source IDs and use exact approved excerpts or deterministic templates populated from those sources. Free-form unsupported factual text is withheld in favor of the FAQ response. Suggestions must be visibly suggestions, without invented venue facts/prices/hours. A second LLM “judge” is not assumed and cannot become an unbudgeted call. Broader factual generation would need evidence that it meets the existing support requirement or a specification amendment.

Render plain escaped text initially; display only server-resolved approved source links, with no raw HTML/images/arbitrary model URLs. Treat user text, sources and output as hostile data. Prompt instructions help quality; server authorization, context projection and absence of executable tools enforce security. Log only minimal operational metadata, not prompt/context/response/credentials.

D4 activation requires a chosen provider's verified official free-only/no-billing enforcement, acceptable retention/training terms, user terms acceptance and secure server configuration. Missing configuration gives the same reliable Help path as outage/timeout/quota/unsafe output. Provider calls are prohibited during this planning/test-double stage. An optional external-service button is a simple labelled link, no trip/question/ID parameters, no sensitive referrer, no automatic data transfer, and no claim of integration.

Completion: AC-13/14/15/16/18 plus relevant authorization, quota and fallback criteria. Real-provider suitability remains distinct from passing fake-adapter tests.

## 10. Pytest case catalogue and acceptance traceability

The following are **planned cases, not executable test files or validated results**. Map logical suite names onto actual source conventions after Phase 0. Parameterized cases cover v1/v2 and applicable adapters without mirroring implementation line by line.

| Suite / AC | Setup and stimulus | Required observable assertion / intended red cause |
| --- | --- | --- |
| `help_contract` — 01/02/20 | Signed-out client requests Help/navigation, with JS absent and integrations off | All required topics/headings/labels available; disabled features honest; missing Help behavior is red |
| `help_budget` — 02 | Synthetic inputs exercising actual allowance semantics | FAQ meaning and currency match actual computation; no guessed daily/trip claim |
| `guest_regression` — 01/19 | Two browser clients, v1/v2 fixtures; planner/Maps/theme/save calls | Original owner allowed, foreign denied, snapshot values unchanged; zero auth/model adapter calls; preservation checks may already pass |
| `identity_callback` — 03 | Fake issuer with test signing keys, valid/invalid claims | Valid verified issuer+subject succeeds once; bad signature/issuer/audience/expiry/state/nonce/PKCE/callback/replay denied; identical email with different subject does not merge |
| `recovery_contract` — 04/12 | Known and unknown identities, clock at expiry, duplicate link and signed/forged recovery event | Neutral responses, one-use ≤15-minute links, resend ceilings, old sessions revoked, no ownership change; provider-specific portions blocked until selected |
| `session_policy` — 05 | Clock crosses idle/absolute/recent-auth thresholds; session fixation input; two devices | Boundaries enforced, identifier rotates, logout revokes current only, all-device revocation invalidates both, CSRF missing/invalid denied |
| `shared_device` — 05/07 | Account session plus unclaimed guest collection; logout then confirmed forget | Logout retains guest authority only; forget warns and rotates it without deleting account trips; cache headers prevent sensitive reuse |
| `authorization_matrix` — 06/10 | Accounts A/B, guest C/D and no principal; every discovered trip endpoint/method | Only effective owner succeeds; foreign responses are neutral and contain no title/count/estimate; forged account fields ignored |
| `claim_preview` — 07/08 | Valid guest cookie and recent verified account; login, decline, cancel, preview | No implicit claim; exact authorized set/count/account shown; no foreign rows or prechecked consent |
| `claim_commit` — 08/09 | Preview nonce; mutate membership, switch session/account/cookie, expire/replay/tamper | Stale/mismatched requests fail with zero transfer; one confirmed eligible set transfers exactly once |
| `claim_postgres_race` — 08/09/19 | Independent DB connections synchronized at a barrier; two claimants plus guest insertion/deletion | One winner/all-or-nothing; membership changes serialize or require re-preview; no phantom/partial transfer; bounded race, not stress test |
| `claim_failure` — 08/09 | Inject failure after first ownership update and after commit before response | Precommit failure rolls back all; postcommit retry safe; old guest authority never regains account rows |
| `snapshot_preservation` — 09/19 | Synthetic v1/v2 with whitespace/Unicode/legacy estimates and timestamps | Untouched stored representation and payload digest/value equality as supported by actual type; no reserialization/upgrade; unrelated rows byte/value identical |
| `quota_boundaries` — 12 | At cap−1/cap/cap+1, new browser same address, multiple workers, restart and unavailable store | Exact identity/global ceilings enforced; no restart/session bypass, retry timing present, guest planner still works |
| `native_boundary` — 10/11 | Actual launch/URL builder with synthetic local collection; offline mode | Launch contains no local content/token; no upload/sync adapter call; system-browser contract only; OS behavior separately pending |
| `ai_consent_context` — 06/13 | No consent, guest, selected A trip, forged B trip, deselect/logout/delete during request | Zero provider calls when unauthorized/unconsented; exact allowlisted projection; late response discarded; no previous-user context |
| `ai_budget` — 14 | Fake token counter/clock/provider; every boundary, competing reservations, abandoned lease/restart | Approved token/character/turn/concurrency/daily limits, ≤15-second deadline without real waits, no retry/failover, conservative failed-call accounting |
| `ai_grounding` — 15 | Invented prices/hours, correct citation attached to unsupported claim, unknown IDs and malicious source instructions | Unsupported factual content withheld; only source-backed templates/excerpts shown; wrong citations rejected; no tools/actions invoked |
| `ai_rendering` — 15/18 | HTML/script/Markdown URL/image payloads and fake secret markers | Escaped inert output; no arbitrary clickable/fetched URL; no credentials/content in logs or client response |
| `ai_fallback` — 01/13/14 | Off/misconfigured provider, quota exhaustion, timeout, malformed/oversize answer | Useful local FAQ response; planner/accounts continue; no unexpected network call or paid fallback |
| `external_ai_link` — 16 | Trip page/context present when external link rendered | Clearly external; no query/fragment/referrer leak or auto-send behavior |
| `deletion_retention` — 17 | Own/foreign trip, recently authenticated delete, synthetic backup and provider failure | Immediate denial/revocation, active erasure ≤24 hours, preserved foreign data, no guest reassignment; outstanding provider state truthful |
| `restore_safety` — 17/19 | Disposable synthetic restore plus protected deletion ledger | Tombstones/revocations applied before serving; no deleted account/trip resurrection; backup expiry policy enforced |
| `config_privacy` — 18/19/20 | Off flags, missing secrets, invalid DB TLS configuration in isolated test configuration | Server gates prevent actions; verified TLS remains required; no secret exposure or production-target fallback; only truthful feature notices |
| `rollback_compatibility` — 19/20 | Synthetic claimed/new/deleted account rows, feature switches off | Guest core usable; account rows stay account-only or fail closed; no old anonymous authority fallback or destructive reset |

Unit layer: ownership predicates, expiry, counters, context projection, citation/render rules and state transitions with fake clocks. Integration layer: real Flask request/session/database behavior, transactional storage, multi-client isolation and PostgreSQL concurrency/restore. Do not use mocks for the database ownership transition and then claim transaction safety.

## 11. Accessibility, platform and provider evidence beyond pytest

Pytest can verify semantic HTML, accessible names, required notices, no-store headers, source IDs, escaping and theme token definitions. It cannot alone prove screen-reader usability, browser Back-cache behavior, actual contrast in every rendered state or 200% zoom layout. Record those checks as pending cloud accessibility/render review using permitted tools, never laptop browser control. If the necessary cloud inspection is unavailable, AC-02 remains partially unverified and that release is blocked; static tests do not substitute for it.

Likewise a mocked OIDC service cannot certify real verification mail, recovery expiration/revocation or no-charge terms. Native launch unit tests cannot certify OS callback/storage behavior. No builds/emulators/physical-device tests are authorized here. Clearly distinguish static/unit evidence, real service contract evidence and platform validation before any later enablement.

## 12. Provider decision records — separate from plan approval

No concrete vendor/free quota is claimed. Retain the approved managed-OIDC recommendation; minimize custom security maintenance. For each candidate, consult dated primary official documentation and record URL, relevant capability, limitation and decision. Do not accept marketing “free” as proof of no-charge enforcement.

| Decision | Required evidence / user action | Development possible without it |
| --- | --- | --- |
| Identity service | OIDC code+PKCE, verified identity, hosted create/sign-in, deletion/logout, event/revocation behavior, regions, free no-card/no-charge limits; user chooses and accepts terms | Generic adapter/session/authorization tests with fake issuer; actual service off |
| Recovery/email | Included or separately approved delivery, sender/domain conditions, quotas, single-use ≤15-minute expiry, app-session revocation on completed recovery; user accepts any separate terms | Recovery state/failure tests; no email sent; accounts not enabled with broken recovery |
| AI provider/model | API eligibility, enforceable zero spend, token accounting, timeout support, retention/training and region terms; user chooses and accepts terms | Context/citation/quota/fallback tests with fake provider; integrated AI off |
| Secure configuration | User enters future credentials directly into approved secure server configuration, never chat | Missing-config behavior and fake-secret leakage checks |
| Storage/backups | Free isolated test storage and actual ≤30-day account-backup retention, protected restore ledger | Small pure unit tests once real source/runner exists; PostgreSQL/activation blocked if unavailable |
| Live release | Separate explicit authorization to change presentation release/data/schema; none provided now | Isolated cloud work only |

Do not assume ChatGPT Plus grants API access or this chat can host the app backend. No payment method, paid trial, upgrade or new API charge may be introduced. If no candidate satisfies the exact approved contract at no cost, keep that feature off and report the precise mismatch; do not silently relax security/privacy to make it fit.

## 13. Integration, release readiness and rollback planning

After each red-to-green slice, rerun the relevant existing tests once and broaden only for affected shared ownership/storage/session paths. Run the full cloud-portable regression suite at the final integration boundary; report unsupported Windows/Android/CI portions as unrun. Historical 1,688 is not a promised current count. Preserve baseline test results separately from new cases and skipped/blocked checks.

Use a private evidence bundle with source/test versions, sanitized pytest reports, AC coverage, pending accessibility/provider/platform checks and no real user data/secrets. A readiness decision requires all applicable criteria green or an explicitly disabled independent increment; an unverified security boundary cannot be waived by a green unit suite.

Future schema work must be additive, inspected and exercised only on synthetic isolated databases before any separately authorized production operation. Preserve stable signing secret, verified database TLS, namespace and legacy cookie access; no destructive reset, automatic local uploads or broad ownership backfill. Test migration compatibility without running it on production. Do not assume “additive schema” makes an old binary ownership-safe.

Rollback sequence for a later authorized release: disable affected server switches/external calls; stop claims immediately if ownership is uncertain; preserve account rows and deletion state; continue guest planning/Help where safe. Use only a release that understands effective account ownership, or fail account endpoints closed. Do not restore an old database over newer trips, unclaim trips, erase new account data, or re-enable stale guest access. A synthetic restore rehearsal must reapply tombstones before traffic. No rollback/deployment operation is performed now.

Current downloads, main, production database, PPTX, DOCX and intro video remain unchanged. Updating materials or announcing enabled features is a later authorized activity after actual validation.

## 14. Beginner explanation and next action

The specification is the agreement about **what** TripPlanner must do. This plan breaks the work into **how** to build it safely: Help first, account ownership next, optional native online access, and optional AI last. Each can stay disabled independently.

In pytest, a unit test checks a small rule, such as when a session expires. An integration test checks components together, such as a signed-in Flask request changing ownership in PostgreSQL. “Red” means a real test fails for the missing feature; “green” means the same test passes after implementation. A broken test environment is not useful red evidence. A fake provider lets us test failure/security rules for free without sending mail or calling an AI API, but it does not prove that a real provider meets the requirements.

**Completed now:** approved specification read; detailed phased implementation/test plan written; read-only cloud source access retried and limitation recorded. **Tests:** behavioral cases planned here; executable pytest tests not yet written, collected or run. **Implementation/integration:** not started. **Precise blocker:** actual repository source remains unreadable through available cloud readers, so real import/route/schema-matched tests and expected failures cannot be validated; a permitted cloud pytest runner and isolated test storage must also be confirmed before running.

No further approval of this plan or unchanged specification is needed to continue the SDD sequence. Next, when authorized cloud source/execution access is available, complete Phase 0 and write/run the tests to meaningful expected failures before implementing their features. Provider choices/terms/configuration and any live release remain separate decisions, with integrations disabled until genuinely ready.

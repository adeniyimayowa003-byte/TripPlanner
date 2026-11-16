# Phase 10 — Accounts, Help and optional AI

**Status: proposed specification; awaiting explicit user approval.**
**Date:** 9 November 2026 (Asia/Shanghai). **Project:** TripPlanner.
**Deliverable scope:** product and security specification only. No implementation/test plan, tests, application code, service provisioning or deployment is authorized by drafting this document.

## 1. Evidence and authority

Public source: https://github.com/adeniyimayowa003-byte/TripPlanner

Supplied last-verified documentation/source commit: `b7d2ee2988930db9e0f755be75ea6bff035c9668`. Supplied deployed-code commit: `b969af3b575b3827ec08b51976e812044f38e100`. Public demo: https://tripplanner-mayowa.onrender.com/.

On the drafting date, cloud reads of the repository, SPEC.md, PLAN.md, PRIVACY.md, README.md, the specs directory and the demo failed. Their contents and exact current route/schema/native-wrapper details were **not independently inspected**. All release facts below come from the user-supplied verified context. File paths, supported auth callbacks, data representation and compatibility with existing specifications remain source-dependent assumptions to reconcile before the later plan. No claim of a fresh source audit is made. A conflict must be surfaced for specification revision, never silently resolved by changing production.

Standards consulted successfully: [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html) and [RFC 8252, OAuth for Native Apps](https://www.rfc-editor.org/rfc/rfc8252). These support the identity protocol recommendation and system-browser approach; they do not establish any vendor's free tier, email allowance or compatibility with this repository. No contemporary vendor quota is asserted.

## 2. Baseline that must remain intact

TripPlanner currently uses Flask/Python, HTML/Jinja/CSS and small vanilla JavaScript. Its curated catalog covers Paris, Lagos, London, New York City, Tokyo and Cape Town, with 48 sourced venues and 18 licensed photos. Explainable interest/pace/family scoring feeds a greedy daily scheduler. Destination currencies are used; prices and time slots are illustrative; unfilled slots remain honest. Maps uses external Google Maps links without an API key. Light, Dark and device theme are per-browser settings. Immutable v1/v2 saved snapshots retain original preferences, results and estimates.

Hosted storage is Render Free plus Neon Free PostgreSQL in Frankfurt, with a stable signing secret and certificate/hostname-verified database TLS. The production namespace is `tripplanner_hosted_v1`. Anonymous saved rows are owned through a protected signed browser cookie, renewed for 365 days, with an owner digest in the database. Clearing that cookie or changing devices loses anonymous access. There are no current accounts, recovery, cross-device sync or integrated LLM.

SQLite previews, Windows downloads and Android downloads hold independent on-device collections. They do not automatically upload or sync. Existing downloads, the 17-slide presentation, 16-page guide and 60-second female-voice intro describe the existing release only.

Historical evidence supplied by the user: 1,688 recorded passing local tests, real PostgreSQL and backup/restore coverage, passing Windows/Linux/Postgres CI, and a 6 November Render restart preserving the QA snapshot and owner/foreign-denial behavior. Windows 11 and an Android 15 emulator were checked; a physical Android phone was not. These are historical baseline results, not validation of Phase 10.

## 3. Product boundaries and approval

The proposed independently releasable boundaries are:

| Phase | Product result | Dependency / default |
| --- | --- | --- |
| 10A | Accessible Help and FAQs | Works without accounts, email or AI |
| 10B | Hosted verified accounts, recovery and deliberate guest-trip claiming | Disabled until identity and recovery prerequisites are approved and configured |
| 10C | Optional native online account access | Separately enabled only for a future compatible native release; offline saves stay independent |
| 10D | Optional integrated AI help | Disabled until provider, privacy and free-only cost gates are satisfied; Help remains sufficient without it |

These are scope boundaries, not an implementation or test plan. There is no fixed 16-week schedule. Approval of this specification permits preparation of the next SDD artifact, not automatic provisioning or deployment. Required order: complete specification and explicit approval → implementation/test plan → pytest tests defined and validated as expected failures → implementation and integration. Any later production action must respect its own authorization boundary.

For this deliverable: cloud-only work, no laptop, desktop apps, browser automation, terminals, private laptop files or credentials; no messages to other people. The cloud-hosted Markdown artifact is the only file produced. No production site, shared database, main branch, downloads or presentation materials may change.

## 4. Guest continuity and account experience

### Guest use

Planning, results, themes, catalog explanations and Help remain usable without signing in or consenting to AI. Existing anonymous saves remain accessible with their valid cookie under the existing ownership rules. A sign-in outage must not block guest planning. Signing in must not automatically merge, claim, export or disclose anonymous trips.

While signed in, new hosted saves belong to the account, clearly labelled as account saves. An existing anonymous collection remains separate until explicitly claimed. Declining a claim changes nothing. Account and anonymous results must never be interleaved without clear ownership labels.

### Maintainable identity recommendation

Recommend a managed, standards-based OpenID Connect identity service with hosted registration/sign-in/recovery, using maintained Flask-compatible integration components. Delegate password storage and verification to that service; TripPlanner should not invent a password database or custom authentication protocol. Vendor selection is unresolved. The selected free offering must support the required verified identity, recovery, logout, rate limits and native flow; otherwise 10B/10C remain disabled or return for a revised specification. “Managed” does not mean a free tier or sufficient delivery allowance has been verified.

Create account and Sign in must be separate, understandable entry points. Registration includes the privacy notice and verification instructions. The first successful verified authentication creates a TripPlanner account bound to the provider's immutable issuer-plus-subject identifier. Email is contact information, never the sole ownership key. Reject unverified identities for account saves/claims. Require a trustworthy verified-email claim or equivalent explicit verification contract from the selected provider. Do not link identities automatically because email strings match; changing provider or linking identities is outside this increment.

Use Authorization Code flow with PKCE, state and nonce protections, exact registered redirect destinations, token signature/issuer/audience/expiry validation and server-side token handling. Reject replayed, expired or mismatched callbacks. Do not place tokens in URLs, browser local storage, snapshots or logs. Authentication must rotate the application session identifier. All sensitive changes require CSRF protection, current authorization and recent authentication as specified below.

### Recovery and failure states

Recovery is through the selected provider's verified channel. Show neutral responses that do not reveal whether an account exists. Recovery links/codes must be single-use, expire within 15 minutes and be rate limited; provider capability must meet this contract before enablement. Expired verification/recovery links offer a limited resend path. Successful recovery revokes existing TripPlanner sessions and requires a new sign-in. The chosen provider must supply a verifiable recovery/revocation signal or an equivalent enforceable session policy; this is a release dependency, not an assumed capability.

Loss of both anonymous cookie and verified account access does not authorize a manual ownership transfer. No staff recovery desk is promised. Provider downtime, mail failure, cancellation and denied consent show a useful message and return safely to guest planning without changing ownership.

### Sessions, authorization and limits

Application sessions use opaque, revocable server-side records and Secure, HttpOnly, SameSite cookies over HTTPS. Default account expiry: 30 minutes idle and 12 hours absolute; no remember-me option in this increment. A session may renew activity only within that absolute lifetime. Claims, account deletion and session-wide revocation require authentication within the previous 5 minutes. The existing 365-day anonymous cookie is not an account session.

Every account list/read/save/delete/claim operation checks ownership on the server, including direct URLs, downloads, AI context selection and native requests. Client-supplied account IDs never grant authority. Another user's trip returns a neutral not-found response without metadata. No public sharing or administrative browsing of trips is introduced.

Proposed mandatory ceilings: sign-in starts 10 per 15 minutes per browser session and per network address; verification/recovery resends 3 per hour per account identifier and 10 per hour per network address; claim/delete attempts 5 per 15 minutes per account. Also require a global 100 authentication starts per minute and a 100 recovery-send/day application ceiling. Provider limits may be stricter. Use bounded, shared, restart-safe enforcement; unavailable enforcement fails closed for affected identity actions. Do not permanently lock an account on attacker-triggered failures. Show retry timing without revealing account existence; allow guest planning. Network limits must account for shared campus networks without bypassing account/global caps.

### Logout and shared devices

Sign out revokes the current application session server-side, clears sensitive client views and AI context, and prevents cached authenticated pages from revealing trips through Back/reload. Authenticated responses use private/no-store caching. “Sign out all devices” revokes all account sessions. Explain that signing out of TripPlanner may leave the identity provider signed in; offer provider logout only if the selected provider supports it, without claiming that app logout signs out every service.

Shared-device guidance must explain that anonymous saves also belong to the browser. Standard account sign-out does not delete unclaimed guest saves. Offer a separate confirmed “Forget this browser's guest access” control that clears/rotates the guest credential, warns that unclaimed saves become inaccessible, and does not affect account trips or silently delete data. An expired session shows no account trips until reauthentication.

## 5. Deliberate claiming of the current guest collection

Possession of a valid current anonymous credential is the existing collection's ownership proof; it cannot identify the human on a shared browser. Verified account authentication alone does not prove anonymous ownership. The UI must explicitly warn about shared computers.

1. A recently authenticated, verified account chooses “Move this browser's guest trips to my account.” Show the verified account identity and a server-derived preview/count containing only trips authorized by the current guest credential.
2. Explain that these trips become account-accessible across devices and cease to be accessible through the old anonymous credential. Require an explicit unchecked confirmation that this is the user's own guest collection. No preselected consent and no claim triggered by login or page load.
3. Bind confirmation to the authenticated account, current guest credential, short-lived one-use nonce (10 minutes) and exact preview membership/version. Revalidate all ownership at commit. Changed membership requires a fresh preview/confirmation; never accept arbitrary row IDs or an owner digest from the client as proof.
4. Commit the ownership transition atomically, all or nothing. Concurrent claims can have only one winner. Repeated confirmation is harmless; partial transfer and cross-account merging are forbidden. Already-account-owned or foreign rows are ineligible.
5. Preserve each snapshot payload's exact stored bytes and version, original preferences/results/estimates, identity and original creation timestamp. Ownership/provenance changes are separate metadata; never regenerate, reserialize or upgrade snapshot contents. Source representation must be inspected before a byte-preservation claim is validated.
6. Consume the old anonymous authority for the claimed rows and rotate browser guest access for future guest use. Record minimal claim provenance without raw cookies, tokens or snapshot contents. Explain success and the destination account; cancellation/failure changes no ownership.

There is no email-based search for guest trips, recovery by guessed ID, bulk database-wide migration, silent reassignment, or automatic local/native import. Account deletion does not return claimed trips to the former anonymous cookie. Claim reversal is outside this increment; explain the consequence before confirmation.

## 6. Hosted versus native collections

Hosted account trips can be accessed on another device after verified sign-in because ownership is tied to the account. Anonymous hosted access depends on the particular browser credential. Offline native and SQLite saves remain on their own device; signing in elsewhere cannot discover them.

For a future 10C-compatible native release, “Continue offline” remains the default. “Open my online account” is explicit, requires connectivity and clearly identifies cloud data. The minimal approved online behavior is opening the hosted account experience in the system browser. It must not silently upload, download into, replace or merge the local collection. Loss of network leaves offline planning and local saves usable; online actions show failure without pretending they were saved.

If a future native build needs an authenticated in-app online client, use the system browser, Authorization Code plus PKCE, state/nonce and registered platform-appropriate callbacks consistent with RFC 8252. No password form in an embedded webview, no embedded client secret and no bearer tokens in deep links. Callback validation, OS-protected token storage and revocation must be demonstrated before enabling that mode. Exact Windows/Android wrapper support is unverified. Unsupported builds use the external hosted experience only. Import/export or synchronization of local collections requires a later explicit opt-in contract and is excluded here. Existing downloads are unchanged.

## 7. Help and FAQs

Provide a persistent Help entry on planning, results and saved-trip pages, usable without accounts and without JavaScript where practical. Include searchable or categorized questions with shareable headings, clear empty-search results and a reset action. All controls support keyboard use, visible focus, semantic headings, screen-reader names, announced status/error messages and 200% text zoom without loss of content. Meet WCAG 2.2 AA contrast targets in Light, Dark and device theme; respect reduced motion and do not use color alone for meaning.

Required approved FAQ answers:

| Question | Required truthful guidance |
| --- | --- |
| Which destinations work? | Only the six named curated cities; this is not worldwide live travel search. |
| What does allowance mean? | A planning budget used for illustrative estimates in the destination currency, not money paid to TripPlanner, a booking, or guaranteed real-world affordability. Exact per-day/per-trip scope and included expense categories must match the existing field/calculation after source reconciliation; do not guess or label it as all travel costs. |
| Why are slots or meals missing? | Catalog coverage, preferences, budget, pace/family suitability and schedule constraints can leave gaps. The greedy scheduler does not guarantee an optimal or completely filled day. Adjust supported preferences or make independent arrangements; do not fabricate venues to fill gaps. |
| Are prices and times current? | They are illustrative. Check the linked venue/source for opening hours, availability, prices and suitability before travel. |
| How does saving work? | Guest hosted saves rely on this browser's protected cookie; clearing it/changing devices loses access. Renewed cookie lifetime is 365 days, not a recovery guarantee. Account saves become cross-device only after the new account feature is enabled; claiming is explicit. |
| Why did my saved estimate not update? | Saved v1/v2 trips are immutable historical snapshots and preserve the original results/estimates. Generate a new trip for a new calculation. |
| How do Maps links work? | They open external Google Maps; internet/service access may be needed. No Google API key or booking is supplied by TripPlanner. |
| Why is the demo slow to open? | Free hosting can sleep and wake slowly. Wait and retry without repeatedly submitting saves. No fixed wake-up time or uptime guarantee is promised. |
| Why are desktop/Android trips different? | On-device collections and hosted collections are independent. Existing apps do not upload or synchronize automatically. |
| What if sign-in or AI is unavailable? | Guest planning and approved Help remain available. Check the specific error and retry later; no paid upgrade is required by this proposal. |
| How do themes work? | Light/Dark/device selection is saved per browser, not automatically across accounts or devices. |
| Is there customer support or emergency help? | This is self-service project guidance. No staffed service, support inbox, response-time promise, ticket queue, emergency monitoring or emergency assistance is provided. |

Do not publish the allowance answer until its source-dependent scope is resolved. Approved Help must reflect enabled features, label future features as unavailable, and never suggest that current downloads already contain them. Optional feedback text can explain limitations, but no contact address, submission form or ticket workflow is invented.

## 8. Optional integrated AI assistant

### User contract and grounding

10D is optional, separate from the deterministic planner and off by default. The entry point says “AI travel/help assistant” and discloses fallibility, provider data transfer, retention terms and limitations before any message is sent. No background invocation or prefetch. Only verified signed-in users may make integrated model requests in this increment; guests get Help/FAQs. AI failure or refusal must not block planning, account recovery or saved-trip access.

Ground answers in a versioned approved FAQ and selected catalog source excerpts. With no trip selected, send no trip. A user may select exactly one currently authorized trip through an explicit context control showing the fields to be sent. Include only destination, necessary preferences, itinerary entries and illustrative estimates; exclude identity/email, cookies, tokens, account IDs, other trips, payment details and unnecessary free text. Turning trip context off clears it immediately. Deletion, logout, ownership loss or session expiry invalidates selection; reauthorize on every request.

Disclose that question text itself goes to the provider and advise against entering sensitive information. Obtain per-session AI consent and a distinct per-trip context opt-in. Send no full trip merely because its page is open. No transcript persistence in TripPlanner; conversation is session-memory only, cleared on logout/expiry, with the bounded context below. No user content may be used for provider training unless separately approved; if the free provider cannot meet the approved retention/training contract, keep integrated AI disabled.

Every factual catalog/FAQ answer includes app-controlled source references that resolve to the corresponding approved FAQ heading, catalog entry or stored source link and version. Validate citations against retrieved source IDs; do not trust model-invented URLs. Unsupported facts receive an explicit “not verified in TripPlanner” response and a suggestion to check official sources. Never invent venues, exact prices, hours, safety conditions or bookings as verified. Distinguish illustrative snapshot estimates from current facts. An answer without valid supporting references for its factual claims is withheld or replaced with a grounded FAQ response.

### Security and action limits

Model credentials remain in server-side secret configuration and are never embedded in HTML, JavaScript, native packages, logs or error responses. Server-selected provider endpoints are allowlisted; model output cannot choose URLs for server fetching. No browsing arbitrary URLs, executable tools, database access, bookings, payments, itinerary mutations, account changes or autonomous external actions are available to the model. AI may suggest actions in words only.

Treat prompts, catalog text, source excerpts and model output as untrusted data. Retrieved instructions cannot override system rules, request secrets, broaden context or grant authority. Isolation and server-side authorization enforce these boundaries even if a prompt-injection attempt persuades the model. Render escaped plain text or a strictly sanitized Markdown subset; no raw HTML, scripts, remote images or executable links. Only validated approved source links are clickable. No user-supplied HTML is trusted.

### Hard limits and fallback

Initial product ceilings, independent of any provider quota: 5 requests/minute and 20/day per account; 100 requests/day globally; maximum one in-flight request/account and two globally; maximum 1,000 characters/question; maximum four previous turns; total provider input at most 6,000 tokens including instructions, sources and selected trip; maximum output 600 tokens; 15-second end-to-end timeout; no automatic retry. Reject excess context instead of truncating rules or mixing users. Provider limits may reduce these ceilings, never increase them silently. Counters and reservations must be shared and durable across workers/restarts, use UTC daily reset with user-visible reset timing, and count failed attempted calls conservatively.

Enforce a provider-side zero-spend/no-billing boundary as well as application caps. A free token allowance that can roll into charges is insufficient. If no enforceable free-only arrangement exists, integrated AI stays disabled. At quota exhaustion, timeout, malformed/unsafe output, provider outage or disabled configuration, show a short accessible explanation and relevant local FAQ links. Do not return partial unverified content or auto-switch providers/paid models. Manual retry is available within remaining limits. Core planning makes no model calls and does not consume AI quota.

### External AI link is different

An optional “Open external AI service” button is a labelled external link, not an integrated assistant. Warn that the user leaves TripPlanner and the external service has its own terms. No trip, question, account identifier, credential or referrer containing trip details is automatically sent, including through URL parameters. The user can separately choose what to type or copy there. A ChatGPT subscription does not supply website API access; this conversation cannot serve as TripPlanner's backend.

## 9. Data, retention and deletion decisions

Collect only immutable provider identity, verified email if required, account timestamps/state, trip ownership metadata, session/revocation state, minimal consent/claim records and bounded abuse counters. No passwords are stored by TripPlanner. Do not log raw tokens, cookies, recovery links, prompts, selected-trip content or responses. Existing catalog photo licensing/source attributions stay intact.

Proposed retention policy for approval:

| Data | Retention and deletion contract |
| --- | --- |
| Existing anonymous trips | No new expiry or cleanup introduced by Phase 10. Cookie expiry is not database deletion. Existing retention policy is source-unverified and must be reconciled; no destructive cleanup is authorized. |
| Account trips/profile | Retain until user deletes trip/account; no inactivity purge in this increment. |
| Sessions | Expire as above; remove expired records within 24 hours, keeping only required revocation state through original expiry. |
| Abuse/security metadata | Minimal pseudonymous records for up to 30 days; short-lived rate counters expire when no longer needed. |
| Claim/consent records | Keep with the active account; delete on account deletion except minimal deletion/revocation marker needed to prevent restoration. |
| AI conversations | No application transcript storage; session memory only. Provider retention must be explicitly verified and disclosed before enablement. |
| Backups | Any backup containing newly introduced account data must expire within 30 days; otherwise accounts remain disabled until a revised policy is approved. Existing backup retention is not asserted. |

Verified users can delete an individual account trip or delete their account after recent reauthentication and a clear confirmation. Access and sessions are revoked immediately; active application data is erased within 24 hours. Deletion includes claimed snapshots, does not alter others' data, and is not undone by backup restoration. Maintain a minimal protected deletion ledger through backup expiry so restores reapply deletions before serving traffic. No raw trip data in that ledger. Provider identity deletion must be supported or a truthful separate provider-deletion procedure disclosed before registration; TripPlanner deletion cannot falsely promise deletion of an unrelated provider-wide account. Provider deletion failures leave the application account disabled and display the outstanding state without restoring access. No unclaim-to-guest side effect.

Privacy notice must identify the chosen processors, actual data regions/transfers, purposes, consent withdrawal, deletion procedure and retention limits before activation. Do not assume the Frankfurt app/database location constrains identity/AI processing. No new analytics or advertising tracking.

## 10. Free-only prerequisites and unresolved decisions

No payment method, upgrade, paid trial, paid API call or new charge is authorized. Render/Neon are the supplied existing baseline, not a claim that every proposed feature fits their current quotas. Free sleep and quotas are acceptable; silent billing fallback is prohibited. No accounts/services are provisioned during drafting. Never request passwords, keys or database connection strings in chat; any future secrets go directly into the approved service's secure configuration UI.

| Decision | Exact dependency before enablement | Result if unresolved |
| --- | --- | --- |
| Identity vendor | User chooses provider and accepts its terms/privacy; verify official current free-plan limits, no-card/no-charge behavior, OIDC features, verification/recovery, callbacks, revocation, regions and deletion | 10B/10C off; guest and Help work |
| Verification/recovery delivery | Confirm provider-included delivery or separately approved free email service, sender/domain requirements, quotas, expiration and delivery behavior; no assumed free SMTP | Registration/recovery unavailable; do not enable accounts with broken recovery |
| Native online mode | Confirm actual wrapper/platform callbacks and secure storage; browser-only hosted access is the minimum | Existing offline apps remain independent |
| AI vendor/model | User chooses service and accepts terms; verify official no-charge enforcement, API eligibility, limits, retention/training and processing region; securely configure credentials later | 10D off; FAQ fallback |
| Hosting/storage capacity | Confirm existing free resources can uphold shared counters, sessions, retention and backups without upgrades | Keep affected increment disabled; revise scope if needed |
| Allowance/source reconciliation | Read actual budget semantics and existing specifications/architecture | Do not publish ambiguous FAQ or finalize dependent plan |

No vendor-specific free-plan claim has been verified or is relied upon here. The architecture recommendation is approved separately from selecting a provider. Selection, terms acceptance, credentials and any spending are distinct user decisions; specification approval does not make them happen.

## 11. Product and security acceptance criteria

These are observable completion requirements, not test code or a test execution plan.

| ID | Acceptance requirement |
| --- | --- |
| AC-01 | With all new integrations off or unavailable, guest planning, existing owned saves, themes and Maps retain baseline behavior; no external model/auth call occurs during normal guest planning. |
| AC-02 | Help is available signed out, covers every required FAQ accurately, works by keyboard/screen reader at 200% zoom, and meets contrast requirements in all themes. Allowance wording matches reconciled source semantics. |
| AC-03 | Cancelled, unverified, forged, expired, replayed or wrong-issuer/audience/callback authentication cannot establish an account session; valid verified registration/sign-in can. No email-only account linking occurs. |
| AC-04 | Recovery gives non-enumerating responses; links expire within 15 minutes, are single-use and rate limited; completed recovery revokes old sessions. No recovery path transfers another person's trips. |
| AC-05 | Session idle/absolute limits, recent-auth requirements, CSRF protection, rotation, logout and all-device revocation are enforceable server-side. Back/reload after logout reveals no account data. |
| AC-06 | Account B cannot list/read/export/delete/claim or send to AI any trip belonging to A, by direct identifier changes or through any web/native endpoint. Invalid access reveals no foreign metadata. |
| AC-07 | Login alone and a declined/cancelled claim leave all guest ownership unchanged. Claim preview contains only current-credential-owned rows and states the destination account/shared-device warning. |
| AC-08 | Confirmed claims are atomic, membership-bound, replay-safe and race-safe. Tampered IDs, foreign/expired cookies, stale previews, other-account rows and wrong sessions cannot transfer trips. |
| AC-09 | Claimed snapshot payload bytes, versions, original values, IDs and creation timestamps match their preclaim values exactly. The old guest credential cannot access claimed rows; unrelated rows remain untouched. |
| AC-10 | Cross-device sign-in shows only that account's hosted saves. Offline/SQLite/native collections neither upload nor merge on sign-in, browser launch, account creation or logout. Existing downloads are unchanged. |
| AC-11 | Native online authentication, if enabled, uses an external system browser and approved callback protections; no embedded secret/password capture or token-bearing deep link is present. Offline behavior remains usable without network. |
| AC-12 | All identity/action/global caps apply across simultaneous workers and restart; blocked/unconfigured states give accessible fallback and cannot bypass quotas through a new client session. |
| AC-13 | AI remains disabled without all provider/privacy/free-only gates. Guests and users without consent cannot cause model requests. Selecting no trip sends no trip; switching/logout/deletion immediately prevents reuse of old context. |
| AC-14 | Every model request contains only allowed bounded context for one authorized selected trip. Over-limit input/output, timeout and concurrency failures resolve to Help without automatic retries or paid fallback. |
| AC-15 | Prompt injection and hostile model output cannot disclose another user's data/secrets, execute markup, initiate bookings or mutate accounts/trips. Citation IDs resolve only to approved sources; unsupported factual responses are replaced or clearly withheld. |
| AC-16 | External AI links automatically transmit no trip/question/credential/identifier. UI accurately distinguishes external service, integrated AI and deterministic planning. |
| AC-17 | Account/trip deletion meets immediate revocation, 24-hour active erasure and 30-day backup expiry requirements; restoration cannot resurrect deleted access/data or reassign it to guests. |
| AC-18 | New privacy notice reflects real configured processors and terms. No prompts/tokens/snapshot contents appear in logs or public artifacts; API secrets are absent from clients and downloads. |
| AC-19 | Production namespace, legacy anonymous authorization, stable signing-secret continuity, verified database TLS and existing snapshot behavior remain intact. No reset, blanket reassignment or copying private rows to public artifacts occurs. |
| AC-20 | Feature labels and published materials describe only what is actually enabled and validated. Historical passing tests and emulator checks are never presented as Phase 10 or physical-device validation. |

## 12. Release and rollback requirements

The present demo remains frozen during the presentation and this specification stage. No release is implied by this document. A later authorized release must have explicit feature switches for Help, accounts/claiming, native online behavior and AI; integrations default off. A disabled switch must prevent server-side calls/actions, not merely hide a button. Help can release independently; AI must never be required by accounts or planning.

Before any later release, exact source/architecture reconciliation, approved specifications and the strict SDD gates must be satisfied, with evidence for applicable acceptance criteria. Any schema evolution must be additive/backward compatible and preserve `tripplanner_hosted_v1`, existing owner relationships and snapshot bytes. Protected backups and recoverability are required; private production rows must not become fixtures or public evidence. No destructive migration or secret rotation as an incidental feature change.

Rollback must first disable the affected feature and external calls while preserving core planning/Help where safe. Stop claims on uncertainty. Never undo legitimate claims by restoring old guest authority, erase newly created account trips, or run a blanket database restore over newer data. After account ownership exists, rollback may use only a compatibility-safe release that continues to enforce account ownership; an old binary that bypasses the new ownership model is not a safe rollback. If safe account access cannot be preserved, account endpoints fail closed with a truthful temporary-unavailable message while guest planning continues. Restore operations must preserve deletion/revocation decisions and verified ownership before reopening access.

Release notes must separate proposed, disabled, enabled and verified capabilities. Current Windows/Android downloads and presentation artifacts remain unchanged until separately authorized, updated and validated. No new claim of staffed support, live travel verification, physical-phone coverage or unlimited free availability is allowed.

## 13. Beginner explanation and approval checkpoint

A specification describes **what users should be able to do and the rules it must obey**. It is different from the later plan explaining how to build it.

Authentication means proving who signed in. Authorization means checking which trips that person may access; a successful login is not permission to read everybody's trips. A guest cookie proves control of one browser collection, while an account can identify the same owner across devices. Claiming is the user's explicit decision to move only that browser's guest trips into the verified account without rewriting the saved itinerary.

The current planner uses fixed catalog data and scheduling rules. An optional LLM generates language and can make mistakes, so it needs approved sources, limits and a reliable FAQ fallback. API access is a separate service from a ChatGPT subscription. A feature switch lets an optional component stay off without breaking the demo. Acceptance criteria state observable pass/fail outcomes; rollback requirements define what must remain safe if a future release is disabled.

**Only this proposed specification has been produced. Nothing has been implemented, tested, provisioned or deployed for Phase 10. Explicit user approval of this specification is required before preparing the implementation/test plan. After that plan, pytest tests must be defined and validated as expected failures before implementation and integration.** Unresolved provider selections remain separate decisions and their integrations remain disabled.

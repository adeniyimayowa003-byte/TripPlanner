# TripPlanner assistant increment — current cloud handoff

**16 November 2026 · Tested source candidate · Not deployed**

This is the newest handoff. Earlier Phase 10A/10B reports and logs are preserved as history. Development resumed from the exact latest **updated** bundle (`libfile_3c5f13bb22a081919caa289a4e02ecab`), not the original submission ZIP. Its SHA-256 is `5e3080b357de0d8bd9a266410847a5e59d2fed711cb2df9a06be138033917755`; archive integrity and Library identity were verified before extraction into a new managed-cloud source copy.

## Feature and verification checklist

| Feature | Current state |
| --- | --- |
| Earlier Help & FAQs | Preserved; availability answer revised and FAQ version advanced to 2 to describe this candidate accurately |
| Earlier account-session foundation | Preserved byte-for-byte, including all 77 existing account tests |
| In-app assistant UI | Implemented at `/assistant`, with navigation, sample questions, single-turn conversation, clear action, native HTML controls and existing Light/Dark/device theme tokens |
| Guest/local/offline-provider fallback | Working deterministic FAQ/catalog answer selection, approved excerpts and internal source citations; no model/account required |
| Integrated model server path | Implemented and tested through the actual Flask app with existing real session service, isolated SQLite admission storage and simulated provider/HTTP transport |
| External HTTPS adapter | Implemented, allowlisted and tested without external network. Keys stay server-side. No redirects/retries/tools/actions. **No live provider call** |
| Selected-trip context | Projection, explicit opt-in, owner rechecks and late-result invalidation tested using a read-only synthetic owned-trip SQLite gateway. Actual production account-trip/claim integration is **not implemented** |
| Actual sign-in/account flows | **Not enabled**; no OIDC callback, registration, mail recovery or public development login was added |
| Production PostgreSQL accounts/quotas/claims | **Not implemented or validated**. Existing trip adapters/schema/namespace remain unchanged |
| Browser/accessibility/native delivery | Semantic and script tests performed. Real browser rendering, screen-reader/zoom, Back-cache lifecycle, builds/emulators/physical devices and new download verification **not performed** |
| Live site/downloads/presentation | **Unchanged**; no deployment, migration, main-branch push, secret rotation or presentation update |

Classification: **usable in-app FAQ fallback plus an implemented/tested but unconfigured and gated LLM server adapter**. It is neither just an external AI link nor a verified live-model assistant. The default source candidate uses FAQ mode only. No runtime is installed by any application factory. Model and transport behavior was simulated in tests; no website account or API session was reused.

## What a user can do in this source candidate

Open Assistant from navigation after running this candidate in an isolated approved environment. Ask “What does my allowance cover?”, “Why are meals missing?”, “I cleared my cookies and lost my trips”, or “Tell me about the Eiffel Tower”. The page shows your question and the selected approved excerpts, with links to `/help#...` or a read-only attributed catalog-source page. Unsupported questions explicitly say the information is not verified. No venue fact, current price or opening hour is invented.

Forms work without JavaScript. Each submission is a fresh turn; no prior conversation is sent to a model. Samples submit only when clicked. Clear conversation opens a clean page. Questions are POSTed rather than placed in URLs; they are not put in the signed draft cookie or an application transcript. The page uses no-store and no-referrer headers. Optional JavaScript clears private DOM content, consent controls and input on navigation/restored-page events; it neither stores history nor makes network calls.

Native/local core can use the fallback without an online model while the application service and bundled data are available. The hosted website itself still requires internet; this is not a new offline PWA or a promise that an unreachable hosted server can answer.

The model/trip controls are disabled in the default candidate. There is no public test identity or fake login. All public model attempts lacking real configured authority fall back, even when the visitor forges an account cookie, account ID, trip ID or consent fields.

## Server model path and guarantees tested

`assistant_runtime.py` composes trusted session, trip-reader, admission and provider interfaces only when server-installed dependencies exist. Strict readiness checks cover identity, privacy, free-only, provider and storage, plus a required concrete provider/region/retention/HTTPS-terms disclosure and no-training attestation. A readiness flag without that disclosure cannot enable calls. The disclosure is rendered before the user question; test-only disclosure values are visibly synthetic. Current factories install none. Test readiness comes from pytest configuration with internally issued synthetic identities, never an HTTP sign-in endpoint. Those tests do not establish actual OIDC authentication or provider entitlement.

Every model turn requires HTTPS, a currently resolved account session, explicit question-transfer consent and, independently, an optional trip ID plus trip-transfer consent. No selected/consented trip means no trip in the outgoing payload. Context is reauthorized before dispatch, after connect in the HTTP adapter, and after response. Lost ownership, changed snapshot fingerprint, deleted/revoked session or expired authority discards the result. The gateway must return account-kind ownership for the resolved account; guest owner digests never become account authority.

Projection permits only destination, necessary preferences, allowance/currency and day/slot/venue/illustrative-estimate entries. Tests seed extra private metadata and show that email, title-like metadata, secrets, account IDs, account token and private row IDs do not enter the model payload. Snapshot serialization/validation is reused for reading; no saved row or snapshot payload is written. The selected-trip citation page checks current account ownership again. Its test gateway is explicitly synthetic and is not a new production collection or a substitute for approved guest claiming.

Provider output is a small JSON selection of at most three unique server-supplied source IDs. The answer is rendered from the server's exact excerpts. There is no arbitrary generated factual prose or model-provided clickable URL. Invalid citations, extra fabricated text, raw HTML, duplicate keys/IDs, tools, truncation, oversized bodies and unsupported output are withheld. Retrieved/user text is treated as data; no tool, booking, payment, database command or account mutation capability is available to the model. Jinja escapes both questions and answers.

Limits tested: 1,000 characters/question; zero prior turns sent (within the four-turn ceiling); context projection <=3,500 UTF-8 bytes; model input <=6,000 tokens including a 200-token framing reserve; model output <=600 tokens; 15-second trusted request budget, never restarted by the inner pipeline; one attempt and no automatic retry. Actual model tokenization is a mandatory future provider-specific dependency—test counters are not proof of a real model's token accounting.

`assistant_limits.py` is an explicit separate **development SQLite** adapter with atomic shared counters: 5/account/sliding minute, 20/account/UTC day, 100 globally/UTC day, one in-flight/account and two globally. UI messages include retry seconds or the UTC reset notice. New sessions/accounts/restarts do not refund calls. Failures consume attempted-call counts conservatively. Missing/incompatible storage blocks models; existing trip files are refused rather than reset. Production must use reviewed shared durable storage; no ephemeral SQLite fallback was wired to hosting.

The runtime holds a worker's reservation until it actually finishes, including after a user-facing timeout. This avoids admitting additional concurrent external work when DNS or a transport remains stuck. A crash-abandoned active reservation deliberately fails closed across restart; recovery requires confirmation the old worker cannot still send. There is no public reset endpoint or automatic lease expiry that could exceed the global cap. This conservative availability limitation and a production maintenance policy remain activation prerequisites; local FAQs keep working.

`assistant_provider.py` implements server-only HTTPS chat JSON with a required explicit host/model/credential/token-counter configuration, TLS certificate checks, bounded response reads, deadline checks, no redirects and no retry. No key is read from a browser or shipped in native staging. The HTTP adapter checks authority/deadline after connection and before sending data. Slow DNS can keep a worker alive longer than the UI deadline, but cannot release its concurrency reservation early or send after the adapter notices expiry. Live DNS/TLS/provider behavior was not exercised.

## Actual SDD and test record

Planning detail was recorded first in `plans/phase-10D-assistant-increment.md`. New tests live in `tests/test_phase10_assistant_*.py`. Logs are under `docs/phase-10D-evidence/`; command/runtime details are preserved. All tests ran in the managed cloud copy against the actual project. No laptop tools, browser control, desktop app, native build/emulator, stress test or paid service was used.

| Checkpoint | Actual result |
| --- | --- |
| Recovered baseline | 1,773 passed, 9 skipped |
| UI red before implementation | 19 failed, 1 passed; missing routes/navigation/behavior |
| Initial UI implementation | 18 passed, 2 failed; catalog cost type fixed, and one boolean-HTML assertion corrected to check attribute presence rather than its `None` parser value |
| UI green | 20 passed |
| Quota module absence | 2 failed, 12 fixture errors; **not** treated as valid behavioral red evidence |
| Quota-store scaffold red / green | 2 failed / 2 passed, remaining cases deselected |
| Reservation red / green with working real fixtures | 12 failed / all 14 quota tests passed |
| Real Flask pipeline red / green | 8 failed, 23 passed / all 31 passed |
| Server HTTP adapter red / green | 19 failed / 19 passed |
| Interim full regression | 1,857 passed, 9 skipped |
| Privacy script/endpoint hardening red / green | 4 failed, 4 passed / all 8 passed |
| Candidate disclosure red / green | 1 failed / new disclosure plus 17 existing Help tests passed; FAQ version assertion intentionally revised from 1 to 2 for changed content |
| Request deadline API probe | Unsupported argument; recorded as an API absence probe, **not** behavioral validation |
| Deadline behavioral red / green | A signature-only scaffold still incorrectly sent a model request after budget expiry; 1 failed. After budget propagation, new deadline test plus 31 runtime tests passed |
| Retry-timing red | 1 failed, 10 passed; explicit retry seconds were missing |
| Intermediate assistant suite | 97 passed in 2.44s |
| Interim entire suite before final privacy changes | 1,870 passed, 9 skipped in 57.15s |
| Provider disclosure gate red / green | 3 failed before missing-disclosure enforcement; all 100 then-current assistant cases passed after adding the gate and explicit synthetic disclosure to test setup |
| In-flight response privacy red / green | 1 failed, 3 passed before rechecking response authority; after the fix all **101 assistant tests passed in 2.73s** |
| Final entire suite | **1,874 passed, 9 skipped in 48.96s; exit 0** |
| Final source audit | `python release_checks.py`: 0 findings; exit 0 |

No planned-only case is counted as executed. Negative security tests that already passed at a scaffold stage are preservation evidence, not proof the model path worked. Positive real-app provider-call tests failed until the actual pipeline was integrated. Simulated transport was additionally connected through the real Flask route and real adapter; this is not called a live LLM call.

The nine skips remain the existing actual PostgreSQL repository/concurrency/restore cases requiring an explicitly guarded disposable loopback administrator DSN. No such DSN or server is configured; `postgres`/`pg_ctl` are not available on PATH. SQLite and mocked transport evidence cannot replace these checks. Current runtime is Linux/Python 3.12 with pinned pytest 9.1.1; exact versions are recorded in `environment.json`, and the actual privacy script ran under cloud Node. Python 3.14, Windows CI, real browsers and native devices were not rerun.

## Preservation and remaining blockers

Byte comparisons confirmed `account_sessions.py`, its five 77-case test modules, `hosted.py`, `hosted_postgres.py`, `hosted_saved_trips.py`, `saved_trips.py`, `snapshots.py` and `version.py` are unchanged from the latest Phase 10B bundle. Existing guest authorization, schema identity, `tripplanner_hosted_v1`, signing-secret continuity, TLS configuration and immutable snapshot contracts are not modified. All original catalog/photo/license assets are retained. New native source staging resources are included for future compatible builds; current downloadable apps were not rebuilt or overwritten.

Actual registration/sign-in/recovery/session transport, auth/recovery quotas, PostgreSQL account/admission adapters, ownership mapping and atomic guest claims, deletion/tombstone/restore contracts and native online mode remain unfinished. Model mode cannot be activated simply by supplying an API key. It still needs those prerequisites, a real authorized trip gateway, provider-specific token accounting, completed privacy disclosure and a verified free-only provider contract. No app startup auto-enables it from environment variables.

Specific external decisions are recorded in `docs/phase-10D-provider-decisions.md`: select managed identity/email and model services, verify actual free/no-billing and data-use terms and accept them in the user's own account. Do not send passwords, keys or connection strings in chat. Groq was investigated as one candidate, not chosen or certified; no universal free quota or no-training assurance is invented. A ChatGPT subscription/session is never used as this application's backend.

Accessibility uses semantic headings, labels, native controls, status/alert messages, wrapping styles and existing theme/focus tokens. Real rendered contrast/200% zoom/screen-reader/Back-cache checks remain unverified; Node lifecycle tests are not browser certification. Existing downloads, live demo, production data, repository main, PPTX/DOCX and intro video remain unchanged. No deployment or production migration is authorized by this bundle.

## Beginner explanation

FAQ mode finds an approved answer and shows where it came from. It works without an AI company. A language model is different: it receives explicitly permitted text and suggests which approved sources answer the question. The server checks that suggestion and displays the checked excerpts, so a made-up price or booking claim cannot appear as verified model prose.

Authentication answers “who signed in?”; authorization answers “may this account read this trip?”. Consent answers “did this person choose to send this question and trip?”. All three must hold before any provider call. A rate limit keeps free usage bounded. A fallback keeps the ordinary planner useful when AI is off, exhausted or broken. Red tests expose missing behavior before implementation; green tests check the same behavior after changes. A skipped test was not checked.

This increment delivers the usable assistant experience and a tested server integration while preserving the approved dependency/security order. Remaining provider/account/real-database gates are explicit; no new approval of unchanged scope is requested.

# Provider decision record — 16 November 2026

No provider has been selected, connected or activated. No account was created, terms accepted, credential read, model called, email sent or payment method added. Free-only is still mandatory. These are primary-document checks, not proof of the user's account entitlements.

## Technical adapter

[OpenAI chat API reference](https://developers.openai.com/api/reference/resources/chat) was read for the chat JSON request/response shape. The code sends a bounded messages request with a completion cap and no tools, and reads a single stopped message. It does not assume OpenAI is free or that a ChatGPT subscription includes API access. OpenAI has not been chosen as the provider.

[Groq compatibility docs](https://console.groq.com/docs/openai) identify the alternative `/openai/v1` base path. The adapter explicitly allows its chat-completions path as well as `/v1/chat/completions`, with an exact configured HTTPS host. This is tested with a fake host/transport, not a Groq call or a compatibility certification for any selected model.

## Groq is a candidate to evaluate, not an activation recommendation

- [Billing documentation](https://console.groq.com/docs/billing-faqs) distinguishes Free and paid Developer tiers and says upgrading requires a payment method. The user's actual tier and an enforceable no-charge/no-upgrade boundary were not inspected. A community FAQ search result suggested no-charge behavior but its direct page redirected elsewhere; it was not used to certify this contract.
- [Data documentation](https://console.groq.com/docs/your-data) describes always-retained usage metadata, exceptional input/output logs up to 30 days, user-controlled Zero Data Retention, and US storage. This establishes issues to disclose and configure; it is not proof of account settings or a complete no-training contract.
- [Services agreement](https://console.groq.com/docs/legal/services-agreement) and the chosen model's license/terms need user acceptance. Exact eligibility and no-training assurances for the intended student/public demo have not been established here. No fixed free-model quota is asserted.

The API key would eventually be entered directly into secure server configuration, never chat, JavaScript, a native package or a source file. The UI's live-mode processor/region/retention notice must be completed using the actually chosen service before privacy readiness can become true. Server readiness booleans are fail-closed gates, not independent verification of a provider's billing/legal controls.

## Specific unresolved inputs and code prerequisites

| Item | Needed before live activation |
| --- | --- |
| Managed identity/email choice | A chosen free OIDC service and verified-mail/recovery arrangement meeting the approved 15-minute single-use recovery and session-revocation contract, with user-accepted terms. None is selected; no public mock login is allowed. |
| Model choice | User-selected provider/model after current official free-only, no-training/retention/region and no-billing controls are verified; actual model tokenizer and endpoint compatibility. The generic adapter alone is insufficient. |
| Secret setup | User configures future credentials in the approved secure service UI; do not paste values into chat. |
| Production account/trip backend | Remaining verified sign-in/recovery/session transport, actual PostgreSQL accounts and quotas, deletion/retention/restore, opt-in claims and authorized trip gateway, with real isolated PostgreSQL tests. Current prototype SQLite is not a production fallback. |
| Release | Separate explicit authorization and release verification. This development task has not changed the live presentation release. |

Unrelated core/Help/FAQ functionality is complete enough to use in the source candidate while these remain unresolved. No repeat approval of the approved specification or unchanged plan is needed for further isolated test-first development. Provider decisions alone will not magically enable the unfinished sign-in/PostgreSQL work.

# TripPlanner public website availability specification

**Status:** APPROVED by the user on 2 November 2026. Proceed through planning, validated tests, then implementation. Provider/account setup and any paid recurring service still require the separate decisions in section 4.  
**Date:** 2 November 2026.  
**Approved availability revision:** The user subsequently selected “Use a free demo; I accept sleep and other free-plan limits.” The [free-demo amendment](phase-09-free-demo.md) replaces the continuous-availability/paid-disk proposal. Saved-trip durability and visitor isolation remain required. No paid resources or upgrades are authorized.  
**Requested outcome:** Other people can open TripPlanner through a public website address, including when the developer's laptop is switched off. The user explicitly selected online hosting rather than automatic startup on this laptop.  
**Related foundation:** [Product specification](../SPEC.md), [delivered local release](phase-08-expanded-release.md), and [release evidence](../docs/final-release-checks.md).

## 1. Problem and outcome

The current address, `http://127.0.0.1:5001/`, refers to the computer on which the browser runs. TripPlanner currently relies on a development process running on the developer's laptop. Stopping that process, restarting the laptop, or making the laptop unavailable prevents requests from reaching it. Restarting the preview repairs local access but does not create an independent public website.

Deliver a separately hosted TripPlanner website with a real public HTTPS address. Visitors can use a normal desktop or mobile browser without installing Python, opening the developer's computer, or starting a local server. The hosted Python application must run on the hosting provider's infrastructure and remain independent of the laptop and its local preview.

The revised service is a free classroom demo: idle sleeping, a wake-up delay, provider quotas and temporary suspension are accepted. It remains independent of the laptop. Saved trips must still use persistent storage outside an ephemeral web-service filesystem. There is no continuous-availability guarantee. See the approved free-demo amendment for the controlling availability target.

## 2. Scope

This increment includes:

- Public browser access to the current six-city planning flow, recommendations, daily itinerary, themes, local photographs, credits, and external Google Maps links.
- A production server, HTTPS, a stable public URL, health checks, and provider-managed process restart.
- Persistent hosted storage and stable session-signing configuration that survive ordinary application restarts and redeployments.
- Separation of different visitors' hosted saved-trip collections, without introducing account registration in this increment.
- Deployment instructions, recovery/backup instructions, and a clear explanation of local versus online data.

This increment does not add worldwide discovery, live prices, bookings, a trained model, a chatbot, payments, email, accounts/passwords, cross-device synchronization, app-store publication, or embedded Maps. Existing Windows and Android downloads remain independent local applications. They do not begin uploading their trips or depending on the online website.

## 3. Public access

1. A visitor opens the actual deployed HTTPS address and can complete the planning flow without developer tools or access to the developer's network.
2. A provider-supplied domain is sufficient. Purchasing a custom domain is optional and excluded unless separately requested.
3. The website must work at desktop and mobile widths, with the same supported destinations, currencies, input limits, scoring rules, scheduling rules, and travel-data limitations as the delivered local application.
4. Public pages must not refer visitors to the developer's `127.0.0.1`, private network address, source folder, or Windows executable to complete the browser flow.
5. The website needs an internet connection. The downloadable applications keep their documented local behavior. The online website is not described as an offline replacement for those applications.

## 4. Availability and operating costs

1. The selected service must support a running Python backend, HTTPS, persistent storage, and restarting an unhealthy/stopped application process.
2. Strict continuous availability requires a service configuration that does not deliberately sleep after inactivity. A free plan with a wake-up delay or an expiring database does not satisfy that requirement unless the user explicitly accepts the limitation as a revised demo target.
3. A production WSGI server must run the hosted application. Flask's development server, debugger, and reloader must not serve the public deployment.
4. A health/readiness endpoint must expose only operational status, with no trip contents, signing secrets, filesystem paths, or visitor identifiers. Unavailable required storage must not appear healthy or silently redirect saves to temporary storage.
5. Startup must fail clearly if required production settings are absent, rather than generating a new temporary secret or selecting a disposable database silently.
6. The hosting provider, region, plan, ongoing compute/storage costs, and any account or domain requirements must be presented before provisioning. The user must approve any spending limit and paid service before charges are incurred. No provider or paid plan is selected by this draft.
7. Do not use periodic fake traffic to evade a provider's idle policy, expose the laptop through port forwarding, disable sleep/security protections, or treat a temporary tunnel as permanent hosting.

## 5. Saved trips and visitor separation

The current local web collection is shared by browsers using the same server/database. Publishing that collection unchanged would let unrelated visitors view one another's saved plans. The hosted mode must therefore isolate collections before public release.

1. A visitor can generate, name, save, list, and reopen their own hosted plans without registration.
2. An unpredictable, protected browser identifier establishes the hosted collection. The server must verify that identifier and derive ownership from it. A submitted form field, URL parameter, or guessed trip number must not let a visitor choose another collection.
3. Another visitor must not see a saved trip's title, preferences, estimates, contents, or existence through collection pages, direct URLs, duplicate-save responses, or error pages. Unauthorized and nonexistent trip details must give the same ordinary unavailable/not-found outcome.
4. Identical plans and titles saved by two visitors must belong to separate collections. Deduplication must operate within the current visitor's collection.
5. Reopening in the same browser/profile must retain access across normal hosted-server restarts and redeployments, while the identification cookie remains available. The documented cookie lifetime and browser storage limitations must be clear in the implementation plan and UI/privacy text.
6. Clearing browser cookies, changing browser/profile/device, or using private browsing can lose access to an anonymous collection. The UI must explain that there is no account recovery or cross-device sync in this increment. People sharing the same browser/profile may share that collection.
7. Hosted saved snapshots retain their reviewed contents. Ownership metadata must not rewrite snapshot JSON, historical estimates, or v1/v2 fingerprint meanings. Any required storage change needs a tested migration or fresh hosted schema with an explicit compatibility contract.
8. No existing laptop, Windows-app, Android-app, presentation-QA, or local web database is uploaded. The public service begins with an empty hosted collection and the reviewed public catalog/photo assets.
9. Local and native modes keep their existing collection behavior and data locations. Hosted privacy must not silently change or erase the existing local saved trips.

## 6. Persistence and deployment lifecycle

1. The hosted database must use durable storage supported by the chosen provider. An ordinary temporary deployment filesystem is insufficient for SQLite saves.
2. Saved plans and visitor ownership must survive a process restart and an ordinary redeploy of the same release. A successful save must mean the transaction committed to durable storage.
3. Session-signing secrets must remain stable across restarts and must come from private host configuration. They must not appear in GitHub, the image bundle, screenshots, logs, or example configuration.
4. The selected storage architecture must match the deployment's worker/instance configuration. Do not claim independent replicas safely share a local SQLite file without a supported design.
5. Backups and a recovery procedure must be documented and tested using disposable data. No destructive restore, secret rotation, deletion, or migration of the user's existing collection is part of routine deployment.
6. A failed save or temporarily unavailable store must show a useful message and must not report success, clear the reviewed result, or expose another visitor's data.
7. Reviewed source code and public licensed assets are the deployment inputs. Virtual environments, SDKs, desktop packages, signing keys, `.tmp`, private databases, and build caches must not enter the web release.

## 7. Public request handling and privacy

- Disable debug output and public tracebacks. Configure the real public hostname and any trusted proxy handling narrowly for the selected provider.
- Protect state-changing forms with the existing CSRF contract. Use HTTPS and protected, HTTP-only identification/session cookies with an appropriate SameSite policy.
- Prevent shared browser/CDN caches from serving one visitor's saved or preference pages to another visitor.
- Keep credentials, cookies, form bodies, and saved-trip contents out of application/access logs. Record enough operational information to diagnose availability without exposing those values.
- Keep the current escaped rendering, validated inputs, safe Maps URLs, readable error states, and licensed-photo attributions.
- Update About, Privacy, README, and presentation guidance to distinguish the hosted anonymous collection from local/native storage. Do not continue claiming that the hosted site stores everything solely on the visitor's own device.
- Do not add analytics, advertising, GPS, automatic native-app uploads, or external AI/data-provider integrations as part of hosting.

## 8. Acceptance criteria

This increment is complete only when the following outcomes have evidence:

1. A real public HTTPS URL loads the home page and planning form from a separate browser context and an external request, independently of the local preview.
2. A visitor completes preferences, explained recommendations, itinerary generation, save, list, and reopen using that URL.
3. Two independent visitor contexts cannot access one another's saved data, including direct-URL guesses and identical-plan save attempts.
4. The same visitor's saved snapshot and access survive a controlled hosted process restart and redeployment without changing the stored snapshot contents.
5. The chosen plan's idle/restart/persistence behavior is documented accurately. An idle-sleep service is never described as continuously running.
6. A missing secret, missing/unwritable durable store, invalid visitor identifier, tampered form, and unavailable database produce the specified safe behavior.
7. Light, Dark, device setting, supported currencies, photos/credits, and external Maps work on the public desktop/mobile flow. Appearance changes do not alter the trip.
8. Existing local/native and historical snapshot regressions still pass. No preselected passing-test count replaces actual results.
9. All application changes follow the required sequence: approved specification, implementation/test plan, tests defined and their expected failures validated, then implementation.
10. The final handoff records the deployed URL, actual host/server/storage configuration, verification results, operating costs approved by the user, recovery instructions, and remaining limits. It never claims actual laptop-off or physical-phone testing unless performed.

## 9. Approval boundary and next stage

Approval accepts the public-hosting and anonymous-collection behavior described here. It does not approve a particular paid plan, create an account, accept new third-party terms, purchase a domain, upload local trips, or publish unfinished code. After approval, the next stage is the implementation and test plan. Hosting-account access and any required provider/cost decision are resolved before the corresponding provisioning action, after the proposal is concrete and reviewable.

This file is a proposed extension to the completed local class-project release, not a claim that a public deployment already exists. No fixed weekly schedule is introduced.

## 10. Verified technical references

- [Flask deployment guidance](https://flask.palletsprojects.com/en/stable/deploying/) requires an appropriate production server/platform instead of its development server for deployment.
- [Render's free-service limitations](https://render.com/docs/free) illustrate why a free hosted URL alone does not establish continuous availability or durable SQLite storage. As checked on 2 November 2026, its free web services sleep after inactivity, cannot attach persistent disks, and its free Postgres databases expire. This is an example, not a selected provider.
- [Render persistent disks](https://render.com/docs/disks) document preservation across restarts/redeployments for supported paid services and the importance of writing inside the mounted path.

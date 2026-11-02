# TripPlanner privacy and offline behavior

TripPlanner is a class-project planner with independent local/native applications and an explicitly configured hosted website mode. Public deployment is pending; see the [hosting guide](docs/public-hosting.md) for its current status. It has no accounts, advertising, analytics, GPS collection, booking, payment, or automatic upload from the downloadable apps. It uses your chosen city, allowance, interests, pace, and optional family-friendly preference to rank bundled ideas.

## Hosted website mode

The selected public-demo design uses Render Free for the website and Neon Free for its database. Both have sleep/usage limits and do not promise continuous availability. Saved trips go to Neon rather than a temporary file on the sleeping web service. Public deployment acceptance remains pending; see the [free-demo guide](docs/free-demo-hosting.md).

When using a deployed public website, requests and submitted preferences go to that server over HTTPS. Saved snapshots, names, creation times and a digest of an anonymous collection identifier are stored on its durable database. Server operators can access data for maintenance and backups. The host receives ordinary connection information, including IP addresses, and may maintain its own operational logs under its policies. Application logging deliberately excludes submitted trip contents, query strings, cookies and secrets; this does not promise control over the host's separate logs.

A protected, signed, HTTP-only browser cookie separates visitor collections. It expires after 365 days without a valid page visit and is renewed on visits. It is not an account: clearing cookies, private browsing, another browser/profile/device, expiry or deliberate server-secret rotation can lose access. There is no account recovery or cross-device sync. People sharing a browser profile share access. Unreachable stored rows and private backups are not automatically deleted when cookies expire; no automated cleanup/retention policy is implemented in this increment. Avoid storing sensitive personal data.

The draft uses a separate signed session cookie. Signed cookies are not encrypted. Appearance stays in browser storage. Shared caches must not store personal pages. A hosted website requires internet, including its images and saves. Native Windows and Android collections are not uploaded or synchronized with it.

## Local and native saved data

The local preview uses a signed browser-session draft and a local SQLite collection. A signed cookie is not encrypted. Browsers using that same local web server/database share the saved collection; there are no private accounts. This differs from the hosted cookie-separated collection described above.

The Windows app stores its settings, signing secret, browser profile, and saved collection under the current Windows account's local application-data folder, normally `%LOCALAPPDATA%\TripPlanner`. An explicit `--data-dir` option selects another profile. The executable folder contains resources, not the collection. The collection is protected by the OS account's file permissions, not application-level encryption. Other people using that same account/profile can see it.

Closing/reopening the Windows app preserves saved trips and appearance. Unsaved drafts may depend on the browser session and are not permanent records. Replacing the portable app folder does not intentionally remove the separate profile. Deleting/clearing the profile, using another profile, changing Windows accounts, or losing the device can remove access to its collection. Back up your own profile before manual repairs; the app does not silently reset corrupt data.

## Internet and outside services

Core recommendations, scheduling, bundled photographs, photo-credit metadata, and local saves do not need an online travel service. Google Maps, venue sources, photographer profiles, and license-deed pages open externally and need internet. Their providers receive the ordinary request and any information in the link, such as the public venue name/address. Clicking those links is optional; external providers have their own policies.

The Windows app runs its own authenticated service on the device's loopback interface, on an allocated port. Its app window receives a fresh launch cookie. It is not a public internet service and must not be exposed as one. Local-first storage is not a promise of protection against malicious software already running in your Windows account.

All costs/time slots are illustrative; the app does not verify live prices, bookings, opening hours, routing, accessibility, dietary requirements, or comprehensive suitability. Supported coverage is the six bundled cities.

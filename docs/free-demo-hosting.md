# TripPlanner free public demo

**Current review, 6 November 2026:** [TripPlanner is live over HTTPS](https://tripplanner-mayowa.onrender.com/) using Render **Free** and Neon **Free** PostgreSQL in Frankfurt, selected by the user on 2 November. Source is on [GitHub](https://github.com/adeniyimayowa003-byte/TripPlanner). Public planning, saving/reopening, photos, Light/Dark and a separate visitor's 404 were verified. Hosted restart/redeploy persistence remains pending; see [submission status](submission-status-2026-11-06.md). No paid plan/disk or extra Auth/Functions/AI Gateway service was selected.

## Why two services

Render runs the Python website and supplies HTTPS. Its free website sleeps after 15 idle minutes and usually takes about a minute to wake. Its filesystem is temporary, so putting SQLite there would lose saved trips. Neon holds the PostgreSQL data separately; normal website sleep/restart/redeploy does not erase committed saves. Neon compute also scales to zero when idle. Neither free tier promises continuous availability.

Keep both accounts/projects on Free and do not add payment methods, disks, paid trials or automatic upgrades. Render's free service has 750 instance hours/month per workspace plus bandwidth/build limits; without payment information, reaching certain limits can suspend services/builds. Neon currently lists 100 CU-hours and 1 GB per project, scale-to-zero after five minutes, and limited transfer/history. Check actual current dashboard allowances. Free quota exhaustion, cold starts and provider issues can interrupt a demonstration. Do not send fake traffic to evade sleep. Render's own free Postgres expires after 30 days and is not this design's database.

## Reviewed configuration

Use [the free example](../hosting/render-free.yaml.example), not the optional historical paid-disk example:

| Render setting | Value |
| --- | --- |
| Instance | Free, one instance, Frankfurt |
| Python | 3.14.7 |
| Build | `pip install -r requirements-hosted.lock.txt` |
| Start | `python serve_hosted.py` |
| Health | `/healthz` |
| Deploys | Manual until external acceptance |
| Disk | None |
| `TRIPPLANNER_STORAGE_BACKEND` | `postgres` |
| `TRIPPLANNER_DATABASE_URL` | Private Neon connection URL, **`sslmode=verify-full`**, optional `channel_binding=require` |
| `TRIPPLANNER_PUBLIC_HOST` | Actual Render hostname without scheme, port or path |
| `TRIPPLANNER_SECRET_KEY` | Private independently generated 64-character hexadecimal secret, retained across redeploys |
| `PORT` | Let Render supply it |

Neon normally supplies a URL with `sslmode=require`. Change **that query value** to `verify-full` while preserving the actual username/password/host/database and optional channel binding. The app verifies the database certificate/hostname using the bundled public Certifi CA trust store. Never post the raw URL in chat, commit it, paste it in screenshots, or put it in a public command-line argument. Enter it directly into Render's private environment configuration. Do not set `TRIPPLANNER_STORAGE_DIR` in this remote mode. Invalid/missing remote settings fail before connecting, and remote failures never fall back to local SQLite/memory.

The DB creates a fresh version-marked `tripplanner_hosted_v1` namespace atomically. Existing incompatible storage is refused, not reset. No local/native/QA collections are uploaded. SQL owner conditions isolate each browser collection; snapshots and fingerprints keep their reviewed v1/v2 meanings. The protected browser cookie renews for 365 days and keeps access after normal server restarts. Clearing cookies, changing browser/device/profile or expiry can lose access; there is no account recovery or sync. Shared profiles share access. See [Privacy](../PRIVACY.md).

## Source publication

Publish reviewed code and licensed public assets only. Run the tests and `python release_checks.py`, inspect the staged file list, and exclude `.tmp`, environments, downloaded SDK/database tools, build/release bundles, secret configuration, databases/journals and private profiles/backups. GitHub holds source; it does not run this Python backend. The existing source checkout has no Git repository initialized at its root; publication should use an isolated reviewed staging repository to preserve the local workspace.

The recorded source suite passed **1,688 tests**, including all 32 PostgreSQL/free-demo cases, with real PostgreSQL 18.6 and actual `pg_dump`/`pg_restore` against disposable databases. [Actual GitHub CI](https://github.com/adeniyimayowa003-byte/TripPlanner/actions/runs/41381620794) passed for Windows, Linux and a dedicated PostgreSQL 18 job. The ordinary Windows/Linux jobs skip DB-dependent cases without a test DSN; the dedicated PostgreSQL job supplies the real DB and matching client tools. The initial CI configuration error was corrected by moving the service-container context to step-level environment settings before the successful run.

## Private backup and recovery

Free hosting is not a backup service. Keep private independent database backups and the signing secret outside the live services, and verify recoverability. On a trusted machine with compatible PostgreSQL client tools on PATH, set the private URL in the process environment without recording it, then run:

```text
python -m hosting.postgres_backup path-to-a-new-private-archive.dump
```

The tool passes credentials through a private child environment, not process arguments, and uses `pg_dump` custom format for the hosted namespace. It refuses overwriting a file and masks failures. A successful archive header is a format check; the recorded disposable restore is the actual recovery check. A failed backup can leave an incomplete file: do not treat it as valid. Protect backups with OS permissions/encrypted storage and secure transfer. Never commit them or rely only on the same service's storage/history. Free Render does not supply the paid-service shell; this operator command runs on a trusted machine, not a public web endpoint.

Restore only after stopping writes, preserving current data, validating the backup and obtaining approval for replacing actual data. Use `pg_restore --exit-on-error --no-owner --no-acl --dbname NEW_DISPOSABLE_DATABASE archive.dump` with private libpq environment credentials to rehearse recovery first. This phase restores only fresh disposable test databases, never the user's existing local/native/cloud collection. Account creation, provider snapshots and regular backup scheduling are not substituted for an independently verified backup.

## Before sharing the real link

Check actual public HTTPS from another context/external request, full planning/save/reopen, two-browser isolation and identical duplicate-save behavior, provider restart/redeploy with the same secret and byte-identical stored rows, and mobile/desktop appearance/photos/Maps. Stop the local preview and verify the public URL still responds. Document cold-start delay honestly and retain local native presentation fallbacks. Do not claim real laptop-off, phone, live TLS or cloud-restart checks from local pytest evidence.

The delivered PowerPoint/Word/Windows/Android files remain the earlier classroom checkpoint. Add a verified real website URL to presentation guidance only after deployment succeeds.

Official references checked 2 November 2026: [Render Free](https://render.com/docs/free), [Neon pricing](https://neon.com/pricing), [Neon plans](https://neon.com/docs/introduction/plans), [Render with Neon](https://neon.com/docs/guides/render), [Psycopg](https://pypi.org/project/psycopg/), [Certifi](https://pypi.org/project/certifi/).

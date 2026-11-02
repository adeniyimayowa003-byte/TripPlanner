# Public TripPlanner website

**Superseded proposal:** The user chose a **free demo** after this paid-disk proposal was prepared. Use the [current free deployment guide](free-demo-hosting.md) and [approved amendment](../specs/phase-09-free-demo.md). The paid service/disk below is historical reference only and is not authorized. Accounts are now ready; public deployment is still being prepared.

**Status, 2 November 2026:** Public availability spec approved; production mode implemented with 60 passing hosting checks, including real local WSGI requests. See the [verification report](phase-09-implementation.md). Provider/cost/account decision and external acceptance are pending. **There is no deployed public URL yet.** Local Windows/Android downloads and their historical release artifacts remain independent.

## Why the current address stops

`127.0.0.1` means the computer opening the address. A browser on another person's computer would look for a server on their own computer. The local preview also stops when its Python process or the laptop stops. A hosted service runs the Python backend on the provider's machine, supplies HTTPS and restarts the process. HTML/image files alone cannot run the existing Flask planner.

## Proposed service and cost decision

The proposed configuration is Render, a free Hobby workspace, a **paid Starter web service**, Frankfurt region, **one instance**, and a **1 GB persistent disk** mounted at `/var/data`. Use its included `onrender.com` hostname; no purchased domain is required. Estimated base cost is **US$7/month compute + US$0.25/month disk**, before taxes, bandwidth/build overages or pricing changes. This is an estimate, not a hard account spending cap. Review the actual total, account limits and payment requirements before creating a resource. No paid service is authorized until the user separately approves it.

An account and linked reviewed Git source repository are needed for this proposed deployment route. The user controls sign-in, payment and acceptance of provider terms. No credentials belong in chat, screenshots or Git. No external repository has been created or uploaded by this phase.

Render's free web service sleeps after inactivity and cannot attach a persistent disk. A free deployment must use a separately agreed storage/availability design; simply selecting Free on this SQLite example loses the required durability. The proposed paid service avoids deliberate idle sleeping but has provider/maintenance outages. Disk-backed redeployments have a short interruption. It is not a zero-downtime guarantee or a design for large-scale concurrent traffic.

## Concrete deployment settings

The [inert example](../hosting/render.yaml.example) is reviewable configuration, not an active deployment or billing operation. After approval, choose the service name/region and supply:

| Setting | Value |
| --- | --- |
| Runtime | Python 3.14.7 |
| Build command | `pip install -r requirements-hosted.lock.txt` |
| Start command | `python serve_hosted.py` |
| Instance count | 1; no autoscaling |
| Health check | `/healthz` |
| Automatic deployment | Off until acceptance |
| Persistent disk | 1 GB at `/var/data` |
| `TRIPPLANNER_STORAGE_DIR` | `/var/data` |
| `TRIPPLANNER_PUBLIC_HOST` | The actual hostname Render assigns, without scheme/path/port |
| `TRIPPLANNER_SECRET_KEY` | Independently generated 64-character hexadecimal secret; stable across redeploys |
| `PORT` | Let Render supply this; the runner validates it |

Create the private secret yourself in a private terminal with `python -c "import secrets; print(secrets.token_hex(32))"`, then place it directly in the host's secret environment editor and retain a private recovery copy. Do not paste it into a source file, public shell recording or chat. `generateValue: true` is intentionally not used in the example: Render generates base64 secrets, whereas this configuration requires hexadecimal. The example prompts for the secret/actual hostname using `sync: false`. Confirm the hostname in the dashboard and update it before accepting the service as ready; a missing/wrong host setting fails closed.

The durable mount must exist at runtime and be outside the source checkout. The host creates a **fresh** `hosted-trips.sqlite3` there. Never upload an existing local, native, QA or presentation database. An existing local/empty/incompatible database is rejected rather than migrated or erased. Do not mount storage over the code, switch to an ephemeral path, remove the disk, scale replicas around a shared SQLite file, or rotate the signing secret as an ordinary redeploy step.

Waitress runs one production process with four threads, bounded request sizes and no access logging. It does not enable Flask's debugger/reloader or trust arbitrary forwarded host/IP headers. The provider terminates HTTPS; internal backend requests may be HTTP. Only the configured public hostname is accepted. `Secure` cookies remain mandatory. Never turn them off to make a hosted production session work over plain HTTP.

## What happens to visitor data

The public collection is separated per browser by a server-signed, unpredictable cookie. The database stores a digest of its random identifier beside the unchanged saved snapshot. Ownership is checked for every list, detail and duplicate-save query. A query/form `owner` value cannot change this. Another visitor's ID returns the same 404 as a missing ID.

The cookie lasts **365 days without a valid page visit** and is renewed on visits. Clearing cookies, private browsing, moving devices/profiles, expiration or changing the server secret can lose access. There is no account recovery or cross-device synchronization. Shared browser profiles share access. Unreachable database rows are not automatically removed. Operators can access hosted data for maintenance/backups. See [Privacy](../PRIVACY.md). Native apps do not upload or share their local collections.

## Deployment inputs and verification

Run `python -m pytest -q` and `python release_checks.py` before any upload. Review exactly what will be committed. Source/public licensed assets are allowed; `.tmp`, `.venv*`, `dist`, `build`, `instance`, private profiles, databases/journals, backups, SDKs, secrets and signing keys are excluded. The historical demo.2 ZIP/APK/presentation files are not web deployment inputs. Never use a broad upload of the desktop folder.

After creating the approved service:

1. Verify the actual public HTTPS URL and `/healthz` externally; check health/restart settings in the provider dashboard.
2. In two separate browser profiles, generate and save the same trip/title. Confirm separate records, stable repeated saves within one profile, and 404 for the other profile's direct URL. Do not copy either profile's identity cookie to the other.
3. Complete the six-city flow and check the correct currencies, licensed images, Light/Dark/System and external Maps at mobile/desktop sizes. Do not claim a real phone was tested if only desktop emulation was used.
4. Restart/redeploy with the **same secret and durable disk**. Reopen each saved trip in its original profile and compare stored snapshot/fingerprint bytes before/after. Check logs for absence of trip contents, cookies and secret values.
5. Stop the laptop's local preview and verify the public URL remains reachable. A different external request confirms independence; physically powering down the laptop is a separate claim that must have its own evidence.
6. Record the real URL, accepted cost, exact configuration, private-backup procedure and observed limits. Only then mark public acceptance complete or update the classroom materials to claim public availability.

Local pytest clients simulate HTTPS for cookie checks, and the production runner test makes real loopback HTTP requests. Neither proves public TLS, live-provider restart, real durable cloud storage or laptop-off access. Those checks remain deployment acceptance work.

## Backup, restart and recovery

Use SQLite's online backup API while the database runs. In the approved provider's private shell:

```text
python -m hosting.backup /var/data/hosted-trips.sqlite3 /var/data/backup-YYYYMMDD-HHMM.sqlite3
```

Choose a new destination each time. The tool refuses to overwrite it, validates the hosted schema and SQLite integrity, and prints no trip content. A failed backup may leave an incomplete destination: never treat it as valid or overwrite it; investigate and use a new destination. The POSIX file is created with mode 0600; protect its containing directory and Windows equivalents according to the host. A backup contains private visitor data.

Back up regularly and before changes; keep at least two validated copies outside the service using an approved encrypted/private transfer and storage method. A copy on the same disk is only a first step, not disaster recovery. Keep the signing secret privately and separately; a database alone cannot recreate a lost anonymous identity cookie. There is no implemented automated backup scheduler or guaranteed retention service. The operator must arrange and verify it before relying on a live service.

Recovery: stop writes, preserve the current DB, verify backup identity/integrity in a separate disposable directory, test recovery with a retained test cookie, then obtain approval before replacing actual user data. Never run a destructive restore against the developer's laptop/native data as deployment maintenance. Do not rely on filesystem-level disk snapshots as a database-consistency guarantee.

For a down site, inspect provider state/billing, health result, configured hostname, stable secret presence and disk mount. `/healthz` returns only `ok` or `unavailable`; a lost file, lock, incompatible schema or unavailable write path returns 503. It never initializes a replacement collection. Fix the storage/configuration cause; do not delete/reset the database or rotate secrets to silence an error.

## Official references checked 2 November 2026

[Flask production deployment](https://flask.palletsprojects.com/en/stable/deploying/) · [Waitress](https://flask.palletsprojects.com/en/stable/deploying/waitress/) · [Waitress configuration](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html) · [Render pricing](https://render.com/pricing) · [Starter compute reference](https://render.com/articles/render-vs-railway) · [Persistent disks and deploy interruptions](https://render.com/docs/disks) · [Free limits](https://render.com/docs/free) · [Blueprint configuration](https://render.com/docs/blueprint-spec) · [Python versions](https://render.com/docs/python-version).

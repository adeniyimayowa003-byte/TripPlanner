# Free-demo amendment — test-first checkpoint

The user selected free hosting with sleep/other free-plan limits on 2 November 2026, then confirmed they created their own free Render and Neon accounts. The [amendment](../specs/phase-09-free-demo.md) preserves durable saves/privacy; its [plan](../plans/phase-09-free-demo-plan.md) was written before new backend code.

Before implementing any PostgreSQL application module, **32 new pytest cases were collected and all 32 failed for expected absent behavior**, in 2.94 seconds, with no setup/collection errors or skips (`.tmp/phase09-free-red.xml`). The missing components are `hosted_postgres`, the PostgreSQL backup tool and the free deployment example. The preceding complete source baseline was **1,656 passing cases**.

The run used a real portable PostgreSQL **18.6** test cluster on an allocated `127.0.0.1` port and separate randomly named databases created/removed by fixtures. Official EDB binaries were downloaded from the PostgreSQL project's linked distribution page into ignored `.tmp`; no Windows service was installed. `TRIPPLANNER_TEST_POSTGRES_DSN` is restricted to a named loopback test admin DB; tests never consult production credentials. The test binary path is separately supplied for real `pg_dump`/`pg_restore` verification. No cloud resources or existing local/native databases were used.

The first launch was delayed by an automatic permission-review timeout; a single permitted retry ran normally. This was not an application or PostgreSQL failure. The first archive download also resumed after a network read timeout, and extracted tools reported PostgreSQL 18.6. Neither condition was treated as successful verification before it actually completed.

Cases cover configuration/TLS and no fallback, actual SQL isolation/concurrency/rollback/legacy snapshots, failed health/missing schema, private errors, two Flask browser profiles and restart, free-deployment/notice behavior, logical backup, no overwrite/no credentials in arguments, and a disposable restore. The restore command was checked to explicitly select its fresh destination DB before implementation; merely generating SQL output would not prove recovery.

Implementation can now begin. Live-provider HTTPS/restart/sleep limits and account integration remain external acceptance work.

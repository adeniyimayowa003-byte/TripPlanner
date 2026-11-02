"""Private logical PostgreSQL backup; never perform an automatic restore."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

import certifi
from psycopg.conninfo import conninfo_to_dict

from saved_trips import StorageUnavailableError


def libpq_environment(database):
    settings = conninfo_to_dict(database)
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("PG", "TRIPPLANNER_"))}
    names = {"host": "PGHOST", "port": "PGPORT", "dbname": "PGDATABASE", "user": "PGUSER",
             "password": "PGPASSWORD", "sslmode": "PGSSLMODE", "channel_binding": "PGCHANNELBINDING"}
    for source, target in names.items():
        if source in settings:
            environment[target] = settings[source]
    environment["PGCONNECT_TIMEOUT"] = "10"
    if settings.get("sslmode") == "verify-full":
        environment["PGSSLROOTCERT"] = certifi.where()
    return environment


def backup_store(database, destination, *, pg_dump_path=None):
    command = str(pg_dump_path) if pg_dump_path else shutil.which("pg_dump")
    if not command:
        raise StorageUnavailableError("PostgreSQL backup tools are unavailable.")
    destination = Path(destination)
    # Exclusive private output. A failed backup remains incomplete; never reuse.
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        try:
            result = subprocess.run(
                [command, "--format=custom", "--schema=tripplanner_hosted_v1", "--no-owner", "--no-acl"],
                env=libpq_environment(database), stdout=output, stderr=subprocess.PIPE, timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError, ValueError):
            raise StorageUnavailableError("Private database backup failed; no valid backup was reported.") from None
        if result.returncode != 0:
            raise StorageUnavailableError("Private database backup failed; no valid backup was reported.")
    if not destination.read_bytes()[:5] == b"PGDMP":
        raise StorageUnavailableError("Private database backup failed validation.")
    return destination


def main():
    from hosted_postgres import validate_database_url
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    options = parser.parse_args()
    database = validate_database_url(os.environ.get("TRIPPLANNER_DATABASE_URL", ""))
    backup_store(database, options.destination)
    print("Private PostgreSQL archive created. Verify recovery in a disposable database and store it securely.")


if __name__ == "__main__":
    main()

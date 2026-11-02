"""Create CI-only wrappers for the PostgreSQL service container's client tools."""
import os
from pathlib import Path
import re
import sys


def main():
    container = os.environ["POSTGRES_CONTAINER_ID"]
    if re.fullmatch(r"[a-f0-9]{12,64}", container) is None:
        raise ValueError("Expected the CI PostgreSQL service container ID.")
    destination = Path(sys.argv[1]).resolve()
    allowed = Path(__file__).resolve().parents[1] / ".tmp"
    if not destination.is_relative_to(allowed) or destination.exists():
        raise ValueError("Choose a new CI wrapper directory under .tmp.")
    destination.mkdir(parents=True)
    source = '''#!/usr/bin/env python3
import os, subprocess, sys
from pathlib import Path
tool = Path(sys.argv[0]).name
command = ["docker", "exec", "-i"]
for key in os.environ:
    if key.startswith("PG"):
        command += ["--env", key]
command += [os.environ["POSTGRES_CONTAINER_ID"], tool]
arguments = sys.argv[1:]
if tool == "pg_restore":
    # Archive lives on the runner; stream it to the service's restore client.
    with open(arguments[-1], "rb") as archive:
        result = subprocess.run(command + arguments[:-1], stdin=archive)
else:
    result = subprocess.run(command + arguments)
raise SystemExit(result.returncode)
'''
    for name in ("pg_dump", "pg_restore"):
        target = destination / name
        target.write_text(source, encoding="utf-8")
        target.chmod(0o755)


if __name__ == "__main__":
    main()

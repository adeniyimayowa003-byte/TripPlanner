"""Private SQLite online backup, with no overwrite or destructive restore."""
import argparse
from contextlib import closing
import os
from pathlib import Path
import sqlite3

from hosted_saved_trips import _validate
from saved_trips import StorageUnavailableError


def backup_store(source, destination):
    destination = Path(destination)
    try:
        with closing(sqlite3.connect(Path(source).resolve().as_uri() + "?mode=ro", uri=True)) as original:
            _validate(original)
            # Exclusively reserve a private destination; do not overwrite a backup.
            descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
            with closing(sqlite3.connect(destination, isolation_level=None)) as copied:
                original.backup(copied)
                _validate(copied)
                if copied.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise StorageUnavailableError("Backup validation failed.")
    except sqlite3.Error as error:
        raise StorageUnavailableError("Backup validation failed.") from error
    # No trip contents, owner IDs or secret values are printed.
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    options = parser.parse_args()
    backup_store(options.source, options.destination)
    print("Private backup created and validated. Store it securely outside source control.")


if __name__ == "__main__":
    main()

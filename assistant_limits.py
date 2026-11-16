"""Explicit, separate development quota storage; never an automatic fallback."""
from contextlib import contextmanager
from pathlib import Path
import os
import re
import secrets
import sqlite3
import time
import math

_MARKER=0x54504151
_SQL='CREATE TABLE attempts (ticket TEXT PRIMARY KEY NOT NULL, account_id TEXT NOT NULL, started_at INTEGER NOT NULL, active INTEGER NOT NULL CHECK(active IN (0,1)))'
class LimitsUnavailable(RuntimeError):pass
class QuotaDenied(RuntimeError):
    def __init__(self,message,retry_after=None):
        super().__init__(message)
        self.retry_after=retry_after


def _path(database):
    path=Path(database)
    if not path.is_absolute():raise ValueError('Quota storage requires an explicit absolute path.')
    if path.is_symlink():raise LimitsUnavailable('AI limits unavailable; using FAQs.')
    return path


@contextmanager
def _connection(database,*,new=False):
    connection=None
    try:
        path=_path(database)
        connection=sqlite3.connect(path.as_uri()+'?mode=rw',uri=True,timeout=2,isolation_level=None)
        connection.execute('BEGIN IMMEDIATE')
        if not new:
            tables=connection.execute("SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
            if (connection.execute('PRAGMA application_id').fetchone()[0]!=_MARKER
                or connection.execute('PRAGMA user_version').fetchone()[0]!=1
                or tables!=[('attempts',_SQL)]):raise LimitsUnavailable('AI limits unavailable; using FAQs.')
        yield connection
    except (OSError,sqlite3.Error):raise LimitsUnavailable('AI limits unavailable; using FAQs.') from None
    finally:
        if connection is not None:
            connection.rollback();connection.close()


def create_limits(database):
    path=_path(database)
    try:
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    except OSError:raise LimitsUnavailable('AI limits unavailable; using FAQs.') from None
    with _connection(path,new=True) as connection:
        connection.execute(_SQL)
        connection.execute(f'PRAGMA application_id={_MARKER}')
        connection.execute('PRAGMA user_version=1')
        connection.commit()

class Limits:
    def __init__(self,database,*,clock=None):
        self.database=_path(database)
        self.clock=clock or time.time
        with _connection(self.database):pass
    def reserve(self,account_id):
        if not isinstance(account_id,str) or re.fullmatch(r'[0-9a-f]{64}',account_id) is None:
            raise ValueError('A verified account identifier is required.')
        value=self.clock()
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:
            raise LimitsUnavailable('AI limits unavailable; using FAQs.')
        now=int(value);day=(now//86400)*86400
        with _connection(self.database) as connection:
            latest=connection.execute('SELECT max(started_at) FROM attempts').fetchone()[0]
            if latest is not None and latest>now:raise LimitsUnavailable('AI limits unavailable; using FAQs.')
            connection.execute('DELETE FROM attempts WHERE active=0 AND started_at<?',(min(day,now-60),))
            active=connection.execute('SELECT account_id FROM attempts WHERE active=1').fetchall()
            if len(active)>=2 or (account_id,) in active:
                raise QuotaDenied('AI is busy. Use FAQs while the running request finishes.')
            minute=connection.execute('SELECT count(*),min(started_at) FROM attempts WHERE account_id=? AND started_at>?',
                                      (account_id,now-60)).fetchone()
            if minute[0]>=5:raise QuotaDenied('AI minute limit reached. Use FAQs or try later.',minute[1]+60-now)
            total=connection.execute('SELECT count(*) FROM attempts WHERE started_at>=?',(day,)).fetchone()[0]
            own=connection.execute('SELECT count(*) FROM attempts WHERE started_at>=? AND account_id=?',(day,account_id)).fetchone()[0]
            if total>=100 or own>=20:
                raise QuotaDenied('AI daily limit reached. It resets at 00:00 UTC; FAQs still work.',day+86400-now)
            ticket=secrets.token_hex(32)
            connection.execute('INSERT INTO attempts VALUES(?,?,?,1)',(ticket,account_id,now))
            connection.commit()
        return ticket

    def finish(self,ticket):
        if not isinstance(ticket,str) or re.fullmatch(r'[0-9a-f]{64}',ticket) is None:return
        with _connection(self.database) as connection:
            connection.execute('UPDATE attempts SET active=0 WHERE ticket=?',(ticket,))
            connection.commit()

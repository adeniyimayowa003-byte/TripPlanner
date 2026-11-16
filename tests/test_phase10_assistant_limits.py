"""Actual durable admission rules; no provider and no production database."""
import importlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


def api():return importlib.import_module('assistant_limits')


@pytest.fixture
def state(tmp_path):
    module=api(); clock=[100000]
    path=tmp_path/'assistant-limits.sqlite3'
    module.create_limits(path)
    return module,clock,module.Limits(path,clock=lambda:clock[0])


def test_create_only_and_no_guest_database_overwrite(tmp_path):
    module=api(); path=tmp_path/'limits.sqlite3'
    module.create_limits(path)
    assert path.is_file()
    before=path.read_bytes()
    with pytest.raises(module.LimitsUnavailable):module.create_limits(path)
    assert path.read_bytes()==before
    import hosted_saved_trips
    guest=tmp_path/'guest.sqlite3';hosted_saved_trips.initialize_store(guest)
    before=guest.read_bytes()
    with pytest.raises(module.LimitsUnavailable):module.Limits(guest)
    assert guest.read_bytes()==before


def test_missing_store_never_recreated(tmp_path):
    module=api(); path=tmp_path/'missing.sqlite3'
    with pytest.raises(module.LimitsUnavailable):module.Limits(path)
    assert not path.exists()


def test_per_account_sliding_minute_and_restart(state):
    module,clock,store=state
    for _ in range(5):store.finish(store.reserve('a'*64))
    second=module.Limits(store.database,clock=lambda:clock[0])
    with pytest.raises(module.QuotaDenied):second.reserve('a'*64)
    clock[0]+=59
    with pytest.raises(module.QuotaDenied):second.reserve('a'*64)
    clock[0]+=1
    second.finish(second.reserve('a'*64))


def test_account_daily_twenty_and_utc_reset(state):
    module,clock,store=state
    for _ in range(20):
        store.finish(store.reserve('a'*64));clock[0]+=61
    with pytest.raises(module.QuotaDenied):store.reserve('a'*64)
    clock[0]=((clock[0]//86400)+1)*86400
    store.finish(store.reserve('a'*64))


def test_global_daily_hundred_cannot_be_bypassed_with_new_accounts(state):
    module,clock,store=state
    for number in range(100):store.finish(store.reserve(f'{number:064x}'))
    with pytest.raises(module.QuotaDenied):store.reserve('f'*64)
    restarted=module.Limits(store.database,clock=lambda:clock[0])
    with pytest.raises(module.QuotaDenied):restarted.reserve('f'*64)


def test_concurrency_and_release_are_shared_and_count_attempts(state):
    module,clock,store=state
    one=store.reserve('a'*64)
    with pytest.raises(module.QuotaDenied):store.reserve('a'*64)
    second=module.Limits(store.database,clock=lambda:clock[0])
    two=second.reserve('b'*64)
    with pytest.raises(module.QuotaDenied):second.reserve('c'*64)
    store.finish(one);store.finish(one)
    second.finish(second.reserve('c'*64));second.finish(two)
    # Failure/success does not refund attempted calls.
    for _ in range(4):store.finish(store.reserve('a'*64))
    with pytest.raises(module.QuotaDenied):store.reserve('a'*64)


def test_abandoned_running_lease_fails_closed_after_restart(state):
    module,clock,store=state
    one=store.reserve('a'*64);two=store.reserve('b'*64)
    clock[0]+=86400
    restarted=module.Limits(store.database,clock=lambda:clock[0])
    with pytest.raises(module.QuotaDenied):restarted.reserve('c'*64)
    restarted.finish(one);restarted.finish(two)
    restarted.finish(restarted.reserve('c'*64))


def test_atomic_admission_with_separate_connections(state):
    module,clock,store=state
    def attempt(number):
        try:return module.Limits(store.database,clock=lambda:clock[0]).reserve(f'{number:064x}')
        except module.QuotaDenied:return None
    with ThreadPoolExecutor(max_workers=3) as workers:results=list(workers.map(attempt,range(3)))
    assert sum(value is not None for value in results)==2


def test_clock_rollback_cannot_reopen_quota(state):
    module,clock,store=state
    store.finish(store.reserve('a'*64));clock[0]-=1
    with pytest.raises(module.LimitsUnavailable):store.reserve('a'*64)


@pytest.mark.parametrize('account',[None,'','a','x'*64,'a'*65])
def test_invalid_account_identifier_never_consumes_quota(state,account):
    _,_,store=state
    with pytest.raises(ValueError):store.reserve(account)

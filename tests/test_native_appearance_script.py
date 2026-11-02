"""Actual appearance script's native persistence adapter, test-first."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]


def run(**options):
    node=shutil.which('node')
    assert node
    result=subprocess.run([node,str(ROOT/'tests/native_appearance_harness.cjs'),str(ROOT/'static/js/appearance.js')],
                          input=json.dumps(options),encoding='utf-8',capture_output=True,timeout=5)
    assert result.returncode==0,result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize('mode',['light','dark','system'])
def test_native_server_preference_wins_without_reading_origin_storage(mode):
    result=run(native=mode)
    assert result['errors']==[] and result['mode']==mode and result['selected']==mode
    assert result['storage']==[] and result['network']==[]


def test_native_change_sends_only_enum_to_same_origin_with_csrf():
    result=run(native='light',change='dark')
    assert result['errors']==[] and result['mode']=='dark' and result['storage']==[]
    assert len(result['network'])==1
    request=result['network'][0]
    assert request['url']=='/_desktop/appearance' and request['method']=='POST'
    assert request['headers']['X-CSRF-Token']=='csrf-sentinel'
    assert json.loads(request['body'])=={'appearance':'dark'}


@pytest.mark.parametrize('failure',[{'reject':True},{'ok':False}])
def test_native_persistence_failure_keeps_page_choice_and_explains_failure(failure):
    result=run(native='light',change='dark',**failure)
    assert result['errors']==[] and result['mode']=='dark'
    assert 'could not remember' in result['status'].lower()


def test_invalid_native_selection_never_sends_a_request():
    result=run(native='dark',change='../private')
    assert result['errors']==[] and result['mode']=='dark' and result['network']==[]

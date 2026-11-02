"""Actual planner-JavaScript tests, defined before editing the production asset."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from phase8_helpers import CITY_PROFILES

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {p['name']: {'currency':p['currency'],'precision':0 if p['currency']=='JPY' else 2,
          'maximum_minor':100000000 if p['currency']=='EUR' else 1000000000 if p['currency']=='JPY' else 100000000000,
          'interests':['food','history'], 'paces':['relaxed']} for p in CITY_PROFILES}


def run(**options):
    node = shutil.which('node')
    assert node, 'Node is required for existing development script tests.'
    result = subprocess.run([node, str(ROOT/'tests/planner_harness.cjs'), str(ROOT/'static/js/plan.js')],
                            input=json.dumps({'config':CONFIG, **options}), encoding='utf-8', capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize('profile', CITY_PROFILES, ids=lambda p:p['currency'])
def test_native_currency_preview_uses_correct_precision_and_preserves_inputs(profile):
    result = run(destination=profile['name'],budget='100',days='3')
    assert result['errors'] == [] and result['budget'] == '100'
    assert result['preview'] == profile['currency'] + (' 33' if profile['currency']=='JPY' else ' 33.33')
    assert result['token'] == 'signed-context-sentinel'


@pytest.mark.parametrize('amount', ['300.00','300.5','3e2','0','1000000001'])
def test_invalid_jpy_preview_never_silently_rounds_or_accepts_bad_amount(amount):
    result = run(destination='Tokyo, Japan',budget=amount)
    assert result['errors'] == [] and result['preview'] == '—' and result['budget'] == amount


def test_currency_change_keeps_amount_but_blocks_preview_until_server_review():
    result = run(destination='Paris, France',budget='300',actions=[{'id':'destination','value':'Tokyo, Japan','event':'change'}, {'id':'budget','value':'450'}])
    assert result['errors'] == [] and result['budget'] == '450' and result['preview'] == '—'
    assert result['currency'] == 'JPY' and result['attrs']['step'] == '1'
    assert 'review' in result['notice'].lower() and result['token'] == 'signed-context-sentinel'


def test_first_city_selection_establishes_currency_without_claiming_conversion():
    result = run(budget='300',actions=[{'id':'destination','value':'Tokyo, Japan','event':'change'}])
    assert result['errors'] == [] and result['preview'] == 'JPY 100'


def test_destination_options_preserve_supported_choices_and_clear_unsupported_ones():
    config = {**CONFIG, 'Tokyo, Japan':{**CONFIG['Tokyo, Japan'],'interests':['history','nature'],'paces':['active']}}
    result = run(config=config,destination='Paris, France',interests=['food','history'],pace='relaxed',
                 actions=[{'id':'destination','value':'Tokyo, Japan','event':'change'}])
    assert result['errors'] == [] and result['pace'] == ''
    assert {x['value'] for x in result['interests']} == {'history','nature'}
    assert [x['value'] for x in result['interests'] if x['checked']] == ['history']


@pytest.mark.parametrize('missing', ['days','budget','destination-data'])
def test_missing_optional_page_nodes_do_not_throw(missing):
    assert run(missing=[missing])['errors'] == []

"""Actual image-error JavaScript checks, defined before the production script."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('images,fail,expected', [
    ([],[],[]),
    ([{'complete':False,'width':0}],[],[False]),
    ([{'complete':True,'width':960}],[],[False]),
    ([{'complete':True,'width':0}],[],[True]),
    ([{'complete':False,'width':0}], [0],[True]),
    ([{'complete':True,'width':960},{'complete':False,'width':0}],[1],[False,True]),
])
def test_real_script_handles_loaded_loading_cached_failure_and_isolated_errors(images,fail,expected):
    node = shutil.which('node')
    assert node, 'Node is needed for existing development script checks.'
    result = subprocess.run([node,str(ROOT/'tests/photo_harness.cjs'),str(ROOT/'static/js/images.js')],
                            input=json.dumps({'images':images,'fail':fail}),encoding='utf-8',capture_output=True,timeout=5)
    assert result.returncode == 0,result.stderr
    observed = json.loads(result.stdout)
    assert observed['errors'] == []
    assert [image['hidden'] for image in observed['images']] == expected
    assert all(image['src']=='/static/sentinel.jpg' for image in observed['images'])

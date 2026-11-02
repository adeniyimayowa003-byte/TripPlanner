"""Portable-bundle and GitHub hygiene gates, defined before their implementation."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from phase8_helpers import api_symbol

ROOT=Path(__file__).resolve().parents[1]


def test_bundle_allowlist_contains_resources_and_excludes_private_scratch():
    files=api_symbol('build_windows','application_files')(ROOT)
    paths={Path(p).as_posix() for p in files}
    assert {'app.py','windows_app.py','app_runtime.py','version.py','data/places.json','data/destinations.json',
            'data/images.json','PHOTO_CREDITS.md','PRIVACY.md','THIRD_PARTY_NOTICES.md'} <= paths
    assert any(p.startswith('templates/') for p in paths)
    assert len([p for p in paths if p.startswith('static/images/places/')])==18
    assert not any(any(part in {'.tmp','.git','.venv','tests','instance','__pycache__'} for part in Path(p).parts) for p in paths)
    assert not any(p.endswith(('.sqlite3','.db','.log','.pem','.key')) or '.env' in Path(p).name for p in paths)
    assert all((ROOT/p).is_file() for p in paths)


def test_staging_ignores_unknown_files_and_never_overwrites_destination(tmp_path):
    files=api_symbol('build_windows','application_files')(ROOT)
    source=tmp_path/'source'
    for relative in files:
        target=source/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,target)
    (source/'unreviewed-secret.txt').write_text('QA sentinel, never ship',encoding='utf-8')
    stage=api_symbol('build_windows','stage_application')
    output=tmp_path/'staged'
    stage(source,output)
    assert not (output/'unreviewed-secret.txt').exists()
    assert {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()} == {Path(p).as_posix() for p in files}
    with pytest.raises((ValueError,FileExistsError)): stage(source,output)


def test_missing_required_asset_fails_staging_before_partial_copy(tmp_path):
    stage=api_symbol('build_windows','stage_application')
    with pytest.raises((ValueError,FileNotFoundError)): stage(tmp_path/'missing',tmp_path/'output')
    assert not (tmp_path/'output').exists()


def test_github_ignore_rules_exclude_data_secrets_profiles_and_build_outputs(tmp_path):
    # Exercise Git itself, not a homemade interpretation of .gitignore patterns.
    git=shutil.which('git')
    assert git, 'Git is required for the GitHub preparation checks.'
    subprocess.run([git,'init','--quiet',str(tmp_path)],check=True,capture_output=True)
    shutil.copyfile(ROOT/'.gitignore',tmp_path/'.gitignore')
    paths=['.env','.env.local','instance/trips.sqlite3','copied.sqlite3','data-export.db','profile/settings.json',
           '.venv-windows/pyvenv.cfg','dist/TripPlanner.exe','build/log.txt','.tmp/qa.sqlite3','private-signing.key','__pycache__/app.pyc']
    result=subprocess.run([git,'check-ignore','--stdin','-z'],cwd=tmp_path,input='\0'.join(paths)+'\0',
                          encoding='utf-8',capture_output=True,check=False)
    assert result.returncode==0
    assert set(result.stdout.rstrip('\0').split('\0'))==set(paths)
    visible=subprocess.run([git,'check-ignore','.env.example','requirements.txt','static/images/places/paris-eiffel-tower.jpg'],
                           cwd=tmp_path,capture_output=True,check=False)
    assert visible.returncode==1


def test_github_source_audit_and_development_workflow_are_ready():
    findings=api_symbol('release_checks','check_source_tree')(ROOT)
    assert findings==[]
    workflow=(ROOT/'.github/workflows/tests.yml').read_text(encoding='utf-8')
    assert 'contents: read' in workflow and 'pytest' in workflow and 'setup-node' in workflow
    assert 'windows-latest' in workflow and 'ubuntu-latest' in workflow
    for path in ('.env.example','CONTRIBUTING.md','PRIVACY.md','THIRD_PARTY_NOTICES.md','requirements-dev.txt','requirements-windows.txt'):
        assert (ROOT/path).is_file()
    assert 'pytest' not in (ROOT/'requirements.txt').read_text(encoding='utf-8')

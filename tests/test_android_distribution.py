"""Android contracts defined before implementation; device gates stay explicit."""
from pathlib import Path
import importlib
import shutil
import pytest

ROOT = Path(__file__).resolve().parents[1]

def symbol(module, name):
    try:
        return getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError):
        pytest.fail(f"Android contract missing: {module}.{name}")

def test_android_manifest_ships_core_resources_without_desktop_or_private_data():
    files = symbol('build_android', 'application_files')(ROOT)
    assert {'app.py', 'app_runtime.py', 'android_runtime.py', 'data/places.json', 'data/images.json', 'PHOTO_CREDITS.md', 'LICENSE'} <= set(files)
    assert 'windows_app.py' not in files
    assert len([x for x in files if x.startswith('static/images/places/')]) == 18
    assert not any(set(Path(x).parts) & {'.tmp', '.git', '.venv', 'instance', 'tests'} for x in files)
    assert not any(x.endswith(('.sqlite3', '.db', '.key', '.jks', '.exe')) for x in files)

def test_android_stage_is_complete_and_ignores_unreviewed_files(tmp_path):
    files = symbol('build_android', 'application_files')(ROOT)
    source = tmp_path/'source'
    for relative in files:
        target = source/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, target)
    (source/'private.txt').write_text('QA only')
    output = tmp_path/'android-source'
    symbol('build_android', 'stage_application')(source, output)
    assert {x.relative_to(output).as_posix() for x in output.rglob('*') if x.is_file()} == set(files)
    with pytest.raises(FileExistsError):
        symbol('build_android', 'stage_application')(source, output)

def test_android_missing_file_fails_before_staging(tmp_path):
    output = tmp_path/'output'
    with pytest.raises((ValueError, FileNotFoundError)):
        symbol('build_android', 'stage_application')(tmp_path/'missing', output)
    assert not output.exists()

def test_android_runtime_reuses_service_and_persists_settings(tmp_path):
    module = symbol('android_runtime', 'AndroidRuntime')
    host = module()
    try:
        first = host.start(str(tmp_path))
        assert first.startswith('http://127.0.0.1:') and '/_desktop/open?token=' in first
        assert host.start(str(tmp_path)) == first
        host.runtime.settings.set_appearance('dark')
        with pytest.raises(ValueError):
            host.start(str(tmp_path/'another'))
        host.stop()
        assert host.runtime is None
        second = host.start(str(tmp_path))
        assert second != first
        assert host.runtime.settings.load()['appearance'] == 'dark'
    finally:
        host.stop()

def test_android_runtime_requires_absolute_private_folder():
    with pytest.raises(ValueError):
        symbol('android_runtime', 'AndroidRuntime')().start('relative-profile')

"""Stage the approved shared app into an isolated Android Gradle project."""
import argparse
from pathlib import Path
import shutil
from build_windows import MODULES, TEMPLATES
from photos import load_image_manifest

ROOT = Path(__file__).resolve().parent

def application_files(root):
    root = Path(root).resolve()
    manifest = load_image_manifest(root/'data/images.json')
    modules = [name for name in MODULES if name != 'windows_app'] + ['android_runtime']
    paths = [*(f'{name}.py' for name in modules), *(f'templates/{name}.html' for name in TEMPLATES),
             'data/places.json', 'data/destinations.json', 'data/images.json',
             'static/css/style.css', 'static/js/appearance.js', 'static/js/images.js', 'static/js/plan.js',
             'static/images/tripplanner.svg', 'LICENSE', 'PHOTO_CREDITS.md', 'PRIVACY.md',
             'CODE_LICENSE.md', 'THIRD_PARTY_NOTICES.md',
             *('static/'+asset['filename'] for asset in manifest['images'].values())]
    paths = sorted(set(paths))
    for relative in paths:
        path = root/relative
        if not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file():
            raise ValueError('Required Android resource missing or unsafe: '+relative)
    return paths

def stage_application(root, destination):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    files = application_files(root)
    if destination.exists():
        raise FileExistsError('Choose a new Android staging folder.')
    destination.mkdir(parents=True)
    for relative in files:
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/relative, target)
    return files

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    options = parser.parse_args()
    files = application_files(ROOT)
    if options.output.exists():
        raise FileExistsError('Choose a new Gradle project folder.')
    shutil.copytree(ROOT/'packaging/android', options.output)
    shutil.copyfile(ROOT/'requirements-android.lock.txt', options.output/'app/requirements.txt')
    stage_application(ROOT, options.output/'app/src/main/python')
    print(f'Staged {len(files)} shared app files. Build and device verification are separate gates.')

if __name__ == '__main__':
    main()

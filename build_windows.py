"""Allowlisted source staging and a reproducible one-folder Windows demo build."""
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib

from photos import load_image_manifest
from version import APP_VERSION

ROOT = Path(__file__).resolve().parent
MODULES = ("app", "app_runtime", "catalog", "csrf", "currencies", "currency_context", "drafts",
           "itinerary", "maps", "money", "photos", "preferences", "recommendations", "saved_trips",
           "snapshots", "version", "windows_app")
TEMPLATES = ("_itinerary_days", "_photos", "_place_location", "about", "base", "credits", "error", "index",
             "itinerary", "recommendations", "saved_error", "saved_trip", "saved_trips", "trip_preferences")
DOCUMENTS = ("LICENSE", "PHOTO_CREDITS.md", "CODE_LICENSE.md", "PRIVACY.md", "THIRD_PARTY_NOTICES.md", "packaging/windows/README.txt",
             "third_party/webview2/LICENSE.txt", "third_party/webview2/NOTICE.txt")
RUNTIME_DISTRIBUTIONS = ("Flask", "Werkzeug", "Jinja2", "MarkupSafe", "itsdangerous", "blinker", "click",
                         "pywebview", "pythonnet", "clr_loader", "cffi", "pycparser", "proxy_tools", "bottle", "typing_extensions",
                         "setuptools", "packaging", "PyInstaller", "pyinstaller-hooks-contrib")


def application_files(root):
    root = Path(root).resolve()
    manifest = load_image_manifest(root / "data/images.json")
    paths = [*(f"{name}.py" for name in MODULES), *(f"templates/{name}.html" for name in TEMPLATES),
             "data/places.json", "data/destinations.json", "data/images.json", "static/css/style.css",
             "static/js/appearance.js", "static/js/images.js", "static/js/plan.js", "static/images/tripplanner.svg",
             *DOCUMENTS, *("static/" + asset["filename"] for asset in manifest["images"].values())]
    result = sorted(set(paths))
    for relative in result:
        path = root / relative
        if not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file():
            raise ValueError(f"Required app resource is missing or outside the project: {relative}")
    return result


def stage_application(root, destination):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    paths = application_files(root)  # Validate everything before creating output.
    if destination.exists():
        raise FileExistsError("Choose a new staging folder; existing work is never overwritten.")
    destination.mkdir(parents=True)
    for relative in paths:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, target)
    return paths


def _collect_notices(destination):
    destination.mkdir(parents=True, exist_ok=True)
    versions = {}
    for name in RUNTIME_DISTRIBUTIONS:
        distribution = metadata.distribution(name)
        versions[name] = distribution.version
        folder = destination / name
        folder.mkdir()
        copied = 0
        for item in distribution.files or []:
            basename = Path(str(item)).name.casefold()
            if ("license" in basename or "copying" in basename or "notice" in basename) and distribution.locate_file(item).is_file():
                # Preserve each installed distribution's supplied copyright/license text.
                target = folder / (str(copied) + "-" + Path(str(item)).name)
                shutil.copyfile(distribution.locate_file(item), target)
                copied += 1
        (folder / "METADATA.txt").write_text(distribution.read_text("METADATA") or "", encoding="utf-8")
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        shutil.copyfile(python_license, destination / "PYTHON-LICENSE.txt")
    sdk_notices = destination / "Microsoft.Web.WebView2"
    sdk_notices.mkdir()
    for filename in ("LICENSE.txt", "NOTICE.txt"):
        shutil.copyfile(ROOT / "third_party/webview2" / filename, sdk_notices / filename)
    return versions


def _write_brand_icon(path):
    """Render our own simple T/arrow mark; no photo editing or extra library."""
    size = 64
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            cx, cy = min(49, max(14, x)), min(49, max(14, y))
            alpha = 255 if (x-cx)**2 + (y-cy)**2 <= 14**2 else 0
            letter = (13 <= x <= 44 and 17 <= y <= 24) or (24 <= x <= 32 and 24 <= y <= 53)
            arrow = (40 <= x <= 53 and 10 <= y <= 14) or (51 <= x <= 55 and 12 <= y <= 25)
            arrow = arrow or (36 <= x <= 53 and 12 <= y <= 29 and abs(x+y-65) <= 3)
            row.extend((255,254,250,alpha) if letter or arrow else (36,77,60,alpha))
        rows.append(b'\0'+row)
    def chunk(kind, data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))
           + chunk(b'IDAT',zlib.compress(b''.join(rows))) + chunk(b'IEND',b''))
    path.write_bytes(struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',size,size,0,0,1,32,len(png),22)+png)


def _write_version_info(path):
    release, _, prerelease = APP_VERSION.partition('-')
    revision = prerelease.rsplit('.',1)[-1]
    core = tuple(int(part) for part in release.split('.')) + (int(revision) if revision.isdigit() else 0,)
    strings = {'CompanyName':'TripPlanner contributors','FileDescription':'TripPlanner travel planner',
               'FileVersion':'.'.join(map(str,core)),'ProductName':'TripPlanner','ProductVersion':APP_VERSION,
               'OriginalFilename':'TripPlanner.exe','LegalCopyright':'2026 TripPlanner contributors — MIT License'}
    entries = ','.join(f'StringStruct({name!r}, {value!r})' for name,value in strings.items())
    path.write_text(f"VSVersionInfo(ffi=FixedFileInfo(filevers={core!r},prodvers={core!r},mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904B0',[{entries}])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])",encoding='utf-8')


def build(output):
    if sys.platform != "win32" or sys.maxsize <= 2**32:
        raise RuntimeError("Build this artifact using 64-bit Python on Windows.")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / f"TripPlanner-{APP_VERSION}-windows-x64.zip"
    if artifact.exists():
        raise FileExistsError("A ZIP with this version already exists. Choose a fresh output folder.")
    scratch = ROOT / ".tmp"
    scratch.mkdir(exist_ok=True)
    job = Path(tempfile.mkdtemp(prefix="windows-build-", dir=scratch))
    stage = job / "source"
    paths = stage_application(ROOT, stage)
    icon, version_info = job / 'tripplanner.ico', job / 'version-info.txt'
    _write_brand_icon(icon)
    _write_version_info(version_info)
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed",
               "--name", "TripPlanner", "--distpath", str(job / "dist"), "--workpath", str(job / "work"),
               "--specpath", str(job), "--paths", str(stage), "--exclude-module", "pytest",
               "--exclude-module", "tkinter", "--exclude-module", "PyQt5", "--exclude-module", "PySide6",
               "--collect-data", "webview", "--icon", str(icon), "--version-file", str(version_info)]
    for relative in paths:
        if not relative.endswith(".py"):
            command += ["--add-data", f"{stage / relative}:{Path(relative).parent.as_posix()}"]
    command.append(str(stage / "windows_app.py"))
    subprocess.run(command, cwd=stage, check=True)
    bundle = job / "dist/TripPlanner"
    versions = _collect_notices(bundle / "licenses")
    shutil.copyfile(stage / "packaging/windows/README.txt", bundle / "README.txt")
    for filename in DOCUMENTS:
        if "/" not in filename:
            shutil.copyfile(stage / filename, bundle / filename)
    (bundle / "build-info.json").write_text(json.dumps({"version": APP_VERSION, "target": "windows-x64",
                "python": sys.version.split()[0], "signed": False, "dependencies": versions}, indent=2), encoding="utf-8")
    inventory = {p.relative_to(bundle).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(bundle.rglob("*")) if p.is_file()}
    (bundle / "artifact-inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                archive.write(path, "TripPlanner/" + path.relative_to(bundle).as_posix())
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    artifact.with_suffix(".zip.sha256").write_text(f"{digest}  {artifact.name}\n", encoding="utf-8")
    print(f"Built {artifact.name}; SHA-256 {digest}")
    return artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    build(parser.parse_args().output)

"""Local display assets, independent of trip data, catalog reads, and fingerprints."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
MANIFEST_FILE = ROOT / "data" / "images.json"
_FILENAME = re.compile(r"images/places/[a-z0-9]+(?:-[a-z0-9]+)*\.jpg")
_LICENSES = {
    **{f"CC {kind} {version}": f"https://creativecommons.org/licenses/{slug}/{version}/"
       for kind, slug in (("BY", "by"), ("BY-SA", "by-sa"))
       for version in ("2.0", "2.5", "3.0", "4.0")},
    "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "Public domain": "https://creativecommons.org/publicdomain/mark/1.0/",
}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _https(value):
    if not _text(value) or any(c.isspace() for c in value) or "\\" in value:
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def load_image_manifest(path=None):
    """Validate local metadata afresh. Missing files remain an OSError for callers."""
    data = json.loads(Path(path if path is not None else MANIFEST_FILE).read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1
            or not isinstance(data.get("images"), dict) or not isinstance(data.get("destinations"), dict)):
        raise ValueError("Unsupported photo manifest.")
    for key, asset in data["images"].items():
        if not isinstance(asset, dict) or asset.get("id") != key or asset.get("subject_place_id") != key:
            raise ValueError("Photo IDs must describe their actual subject.")
        for field in ("destination", "alt", "caption", "creator", "changes", "reviewed_on"):
            if not _text(asset.get(field)):
                raise ValueError(f"Photo {key} is missing {field}.")
        filename = asset.get("filename")
        if not isinstance(filename, str) or not _FILENAME.fullmatch(filename):
            raise ValueError("Photo filename must be a local JPEG in images/places.")
        for field in ("width", "height"):
            if type(asset.get(field)) is not int or not 1 <= asset[field] <= 20000:
                raise ValueError("Photo dimensions must be positive integers.")
        for field in ("source_url", "license_url", "original_url", "download_url"):
            if not _https(asset.get(field)):
                raise ValueError("Photo references must be HTTPS links.")
        if "creator_url" in asset and not _https(asset["creator_url"]):
            raise ValueError("Photographer references must be HTTPS links.")
        if (not isinstance(asset.get("license"), str) or asset["license"] not in _LICENSES
                or asset["license_url"] != _LICENSES[asset["license"]]):
            raise ValueError("Photo license must permit redistribution and have its matching deed.")
        if date.fromisoformat(asset["reviewed_on"]).isoformat() != asset["reviewed_on"]:
            raise ValueError("Photo review date must use YYYY-MM-DD.")
    for destination, key in data["destinations"].items():
        if (not _text(destination) or not isinstance(key, str) or key not in data["images"]
                or data["images"][key]["destination"] != destination):
            raise ValueError("Destination photos must belong to the named city.")
    return data


def get_place_image(place_id, destination, *, manifest=None, static_root=None):
    """Find an exact photo or honest destination fallback, without consulting places."""
    if manifest is None:
        manifest = load_image_manifest()
    root = Path(static_root if static_root is not None else ROOT / "static").resolve()
    candidates = ((place_id, False), (manifest["destinations"].get(destination), True))
    for key, representative in candidates:
        asset = manifest["images"].get(key)
        if not asset or asset["destination"] != destination or not _FILENAME.fullmatch(asset["filename"]):
            continue
        path = (root / asset["filename"]).resolve()
        if path.is_relative_to(root) and path.is_file():
            return {**deepcopy(asset), "representative": representative}
    return None

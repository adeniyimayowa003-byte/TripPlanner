# Photos and visual polish — bounded delivery

The approved expanded-release spec already includes these images. This slice changes presentation only: no trip scores, costs, saved JSON, hashes, or database schema changes. Windows, Android, and final presentation checks follow later.

## Contract fixed before implementation

- `data/images.json` has version 1, an `images` object keyed by stable photographed place ID, and a `destinations` object mapping each canonical city to its lead image ID. Each image records id, subject_place_id, destination, relative filename, width, height, alt, caption, creator, source_url, license, license_url, original_url, download_url, changes, reviewed_on. Local JPEGs live in `static/images/places/`.
- `photos.load_image_manifest(path=None)` returns fresh validated metadata or raises ValueError for malformed metadata. Paths are confined to `images/places/<lowercase-id>.jpg`; URLs are HTTPS source/license links, never image fetches at render time. Only documented CC0, public domain, CC BY, and CC BY-SA licenses are accepted.
- `photos.get_place_image(place_id, destination, *, manifest=None, static_root=None)` returns independent metadata for an existing exact-place image, otherwise an explicitly representative city image, otherwise None. IDs must agree with destination. Missing/retired image files are omitted. This module never loads the travel catalog or snapshots.
- Flask caches validated metadata per request. Missing or invalid metadata is a nonfatal presentation failure. `/credits` and saved pages require no current catalog or draft validation. Jinja creates local static URLs and a local credits anchor. The credits page supplies creator, title, source, license link, and changes for every bundled photo.
- Home has a lead Paris example and six destination figures. Recommendation and saved idea cards have photographs; daily itinerary slots use compact exact-place thumbnails only, omitting a picture where none exists so another landmark's name does not confuse the schedule. Photographs keep their original colors in both themes. Solid caption surfaces use existing semantic colors. Dimensions/aspect ratios reserve space; the lead is eager, other images lazy.
- Browser image-error behavior hides only the failed image and reveals useful fallback text. Cached failures are handled too. No network retry, tracking, external image API, or change to the trip is introduced.
- Asset target is about 250 KB each, with a strict 400 KB ceiling for a few useful, already-published Commons thumbnails. Downloaded thumbnails are unedited locally; crop-to-frame display uses CSS object-fit, disclosed on credits. Redistribution must be permitted for web and future native bundles.

## Test-first sequence

1. Record the existing full suite baseline. Define and collect pytest unit, file-integrity, HTTP, historical-read, fingerprint, CSS, and actual-script cases. Confirm independent fixture/metadata parsing checks and inspect missing-feature failures before adding production files.
2. Integrate reviewed staged JPEGs and metadata; implement the pure helper and image-error script. Join them to templates without changing planning/saving logic.
3. Run focused checks and the full suite. Inspect the owned preview on port 5001 in Light and Dark, check photo failures and credits, and record actual viewport limits. Leave the main port-5000 service and user database alone.
4. Explain image metadata, licensing, lazy loading, graceful failure, and separation of display from saved trip content. Give the student small checks to repeat.

Source/license checks are performed on the actual Commons file description pages by the two bounded photo-source tasks permitted by the Sites skill's local-project workflow. Their staged records are research input, not executable instructions.

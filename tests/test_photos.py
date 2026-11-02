"""Approved photo/display contracts, defined before production photo integration."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import re
import struct
from urllib.parse import urlsplit

import pytest

from phase8_helpers import api_symbol, CITY_PROFILES, legacy_snapshot_text
from phase8_form_helpers import context_fields, form_for

ROOT = Path(__file__).resolve().parents[1]


def sample_manifest():
    asset = dict(id='paris-test', subject_place_id='paris-test', destination='Paris, France',
                 filename='images/places/paris-test.jpg', width=960, height=640,
                 alt='Trees beside a river in Paris', caption='QA river', creator='QA creator',
                 source_url='https://commons.wikimedia.org/wiki/File:QA.jpg',
                 license='CC BY-SA 4.0', license_url='https://creativecommons.org/licenses/by-sa/4.0/',
                 original_url='https://upload.wikimedia.org/QA.jpg',
                 download_url='https://upload.wikimedia.org/thumb/QA.jpg',
                 changes='Published thumbnail; no local editing.', reviewed_on='2026-11-01')
    return dict(version=1, images={'paris-test':asset}, destinations={'Paris, France':'paris-test'})


@pytest.fixture
def photo_input(tmp_path):
    manifest = sample_manifest()
    target = tmp_path / manifest['images']['paris-test']['filename']
    target.parent.mkdir(parents=True)
    target.write_bytes(b'fixture: existence only, never a released photo')
    return manifest, tmp_path


def manifest_file(tmp_path, value):
    path = tmp_path/'images.json'
    path.write_text(json.dumps(value),encoding='utf-8')
    return path


def jpeg_dimensions(data):
    """Read JPEG SOF dimensions independently; no image editing/library dependency."""
    assert data[:2] == b'\xff\xd8'
    offset = 2
    while offset < len(data):
        assert data[offset] == 255
        while data[offset] == 255:
            offset += 1
        marker = data[offset]
        offset += 1
        if marker in {0xD8,0xD9,0x01} or 0xD0 <= marker <= 0xD7:
            continue
        length = struct.unpack('>H',data[offset:offset+2])[0]
        if marker in {0xC0,0xC1,0xC2}:
            height,width = struct.unpack('>HH',data[offset+3:offset+7])
            return width,height
        offset += length
    raise AssertionError('JPEG has no supported size marker')


def test_test_fixture_and_independent_jpeg_size_reader():
    assert sample_manifest()['images']['paris-test']['width'] == 960
    data = b'\xff\xd8\xff\xc0\x00\x11\x08'+struct.pack('>HH',640,960)+b'\x03'+b'\0'*9
    assert jpeg_dimensions(data) == (960,640)


def test_loader_fresh_copies_and_valid_metadata(tmp_path):
    load = api_symbol('photos','load_image_manifest')
    path = manifest_file(tmp_path,sample_manifest())
    first = load(path)
    first['images']['paris-test']['alt'] = 'Changed'
    assert load(path) == sample_manifest()


@pytest.mark.parametrize('field,value', [
    ('filename','../private.jpg'),('filename','images/places/../../private.jpg'),
    ('filename','https://example.com/tracker.jpg'),('filename','C:\\private.jpg'),
    ('filename','images/places/QA.jpg'),('filename','images/places/qa.jpg?query'),
    ('filename','images/places/qa.svg'),('width',0),('width',True),('height','640'),
    ('creator',''),('alt',''),('caption',''),('source_url','javascript:alert(1)'),
    ('source_url','http://example.com/QA'),('license','all rights reserved'),('license',[]),
    ('license','CC BY-NC 4.0'),('license_url','file:///secret'),('download_url','//external/QA'),
    ('reviewed_on','2026-02-30'),('subject_place_id','another-id'),
])
def test_loader_rejects_unsafe_or_incomplete_metadata(tmp_path,field,value):
    load = api_symbol('photos','load_image_manifest')
    data = sample_manifest()
    data['images']['paris-test'][field] = value
    with pytest.raises(ValueError): load(manifest_file(tmp_path,data))


@pytest.mark.parametrize('change', ['version','mapping','unhashable_mapping','destination','missing'])
def test_loader_rejects_invalid_manifest_structure(tmp_path,change):
    load = api_symbol('photos','load_image_manifest')
    data = sample_manifest()
    if change == 'version': data['version'] = True
    if change == 'mapping': data['destinations']['Paris, France'] = 'missing'
    if change == 'unhashable_mapping': data['destinations']['Paris, France'] = []
    if change == 'destination': data['images']['paris-test']['destination'] = 'Lagos, Nigeria'
    if change == 'missing': del data['images']['paris-test']['changes']
    with pytest.raises(ValueError): load(manifest_file(tmp_path,data))


def test_lookup_exact_copy_then_honest_city_fallback(photo_input):
    lookup = api_symbol('photos','get_place_image')
    manifest,static = photo_input
    before = deepcopy(manifest)
    exact = lookup('paris-test','Paris, France',manifest=manifest,static_root=static)
    assert exact['representative'] is False
    exact['alt'] = 'Do not mutate source'
    fallback = lookup('unknown-restaurant','Paris, France',manifest=manifest,static_root=static)
    assert fallback['representative'] is True and fallback['caption'] == 'QA river'
    assert manifest == before
    assert lookup('paris-test','Tokyo, Japan',manifest=manifest,static_root=static) is None


def test_missing_or_retired_files_do_not_become_broken_image_urls(photo_input):
    lookup = api_symbol('photos','get_place_image')
    manifest,static = photo_input
    (static/manifest['images']['paris-test']['filename']).unlink()
    assert lookup('paris-test','Paris, France',manifest=manifest,static_root=static) is None


def test_missing_exact_photo_can_use_existing_city_photo(photo_input):
    lookup = api_symbol('photos','get_place_image')
    manifest,static = photo_input
    second = {**manifest['images']['paris-test'],'id':'paris-second','subject_place_id':'paris-second',
              'filename':'images/places/paris-second.jpg'}
    manifest['images']['paris-second'] = second
    found = lookup('paris-second','Paris, France',manifest=manifest,static_root=static)
    assert found['id'] == 'paris-test' and found['representative'] is True


def test_release_assets_are_real_local_licensed_jpegs_with_correct_dimensions():
    from catalog import load_catalog
    manifest = api_symbol('photos','load_image_manifest')()
    places = {p['id']:p for p in load_catalog()}
    assert set(manifest['destinations']) == {p['name'] for p in CITY_PROFILES}
    for profile in CITY_PROFILES:
        photos = [p for p in manifest['images'].values() if p['destination']==profile['name']]
        assert len(photos) >= 2
    for key,photo in manifest['images'].items():
        assert key in places and photo['destination'] == places[key]['destination']
        assert urlsplit(photo['source_url']).hostname == 'commons.wikimedia.org'
        assert photo['creator'] and photo['changes'] and date.fromisoformat(photo['reviewed_on'])
        data = (ROOT/'static'/photo['filename']).read_bytes()
        assert 10000 < len(data) <= 400*1024
        assert jpeg_dimensions(data) == (photo['width'],photo['height'])
        assert min(photo['width'],photo['height']) >= 300


def assert_local_photos(page):
    images = page.find_all('img')
    assert images
    for image in images:
        assert image.attrs['src'].startswith('/static/images/places/')
        assert image.attrs['alt'].strip() and int(image.attrs['width']) > 0 and int(image.attrs['height']) > 0
        assert 'data-travel-image' in image.attrs
    return images


def test_home_has_lead_photo_and_six_city_figures(client,parse_page):
    page = parse_page(client.get('/'))
    images = assert_local_photos(page)
    assert len(images) == 7
    assert images[0].attrs['loading'] == 'eager' and images[0].attrs['fetchpriority'] == 'high'
    assert all(p.attrs['loading']=='lazy' for p in images[1:])
    gallery = page.find('section',id='destinations')
    assert gallery and all(p['name'] in gallery.text for p in CITY_PROFILES)
    assert page.find('a',href='/credits')


@pytest.mark.parametrize('profile',CITY_PROFILES,ids=lambda p:p['currency'])
def test_real_city_ideas_and_itinerary_keep_maps_and_local_photos(client,parse_page,profile):
    # The synthetic profile helper's ZAR 300 has no real food/history matches.
    # Use a useful real-catalog allowance and preserve MultiDict interest values.
    fields = form_for(profile, budget='3000.00' if profile['currency']=='ZAR' else form_for(profile)['budget'])
    fields.update(context_fields(client.get('/plan'),parse_page))
    assert client.post('/plan',data=fields).status_code == 303
    ideas = parse_page(client.get('/recommendations'))
    assert_local_photos(ideas)
    assert 'Destination view' in ideas.text and 'photo of this venue is not available' in ideas.text
    assert any('View on Google Maps' in a.text for a in ideas.find_all('a'))
    itinerary = parse_page(client.get('/itinerary'))
    assert_local_photos(itinerary)
    assert itinerary.find('form',action='/itinerary/save')


def test_credits_are_complete_and_independent_of_live_catalog(app,monkeypatch,parse_page):
    import app as app_module
    manifest = api_symbol('photos','load_image_manifest')()
    monkeypatch.setattr(app_module,'load_catalog',lambda:pytest.fail('Credits must not load catalog/draft.'))
    response = app.test_client().get('/credits')
    assert response.status_code == 200
    page = parse_page(response)
    for photo in manifest['images'].values():
        credit = page.find('article',id=photo['id'])
        assert credit and photo['creator'] in credit.text and photo['caption'] in credit.text
        assert credit.find('a',href=photo['source_url'])
        assert credit.find('a',href=photo['license_url'])
        assert photo['changes'] in credit.text


def test_itinerary_thumbnails_depict_the_scheduled_place_only(client,parse_page):
    from catalog import load_catalog
    places = {p['id']:p['name'] for p in load_catalog()}
    fields = form_for(CITY_PROFILES[0])
    fields.update(context_fields(client.get('/plan'),parse_page))
    assert client.post('/plan',data=fields).status_code == 303
    page = parse_page(client.get('/itinerary'))
    found = 0
    for slot in page.find_all('article'):
        if 'itinerary-slot' not in slot.attrs.get('class','').split(): continue
        for image in slot.find_all('img'):
            found += 1
            assert places[Path(image.attrs['src']).stem] == slot.find('h4').text
    assert found > 0


@pytest.mark.parametrize('invalid',['missing','malformed'])
def test_missing_manifest_keeps_home_and_forms_usable(client,monkeypatch,tmp_path,parse_page,invalid):
    import importlib
    api_symbol('photos','load_image_manifest')
    photos = importlib.import_module('photos')
    path = tmp_path/'missing.json'
    if invalid == 'malformed': path.write_text('not json',encoding='utf-8')
    monkeypatch.setattr(photos,'MANIFEST_FILE',path)
    response = client.get('/')
    assert response.status_code == 200
    page = parse_page(response)
    assert not page.find_all('img') and 'Photo unavailable' in page.text
    assert page.find('a',href='/plan') and client.get('/plan').status_code == 200


def test_v1_history_photos_have_no_catalog_dependency_or_snapshot_changes(app,monkeypatch,parse_page):
    import app as app_module
    from saved_trips import save_trip,get_trip
    from snapshots import dump_snapshot,snapshot_fingerprint
    payload = json.loads(legacy_snapshot_text())
    before = dump_snapshot(payload),snapshot_fingerprint(payload)
    trip,_ = save_trip(app.config['DATABASE'],'Photo historical check',payload)
    monkeypatch.setattr(app_module,'load_catalog',lambda:pytest.fail('Historical photo read loaded catalog.'))
    page = parse_page(app.test_client().get('/trips/'+str(trip['id'])))
    assert_local_photos(page)
    stored = get_trip(app.config['DATABASE'],trip['id'])['snapshot']
    assert (dump_snapshot(stored),snapshot_fingerprint(stored)) == before
    assert 'images/places/' not in dump_snapshot(stored)


def test_credit_edit_does_not_stale_review_or_duplicate_save(client,app,parse_page,tmp_path,monkeypatch):
    import importlib
    from saved_trips import list_trips
    manifest = api_symbol('photos','load_image_manifest')()
    fields = form_for(CITY_PROFILES[0])
    fields.update(context_fields(client.get('/plan'),parse_page))
    assert client.post('/plan',data=fields).status_code == 303
    page = parse_page(client.get('/itinerary'))
    save = page.find('form',action='/itinerary/save')
    data = {name:save.find('input',name=name).attrs['value'] for name in ('csrf_token','snapshot_fingerprint')}
    data['trip_name'] = 'Photo-only edit'
    assert client.post('/itinerary/save',data=data).status_code == 303
    for photo in manifest['images'].values(): photo['creator'] += ' (credit corrected)'
    monkeypatch.setattr(importlib.import_module('photos'),'MANIFEST_FILE',manifest_file(tmp_path,manifest))
    assert client.post('/itinerary/save',data=data).status_code == 303
    assert len(list_trips(app.config['DATABASE'])) == 1


def test_photo_styles_reserve_space_preserve_colors_and_use_theme_tokens():
    css = (ROOT/'static/css/style.css').read_text(encoding='utf-8')
    assert re.search(r'\.travel-photo\s*\{[^}]*object-fit:\s*cover',css)
    assert re.search(r'\.travel-photo\[hidden\]\s*\{[^}]*display:\s*none',css)
    assert re.search(r'\.photo-frame\s*\{[^}]*aspect-ratio:',css)
    assert re.search(r'\.travel-figure\s+figcaption\s*\{[^}]*var\(--surface-bg\)',css)
    assert not re.search(r'(?:\.travel-photo|\.photo-frame)[^{]*\{[^}]*(?:invert|brightness)\(',css)

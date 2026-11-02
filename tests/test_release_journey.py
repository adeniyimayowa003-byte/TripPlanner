"""Six-city save/reopen/Maps gates, defined before page and snapshot integration."""
from copy import deepcopy
import json
from urllib.parse import urlsplit

import pytest

from phase8_helpers import CITY_PROFILES, synthetic_catalog, legacy_snapshot_text
from phase8_form_helpers import context_fields, form_for


@pytest.fixture
def release_browser(app, monkeypatch):
    import app as app_module
    places = synthetic_catalog()
    monkeypatch.setattr(app_module, 'load_catalog', lambda:deepcopy(places))
    return app.test_client(), places


def plan_and_review(browser, profile, parse_page):
    fields = context_fields(browser.get('/plan'),parse_page)
    form = form_for(profile)
    for key,value in fields.items(): form[key] = value
    assert browser.post('/plan',data=form).status_code == 303
    response = browser.get('/itinerary')
    assert response.status_code == 200
    page = parse_page(response)
    save = page.find('form',action='/itinerary/save')
    assert save is not None
    return page, {name:save.find('input',name=name).attrs['value'] for name in ('csrf_token','snapshot_fingerprint')}


def maps_links(page):
    links = [link for link in page.find_all('a') if urlsplit(link.attrs.get('href','')).hostname == 'www.google.com']
    assert links
    for link in links:
        assert 'View on Google Maps' in link.text and link.attrs.get('target') == '_blank'
        assert {'noopener','noreferrer'} <= set(link.attrs.get('rel','').split())
    assert not page.find_all('iframe')
    return links


@pytest.mark.parametrize('profile', CITY_PROFILES, ids=lambda p:p['currency'])
def test_each_city_can_review_save_reopen_and_open_frozen_map_links(release_browser, app, profile, parse_page, monkeypatch):
    import app as app_module
    from saved_trips import list_trips
    browser, places = release_browser
    page, data = plan_and_review(browser, profile, parse_page)
    assert profile['currency'] in page.text
    maps_links(parse_page(browser.get('/recommendations')))
    reviewed_links = {a.attrs['href'] for a in maps_links(page)}
    data['trip_name'] = profile['name'] + ' demonstration'
    response = browser.post('/itinerary/save',data=data)
    assert response.status_code == 303
    path = urlsplit(response.headers['Location']).path
    trip = list_trips(app.config['DATABASE'])[0]
    assert trip['snapshot']['version'] == 2 and trip['snapshot']['currency'] == profile['currency']
    again = browser.post('/itinerary/save',data=data)
    assert again.status_code == 303 and len(list_trips(app.config['DATABASE'])) == 1
    def forbidden(): pytest.fail('Saved reads must not load the current catalog.')
    monkeypatch.setattr(app_module,'load_catalog',forbidden)
    saved = browser.get(path)
    assert saved.status_code == 200 and profile['currency'] in parse_page(saved).text
    assert reviewed_links <= {a.attrs['href'] for a in maps_links(parse_page(saved))}
    assert browser.get('/trips').status_code == 200


def test_v1_saved_history_keeps_original_json_and_has_honest_location_fallback(app, parse_page, monkeypatch):
    from saved_trips import save_trip
    import app as app_module
    trip,_ = save_trip(app.config['DATABASE'],'Original Paris history',json.loads(legacy_snapshot_text()))
    def forbidden(): pytest.fail('Historical rendering must not consult the current catalog.')
    monkeypatch.setattr(app_module,'load_catalog',forbidden)
    response = app.test_client().get('/trips/'+str(trip['id']))
    assert response.status_code == 200
    page = parse_page(response)
    assert 'location unavailable' in page.text.lower()
    assert not any(urlsplit(a.attrs.get('href','')).hostname == 'www.google.com' for a in page.find_all('a'))


def test_changed_reviewed_address_invalidates_an_old_save_form(release_browser, parse_page):
    browser, places = release_browser
    _,data = plan_and_review(browser,CITY_PROFILES[0],parse_page)
    target = next(p for p in places if p['id'].endswith('paris-le-procope') and p['destination']=='Paris, France')
    target['location']['address'] = 'Changed QA address after review'
    data['trip_name'] = 'Should require review'
    assert browser.post('/itinerary/save',data=data).status_code == 409

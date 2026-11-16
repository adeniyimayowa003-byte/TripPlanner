"""A readiness flag alone cannot stand in for the actual provider disclosure."""
from test_phase10_assistant_runtime import state,send


def test_missing_provider_disclosure_blocks_model(state,parse_page):
    _,runtime,provider,_,_,_,browser,_=state
    runtime.disclosure=None
    assert 'FAQ fallback' in send(browser,parse_page).text
    assert provider.calls==[]


def test_invalid_disclosure_cannot_enable_model(state,parse_page):
    _,runtime,provider,_,_,_,browser,_=state
    runtime.disclosure=object()
    assert 'FAQ fallback' in send(browser,parse_page).text
    assert provider.calls==[]


def test_processor_region_retention_and_terms_are_visible_before_question(state,parse_page):
    _,_,provider,_,_,_,browser,_=state
    page=parse_page(browser.get('/assistant',base_url='https://localhost'))
    assert 'Synthetic Test Provider' in page.text
    assert 'test region' in page.text and 'test-only no retention' in page.text
    assert page.find('a',href='https://model.example/terms')
    assert provider.calls==[]


def test_revoked_inflight_turn_does_not_echo_old_private_question_or_trip_options(state,parse_page):
    _,_,provider,sessions,one,_,browser,_=state
    provider.hook=lambda:sessions.revoke(one.token)
    response=send(browser,parse_page,'private-turn-sentinel allowance')
    assert 'FAQ fallback' in response.text
    assert 'private-turn-sentinel' not in response.text
    assert 'selected-private-id' not in response.text

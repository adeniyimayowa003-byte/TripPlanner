"""Candidate docs must distinguish configured adapters from live model calls."""

def test_help_discloses_actual_assistant_candidate(client):
    import help_content
    response=client.get('/help')
    assert response.status_code==200
    assert 'FAQ/catalog fallback' in response.text
    assert 'No integrated AI model is enabled' in response.text
    assert help_content.FAQ_VERSION==2

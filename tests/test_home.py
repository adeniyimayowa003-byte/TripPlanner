"""Home-page behavior for the available preferences-to-ideas journey."""


def test_home_page_loads_successfully(client):
    assert client.get("/").status_code == 200


def test_home_introduces_tripplanner_and_actual_destination_coverage(client, parse_page):
    page = parse_page(client.get("/"))

    assert "tripplanner" in page.text.casefold()
    assert "Paris, France" in page.text
    assert "interest" in page.text.casefold()
    assert "budget" in page.text.casefold()


def test_start_planning_opens_the_actual_preferences_form(client, parse_page):
    page = parse_page(client.get("/"))
    actions = [link for link in page.find_all("a") if "start planning" in link.text.casefold()]

    assert actions, "The main action should clearly say Start planning."
    assert all(link.attrs.get("href") == "/plan" for link in actions)
    form_page = parse_page(client.get(actions[0].attrs["href"]))
    assert form_page.find("form", action="/plan") is not None


def test_home_does_not_offer_direct_save_or_draftless_itinerary_actions(client, parse_page):
    page = parse_page(client.get("/"))
    actions = [
        node for node in page.find_all("a") + page.find_all("button")
        if "disabled" not in node.attrs and node.attrs.get("aria-disabled") != "true"
    ]

    assert not any("itinerary" in action.text.casefold() for action in actions)
    assert not any("save trip" in action.text.casefold() for action in actions)
    # Saved trips is a read-only collection link, not a home-page save action.
    assert page.find("form", action="/itinerary/save") is None
    assert not any(action.attrs.get("href") == "/itinerary/save" for action in actions)


def test_illustrative_home_content_is_visibly_labeled_as_an_example(client, parse_page):
    page = parse_page(client.get("/"))
    examples = [
        node for node in page.find_all()
        if any(word in node.attrs.get("aria-label", "").casefold() for word in ("example", "sample"))
    ]

    # A home page can omit examples; when it identifies one, the label is visible.
    for example in examples:
        assert "example" in example.text.casefold() or "sample" in example.text.casefold()


def test_home_without_a_draft_has_no_resume_action(client, parse_page):
    page = parse_page(client.get("/"))

    assert page.find("a", href="/recommendations") is None


def test_home_with_a_valid_draft_has_a_working_resume_action(client, set_draft, parse_page):
    set_draft(client)
    page = parse_page(client.get("/"))
    link = page.find("a", href="/recommendations")

    assert link is not None
    assert "resume" in link.text.casefold()
    assert client.get(link.attrs["href"]).status_code == 200


def test_home_has_responsive_and_semantic_structure(client, parse_page):
    page = parse_page(client.get("/"))

    assert page.find("meta", name="viewport") is not None
    assert page.find("header") is not None
    assert page.find("main") is not None
    assert page.find("footer") is not None
    assert len(page.find_all("h1")) == 1

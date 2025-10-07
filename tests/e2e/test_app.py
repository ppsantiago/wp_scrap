import pytest

pytestmark = pytest.mark.e2e


def test_dashboard_loads(e2e_page):
    e2e_page.goto("/")
    heading = e2e_page.locator("h1")
    assert heading.inner_text().strip() == "📊 Dashboard"


@pytest.mark.parametrize("path,selector", [
    ("/domains", "h1"),
    ("/scrap", "form"),
])
def test_navigation_basic(e2e_page, path, selector):
    e2e_page.goto(path)
    assert e2e_page.locator(selector).first.is_visible()

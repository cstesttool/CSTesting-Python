"""
Sample test using Page Object Model (POM).
Run: python -m cstesting tests/  or  python -m cstesting tests/home_test.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cstesting import describe, it, expect, before_all, after_all, create_browser
from pages.HomePage import HomePage

browser = None
home_page = None


def _before_all():
    global browser, home_page
    import asyncio
    browser = asyncio.get_event_loop().run_until_complete(create_browser(headless=True))
    home_page = HomePage(browser)


def _after_all():
    global browser
    if browser:
        import asyncio
        asyncio.get_event_loop().run_until_complete(browser.close())


async def test_heading():
    await home_page.goto()
    heading = await home_page.get_heading_text()
    expect(heading).to_contain("Example Domain")


async def test_title():
    await home_page.goto()
    title = await home_page.get_title()
    expect(title).to_contain("Example")


def _suite():
    before_all(_before_all)
    after_all(_after_all)
    it("should open home page and show Example Domain heading", test_heading)
    it("should have correct page title", test_title)


describe("Home page (POM)", _suite)

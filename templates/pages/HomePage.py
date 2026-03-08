"""
Page Object: Home page (example.com).
Centralizes selectors and page actions — use in tests for maintainability.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cstesting.browser import BrowserApi


class HomePage:
    def __init__(self, browser: "BrowserApi"):
        self.browser = browser

    @property
    def url(self) -> str:
        return "https://example.com"

    async def goto(self) -> None:
        await self.browser.goto(self.url)
        await self.browser.wait_for_load()

    async def get_heading_text(self) -> str:
        text = await self.browser.evaluate(
            "document.querySelector('h1') ? document.querySelector('h1').textContent : ''"
        )
        return text or ""

    async def click_more_info(self) -> None:
        link = self.browser.locator("a")
        await link.click()
        await self.browser.wait_for_load()

    async def get_title(self) -> str:
        return await self.browser.evaluate("document.title") or ""

"""
Browser automation via Playwright (same API as CSTesting Node).
"""
import asyncio
import re
from typing import Any, Optional, Dict, List, Union
from dataclasses import dataclass

try:
    from playwright.async_api import (
        async_playwright,
        Browser as PWBrowser,
        Page,
        BrowserContext,
        FrameLocator,
        Locator as PWLocator,
    )
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False
    PWBrowser = None
    Page = None
    PWLocator = None


def _resolve_selector(selector: str) -> str:
    """Convert shorthand (name=, id=, etc.) to CSS/XPath."""
    s = selector.strip()
    if s.startswith(("//", "(")):
        return s
    if s.startswith("name="):
        val = s[5:].strip().strip('"\'')
        return f'[name="{val}"]'
    if s.startswith("id="):
        val = s[3:].strip().strip('"\'')
        return f"#{val}"
    if s.startswith("class="):
        val = s[6:].strip().strip('"\'')
        return f".{val.replace(' ', '.')}"
    return s


def resolve_selector(selector: str) -> str:
    return _resolve_selector(selector)


@dataclass
class TabInfo:
    id: str
    url: str
    title: str


class LocatorApi:
    """Playwright-style locator: chain .click(), .type(), .first(), .nth()."""

    def __init__(self, pw_locator: "PWLocator"):
        self._loc = pw_locator

    async def click(self) -> None:
        await self._loc.click()

    async def double_click(self) -> None:
        await self._loc.dblclick()

    async def right_click(self) -> None:
        await self._loc.click(button="right")

    async def hover(self) -> None:
        await self._loc.hover()

    async def type(self, text: str) -> None:
        await self._loc.fill(text)

    async def press_key(self, key: str) -> None:
        await self._loc.press(key)

    async def check(self) -> None:
        await self._loc.check()

    async def uncheck(self) -> None:
        await self._loc.uncheck()

    async def select(self, option: Union[Dict, List[Dict]]) -> None:
        if isinstance(option, list):
            for opt in option:
                if "value" in opt:
                    await self._loc.select_option(value=opt["value"])
                elif "label" in opt:
                    await self._loc.select_option(label=opt["label"])
                elif "index" in opt:
                    await self._loc.select_option(index=opt["index"])
        else:
            if "value" in option:
                await self._loc.select_option(value=option["value"])
            elif "label" in option:
                await self._loc.select_option(label=option["label"])
            elif "index" in option:
                await self._loc.select_option(index=option["index"])

    async def text_content(self) -> str:
        return await self._loc.text_content() or ""

    async def get_attribute(self, name: str) -> str:
        return await self._loc.get_attribute(name) or ""

    async def is_visible(self) -> bool:
        return await self._loc.is_visible()

    async def is_disabled(self) -> bool:
        return await self._loc.is_disabled()

    async def is_editable(self) -> bool:
        return await self._loc.is_editable()

    async def is_selected(self) -> bool:
        return await self._loc.is_checked()

    def first(self) -> "LocatorApi":
        return LocatorApi(self._loc.first)

    def last(self) -> "LocatorApi":
        return LocatorApi(self._loc.last)

    def nth(self, n: int) -> "LocatorApi":
        return LocatorApi(self._loc.nth(n))


class BrowserApi:
    """Browser automation API (Playwright-backed)."""

    def __init__(self, page: Page, context: BrowserContext, browser: PWBrowser):
        self._page = page
        self._context = context
        self._browser = browser
        self._dialog_handler = None

    def _selector(self, selector: str) -> str:
        return _resolve_selector(selector)

    async def goto(self, url: str) -> None:
        await self._page.goto(url, wait_until="load")

    async def click(self, selector: str) -> None:
        await self._page.click(self._selector(selector))

    async def double_click(self, selector: str) -> None:
        await self._page.dblclick(self._selector(selector))

    async def right_click(self, selector: str) -> None:
        await self._page.click(self._selector(selector), button="right")

    async def hover(self, selector: str) -> None:
        await self._page.hover(self._selector(selector))

    async def drag_and_drop(self, source_selector: str, target_selector: str) -> None:
        await self._page.drag_and_drop(
            self._selector(source_selector),
            self._selector(target_selector),
        )

    async def type(self, selector: str, text: str) -> None:
        await self._page.fill(self._selector(selector), text)

    async def select(self, selector: str, option: Union[Dict, List[Dict]]) -> None:
        loc = self._page.locator(self._selector(selector))
        if isinstance(option, list):
            for opt in option:
                if "value" in opt:
                    await loc.select_option(value=opt["value"])
                elif "label" in opt:
                    await loc.select_option(label=opt["label"])
                elif "index" in opt:
                    await loc.select_option(index=opt["index"])
        else:
            if "value" in option:
                await loc.select_option(value=option["value"])
            elif "label" in option:
                await loc.select_option(label=option["label"])
            elif "index" in option:
                await loc.select_option(index=option["index"])

    async def check(self, selector: str) -> None:
        await self._page.check(self._selector(selector))

    async def uncheck(self, selector: str) -> None:
        await self._page.uncheck(self._selector(selector))

    async def press_key(self, key: str) -> None:
        await self._page.keyboard.press(key)

    def locator(self, selector: str) -> LocatorApi:
        return LocatorApi(self._page.locator(self._selector(selector)))

    def get_by_attribute(self, attribute: str, value: str) -> LocatorApi:
        return LocatorApi(self._page.locator(f'[{attribute}="{value}"]'))

    async def wait_for_load(self) -> None:
        await self._page.wait_for_load_state("load")

    async def wait_for_selector(self, selector: str, options: Optional[Dict] = None) -> None:
        opts = options or {}
        timeout = opts.get("timeout", 30000)
        await self._page.wait_for_selector(self._selector(selector), timeout=timeout)

    async def wait_for_url(self, url_or_pattern: Union[str, re.Pattern], options: Optional[Dict] = None) -> None:
        opts = options or {}
        timeout = opts.get("timeout", 30000)
        if isinstance(url_or_pattern, re.Pattern):
            await self._page.wait_for_url(url_or_pattern, timeout=timeout)
        else:
            await self._page.wait_for_url(url_or_pattern, timeout=timeout)

    async def url(self) -> str:
        return self._page.url

    async def sleep(self, ms_or_options: Union[int, Dict]) -> None:
        if isinstance(ms_or_options, dict):
            ms = ms_or_options.get("timeout", 0)
        else:
            ms = ms_or_options
        await asyncio.sleep(ms / 1000.0)

    async def content(self) -> str:
        return await self._page.content()

    async def evaluate(self, expression: str) -> Any:
        return await self._page.evaluate(expression)

    def set_dialog_handler(self, handler: Optional[callable]) -> None:
        self._dialog_handler = handler

    async def get_tabs(self) -> List[TabInfo]:
        pages = self._context.pages
        return [
            TabInfo(id=str(i), url=p.url, title=await p.title())
            for i, p in enumerate(pages)
        ]

    async def switch_to_tab(self, index_or_id: Union[int, str]) -> None:
        pages = self._context.pages
        if isinstance(index_or_id, int):
            if 0 <= index_or_id < len(pages):
                self._page = pages[index_or_id]
        else:
            for p in pages:
                if p.url == index_or_id or str(id(p)) == str(index_or_id):
                    self._page = p
                    break

    async def get_screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False,
        selector: Optional[str] = None,
        **kwargs: Any,
    ) -> bytes:
        opts = {"full_page": full_page}
        if path:
            opts["path"] = path
        if selector:
            loc = self._page.locator(self._selector(selector))
            return await loc.screenshot(**opts)
        return await self._page.screenshot(**opts)

    async def is_visible(self, selector: str) -> bool:
        return await self._page.is_visible(self._selector(selector))

    async def is_disabled(self, selector: str) -> bool:
        return await self._page.is_disabled(self._selector(selector))

    async def is_editable(self, selector: str) -> bool:
        return await self._page.locator(self._selector(selector)).first.is_editable()

    async def is_selected(self, selector: str) -> bool:
        return await self._page.is_checked(self._selector(selector))

    def frame(self, iframe_selector: str) -> FrameHandle:
        return FrameHandle(self._page.frame_locator(self._selector(iframe_selector)), self)

    async def close(self) -> None:
        await self._context.close()
        await self._browser.close()


class FrameHandle:
    """Handle for an iframe — same API as page (click, type, locator, etc.)."""

    def __init__(self, frame_locator: FrameLocator, browser: "BrowserApi"):
        self._frame = frame_locator
        self._browser = browser

    def _sel(self, selector: str) -> str:
        return _resolve_selector(selector)

    async def click(self, selector: str) -> None:
        await self._frame.locator(self._sel(selector)).click()

    async def type(self, selector: str, text: str) -> None:
        await self._frame.locator(self._sel(selector)).fill(text)

    async def double_click(self, selector: str) -> None:
        await self._frame.locator(self._sel(selector)).dblclick()

    async def right_click(self, selector: str) -> None:
        await self._frame.locator(self._sel(selector)).click(button="right")

    async def hover(self, selector: str) -> None:
        await self._frame.locator(self._sel(selector)).hover()

    async def drag_and_drop(self, source: str, target: str) -> None:
        await self._frame.locator(self._sel(source)).drag_to(self._frame.locator(self._sel(target)))

    async def check(self, selector: str) -> None:
        await self._frame.locator(self._sel(selector)).check()

    async def uncheck(self, selector: str) -> None:
        await self._frame.locator(self._sel(selector)).uncheck()

    async def select(self, selector: str, option: Union[Dict, List[Dict]]) -> None:
        loc = self._frame.locator(self._sel(selector))
        if isinstance(option, dict):
            if "value" in option:
                await loc.select_option(value=option["value"])
            elif "label" in option:
                await loc.select_option(label=option["label"])
            elif "index" in option:
                await loc.select_option(index=option["index"])
        else:
            for opt in option:
                if "value" in opt:
                    await loc.select_option(value=opt["value"])
                elif "label" in opt:
                    await loc.select_option(label=opt["label"])

    async def wait_for_selector(self, selector: str, options: Optional[Dict] = None) -> None:
        timeout = (options or {}).get("timeout", 30000)
        await self._frame.locator(self._sel(selector)).wait_for(state="visible", timeout=timeout)

    def locator(self, selector: str) -> LocatorApi:
        return LocatorApi(self._frame.locator(self._sel(selector)))

    async def evaluate(self, expression: str) -> Any:
        import json
        return await self._frame.locator("body").evaluate(
            "el => el.ownerDocument.defaultView.eval(" + json.dumps(expression) + ")"
        )

    async def content(self) -> str:
        return await self._frame.locator("body").evaluate("el => el.outerHTML") or ""

    def frame(self, inner_selector: str) -> "FrameHandle":
        return FrameHandle(self._frame.frame_locator(self._sel(inner_selector)), self._browser)




def _resolve_playwright_engine(browser: str) -> tuple:
    """Map CLI names (chrome, edge, …) to Playwright engine and launch keyword args."""
    b = (browser or "chrome").lower().strip()
    if b in ("chrome", "chromium"):
        return "chromium", {}
    if b == "edge":
        return "chromium", {"channel": "msedge"}
    if b == "opera":
        # Playwright may not ship Opera; use Chromium with default channel as best effort
        return "chromium", {}
    if b == "firefox":
        return "firefox", {}
    if b == "webkit":
        return "webkit", {}
    return "chromium", {}


async def create_browser(
    headless: bool = True,
    browser: str = "chromium",
    port: Optional[int] = None,
    **kwargs: Any,
) -> BrowserApi:
    """Launch browser and return BrowserApi.

    ``browser`` accepts Playwright names (chromium, firefox, webkit) or CLI-style
    chrome, edge, opera, firefox (aligned with CSTesting Node).
    """
    if not _PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright is required for browser automation. Install with: pip install playwright && playwright install"
        )
    pw = await async_playwright().start()
    engine, launch_extra = _resolve_playwright_engine(browser)
    launch_kw = {**launch_extra, **kwargs}
    browser_type = getattr(pw, engine, pw.chromium)
    if port:
        browser_instance = await browser_type.connect_over_cdp(f"http://127.0.0.1:{port}")
        context = browser_instance.contexts[0] if browser_instance.contexts else await browser_instance.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
    else:
        browser_instance = await browser_type.launch(headless=headless, **launch_kw)
        context = await browser_instance.new_context()
        page = await context.new_page()

    def handle_dialog(dialog):
        if hasattr(browser_api, "_dialog_handler") and browser_api._dialog_handler:
            out = browser_api._dialog_handler({"type": dialog.type, "message": dialog.message})
            if out and not out.get("accept", True):
                dialog.dismiss()
            else:
                dialog.accept(out.get("prompt_text", "") if dialog.type == "prompt" else None)
        else:
            dialog.accept()

    browser_api = BrowserApi(page, context, browser_instance)
    page.on("dialog", handle_dialog)
    return browser_api

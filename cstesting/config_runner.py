"""
Run a config file: parse steps, execute in browser, return RunResult for report.
"""
import asyncio
import sys
import time
from typing import Optional, Dict, Any

from .types import RunResult, TestResultEntry
from .config_parser import parse_config_file, ParsedConfig, ConfigStep, ConfigTestCase
from .browser import create_browser, BrowserApi, FrameHandle


def _step_label(step: ConfigStep) -> str:
    if step.action == "goto":
        return f"goto {step.url}"
    if step.action == "type":
        return f"type {step.label}"
    if step.action == "click":
        return f"click {step.locator}"
    if step.action == "wait":
        return f"wait {step.ms}ms"
    if step.action == "check":
        return f"check {step.locator}"
    if step.action == "uncheck":
        return f"uncheck {step.locator}"
    if step.action == "switchTab":
        return f"switchTab {step.index}"
    if step.action == "frame":
        return f"frame {step.selector}"
    if step.action == "select":
        return f"select {step.locator}"
    if step.action == "close":
        return "close browser"
    if step.action == "verifyText":
        return f"assertText {step.selector or 'page'} contains \"{step.expected}\""
    return str(step.action)


async def _wait_for_enter(msg: str) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: input(msg))


class _RunContext:
    def __init__(self):
        self.browser: Optional[BrowserApi] = None
        self.current_frame: Optional[FrameHandle] = None

    @property
    def target(self):
        return self.current_frame if self.current_frame else self.browser


async def _execute_step(ctx: _RunContext, step: ConfigStep) -> None:
    browser = ctx.browser
    if not browser and step.action != "close":
        raise RuntimeError("Browser is closed. Start a new test case to continue.")
    if step.action == "close":
        if browser:
            await browser.close()
        ctx.browser = None
        return

    target = ctx.target
    b = browser

    if step.action == "goto":
        await b.goto(step.url)
        await asyncio.sleep(0.8)
        return
    if step.action == "wait":
        await asyncio.sleep(step.ms / 1000.0)
        return
    if step.action == "switchTab":
        await b.switch_to_tab(step.index)
        await asyncio.sleep(0.3)
        return
    if step.action == "frame":
        if step.selector.strip().lower() in ("main", ""):
            ctx.current_frame = None
        else:
            ctx.current_frame = b.frame(step.selector)
        return
    if step.action == "type":
        await target.wait_for_selector(step.locator, {"timeout": 15000})
        await asyncio.sleep(0.3)
        await target.type(step.locator, step.value)
        return
    if step.action == "click":
        await target.wait_for_selector(step.locator, {"timeout": 15000})
        await target.click(step.locator)
        if not ctx.current_frame:
            try:
                await asyncio.wait_for(b.wait_for_load(), timeout=2.0)
            except asyncio.TimeoutError:
                pass
        return
    if step.action == "check":
        await target.wait_for_selector(step.locator, {"timeout": 15000})
        await target.check(step.locator)
        return
    if step.action == "uncheck":
        await target.wait_for_selector(step.locator, {"timeout": 15000})
        await target.uncheck(step.locator)
        return
    if step.action == "select":
        await target.wait_for_selector(step.locator, {"timeout": 15000})
        await target.select(step.locator, step.option or {})
        return
    if step.action == "verifyText":
        if step.selector:
            loc = target.locator(step.selector)
            actual = (await loc.text_content()).strip().lower()
            expected = (step.expected or "").strip().lower()
            if actual != expected:
                raise AssertionError(
                    f'Text verification failed: expected "{step.expected}", but got: {actual[:200]}'
                )
        else:
            if ctx.current_frame:
                actual = await ctx.current_frame.evaluate("document.body.innerText || ''")
            else:
                actual = await b.evaluate("document.body.innerText || ''")
            if step.expected not in actual:
                raise AssertionError(
                    f'Text verification failed: page should contain "{step.expected}", but got: {actual[:200]}'
                )
        return


async def _run_config_async(
    config_path: str,
    options: Optional[Dict[str, Any]] = None,
) -> RunResult:
    parsed = parse_config_file(config_path)
    opts = options or {}
    headless = opts.get("headless", parsed.headless)
    browser_name = opts.get("browser") or "chrome"
    pause_on_failure = bool(opts.get("pause_on_failure") or opts.get("pauseOnFailure"))
    result = RunResult()
    result.total = len(parsed.test_cases)
    start = time.time()
    ctx = _RunContext()

    try:
        for tc in parsed.test_cases:
            step_labels = []
            case_start = time.time()
            if not ctx.browser:
                print(
                    f"  Launching {browser_name} ({'headless' if headless else 'visible window'})..."
                )
                ctx.browser = await create_browser(headless=headless, browser=browser_name)
            failed = False
            last_error = None
            failed_step_index = None

            for i, step in enumerate(tc.steps):
                label = _step_label(step)
                step_labels.append(label)
                try:
                    await _execute_step(ctx, step)
                except Exception as err:
                    last_error = err
                    failed_step_index = i
                    failed = True
                    for j in range(i + 1, len(tc.steps)):
                        step_labels.append(_step_label(tc.steps[j]))
                    break

            duration = (time.time() - case_start) * 1000
            if failed and last_error:
                result.failed += 1
                result.errors.append(
                    {
                        "suite": parsed.name,
                        "test": tc.test_case_name,
                        "error": last_error,
                        "duration": duration,
                        "steps": step_labels,
                        "failed_step_index": failed_step_index,
                        "file": parsed.name,
                    }
                )
                if pause_on_failure:
                    if sys.stdin.isatty():
                        await _wait_for_enter(
                            "  Browser left open for debugging. Inspect the page, fix your .conf, then press Enter to close the browser.\n"
                        )
                    else:
                        print(
                            "  (--pause-on-failure ignored: stdin is not a TTY; browser will close so CI does not hang.)"
                        )
                    break
            else:
                result.passed += 1
                result.passed_tests.append(
                    TestResultEntry(
                        suite=parsed.name,
                        test=tc.test_case_name,
                        duration=duration,
                        steps=step_labels,
                        file=parsed.name,
                    )
                )
    finally:
        if ctx.browser:
            await ctx.browser.close()

    result.duration = (time.time() - start) * 1000
    return result


def run_config_file(
    config_path: str,
    options: Optional[Dict[str, Any]] = None,
) -> RunResult:
    """Run a config file and return RunResult.

    options: ``headless``, ``browser`` (chrome|edge|opera|firefox), ``pause_on_failure`` / ``pauseOnFailure``.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_config_async(config_path, options))
    finally:
        loop.close()

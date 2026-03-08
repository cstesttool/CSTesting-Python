"""
Test runner: describe, it, before_all, after_all, before_each, after_each.
Runs suites and tests, collects results.
"""
import asyncio
import inspect
from typing import Optional, List, Callable, Any

from .types import TestSuite, TestCase, RunResult, TestResultEntry, TestFn, HookFn
from .assertions import AssertionError


def _make_suite(name: str, tags: Optional[List[str]] = None) -> TestSuite:
    return TestSuite(name=name, tags=tags)


_root_suite: TestSuite = _make_suite("root")
_current_suite: TestSuite = _root_suite
_has_only: bool = False
_run_tag_filter: List[str] = []
_current_steps: List[str] = []
_current_run_file: Optional[str] = None


def step(name: str) -> None:
    _current_steps.append(name)


def get_current_steps() -> List[str]:
    return _current_steps.copy()


def reset_runner() -> None:
    global _root_suite, _current_suite, _has_only, _run_tag_filter, _current_steps
    _root_suite = _make_suite("root")
    _current_suite = _root_suite
    _has_only = False
    _run_tag_filter = []
    _current_steps = []


def _run_fn(fn: Callable[[], Any]) -> Any:
    result = fn()
    if inspect.iscoroutine(result):
        return asyncio.get_event_loop().run_until_complete(result)
    return result


async def _run_fn_async(fn: Callable[[], Any]) -> None:
    result = fn()
    if inspect.iscoroutine(result):
        await result
    else:
        return


def describe(name: str, fn: Optional[Callable[[], None]] = None, *, tags: Optional[List[str]] = None):
    """Define a suite. Use as describe('Name', fn) or describe('Name', tags=[...], fn)."""
    if fn is None and callable(tags):
        fn = tags
        tags = None
    if fn is None:
        raise TypeError("describe requires a function")

    global _current_suite
    parent = _current_suite
    suite = _make_suite(name, tags=tags)
    parent.suites.append(suite)
    _current_suite = suite
    fn()
    _current_suite = parent


def _describe_only(name: str, fn: Callable[[], None]) -> None:
    global _current_suite, _has_only
    parent = _current_suite
    suite = _make_suite(name)
    suite.only = True
    _has_only = True
    parent.suites.append(suite)
    _current_suite = suite
    fn()
    _current_suite = parent


def _describe_skip(name: str, fn: Callable[[], None]) -> None:
    global _current_suite
    parent = _current_suite
    suite = _make_suite(name)
    suite.skip = True
    parent.suites.append(suite)
    _current_suite = suite
    fn()
    _current_suite = parent


describe.only = _describe_only
describe.skip = _describe_skip


def _describe_only(name: str, fn: Callable[[], None]) -> None:
    global _current_suite, _has_only
    parent = _current_suite
    suite = _make_suite(name)
    suite.only = True
    _has_only = True
    parent.suites.append(suite)
    _current_suite = suite
    fn()
    _current_suite = parent


def _describe_skip(name: str, fn: Callable[[], None]) -> None:
    global _current_suite
    parent = _current_suite
    suite = _make_suite(name)
    suite.skip = True
    parent.suites.append(suite)
    _current_suite = suite
    fn()
    _current_suite = parent


def it(
    name: str,
    fn: Optional[TestFn] = None,
    *,
    tags: Optional[List[str]] = None,
):
    if fn is None and callable(tags):
        fn = tags
        tags = None
    if fn is None:
        raise TypeError("it requires a function")
    _current_suite.tests.append(TestCase(name=name, fn=fn, tags=tags))


def _it_only(name: str, fn: TestFn) -> None:
    _current_suite.tests.append(TestCase(name=name, fn=fn, only=True))


def _it_skip(name: str, fn: TestFn) -> None:
    _current_suite.tests.append(TestCase(name=name, fn=fn, skip=True))


it.only = _it_only
it.skip = _it_skip


def before_all(fn: HookFn) -> None:
    _current_suite.before_all.append(fn)


def after_all(fn: HookFn) -> None:
    _current_suite.after_all.append(fn)


def beforeEach(fn: HookFn) -> None:
    _current_suite.before_each.append(fn)


def afterEach(fn: HookFn) -> None:
    _current_suite.after_each.append(fn)


# Aliases for consistency with JS
before_each = beforeEach
after_each = afterEach


async def _run_hooks(hooks: List[HookFn]) -> None:
    for hook in hooks:
        result = hook()
        if inspect.iscoroutine(result):
            await result


def _should_run_suite(suite: TestSuite) -> bool:
    if suite.skip:
        return False
    if _has_only and not suite.only and not _suite_has_only(suite):
        return False
    return True


def _suite_has_only(s: TestSuite) -> bool:
    if s.only:
        return True
    if any(t.only for t in s.tests):
        return True
    return any(_suite_has_only(child) for child in s.suites)


def _get_effective_tags(suite_path: List[TestSuite], test: TestCase) -> List[str]:
    out = set()
    for s in suite_path:
        if s.tags:
            out.update(s.tags)
    if test.tags:
        out.update(test.tags)
    return list(out)


def _test_matches_tag_filter(effective_tags: List[str]) -> bool:
    if not _run_tag_filter:
        return True
    return any(t in _run_tag_filter for t in effective_tags)


async def _run_suite(
    suite: TestSuite,
    path: str,
    suite_path: List[TestSuite],
    result: RunResult,
    start_time: float,
) -> None:
    import time
    if not _should_run_suite(suite):
        return

    full_path = f"{path} > {suite.name}" if path else suite.name
    next_suite_path = suite_path + [suite]

    await _run_hooks(suite.before_all)

    for test in suite.tests:
        effective_tags = _get_effective_tags(next_suite_path, test)
        tag_match = _test_matches_tag_filter(effective_tags)
        run_test = not test.skip and (not _has_only or test.only) and tag_match
        global _current_steps
        _current_steps = []
        test_start = time.time()

        if not run_test:
            result.skipped += 1
            result.total += 1
            result.skipped_tests.append(
                TestResultEntry(
                    suite=full_path,
                    test=test.name,
                    duration=0,
                    file=_current_run_file,
                    tags=effective_tags or None,
                )
            )
            continue

        result.total += 1
        _current_steps.append("Test case started")
        try:
            await _run_hooks(suite.before_each)
            await _run_fn_async(test.fn)
            await _run_hooks(suite.after_each)
            result.passed += 1
            result.passed_tests.append(
                TestResultEntry(
                    suite=full_path,
                    test=test.name,
                    duration=(time.time() - test_start) * 1000,
                    steps=_current_steps.copy() if _current_steps else None,
                    file=_current_run_file,
                    tags=effective_tags or None,
                )
            )
        except Exception as err:
            duration = (time.time() - test_start) * 1000
            try:
                await _run_hooks(suite.after_each)
            except Exception:
                pass
            result.failed += 1
            result.errors.append({
                "suite": full_path,
                "test": test.name,
                "error": err,
                "duration": duration,
                "steps": _current_steps.copy() if _current_steps else None,
                "file": _current_run_file,
                "tags": effective_tags or None,
            })

    for child in suite.suites:
        await _run_suite(child, full_path, next_suite_path, result, start_time)

    await _run_hooks(suite.after_all)


def run(options: Optional[dict] = None) -> RunResult:
    """Run all registered suites. options: tags=[], file=''."""
    import time
    global _run_tag_filter, _current_run_file
    opts = options or {}
    _run_tag_filter = opts.get("tags") or []
    _current_run_file = opts.get("file")

    result = RunResult()
    start = time.time()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_suite(_root_suite, "", [], result, start))
    finally:
        loop.close()
    result.duration = (time.time() - start) * 1000
    return result


def get_root_suite() -> TestSuite:
    return _root_suite

"""
CSTesting — Python testing framework (port of EasyTesting/CSTesting Node).
Usage: from cstesting import describe, it, expect, before_all, after_all, create_browser, request
"""

from .runner import (
    describe,
    it,
    before_all,
    after_all,
    beforeEach,
    afterEach,
    before_each,
    after_each,
    run,
    reset_runner,
    step,
)
from .assertions import expect, AssertionError
from .api_request import request, ResponseAssertions, ApiResponse
from .config_runner import run_config_file
from .config_parser import parse_config_file, ParsedConfig, ConfigStep, ConfigTestCase
from .report import write_report, generate_html_report
from .types import RunResult

__all__ = [
    "describe",
    "it",
    "before_all",
    "after_all",
    "beforeEach",
    "afterEach",
    "before_each",
    "after_each",
    "run",
    "reset_runner",
    "step",
    "expect",
    "AssertionError",
    "request",
    "ResponseAssertions",
    "ApiResponse",
    "run_config_file",
    "parse_config_file",
    "ParsedConfig",
    "ConfigStep",
    "ConfigTestCase",
    "write_report",
    "generate_html_report",
    "RunResult",
]

# Lazy import for browser (optional Playwright)
def create_browser(*args, **kwargs):
    """Launch browser. Requires: pip install playwright && playwright install"""
    from .browser import create_browser as _create_browser
    return _create_browser(*args, **kwargs)

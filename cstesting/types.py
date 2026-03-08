"""
Internal types for the test runner.
"""
from typing import Callable, List, Optional, Any, Dict
from dataclasses import dataclass, field


TestFn = Callable[[], Any]  # void or Awaitable[None]
HookFn = Callable[[], Any]


@dataclass
class TestCase:
    name: str
    fn: TestFn
    only: bool = False
    skip: bool = False
    tags: Optional[List[str]] = None


@dataclass
class TestSuite:
    name: str
    suites: List["TestSuite"] = field(default_factory=list)
    tests: List[TestCase] = field(default_factory=list)
    before_all: List[HookFn] = field(default_factory=list)
    after_all: List[HookFn] = field(default_factory=list)
    before_each: List[HookFn] = field(default_factory=list)
    after_each: List[HookFn] = field(default_factory=list)
    only: bool = False
    skip: bool = False
    tags: Optional[List[str]] = None


@dataclass
class TestResultEntry:
    suite: str
    test: str
    duration: Optional[float] = None
    steps: Optional[List[str]] = None
    file: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class RunResult:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total: int = 0
    duration: float = 0.0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    passed_tests: List[TestResultEntry] = field(default_factory=list)
    skipped_tests: List[TestResultEntry] = field(default_factory=list)

"""
Simple assertion library (expect-style API).
Similar to Jest/Cypress expect.
"""

import re
import inspect
import asyncio
from typing import Any, Optional, Union


class AssertionError(Exception):
    def __init__(
        self,
        message: str,
        expected: Optional[Any] = None,
        actual: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.expected = expected
        self.actual = actual


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class ExpectApi:
    def __init__(self, actual: Any, negate: bool = False):
        self._actual = actual
        self._negate = negate

    def _wrap(self, pass_: bool, fail_message: str, pass_message: Optional[str] = None):
        ok = not pass_ if self._negate else pass_
        msg = fail_message if not ok else (pass_message or fail_message)
        if not ok:
            raise AssertionError(msg, getattr(self, "_expected", None), self._actual)

    def to_be(self, expected: Any) -> None:
        self._expected = expected
        self._wrap(
            self._actual is expected,
            f"Expected {self._actual!r} to be {expected!r}",
            f"Expected not to be {expected!r}",
        )

    def to_equal(self, expected: Any) -> None:
        import json
        self._expected = expected
        try:
            a_str = json.dumps(self._actual, sort_keys=True, default=str)
            e_str = json.dumps(expected, sort_keys=True, default=str)
            pass_ = a_str == e_str
        except (TypeError, ValueError):
            pass_ = self._actual == expected
            a_str, e_str = repr(self._actual), repr(expected)
        self._wrap(
            pass_,
            f"Expected {a_str} to equal {e_str}",
            f"Expected not to equal {e_str}",
        )

    def to_be_truthy(self) -> None:
        self._wrap(bool(self._actual), f"Expected {self._actual!r} to be truthy", f"Expected {self._actual!r} to be falsy")

    def to_be_falsy(self) -> None:
        self._wrap(not self._actual, f"Expected {self._actual!r} to be falsy", f"Expected {self._actual!r} to be truthy")

    def to_be_null(self) -> None:
        self._wrap(self._actual is None, f"Expected {self._actual!r} to be null", "Expected not to be null")

    def to_be_defined(self) -> None:
        self._wrap(self._actual is not None, "Expected value to be defined", "Expected value to be undefined")

    def to_be_undefined(self) -> None:
        self._wrap(self._actual is None, "Expected value to be undefined", "Expected value to be defined")

    def to_throw(self, expected_message: Optional[Union[str, re.Pattern]] = None) -> None:
        if not callable(self._actual):
            raise AssertionError("Expected value to be a callable", None, self._actual)
        threw = False
        thrown = None
        try:
            result = self._actual()
            if inspect.iscoroutine(result):
                _run_async(result)
        except Exception as e:
            threw = True
            thrown = e
        self._wrap(threw, "Expected function to throw", "Expected function not to throw")
        if expected_message is not None and threw and thrown is not None:
            msg = str(thrown)
            if isinstance(expected_message, str):
                match = msg == expected_message
            else:
                match = bool(expected_message.search(msg))
            if not match:
                raise AssertionError(f"Expected throw message to match, got: {msg}", expected_message, msg)

    def to_be_greater_than(self, n: float) -> None:
        try:
            val = float(self._actual)
        except (TypeError, ValueError):
            val = float("nan")
        self._wrap(
            not (val != val) and val > n,
            f"Expected {self._actual} to be greater than {n}",
            f"Expected {self._actual} not to be greater than {n}",
        )

    def to_be_less_than(self, n: float) -> None:
        try:
            val = float(self._actual)
        except (TypeError, ValueError):
            val = float("nan")
        self._wrap(
            not (val != val) and val < n,
            f"Expected {self._actual} to be less than {n}",
            f"Expected {self._actual} not to be less than {n}",
        )

    def to_contain(self, item: Any) -> None:
        if isinstance(self._actual, (list, tuple)):
            has = item in self._actual
        elif isinstance(self._actual, str):
            has = str(item) in self._actual
        else:
            has = False
        self._wrap(
            has,
            f"Expected {self._actual!r} to contain {item!r}",
            f"Expected {self._actual!r} not to contain {item!r}",
        )

    def to_have_length(self, n: int) -> None:
        length = getattr(self._actual, "length", None) or getattr(self._actual, "__len__", lambda: None)()
        if length is None and hasattr(self._actual, "__len__"):
            length = len(self._actual)
        self._wrap(
            length == n,
            f"Expected length {length} to be {n}",
            f"Expected length not to be {n}",
        )

    @property
    def not_(self) -> "ExpectApi":
        """Use expect(x).not_.to_be(y) for negated assertions (Python reserves 'not')."""
        return ExpectApi(self._actual, negate=True)


def expect(actual: Any) -> ExpectApi:
    return ExpectApi(actual)

"""
API testing — Rest-Assured style fluent request and assertions.
"""
import json
import re
import urllib.request
import urllib.error
import ssl
from typing import Any, Optional, Dict, Union
from dataclasses import dataclass

from .assertions import AssertionError


@dataclass
class ApiResponse:
    status: int
    headers: Dict[str, str]
    body: Any
    raw_body: str


def _get_by_path(obj: Any, path: str) -> Any:
    """Get a value from an object by dot path, e.g. 'user.name' or 'items[0].id'."""
    path = path.replace("$.", "").strip()
    if not path:
        return obj
    parts = re.split(r"\.(?![^\[]*\])", path)
    current = obj
    for part in parts:
        if current is None:
            return None
        m = re.match(r"^(\w+)\[(\d+)\]$", part)
        if m:
            key, idx = m.group(1), int(m.group(2))
            current = (current or {}).get(key)
            current = current[idx] if isinstance(current, list) and 0 <= idx < len(current) else None
        else:
            current = (current or {}).get(part)
    return current


def _request(
    method: str,
    url: str,
    body: Optional[Any] = None,
    options: Optional[Dict] = None,
) -> ApiResponse:
    options = options or {}
    headers = dict(options.get("headers") or {})
    timeout = options.get("timeout", 30)

    if body is not None:
        data = json.dumps(body).encode("utf-8") if not isinstance(body, str) else body.encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
        headers["Content-Length"] = str(len(data))
    else:
        data = None

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    ctx = ssl.create_default_context()
    res = None
    raw = ""
    try:
        res = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raw = res.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        res = e
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
    except Exception as e:
        if "timeout" in str(e).lower():
            raise AssertionError("Request timeout", None, None) from e
        raise

    out_headers = {}
    for k, v in res.headers.items():
        out_headers[k.lower()] = v if isinstance(v, str) else (v[0] if v else "")

    parsed = raw
    ct = out_headers.get("content-type", "")
    if "application/json" in ct and raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            pass

    status = getattr(res, "code", getattr(res, "status", 0))
    return ApiResponse(status=status, headers=out_headers, body=parsed, raw_body=raw)


class ResponseAssertions:
    def __init__(self, res: ApiResponse):
        self._res = res

    def expect_status(self, status: int) -> "ResponseAssertions":
        if self._res.status != status:
            raise AssertionError(
                f"Expected status {status}, got {self._res.status}. Body: {self._res.raw_body[:200]}",
                status,
                self._res.status,
            )
        return self

    def expect_header(self, name: str, value: Union[str, re.Pattern]) -> "ResponseAssertions":
        key = name.lower()
        actual = self._res.headers.get(key)
        if actual is None:
            raise AssertionError(f'Expected header "{name}" to be present', value, None)
        if isinstance(value, str):
            if actual != value:
                raise AssertionError(
                    f'Expected header "{name}" to be {value!r}, got {actual!r}',
                    value,
                    actual,
                )
        else:
            if not value.search(actual):
                raise AssertionError(
                    f'Expected header "{name}" to match {value}, got {actual}',
                    value,
                    actual,
                )
        return self

    def expect_body(self, expected: Any) -> "ResponseAssertions":
        if json.dumps(self._res.body, sort_keys=True, default=str) != json.dumps(
            expected, sort_keys=True, default=str
        ):
            raise AssertionError(
                f"Expected body {expected!r}, got {self._res.body!r}",
                expected,
                self._res.body,
            )
        return self

    def expect_json(self, path: str, value: Any) -> "ResponseAssertions":
        actual = _get_by_path(self._res.body, path)
        if actual != value:
            raise AssertionError(
                f'Expected body at "{path}" to be {value!r}, got {actual!r}',
                value,
                actual,
            )
        return self

    def get_response(self) -> ApiResponse:
        return self._res


def _fluent(
    method: str, url: str, body: Optional[Any] = None, options: Optional[Dict] = None
) -> ResponseAssertions:
    return ResponseAssertions(_request(method, url, body, options))


def verify_status(
    method: str,
    url: str,
    expected_status: int,
    body: Optional[Any] = None,
    options: Optional[Dict] = None,
) -> ApiResponse:
    res = _request(method, url, body, options)
    if res.status != expected_status:
        raise AssertionError(
            f"Expected status {expected_status}, got {res.status}. Body: {res.raw_body[:200]}",
            expected_status,
            res.status,
        )
    return res


class RequestApi:
    def get(self, url: str, options: Optional[Dict] = None) -> ResponseAssertions:
        return _fluent("GET", url, None, options)

    def post(
        self, url: str, body: Optional[Any] = None, options: Optional[Dict] = None
    ) -> ResponseAssertions:
        return _fluent("POST", url, body, options)

    def put(
        self, url: str, body: Optional[Any] = None, options: Optional[Dict] = None
    ) -> ResponseAssertions:
        return _fluent("PUT", url, body, options)

    def patch(
        self, url: str, body: Optional[Any] = None, options: Optional[Dict] = None
    ) -> ResponseAssertions:
        return _fluent("PATCH", url, body, options)

    def delete(self, url: str, options: Optional[Dict] = None) -> ResponseAssertions:
        return _fluent("DELETE", url, None, options)

    def verify_status(
        self,
        method: str,
        url: str,
        expected_status: int,
        body: Optional[Any] = None,
        options: Optional[Dict] = None,
    ) -> ApiResponse:
        return verify_status(method, url, expected_status, body, options)

    def request(
        self,
        method: str,
        url: str,
        body: Optional[Any] = None,
        options: Optional[Dict] = None,
    ) -> ApiResponse:
        return _request(method, url, body, options)


request = RequestApi()

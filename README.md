# CSTesting (Python)

Python port of **CSTesting** — a simple testing framework with a test runner, assertions, API testing, and browser automation (Playwright).

## Install

```bash
# Core only (describe, it, expect, request — no browser)
pip install -e .

# With browser support (Playwright)
pip install -e ".[browser]"
playwright install chromium
```

## Quick start

**1. Create a test file** (e.g. `math_test.py`):

```python
from cstesting import describe, it, expect

def _suite():
    it("adds numbers", lambda: expect(1 + 1).to_be(2))
    it("compares objects", lambda: expect({"a": 1}).to_equal({"a": 1}))

describe("Math", _suite)
```

**2. Run tests:**

```bash
python -m cstesting
python -m cstesting "**/*.test.py"
python -m cstesting tests/
python -m cstesting example/math_test.py
```

## API

### Test structure

- **`describe(name, fn)`** — define a suite
- **`it(name, fn)`** — define a test (sync or async)
- **`describe.only(name, fn)`** / **`it.only(name, fn)`** — run only this suite/test
- **`describe.skip(name, fn)`** / **`it.skip(name, fn)`** — skip

### Hooks

- **`before_all(fn)`** — run once before all tests in the suite
- **`after_all(fn)`** — run once after all tests
- **`beforeEach(fn)`** / **`afterEach(fn)`** — run before/after each test

### Assertions (`expect(value)`)

| Matcher | Example |
|--------|--------|
| `to_be(expected)` | strict equality |
| `to_equal(expected)` | deep equality |
| `to_be_truthy()` / `to_be_falsy()` | boolean |
| `to_be_null()` / `to_be_defined()` / `to_be_undefined()` | null/defined |
| `to_throw(message?)` | expect(fn).to_throw() |
| `to_be_greater_than(n)` / `to_be_less_than(n)` | numbers |
| `to_contain(item)` | list or string |
| `to_have_length(n)` | length |
| `expect(x).not_.to_be(y)` | negate (use `not_` in Python) |

### API testing (Rest-Assured style)

```python
from cstesting import describe, it, request

def _suite():
    it("GET", lambda: (
        request.get("https://api.example.com/users/1")
        .expect_status(200)
        .expect_json("name", "John")
    ))
    it("verifyStatus", lambda: request.verify_status("GET", "https://api.example.com/health", 200))

describe("API", _suite)
```

- **`request.get(url)`**, **`request.post(url, body)`**, **`request.put`**, **`request.patch`**, **`request.delete`**
- Chain: **`.expect_status(200)`**, **`.expect_header('content-type', pattern)`**, **`.expect_body({})`**, **`.expect_json('path', value)`**
- **`request.verify_status(method, url, expected_status, body=None)`**
- **`res.get_response()`** for raw `ApiResponse` (status, headers, body, raw_body)

### Browser automation (optional)

Requires: `pip install playwright && playwright install chromium`

```python
import asyncio
from cstesting import describe, it, expect, before_all, after_all, create_browser

browser = None

def _suite():
    def _before():
        global browser
        browser = asyncio.get_event_loop().run_until_complete(create_browser(headless=True))
    def _after():
        global browser
        if browser:
            asyncio.get_event_loop().run_until_complete(browser.close())

    before_all(_before)
    after_all(_after)

    async def _test():
        await browser.goto("https://example.com")
        html = await browser.content()
        expect(html).to_contain("Example Domain")

    it("loads the page", _test)

describe("Browser", _suite)
```

- **`create_browser(headless=True, browser='chromium')`** — async, returns browser API
- **`browser.goto(url)`**, **`browser.click(selector)`**, **`browser.type(selector, text)`**
- **`browser.locator(selector)`** → **`.click()`**, **`.type(text)`**, **`.first`**, **`.nth(n)`**
- **`browser.wait_for_selector(selector)`**, **`browser.content()`**, **`browser.evaluate(expr)`**
- **`browser.check(selector)`**, **`browser.uncheck(selector)`**, **`browser.select(selector, option)`**

### Config-driven tests

Run flows from a `.conf` file without writing code:

```conf
# Login (one test case)
headed=true
goto:https://example.com/login
username:#email=value:user@test.com
password:#password=value:secret
click=button[type="submit"]
```

```bash
python -m cstesting run login.conf
python -m cstesting login.conf --headed
```

Programmatic: **`from cstesting import run_config_file; result = run_config_file('login.conf')`**

### Init (Page Object Model)

```bash
python -m cstesting init
```

Creates `pages/` and `tests/` with sample HomePage and test.

### Report

After a run, an HTML report is written to **`report/report.html`** (searchable, expandable steps, errors).

## Programmatic run

```python
from cstesting import describe, it, expect, run

def _suite():
    it("works", lambda: expect(1).to_be(1))

describe("My tests", _suite)

result = run()
print(result)  # passed, failed, skipped, total, duration, errors
```

## Publish to PyPI

1. **Create accounts** (if needed):
   - [PyPI](https://pypi.org/account/register/)
   - Optional: [Test PyPI](https://test.pypi.org/account/register/) for testing first

2. **Install build tools:**
   ```bash
   python -m pip install build twine
   ```
   (If `pip` or `python` isn’t recognized, use the full path to your Python executable, or on Windows try `py -m pip install build twine`.)

3. **Build the package:**
   ```bash
   python -m build
   ```
   On Windows, if `python` isn’t recognized, use **`py -m build`** instead.
   This creates `dist/cstesting-0.1.0.tar.gz` and a wheel.

4. **Upload to PyPI:**
   ```bash
   python -m twine upload dist/*
   ```
   On Windows, if `python` isn’t recognized, use **`py -m twine upload dist/*`**.
   Use your PyPI username and password (or [API token](https://pypi.org/manage/account/token/)).

   To try Test PyPI first:
   ```bash
   python -m twine upload --repository testpypi dist/*
   ```

5. **Bump version** in `pyproject.toml` for each new release, then repeat steps 3–4.

## License

MIT. Port of [EasyTesting](https://github.com/lokesh771988/EasyTesting) (Node.js) to Python.

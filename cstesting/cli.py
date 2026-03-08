#!/usr/bin/env python3
"""
CSTesting CLI — discover and run test files, run config files, init (POM scaffold).
Usage: python -m cstesting [pattern]  |  python -m cstesting init  |  python -m cstesting run login.conf
"""
import os
import sys
import glob
import importlib.util
from pathlib import Path
from typing import Optional

from .runner import run, reset_runner
from .assertions import AssertionError
from .report import write_report
from .config_runner import run_config_file
from .types import RunResult


TEST_EXTENSIONS = (".test.py", ".spec.py")


def _is_test_file(name: str) -> bool:
    return any(name.endswith(ext) for ext in TEST_EXTENSIONS)


def _get_templates_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "templates"


def init() -> None:
    """Create pages/ and tests/ with Page Object Model sample code."""
    cwd = Path.cwd()
    templates = _get_templates_dir()
    if not templates.exists():
        print("Templates not found. Run init from a project that has cstesting installed.")
        sys.exit(1)
    pages_dir = cwd / "pages"
    tests_dir = cwd / "tests"
    pages_dir.mkdir(exist_ok=True)
    tests_dir.mkdir(exist_ok=True)
    for dest_name, subdir in [("HomePage.py", "pages"), ("home_test.py", "tests")]:
        src = templates / subdir / dest_name
        if not src.exists():
            src = templates / dest_name
        if src.exists():
            dest = pages_dir / dest_name if subdir == "pages" else tests_dir / dest_name
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            print("  Created:", dest.relative_to(cwd))
    print("\nPage Object Model (POM) structure ready:\n  pages/  – page objects\n  tests/  – test files (*.test.py)\n\nRun: python -m cstesting tests/\n")


def find_test_files(pattern: str, cwd: Path) -> list:
    if "*" in pattern or pattern.endswith(".py"):
        files = []
        for path in cwd.rglob("*"):
            if path.is_file() and _is_test_file(path.name):
                files.append(str(path))
        return sorted(files)
    resolved = cwd / pattern
    if resolved.is_file():
        return [str(resolved)]
    if resolved.is_dir():
        files = []
        for path in resolved.rglob("*"):
            if path.is_file() and _is_test_file(path.name):
                files.append(str(path))
        return sorted(files)
    return []


def load_test_file(file_path: str) -> None:
    """Import the test module so it registers describe/it."""
    path = Path(file_path).resolve()
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)


def format_error(err: Exception) -> str:
    if isinstance(err, AssertionError):
        parts = [err.args[0] if err.args else str(err)]
        if getattr(err, "actual", None) is not None:
            parts.append(f"  Actual: {err.actual}")
        if getattr(err, "expected", None) is not None:
            parts.append(f"  Expected: {err.expected}")
        return "\n".join(parts)
    return "".join(__import__("traceback").format_exception(type(err), err, err.__traceback__))


def resolve_config_path(config_path: str) -> Optional[str]:
    cwd = Path.cwd()
    resolved = cwd / config_path
    if resolved.is_file():
        return str(resolved)
    if "/" not in config_path and "\\" not in config_path:
        parent = cwd.parent / config_path
        if parent.is_file():
            return str(parent)
    return None


def run_config(config_path: str, headless: bool = True) -> None:
    resolved = resolve_config_path(config_path)
    if not resolved:
        print(f"Config file not found: {config_path}")
        sys.exit(1)
    print(f"Running config: {config_path}\n")
    result = run_config_file(resolved, {"headless": headless})
    if result.errors:
        print("\nFailed test(s):")
        for e in result.errors:
            print(f"  ✗ {e['suite']} > {e['test']}")
            print(f"    {(e['error'].args[0] if e['error'].args else str(e['error']))}")
    print("\n" + "─" * 50)
    print(f"  Passed: {result.passed}  Failed: {result.failed}  Total: {result.total}  ({result.duration:.0f}ms)")
    report_path = write_report(result, report_dir="report", filename="report.html")
    print(f"  Report: {report_path}")
    if result.failed > 0:
        sys.exit(1)


def main() -> None:
    argv = sys.argv[1:]
    cwd = Path.cwd()

    if "init" in argv:
        init()
        return

    if "run" in argv:
        idx = argv.index("run")
        config_path = argv[idx + 1] if idx + 1 < len(argv) else None
        if not config_path:
            print("Usage: python -m cstesting run <config.conf> [--headed]")
            sys.exit(1)
        headed = "--headed" in argv
        run_config(config_path, headless=not headed)
        return

    # Direct config: python -m cstesting login.conf
    arg = None
    for a in argv:
        if a.startswith("-"):
            continue
        if a.endswith(".conf") or a.endswith(".config"):
            if resolve_config_path(a):
                arg = a
                break
        arg = a
        break

    if arg and (arg.endswith(".conf") or arg.endswith(".config")):
        if resolve_config_path(arg):
            run_config(arg, headless="--headed" not in argv)
            return

    pattern = arg or "**/*.test.py"
    test_files = find_test_files(pattern, cwd)
    if not test_files:
        print("No test files found. Create files matching *.test.py or *.spec.py — or run: python -m cstesting path/to/test.py")
        sys.exit(0)

    total_result = RunResult()
    for file_path in test_files:
        reset_runner()
        try:
            load_test_file(file_path)
        except Exception as err:
            print(f"Failed to load {file_path}:", err)
            sys.exit(1)
        rel = Path(file_path).relative_to(cwd)
        result = run({"file": str(rel)})
        total_result.passed += result.passed
        total_result.failed += result.failed
        total_result.skipped += result.skipped
        total_result.total += result.total
        total_result.duration += result.duration
        total_result.errors.extend(result.errors)
        total_result.passed_tests.extend(result.passed_tests or [])
        total_result.skipped_tests.extend(result.skipped_tests or [])
        print(f"\n {rel}")
        for e in result.errors:
            print(f"  ✗ {e['suite']} > {e['test']}")
            for line in format_error(e["error"]).splitlines():
                print("    ", line)

    print("\n" + "─" * 50)
    print(f"  Passed: {total_result.passed}  Failed: {total_result.failed}  Skipped: {total_result.skipped}  Total: {total_result.total}  ({total_result.duration:.0f}ms)")
    report_path = write_report(total_result, report_dir="report", filename="report.html")
    print(f"  Report: {report_path}")
    if total_result.failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

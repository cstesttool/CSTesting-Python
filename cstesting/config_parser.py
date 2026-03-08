"""
Config file parser for config-driven tests.
Format: one step per line; # starts a test case; goto:, type, click=, etc.
"""
import re
from pathlib import Path
from typing import List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ConfigStep:
    action: str
    # action-specific fields (use getattr or match on action)
    url: Optional[str] = None
    label: Optional[str] = None
    locator: Optional[str] = None
    value: Optional[str] = None
    ms: Optional[int] = None
    path: Optional[str] = None
    full_page: Optional[bool] = None
    element: Optional[str] = None
    index: Optional[int] = None
    selector: Optional[str] = None
    source_locator: Optional[str] = None
    option: Optional[dict] = None
    behavior: Optional[str] = None
    prompt_text: Optional[str] = None
    expected: Optional[str] = None
    text_selector: Optional[str] = None
    attr_selector: Optional[str] = None
    attribute_name: Optional[str] = None
    baseline_path: Optional[str] = None
    threshold: Optional[float] = None


@dataclass
class ConfigTestCase:
    test_case_name: str
    steps: List[ConfigStep] = field(default_factory=list)


@dataclass
class ParsedConfig:
    name: str
    headless: bool = True
    test_cases: List[ConfigTestCase] = field(default_factory=list)


def _parse_line(line: str) -> Optional[ConfigStep]:
    trimmed = line.strip()
    if not trimmed or trimmed.startswith("#"):
        return None
    if re.match(r"^headless=(true|false)$", trimmed, re.I) or re.match(
        r"^headed=(true|false)$", trimmed, re.I
    ):
        return None

    # click=<locator>
    m = re.match(r"^click=(.+)$", trimmed)
    if m:
        return ConfigStep(action="click", locator=m.group(1).strip())

    # goto:<url>
    m = re.match(r"^goto:(.+)$", trimmed)
    if m:
        return ConfigStep(action="goto", url=m.group(1).strip())

    # wait:2000 or wait:2
    m = re.match(r"^wait:(\d+)$", trimmed)
    if m:
        ms = int(m.group(1))
        if 0 < ms < 100:
            ms *= 1000
        return ConfigStep(action="wait", ms=ms)

    # <label>:<locator>=value:<text>
    if "=value:" in trimmed:
        idx = trimmed.index("=value:")
        before, value = trimmed[:idx], trimmed[idx + 7 :]
        if ":" in before:
            label, locator = before.split(":", 1)
            return ConfigStep(
                action="type",
                label=label.strip(),
                locator=locator.strip(),
                value=value.strip(),
            )

    # check=, uncheck=
    m = re.match(r"^check=(.+)$", trimmed)
    if m:
        return ConfigStep(action="check", locator=m.group(1).strip())
    m = re.match(r"^uncheck=(.+)$", trimmed)
    if m:
        return ConfigStep(action="uncheck", locator=m.group(1).strip())

    # switchTab=0
    m = re.match(r"^switchTab=(\d+)$", trimmed)
    if m:
        return ConfigStep(action="switchTab", index=int(m.group(1)))

    # frame=main or frame=selector
    m = re.match(r"^frame=(.+)$", trimmed)
    if m:
        return ConfigStep(action="frame", selector=m.group(1).strip())

    # select=<locator>=value:x or =label:Text
    m = re.match(r"^select=(.+)$", trimmed)
    if m:
        rest = m.group(1).strip()
        if "=value:" in rest:
            locator, val = rest.split("=value:", 1)
            return ConfigStep(
                action="select", locator=locator.strip(), option={"value": val.strip()}
            )
        if "=label:" in rest:
            locator, lab = rest.split("=label:", 1)
            return ConfigStep(
                action="select", locator=locator.strip(), option={"label": lab.strip()}
            )

    # close
    if re.match(r"^closeBrowser?$", trimmed, re.I):
        return ConfigStep(action="close")

    # assertText=expected or assertText=selector=expected
    m = re.match(r"^assertText=(.+)$", trimmed, re.I)
    if m:
        rest = m.group(1).strip()
        if "=" not in rest:
            return ConfigStep(action="verifyText", expected=rest)
        eq = rest.rfind("=")
        selector, expected = rest[:eq].strip(), rest[eq + 1 :].strip()
        return ConfigStep(action="verifyText", expected=expected, selector=selector)

    return None


def _parse_headless_option(line: str) -> Optional[bool]:
    trimmed = line.strip()
    if not trimmed or trimmed.startswith("#"):
        return None
    m = re.match(r"^headless=(true|false)$", trimmed, re.I)
    if m:
        return m.group(1).lower() == "true"
    m = re.match(r"^headed=(true|false)$", trimmed, re.I)
    if m:
        return m.group(1).lower() != "true"
    return None


def parse_config_file(file_path: str) -> ParsedConfig:
    path = Path(file_path)
    name = path.name
    content = path.read_text(encoding="utf-8")
    test_cases: List[ConfigTestCase] = []
    headless = True
    current_name = name
    current_steps: List[ConfigStep] = []

    def push_current():
        if current_steps:
            test_cases.append(ConfigTestCase(test_case_name=current_name, steps=current_steps.copy()))
            current_steps.clear()

    for line in content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("#"):
            push_current()
            current_name = trimmed[1:].strip() or "Unnamed"
            continue
        opt = _parse_headless_option(line)
        if opt is not None:
            headless = opt
            continue
        step = _parse_line(line)
        if step:
            current_steps.append(step)

    push_current()
    return ParsedConfig(name=name, headless=headless, test_cases=test_cases)

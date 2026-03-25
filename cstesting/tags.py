"""
Test tag helpers: normalize @sanity / sanity, parse @tags from titles, merge with explicit tags.
Aligned with CSTesting Node (tags.ts).
"""
import re
from typing import List, Optional


def normalize_test_tag(t: str) -> str:
    return t.strip().lstrip("@").lower()


def normalize_test_tag_list(tags: Optional[List[str]]) -> Optional[List[str]]:
    if not tags:
        return None
    u = list(dict.fromkeys(normalize_test_tag(x) for x in tags if normalize_test_tag(x)))
    return u if u else None


# @word at start or after whitespace (avoids user@domain)
_TITLE_TAG_RE = re.compile(r"(?:^|\s)@([a-zA-Z][\w-]*)")


def tags_from_test_title(name: str) -> List[str]:
    out: List[str] = []
    for m in _TITLE_TAG_RE.finditer(name):
        nt = normalize_test_tag(m.group(1))
        if nt:
            out.append(nt)
    return out


def merge_test_tags(name: str, explicit: Optional[List[str]] = None) -> Optional[List[str]]:
    merged = list(
        dict.fromkeys(
            tags_from_test_title(name)
            + [normalize_test_tag(x) for x in (explicit or []) if normalize_test_tag(x)]
        )
    )
    return merged if merged else None

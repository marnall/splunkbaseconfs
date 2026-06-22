#!/usr/bin/env python3
"""
i18n key audit (Issue #38).

Scans the app for `data-key="..."` references in dashboard XML and JS, and
the `_i18n['en-US' | 'zh-CN']` dictionaries in `appserver/static/mcp_utils.js`,
and reports:

  * keys referenced but missing from BOTH dictionaries (hard error)
  * keys referenced but missing from one dictionary (soft warning — DOM hook
    falls back to the inline default text, but Chinese / English users will
    see un-translated text)
  * keys defined but never referenced (dead-code in the dictionary)

Exit code 0 if no missing keys, 1 if any key is missing from both dicts,
2 if at least one dictionary is incomplete.

Run it from the app root:
    python3 bin/i18n_audit.py

Or via Splunk's Python:
    $SPLUNK_HOME/bin/splunk cmd python3 \\
        $SPLUNK_HOME/etc/apps/AI_Query_Assistant_for_Splunk/bin/i18n_audit.py
"""
from __future__ import annotations
import os
import re
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent

DATA_KEY_RE = re.compile(r'data-key="([^"]+)"')
# Match a real i18n key: dotted alphanum/underscore, no spaces/quotes/+,
# at least one dot, doesn't start/end with .  (rejects JS template
# fragments like `' + var + '` and doc placeholders like `license.xxx`).
KEY_SHAPE_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)+$')
PLACEHOLDER_KEYS = {'license.xxx', 'license.yyy', 'foo.bar'}
# Match `'key.subkey': '...'` lines inside the i18n dict. Non-greedy on key,
# stops at first quote, comma or colon.
DICT_KEY_RE = re.compile(r"^\s*'([a-zA-Z][a-zA-Z0-9_.]*)'\s*:")

VIEWS_DIR = APP_ROOT / 'default' / 'data' / 'ui' / 'views'
STATIC_DIR = APP_ROOT / 'appserver' / 'static'
UTILS = STATIC_DIR / 'mcp_utils.js'


def _valid_key(k: str) -> bool:
    return bool(KEY_SHAPE_RE.match(k)) and k not in PLACEHOLDER_KEYS


def collect_referenced_keys() -> set[str]:
    keys: set[str] = set()
    for path in list(VIEWS_DIR.rglob('*.xml')) + list(STATIC_DIR.rglob('*.js')):
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for k in DATA_KEY_RE.findall(text):
            if _valid_key(k):
                keys.add(k)
        # Also pick up mcpUtils.t('key', ...) calls in JS so dictionary-only
        # keys (like 'history.loading') are counted as referenced.
        for k in re.findall(r"mcpUtils\.t\(\s*'([a-zA-Z][a-zA-Z0-9_.]*)'", text):
            if _valid_key(k):
                keys.add(k)
        for k in re.findall(r"\bt\(\s*'([a-zA-Z][a-zA-Z0-9_.]*)'", text):
            if _valid_key(k):
                keys.add(k)
    return keys


def collect_dict_keys() -> tuple[set[str], set[str]]:
    """Return (en_keys, zh_keys) parsed from mcp_utils.js _i18n object."""
    text = UTILS.read_text(encoding='utf-8')
    # Find each section by anchor: `'zh-CN': {` and `'en-US': {`. We then
    # walk lines until the matching `}` at brace depth 0.
    zh_keys: set[str] = set()
    en_keys: set[str] = set()

    for label, target in (("'zh-CN':", zh_keys), ("'en-US':", en_keys)):
        idx = text.find(label)
        if idx < 0:
            continue
        # Find opening `{` after the label.
        brace_open = text.find('{', idx)
        if brace_open < 0:
            continue
        depth = 0
        i = brace_open
        while i < len(text):
            ch = text[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    section = text[brace_open + 1:i]
                    for line in section.splitlines():
                        m = DICT_KEY_RE.match(line)
                        if m:
                            target.add(m.group(1))
                    break
            i += 1

    return en_keys, zh_keys


def main() -> int:
    referenced = collect_referenced_keys()
    en_keys, zh_keys = collect_dict_keys()

    missing_both = sorted(k for k in referenced if k not in en_keys and k not in zh_keys)
    missing_en = sorted(k for k in referenced if k not in en_keys and k in zh_keys)
    missing_zh = sorted(k for k in referenced if k not in zh_keys and k in en_keys)
    unused = sorted((en_keys | zh_keys) - referenced)

    print(f"i18n keys: referenced={len(referenced)}  en-US={len(en_keys)}  zh-CN={len(zh_keys)}")
    print()

    rc = 0
    if missing_both:
        rc = max(rc, 1)
        print(f"[FAIL] {len(missing_both)} key(s) referenced but missing in BOTH dictionaries:")
        for k in missing_both:
            print(f"  - {k}")
        print()
    if missing_en:
        rc = max(rc, 2)
        print(f"[WARN] {len(missing_en)} key(s) missing from en-US:")
        for k in missing_en:
            print(f"  - {k}")
        print()
    if missing_zh:
        rc = max(rc, 2)
        print(f"[WARN] {len(missing_zh)} key(s) missing from zh-CN:")
        for k in missing_zh:
            print(f"  - {k}")
        print()
    if unused:
        # Unused entries are not a hard failure but worth reporting.
        print(f"[INFO] {len(unused)} key(s) defined but never referenced (candidates for removal):")
        # Don't list 200+ keys if huge; cap to first 30.
        for k in unused[:30]:
            print(f"  - {k}")
        if len(unused) > 30:
            print(f"  ... and {len(unused) - 30} more")
        print()

    if rc == 0:
        print("[OK] All referenced keys are present in both en-US and zh-CN dictionaries.")
    return rc


if __name__ == '__main__':
    sys.exit(main())

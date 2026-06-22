"""Shared `.conf.spec` finder + parser (v1.5.0 — Data Foundation).

Splunk ships an authoritative spec for every conf file as a `*.conf.spec` under
`$SPLUNK_HOME/etc/system/README/` (version-matched to the running install), plus
per-app specs under `etc/apps/<app>/README/`. There is **no REST endpoint** for
these, so we read them from disk. This module is the single place that finds and
parses them; both the `splunk-conf-spec` knowledge connector and the
`splunk_validate_props_conf` / `_transforms_conf` validators use it.

Self-hosted only: on Splunk Cloud, an app cannot read the system README, so the
caller (probe / handler) gates on `is_splunk_cloud` and degrades gracefully.

A parsed spec is:
  { "conf": "props",
    "attrs": { "<EXACT_NAME>": {"syntax": str, "description": str, "default": str|None}, ... },
    "prefixes": [ {"prefix": "TRANSFORMS-", "raw": "TRANSFORMS-<class>", "syntax": str, "description": str}, ... ] }

`attrs` holds attributes with a fixed name; `prefixes` holds the `NAME-<class>` /
`field.<x>` style attributes whose real name is "<prefix><something>" — an
input attribute is recognised if it exactly matches an `attrs` key OR starts
with any `prefixes[].prefix`.
"""

from __future__ import annotations

import os
import re

# conf_name -> parsed spec (per process; specs don't change within a session).
_SPEC_CACHE = {}
# conf_name -> path (built once).
_PATH_INDEX = {"map": None}

_ATTR_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.<>\-]*?)\s*=\s*(.*)$")
_STANZA_RE = re.compile(r"^\[.*\]\s*$")
_DEFAULT_RE = re.compile(r"(?i)default(?:s)?\s+(?:to|is|:)?\s*([^.\n]+)")


def splunk_home():
    return os.environ.get("SPLUNK_HOME") or ""


def _spec_dirs():
    """Directories to scan for *.conf.spec, most-authoritative first."""
    home = splunk_home()
    if not home:
        return []
    dirs = [os.path.join(home, "etc", "system", "README")]
    return [d for d in dirs if os.path.isdir(d)]


def _build_path_index():
    if _PATH_INDEX["map"] is not None:
        return _PATH_INDEX["map"]
    out = {}
    for d in _spec_dirs():
        try:
            for fn in os.listdir(d):
                if fn.endswith(".conf.spec"):
                    conf = fn[: -len(".conf.spec")]
                    # First dir wins (system README is authoritative).
                    out.setdefault(conf, os.path.join(d, fn))
        except Exception:
            continue
    _PATH_INDEX["map"] = out
    return out


def available_confs():
    """Sorted list of conf names that have a discoverable .spec."""
    return sorted(_build_path_index().keys())


def has_specs():
    return bool(_build_path_index())


def _flush_attr(attrs, prefixes, name, syntax, desc_lines):
    if not name:
        return
    desc = " ".join(s.strip() for s in desc_lines).strip()
    default = None
    m = _DEFAULT_RE.search(desc)
    if m:
        default = m.group(1).strip().strip("\"'") or None
    rec = {"syntax": (syntax or "").strip(), "description": desc, "default": default}
    if "<" in name or name.endswith("-") or name.endswith("."):
        # NAME-<class> / field.<x> style → a prefix matcher.
        prefix = re.split(r"<", name, 1)[0]
        prefixes.append({"prefix": prefix, "raw": name, **rec})
    else:
        attrs[name] = rec


def parse_spec_text(text, conf=""):
    """Parse raw .conf.spec text into the {conf, attrs, prefixes} structure."""
    attrs = {}
    prefixes = []
    cur_name = None
    cur_syntax = None
    cur_desc = []
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _STANZA_RE.match(stripped):
            _flush_attr(attrs, prefixes, cur_name, cur_syntax, cur_desc)
            cur_name, cur_syntax, cur_desc = None, None, []
            continue
        if stripped.startswith("*"):
            cur_desc.append(stripped.lstrip("* ").strip())
            continue
        m = _ATTR_RE.match(stripped)
        if m:
            _flush_attr(attrs, prefixes, cur_name, cur_syntax, cur_desc)
            cur_name, cur_syntax, cur_desc = m.group(1), m.group(2), []
            continue
        # Continuation of a description without a leading '*'.
        if cur_name:
            cur_desc.append(stripped)
    _flush_attr(attrs, prefixes, cur_name, cur_syntax, cur_desc)
    return {"conf": conf, "attrs": attrs, "prefixes": prefixes}


def load_spec(conf):
    """Parsed spec for one conf name (e.g. 'props'), or None if not found."""
    conf = (conf or "").strip().lower()
    if not conf:
        return None
    if conf in _SPEC_CACHE:
        return _SPEC_CACHE[conf]
    path = _build_path_index().get(conf)
    if not path:
        _SPEC_CACHE[conf] = None
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except Exception:
        _SPEC_CACHE[conf] = None
        return None
    spec = parse_spec_text(text, conf)
    _SPEC_CACHE[conf] = spec
    return spec


def recognise(spec, attr_name):
    """Classify an attribute name against a parsed spec → 'exact' | 'prefix' | None."""
    if not spec or not attr_name:
        return None
    if attr_name in spec["attrs"]:
        return "exact"
    upper = attr_name
    for p in spec["prefixes"]:
        pref = p["prefix"]
        if pref and upper.startswith(pref) and len(upper) > len(pref):
            return "prefix"
    return None

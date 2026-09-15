#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import re

VENDOR_SUFFIX: dict[str, tuple[str, str]] = {
    "fortigate": (" type=traffic subtype=forward", " type=traffic subtype=local"),
    "panos": ("", " dest_zone=mgmt"),
    "asa": (
        ' ("%ASA-6-302014" OR "%ASA-6-302016" OR "%ASA-4-106023" OR "%ASA-4-106100")',
        ' ("%ASA-4-106023" OR "%ASA-4-106100") identity:',
    ),
    "other": ("", ""),
}
DEFAULT_VENDOR = "fortigate"

_NAME_OK = re.compile(r"^[A-Za-z0-9_.:*-]+$")

SHIPPED_INDEX = "fw_index_not_set"
SHIPPED_SOURCETYPE = "fw_sourcetype_not_set"

MANAGED = "managed"
ADOPT = "adopt"
DEFAULTS = "app-default"

MACROS_RESET = "macros-reset"
HAND_WRITTEN = "hand-written"
UNSET = "unset"

class Source:

    __slots__ = ("index", "sourcetype", "n")

    def __init__(self, index: str, sourcetype: str, n: int = 0) -> None:
        self.index = (index or "").strip()
        self.sourcetype = (sourcetype or "").strip()
        self.n = n

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Source)
                and (self.index, self.sourcetype) == (other.index, other.sourcetype))

    def __repr__(self) -> str:
        return f"Source({self.index!r}, {self.sourcetype!r})"

    @property
    def term(self) -> str:
        return f"index={self.index} sourcetype={self.sourcetype}"

def vendor_or_default(vendor: str | None) -> str:
    v = (vendor or "").strip()
    return v if v in VENDOR_SUFFIX else DEFAULT_VENDOR

def validate_source(index: str, sourcetype: str, summary_index: str = "cip_ti_matches") -> str:
    for label, value in (("Index", index), ("Sourcetype", sourcetype)):
        v = (value or "").strip()
        if not v:
            return f"{label} is required."
        if not _NAME_OK.match(v):
            return (f"{label} may only contain letters, digits and _ . : * - "
                    f"(got {v!r}).")
        if v.startswith("*"):
            return (f"{label} may not start with * . A wildcard here makes the detection"
                    " search read its own summary index.")
    idx = (index or "").strip()
    if idx == summary_index:
        return (f"Index may not be {summary_index} - that is this app's own summary index,"
                " not firewall traffic.")
    if "*" in idx and fnmatch.fnmatchcase(summary_index, idx):
        return (f"Index {idx} also matches {summary_index}, this app's own summary index."
                " Name the firewall index without that wildcard.")
    if (index or "").strip() == SHIPPED_INDEX or (sourcetype or "").strip() == SHIPPED_SOURCETYPE:
        return ("That is the shipped placeholder, not a log source - type the index and"
                " sourcetype this firewall actually logs into.")
    return ""

def parse_sources(stanzas: dict[str, dict[str, str]]) -> list[Source]:
    out: list[Source] = []
    for name, content in stanzas.items():
        m = re.match(r"^source:(\d+)$", name.strip())
        if not m:
            continue
        if _truthy(content.get("disabled")):
            continue
        s = Source(content.get("index", ""), content.get("sourcetype", ""), int(m.group(1)))
        if s.index and s.sourcetype:
            out.append(s)
    out.sort(key=lambda s: s.n)
    return out

def _truthy(v: object) -> bool:
    return str("" if v is None else v).strip().lower() in ("1", "true", "yes", "on")

def generate(sources: list[Source], vendor: str) -> tuple[str, str]:
    fwd_sfx, loc_sfx = VENDOR_SUFFIX[vendor_or_default(vendor)]
    if len(sources) == 1:
        t = sources[0].term
        return t + fwd_sfx, t + loc_sfx
    return (
        " OR ".join(f"({s.term}{fwd_sfx})" for s in sources),
        " OR ".join(f"({s.term}{loc_sfx})" for s in sources),
    )

def definition_vendor(server_fwd: str, server_loc: str,
                      sources: list[Source]) -> str | None:
    if not sources:
        return None
    sf, sl = _norm(server_fwd), _norm(server_loc)
    for name in VENDOR_SUFFIX:
        gf, gl = generate(sources, name)
        if (gf or gl) and sf == _norm(gf) and sl == _norm(gl):
            return name
    return None

def legacy_generate(fw_index: str, fw_sourcetype: str, vendor: str) -> tuple[str, str]:
    i, st = (fw_index or "").strip(), (fw_sourcetype or "").strip()
    if not i or not st:
        return "", ""
    return generate([Source(i, st)], vendor)

def classify(server_fwd: str, server_loc: str, sources: list[Source], vendor: str,
             fw_index: str = "", fw_sourcetype: str = "") -> str:
    sf, sl = _norm(server_fwd), _norm(server_loc)
    if not sf and not sl:
        return UNSET
    if definition_vendor(sf, sl, sources) is not None:
        return MANAGED
    lf, ll = legacy_generate(fw_index, fw_sourcetype, vendor)
    if (lf or ll) and sf == _norm(lf) and sl == _norm(ll):
        return ADOPT
    df, dl = generate([Source(SHIPPED_INDEX, SHIPPED_SOURCETYPE)], DEFAULT_VENDOR)
    if sf == _norm(df) and sl == _norm(dl):
        return DEFAULTS
    return HAND_WRITTEN

def _norm(d: str) -> str:
    return " ".join((d or "").split())

def adopt(fw_index: str, fw_sourcetype: str) -> list[Source]:
    i, st = (fw_index or "").strip(), (fw_sourcetype or "").strip()
    return [Source(i, st, 1)] if i and st else []

def shipped_default() -> list[Source]:
    return [Source(SHIPPED_INDEX, SHIPPED_SOURCETYPE, 1)]

def stanza_writes(sources: list[Source], existing: dict[str, dict[str, str]]
                  ) -> list[tuple[str, dict[str, str]]]:
    out: list[tuple[str, dict[str, str]]] = []
    for n, s in enumerate(sources, 1):
        out.append((f"source:{n}", {"index": s.index, "sourcetype": s.sourcetype,
                                    "disabled": "0"}))
    used = {f"source:{n}" for n in range(1, len(sources) + 1)}
    for name in sorted(existing):
        if re.match(r"^source:\d+$", name.strip()) and name not in used:
            if not _truthy(existing[name].get("disabled")):
                out.append((name, {"disabled": "1"}))
    return out

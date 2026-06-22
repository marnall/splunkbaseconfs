"""Shared CIM data-model reader (v1.5.0 — Data Foundation).

Reads the installed Splunk Common Information Model definitions from
`$SPLUNK_HOME/etc/apps/Splunk_SA_CIM/default/data/models/*.json` — so CIM advice
is always version-matched to whatever CIM the customer has installed, not the
LLM's training data. Used by the `cim-data-models` knowledge connector now and
by the CIM Coverage Audit later.

There is no REST endpoint for the model JSON, so we read from disk →
**self-hosted only** (the caller gates on `is_splunk_cloud`).

A parsed model is:
  { "model": "Authentication", "display": str, "description": str,
    "datasets": [ {"name", "display", "parent", "tags": [..], "constraint": str|None,
                   "fields": [ {"name","required","type","comment"} ]} ],
    "all_fields": [sorted field names across datasets] }
"""

from __future__ import annotations

import json
import os
import re

_MODEL_CACHE = {}
_TAG_RE = re.compile(r"\btag\s*=\s*([A-Za-z0-9_]+)")


def _models_dir():
    home = os.environ.get("SPLUNK_HOME") or ""
    if not home:
        return ""
    d = os.path.join(home, "etc", "apps", "Splunk_SA_CIM",
                     "default", "data", "models")
    return d if os.path.isdir(d) else ""


def cim_installed():
    return bool(_models_dir())


def available_models():
    d = _models_dir()
    if not d:
        return []
    out = []
    try:
        for fn in os.listdir(d):
            if fn.endswith(".json"):
                out.append(fn[: -len(".json")])
    except Exception:
        pass
    return sorted(out)


def _tags_from_constraints(constraints):
    tags = set()
    for c in (constraints or []):
        for m in _TAG_RE.finditer((c or {}).get("search") or ""):
            tags.add(m.group(1))
    return sorted(tags)


def load_model(name):
    name = (name or "").strip()
    if not name:
        return None
    if name in _MODEL_CACHE:
        return _MODEL_CACHE[name]
    d = _models_dir()
    path = os.path.join(d, name + ".json") if d else ""
    if (not path or not os.path.exists(path)) and d:
        for m in available_models():
            if m.lower() == name.lower():
                path, name = os.path.join(d, m + ".json"), m
                break
    if not path or not os.path.exists(path):
        _MODEL_CACHE[name] = None
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw = json.load(fh)
    except Exception:
        _MODEL_CACHE[name] = None
        return None

    datasets = []
    all_fields = {}
    for o in raw.get("objects", []) or []:
        flds = []
        for f in o.get("fields", []) or []:
            fn = f.get("fieldName")
            if not fn:
                continue
            rec = {
                "name": fn,
                "required": bool(f.get("required")),
                "type": f.get("type"),
                # CIM field comments are usually strings but occasionally a JSON
                # object — coerce so slicing never blows up.
                "comment": str(f.get("comment") or "")[:200],
            }
            flds.append(rec)
            all_fields.setdefault(fn, rec)
        constraints = o.get("constraints") or []
        datasets.append({
            "name": o.get("objectName"),
            "display": o.get("displayName"),
            "parent": o.get("parentName"),
            "tags": _tags_from_constraints(constraints),
            "constraint": (constraints[0].get("search") if constraints else None),
            "fields": flds,
        })
    # CIM datasets inherit fields + tags from their parent chain (BaseEvent →
    # Authentication → Failed_Authentication). Roll those up so each dataset
    # reports its EFFECTIVE fields/tags, not just the ones it newly declares.
    by_name = {d["name"]: d for d in datasets if d.get("name")}

    def _ancestors(d, seen):
        chain = []
        p = d.get("parent")
        while p and p in by_name and p not in seen:
            seen.add(p)
            par = by_name[p]
            chain.append(par)
            p = par.get("parent")
        return chain

    for d in datasets:
        seen = {d.get("name")}
        chain = _ancestors(d, seen)
        eff_fields = {f["name"] for f in d.get("fields") or []}
        eff_tags = set(d.get("tags") or [])
        for anc in chain:
            eff_fields.update(f["name"] for f in anc.get("fields") or [])
            eff_tags.update(anc.get("tags") or [])
        d["effective_fields"] = sorted(eff_fields)
        d["effective_tags"] = sorted(eff_tags)

    parsed = {
        "model": raw.get("modelName") or name,
        "display": raw.get("displayName"),
        "description": raw.get("description"),
        "datasets": datasets,
        "all_fields": sorted(all_fields.keys()),
    }
    _MODEL_CACHE[name] = parsed
    return parsed

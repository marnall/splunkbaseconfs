#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cip_ti_sources as src

APP = "TA-cip-ti-feed"
MGMT = "https://127.0.0.1:8089"
CONF = "cip_ti_feed"
MACRO_FWD = "cip_ti_traffic"
MACRO_LOC = "cip_ti_traffic_local"
SECRET_NAMES = ("cip_key", "slack_webhook")

_INT_0_100 = ("confidence", "alert_min_confidence")
_FLAGS = ("alert_outbound_established", "alert_inbound_established",
          "alert_outbound_attempted", "alert_inbound_attempted",
          "alert_outbound_blocked", "alert_inbound_blocked")
_FREE = ("cip_env", "web_base_url", "feed_limit")
SETTING_KEYS = _INT_0_100 + _FLAGS + _FREE + ("fw_vendor",)

_DIGITS_0_100 = re.compile(r"[0-9]{1,3}")

_FEED_LIMIT_MAX = 50000

_ENVS = ("LIVE", "TEST")

_WEB_BASE_URL = re.compile(r"https?://[^/?#@\s]+")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")

def validate(settings: dict[str, Any], sources: list[dict[str, Any]]) -> str:
    for k in _INT_0_100:
        if k not in settings:
            continue
        raw = str(settings.get(k, "")).strip()
        if raw == "":
            continue
        if not _DIGITS_0_100.fullmatch(raw):
            return f"{k} must be a whole number between 0 and 100 (got {raw[:20]!r})."
        if int(raw) > 100:
            return f"{k} must be between 0 and 100 (got {int(raw)})."
    for k in _FREE + ("fw_vendor",):
        if k in settings and _CONTROL.search(str(settings[k])):
            return f"{k} may not contain control characters."
    if "cip_env" in settings:
        env = str(settings["cip_env"]).strip().upper()
        if env and env not in _ENVS:
            return f"cip_env must be LIVE or TEST (got {str(settings['cip_env'])[:20]!r})."
    if "web_base_url" in settings:
        url = str(settings["web_base_url"]).strip()
        if url and not _WEB_BASE_URL.fullmatch(url):
            return ("web_base_url must be the Splunk web address only, scheme and host like"
                    f" https://splunk.example.com:8000 (got {url[:60]!r}).")
    if "feed_limit" in settings:
        raw = str(settings["feed_limit"]).strip()
        if raw and not (raw.isascii() and raw.isdigit()
                        and 1 <= int(raw) <= _FEED_LIMIT_MAX):
            return (f"feed_limit must be a whole number between 1 and {_FEED_LIMIT_MAX}"
                    f" (got {raw[:20]!r}).")
    for k in _FLAGS:
        if k in settings and str(settings[k]).strip() not in ("0", "1"):
            return f"{k} must be 0 or 1."
    if "fw_vendor" in settings:
        v = str(settings["fw_vendor"]).strip()
        if v and v not in src.VENDOR_SUFFIX:
            return (f"Unknown firewall product {v!r}. Pick one of: "
                    + ", ".join(sorted(src.VENDOR_SUFFIX)) + ".")
    seen: set[tuple[str, str]] = set()
    for i, s in enumerate(sources, 1):
        index = str(s.get("index", "")).strip()
        st = str(s.get("sourcetype", "")).strip()
        msg = src.validate_source(index, st)
        if msg:
            return f"Source {i}: {msg}"
        if (index, st) in seen:
            return f"Source {i}: {index} / {st} is listed twice."
        seen.add((index, st))
    return ""

def plan(settings: dict[str, Any], sources: list[dict[str, Any]],
         current: dict[str, Any]) -> dict[str, Any]:
    vendor = src.vendor_or_default(settings.get("fw_vendor") or current.get("vendor"))
    slist = [src.Source(str(s.get("index", "")), str(s.get("sourcetype", "")))
             for s in sources]
    fwd, loc = src.generate(slist, vendor)
    state = src.classify(current.get("macro_fwd", ""), current.get("macro_loc", ""),
                         current.get("sources", []), current.get("vendor", ""),
                         current.get("fw_index", ""), current.get("fw_sourcetype", ""))

    skipped: list[dict[str, str]] = []
    macros: dict[str, str] | None = None
    if state == src.HAND_WRITTEN:
        skipped.append({
            "what": "log source macros",
            "why": ("the current definitions were not written by this page, so they are left"
                    " exactly as they are"),
        })
    elif not slist:
        skipped.append({"what": "log source macros",
                        "why": "no log source is listed yet"})
    else:
        macros = {MACRO_FWD: fwd, MACRO_LOC: loc}

    keep = _normalise({k: str(v) for k, v in settings.items() if k in SETTING_KEYS})
    keep["fw_vendor"] = vendor
    return {
        "macros": macros,
        "previous": {MACRO_FWD: current.get("macro_fwd", ""),
                     MACRO_LOC: current.get("macro_loc", "")},
        "stanzas": src.stanza_writes(slist, current.get("stanzas", {})) if macros else [],
        "settings": keep,
        "skipped": skipped,
        "state": state,
        "generated": {"forward": fwd, "local": loc},
    }

def _normalise(keep: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in keep.items():
        raw = v.strip()
        if k in _INT_0_100 or k == "feed_limit":
            if raw:
                out[k] = str(int(raw))
        elif k == "cip_env":
            if raw:
                out[k] = raw.upper()
        else:
            out[k] = raw
    return out

def apply_plan(p: dict[str, Any], secrets: dict[str, str], rest: Callable[..., tuple[int, str]]
               ) -> dict[str, Any]:
    wrote: list[str] = []
    skipped = list(p["skipped"])

    def write(label: str, path: str, body: dict[str, str]) -> bool:
        status, text = rest("POST", path, body)
        if 200 <= status < 300:
            wrote.append(label)
            return True
        skipped.append({"what": label, "why": _why(status, text)})
        return False

    ok = True
    if p["macros"]:
        ok = _write_macro_pair(p, rest, write, wrote, skipped)
        if not ok:
            todo = [n for n, _k in p["stanzas"]] + ["settings"]
            todo += [f"secret {n}" for n in SECRET_NAMES if str(secrets.get(n, "") or "")]
            skipped.append({"what": ", ".join(todo),
                            "why": "not attempted because the log source macros did not save"})
            skipped.append({"what": "is_configured",
                            "why": "left as it was because something above did not save"})
            return {"ok": False, "gated": True, "wrote": wrote, "skipped": skipped,
                    "macros": p["generated"], "state": p["state"]}

    for name, keys in p["stanzas"]:
        if _exists(rest, f"configs/conf-{CONF}/{_q(name)}"):
            ok = write(name, f"configs/conf-{CONF}/{_q(name)}", keys) and ok
        else:
            body = dict(keys)
            body["name"] = name
            ok = write(name, f"configs/conf-{CONF}", body) and ok

    if p["settings"]:
        ok = write("settings", f"configs/conf-{CONF}/settings", p["settings"]) and ok

    for name in SECRET_NAMES:
        value = str(secrets.get(name, "") or "")
        if not value:
            continue
        if not _put_secret(rest, name, value):
            skipped.append({"what": f"secret {name}", "why": "could not be stored"})
            ok = False
        else:
            wrote.append(f"secret {name}")
            st, txt = rest("POST", f"storage/passwords/{_q(':' + name + ':')}/acl",
                           {"sharing": "app", "owner": "nobody",
                            "perms.read": "admin", "perms.write": "admin"})
            if not (200 <= st < 300):
                skipped.append({"what": f"secret {name} permissions (read stays open)",
                                "why": _why(st, txt)})

    gated = False
    if ok:
        if not write("is_configured", "configs/conf-app/install", {"is_configured": "1"}):
            gated = True
        else:
            st, _txt = rest("POST", f"apps/local/{_q(APP)}/_reload", {})
            if not (200 <= st < 300):
                skipped.append({"what": "app registry reload",
                                "why": _why(st, _txt)})
                gated = True
    else:
        skipped.append({"what": "is_configured",
                        "why": "left as it was because something above did not save"})
        gated = True

    return {"ok": ok, "gated": gated, "wrote": wrote, "skipped": skipped,
            "macros": p["generated"], "state": p["state"]}

def _write_macro_pair(p: dict[str, Any], rest: Callable[..., tuple[int, str]],
                      write: Callable[[str, str, dict[str, str]], bool],
                      wrote: list[str], skipped: list[dict[str, str]]) -> bool:
    (first, first_def), (second, second_def) = list(p["macros"].items())
    if not write(f"macro {first}", f"configs/conf-macros/{_q(first)}",
                 {"definition": first_def}):
        skipped.append({"what": f"macro {second}",
                        "why": f"not attempted because macro {first} did not save"})
        return False
    if write(f"macro {second}", f"configs/conf-macros/{_q(second)}",
             {"definition": second_def}):
        return True
    wrote.remove(f"macro {first}")
    previous = p.get("previous", {}).get(first, "")
    if not previous:
        skipped.append({"what": f"macro {first}",
                        "why": f"written, but macro {second} did not save and the previous"
                               " definition is not known, so it was not rolled back; the pair"
                               " is now inconsistent, restore local/macros.conf by hand"})
        return False
    undo, _txt = rest("POST", f"configs/conf-macros/{_q(first)}", {"definition": previous})
    if 200 <= undo < 300:
        skipped.append({"what": f"macro {first}",
                        "why": f"rolled back to its previous definition because macro {second}"
                               " did not save"})
    else:
        skipped.append({"what": f"macro {first}",
                        "why": f"written, then the rollback failed ({_why(undo, _txt)}); the pair"
                               " is now inconsistent, restore local/macros.conf by hand"})
    return False

def _put_secret(rest: Callable[..., tuple[int, str]], name: str, value: str) -> bool:
    status, _ = rest("POST", f"storage/passwords/{_q(':' + name + ':')}", {"password": value})
    if 200 <= status < 300:
        return True
    status, _ = rest("POST", "storage/passwords", {"name": name, "password": value})
    return 200 <= status < 300

def _exists(rest: Callable[..., tuple[int, str]], path: str) -> bool:
    status, _ = rest("GET", path, None)
    return 200 <= status < 300

def _why(status: int, text: str) -> str:
    if status == 403:
        return "this account is not allowed to write it (needs admin_all_objects)"
    if status == 404:
        return "the object it writes to does not exist"
    if status == 401:
        return "the session expired; reload the page"
    return f"splunkd answered {status}"

def _q(s: str) -> str:
    return urllib.parse.quote(s, safe="")

def load_current(rest: Callable[..., tuple[int, str]]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "settings": {}, "stanzas": {}, "sources": [], "vendor": src.DEFAULT_VENDOR,
        "fw_index": "", "fw_sourcetype": "", "macro_fwd": "", "macro_loc": "",
        "can_write": False, "secrets": {n: False for n in SECRET_NAMES},
    }
    status, text = rest("GET", f"configs/conf-{CONF}?count=0", None)
    if 200 <= status < 300:
        for entry in _entries(text):
            name = str(entry.get("name", ""))
            content = entry.get("content") or {}
            out["stanzas"][name] = {k: str(v) for k, v in content.items()
                                    if not str(k).startswith("eai")}
            if name == "settings":
                out["settings"] = out["stanzas"][name]
                out["can_write"] = bool((entry.get("acl") or {}).get("can_write", False))
    s = out["settings"]
    out["vendor"] = src.vendor_or_default(s.get("fw_vendor"))
    out["fw_index"] = s.get("fw_index", "")
    out["fw_sourcetype"] = s.get("fw_sourcetype", "")
    out["sources"] = src.parse_sources(out["stanzas"])

    for key, macro in (("macro_fwd", MACRO_FWD), ("macro_loc", MACRO_LOC)):
        status, text = rest("GET", f"configs/conf-macros/{_q(macro)}", None)
        if 200 <= status < 300:
            for entry in _entries(text):
                out[key] = str((entry.get("content") or {}).get("definition") or "")

    for name in SECRET_NAMES:
        status, _ = rest("GET", f"storage/passwords/{_q(':' + name + ':')}?f=username", None)
        if 200 <= status < 300:
            out["secrets"][name] = True
        else:
            out["secrets"][name] = False if out["can_write"] else None
    return out

def _entries(text: str) -> list[dict[str, Any]]:
    try:
        return list(json.loads(text).get("entry") or [])
    except Exception:
        return []

def public_state(current: dict[str, Any]) -> dict[str, Any]:
    state = src.classify(current["macro_fwd"], current["macro_loc"], current["sources"],
                         current["vendor"], current["fw_index"], current["fw_sourcetype"])
    sources = current["sources"]
    if state == src.ADOPT:
        sources = src.adopt(current["fw_index"], current["fw_sourcetype"])
    elif state == src.DEFAULTS:
        if not sources:
            sources = src.adopt(current.get("fw_index", ""), current.get("fw_sourcetype", ""))
        if sources:
            state = src.MACROS_RESET
        else:
            sources = src.shipped_default()
    return {
        "ok": True,
        "settings": {k: v for k, v in current["settings"].items() if k in SETTING_KEYS},
        "vendor": current["vendor"],
        "sources": [{"index": s.index, "sourcetype": s.sourcetype} for s in sources],
        "state": state,
        "macros": {"forward": current["macro_fwd"], "local": current["macro_loc"]},
        "editable": state != src.HAND_WRITTEN,
        "can_write": current["can_write"],
        "secrets": current["secrets"],
        "vendors": sorted(src.VENDOR_SUFFIX),
        "suffixes": {k: {"forward": fwd, "local": loc}
                     for k, (fwd, loc) in src.VENDOR_SUFFIX.items()},
        "definition_vendor": src.definition_vendor(current["macro_fwd"], current["macro_loc"],
                                                   sources),
    }

def make_rest(session_key: str, mgmt: str = MGMT) -> Callable[..., tuple[int, str]]:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    def rest(method: str, path: str, body: dict[str, str] | None) -> tuple[int, str]:
        url = f"{mgmt}/servicesNS/nobody/{APP}/{path}"
        url += ("&" if "?" in url else "?") + "output_mode=json"
        data = urllib.parse.urlencode(body or {}).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Authorization": "Splunk " + session_key})
        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            return exc.code, ""
        except Exception:
            return 0, ""

    return rest

_LOGGER: logging.Logger | None = None

def _logger() -> logging.Logger | None:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER
    try:
        home = os.environ.get("SPLUNK_HOME") or "/opt/splunk"
        path = os.path.join(home, "var", "log", "splunk", "cip_ti_setup.log")
        h = logging.handlers.RotatingFileHandler(
            path, maxBytes=2 * 1024 * 1024, backupCount=2, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        lg = logging.getLogger("cip_ti_setup")
        lg.setLevel(logging.INFO)
        lg.propagate = False
        lg.handlers = [h]
        _LOGGER = lg
    except Exception:
        _LOGGER = None
    return _LOGGER

def _log(msg: str) -> None:
    lg = _logger()
    if lg is None:
        return
    try:
        lg.info(msg)
    except Exception:
        pass

def handle_request(in_data: dict[str, Any],
                   rest_factory: Callable[[str], Callable[..., tuple[int, str]]] = make_rest
                   ) -> dict[str, Any]:
    session = (in_data.get("session") or {}).get("authtoken", "")
    if not session:
        return {"ok": False, "error": "no session"}
    rest = rest_factory(session)
    current = load_current(rest)

    payload = _payload(in_data)
    if not payload:
        return public_state(current)

    _qkeys = ""
    try:
        _q = in_data.get("query") or []
        _qkeys = "|".join(sorted(str(k) for k, _v in _q)) if isinstance(_q, list) else ""
    except Exception:
        _qkeys = ""
    _log("event=setup_save phase=enter"
         f" method=\"{str(in_data.get('method', '')).upper()}\""
         f" query_keys=\"{_qkeys[:80]}\""
         f" attempt={payload.get('attempt') or 1}"
         f" settings_keys={len(payload.get('settings') or {})}"
         f" sources={len(payload.get('sources') or [])}"
         f" secrets={len(payload.get('secrets') or {})}"
         f" can_write={1 if current['can_write'] else 0}")

    _diag = payload.get("diag")
    if isinstance(_diag, dict):
        _log("event=setup_save phase=retry_after_unconfirmed"
             f" prev_status={_diag.get('status')}"
             f" prev_len={_diag.get('len')}"
             f" prev_keys=\"{str(_diag.get('keys') or '')[:120]}\""
             f" prev_err=\"{str(_diag.get('err') or '')[:80]}\"")
    if not current["can_write"]:
        _log("event=setup_save phase=refused reason=no_write_capability")
        return {"ok": False, "wrote": [], "skipped": [],
                "error": ("This account cannot write the app configuration"
                          " (needs admin_all_objects)."),
                "macros": {"forward": current["macro_fwd"], "local": current["macro_loc"]}}
    settings = dict(payload.get("settings") or {})
    sources = list(payload.get("sources") or [])
    msg = validate(settings, sources)
    if msg:
        _log("event=setup_save phase=refused reason=validation")
        return {"ok": False, "wrote": [], "skipped": [], "error": msg}
    out = apply_plan(plan(settings, sources, current), payload.get("secrets") or {}, rest)
    _log("event=setup_save phase=done"
         f" ok={1 if out.get('ok') else 0}"
         f" gated={1 if out.get('gated') else 0}"
         f" wrote={len(out.get('wrote') or [])}"
         f" skipped={len(out.get('skipped') or [])}"
         f" wrote_labels=\"{'|'.join(out.get('wrote') or [])}\"")
    return out

def _payload(in_data: dict[str, Any]) -> dict[str, Any]:
    raw = in_data.get("payload")
    if isinstance(raw, dict):
        return raw

    parsed = _as_json(raw)
    if parsed is not None:
        return parsed

    if isinstance(raw, str) and raw:
        for key, values in urllib.parse.parse_qs(raw, keep_blank_values=True).items():
            if key == "payload" and values:
                parsed = _as_json(values[0])
                if parsed is not None:
                    return parsed

    for pair in in_data.get("form") or []:
        try:
            key, value = pair[0], pair[1]
        except Exception:
            continue
        if key == "payload":
            parsed = _as_json(value)
            if parsed is not None:
                return parsed

    return {}

def _as_json(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        out = json.loads(raw)
    except Exception:
        return None
    return out if isinstance(out, dict) else None

try:
    from splunk.persistconn.application import PersistentServerConnectionApplication
except Exception:
    PersistentServerConnectionApplication = object

class SetupHandler(PersistentServerConnectionApplication):

    def __init__(self, _command_line: str | None = None, _command_arg: str | None = None) -> None:
        super().__init__()

    def handle(self, in_string: str) -> dict[str, Any]:
        try:
            in_data = json.loads(in_string)
        except Exception:
            return {"status": 400, "payload": {"ok": False, "error": "bad request"}}
        try:
            body = handle_request(in_data)
        except Exception as exc:
            return {"status": 500,
                    "payload": {"ok": False, "error": f"setup failed ({type(exc).__name__})"}}
        return {"status": 200 if body.get("ok") else 400, "payload": body}

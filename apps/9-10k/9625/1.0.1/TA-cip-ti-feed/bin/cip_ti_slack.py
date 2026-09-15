#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import json
import re
import ssl
import sys
import time
import zlib
from typing import Any
from urllib.parse import quote, urlparse

APP_DEFAULT = "TA-cip-ti-feed"

PW_USER = "slack_webhook"

PW_ENTITY = quote(f":{PW_USER}:", safe="")

_SEV_EMOJI = {"critical": "\U0001f534", "high": "\U0001f7e0",
              "watch": "\U0001f7e1", "info": "⚪"}

_SEV_ORDER = ("info", "watch", "high", "critical")
_ALERT_EMOJI = "\U0001f6a8"

_PAST_EMOJI = "\U0001f553"

_WARN = "⚠️"
_BULLET = "•"

_SEP = "  ·  "

_AGE_MIN_DAYS = 1

_SECTION_LIMIT = 2900
_MAX_BLOCKS = 47
_MAX_SECTIONS = _MAX_BLOCKS - 3
_MAX_ROWS_CEILING = 50
_HEADER_LIMIT = 150
_REASON_LIMIT = 120

_PORTS_MAX = 20

_ASSET_LINE_FIELDS = (9, 12, 13)
_ASSET_LINES_MAX = 10

_RESULTS_LABEL = "Results in Splunk (kept 24 hours)"
_NO_LINK = "no link, results kept 24 hours in Splunk"
_LEGACY_ALLOWED = "allowed (outcome not recorded, completed and no reply not split)"

_STAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})(?: (\S+))?$")

def log(msg: str) -> None:
    sys.stderr.write(f"cip_ti_slack: {msg}\n")

def note(msg: str) -> None:
    sys.stdout.write(f"cip_ti_slack: {msg}\n")

def _esc(s: Any) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def mask_ip(ip: str) -> str:
    parts = ip.split(".")
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        return f"{parts[0]}.{parts[1]}.x.x"
    if ":" in ip:
        head = ":".join(ip.split(":")[:2])
        return f"{head}:x" if head else "::x"
    return ip

def parse_results(path: str) -> list[dict[str, str]] | None:
    if not path:
        return []
    try:
        with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []
    except (OSError, EOFError, zlib.error, csv.Error, UnicodeError) as exc:
        log(f"failed to read results ({type(exc).__name__})")
        return None

def _as_int(v: Any, default: int = 0) -> int:
    try:
        return int(float(str(v)))
    except (TypeError, ValueError):
        return default

def _human_bytes(v: Any) -> str:
    n = float(_as_int(v))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def _mv(value: Any) -> list[str]:
    return [p.strip() for p in str(value or "").split(",") if p.strip()]

def _distinct(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out

def _plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"

def _sev_word(v: Any) -> str:
    w = str(v or "").strip().lower()
    return w if w in _SEV_EMOJI else "info"

def _labelled(label: str, items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return f"*{label}:*  {items[0]}"
    return f"*{label} ({len(items)}):*  " + _SEP.join(items)

def _ports_text(ports: list[str]) -> str:
    head = ", ".join(ports[:_PORTS_MAX])
    rest = len(ports) - _PORTS_MAX
    return head + (f", and {rest} more" if rest > 0 else "")

def _age_suffix(epoch: Any, now: float) -> str:
    try:
        days = int((now - float(epoch)) // 86400)
    except (TypeError, ValueError):
        return ""
    if days < _AGE_MIN_DAYS:
        return ""
    return f"  ({_plural(days, 'day')} ago)"

def _stamp(s: Any) -> tuple[str, str, str] | None:
    m = _STAMP_RE.match(str(s or "").strip())
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3) or ""

def _seen_text(first: str, seen: str) -> str:
    if not first or first == seen:
        return seen
    a, b = _stamp(first), _stamp(seen)
    if a is None or b is None:
        return seen
    if a[0] == b[0] and a[2] == b[2]:
        return f"{a[0]} {a[1]} to {b[1]}" + (f" {b[2]}" if b[2] else "")
    return f"{first} to {seen}"

def _asset_lines(raw: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ln in str(raw or "").split(";"):
        parts = [p.strip() for p in ln.split("|")]
        if len(parts) not in _ASSET_LINE_FIELDS or not parts[0]:
            continue
        try:
            last = float(parts[5])
        except ValueError:
            last = 0.0
        has_bytes = len(parts) >= 12
        names: list[str] = []
        if len(parts) == 13 and parts[12] and parts[12] != "-":
            names = [n.strip() for n in parts[12].split("/") if n.strip()]
        out.append({"key": parts[0], "est": _as_int(parts[1]), "att": _as_int(parts[2]),
                    "blk": _as_int(parts[3]), "ev": _as_int(parts[4]), "last": last,
                    "first_str": parts[6], "last_str": parts[7], "ports": parts[8],
                    "sent": _as_int(parts[10]) if has_bytes else 0,
                    "rcvd": _as_int(parts[11]) if has_bytes else 0,
                    "has_bytes": has_bytes, "names": names})
    out.sort(key=lambda d: (-d["est"], -d["last"], d["key"]))
    return out

def _asset_line_text(d: dict[str, Any], mask: bool, card_ports: set[str], inbound: bool) -> str:
    key = ", ".join(mask_ip(a) if mask else a for a in _mv(d["key"])) or d["key"]
    who = _esc(key)
    if d["names"]:
        who = f"{_esc(' / '.join(d['names']))} ({who})"
    parts = [who]
    if d["est"]:
        parts.append(f"*{d['est']} completed*")
    if d["att"]:
        parts.append(f"{d['att']} no reply")
    if d["blk"]:
        parts.append(f"{d['blk']} denied")
    if len(parts) == 1:
        parts.append(_plural(d["ev"], "event"))

    first, last = d["first_str"], d["last_str"]
    if first == last:
        parts.append(_esc(first))
    else:
        if last[:5] == first[:5]:
            last = last[5:].lstrip()
        parts.append(f"{_esc(first)} to {_esc(last)}")
    if d["has_bytes"] and d["est"] > 0:
        by_us, to_us = (d["rcvd"], d["sent"]) if inbound else (d["sent"], d["rcvd"])
        parts.append(f"↑ {_human_bytes(by_us)} ↓ {_human_bytes(to_us)}")
    ports = [x for x in d["ports"].split("/") if x and x != "-"]
    if ports and set(ports) != card_ports:
        parts.append("dest ports " + _esc(_ports_text(ports)))
    return (_WARN if d["est"] > 0 else _BULLET) + "  " + _SEP.join(parts)

def _match_text(r: dict[str, str], mask: bool) -> str:
    return "\n".join(_match_lines(r, mask))

def _asset_block(r: dict[str, str], assets: list[str], mask: bool, inbound: bool,
                 card_ports: set[str], max_lines: int) -> tuple[list[str], set[str]]:
    k = len(assets)
    label = "*Our asset:*" if k == 1 else f"*Our assets ({k}):*"
    parsed = _asset_lines(r.get("asset_lines"))
    if parsed:
        entries = [(_asset_line_text(d, mask, card_ports, inbound), set(_mv(d["key"])), d["names"])
                   for d in parsed]
    else:
        entries = [(f"{_BULLET}  {_esc(mask_ip(a) if mask else a)}", {a}, []) for a in assets]
    shown = entries[:max_lines]
    covered: set[str] = set()
    for e in shown:
        covered |= e[1]
    rest = k - len(covered & set(assets))
    lines = [label] + [e[0] for e in shown]
    if rest > 0:
        lines.append(f"and {rest} more asset{'s' if rest != 1 else ''}")
    carried = {n for e in entries[:_ASSET_LINES_MAX] for n in e[2]}
    return lines, carried

def _match_lines(r: dict[str, str], mask: bool, max_asset_lines: int = _ASSET_LINES_MAX) -> list[str]:
    sev = _sev_word(r.get("severity"))
    direction_raw = (r.get("ti_direction") or "").strip() or "unknown"
    direction = _esc(direction_raw)
    inbound = direction_raw == "inbound"
    mip = _esc((r.get("match_ip") or "?").strip())
    assets = _distinct(_mv(r.get("internal_ip")))
    k = len(assets)

    raw_est = r.get("established_count")
    legacy = raw_est is None or str(raw_est).strip() == ""
    est = 0 if legacy else _as_int(raw_est)
    att = _as_int(r.get("attempted_count"))
    passed = _as_int(r.get("passed_count")) if legacy else 0
    blocked = _as_int(r.get("blocked_count"))
    events = _as_int(r.get("event_count"))

    lines = [f"{_SEV_EMOJI[sev]}  *{mip}*{_SEP}{direction}{_SEP}{sev}"]

    parts = []
    if est:
        parts.append(f"*{est} completed*")
    if att:
        parts.append(f"{att} no reply")
    if passed:
        parts.append(f"{passed} {_LEGACY_ALLOWED}")
    if blocked:
        parts.append(f"{blocked} denied")
    if not parts:
        parts.append("no sessions counted")
    tail = f"   ({_plural(events, 'event')})" if events else ""
    lines.append(f"*Firewall:*  {(_WARN + '  ') if est > 0 else ''}{_SEP.join(parts)}{tail}")

    badges = []
    if (r.get("self_egress") or "").strip() == "ours":
        badges.append("this is one of OUR OWN public addresses, not an outsider")
    surface = (r.get("surface_str") or "").strip()
    if surface == "firewall itself":
        badges.append("aimed at the firewall itself, not through it")
    elif surface == "partly firewall itself":
        badges.append("some traffic aimed at the firewall itself, the rest through it")
    paths = [p for p in _mv(r.get("path_str")) if p != "-"]
    own = [p for p in paths if p != "internet"]
    if own:
        link = _esc(", ".join(own))
        if "internet" in paths:
            badges.append(f"partly over our own {link} link, the rest from the internet")
        else:
            badges.append(f"over our own {link} link, not from the internet")
    if badges:
        lines.append("*Note:*  " + _SEP.join(badges))

    ports_all = _mv(r.get("dst_ports_str"))
    carried: set[str] = set()
    if assets:
        block, carried = _asset_block(r, assets, mask, inbound, set(ports_all), max_asset_lines)
        lines += block
    device = (r.get("device_name") or "").strip()
    if device and device != "-":
        names = [n for n in _distinct(_mv(device))
                 if n.replace("|", " ").replace(";", " ") not in carried]
        if names:
            lines.append(_labelled("Asset name" if len(names) == 1 else "Asset names", [_esc(n) for n in names]))

    seen_raw = (r.get("seen_time") or "").strip()
    if seen_raw:
        seen = _esc(_seen_text((r.get("first_time") or "").strip(), seen_raw))
        lines.append(f"*Seen:*  {seen}{_age_suffix(r.get('seen_epoch'), time.time())}")
    firewall = (r.get("firewall") or "").strip()
    if firewall and firewall != "-":
        lines.append(_labelled("Seen by", [_esc(f) for f in _mv(firewall)]))
    if est > 0 or (legacy and passed > 0):
        sent = _as_int(r.get("sent_bytes"))
        recv = _as_int(r.get("received_bytes"))
        by_us, to_us = (recv, sent) if inbound else (sent, recv)
        data_label = "Data (all assets)" if k >= 2 else "Data"
        lines.append(f"*{data_label}:*  ↑ {_human_bytes(by_us)} sent by us · ↓ {_human_bytes(to_us)} sent to us")
    if ports_all:
        lines.append(f"*Dest ports:*  {_esc(_ports_text(ports_all))}")
    profile = (r.get("ti_profile") or "").strip()
    conf = (r.get("ti_confidence") or "").strip()
    feed_seen = (r.get("feed_seen") or "").strip()
    feed = [f"{_esc(profile)} profile" if profile else "unknown profile",
            f"confidence {_esc(conf)} / 100" if conf else "confidence unknown"]
    if feed_seen and feed_seen != "-":
        feed.append(f"last sighting {_esc(feed_seen)}")
    lines.append("*Threat feed:*  " + _SEP.join(feed))
    reason = _esc(" ".join((r.get("ti_reason") or "").splitlines())[:_REASON_LIMIT])
    if reason:
        lines.append(f"*Reason:*  {reason}")
    return lines

def _section_text(r: dict[str, str], mask: bool, open_line: str) -> str:
    budget = _SECTION_LIMIT - (len(open_line) + 1 if open_line else 0)
    n = _ASSET_LINES_MAX
    lines = _match_lines(r, mask, n)
    while len("\n".join(lines)) > budget and n > 0:
        n -= 1
        lines = _match_lines(r, mask, n)
    body = "\n".join(lines)
    if len(body) > budget:
        kept: list[str] = []
        size = 0
        for ln in lines:
            add = len(ln) + (1 if kept else 0)
            if size + add > budget:
                break
            kept.append(ln)
            size += add
        body = "\n".join(kept)
    if not open_line:
        return body
    return f"{body}\n{open_line}" if body else open_line

def _not_shown_text(rows: list[dict[str, str]]) -> str:
    items = [f"{_SEV_EMOJI[_sev_word(x.get('severity'))]} {_esc((x.get('match_ip') or '?').strip())} "
             f"{_esc((x.get('ti_direction') or '').strip() or 'unknown')}" for x in rows]
    text = f"*Not shown ({len(rows)}):*  " + _SEP.join(items)
    if len(text) > _SECTION_LIMIT:
        tail = f"{_SEP}(list cut)"
        text = text[:_SECTION_LIMIT - len(tail)].rsplit(_SEP, 1)[0] + tail
    return text

def _ui_origin(base_url: str, results_link: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if base and base.lower().startswith(("http://", "https://")):
        return base
    rl = (results_link or "").strip()
    if rl and not _is_loopback(rl):
        pr = urlparse(rl)
        if pr.scheme and pr.netloc:
            return f"{pr.scheme}://{pr.netloc}"
    return ""

def _results_anchor(results_link: str) -> str:
    return f"<{results_link}|{_RESULTS_LABEL}>"

def _row_links(origin: str, app: str, match_ip: str) -> str:
    ip = (match_ip or "").strip()
    if not origin or not ip:
        return ""
    q = quote(ip, safe="")
    inv = f"{origin}/app/{quote(app, safe='')}/ti_feed_investigate?form.mip={q}"
    hist = f"{origin}/app/{quote(app, safe='')}/ti_feed_history?form.q={q}"
    return f"*Open:*  <{inv}|Investigate>{_SEP}<{hist}|IP lookup>"

def build_slack_payload(search_name: str, rows: list[dict[str, str]],
                        cfg: dict[str, Any], results_link: str,
                        ui_origin: str = "", app: str = APP_DEFAULT) -> dict[str, Any]:
    max_rows = min(_MAX_ROWS_CEILING, max(1, _as_int(cfg.get("max_rows"), 20)))
    mask = str(cfg.get("mask_internal_ip", "0")).strip().lower() in ("1", "true", "yes")
    total = len(rows)

    n_ips = len({(r.get("match_ip") or "").strip() for r in rows if (r.get("match_ip") or "").strip()})
    n_assets = len({a for r in rows for a in _mv(r.get("internal_ip"))})
    a_seg = f" · {_plural(n_assets, 'asset')}" if n_assets else ""
    top = _SEV_ORDER[max((_SEV_ORDER.index(_sev_word(r.get("severity"))) for r in rows), default=0)]
    ips = _plural(n_ips, "malicious IP")
    if str(cfg.get("kind") or "").strip().lower() == "past":
        header = f"{_PAST_EMOJI} up to {top} · {_plural(total, 'past contact')} on {ips}{a_seg} (not new traffic)"
    else:
        header = f"{_ALERT_EMOJI} up to {top} · {_plural(total, 'match', 'matches')} on {ips}{a_seg}"
    header = header[:_HEADER_LIMIT]
    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": header, "emoji": True}},
    ]

    shown = rows[:min(max_rows, _MAX_SECTIONS)]
    for r in shown:
        body = _section_text(r, mask, _row_links(ui_origin, app, r.get("match_ip", "")))
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": body}})
    if total > len(shown):
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": _not_shown_text(rows[len(shown):])}})
    run = _results_anchor(results_link) if results_link else _NO_LINK
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Alert run:*  {run}"}})

    payload: dict[str, Any] = {
        "text": f"{header} · {search_name}",
        "blocks": blocks,
    }
    channel = str(cfg.get("channel") or "").strip()
    if channel:
        payload["channel"] = channel
    return payload

def resolve_webhook(cfg: dict[str, Any], session_key: str, server_uri: str, app: str) -> str:
    direct = str(cfg.get("webhook_url") or "").strip()
    if direct:
        return direct
    if not session_key:
        return ""
    base = server_uri or "https://127.0.0.1:8089"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    import urllib.request
    url = f"{base}/servicesNS/nobody/{app}/storage/passwords/{PW_ENTITY}?output_mode=json"
    req = urllib.request.Request(url, headers={"Authorization": f"Splunk {session_key}"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as exc:
        log(f"storage/passwords lookup failed ({type(exc).__name__})")
        return ""
    for entry in data.get("entry", []):
        c = entry.get("content", {}) or {}
        if c.get("username") == PW_USER:
            return str(c.get("clear_password") or "")
    return ""

def resolve_base_url(session_key: str, server_uri: str, app: str) -> str:
    if not session_key:
        return ""
    base = server_uri or "https://127.0.0.1:8089"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    import urllib.request
    url = f"{base}/servicesNS/nobody/{app}/configs/conf-cip_ti_feed/settings?output_mode=json"
    req = urllib.request.Request(url, headers={"Authorization": f"Splunk {session_key}"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as exc:
        log(f"base-url lookup failed ({type(exc).__name__})")
        return ""
    try:
        content = data["entry"][0]["content"]
    except (KeyError, IndexError, TypeError):
        return ""
    return str(content.get("web_base_url") or "").strip().rstrip("/")

def _is_loopback(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return True
    return host in ("localhost", "::1", "0.0.0.0") or host.startswith("127.")

def build_results_url(base_url: str, results_link: str, app: str, sid: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if base and not base.lower().startswith(("http://", "https://")):
        base = ""
    rl = (results_link or "").strip()
    if base:
        if rl:
            pr = urlparse(rl)
            return base + pr.path + (f"?{pr.query}" if pr.query else "")
        if sid:
            return f"{base}/app/{quote(app)}/search?sid={quote(sid)}"
        return base
    if rl and not _is_loopback(rl):
        return rl
    return ""

def post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    import urllib.error
    import urllib.request
    body = json.dumps(payload).encode("utf-8")
    try:
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
            return (200 <= r.status < 300), f"http={r.status}"
    except urllib.error.HTTPError as exc:
        return False, f"http={exc.code}"
    except ValueError:
        return False, "bad webhook url (needs https://)"
    except Exception as exc:
        return False, type(exc).__name__

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--execute" not in argv:
        log("must be invoked by Splunk as an alert action (--execute); direct run not supported")
        return 1
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        log("failed to parse stdin payload JSON")
        return 2
    cfg = payload.get("configuration", {}) or {}
    app = payload.get("app") or APP_DEFAULT
    rows = parse_results(payload.get("results_file", ""))
    if rows is None:
        log("results file present but unreadable; failing the action (Splunk records it as failed)")
        return 5
    if not rows:
        note("no results; nothing to send")
        return 0
    session_key = payload.get("session_key", "")
    server_uri = payload.get("server_uri", "")
    webhook = resolve_webhook(cfg, session_key, server_uri, APP_DEFAULT)
    if not webhook:
        log("no webhook configured; set it in Set up or the alert's webhook_url param")
        return 3
    base_url = resolve_base_url(session_key, server_uri, APP_DEFAULT)
    link = build_results_url(base_url, payload.get("results_link", ""), app,
                             str(payload.get("sid", "")))
    ui = _ui_origin(base_url, payload.get("results_link", ""))
    msg = build_slack_payload(payload.get("search_name", "CIP TI Feed"), rows, cfg, link,
                              ui_origin=ui, app=APP_DEFAULT)
    ok, detail = post_webhook(webhook, msg)
    if ok:
        note(f"sent rows={len(rows)} {detail}")
        return 0
    log(f"send failed {detail}")
    return 4

if __name__ == "__main__":
    raise SystemExit(main())

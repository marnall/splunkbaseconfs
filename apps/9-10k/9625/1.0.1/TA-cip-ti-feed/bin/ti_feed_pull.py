#!/usr/bin/env python3
from __future__ import annotations

import argparse
import calendar
import csv
import json
import os
import re
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_a: object, **_k: object) -> bool:
        return False

BASES = {"LIVE": "https://dl.criminalip.io", "TEST": "https://test-dl.criminalip.io"}
STATUS_PATH = "/ti/v1/feed/status"
FEED_PATH = "/ti/v1/feed/{direction}"
DIRECTIONS = ("inbound", "outbound")
PROFILES = ("block", "monitor")
_LIMIT_MAX = 50000
CSV_HEADER = ["ip", "profile", "confidence", "reason", "feed_version",
              "profiles", "reasons", "first_seen_min", "last_seen_max", "score_max"]

_RETRYABLE_CODES = (1000, 1005)
_RETRY_WAITS = (15, 45)
_REQUEST_SPACING = 2

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_KEPT_STALE = 3
EXIT_WROTE_PARTIAL = 4
EXIT_STATUS_UNAVAILABLE = 5

SHRINK_RATIO = 0.5

_CODE_MSG = {1000: "quota exceeded", 1001: "invalid params", 1002: "invalid license",
             1005: "feed not ready", 9099: "server exception"}

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_CTX = ssl.create_default_context()

def _mask(k: str) -> str:
    return f"set(len={len(k)})" if k else "(empty)"

def _redact(text: str, secret: str) -> str:
    if not secret:
        return text
    out = text.replace(secret, "***")
    enc = urllib.parse.quote(secret, safe="")
    return out.replace(enc, "***") if enc != secret else out

def _coerce_conf(v: Any) -> int:
    if isinstance(v, bool):
        return 0
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return 0

def _clean_reason(text: str) -> str:
    s = re.sub(r'[\r\n"\x00-\x1f]+', " ", str(text))
    return s.encode("ascii", "replace").decode("ascii").strip()[:160]

def _get(url: str, timeout: int = 60) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, raw[:500]
    except urllib.error.HTTPError as exc:
        return exc.code, f"HTTPError {exc.code}: {exc.reason}"
    except Exception as exc:
        return -1, f"{type(exc).__name__}: {exc}"

def _status_url(base: str, key: str) -> str:
    return f"{base}{STATUS_PATH}?" + urllib.parse.urlencode({"key": key})

def _feed_url(base: str, direction: str, key: str, profile: str,
              confidence: int, limit: int) -> str:
    q = urllib.parse.urlencode(
        {"key": key, "profile": profile, "confidence": confidence,
         "limit": limit, "format": "json"}
    )
    return f"{base}{FEED_PATH.format(direction=direction)}?{q}"

def _check_code(resp: Any) -> tuple[bool, str]:
    if not isinstance(resp, dict):
        return False, f"non-JSON: {str(resp)[:120]}"
    code = resp.get("code")
    if code in (200, "200"):
        return True, "ok"
    return False, f"code={code} {_CODE_MSG.get(code, '')}".strip()

def _coerce_score(v: Any) -> str:
    try:
        return f"{float(v):g}"
    except (TypeError, ValueError):
        return ""

def _coerce_seen(v: Any) -> str:
    s = str(v or "").strip().replace("T", " ", 1)
    return s[:19].strip()

def _rec(d: dict[str, Any]) -> dict[str, Any] | None:
    ip = str(d.get("ip") or "").strip()
    if not ip:
        return None
    return {
        "ip": ip,
        "confidence": _coerce_conf(d.get("confidence")),
        "score": _coerce_score(d.get("score")),
        "reason": str(d.get("reason") or "").strip(),
        "first_seen": _coerce_seen(d.get("first_seen")),
        "last_seen": _coerce_seen(d.get("last_seen")),
    }

def _sleep(seconds: float) -> None:
    time.sleep(seconds)

def _existing_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return max(0, sum(1 for _ in f) - 1)
    except OSError:
        return 0

def _get_retry(url: str, label: str, key: str) -> tuple[bool, Any, int, int]:
    why: Any = ""
    st = -1
    for i in range(len(_RETRY_WAITS) + 1):
        st, resp = _get(url)
        ok, why = _check_code(resp) if st == 200 else (False, f"http={st}: {resp}")
        if ok:
            return True, resp, i + 1, st
        code = resp.get("code") if isinstance(resp, dict) else None
        retryable = (code in _RETRYABLE_CODES or st == 429 or st == -1
                     or (isinstance(st, int) and st >= 500))
        if not retryable or i == len(_RETRY_WAITS):
            return False, why, i + 1, st
        wait = _RETRY_WAITS[i]
        print(f"  - [{label}] {_clean_reason(_redact(str(why), key))} - retrying in {wait}s "
              f"({i + 2}/{len(_RETRY_WAITS) + 1})", file=sys.stderr)
        _sleep(wait)
    return False, why, len(_RETRY_WAITS) + 1, st

def _fetch_feed(base: str, direction: str, key: str, profile: str,
                confidence: int, limit: int) -> tuple[bool, Any, int]:
    ok, resp, attempts, _st = _get_retry(
        _feed_url(base, direction, key, profile, confidence, limit),
        f"{direction}/{profile}", key)
    return ok, resp, attempts

def _clamp_limit(limit: int) -> int:
    if limit > _LIMIT_MAX:
        print(f"  - limit {limit} is over the API maximum {_LIMIT_MAX} - clamped to {_LIMIT_MAX}",
              file=sys.stderr)
        return _LIMIT_MAX
    return max(1, limit)

_SEEN_UTC_OFFSET = 9 * 3600
_SEEN_AHEAD_SLACK = 900

def _epoch_utc(s: str, fmts: tuple[str, ...] = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")) -> int | None:
    s = str(s or "").strip().replace("T", " ", 1)[:19]
    for fmt in fmts:
        try:
            return calendar.timegm(time.strptime(s, fmt))
        except ValueError:
            continue
    return None

def _check_feed_clocks(direction: str, profile: str, gen_at: str, fv: str, seen_max: str) -> None:
    seen = _epoch_utc(seen_max)
    if seen is None:
        return
    seen_utc = seen - _SEEN_UTC_OFFSET
    stamp = _epoch_utc(fv, ("%Y%m%d_%H%M",))
    gen = _epoch_utc(gen_at)
    print(f"cip_ti_feedsync event=feed_clock direction={direction} profile={profile} "
          f"last_seen_max=\"{seen_max}\" feed_version={fv or '-'} generated_at=\"{gen_at or '-'}\" "
          f"stamp_gap_seconds={seen_utc - stamp if stamp is not None else '-'} "
          f"gen_gap_seconds={seen_utc - gen if gen is not None else '-'}")
    if gen is not None and seen_utc - gen > _SEEN_AHEAD_SLACK:
        print(f"  WARNING: [{direction}/{profile}] last_seen {seen_max} (read as KST) is "
              f"{seen_utc - gen}s after generated_at {gen_at} (read as UTC). A snapshot cannot "
              f"hold observations from after it was built - the feed's clocks may have changed. "
              f"Check the two tz macros in default/macros.conf.", file=sys.stderr)

def _report_truncation(direction: str, profile: str, limit: int, at_limit: int,
                       raw_n: int, sc: int | None, tc: int) -> None:
    if isinstance(sc, int) and sc > limit:
        print(f"  [{direction}/{profile}] TRUNCATED - status reports {sc} entries "
              f"but only {limit} were requested. {sc - limit} were not received. "
              f"Fetch the remainder in batches with `updated_after`.", file=sys.stderr)
        print(f"cip_ti_feedsync event=feed_truncated direction={direction} "
              f"profile={profile} feed_total={sc} asked_limit={limit} "
              f"missing={sc - limit} source=status")
    elif tc > limit:
        print(f"  [{direction}/{profile}] TRUNCATED - the feed reports {tc} entries "
              f"but only {limit} were requested. {tc - limit} were not received. "
              f"Fetch the remainder in batches with `updated_after`.", file=sys.stderr)
        print(f"cip_ti_feedsync event=feed_truncated direction={direction} "
              f"profile={profile} feed_total={tc} asked_limit={limit} "
              f"missing={tc - limit} source=meta")
    elif tc < 0 and at_limit:
        print(f"  - [{direction}/{profile}] {raw_n} rows = the requested limit "
              f"({limit}). The response carries no total_count, so completeness cannot "
              f"be judged.", file=sys.stderr)

def pull_direction(base: str, direction: str, key: str,
                   confidence: int, limit: int,
                   feed_counts: dict[tuple[str, str], int] | None = None
                   ) -> tuple[dict[str, dict], int]:
    limit = _clamp_limit(limit)
    merged: dict[str, dict[str, Any]] = {}
    feed_version = ""
    ok_profiles = 0
    for idx, profile in enumerate(PROFILES):
        if idx:
            _sleep(_REQUEST_SPACING)
        ok, resp, attempts = _fetch_feed(base, direction, key, profile, confidence, limit)
        if not ok:
            reason = _clean_reason(_redact(str(resp), key))
            print(f"  [{direction}/{profile}] FAIL - {reason}", file=sys.stderr)
            print(f"cip_ti_feedsync event=feed_error direction={direction} "
                  f"profile={profile} attempts={attempts} reason=\"{reason}\"")
            continue
        body = resp.get("body")
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(body, dict) or (data is not None and not isinstance(data, list)):
            reason = (f"200 with a malformed envelope (body={type(body).__name__}, "
                      f"data={type(data).__name__})")
            print(f"  [{direction}/{profile}] FAIL - {reason}", file=sys.stderr)
            print(f"cip_ti_feedsync event=feed_error direction={direction} "
                  f"profile={profile} attempts={attempts} reason=\"{reason}\"")
            continue
        rbody = body
        data = data or []
        if not data:
            print(f"  [{direction}/{profile}] FAIL - HTTP 200 but data was empty. "
                  f"The lookup is kept as it is rather than overwritten with a partial feed.",
                  file=sys.stderr)
            print(f"cip_ti_feedsync event=feed_error direction={direction} "
                  f"profile={profile} attempts={attempts} reason=\"200 with empty data\"")
            continue
        meta = rbody.get("meta")
        meta = meta if isinstance(meta, dict) else {}
        raw_n = len(data)
        at_limit = 1 if raw_n >= limit else 0
        try:
            _tc = int(float(str(meta.get("total_count")).strip()))
        except (TypeError, ValueError):
            _tc = -1
        _sc = (feed_counts or {}).get((direction, profile))
        if isinstance(_sc, int) and _sc > 0 and raw_n < max(1, _sc * SHRINK_RATIO):
            reason = (f"shrunk: status reports {_sc} entries but {raw_n} arrived "
                      f"(under {int(SHRINK_RATIO * 100)}%)")
            print(f"  [{direction}/{profile}] FAIL - {reason}. The lookup is kept as it is "
                  f"rather than overwritten with a partial feed.", file=sys.stderr)
            print(f"cip_ti_feedsync event=feed_error direction={direction} "
                  f"profile={profile} attempts={attempts} reason=\"{reason}\"")
            _report_truncation(direction, profile, limit, at_limit, raw_n, _sc, _tc)
            continue
        ok_profiles += 1
        fv = str(meta.get("feed_version") or "")
        total_count = meta.get("total_count")
        sent_count = meta.get("count")
        if ok_profiles == 1:
            perms = meta.get("feed_permissions")
            perms = perms if isinstance(perms, list) else []
            print(f"cip_ti_feedsync event=feed_plan direction={direction} profile={profile} "
                  f"plan=\"{meta.get('plan')}\" permission_count={len(perms)} "
                  f"permissions=\"{'|'.join(str(x) for x in perms)}\" "
                  f"ttl_hours={meta.get('ttl_hours')} stale={meta.get('stale')} "
                  f"meta_keys=\"{'|'.join(sorted(meta))}\"")
        gen_at = str(meta.get("generated_at") or "")
        feed_version = fv or feed_version
        n = 0
        seen_max = ""
        for raw in data:
            rec = _rec(raw) if isinstance(raw, dict) else None
            if rec is None:
                continue
            n += 1
            if rec["last_seen"] > seen_max:
                seen_max = rec["last_seen"]
            cur = merged.get(rec["ip"])
            if cur is None:
                merged[rec["ip"]] = {
                    "ip": rec["ip"], "profile": profile,
                    "confidence": rec["confidence"], "reason": rec["reason"],
                    "score_max": rec["score"],
                    "profiles": {profile},
                    "reasons": {rec["reason"]} if rec["reason"] else set(),
                    "first_seen_min": rec["first_seen"], "last_seen_max": rec["last_seen"],
                }
                continue
            cur["profiles"].add(profile)
            if rec["reason"]:
                cur["reasons"].add(rec["reason"])
            if rec["confidence"] > cur["confidence"]:
                cur["confidence"] = rec["confidence"]
            if profile == "block":
                cur["profile"] = "block"
                if rec["reason"]:
                    cur["reason"] = rec["reason"]
            fs = rec["first_seen"]
            if fs and (not cur["first_seen_min"] or fs < cur["first_seen_min"]):
                cur["first_seen_min"] = fs
            if rec["last_seen"] > cur["last_seen_max"]:
                cur["last_seen_max"] = rec["last_seen"]
            try:
                if rec["score"] and float(rec["score"]) > float(cur["score_max"] or 0):
                    cur["score_max"] = rec["score"]
            except ValueError:
                pass
        print(f"cip_ti_feedsync event=feed_pull direction={direction} profile={profile} "
              f"rows={n} raw_rows={raw_n} asked_limit={limit} at_limit={at_limit} "
              f"total_count={total_count if total_count is not None else '-'} "
              f"sent_count={sent_count if sent_count is not None else '-'} "
              f"generated_at=\"{gen_at or '-'}\" "
              f"feed_version={fv or '-'} meta_keys={'|'.join(sorted(meta)) or '-'}")
        _check_feed_clocks(direction, profile, gen_at, fv, seen_max)
        try:
            if sent_count is not None and int(sent_count) > raw_n:
                print(f"  WARNING: [{direction}/{profile}] feed said it sent {sent_count} but "
                      f"{raw_n} arrived - rows were lost in transit or parsing.",
                      file=sys.stderr)
        except (TypeError, ValueError):
            pass
        _report_truncation(direction, profile, limit, at_limit, raw_n, _sc, _tc)
    for row in merged.values():
        row["feed_version"] = feed_version
    return merged, ok_profiles

def write_csv(path: Path, rows: dict[str, dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    _um = os.umask(0)
    os.umask(_um)
    try:
        os.chmod(tmp, 0o666 & ~_um)
    except OSError:
        pass
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADER)
            w.writeheader()
            for r in sorted(rows.values(), key=lambda x: x["ip"]):
                w.writerow({
                    "ip": r["ip"], "profile": r["profile"], "confidence": r["confidence"],
                    "reason": r["reason"], "feed_version": r.get("feed_version", ""),
                    "profiles": "|".join(sorted(r["profiles"])),
                    "reasons": "|".join(sorted(r["reasons"])),
                    "first_seen_min": r["first_seen_min"], "last_seen_max": r["last_seen_max"],
                    "score_max": r.get("score_max", ""),
                })
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    return len(rows)

_KEY_VAR_NAMES = {"CRIMINALIP_TI_KEY", "CRIMINALIP_TI_KEY_LIVE", "KEY"}

def resolve_key(env_name: str, key_file: str | None) -> str:
    if key_file:
        try:
            text = Path(key_file).read_text(encoding="utf-8-sig")
        except OSError as exc:
            print(f"ERROR: cannot read key file {key_file} ({type(exc).__name__})",
                  file=sys.stderr)
            return ""
        known = _KEY_VAR_NAMES | {env_name.upper()}
        for raw in text.splitlines():
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            if "=" in s and s.split("=", 1)[0].strip().upper() in known:
                return s.split("=", 1)[1].strip()
            return s
        return ""
    return (os.environ.get(env_name) or "").strip()

def print_status(base: str, key: str) -> tuple[bool, dict[tuple[str, str], int]]:
    counts: dict[tuple[str, str], int] = {}
    ok, resp, attempts, st = _get_retry(_status_url(base, key), "status", key)
    if not ok:
        reason = _clean_reason(_redact(str(resp), key))
        print(f"[status] FAIL http={st} attempts={attempts} - {reason}")
        print(f"cip_ti_feedsync event=feed_error direction=- profile=- stage=status "
              f"attempts={attempts} reason=\"{reason}\"")
        return False, counts
    print(f"[status] http={st} -> OK")
    if isinstance(resp, dict):
        b = resp.get("body")
        b = b if isinstance(b, dict) else {}
        print(f"  feed_version={b.get('feed_version')} ttl_hours={b.get('ttl_hours')}")
        print(f"cip_ti_feedsync event=feed_status_meta "
              f"body_keys=\"{'|'.join(sorted(b)) if isinstance(b, dict) else ''}\" "
              f"ttl_hours={b.get('ttl_hours')}")
        feeds = b.get("feeds")
        for fd in feeds if isinstance(feeds, list) else []:
            if not isinstance(fd, dict):
                continue
            print(f"  - {fd.get('direction')}/{fd.get('profile')}: "
                  f"available={fd.get('available')} count={fd.get('count')} "
                  f"stale={fd.get('stale')} v={fd.get('feed_version')}")
            print(f"cip_ti_feedsync event=feed_status "
                  f"direction={fd.get('direction')} profile={fd.get('profile')} "
                  f"feed_count={fd.get('count')} available={fd.get('available')} "
                  f"stale={fd.get('stale')} generated_at=\"{fd.get('generated_at')}\" "
                  f"feed_version={fd.get('feed_version')}")
            try:
                counts[(str(fd.get("direction")), str(fd.get("profile")))] = int(
                    float(str(fd.get("count")).strip()))
            except (TypeError, ValueError):
                pass
    return ok, counts

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="CIP TI Feed to Splunk lookup CSV pull")
    p.add_argument("--env", choices=["LIVE", "TEST"], default=None,
                   help="default = CRIMINALIP_TI_ENV (live|test), otherwise live")
    p.add_argument("--base", default=None, help="override base URL")
    p.add_argument("--out-dir", default=".",
                   help="directory the cip_ti_{inbound,outbound}.csv files are written to")
    p.add_argument("--confidence", type=int, default=70)
    p.add_argument("--limit", type=int, default=_LIMIT_MAX)
    p.add_argument("--probe", action="store_true",
                   help="query status only: checks the key, endpoint and availability "
                        "without spending feed quota")
    p.add_argument("--key-file", default=None,
                   help="path to a file holding the license key: first non-empty "
                        "line, either `KEY=value` or the raw value. For injecting the secret "
                        "into a Splunk scripted input; chmod 600. Falls back to the "
                        "environment.")
    args = p.parse_args(argv)

    load_dotenv()
    env = (args.env or os.environ.get("CRIMINALIP_TI_ENV") or "LIVE").strip().upper()
    if env not in BASES:
        env = "LIVE"
    key_var = "CRIMINALIP_TI_KEY_LIVE" if env == "LIVE" else "CRIMINALIP_TI_KEY"
    key = resolve_key(key_var, args.key_file)
    base = args.base or BASES[env]
    if not key:
        src = args.key_file or f"env {key_var} (.env)"
        print(f"ERROR: no Criminal IP TI Feed License (API Key) (source={src})", file=sys.stderr)
        return EXIT_CONFIG
    if args.limit < 1:
        print(f"ERROR: --limit must be between 1 and {_LIMIT_MAX} (got {args.limit})",
              file=sys.stderr)
        print(f"cip_ti_feedsync event=config_invalid key=feed_limit value=\"{args.limit}\"")
        return EXIT_CONFIG
    print(f"env={env} base={base} key={_mask(key)} confidence={args.confidence}")

    ok, feed_counts = print_status(base, key)
    if args.probe:
        return EXIT_OK if ok else EXIT_STATUS_UNAVAILABLE
    if not ok:
        print("status check failed - verify the key, endpoint and network access, then "
              "retry. The whole pull is stopped.", file=sys.stderr)
        return EXIT_STATUS_UNAVAILABLE

    out = Path(args.out_dir)
    total = 0
    kept = 0
    partial = 0
    for d_idx, direction in enumerate(DIRECTIONS):
        if d_idx:
            _sleep(_REQUEST_SPACING)
        print(f"[{direction}]")
        rows, ok_profiles = pull_direction(base, direction, key, args.confidence, args.limit,
                                           feed_counts)
        target = out / f"cip_ti_{direction}.csv"
        if ok_profiles < len(PROFILES) or not rows:
            have = _existing_rows(target)
            if rows and have == 0:
                n = _write_or_report(target, rows, direction)
                if n < 0:
                    kept += 1
                    continue
                total += n
                partial += 1
                print(f"  WARNING: {direction}: {ok_profiles}/{len(PROFILES)} profiles ok - "
                      f"the existing lookup is empty (header only), so there is nothing to "
                      f"protect. Writing the {n} rows received (partial).", file=sys.stderr)
                print(f"  -> {target}  ({n} unique IPs, PARTIAL)")
                print(f"cip_ti_feedsync event=feed_partial direction={direction} "
                      f"ok_profiles={ok_profiles} of={len(PROFILES)} rows={n} "
                      f"kept_rows=0 action=wrote_partial reason=profile_failed")
                continue
            print(f"  WARNING: {direction}: {ok_profiles}/{len(PROFILES)} profiles ok, "
                  f"{len(rows)} rows - lookup not updated, the existing {have} rows are kept",
                  file=sys.stderr)
            print(f"cip_ti_feedsync event=feed_partial direction={direction} "
                  f"ok_profiles={ok_profiles} of={len(PROFILES)} rows={len(rows)} "
                  f"kept_rows={have} action=kept_existing reason=profile_failed")
            kept += 1
            continue
        have = _existing_rows(target)
        if have > 0 and len(rows) < have * SHRINK_RATIO:
            print(f"  WARNING: {direction}: {len(rows)} rows received but the existing "
                  f"lookup has {have} - under {int(SHRINK_RATIO * 100)}%, so the lookup is "
                  f"kept as it is. Check feed_limit and the feed itself.", file=sys.stderr)
            print(f"cip_ti_feedsync event=feed_partial direction={direction} "
                  f"ok_profiles={ok_profiles} of={len(PROFILES)} rows={len(rows)} "
                  f"kept_rows={have} action=kept_existing reason=shrunk")
            kept += 1
            continue
        n = _write_or_report(target, rows, direction)
        if n < 0:
            kept += 1
            continue
        total += n
        print(f"  -> {target}  ({n} unique IPs)")
    if partial or kept:
        print(f"FAILED: {partial + kept}/{len(DIRECTIONS)} feeds not fully updated "
              f"(kept={kept} partial={partial}) - see the warnings above", file=sys.stderr)
        return EXIT_WROTE_PARTIAL if partial else EXIT_KEPT_STALE
    print(f"done: {total} rows across {len(DIRECTIONS)} feeds")
    return EXIT_OK

def _write_or_report(target: Path, rows: dict[str, dict], direction: str) -> int:
    try:
        return write_csv(target, rows)
    except OSError as exc:
        reason = _clean_reason(f"{type(exc).__name__}: {exc}")
        print(f"  {direction}: FAIL - could not write {target.name} ({reason}). "
              f"The existing lookup is kept.", file=sys.stderr)
        print(f"cip_ti_feedsync event=feed_write_error direction={direction} "
              f"file=\"{target.name}\" rows={len(rows)} reason=\"{reason}\"")
        return -1

if __name__ == "__main__":
    raise SystemExit(main())

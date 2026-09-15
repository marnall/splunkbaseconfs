#!/usr/bin/env python
from __future__ import annotations

import sys

import cip_ti_setup as H
import cip_ti_sources as src

_TAG = "cip_ti_feedsync event=macro_heal"

_FAIL_TOKEN = "FAIL"

def out(msg: str) -> None:
    sys.stdout.write(f"{_TAG} {msg}\n")

def _recoverable_sources(current: dict) -> list:
    return list(current.get("sources") or []) or src.adopt(
        current.get("fw_index", ""), current.get("fw_sourcetype", ""))

def heal(rest) -> int:
    current = H.load_current(rest)
    sources = _recoverable_sources(current)
    state = src.classify(current.get("macro_fwd", ""), current.get("macro_loc", ""),
                         list(current.get("sources") or []), current.get("vendor", ""),
                         current.get("fw_index", ""), current.get("fw_sourcetype", ""))

    if state != src.DEFAULTS:
        out(f"action=none state={state} sources={len(sources)}")
        return 0
    if not sources:
        out(f"action=none state={state} sources=0 reason=nothing_configured")
        return 0

    bad = H.validate({}, [{"index": s.index, "sourcetype": s.sourcetype} for s in sources])
    if bad:
        out(f'action=none state={state} sources={len(sources)}'
            f' reason=invalid_sources detail="{bad[:120]}"')
        return 0

    vendor = src.vendor_or_default(current.get("vendor"))
    fwd, loc = src.generate(sources, vendor)
    shipped_fwd, shipped_loc = src.generate(
        [src.Source(src.SHIPPED_INDEX, src.SHIPPED_SOURCETYPE)], src.DEFAULT_VENDOR)

    def put(name: str, definition: str) -> int:
        status, _text = rest("POST", f"configs/conf-macros/{H._q(name)}",
                             {"definition": definition})
        return status

    first = put(H.MACRO_FWD, fwd)
    if not (200 <= first < 300):
        out(f"action=none state={state} sources={len(sources)} {_FAIL_TOKEN}"
            f' reason=write_failed step=1 detail="{H.MACRO_FWD}:{first}"')
        return 1

    second = put(H.MACRO_LOC, loc)
    if 200 <= second < 300:
        out(f"action=healed state={src.MACROS_RESET} sources={len(sources)}"
            f" vendor={vendor} wrote=2")
        return 0

    undo = put(H.MACRO_FWD, shipped_fwd)
    if 200 <= undo < 300:
        out(f"action=rolled_back state={state} sources={len(sources)} {_FAIL_TOKEN}"
            f' reason=write_failed step=2 detail="{H.MACRO_LOC}:{second}"')
        return 1
    out(f"action=partial_stuck state={state} sources={len(sources)} {_FAIL_TOKEN}"
        f' reason=rollback_failed detail="{H.MACRO_LOC}:{second} undo:{undo}"')
    return 1

def main() -> int:
    session = sys.stdin.readline().strip()
    if not session:
        out("action=none reason=no_session_key")
        return 0
    token = session.split(None, 1)[1] if session.lower().startswith("splunk ") else session
    try:
        return heal(H.make_rest(token))
    except Exception as exc:
        out(f'action=none {_FAIL_TOKEN} reason=error detail="{str(exc)[:120]}"')
        return 0

if __name__ == "__main__":
    raise SystemExit(main())

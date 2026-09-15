#!/usr/bin/env python3
from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

MGMT = "https://127.0.0.1:8089"
APP = "TA-cip-ti-feed"
USERNAME = "cip_key"

def entry_url() -> str:
    name = urllib.parse.quote(f":{USERNAME}:", safe="")
    return f"{MGMT}/servicesNS/nobody/{APP}/storage/passwords/{name}?output_mode=json"

def main(stdin=None, stdout=None) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    session = stdin.readline().strip()
    if not session:
        return 2
    token = session.split(None, 1)[1] if session.lower().startswith("splunk ") else session

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(entry_url(), headers={"Authorization": f"Splunk {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        return 4 if exc.code == 404 else 3
    except Exception:
        return 3

    entries = data.get("entry") if isinstance(data, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        content = (entry.get("content") if isinstance(entry, dict) else None) or {}
        if content.get("username") == USERNAME:
            pw = content.get("clear_password") or ""
            if pw:
                stdout.write(pw)
                return 0
    return 4

if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
"""Aegisyst for Splunk — scheduled input.

Pulls approved Sigma-derived SPL rules from the customer's Aegisyst tenant
and logs each response payload to `$SPLUNK_HOME/var/log/splunk/aegisyst.log`.

Runs on the schedule defined in `default/inputs.conf` (every 6 hours by
default). The `Aegisyst API Key` is read from the app's `aegisyst.conf`
which is written by the Setup screen (see `default/setup.xml`).

To trigger a manual pull without waiting for the schedule, run:
    $SPLUNK_HOME/bin/splunk cmd python $SPLUNK_HOME/etc/apps/aegisyst_for_splunk/bin/aegisyst_pull.py
"""
from __future__ import annotations
import json
import logging
import logging.handlers
import os
import sys
import ssl
from urllib import request as urlrequest, error as urlerror

APP_NAME = "aegisyst_for_splunk"

# ---------- logging -------------------------------------------------------
SPLUNK_HOME = os.environ.get("SPLUNK_HOME", "/opt/splunk")
LOG_PATH = os.path.join(SPLUNK_HOME, "var", "log", "splunk", "aegisyst.log")

# Fall back to stdout if the log dir isn't writable (e.g. running outside Splunk).
try:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
except OSError:
    handler = logging.StreamHandler(sys.stdout)

handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s aegisyst_pull %(message)s"
))
log = logging.getLogger("aegisyst_pull")
log.setLevel(logging.INFO)
log.addHandler(handler)


# ---------- config --------------------------------------------------------
def _read_conf():
    """Read the app's aegisyst.conf. Splunk merges default/ + local/ but here
    we do the merge manually so the script also runs outside Splunk."""
    import configparser

    conf = {"api_key": "", "hec_url": "", "aegisyst_api_url": "https://aegisyst.com"}
    app_dir = os.path.join(SPLUNK_HOME, "etc", "apps", APP_NAME)
    # Allow running the script from any location by walking up.
    if not os.path.isdir(app_dir):
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_app_dir = os.path.dirname(here)
        if os.path.basename(maybe_app_dir) == APP_NAME:
            app_dir = maybe_app_dir

    for scope in ("default", "local"):
        cfg_path = os.path.join(app_dir, scope, "aegisyst.conf")
        if not os.path.isfile(cfg_path):
            continue
        parser = configparser.RawConfigParser()
        parser.read(cfg_path)
        if parser.has_section("aegisyst"):
            for k in conf.keys():
                if parser.has_option("aegisyst", k):
                    v = parser.get("aegisyst", k).strip()
                    if v:
                        conf[k] = v
    return conf


# ---------- HTTP ----------------------------------------------------------
def fetch_rules(api_key: str, api_base: str) -> dict:
    url = api_base.rstrip("/") + "/api/v1/spl/deploy"
    body = json.dumps({}).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "User-Agent": "AegisystForSplunk/1.0.0",
        },
    )
    # Splunk's bundled Python may lack a proper CA bundle on some platforms;
    # fall back to the system default context.
    ctx = ssl.create_default_context()
    with urlrequest.urlopen(req, timeout=30, context=ctx) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


# ---------- main ----------------------------------------------------------
def main() -> int:
    conf = _read_conf()
    api_key = conf.get("api_key", "").strip()
    api_base = conf.get("aegisyst_api_url", "https://aegisyst.com").strip()

    if not api_key:
        log.error("No API key configured. Set it in Manager → Aegisyst for Splunk → Set up.")
        return 1

    log.info("pull start api_base=%s", api_base)
    try:
        data = fetch_rules(api_key, api_base)
    except urlerror.HTTPError as e:
        log.error("aegisyst api error http=%s body=%s", e.code, e.read().decode("utf-8", "ignore"))
        return 2
    except Exception as e:  # noqa: BLE001
        log.error("aegisyst api error unexpected=%s", e)
        return 3

    total = data.get("total", 0)
    skipped = data.get("skipped", 0)
    rules = data.get("rules", []) or []

    log.info(
        "pull ok customer_id=%s total=%d skipped=%d",
        data.get("customer_id", "?"), total, skipped,
    )

    # Log each rule payload as a single-line JSON event so Splunk can index them.
    for r in rules:
        log.info(
            "rule id=%s name=%r severity=%s techniques=%s spl=%r",
            r.get("id"), r.get("name"), r.get("severity"),
            ",".join(r.get("technique_ids", []) or []),
            (r.get("spl") or "").replace("\n", " ⏎ "),
        )

    log.info("pull complete rules=%d", len(rules))
    return 0


if __name__ == "__main__":
    sys.exit(main())

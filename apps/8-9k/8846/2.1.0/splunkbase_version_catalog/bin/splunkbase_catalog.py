#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Splunkbase Version Catalog - modular input.

Polls the public Splunkbase v1 API and maintains a local catalogue of app
versions in a KV Store collection (``splunkbase_catalog``). One event per app
is also emitted on every run so a historical trend is retained in the index.

The script uses only the Python 3 standard library, so the app is fully
self-contained and friendly to Splunk Cloud AppInspect vetting (no bundled
third-party packages to review).

Modular input protocol implemented here:
  * ``--scheme``              -> print the input scheme
  * ``--validate-arguments``  -> validate proposed configuration (stdin XML)
  * (no args)                 -> read run configuration from stdin and run
                                 as a persistent daemon (see below)

Scheduling: this input runs with ``use_single_instance = true`` - Splunk
starts ONE long-lived process for all enabled stanzas together and expects
that process to manage its own repeat schedule; it does not restart the
script on a timer the way ``use_single_instance = false`` inputs do. Each
stanza has a fixed daily ``run_at`` time (24-hour HH:MM, search head local
time) instead of a seconds-based interval, since a plain interval measured
from "last run" drifts and doesn't match most people's expectation of a
fixed daily refresh. The process wakes up once a minute, and for each
stanza checks whether today's ``run_at`` has passed and it hasn't already
run today; if so it collects and records today's date in a small checkpoint
file (one per stanza, under Splunk's checkpoint directory for this input) so
a restart mid-day - or Splunk itself restarting - never causes a double run
or a skipped day.

The TLS verification of the local management endpoint (https://127.0.0.1:8089)
is disabled on purpose: splunkd presents a self-signed certificate on the
loopback management port. Outbound calls to Splunkbase are verified by default
and controlled by the ``verify_ssl`` input parameter.
"""

import json
import logging
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

APP_NAME = "splunkbase_version_catalog"
COLLECTION = "splunkbase_catalog"
SOURCETYPE = "splunkbase:catalog"
SB_API = "https://splunkbase.splunk.com/api/v1/app"
USER_AGENT = "Splunkbase-Version-Catalog/2.0 (Splunk modular input)"
HTTP_TIMEOUT = 60
PAGE_SIZE = 100
RELEASE_PAGE_LIMIT = 200     # single generous page; releases per app rarely exceed this
REQUEST_PAUSE = 0.3          # be gentle with the public API
KV_BATCH = 500               # records per KV Store batch_save call
POLL_SECONDS = 60            # how often the daemon wakes up to check run_at
DEFAULT_RUN_AT = "03:15"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [splunkbase_catalog] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("splunkbase_catalog")

TRUE_SET = ("1", "true", "yes", "t", "on")

SCHEME = """<scheme>
  <title>Splunkbase Version Catalog</title>
  <description>Builds a local catalogue of Splunkbase app versions in a KV Store.</description>
  <use_external_validation>true</use_external_validation>
  <streaming_mode>xml</streaming_mode>
  <use_single_instance>true</use_single_instance>
  <endpoint>
    <args>
      <arg name="app_ids">
        <title>Splunkbase app IDs</title>
        <description>Comma-separated Splunkbase numeric app IDs to track (the number in the app's Splunkbase URL, e.g. 833,2890). Leave empty and enable "Fetch all" to catalogue the entire Splunkbase listing.</description>
        <data_type>string</data_type>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="fetch_all">
        <title>Fetch all apps</title>
        <description>When true, paginates the entire Splunkbase listing instead of only the IDs above. This is heavy: roughly one request per app.</description>
        <data_type>boolean</data_type>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="max_apps">
        <title>Maximum apps (fetch all)</title>
        <description>Upper bound on how many apps to retrieve when "Fetch all" is enabled. Default 200.</description>
        <data_type>number</data_type>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="run_at">
        <title>Run at (24-hour HH:MM)</title>
        <description>Fixed daily time to refresh the catalogue, in the search head's local time zone, e.g. "03:15". Default "03:15" if left blank. This input is a single persistent process that wakes up about once a minute and fires once per day at this time, tracked in a checkpoint file so a restart never causes a double run or a skipped day.</description>
        <data_type>string</data_type>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="proxy_url">
        <title>Proxy URL</title>
        <description>Optional outbound HTTP(S) proxy, e.g. https://proxy.example.com:8080</description>
        <data_type>string</data_type>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="verify_ssl">
        <title>Verify TLS for Splunkbase</title>
        <description>Verify TLS certificates on outbound Splunkbase calls. Default true.</description>
        <data_type>boolean</data_type>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
    </args>
  </endpoint>
</scheme>
"""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in TRUE_SET


def version_key(value):
    """Return a sortable tuple of the integer parts of a version string."""
    parts = re.findall(r"\d+", value or "")
    return tuple(int(p) for p in parts) if parts else (0,)


def parse_dt(value):
    """Best-effort ISO 8601 -> epoch seconds. Returns 0 when unparseable."""
    if not value:
        return 0
    text = value.replace("Z", "+0000")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, fmt).timestamp()
        except ValueError:
            continue
    return 0


def read_stdin_xml():
    raw = sys.stdin.read()
    if not raw or not raw.strip():
        return None
    return ET.fromstring(raw)


_RUN_AT_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def parse_run_at(value):
    """Parse a 24-hour HH:MM string into an (hour, minute) tuple. Raises
    ValueError with a human-readable message on anything else."""
    text = (value or "").strip() or DEFAULT_RUN_AT
    match = _RUN_AT_RE.match(text)
    if not match:
        raise ValueError(
            "run_at must be a 24-hour HH:MM time, e.g. '03:15'; got '{0}'".format(value))
    return int(match.group(1)), int(match.group(2))


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def _build_opener(verify_ssl, proxy_url):
    ctx = ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()
    handlers = [urllib.request.HTTPSHandler(context=ctx)]
    if proxy_url:
        handlers.append(urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}))
    return urllib.request.build_opener(*handlers)


def http_get_json(url, verify_ssl=True, proxy_url=None):
    opener = _build_opener(verify_ssl, proxy_url)
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
        payload = resp.read()
    return json.loads(payload.decode("utf-8", "replace"))


def kvstore_batch_save(server_uri, session_key, records):
    """Upsert records into the KV Store collection. Each record carries a
    deterministic ``_key`` so repeated runs update in place rather than
    creating duplicates."""
    if not records:
        return 0
    url = "{base}/servicesNS/nobody/{app}/storage/collections/data/{coll}/batch_save".format(
        base=server_uri.rstrip("/"), app=APP_NAME, coll=COLLECTION)
    # loopback management port presents a self-signed cert
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    saved = 0
    for i in range(0, len(records), KV_BATCH):
        chunk = records[i:i + KV_BATCH]
        req = urllib.request.Request(
            url,
            data=json.dumps(chunk).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": "Splunk {0}".format(session_key),
                "Content-Type": "application/json",
            },
        )
        with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
            resp.read()
        saved += len(chunk)
    return saved


# ---------------------------------------------------------------------------
# Splunkbase data shaping
# ---------------------------------------------------------------------------
def normalize_releases(payload):
    if isinstance(payload, dict):
        return payload.get("results") or []
    if isinstance(payload, list):
        return payload
    return []


def pick_latest(releases):
    if not releases:
        return None

    def sort_key(rel):
        return (
            parse_dt(rel.get("published_datetime") or rel.get("created_datetime")),
            version_key(rel.get("title") or rel.get("name")),
        )

    return sorted(releases, key=sort_key)[-1]


def build_record(uid, meta, release, now_epoch):
    meta = meta or {}
    appid = meta.get("appid") or ""
    title = meta.get("title") or meta.get("name") or appid or str(uid)
    record = {
        "_key": str(uid),
        "app_uid": int(uid),
        "appid": appid,
        "title": title,
        "is_archived": bool(meta.get("is_archived")),
        "archive_status": meta.get("archive_status") or "",
        "app_url": "https://splunkbase.splunk.com/app/{0}/".format(uid),
        "last_checked": int(now_epoch),
        "latest_version": "",
        "release_id": None,
        "release_date": "",
        "splunk_versions": "",
        "min_splunk_version": "",
        "max_splunk_version": "",
        "cloud_compatible": False,
        "fedramp": "",
        "platform": "",
        "filename": "",
    }
    if release:
        versions = []
        for item in (release.get("product_versions") or []):
            if isinstance(item, dict):
                versions.append(str(item.get("name") or item.get("version") or ""))
            else:
                versions.append(str(item))
        versions = sorted([v for v in versions if v], key=version_key)
        record.update({
            "latest_version": release.get("title") or release.get("name") or "",
            "release_id": release.get("id"),
            "release_date": release.get("published_datetime")
            or release.get("created_datetime") or "",
            "splunk_versions": ",".join(versions),
            "min_splunk_version": versions[0] if versions else "",
            "max_splunk_version": versions[-1] if versions else "",
            "cloud_compatible": bool(release.get("cloud_compatible")),
            "fedramp": release.get("fedramp_validation") or "",
            "platform": release.get("platform") or "",
            "filename": release.get("filename") or "",
        })
    return record


def list_all_apps(max_apps, verify_ssl, proxy_url):
    apps = []
    offset = 0
    while len(apps) < max_apps:
        url = "{base}/?offset={off}&limit={lim}".format(base=SB_API, off=offset, lim=PAGE_SIZE)
        try:
            data = http_get_json(url, verify_ssl, proxy_url)
        except Exception as exc:  # noqa: BLE001
            log.error("Listing failed at offset %d: %s", offset, exc)
            break
        results = data.get("results") if isinstance(data, dict) else None
        total = data.get("total", 0) if isinstance(data, dict) else 0
        if not results:
            break
        apps.extend(results)
        offset += len(results)
        log.info("Fetched %d/%d records from Splunkbase listing", min(offset, total), total)
        if total and offset >= total:
            break
        time.sleep(REQUEST_PAUSE)
    return apps[:max_apps]


# ---------------------------------------------------------------------------
# Event streaming (XML protocol)
# ---------------------------------------------------------------------------
def emit_events(records, stanza):
    if not records:
        return
    stream = ET.Element("stream")
    for rec in records:
        event = ET.SubElement(stream, "event", {"stanza": stanza})
        ET.SubElement(event, "time").text = str(rec.get("last_checked", int(time.time())))
        ET.SubElement(event, "source").text = stanza
        ET.SubElement(event, "sourcetype").text = SOURCETYPE
        ET.SubElement(event, "data").text = json.dumps(rec, ensure_ascii=False)
        ET.SubElement(event, "done")
    sys.stdout.write(ET.tostring(stream, encoding="unicode"))
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Configuration parsing
# ---------------------------------------------------------------------------
def get_input_config():
    cfg = {
        "session_key": None,
        "server_uri": "https://127.0.0.1:8089",
        "checkpoint_dir": None,
        "stanzas": [],
    }
    root = read_stdin_xml()
    if root is None:
        return cfg
    session_key = root.find("session_key")
    if session_key is not None and session_key.text:
        cfg["session_key"] = session_key.text
    server_uri = root.find("server_uri")
    if server_uri is not None and server_uri.text:
        cfg["server_uri"] = server_uri.text
    checkpoint_dir = root.find("checkpoint_dir")
    if checkpoint_dir is not None and checkpoint_dir.text:
        cfg["checkpoint_dir"] = checkpoint_dir.text
    configuration = root.find("configuration")
    if configuration is not None:
        for stanza in configuration.findall("stanza"):
            params = {p.get("name"): p.text for p in stanza.findall("param")}
            cfg["stanzas"].append((stanza.get("name"), params))
    return cfg


def validate_arguments():
    """Reject obviously invalid configurations. Exit non-zero with a message
    on stderr to surface the error in Splunk Web."""
    try:
        root = read_stdin_xml()
        if root is None:
            return 0
        item = root.find("item")
        params = {}
        if item is not None:
            params = {p.get("name"): p.text for p in item.findall("param")}
        app_ids = (params.get("app_ids") or "").strip()
        if app_ids:
            for token in app_ids.split(","):
                token = token.strip()
                if token and not token.isdigit():
                    raise ValueError(
                        "app_ids must be a comma-separated list of numeric "
                        "Splunkbase IDs; got '{0}'".format(token))
        max_apps = (params.get("max_apps") or "").strip()
        if max_apps and (not max_apps.isdigit() or int(max_apps) < 1):
            raise ValueError("max_apps must be a positive integer")
        run_at = (params.get("run_at") or "").strip()
        if run_at:
            parse_run_at(run_at)
        if not app_ids and not as_bool(params.get("fetch_all")):
            raise ValueError(
                "Provide one or more app_ids, or enable 'Fetch all apps'.")
        return 0
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(str(exc))
        return 1


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------
def process_stanza(name, params, cfg):
    verify_ssl = as_bool(params.get("verify_ssl"), True)
    proxy_url = (params.get("proxy_url") or "").strip() or None
    fetch_all = as_bool(params.get("fetch_all"), False)
    try:
        max_apps = int((params.get("max_apps") or "200").strip())
    except ValueError:
        max_apps = 200
    app_ids_raw = (params.get("app_ids") or "").strip()

    targets = []  # list of (uid, meta_or_None)
    if fetch_all:
        for summary in list_all_apps(max_apps, verify_ssl, proxy_url):
            uid = summary.get("uid")
            if uid is not None:
                targets.append((uid, summary))
    if app_ids_raw:
        for token in app_ids_raw.split(","):
            token = token.strip()
            if token.isdigit():
                targets.append((int(token), None))

    if not targets:
        log.warning("Input %s: no app_ids and fetch_all disabled; nothing to do.", name)
        return

    now_epoch = time.time()
    records = []
    for uid, meta in targets:
        try:
            if meta is None:
                meta = http_get_json("{0}/{1}/".format(SB_API, uid), verify_ssl, proxy_url)
                time.sleep(REQUEST_PAUSE)
            releases = normalize_releases(
                http_get_json(
                    "{0}/{1}/release/?limit={2}".format(SB_API, uid, RELEASE_PAGE_LIMIT),
                    verify_ssl, proxy_url))
            records.append(build_record(uid, meta, pick_latest(releases), now_epoch))
            time.sleep(REQUEST_PAUSE)
        except urllib.error.HTTPError as exc:
            log.error("App %s: HTTP %s %s", uid, exc.code, exc.reason)
        except Exception as exc:  # noqa: BLE001
            log.error("App %s: %s", uid, exc)

    emit_events(records, name)

    if cfg.get("session_key"):
        try:
            saved = kvstore_batch_save(cfg["server_uri"], cfg["session_key"], records)
            log.info("Input %s: catalogued %d apps (KV Store upserts: %d)",
                     name, len(records), saved)
        except Exception as exc:  # noqa: BLE001
            log.error("KV Store save failed for %s: %s", name, exc)
    else:
        log.error("No session key supplied; cannot write to KV Store.")


# ---------------------------------------------------------------------------
# Scheduling (persistent daemon: use_single_instance = true)
# ---------------------------------------------------------------------------
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_-]")


def checkpoint_path(checkpoint_dir, stanza_name):
    safe = _SAFE_NAME_RE.sub("_", stanza_name or "default")
    return os.path.join(checkpoint_dir, "splunkbase_catalog_{0}.json".format(safe))


def read_last_run_date(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("last_run_date")
    except (OSError, ValueError):
        return None


def write_last_run_date(path, date_str):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump({"last_run_date": date_str}, fh)
    os.replace(tmp_path, path)


def should_run_now(hour_minute, last_run_date, now):
    hour, minute = hour_minute
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    today_str = now.strftime("%Y-%m-%d")
    return now >= scheduled and last_run_date != today_str


def maybe_run_stanza(name, params, cfg, checkpoint_dir):
    run_at_raw = (params.get("run_at") or "").strip()
    try:
        hour_minute = parse_run_at(run_at_raw)
    except ValueError as exc:
        log.error("Input %s: %s; skipping schedule check.", name, exc)
        return

    path = checkpoint_path(checkpoint_dir, name)
    last_run_date = read_last_run_date(path)
    now = datetime.now()
    if not should_run_now(hour_minute, last_run_date, now):
        return

    log.info("Input %s: run_at %s reached, starting collection.",
              name, run_at_raw or DEFAULT_RUN_AT)
    process_stanza(name, params, cfg)
    write_last_run_date(path, now.strftime("%Y-%m-%d"))


def run_forever(cfg):
    checkpoint_dir = cfg.get("checkpoint_dir") or "."
    try:
        os.makedirs(checkpoint_dir, exist_ok=True)
    except OSError as exc:
        log.error("Could not create checkpoint directory %s: %s", checkpoint_dir, exc)

    log.info("Splunkbase Version Catalog daemon started for %d stanza(s); checking every %ss.",
              len(cfg["stanzas"]), POLL_SECONDS)
    while True:
        for name, params in cfg["stanzas"]:
            try:
                maybe_run_stanza(name, params, cfg, checkpoint_dir)
            except Exception as exc:  # noqa: BLE001
                log.error("Input %s: unexpected error during schedule check: %s", name, exc)
        time.sleep(POLL_SECONDS)


def run():
    cfg = get_input_config()
    if not cfg["stanzas"]:
        log.warning("No input stanzas found on stdin.")
        return
    run_forever(cfg)


def main():
    args = sys.argv[1:]
    if args and args[0] == "--scheme":
        sys.stdout.write(SCHEME)
        return 0
    if args and args[0] == "--validate-arguments":
        return validate_arguments()
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

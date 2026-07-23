#!/usr/bin/env python
"""
vCISO Threat Intel - Splunk modular input.

Emits one event per IOC into Splunk. The feed key is OPTIONAL:
  - no key   -> the PUBLIC aggregated IOC feed (https://<host>/api/iocs)
  - with key -> ONLY that member's personal feed (https://<host>/api/feed/<key>)
Checkpointed on the IOC timestamp so each run only pulls new indicators (the first
run with no key backfills the public feed by paging). Standard library only
(works with Splunk's bundled Python 3).
"""
import sys
import os
import json
import re
import ssl
import urllib.request
import urllib.error
from xml.dom import minidom

SCHEME = """<scheme>
  <title>vCISO Threat Intel Feed</title>
  <description>Pull vCISO IOC indicators into Splunk. No key = public aggregated feed; with a key = your personal feed only.</description>
  <use_external_validation>true</use_external_validation>
  <streaming_mode>simple</streaming_mode>
  <endpoint>
    <args>
      <arg name="feed_url">
        <title>Feed base URL</title>
        <description>e.g. https://vciso.au (no trailing slash)</description>
        <required_on_create>false</required_on_create>
      </arg>
      <arg name="feed_key">
        <title>Feed key (optional)</title>
        <description>Leave blank for the PUBLIC aggregated IOC feed. Set your personal key (starts with vciso_) to pull ONLY your personal feed instead. Generate it in your vCISO profile.</description>
        <required_on_create>false</required_on_create>
      </arg>
      <arg name="verify_tls">
        <title>Verify TLS</title>
        <description>Verify the server certificate (true/false). Set false only for an internal instance with a self-signed cert.</description>
        <required_on_create>false</required_on_create>
      </arg>
    </args>
  </endpoint>
</scheme>"""


def _text(node, name, default=""):
    els = node.getElementsByTagName(name)
    if els and els[0].firstChild:
        return els[0].firstChild.data
    return default


def get_config():
    """Parse the input config Splunk passes on stdin."""
    raw = sys.stdin.read()
    doc = minidom.parseString(raw)
    root = doc.documentElement
    checkpoint_dir = _text(root, "checkpoint_dir")
    out = []
    for stanza in root.getElementsByTagName("stanza"):
        name = stanza.getAttribute("name")
        params = {"feed_url": "https://vciso.au", "feed_key": ""}
        for p in stanza.getElementsByTagName("param"):
            if p.firstChild:
                params[p.getAttribute("name")] = p.firstChild.data
        out.append((name, params))
    return checkpoint_dir, out


def cp_path(checkpoint_dir, stanza):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", stanza)
    return os.path.join(checkpoint_dir or ".", safe + ".since")


def fetch(url, ctx):
    req = urllib.request.Request(url, headers={"User-Agent": "vciso-splunk-app/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


PAGE = 1000  # /api/iocs caps each response at 1000 rows; page through with offset.


def normalize(r):
    """Map both feed shapes (public /api/iocs and personal /api/feed) to one schema."""
    return {
        "ioc_type": r.get("ioc_type"),
        "value": r.get("value"),
        "threat_type": r.get("threat_type"),
        "malware": r.get("malware"),
        "verdict": r.get("verdict"),
        "source": r.get("source") or r.get("feed_name"),
        "source_name": r.get("source_name") or r.get("feed_name"),
        "reference": r.get("reference"),
        "tags": r.get("tags"),
        # personal feed uses created_at; public feed uses last_seen/first_seen.
        "created_at": r.get("created_at") or r.get("last_seen") or r.get("first_seen") or "",
    }


def fetch_iocs(base, key, ctx, since):
    """Return the IOC rows to consider this run. Key -> personal only; no key ->
    public. Pages by 1000 (the server cap) until exhausted, so a first run pulls
    the whole feed (not just the first page); `since` keeps later runs small."""
    rows, offset = [], 0
    while True:
        if key:
            url = "%s/api/feed/%s?format=json&limit=%d&offset=%d" % (base, key, PAGE, offset)
        else:
            url = "%s/api/iocs?format=json&limit=%d&offset=%d" % (base, PAGE, offset)
        if since:
            url += "&since=" + urllib.request.quote(since)
        page = (fetch(url, ctx) or {}).get("iocs", [])
        if not page:
            break
        rows.extend(page)
        offset += len(page)
        if offset >= 2_000_000:  # safety stop
            break
    return rows


def run():
    checkpoint_dir, stanzas = get_config()
    for stanza, params in stanzas:
        base = (params.get("feed_url") or "https://vciso.au").rstrip("/")
        key = (params.get("feed_key") or "").strip()
        if key and not key.startswith("vciso_"):
            sys.stderr.write("ERROR vciso_feed: feed_key for %s is set but invalid (must start with vciso_)\n" % stanza)
            continue
        mode = "personal" if key else "public"

        verify = (params.get("verify_tls") or "true").strip().lower() not in ("0", "false", "no")
        ctx = ssl.create_default_context() if verify else ssl._create_unverified_context()

        cp = cp_path(checkpoint_dir, stanza)
        since = ""
        if os.path.exists(cp):
            try:
                with open(cp) as fh:
                    since = fh.read().strip()
            except Exception:
                since = ""

        try:
            iocs = fetch_iocs(base, key, ctx, since)
        except urllib.error.HTTPError as e:
            sys.stderr.write("ERROR vciso_feed: HTTP %s for %s (%s)\n" % (e.code, stanza, mode))
            continue
        except Exception as e:
            sys.stderr.write("ERROR vciso_feed: %s (%s)\n" % (e, mode))
            continue

        newest = since
        emitted = 0
        for raw in iocs:
            ioc = normalize(raw)
            ca = ioc.get("created_at") or ""
            # ?since= is inclusive (>=); skip rows at/before the checkpoint but
            # still advance past them.
            if since and ca and ca <= since:
                if ca > newest:
                    newest = ca
                continue
            try:
                sys.stdout.write(json.dumps(ioc, separators=(",", ":")) + "\n")
                emitted += 1
                if ca > newest:
                    newest = ca
            except Exception:
                continue
        sys.stdout.flush()

        if newest and newest != since:
            try:
                with open(cp, "w") as fh:
                    fh.write(newest)
            except Exception as e:
                sys.stderr.write("WARN vciso_feed: checkpoint write failed: %s\n" % e)
        sys.stderr.write("INFO vciso_feed: %s (%s) emitted %d IOCs\n" % (stanza, mode, emitted))


def validate():
    # Key is optional (blank = public feed). If one is set, it must look right.
    try:
        _, stanzas = get_config()
        for _, params in stanzas:
            key = (params.get("feed_key") or "").strip()
            if key and not key.startswith("vciso_"):
                sys.stderr.write("Feed key, if set, must start with 'vciso_' (leave blank for the public feed).\n")
                sys.exit(1)
    except Exception as e:
        sys.stderr.write("Validation error: %s\n" % e)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            sys.stdout.write(SCHEME)
        elif sys.argv[1] == "--validate-arguments":
            validate()
        else:
            sys.exit(0)
    else:
        run()

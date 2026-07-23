#!/usr/bin/env python
"""
vCISO Threat Intel - PUBLIC community data modular input.

Pulls the open, no-key community datasets the website publishes and indexes them
into Splunk so everyone running the app gets the whole platform's intel, not just
their personal feed:

  victims  -> /api/victims            ransomware-victim records
  news     -> /api/incidents?hours=   news, advisories, CVEs, darkweb items
  markets  -> /api/darkweb/markets    darkweb-marketplace metadata (no .onion, no stolen data)

One input pulls all three and routes each event to a CLEAN per-category
sourcetype (XML streaming), so analysts can write rules per source:
  victim                 -> vciso:victim
  news (advisory/CVE)    -> vciso:advisory
  news (everything else) -> vciso:news
  market                 -> vciso:darkweb
Each event is JSON with a `dataset` field and a normalized `event_time`.
Checkpointed per dataset so each run only emits new items. Standard library
only. Free, for the community.
"""
import sys
import os
import json
import re
import ssl
import urllib.request
import urllib.error
from xml.dom import minidom
from xml.sax.saxutils import escape


# Map each item to a clean, rule-friendly sourcetype (one index, many sourcetypes).
def sourcetype_for(dataset, item):
    if dataset == "victim":
        return "vciso:victim"
    if dataset == "market":
        return "vciso:darkweb"
    if dataset == "ioc":
        return "vciso:ioc"
    if dataset == "news":
        cat = (item.get("category") or "").strip().lower()
        return "vciso:advisory" if cat in ("advisory", "vulnerability") else "vciso:news"
    return "vciso:public"


def emit_event(rec, st):
    """Write one XML-streaming event with an explicit per-event sourcetype."""
    data = escape(json.dumps(rec, separators=(",", ":")))
    sys.stdout.write("<event><sourcetype>%s</sourcetype><data>%s</data></event>\n" % (st, data))

SCHEME = """<scheme>
  <title>vCISO Community Intel (public)</title>
  <description>Pull the open vCISO ransomware-victim, news/advisory and darkweb data into Splunk. No key needed.</description>
  <use_external_validation>false</use_external_validation>
  <streaming_mode>xml</streaming_mode>
  <endpoint>
    <args>
      <arg name="base_url">
        <title>Base URL</title>
        <description>e.g. https://vciso.au (no trailing slash)</description>
        <required_on_create>false</required_on_create>
      </arg>
      <arg name="window_hours">
        <title>News window (hours)</title>
        <description>How far back to pull news/advisory items each run. Default 72.</description>
        <required_on_create>false</required_on_create>
      </arg>
      <arg name="feed_key">
        <title>Personal feed key (optional)</title>
        <description>Leave blank for public data only. Add your vciso_ key to ALSO pull your personal IOC feed.</description>
        <required_on_create>false</required_on_create>
      </arg>
      <arg name="verify_tls">
        <title>Verify TLS</title>
        <description>Verify the server certificate (true/false). Default true.</description>
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
    doc = minidom.parseString(sys.stdin.read())
    root = doc.documentElement
    checkpoint_dir = _text(root, "checkpoint_dir")
    out = []
    for stanza in root.getElementsByTagName("stanza"):
        name = stanza.getAttribute("name")
        params = {"base_url": "https://vciso.au", "window_hours": "72", "feed_key": "", "verify_tls": "true"}
        for p in stanza.getElementsByTagName("param"):
            if p.firstChild:
                params[p.getAttribute("name")] = p.firstChild.data
        out.append((name, params))
    return checkpoint_dir, out


def cp_path(checkpoint_dir, stanza, dataset):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", stanza + "." + dataset)
    return os.path.join(checkpoint_dir or ".", safe + ".since")


def read_cp(path):
    try:
        with open(path) as fh:
            return fh.read().strip()
    except Exception:
        return ""


def write_cp(path, val):
    try:
        with open(path, "w") as fh:
            fh.write(val)
    except Exception as e:
        sys.stderr.write("WARN vciso_public: checkpoint write failed: %s\n" % e)


def fetch(url, ctx):
    req = urllib.request.Request(url, headers={"User-Agent": "vciso-splunk-app/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


# (dataset, url builder, list extractor, time field) for each public feed.
def datasets(base, hours):
    return [
        ("victim", "%s/api/victims?limit=500" % base,
         lambda d: d.get("victims", []), ("published_at", "discovered_at")),
        ("news", "%s/api/incidents?hours=%s" % (base, hours),
         lambda d: [x for x in d.get("incidents", []) if x.get("category")], ("published_at",)),
        ("market", "%s/api/darkweb/markets" % base,
         lambda d: d.get("listings", []), ("posted_at", "first_seen")),
    ]


def event_time(item, fields):
    for f in fields:
        v = item.get(f)
        if v:
            return str(v)
    return ""


def run():
    checkpoint_dir, stanzas = get_config()
    sys.stdout.write("<stream>\n")
    for stanza, params in stanzas:
        base = (params.get("base_url") or "https://vciso.au").rstrip("/")
        hours = params.get("window_hours") or "72"
        verify = (params.get("verify_tls") or "true").strip().lower() not in ("0", "false", "no")
        ctx = ssl.create_default_context() if verify else ssl._create_unverified_context()

        for dataset, url, extract, tfields in datasets(base, hours):
            cp = cp_path(checkpoint_dir, stanza, dataset)
            since = read_cp(cp)
            try:
                data = fetch(url, ctx)
            except urllib.error.HTTPError as e:
                sys.stderr.write("ERROR vciso_public: HTTP %s for %s\n" % (e.code, dataset))
                continue
            except Exception as e:
                sys.stderr.write("ERROR vciso_public: %s (%s)\n" % (e, dataset))
                continue

            items = extract(data) if isinstance(data, dict) else []
            newest, emitted = since, 0
            for it in items:
                et = event_time(it, tfields)
                if since and et and et <= since:
                    if et > newest:
                        newest = et
                    continue
                rec = dict(it)
                rec["dataset"] = dataset
                rec["event_time"] = et
                try:
                    emit_event(rec, sourcetype_for(dataset, it))
                    emitted += 1
                    if et > newest:
                        newest = et
                except Exception:
                    continue
            sys.stdout.flush()
            if newest and newest != since:
                write_cp(cp, newest)
            sys.stderr.write("INFO vciso_public: %s emitted %d\n" % (dataset, emitted))

        # Optional: also pull the member's PERSONAL feed when a key is provided.
        # No key -> public data only; key set -> personal IOCs too (dataset=ioc).
        feed_key = (params.get("feed_key") or "").strip()
        if feed_key.startswith("vciso_"):
            cp = cp_path(checkpoint_dir, stanza, "ioc")
            since = read_cp(cp)
            try:
                pdata = fetch("%s/api/feed/%s?format=json&limit=50000" % (base, feed_key), ctx)
            except Exception as e:
                sys.stderr.write("ERROR vciso_public: personal feed (%s)\n" % e)
                pdata = None
            if isinstance(pdata, dict):
                newest, emitted = since, 0
                for it in pdata.get("iocs", []):
                    et = str(it.get("created_at") or "")
                    if since and et and et <= since:
                        if et > newest:
                            newest = et
                        continue
                    rec = dict(it)
                    rec["dataset"] = "ioc"
                    rec["event_time"] = et
                    try:
                        emit_event(rec, "vciso:ioc")
                        emitted += 1
                        if et > newest:
                            newest = et
                    except Exception:
                        continue
                sys.stdout.flush()
                if newest and newest != since:
                    write_cp(cp, newest)
                sys.stderr.write("INFO vciso_public: ioc (personal) emitted %d\n" % emitted)
    sys.stdout.write("</stream>\n")
    sys.stdout.flush()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--scheme":
        sys.stdout.write(SCHEME)
    else:
        run()

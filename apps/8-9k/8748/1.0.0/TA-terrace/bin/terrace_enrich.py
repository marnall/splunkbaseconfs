#!/usr/bin/env python
"""Adaptive response action: Enrich with Terrace Networks.
Called by Splunk Enterprise Security when an analyst triggers enrichment on a notable event.
"""

import csv
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        sys.stderr.write("This script is called by Splunk as an alert action.\n")
        sys.exit(1)

    payload = json.loads(sys.stdin.read())
    config = payload.get("configuration", {})
    ip_field = config.get("ip_field", "src_ip")
    results_file = payload.get("results_file", "")

    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "")

    if not api_key or not base_url:
        # Read from terrace.conf (setup page stores config there)
        session_key = payload.get("session_key", "")
        if session_key:
            conf_api_key, conf_base_url = _get_conf_settings(session_key)
            if not api_key:
                api_key = conf_api_key
            if not base_url:
                base_url = conf_base_url
    if not base_url:
        base_url = "https://api.terracenetworks.com"

    if not api_key:
        sys.stderr.write("Terrace API key not configured\n")
        sys.exit(1)

    from terrace_api import TerraceClient

    client = TerraceClient(api_key=api_key, base_url=base_url)

    # Read IPs from results
    ips = set()
    if results_file:
        try:
            opener = gzip.open if results_file.endswith(".gz") else open
            with opener(results_file, "rt") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ip = row.get(ip_field, "").strip()
                    if ip:
                        ips.add(ip)
        except Exception as e:
            sys.stderr.write(f"Error reading results: {e}\n")

    enriched_count = 0
    for ip in ips:
        try:
            detail = client.get_ip_detail(ip)
            _write_to_kvstore(payload.get("session_key", ""), ip, detail)
            enriched_count += 1
        except Exception as e:
            sys.stderr.write(f"Error enriching {ip}: {e}\n")

    sys.stderr.write(f"Terrace: enriched {enriched_count} IPs\n")


def _get_conf_settings(session_key):
    """Read API key from storage/passwords."""
    try:
        import splunklib.client as client

        service = client.connect(
            token=session_key, host="localhost", port=8089, app="TA-terrace",
        )
        for cred in service.storage_passwords:
            if cred.realm == "TA-terrace" and cred.username == "api_key":
                return cred.clear_password, "https://api.terracenetworks.com"
    except Exception:
        pass
    return "", ""


def _write_to_kvstore(session_key, ip, detail):
    """Write enrichment to the terrace_threat_intel KV store collection."""
    if not session_key:
        return

    try:
        import splunklib.client as client

        service = client.connect(token=session_key, host="localhost", port=8089)
        collection = service.kvstore["terrace_threat_intel"]

        tags = detail.get("tags", [])
        tag_ids = [t.get("tag_id", "") for t in tags if isinstance(t, dict)]
        intents = set(t.get("intent", "") for t in tags if isinstance(t, dict))

        threat_score = 10
        classification = "unknown"
        if "malicious" in intents:
            threat_score = 90
            classification = "malicious"
        elif "suspicious" in intents:
            threat_score = 50
            classification = "suspicious"

        enrichment = detail.get("enrichment", {})

        record = {
            "_key": ip,
            "ip": ip,
            "classification": classification,
            "tags": ",".join(tag_ids),
            "threat_score": threat_score,
            "asn": enrichment.get("asn", 0),
            "asn_org": enrichment.get("asn_org", ""),
            "country": enrichment.get("country", ""),
            "first_seen": detail.get("first_seen", ""),
            "last_seen": detail.get("last_seen", ""),
            "source": "terrace",
        }

        collection.data.insert(json.dumps(record))
    except Exception as e:
        sys.stderr.write(f"KV store write error for {ip}: {e}\n")


if __name__ == "__main__":
    main()

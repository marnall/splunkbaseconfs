#!/usr/bin/env python
"""
QuantumGenie modular input for Splunk.

v1 scope: pulls the CBOM/relationship snapshot from QuantumGenie's external
API (GET /api/external/v1/cbom) on a polling interval and writes each
resource, relationship, and certificate as a Splunk event. One direction
only (QuantumGenie -> Splunk); no write-back in this version.

This intentionally uses only the Python standard library (urllib, json,
xml.dom.minidom) so it has no third-party dependency footprint beyond what
Splunk itself ships with -- keeps AppInspect review simple for v1.
"""

import sys
import json
import time
import urllib.request
import urllib.error
from xml.dom.minidom import Document

SCHEME = """<scheme>
    <title>QuantumGenie CBOM</title>
    <description>Pulls cryptographic discovery (CBOM) records from a QuantumGenie workspace.</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <endpoint>
        <args>
            <arg name="quantumgenie_url">
                <title>QuantumGenie URL</title>
                <description>Base URL of your QuantumGenie deployment, e.g. https://app.quantumgenie.ai</description>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="api_token">
                <title>API Token</title>
                <description>Integration API token generated from QuantumGenie's Integration API Tokens page.</description>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="polling_interval">
                <title>Polling interval (seconds)</title>
                <description>How often to poll QuantumGenie for new records. Default 300.</description>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>"""


def do_scheme():
    print(SCHEME)


def get_validation_data():
    """Read the validation payload Splunk sends on stdin during --validate-arguments."""
    val_data = {}
    doc = _read_stdin_xml()
    item_node = doc.getElementsByTagName("item")[0]
    for param_node in item_node.getElementsByTagName("param"):
        name = param_node.getAttribute("name")
        val_data[name] = param_node.firstChild.nodeValue if param_node.firstChild else ""
    return val_data


def _read_stdin_xml():
    from xml.dom.minidom import parseString
    input_str = sys.stdin.read()
    return parseString(input_str)


def validate_arguments():
    try:
        args = get_validation_data()
        url = (args.get("quantumgenie_url") or "").strip()
        token = (args.get("api_token") or "").strip()
        if not url.startswith("http"):
            raise ValueError("QuantumGenie URL must start with http:// or https://")
        if not token:
            raise ValueError("API token is required.")
    except Exception as exc:  # noqa: BLE001 - Splunk expects a clean error message, not a traceback
        print_validation_error(str(exc))
        sys.exit(1)


def print_validation_error(message):
    doc = Document()
    error_el = doc.createElement("error")
    doc.appendChild(error_el)
    message_el = doc.createElement("message")
    error_el.appendChild(message_el)
    message_el.appendChild(doc.createTextNode(message))
    print(doc.toxml())


def fetch_cbom_snapshot(base_url, api_token, timeout_seconds=30):
    endpoint = base_url.rstrip("/") + "/api/external/v1/cbom"
    request = urllib.request.Request(
        endpoint,
        headers={
            "Authorization": "Bearer " + api_token,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def stream_event(stanza_name, source, event_time, record):
    """Build one <event> element for Splunk's streaming XML input.

    Splunk expects a single well-formed document for the whole run: one
    <stream> root containing every <event> child, not one standalone XML
    document (with its own declaration) per event. This returns just the
    <event> fragment; do_run() wraps the full set in <stream>...</stream>.
    """
    doc = Document()
    event_el = doc.createElement("event")
    event_el.setAttribute("stanza", stanza_name)

    time_el = doc.createElement("time")
    time_el.appendChild(doc.createTextNode(str(event_time)))
    event_el.appendChild(time_el)

    source_el = doc.createElement("source")
    source_el.appendChild(doc.createTextNode(source))
    event_el.appendChild(source_el)

    sourcetype_el = doc.createElement("sourcetype")
    sourcetype_el.appendChild(doc.createTextNode("quantumgenie:cbom"))
    event_el.appendChild(sourcetype_el)

    data_el = doc.createElement("data")
    data_el.appendChild(doc.createTextNode(json.dumps(record)))
    event_el.appendChild(data_el)

    # toxml() on the *element* (not the Document) omits the "<?xml ...?>"
    # declaration, which is what makes multiple of these valid as siblings
    # inside one <stream> root.
    print(event_el.toxml())
    sys.stdout.flush()


def run(stanza_name, base_url, api_token, polling_interval_seconds):
    now = time.time()

    try:
        snapshot = fetch_cbom_snapshot(base_url, api_token)
    except urllib.error.HTTPError as exc:
        sys.stderr.write("QuantumGenie API returned HTTP %s: %s\n" % (exc.code, exc.reason))
        return
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("Failed to reach QuantumGenie API: %s\n" % str(exc))
        return

    for resource in snapshot.get("resources", []):
        stream_event(stanza_name, "quantumgenie:resource", now, resource)

    for relationship in snapshot.get("relationships", []):
        stream_event(stanza_name, "quantumgenie:relationship", now, relationship)

    for certificate in snapshot.get("certificates", []):
        stream_event(stanza_name, "quantumgenie:certificate", now, certificate)


def do_run():
    doc = _read_stdin_xml()
    print("<stream>")
    sys.stdout.flush()

    for stanza in doc.getElementsByTagName("stanza"):
        stanza_name = stanza.getAttribute("name")
        params = {}
        for param_node in stanza.getElementsByTagName("param"):
            params[param_node.getAttribute("name")] = (
                param_node.firstChild.nodeValue if param_node.firstChild else ""
            )

        base_url = (params.get("quantumgenie_url") or "").strip()
        api_token = (params.get("api_token") or "").strip()
        polling_interval = int(params.get("polling_interval") or 300)

        run(stanza_name, base_url, api_token, polling_interval)

    print("</stream>")
    sys.stdout.flush()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--scheme":
        do_scheme()
    elif len(sys.argv) > 1 and sys.argv[1] == "--validate-arguments":
        validate_arguments()
    else:
        do_run()

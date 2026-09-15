#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DentiSystems Modular Input for Splunk
Fetches recent threat events and IOCs from DentiGrid API
"""

import sys
import os
import json
import xml.dom.minidom
import xml.sax.saxutils
import urllib.request
import urllib.error
import time

SCHEME = """<scheme>
    <title>DentiSystems Intelligence Feed</title>
    <description>Polls DentiGrid threat intelligence feed endpoint for honeypot telemetry and IOCs</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>
    <endpoint>
        <args>
            <arg name="name">
                <title>Feed Name</title>
                <description>Unique identifier for this feed configuration</description>
            </arg>
            <arg name="api_url">
                <title>DentiGrid API Feed URL</title>
                <description>Endpoint URL (e.g. https://api.grid.denti.systems/api/attacks/recent?format=json)</description>
            </arg>
            <arg name="api_token">
                <title>API Token</title>
                <description>Bearer Token for DentiGrid API authentication</description>
                <required_on_create>true</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def do_scheme():
    print(SCHEME)

def validate_arguments():
    # Read config from stdin for validation
    config_str = sys.stdin.read()
    if not config_str:
        return
    doc = xml.dom.minidom.parseString(config_str)
    root = doc.documentElement
    items = root.getElementsByTagName("param")
    params = {}
    for item in items:
        name = item.getAttribute("name")
        if item.firstChild and item.firstChild.nodeType == item.firstChild.TEXT_NODE:
            params[name] = item.firstChild.data
    
    api_url = params.get("api_url", "")
    if api_url and not (api_url.startswith("http://") or api_url.startswith("https://")):
        print("<error><message>api_url must begin with http:// or https://</message></error>", file=sys.stderr)
        sys.exit(1)

def run_input():
    config_str = sys.stdin.read()
    if not config_str:
        return
    doc = xml.dom.minidom.parseString(config_str)
    root = doc.documentElement
    conf_node = root.getElementsByTagName("configuration")
    if not conf_node:
        return

    items = conf_node[0].getElementsByTagName("stanza")
    for stanza in items:
        stanza_name = stanza.getAttribute("name")
        params = {}
        for param in stanza.getElementsByTagName("param"):
            name = param.getAttribute("name")
            if param.firstChild and param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                params[name] = param.firstChild.data
        
        api_url = params.get("api_url", "https://api.grid.denti.systems/api/attacks/recent?format=json")
        api_token = params.get("api_token", "")
        
        headers = {
            "User-Agent": "Splunk-TA-DentiSystems/1.0.0",
            "Accept": "application/json"
        }
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"

        req = urllib.request.Request(api_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    attacks = data if isinstance(data, list) else data.get("attacks", [data])
                    
                    sys.stdout.write("<stream>")
                    for attack in attacks:
                        event_time = attack.get("timestamp", time.time())
                        if event_time > 1e11:
                            event_time = event_time / 1000.0
                        
                        event_xml = f"""<event>
    <time>{event_time:.3f}</time>
    <source>dentigrid-feed</source>
    <sourcetype>dentisystems:threat</sourcetype>
    <data>{xml.sax.saxutils.escape(json.dumps(attack))}</data>
</event>"""
                        sys.stdout.write(event_xml)
                    sys.stdout.write("</stream>")
                    sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Error fetching DentiSystems feed: {e}\n")

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_arguments()
    else:
        run_input()

if __name__ == "__main__":
    main()

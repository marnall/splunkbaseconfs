#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layer7 Modular Input (starter)
- Registers a scheme "layer7"
- Polls an endpoint on interval
- Writes events to Splunk in JSON (extend with ECS mapping later)

Test locally:
  $SPLUNK_HOME/bin/splunk cmd python bin/layer7_modinput.py --scheme
"""

import sys, time, json, traceback
from xml.sax.saxutils import escape

# --------- Splunk MI helpers (no external deps) ----------

def print_scheme():
    scheme = f"""<scheme>
  <title>layer7</title>
  <description>Collect Layer7 events</description>
  <use_external_validation>true</use_external_validation>
  <streaming_mode>xml</streaming_mode>
  <endpoint>
    <args>
      <arg name="api_base">
        <title>API Base URL</title>
        <description>Base URL, e.g. https://api.layer7.example</description>
        <data_type>string</data_type>
        <required_on_edit>false</required_on_edit>
        <required_on_create>true</required_on_create>
      </arg>
      <arg name="api_key">
        <title>API Key</title>
        <description>API key or token (consider using storage/passwords)</description>
        <data_type>string</data_type>
        <required_on_edit>false</required_on_edit>
        <required_on_create>true</required_on_create>
      </arg>
      <arg name="interval">
        <title>Interval (sec)</title>
        <description>Polling frequency in seconds</description>
        <data_type>number</data_type>
        <required_on_edit>false</required_on_edit>
        <required_on_create>false</required_on_create>
      </arg>
      <arg name="index">
        <title>Index</title>
        <description>Target Splunk index</description>
        <data_type>string</data_type>
        <required_on_edit>false</required_on_edit>
        <required_on_create>false</required_on_create>
      </arg>
    </args>
  </endpoint>
</scheme>"""
    sys.stdout.write(scheme)

def print_validation_ok():
    sys.stdout.write("")

def print_validation_error(msg):
    sys.stderr.write(msg)
    sys.exit(1)

def read_xml_stdin():
    """Read <config> XML from Splunk."""
    return sys.stdin.read()

def parse_xml_kv(xml_text):
    """
    Minimal parse to extract stanza name and args. This is intentionally simple.
    For complex needs, use splunklib (SDK), but this works w/o external deps.
    """
    def between(s, start, end):
        i = s.find(start)
        if i == -1: return ""
        i += len(start)
        j = s.find(end, i)
        return s[i:j] if j != -1 else ""
    conf = {}
    conf['stanza'] = between(xml_text, "<stanza>", "</stanza>") or "layer7://unknown"
    # crude arg extraction
    args_block = between(xml_text, "<param_list>", "</param_list>")
    conf['params'] = {}
    # look for <param name="x">value</param>
    pos = 0
    while True:
        p_start = args_block.find('<param name="', pos)
        if p_start == -1: break
        p_start += len('<param name="')
        p_end = args_block.find('">', p_start)
        name = args_block[p_start:p_end]
        v_end = args_block.find("</param>", p_end)
        value = args_block[p_end+2:v_end]
        conf['params'][name] = value.strip()
        pos = v_end + len("</param>")
    return conf

def do_collect(conf):
    params = conf.get('params', {})
    api_base = params.get('api_base', '')
    api_key  = params.get('api_key', '')
    interval = int(params.get('interval', '300'))
    # index is passed via event metadata, but we can leave default to Splunk input

    if not api_base or not api_key:
        raise ValueError("api_base and api_key are required.")

    # --- PLACEHOLDER: call your API here ---
    # Simulate one batch per run. Replace with real requests (urllib) if allowed.
    now = int(time.time())
    sample_events = [
        {
            "@timestamp": now,
            "event": {
                "category": ["network"],
                "type": ["connection"],
                "kind": "event"
            },
            "source": {"ip": "192.0.2.10", "port": 443},
            "destination": {"ip": "198.51.100.25", "port": 443},
            "network": {"protocol": "tls"},
            "observer": {"vendor": "Layer7", "product": "Gateway"},
            "message": "Sample Layer7 connection event"
        }
    ]

    # Write each event on its own line (XML streaming mode)
    for ev in sample_events:
        sys.stdout.write(f"<stream><event unbroken=\"1\">")
        payload = json.dumps(ev, separators=(',', ':'))
        sys.stdout.write(f"<data>{escape(payload)}</data>")
        sys.stdout.write(f"</event></stream>")

def run():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            print_scheme()
            return
        if sys.argv[1] == "--validate-arguments":
            _ = read_xml_stdin()
            # Add any argument checks here:
            print_validation_ok()
            return

    # normal run
    xml = read_xml_stdin()
    conf = parse_xml_kv(xml)
    try:
        do_collect(conf)
    except Exception as e:
        err = f"Layer7 MI error: {e}\n{traceback.format_exc()}"
        sys.stderr.write(err)
        sys.exit(1)

if __name__ == "__main__":
    run()

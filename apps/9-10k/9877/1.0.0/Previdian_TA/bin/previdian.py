#!/usr/bin/env python
"""Previdian modular input.

Introspection (--scheme) drives Settings > Data inputs > Previdian.
Execution streams JSON events and refreshes the CVE and Priority lookups.
"""

import csv
import os
import sys
import xml.sax.saxutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from previdian_client import PrevidianError
from previdian_events import LOOKUP_FIELDS, dumps, epoch
from previdian_poll import Checkpoint, config_from_params, poll

PRIORITY_FIELDS = [
  "cve_id",
  "vulnerability_id",
  "title",
  "vendor",
  "product",
  "classification",
  "bucket",
  "workflow_state",
  "score",
  "sensor_observed",
  "in_cisa_kev",
  "confidence_level",
  "watched_name",
  "previdian_url"
]

SCHEME = """<scheme>
  <title>Previdian</title>
  <description>Poll Previdian for exploitation intelligence. Use a Pro or Enterprise API token from https://previdian.com/account/api. The tier must match the token.</description>
  <use_external_validation>true</use_external_validation>
  <streaming_mode>xml</streaming_mode>
  <endpoint>
    <args>
      <arg name="api_token">
        <title>API token</title>
        <description>X-API-Token from the Previdian account API page.</description>
        <required_on_create>true</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="base_url">
        <title>Base URL</title>
        <description>Previdian host. Leave the default unless you were told otherwise.</description>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="tier">
        <title>Account tier</title>
        <description>pro or enterprise. Must match the token. A mismatch returns 403.</description>
        <required_on_create>true</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="collect_kevs">
        <title>Catalog</title>
        <description>1 to sync the KEV catalog with modified_since. 0 to skip.</description>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="collect_notifications">
        <title>Watch notifications</title>
        <description>1 to index Watch notifications. 0 to skip.</description>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="collect_priority">
        <title>Priority queue</title>
        <description>1 to refresh the Priority lookup. 0 to skip. This does not index a new event per poll.</description>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="collect_observations">
        <title>Raw observations</title>
        <description>1 to index Enterprise raw telemetry. Requires an Enterprise token. Default 0.</description>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="collect_infrastructure">
        <title>Attacker infrastructure</title>
        <description>1 to index the Enterprise attacker infrastructure catalog. Default 0.</description>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
      <arg name="collect_attackers">
        <title>Observed attackers</title>
        <description>1 to index Enterprise attacker summaries. Default 0.</description>
        <required_on_create>false</required_on_create>
        <required_on_edit>false</required_on_edit>
      </arg>
    </args>
  </endpoint>
</scheme>
"""


def run(argv=None):
  argv = list(sys.argv[1:] if argv is None else argv)
  if "--scheme" in argv:
    sys.stdout.write(SCHEME)
    return 0
  if "--validate-arguments" in argv:
    return validate_stream(sys.stdin)
  return stream(sys.stdin)


def validate_stream(handle):
  try:
    params = _params_from_xml(handle.read())
    config = config_from_params(params)
    from previdian_client import PrevidianClient
    PrevidianClient(config["base_url"], config["api_token"], config["tier"]).validate()
  except PrevidianError as error:
    sys.stderr.write(str(error) + "\n")
    return 1
  return 0


def stream(handle):
  try:
    params = _params_from_xml(handle.read())
    config = config_from_params(params)
  except PrevidianError as error:
    sys.stderr.write(str(error) + "\n")
    return 1
  checkpoint_path = os.environ.get("PREVIDIAN_CHECKPOINT") or os.path.join(
    os.environ.get("SPLUNK_HOME", "."),
    "var",
    "lib",
    "splunk",
    "modinputs",
    "previdian",
    "checkpoint.json"
  )
  checkpoint = Checkpoint(checkpoint_path)
  try:
    result = poll(config, checkpoint)
  except PrevidianError as error:
    sys.stderr.write(str(error) + "\n")
    return 1
  for message in result["messages"]:
    sys.stderr.write(message + "\n")
  sys.stdout.write("<stream>")
  for event in result["events"]:
    sys.stdout.write(_event_xml(config["index"], event))
  sys.stdout.write("</stream>\n")
  _write_lookup("previdian_kev.csv", LOOKUP_FIELDS, result["kev_rows"])
  _write_lookup("previdian_priority.csv", PRIORITY_FIELDS, result["priority_rows"], replace=True)
  checkpoint.save()
  return 0


def _event_xml(index, event):
  data = dumps(event["data"])
  time_attr = ""
  stamp = epoch(event.get("time"))
  if stamp:
    time_attr = "<time>%s</time>" % stamp
  return "<event><index>%s</index><sourcetype>%s</sourcetype>%s<data>%s</data></event>" % (
    xml.sax.saxutils.escape(index),
    xml.sax.saxutils.escape(event["sourcetype"]),
    time_attr,
    xml.sax.saxutils.escape(data)
  )


def _write_lookup(filename, fields, rows, replace=False):
  if not rows and not replace:
    return
  directory = os.environ.get("PREVIDIAN_LOOKUP_DIR")
  if not directory:
    home = os.environ.get("SPLUNK_HOME")
    if not home:
      return
    directory = os.path.join(home, "etc", "apps", "Previdian_TA", "lookups")
  os.makedirs(directory, exist_ok=True)
  path = os.path.join(directory, filename)
  existing = []
  if not replace and os.path.exists(path):
    with open(path, "r", encoding="utf-8", newline="") as handle:
      existing = list(csv.DictReader(handle))
  by_id = {}
  for row in existing:
    key = row.get("cve_id") or row.get("vulnerability_id")
    if key:
      by_id[key] = row
  for row in rows:
    key = row.get("cve_id") or row.get("vulnerability_id")
    if key:
      by_id[key] = row
  written = list(by_id.values()) if not replace else rows
  temporary = path + ".tmp"
  with open(temporary, "w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in written:
      writer.writerow(row)
  os.replace(temporary, path)


def _params_from_xml(raw):
  import xml.etree.ElementTree as ET
  if not raw or not raw.strip():
    raise PrevidianError("Modular input received no configuration")
  root = ET.fromstring(raw)
  stanza = root.find(".//configuration/stanza")
  if stanza is None:
    stanza = root.find(".//item")
  params = {}
  if stanza is None:
    raise PrevidianError("Modular input configuration had no stanza")
  for param in stanza.findall("param"):
    name = param.get("name")
    if name:
      params[name] = param.text or ""
  return params


if __name__ == "__main__":
  sys.exit(run())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Splunk modular input: Airtable enterprise audit log events.

Polls GET /v0/meta/enterpriseAccounts/{id}/auditLogEvents and emits each
event as a JSON document for indexing.

Checkpointing uses Airtable's `next` pagination token, which is designed for
continuous consumption: when no endTime is supplied, the response always
returns a `next` token marking the point from which to resume. This is stored
between runs. On first run (no checkpoint) the input uses initial_start_time.
"""

from __future__ import absolute_import, print_function

import json
import os
import sys
import time
import xml.sax.saxutils as saxutils
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import requests  # noqa: E402

APP_NAME = "TA-airtable-auditlogs"
API_BASE = "https://api.airtable.com/v0/meta/enterpriseAccounts"
SCHEME = """<scheme>
    <title>Airtable Audit Logs</title>
    <description>Collect Airtable enterprise audit log events via the Airtable Web API.</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>
    <endpoint>
        <args>
            <arg name="enterprise_account_id">
                <title>Enterprise Account ID</title>
                <description>Airtable enterprise account ID, format entXXXXXXXXXXXXXX.</description>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="token_realm">
                <title>Credential Realm</title>
                <description>Realm under which the PAT is stored. Defaults to airtable_auditlogs.</description>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="token_username">
                <title>Credential Username</title>
                <description>Username key for the stored Personal Access Token.</description>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="categories">
                <title>Categories</title>
                <description>Comma separated audit log categories. Blank collects all.</description>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="event_types">
                <title>Event Types</title>
                <description>Comma separated event types, max 100. Takes precedence over categories.</description>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="exclude_event_types">
                <title>Excluded Event Types</title>
                <description>Comma separated event types to drop before indexing.</description>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="page_size">
                <title>Page Size</title>
                <description>Events per page, max 1000.</description>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="initial_start_time">
                <title>Initial Start Time</title>
                <description>ISO 8601 backfill start, first run only. Max 180 days ago.</description>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="request_timeout">
                <title>Request Timeout</title>
                <description>HTTP timeout in seconds.</description>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="max_pages_per_run">
                <title>Max Pages Per Run</title>
                <description>Cap on pages fetched per interval. 0 for unlimited.</description>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""


# ---------------------------------------------------------------- logging

def log(level, message):
    sys.stderr.write("%s [%s] %s\n" % (level, APP_NAME, message))
    sys.stderr.flush()


# ---------------------------------------------------------------- config

def read_input_config():
    """Parse the input definition Splunk sends on stdin."""
    raw = sys.stdin.read()
    root = ET.fromstring(raw)

    session_key = root.findtext("session_key") or ""
    checkpoint_dir = root.findtext("checkpoint_dir") or ""

    configs = []
    for node in root.findall("./configuration/stanza"):
        stanza = node.get("name")
        conf = {"stanza": stanza}
        for param in node.findall("param"):
            conf[param.get("name")] = param.text
        configs.append(conf)

    return session_key, checkpoint_dir, configs


def csv_list(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# ---------------------------------------------------------------- secrets

def get_token(session_key, realm, username):
    """Fetch the PAT from Splunk's credential store."""
    import splunklib.client as client

    service = client.connect(token=session_key, owner="nobody", app=APP_NAME)
    for cred in service.storage_passwords:
        if cred.realm == realm and cred.username == username:
            return cred.clear_password
    raise RuntimeError(
        "No credential found for realm '%s' username '%s'. Store the PAT first."
        % (realm, username)
    )


# ---------------------------------------------------------------- checkpoint

def checkpoint_path(checkpoint_dir, stanza):
    safe = "".join(c if c.isalnum() else "_" for c in stanza)
    return os.path.join(checkpoint_dir, "%s.json" % safe)


def load_checkpoint(path):
    try:
        with open(path, "r") as handle:
            return json.load(handle)
    except (IOError, ValueError):
        return {}


def save_checkpoint(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(data, handle)
    os.rename(tmp, path)


# ---------------------------------------------------------------- api

def fetch_page(session, url, headers, params, timeout):
    """One API call, with retry on 429 and 5xx."""
    attempts = 0
    while True:
        attempts += 1
        response = session.get(url, headers=headers, params=params, timeout=timeout)

        if response.status_code == 200:
            return response.json()

        if response.status_code == 429 or response.status_code >= 500:
            if attempts >= 5:
                raise RuntimeError(
                    "Airtable API failed after %d attempts: HTTP %s %s"
                    % (attempts, response.status_code, response.text[:400])
                )
            backoff = min(2 ** attempts, 30)
            log("WARN", "HTTP %s, retrying in %ds" % (response.status_code, backoff))
            time.sleep(backoff)
            continue

        raise RuntimeError(
            "Airtable API error: HTTP %s %s" % (response.status_code, response.text[:400])
        )


# ---------------------------------------------------------------- output

def emit_event(stanza, sourcetype, index, event):
    """Write one event in Splunk's XML streaming format."""
    body = json.dumps(event, separators=(",", ":"), sort_keys=True)
    parts = [
        "<event>",
        "<source>%s</source>" % saxutils.escape(stanza),
        "<sourcetype>%s</sourcetype>" % saxutils.escape(sourcetype),
    ]
    if index:
        parts.append("<index>%s</index>" % saxutils.escape(index))
    timestamp = event.get("timestamp")
    if timestamp:
        parts.append("<time>%s</time>" % saxutils.escape(str(timestamp)))
    parts.append("<data>%s</data>" % saxutils.escape(body))
    parts.append("</event>")
    sys.stdout.write("".join(parts))


# ---------------------------------------------------------------- run

def run_input(conf, session_key, checkpoint_dir):
    stanza = conf["stanza"]
    account_id = (conf.get("enterprise_account_id") or "").strip()
    if not account_id:
        raise RuntimeError("enterprise_account_id is required")

    realm = (conf.get("token_realm") or "airtable_auditlogs").strip()
    username = (conf.get("token_username") or "").strip()
    if not username:
        raise RuntimeError("token_username is required")

    sourcetype = conf.get("sourcetype") or "airtable:auditlog"
    index = conf.get("index") or ""
    timeout = int(conf.get("request_timeout") or 60)
    page_size = min(int(conf.get("page_size") or 1000), 1000)
    max_pages = int(conf.get("max_pages_per_run") or 100)

    categories = csv_list(conf.get("categories"))
    event_types = csv_list(conf.get("event_types"))
    excluded = set(csv_list(conf.get("exclude_event_types")))

    if len(event_types) > 100:
        raise RuntimeError("event_types exceeds the API maximum of 100 values")
    if len(categories) > 100:
        raise RuntimeError("categories exceeds the API maximum of 100 values")

    token = get_token(session_key, realm, username)

    cp_path = checkpoint_path(checkpoint_dir, stanza)
    checkpoint = load_checkpoint(cp_path)
    next_token = checkpoint.get("next")

    url = "%s/%s/auditLogEvents" % (API_BASE, account_id)
    headers = {
        "Authorization": "Bearer %s" % token,
        "User-Agent": "%s/1.0" % APP_NAME,
    }

    base_params = {
        "pageSize": page_size,
        "sortOrder": "ascending",
    }
    if event_types:
        base_params["eventType"] = event_types
    elif categories:
        base_params["category"] = categories

    if not next_token:
        initial = (conf.get("initial_start_time") or "").strip()
        if initial:
            base_params["startTime"] = initial
        log("INFO", "%s: no checkpoint, starting fresh" % stanza)
    else:
        log("INFO", "%s: resuming from checkpoint" % stanza)

    session = requests.Session()
    pages = 0
    emitted = 0
    dropped = 0

    while True:
        params = dict(base_params)
        if next_token:
            params["next"] = next_token

        payload = fetch_page(session, url, headers, params, timeout)

        events = payload.get("events") or []
        for event in events:
            if event.get("action") in excluded:
                dropped += 1
                continue
            emit_event(stanza, sourcetype, index, event)
            emitted += 1
        sys.stdout.flush()

        pagination = payload.get("pagination") or {}
        new_next = pagination.get("next")

        # Persist progress after every page, so a crash does not replay work.
        if new_next:
            next_token = new_next
            save_checkpoint(cp_path, {"next": next_token, "updated": int(time.time())})

        pages += 1

        # No events returned means we have caught up to the present.
        if not events:
            break
        if not new_next:
            break
        if max_pages and pages >= max_pages:
            log("INFO", "%s: hit max_pages_per_run (%d), will resume next interval"
                % (stanza, max_pages))
            break

    log("INFO", "%s: %d pages, %d events indexed, %d dropped by filter"
        % (stanza, pages, emitted, dropped))


def validate_arguments():
    """External validation, called by Splunk before saving an input."""
    raw = sys.stdin.read()
    root = ET.fromstring(raw)
    account_id = ""
    for param in root.findall("./item/param"):
        if param.get("name") == "enterprise_account_id":
            account_id = (param.text or "").strip()

    if not account_id.startswith("ent"):
        print("Invalid enterprise_account_id: expected format entXXXXXXXXXXXXXX",
              file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            print(SCHEME)
            sys.exit(0)
        if sys.argv[1] == "--validate-arguments":
            validate_arguments()
            return

    session_key, checkpoint_dir, configs = read_input_config()

    sys.stdout.write("<stream>")
    failures = 0
    for conf in configs:
        try:
            run_input(conf, session_key, checkpoint_dir)
        except Exception as exc:  # noqa: BLE001
            failures += 1
            log("ERROR", "%s: %s" % (conf.get("stanza"), exc))
    sys.stdout.write("</stream>")
    sys.stdout.flush()

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python

import sys
import os
import requests
import time
import json
from datetime import datetime

# Debug log file
DEBUG_LOG = "/opt/splunk/var/log/socradar/status_update_log.txt"

def log_debug(msg):
    os.makedirs(os.path.dirname(DEBUG_LOG), exist_ok=True)
    with open(DEBUG_LOG, 'a') as f:
        f.write(f"[{datetime.now()}] {msg}\n")

# Simple version that outputs CSV directly
print("alarm_id,status,result,message,time")

try:
    log_debug("=== NEW STATUS UPDATE REQUEST ===")

    # Read all input
    input_lines = []
    for line in sys.stdin:
        input_lines.append(line.strip())

    log_debug(f"Input lines: {input_lines}")

    # Parse alarm_id and new_status from input
    alarm_id = ""
    new_status = ""

    for line in input_lines:
        if "alarm_id=" in line:
            parts = line.split(',')
            for part in parts:
                if 'alarm_id=' in part:
                    alarm_id = part.split('=', 1)[1].strip().strip('"')
                elif 'new_status=' in part:
                    new_status = part.split('=', 1)[1].strip().strip('"')

    log_debug(f"Parsed: alarm_id={alarm_id}, new_status={new_status}")

    if not alarm_id:
        print("NONE,No alarm selected,WAITING,Enter an alarm ID," + str(int(time.time())))
        sys.exit(0)

    # Get credentials
    conf_file = "/opt/splunk/etc/apps/TA-socradar-incidents/local/inputs.conf"
    company_id = None
    api_key = None

    if os.path.exists(conf_file):
        with open(conf_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('socradar_company_id'):
                    company_id = line.split('=', 1)[1].strip()
                elif line.startswith('socradar_api_key'):
                    api_key = line.split('=', 1)[1].strip()

    if not company_id or not api_key:
        log_debug("Missing credentials")
        print(f"{alarm_id},Error,ERROR,Missing credentials," + str(int(time.time())))
        sys.exit(0)

    # Status mapping
    status_map = {
        '0': 'Open',
        '1': 'OnHold-Investigating',
        '2': 'Closed-Resolved',
        '3': 'OnHold-Pending',
        '5': 'OnHold-Legal',
        '9': 'Closed-FalsePositive',
        '10': 'Closed-Duplicate',
        '11': 'Closed-ProcessedInternally',
        '12': 'Closed-Mitigated',
        '13': 'Closed-NotApplicable'
    }

    status_name = status_map.get(new_status, f'Status-{new_status}')

    # Make API call
    url = f"https://platform.socradar.com/api/company/{company_id}/alarms/status/change?key={api_key}"
    payload = {
        "status": new_status,
        "alarm_ids": alarm_id,
        "comments": f"Updated via Splunk to: {status_name}"
    }

    log_debug(f"Calling API: {url[:50]}...")
    log_debug(f"Payload: {payload}")

    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
    response_data = response.json()

    log_debug(f"API Response: {response.status_code} - {response_data}")

    if response.status_code == 200 and response_data.get('is_success', False):
        print(f"{alarm_id},{status_name},SUCCESS,Updated successfully," + str(int(time.time())))
        # The status is now changed at SOCRadar. The modular-input collector
        # detects the status change on its next poll and re-indexes the FULL
        # alarm (with the new status) into the socradar_incidents index, so the
        # dashboard reflects it within one collection cycle.
        #
        # We intentionally do NOT write a synthetic event here: a minimal
        # alarm_id+status event would become the newest event for that alarm_id
        # and (via the dashboard's `dedup alarm_id sortby -_time`) hide the full
        # alarm content. It also required admin credentials this command does
        # not have (commands.conf enableheader=false => no session key passed).
        log_debug(f"Status change SUCCESS for {alarm_id} -> {status_name}; dashboard updates on next collector poll.")
    else:
        msg = response_data.get('message', 'Update failed').replace(',', ';')
        print(f"{alarm_id},{status_name},FAILED,{msg}," + str(int(time.time())))
        log_debug(f"Update failed: {msg}")

except Exception as e:
    log_debug(f"EXCEPTION: {e}")
    print(f"ERROR,Error,ERROR,{str(e).replace(',', ';')}," + str(int(time.time())))

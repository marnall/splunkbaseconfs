#!/usr/bin/env python3

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

import sys
import os
import re
from pathlib import Path
import json
from datetime import datetime, timedelta
import time
import platform

ta_name = 'SecurityOnionSplunk'
_lib_base = os.path.join(os.path.dirname(__file__), 'lib')
ta_lib_name = os.path.join(_lib_base, 'py313' if sys.version_info >= (3, 10) else 'py39')
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, ta_lib_name)
sys.path = new_paths

# Import splunklib modules
sys.path.insert(0, os.path.dirname(__file__))
from splunklib.modularinput import Script, Scheme, Argument, Event, EventWriter

# Import our query_events function
from query_events import query_events


class SecurityOnionAlertsInput(Script):
    """A modular input that pulls alerts from Security Onion API"""

    def get_scheme(self):
        """Return the scheme for this modular input"""
        scheme = Scheme("Security Onion Alerts")
        scheme.description = "Pulls alerts from Security Onion API"
        scheme.use_external_validation = False
        scheme.use_single_instance = False

        # Add custom arguments
        search_window = Argument("search_window")
        search_window.title = "Search window (minutes)"
        search_window.description = "How many far back in time to pull alerts from (default 5)"
        search_window.data_type = Argument.data_type_number
        search_window.required_on_create = False
        search_window.required_on_edit = False
        scheme.add_argument(search_window)

        event_limit = Argument("event_limit")
        event_limit.title = "Event Limit"
        event_limit.description = "Maximum number of events to retrieve (default 400)"
        event_limit.data_type = Argument.data_type_number
        event_limit.required_on_create = False
        event_limit.required_on_edit = False
        scheme.add_argument(event_limit)

        return scheme

    def get_local_timezone(self):
        try:
            import time
            # Check if we're currently in daylight saving time
            is_dst = time.localtime().tm_isdst

            if is_dst > 0:
                tz_abbr = time.tzname[1]  # DST timezone (e.g., EDT)
            else:
                tz_abbr = time.tzname[0]  # Standard timezone (e.g., EST)
            tz_map = {
                'EST': 'America/New_York', 'EDT': 'America/New_York',
                'CST': 'America/Chicago', 'CDT': 'America/Chicago',
                'MST': 'America/Denver', 'MDT': 'America/Denver',
                'PST': 'America/Los_Angeles', 'PDT': 'America/Los_Angeles',
                'AST': 'America/Halifax', 'ADT': 'America/Halifax',
                'NST': 'America/St_Johns', 'NDT': 'America/St_Johns',
                'BRT': 'America/Sao_Paulo', 'BRST': 'America/Sao_Paulo',
                'ART': 'America/Argentina/Buenos_Aires',
                'COT': 'America/Bogota', 'PET': 'America/Lima',
                'VET': 'America/Caracas', 'CLT': 'America/Santiago',
                'GMT': 'Europe/London', 'BST': 'Europe/London',
                'WET': 'Europe/Lisbon', 'WEST': 'Europe/Lisbon',
                'CET': 'Europe/Paris', 'CEST': 'Europe/Paris',
                'EET': 'Europe/Athens', 'EEST': 'Europe/Athens',
                'MSK': 'Europe/Moscow',
                'IST': 'Asia/Kolkata', 'PKT': 'Asia/Karachi',
                'BDT': 'Asia/Dhaka', 'ICT': 'Asia/Bangkok',
                'WIB': 'Asia/Jakarta', 'WIT': 'Asia/Jayapura',
                'SGT': 'Asia/Singapore', 'HKT': 'Asia/Hong_Kong',
                'CST': 'Asia/Shanghai', 'JST': 'Asia/Tokyo',
                'KST': 'Asia/Seoul', 'GST': 'Asia/Dubai',
                'AST': 'Asia/Riyadh', 'IDT': 'Asia/Jerusalem',
                'IST': 'Asia/Jerusalem',
                'AEST': 'Australia/Sydney', 'AEDT': 'Australia/Sydney',
                'ACST': 'Australia/Adelaide', 'ACDT': 'Australia/Adelaide',
                'AWST': 'Australia/Perth', 'NZST': 'Pacific/Auckland',
                'NZDT': 'Pacific/Auckland', 'FJT': 'Pacific/Fiji',
                'CAT': 'Africa/Johannesburg', 'EAT': 'Africa/Nairobi',
                'WAT': 'Africa/Lagos', 'SAST': 'Africa/Johannesburg',
                'UTC': 'Etc/UTC', 'GMT': 'Etc/GMT',
                'Z': 'Etc/UTC', 'ZULU': 'Etc/UTC'
            }

            if tz_abbr in tz_map:
                return tz_map[tz_abbr]
        except:
            pass

        # Default to UTC if we can't determine the timezone
        return 'Etc/UTC'

    def stream_events(self, inputs, ew):
        """Stream events to Splunk"""

        # Process each input
        for input_name, input_item in inputs.inputs.items():
            # Get configuration
            search_window = float(input_item.get("search_window", "5"))
            query = 'tags: alert AND _exists_:rule.name AND _exists_:rule.uuid | groupby event.module*'
            event_limit = int(input_item.get("event_limit", "400"))

            # Log that we're starting
            ew.log(EventWriter.INFO, f"Starting Security Onion alerts collection for input {input_name}")

            # Get local timezone
            local_timezone = self.get_local_timezone()

            # Time range based on search_window parameter
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=search_window)
            date_range = f"{start_time.strftime('%Y/%m/%d %I:%M:%S %p')} - {end_time.strftime('%Y/%m/%d %I:%M:%S %p')}"

            # Build query parameters with local timezone
            query_params = {
                'query': query,
                'range': date_range,
                'zone': local_timezone,
                'format': '2006/01/02 3:04:05 PM',
                'metricLimit': event_limit,
                'eventLimit': event_limit
            }

            try:
                # Log the timezone being used
                ew.log(EventWriter.INFO, f"Using timezone: {local_timezone}")

                # Query Security Onion API
                result = query_events(query_params)

                if result and isinstance(result, dict):
                    events = result.get('events', [])

                    ew.log(EventWriter.INFO, f"Retrieved {len(events)} alerts from Security Onion")

                    for event_data in events:
                        # Extract payload data
                        payload = event_data.get('payload', event_data)

                        # Create flattened event data
                        flattened_data = {}

                        # Add all payload fields to the event
                        if isinstance(payload, dict):
                            # Flatten the payload for Splunk
                            for key, value in payload.items():
                                if isinstance(value, (str, int, float, bool)):
                                    flattened_data[key] = value
                                elif isinstance(value, dict):
                                    # Flatten nested dicts
                                    for subkey, subvalue in value.items():
                                        if isinstance(subvalue, (str, int, float, bool)):
                                            flattened_data[f"{key}.{subkey}"] = subvalue
                                elif isinstance(value, list) and len(value) > 0:
                                    # For lists, take the first value or join them
                                    if isinstance(value[0], str):
                                        flattened_data[key] = ", ".join(value)
                                    else:
                                        flattened_data[key] = str(value[0])

                        # Add securityonion field for workflow action
                        flattened_data['securityonion'] = 'true'

                        # Ensure community_id is available if it exists
                        if 'network.community_id' in flattened_data:
                            flattened_data['community_id'] = flattened_data['network.community_id']

                        # Ensure uid is available if it exists
                        if 'log.id.uid' in flattened_data:
                            flattened_data['uid'] = flattened_data['log.id.uid']

                        # Get timestamp
                        timestamp = None
                        if '@timestamp' in flattened_data:
                            try:
                                dt = datetime.fromisoformat(flattened_data['@timestamp'].replace('Z', '+00:00'))
                                timestamp = dt.timestamp()
                            except:
                                pass

                        # Create the event as JSON
                        json_data = json.dumps(flattened_data)

                        # Create Splunk event
                        event = Event()
                        event.data = json_data
                        event.sourcetype = input_item.get("sourcetype", "securityonion:alerts")
                        event.source = input_item.get("source", "securityonion_api")
                        event.host = input_item.get("host", "securityonion")
                        event.stanza = input_name

                        if timestamp:
                            event.time = f"{timestamp:.3f}"

                        # Write the event
                        ew.write_event(event)

            except Exception as e:
                import traceback
                ew.log(EventWriter.ERROR, f"Failed to retrieve Security Onion alerts: {str(e)}")
                ew.log(EventWriter.DEBUG, f"Traceback: {traceback.format_exc()}")

            ew.log(EventWriter.INFO, f"Completed Security Onion alerts collection for input {input_name}")


if __name__ == "__main__":
    sys.exit(SecurityOnionAlertsInput().run(sys.argv))

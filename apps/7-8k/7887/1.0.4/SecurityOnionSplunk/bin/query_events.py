#!/usr/bin/env python3

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

import sys
import os
import re
from pathlib import Path

ta_name = 'SecurityOnionSplunk'
_lib_base = os.path.join(os.path.dirname(__file__), 'lib')
ta_lib_name = os.path.join(_lib_base, 'py313' if sys.version_info >= (3, 10) else 'py39')
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, ta_lib_name)
sys.path = new_paths

import requests

sys.path.insert(0, str(Path(__file__).parent))
import get_oauth_token as auth

def query_events(query_params, additional_headers=None):
    try:
        token_data = auth.get_oauth_token()
        access_token = token_data['access_token']
        urlbase = auth.normalize_urlbase(token_data['urlbase'])

        if not access_token:
            raise RuntimeError("No access token received")

    except Exception as e:
        raise RuntimeError(f"Failed to get OAuth token: {e}")

    api_url = f"{urlbase}/connect/events"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }

    if additional_headers:
        headers.update(additional_headers)

    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=headers,
            timeout=30,
            verify=auth.get_cert_path()
        )
        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to query events API: {e}")


def find_community_id_by_uid(uid, timestamp=None, timezone="Etc/UTC"):
    """
    Find community_id for a given uid, optionally filtered by timestamp.

    Args:
        uid (str): The uid to search for
        timestamp (str): Optional timestamp to narrow the search
        timezone (str): Timezone for the query (default: Etc/UTC)

    Returns:
        str: The community_id if found, None otherwise
    """
    from datetime import datetime, timedelta

    search_query = f'log.id.uid:{uid}'

    if timestamp:
        try:
            # Check if timestamp is numeric (epoch seconds)
            if timestamp.replace('.', '').replace('-', '').isdigit():
                dt = datetime.fromtimestamp(float(timestamp))
            else:
                # Handle ISO format timestamp
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            start_time = dt - timedelta(hours=1)
            end_time = dt + timedelta(hours=1)
            date_range = f"{start_time.strftime('%Y/%m/%d %I:%M:%S %p')} - {end_time.strftime('%Y/%m/%d %I:%M:%S %p')}"
        except Exception as e:
            # Fallback to last 24 hours if timestamp parsing fails
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            date_range = f"{start_time.strftime('%Y/%m/%d %I:%M:%S %p')} - {end_time.strftime('%Y/%m/%d %I:%M:%S %p')}"
    else:
        # Default to last 24 hours
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        date_range = f"{start_time.strftime('%Y/%m/%d %I:%M:%S %p')} - {end_time.strftime('%Y/%m/%d %I:%M:%S %p')}"

    query_params = {
        'query': search_query,
        'range': date_range,
        'zone': timezone,
        'format': '2006/01/02 3:04:05 PM',
        'metricLimit': 10,
        'eventLimit': 100
    }

    try:
        result = query_events(query_params)

        # grab community_id from the first matching event (with a matching uid / log.id.uid)
        if result and isinstance(result, dict):
            events = result.get('events', [])
            if events and len(events) > 0:
                for event in events:
                    payload = event.get('payload', event)

                    if isinstance(payload, dict) and 'network.community_id' in payload:
                        community_id = payload['network.community_id']
                        if community_id:
                            return community_id

        return None

    except Exception as e:
        raise RuntimeError(f"Failed to find community_id: {e}")
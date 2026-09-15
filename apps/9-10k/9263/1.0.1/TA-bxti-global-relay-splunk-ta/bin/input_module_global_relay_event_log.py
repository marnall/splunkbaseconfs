# encoding = utf-8

import os
import sys
import time
import datetime

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''


def validate_input(helper, definition):
    """Validate the provisioned Global Relay HTTPS endpoint."""
    from urllib.parse import urlparse

    api_url = (definition.parameters.get('api_url') or '').strip()
    interval = definition.parameters.get('interval')
    parsed = urlparse(api_url)
    hostname = (parsed.hostname or '').lower()

    if parsed.scheme.lower() != 'https':
        raise ValueError('Event Log API URL must use HTTPS.')
    if not hostname.endswith('.globalrelay.com'):
        raise ValueError('Event Log API URL must use a globalrelay.com host.')
    if parsed.username or parsed.password:
        raise ValueError('Do not embed credentials in the Event Log API URL.')
    if not parsed.path.startswith('/api/v1/get-events'):
        raise ValueError('Event Log API URL must use /api/v1/get-events.')
    if interval is not None:
        try:
            interval_seconds = float(interval)
        except (TypeError, ValueError):
            raise ValueError('Interval must be a number of seconds.')
        if interval_seconds < 6:
            raise ValueError('Interval must be at least 6 seconds to respect the Global Relay limit of 10 requests per minute.')


def collect_events(helper, ew):
    """Collect one Global Relay response page and persist its continuation URL."""
    import base64
    import hashlib
    import json
    from urllib.parse import urlparse

    account = helper.get_arg('global_account') or {}
    api_url = (helper.get_arg('api_url') or '').strip()
    username = account.get('username')
    password = account.get('password')

    if not username or not password:
        raise ValueError('Select a Global Relay account with a username and password.')

    checkpoint_key = 'next_url_' + hashlib.sha256(api_url.encode('utf-8')).hexdigest()
    checkpoint = helper.get_check_point(checkpoint_key)
    request_url = checkpoint.get('next_url') if isinstance(checkpoint, dict) else checkpoint
    request_url = request_url or api_url

    parsed = urlparse(request_url)
    if parsed.scheme.lower() != 'https' or not (parsed.hostname or '').lower().endswith('.globalrelay.com'):
        raise ValueError('Refusing an invalid or untrusted Global Relay continuation URL.')

    token = base64.b64encode(('{}:{}'.format(username, password)).encode('utf-8')).decode('ascii')
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic ' + token,
        'User-Agent': 'BXTI-Global-Relay-Splunk-TA/1.0.1',
    }

    response = helper.send_http_request(
        request_url,
        'GET',
        headers=headers,
        verify=True,
        timeout=60,
        use_proxy=True,
    )

    if response.status_code == 429:
        helper.log_warning('Global Relay rate limit reached; retrying on the next interval.')
        return
    if response.status_code == 400 and checkpoint:
        raise ValueError('Global Relay rejected the saved offset. The queue may have exceeded its 96-hour retention window; reset the input checkpoint deliberately to avoid duplicates.')
    if response.status_code in (401, 403):
        raise ValueError('Global Relay authentication or authorization failed.')
    response.raise_for_status()

    payload = response.json()
    api_status = payload.get('Status', payload.get('status', response.status_code))
    if int(api_status) != 200:
        raise ValueError('Global Relay returned API status {}.'.format(api_status))

    events = payload.get('Data', payload.get('data', []))
    if not isinstance(events, list):
        raise ValueError('Global Relay response Data field is not an array.')

    for item in events:
        if not isinstance(item, dict):
            helper.log_warning('Skipping a non-object item in the Global Relay Data array.')
            continue
        event_time = item.get('EventTime')
        splunk_time = float(event_time) / 1000.0 if event_time is not None else None
        event = helper.new_event(
            source=request_url,
            index=helper.get_output_index(),
            sourcetype='globalrelay:eventlog',
            time=splunk_time,
            data=json.dumps(item, separators=(',', ':'), sort_keys=True),
        )
        ew.write_event(event)

    next_url = payload.get('@NextUrl', payload.get('@nextUrl'))
    if not next_url:
        raise ValueError('Global Relay response did not contain @NextUrl.')

    next_parsed = urlparse(next_url)
    if next_parsed.scheme.lower() != 'https' or not (next_parsed.hostname or '').lower().endswith('.globalrelay.com'):
        raise ValueError('Global Relay returned an untrusted @NextUrl.')

    helper.save_check_point(checkpoint_key, {
        'next_url': next_url,
        'updated_at': int(time.time()),
    })
    helper.log_info('Collected {} Global Relay event(s).'.format(len(events)))

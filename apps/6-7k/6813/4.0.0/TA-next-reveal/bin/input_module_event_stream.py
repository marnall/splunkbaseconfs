
# encoding = utf-8

from functools import reduce
from typing import Mapping, Any
import asyncio
import json
import pyrfc3339
import socket
import urllib.parse

USER_AGENT = 'TA-Next-Reveal/4.0.0 (Splunk)'

# event types which can be ingested by splunk. each entry should
# have the following keys:
#  ts_field:    dot-separated path to a field in the JSON object
#               which contains the timestamp for the event
#  source_type: the splunk source type the event should be mapped
#               onto
event_types = {
    "sensor": {
        "ts_field": "timestamp",
        "source_type": "Reveal:EventStream:Detections:JSON"
    }, 
    "incident": {
        "ts_field": "last_updated",
        "source_type": "Reveal:EventStream:Incidents:JSON"
    },
    "audit_log": {
        "ts_field": "fields.timestamp",
        "source_type": "Reveal:EventStream:AuditLogs:JSON"
    },
    "action": {
        "ts_field": "timestamp",
        "source_type": "Reveal:EventStream:Actions:JSON"
    }
}

def format_splunk_event_time(timestamp):
    return "{:.3f}".format(timestamp)

def deep_get(d, keys):
    """
    Returns the value of a nested value in the dictionary d, e.g.
        d = { "outer": { "inner": "val" } }
        deep_get(d, "outer.inner") # returns "val"
    """
    getter = lambda x, k: x.get(k) if isinstance(x, dict) else None
    return reduce(getter, keys.split('.'), d)

def validate_input(helper, definition):
    if not definition.parameters.get('access_token'):
        raise ValueError('access token required')
    if not definition.parameters.get('connector_url'):
        raise ValueError('URL required')
    parse_client_url(definition.parameters.get('connector_url'))

def is_status_change(data: Mapping[str, Any]) -> bool:
    return (
        data.get("changed_status_at") is not None
        and data.get("changed_status_by", "") != ""
        and data.get("status") is not None
    )

def pick_incident_event_time(helper, data: Mapping[str, Any]) -> float:
    """
    Determine _time for an incident update.

    Rules:
    - Creation selects started
    - Status change selects changed_status_at (authoritative)
    - Other updates (new_user, new_node, correlation churn) select last_updated
    """

    # Creation
    if data.get("type") == "created":
        return pyrfc3339.parse(data["started"]).timestamp()

    # Explicit status change by administrator e.g. resolving incident
    if is_status_change(data):
        return pyrfc3339.parse(data["changed_status_at"]).timestamp()
    
    # Correlation / enrichment update
    if data.get("last_detection"):
        return pyrfc3339.parse(data["last_detection"]).timestamp()

    # All other incident updates
    return pyrfc3339.parse(data["last_updated"]).timestamp()

def parse_client_url(connector_url):
    url = urllib.parse.urlparse(connector_url, allow_fragments=False)
    if url.scheme != 'https':
        raise ValueError(
            'invalid stream URL: scheme must be https {}'.format(url.scheme))
    if not url.hostname:
        raise ValueError(f"Connector URL does not contain a hostname: {connector_url!r}")
    # When calling write_event Splunk expects host to be set to the hostname of the connector
    connector_hostname = url.hostname.lower()
    qs = urllib.parse.parse_qs(url.query)
    if 'stream_id' not in qs:
        raise ValueError('invalid stream URL: missing stream_id')
    return (connector_hostname, url, qs['stream_id'])

def auth_headers(helper):
    return { 
        "Authorization": "Bearer {}".format(helper.get_arg("access_token")) 
    }

def connect_websocket(helper, url):
    import websockets
    return websockets.connect(
        url._replace(scheme='wss').geturl(), 
        additional_headers=auth_headers(helper), 
        user_agent_header=USER_AGENT)

def get_event(helper, event_data):
    for event_type, info in event_types.items():
        if event_type in event_data:
            data = event_data[event_type]
            source_type = info["source_type"]
            if get_bool(helper.get_arg("discard_extended_metadata")) and event_type == "sensor":
                data.pop("extended_metadata", None)

            if event_type == "incident":
                event_time = pick_incident_event_time(helper, data)
                return data, source_type, format_splunk_event_time(event_time)

            timestamp = deep_get(data, info["ts_field"])
            if timestamp is None:
                raise KeyError("timestamp not found in event")
            
            event_time = pyrfc3339.parse(timestamp).timestamp()
            return data, source_type, format_splunk_event_time(event_time)

    raise ValueError("unknown event type")

def write_event(helper, ew, input_type, index, event_data, stream_id, connector_host):
    try:
        event, source_type, event_time = get_event(helper, event_data)
    except (KeyError, ValueError, TypeError) as exc:
        helper.log_warning(f"Skipping malformed or unsupported FortiDLP event: {exc!r}")
        helper.log_debug(f"Skipped event payload: {event_data!r}")
        return False
    except Exception as exc:
        helper.log_error(f"Unexpected error converting FortiDLP event; stopping stream: {exc!r}")
        raise

    payload = {
        "ta_data": {"stream_id": stream_id},
        "event": event,
    }

    enrichment_errors = event_data.get("enrichment_errors")
    if enrichment_errors:
        payload["ta_data"]["enrichment_errors"] = enrichment_errors

    splunk_event = helper.new_event(
        source=input_type,
        index=index,
        sourcetype=source_type,
        data=json.dumps(payload),
        time=event_time,
        host=connector_host,
    )

    ew.write_event(splunk_event)
    return True


async def stream_events(helper, ew):
    from websockets.exceptions import ConnectionClosed, InvalidHandshake

    input_type = helper.get_input_type()
    index = helper.get_output_index()
    (connector_hostname, url, stream_id) = parse_client_url(helper.get_arg('connector_url'))
    
    try:
        async with connect_websocket(helper, url) as ws:
            async for event in ws:
                try:
                    event_data = json.loads(event)
                except json.JSONDecodeError as exc:
                    helper.log_warning(f"Skipping invalid JSON message from FortiDLP stream: {exc!r}")
                    helper.log_debug(f"Invalid JSON payload: {event!r}")
                    continue

                write_event(helper, ew, input_type, index, event_data, stream_id, connector_hostname)

    except socket.gaierror as exc:
        helper.log_warning(
            f"FortiDLP connector hostname {connector_hostname!r} could not be resolved; "
            f"collection will retry on next run: {exc!r}"
        )
        return

    except ConnectionClosed as exc:
        helper.log_warning(
            f"FortiDLP websocket connection closed; collection will retry on next run: {exc!r}"
        )
        return

    except (asyncio.TimeoutError, TimeoutError) as exc:
        helper.log_warning(
            f"FortiDLP websocket timed out; collection will retry on next run: {exc!r}"
        )
        return

    except InvalidHandshake as exc:
        helper.log_error(
            f"FortiDLP websocket handshake failed; check connector URL/auth/proxy: {exc!r}"
        )
        raise


def poll_events(helper, ew):
    input_type = helper.get_input_type()
    index = helper.get_output_index()
    
    (connector_hostname, url, stream_id) = parse_client_url(helper.get_arg('connector_url'))  
    response = helper.send_http_request(
                    url.geturl(), 
                    'GET',
                    headers=auth_headers(helper), 
                    parameters={"format": "json"}, 
                    verify=True,
                    # (Connect timeout, read timeout) - FortiDLP poll can block up to 30s before returning events
                    timeout=(10.0, 60.0))

    response.raise_for_status()
    events = response.json()
    for event_data in events["events"]:
        write_event(helper, ew, input_type, index, event_data, stream_id, connector_hostname)

def get_bool(raw, default=False):
    """
    Normalize Add-on Builder checkbox values.

    AOB returns strings like '1', '0', 'true', 'false'.
    """
    if raw is None:
        return default
    return str(raw).lower() in ("1", "true", "yes", "on")

def collect_events(helper, ew):
    index = helper.get_output_index()
    if not index:
        raise ValueError("No index configured for this input")

    # Read and normalize the global setting
    raw_ws = helper.get_global_setting("websocket_streaming_mode")
    websocket_mode = get_bool(raw_ws, default=True)

    helper.log_debug(f"websocket_streaming_mode raw={raw_ws!r} parsed={websocket_mode}")

    if websocket_mode:
        helper.log_debug('streaming event collector starting')
        asyncio.run(stream_events(helper, ew))
        helper.log_debug('streaming event collector finished')
    else:
        helper.log_debug('polling event collector starting')
        poll_events(helper, ew)
        helper.log_debug('polling event collector finished')

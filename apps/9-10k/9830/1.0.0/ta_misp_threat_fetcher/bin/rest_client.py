import json
import os
import requests

SUPPORTED_IOC_TYPES = [
    'ip-src', 'ip-dst', 'domain', 'hostname',
    'md5', 'sha1', 'sha256', 'url', 'uri',
    'email-src', 'filename',
]


def build_attribute_body(start_ts, end_ts, page, page_size,
                         tag_filter, published_only, ioc_types=None):
    body = {
        "returnFormat": "json",
        "timestamp": [str(int(start_ts)), str(int(end_ts))],
        "limit": page_size,
        "page": page,
        "type": ioc_types or SUPPORTED_IOC_TYPES,
        "includeEventUuid": 1,
        "includeEventTags": 1,
        "to_ids": 1,
    }
    if published_only:
        body["published"] = 1
    if tag_filter:
        tags = [t.strip() for t in tag_filter.split(',') if t.strip()]
        or_tags = [t for t in tags if not t.startswith('!')]
        not_tags = [t.lstrip('!') for t in tags if t.startswith('!')]
        tag_obj = {}
        if or_tags:
            tag_obj["OR"] = or_tags
        if not_tags:
            tag_obj["NOT"] = not_tags
        if tag_obj:
            body["tags"] = tag_obj
    return body


def _make_request(logger, endpoint, headers, body, verify_ssl, proxy_dict):
    try:
        response = requests.post(
            endpoint, headers=headers, json=body,
            verify=verify_ssl, proxies=proxy_dict, timeout=(30, 120)
        )
        if response.status_code in (401, 403):
            return {"error": True, "reason": "Authentication failed [%d]" % response.status_code}
        if response.status_code == 404:
            return {"error": True, "reason": "Endpoint not found [404]"}
        if response.status_code in (429, 503):
            return {"error": True, "reason": "Server unavailable [%d]" % response.status_code}
        if response.status_code != 200:
            return {"error": True, "reason": "Unexpected [%d]" % response.status_code}
        return response
    except requests.exceptions.Timeout:
        return {"error": True, "reason": "Request timed out"}
    except requests.exceptions.ConnectionError as e:
        return {"error": True, "reason": "Connection failed: %s" % str(e)[:200]}
    except Exception as e:
        return {"error": True, "reason": str(e)[:200]}


def test_connection(logger, misp_url, headers, verify_ssl, proxy_dict=None):
    try:
        endpoint = misp_url.rstrip('/') + '/servers/getVersion'
        response = requests.get(
            endpoint, headers=headers,
            verify=verify_ssl, proxies=proxy_dict, timeout=10
        )
        if response.status_code == 200:
            version = response.json().get("version", "unknown")
            logger.info("MISP connection OK (v%s)", version)
            return True
        logger.error("MISP connection failed [%d]", response.status_code)
        return False
    except Exception as e:
        logger.error("MISP connection failed: %s", e)
        return False


def get_attributes(logger, misp_url, start_ts, end_ts, page, page_size,
                   headers, tag_filter, published_only, verify_ssl,
                   proxy_dict=None, ioc_types=None):
    body = build_attribute_body(
        start_ts, end_ts, page, page_size,
        tag_filter, published_only, ioc_types
    )
    endpoint = misp_url.rstrip('/') + '/attributes/restSearch'

    result = _make_request(logger, endpoint, headers, body, verify_ssl, proxy_dict)
    if isinstance(result, dict):
        return result

    data = result.json()
    attributes = data.get('response', {}).get('Attribute', [])
    logger.info("Fetched %d attributes (page %d)", len(attributes), page)
    return attributes


def lean_attribute(attr):
    return {
        "type": attr.get("type"),
        "category": attr.get("category"),
        "value": attr.get("value"),
        "to_ids": attr.get("to_ids"),
        "uuid": attr.get("uuid"),
        "event_id": attr.get("event_id"),
        "event_uuid": attr.get("event_uuid"),
        "event_info": attr.get("event_info", ""),
        "timestamp": attr.get("timestamp"),
        "comment": attr.get("comment") or None,
        "tags": _extract_tags(attr),
    }


def _extract_tags(attr):
    tags = []
    for t in attr.get("EventTag", attr.get("Tag", [])):
        tag = t.get("Tag", t) if isinstance(t, dict) else {}
        name = tag.get("name", "")
        if name:
            tags.append(name)
    return tags or None


def build_proxy_dict(proxy_settings):
    if not proxy_settings:
        return None
    enabled = proxy_settings.get("proxy_enabled", "0")
    if not enabled or str(enabled) in ("0", "false", "False"):
        return None
    url = proxy_settings.get("proxy_url", "")
    port = proxy_settings.get("proxy_port", "")
    ptype = proxy_settings.get("proxy_type", "http")
    user = proxy_settings.get("proxy_username", "")
    pwd = proxy_settings.get("proxy_password", "")
    if not url:
        return None
    auth = f"{user}:{pwd}@" if user and pwd else ""
    proxy_uri = f"{ptype}://{auth}{url}:{port}" if port else f"{ptype}://{auth}{url}"
    return {"http": proxy_uri, "https": proxy_uri}


def save_state(state, log_location, source, logger=None):
    try:
        file_dir = os.path.join(log_location, 'misp_data_input', 'misp-data-' + str(source))
        filepath = os.path.join(file_dir, 'state.json')
        os.makedirs(file_dir, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(json.dumps(state))
    except Exception as e:
        if logger:
            logger.error("save_state failed: %s", e)


def load_state(log_location, source, logger=None):
    try:
        file_dir = os.path.join(log_location, 'misp_data_input', 'misp-data-' + str(source))
        filepath = os.path.join(file_dir, 'state.json')
        if os.path.exists(filepath) and os.path.getsize(filepath):
            with open(filepath, "r") as f:
                return json.loads(f.read())
        return None
    except Exception as e:
        if logger:
            logger.error("load_state failed: %s", e)
        return None

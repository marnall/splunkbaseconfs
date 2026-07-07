from __future__ import print_function
import os
import sys
import json
import six.moves.urllib.request, six.moves.urllib.error, six.moves.urllib.parse

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
APP_NAME = "rootly-splunk"


def _build_rootly_fields(payload):
    """Build the rootly namespace fields from configuration."""
    settings = payload.get('configuration', {})
    rootly = {}

    # Preserve any existing rootly fields (e.g. notification_target)
    if isinstance(payload.get('rootly'), dict):
        rootly = payload['rootly'].copy()

    # Description
    description = settings.get('description', '').strip()
    if description:
        rootly['description'] = description

    # Summary override
    summary = settings.get('summary', '').strip()
    if summary:
        rootly['summary'] = summary

    # Custom fields (JSON object merged into rootly namespace)
    custom_fields_str = settings.get('custom_fields', '').strip()
    if custom_fields_str:
        try:
            custom_fields = json.loads(custom_fields_str)
            if isinstance(custom_fields, dict):
                rootly.update(custom_fields)
            else:
                print("WARN custom_fields must be a JSON object, got %s" % type(custom_fields).__name__, file=sys.stderr)
        except (json.JSONDecodeError, ValueError) as e:
            print("WARN Could not parse custom_fields JSON: %s" % e, file=sys.stderr)

    return rootly


def _read_integration_url_from_conf():
    """Read integration URL directly from rootly.conf on disk.

    Uses Python's configparser to read the conf file, bypassing the Splunk
    REST API entirely. This avoids the list_storage_passwords capability
    requirement that prevents non-admin users from reading storage passwords.

    Reads default/rootly.conf first, then local/rootly.conf (local overrides).
    """
    conf_paths = [
        os.path.join(APP_DIR, "default", "rootly.conf"),
        os.path.join(APP_DIR, "local", "rootly.conf"),
    ]
    try:
        parser = ConfigParser()
        parser.read(conf_paths)
        url = parser.get("settings", "integration_url")
        if url and url.strip():
            return url.strip()
    except Exception as e:
        print("DEBUG Could not read integration_url from rootly.conf: %s" % e, file=sys.stderr)
    return None


def _read_integration_url_from_passwords(service):
    """Read integration URL from Splunk storage passwords.

    Requires the list_storage_passwords capability. Falls back gracefully
    if the user lacks this permission.
    """
    try:
        for passwd in service.storage_passwords:
            if passwd.realm is None or passwd.realm.strip() != APP_NAME:
                continue
            if passwd.username == "integration_url":
                return passwd.clear_password
    except Exception as e:
        print("WARN Could not read storage_passwords (user may lack "
              "list_storage_passwords capability): %s" % e, file=sys.stderr)
    return None


def _resolve_integration_url(service, settings):
    """Resolve the integration URL from all sources in priority order.

    Priority (highest first):
    1. Per-alert override (integration_url_override in alert action form)
    2. Conf file on disk (rootly.conf - no Splunk capabilities needed)
    3. Storage passwords (requires list_storage_passwords capability)
    4. Alert action default (alert_actions.conf param.integration_url)
    """
    if settings.get('integration_url_override'):
        return settings['integration_url_override']

    url = _read_integration_url_from_conf()
    if url:
        return url

    url = _read_integration_url_from_passwords(service)
    if url:
        return url

    if settings.get('integration_url'):
        return settings['integration_url']

    return None


def _sanitize_payload(payload):
    """Remove sensitive data and parse custom_fields before sending."""
    del payload['session_key']

    config = payload.get('configuration', {})
    for key in ('integration_url', 'integration_url_override'):
        config.pop(key, None)

    custom_fields_str = config.get('custom_fields', '').strip()
    if custom_fields_str:
        try:
            config['custom_fields'] = json.loads(custom_fields_str)
        except (json.JSONDecodeError, ValueError):
            pass
    else:
        config.pop('custom_fields', None)


def _post_to_rootly(url, payload):
    """Send the alert payload to Rootly via HTTPS POST."""
    body = json.dumps(payload).encode('utf-8')
    req = six.moves.urllib.request.Request(url, body, {"Content-Type": "application/json"})

    try:
        res = six.moves.urllib.request.urlopen(req)
        response_body = res.read()
        print("INFO Rootly server responded with HTTP status=%d" % res.code, file=sys.stderr)
        print("DEBUG Rootly server response: %s" % response_body, file=sys.stderr)
        return 200 <= res.code < 300
    except six.moves.urllib.error.HTTPError as e:
        print("ERROR Error sending message: %s" % e, file=sys.stderr)
        print("ERROR Server response: %s" % e.read(), file=sys.stderr)
        return False


def send_notification(payload):
    settings = payload.get('configuration', {})
    session_key = str(payload.get('session_key'))

    service = client.connect(token=session_key, owner='nobody', app=APP_NAME)

    url = _resolve_integration_url(service, settings)
    if not url:
        print("ERROR Integration url must be configured", file=sys.stderr)
        return False

    if not url.startswith('https://'):
        print("ERROR URL must use HTTPS", file=sys.stderr)
        return False

    rootly_fields = _build_rootly_fields(payload)
    if rootly_fields:
        payload['rootly'] = rootly_fields

    _sanitize_payload(payload)

    return _post_to_rootly(url, payload)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        success = send_notification(payload)

        if not success:
            print("FATAL Failed sending Incident alert notification", file=sys.stderr)
            sys.exit(2)
        else:
            print("INFO Incident alert notification successfully sent", file=sys.stderr)
    else:
        print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)

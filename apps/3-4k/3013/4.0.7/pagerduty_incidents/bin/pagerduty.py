from __future__ import print_function
import os
import subprocess
import sys
import json
import re
import six.moves.urllib.request, six.moves.urllib.error, six.moves.urllib.parse
from urllib.parse import urlparse
from fnmatch import fnmatch

if sys.version < '3':
    from ConfigParser import ConfigParser
    from StringIO import StringIO
else:
    from configparser import ConfigParser
    from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client

def send_notification(payload):
    settings = payload.get('configuration')
    session_key = str(payload.get('session_key'))

    url = ""
    integration_key = None
    integration_url = None

    server_uri = payload.get('server_uri', 'https://localhost:8089')
    try:
        parsed = urlparse(server_uri)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 8089
    except Exception:
        print("WARN Could not parse server_uri '%s', using defaults" % server_uri, file=sys.stderr)
        host, port = 'localhost', 8089

    service = client.connect(token=session_key, app='pagerduty_incidents', host=host, port=port)
    for passwd in service.storage_passwords:
        if passwd.realm is None or passwd.realm.strip() != 'pagerduty_incidents':
            continue
        if passwd.username == "integration_url":
            integration_url = passwd.clear_password
        if passwd.username == "integration_key":
            integration_key = passwd.clear_password


    # Attempting to set the url from the configs
    if settings.get('integration_url_override'):
        url = settings.get('integration_url_override')
    elif settings.get('integration_key_override'):
        url = settings.get('integration_key_override')
    elif integration_url:
        url = integration_url
    elif settings.get('integration_url'):
        url = settings.get('integration_url')
    elif integration_key:
        url = integration_key
    elif settings.get('integration_key'):
        url = settings.get('integration_key')
    else:
        print("ERROR Integration key or url must be configurated specified.", file=sys.stderr)
        return False

    # Check for a global rule key
    if len(url) == 32 and url.startswith('R'):
        url = 'https://events.pagerduty.com/x-ere/' + url
    elif len(url) == 32:
        url = 'https://events.pagerduty.com/integration/' + url + '/enqueue'

    custom_details = settings.get('custom_details')

    if not custom_details is None:
        try:
            if type(custom_details) is dict:
                payload["result"]["custom_details"] = custom_details
            else:
                payload["result"]["custom_details"] = json.loads(custom_details)
        except ValueError:
            print("WARN Failed to convert custom details to JSON object", file=sys.stderr)
            payload["result"]["custom_details"] = custom_details


    del payload['session_key']

    body = json.dumps(payload)
    body = body.encode('utf-8')

    if not url.startswith('https://'):
        print("URL must use HTTPS", file=sys.stderr)
        return False

    req = six.moves.urllib.request.Request(url, body, {"Content-Type": "application/json"})

    try:
        res = six.moves.urllib.request.urlopen(req)
        body = res.read()
        print("INFO PagerDuty server responded with HTTP status=%d" % res.code, file=sys.stderr)
        print("DEBUG PagerDuty server response: %s" % body, file=sys.stderr)
        return 200 <= res.code < 300
    except six.moves.urllib.error.HTTPError as e:
        print("ERROR Error sending message: %s (%s)" % (e, str(dir(e))), file=sys.stderr)
        print("ERROR Server response: %s" % e.read(), file=sys.stderr)
        return False

def replace_tokens(payload):
    if not (payload.get('configuration') and payload.get('configuration').get('custom_details')):
        return payload

    custom_details = payload['configuration']['custom_details']

    matches = re.findall("\"__(.*)__\"", custom_details)
    for match in matches:
        # escape all of the quotes
        str = json.dumps(match)
        # replace the underscores
        match = "\"__{0}__\"".format(match)
        # replace the string
        custom_details = custom_details.replace(match, str)

    payload['configuration']['custom_details'] = custom_details

    return payload


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        payload = replace_tokens(payload)
        success = send_notification(payload)

        if not success:
            print("FATAL Failed trying to incident alert", file=sys.stderr)
            sys.exit(2)
        else:
            print("INFO Incident alert notification successfully sent", file=sys.stderr)
    else:
        print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)

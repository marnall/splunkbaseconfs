from __future__ import print_function
import platform
import os
import re
import sys
import json
import time
import splunk.entity as entity
import six.moves.urllib.request, six.moves.urllib.error, six.moves.urllib.parse

IS_PY_2 = sys.version < '3'

def post(url, body):
    """
    post is a version independent way of posting data
    url  [str] - the url of the request
    body [str] - the payload to send
    returns the response status code and body
    """
    res_body = ""
    res_code = -1
    req = six.moves.urllib.request.Request(url, body.encode('utf-8'), {"Content-Type": "application/json"})
    res = six.moves.urllib.request.urlopen(req, timeout=30)
    res_body = res.read().decode('utf-8')
    res_code = res.code

    return (res_code, res_body)

def get_api_key(settings):
    try:
          api_key = settings.get('api_key')
          return api_key
    except Exception as e:
        raise Exception("Could not get %s credentials from splunk. Error: %s"
                        % (myapp, str(e)))

def create_alert(payload):
    search_name = payload.get('search_name')
    settings = payload.get('configuration')
    api_key = get_api_key(settings)

    uuid_pattern = re.compile(
        '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z')
    match = uuid_pattern.match(api_key)

    if match is not None:
        url = "https://api.eu.opsgenie.com/v1/json/splunk?apiKey=" + api_key
        print("DEBUG Only API Key is provided for search=%s" % search_name, file=sys.stderr)

    body = json.dumps(payload)

    print('DEBUG Posting data for search=%s using API with body=%s' % (search_name, body),
        file=sys.stderr)

    for i in range(3):
        try:
            (code, body) = post(url, body)
            print("INFO Opsgenie server responded with HTTP status=%d for search=%s" % (code, search_name),
                file=sys.stderr)
            return 200 <= code < 300
        except Exception as e:
            print("ERROR Error sending data to Opsgenie for search=%s: %s" % (search_name, e),
                file=sys.stderr)
            print("Retrying in 1 second for search=%s" % search_name, file=sys.stderr)
            time.sleep(1)
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
    try:
        payload = json.loads(sys.stdin.read())
        search = payload.get('search_name')
        success = create_alert(payload)
        if not success:
            print("FATAL Failed to post data to Opsgenie for search=%s" % search, file=sys.stderr)
            sys.exit(2)
        else:
            print("INFO Data posted to Opsgenie Successfully for search=%s" % search, file=sys.stderr)
    except Exception as e:
        print("ERROR Unexpected error: %s" % e, file=sys.stderr)
        sys.exit(3)

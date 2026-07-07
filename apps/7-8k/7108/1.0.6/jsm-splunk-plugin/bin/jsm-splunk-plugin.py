from __future__ import print_function
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

def get_api_key(sessionKey):
    if len(sessionKey) == 0:
        print("ERROR Did not receive a session key from splunkd. " +
              "Please enable passAuth in inputs.conf for this script", file=sys.stderr)
        raise Exception("No session key provided. Could not get JSM API Key.")

    try:
        # list all credentials
        entities = entity.getEntities(['storage', 'passwords'], namespace='jsm-splunk-plugin', count=-1,
                                      owner='nobody', sessionKey=sessionKey)
    except Exception as e:
        raise Exception("Could not get JSM API Key from credentials. Error: %s"
                        % (str(e)))

    api_key=""
    url=""

    for i, c in entities.items():
        api_key_regex = re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z')
 
        if c['username'] == 'api_key':
            masked_password = c['clear_password'][:6] + '*' * (len(c['clear_password']) - 6)
            print("DEBUG Found api_key:%s" % masked_password, file=sys.stderr)
            # Check if the api_key we found is for jsm-splunk-plugin, since global credentials can also get listed here (e.g. app=system)
            if c['eai:acl']['app'] != 'jsm-splunk-plugin':
                print("DEBUG Skipping password=%s which has app=%s" % (c['username'], c['eai:acl']['app']), file=sys.stderr)
                continue
            if api_key_regex.match(c['clear_password']) is not None:
                print("DEBUG Regex test for api_key: Success", file=sys.stderr)
                api_key = c['clear_password']
            else:
                print("DEBUG Regex test for api_key: Failure", file=sys.stderr)

        elif c['username'] == 'url':
            print("DEBUG Found url:%s" % c['clear_password'], file=sys.stderr)
            url = c['clear_password']

    if api_key == "":
        raise Exception("No credentials found. Could not get JSM API Key.")
    
    if url == "":
        print("INFO Could not get JSM URL, assuming default: 'https://api.atlassian.com'", file=sys.stderr)
        url = "https://api.atlassian.com"

    return api_key, url

def create_alert(payload):
    search_name = payload.get('search_name')
    session_key = payload.get('session_key')
    api_key, url = get_api_key(session_key)

    url = url + "/jsm/ops/integration/v1/json/splunk"
    payload['apiKey'] = api_key

    body = json.dumps(payload)

    print('DEBUG Posting data for url=%s search=%s using API with body=%s' % (url, search_name, body),
            file=sys.stderr)

    for i in range(3):
        try:
            (code, body) = post(url, body)
            print("INFO JSM server responded with HTTP status=%d for search=%s" % (code, search_name),
                    file=sys.stderr)
            return 200 <= code < 300
        except Exception as e:
            print("ERROR Error sending data to JSM for search=%s: %s" % (search_name, e),
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
            print("FATAL Failed to post data to JSM for search=%s" % search, file=sys.stderr)
            sys.exit(2)
        else:
            print("INFO Data posted to JSM Successfully for search=%s" % search, file=sys.stderr)
    except Exception as e:
        print("ERROR Unexpected error: %s" % e, file=sys.stderr)
        sys.exit(3)

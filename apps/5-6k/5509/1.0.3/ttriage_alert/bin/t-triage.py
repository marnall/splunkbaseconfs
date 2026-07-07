from __future__ import print_function
import sys, json, urllib.request, urllib.error, urllib.parse
import time
import gzip
import csv

def decompress(results_file):
    keys = {'_time', '_raw', '_indextime', 'host', 'source', 'sourcetype'}
    if (results_file.endswith(".gz")):
        with gzip.open(results_file,'rt') as search_results_file:
            return search_results_file.read()
    else:
        return None

def sendEvents(token, tokenType, payload):
    api = payload.get('configuration').get('base_url') + '/logs/push'
    print('DEBUG Calling URL = "%s", trying to send events' % api, file=sys.stderr)
    payload['events'] = decompress(payload.get('results_file'))
    payload['alert_time'] = str(round(time.time() * 1000))
    payload['pattern'] = payload.get("configuration").get("pattern")
    payload['package_names'] = payload.get("configuration").get("package_names")

    file = open("/var/log/splunk_test_payload.log", "w")
    file.write(json.dumps(payload))
    file.close()

    try:
        req = urllib.request.Request(api, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Authorization": "%s %s" % (tokenType, token)})
        res = urllib.request.urlopen(req)
        body = res.read()
        print("INFO t-Triage responded with HTTP status %d" % res.code, file=sys.stderr)
        print("DEBUG t-Triage response: %s" % json.loads(body), file=sys.stderr)
        res_dict = json.loads(body)
        return res_dict
    except urllib.error.HTTPError as e:
        print("ERROR Error sending message: %s" % e, file=sys.stderr)
        return None

def login(settings):
    print("DEBUG Sending message with settings %s" % settings, file=sys.stderr)
    base_url = settings.get('base_url')
    client_id = settings.get('client_id')
    secret_id = settings.get('secret_id')
    auth_url = "%s/auth/token" % base_url

    if (base_url != None and base_url[-1] == "/"):
        base_url = base_url.rstrip('/')

    print("INFO Sending message to t-Triage URL = %s" % auth_url, file=sys.stderr)

    auth_body = json.dumps(dict(clientId = client_id, secretId = secret_id)).encode()
    print('DEBUG Calling URL = "%s", trying to authenticate" % auth_url', file=sys.stderr)
    try:
        req = urllib.request.Request(auth_url, data=auth_body, headers={"Content-Type": "application/json"})
        res = urllib.request.urlopen(req)
        body = res.read()
        print("INFO t-Triage responded with HTTP status %d" % res.code, file=sys.stderr)
        res_dict = json.loads(body)
        return [res_dict['accessToken'], res_dict['tokenType']]
    except urllib.error.HTTPError as e:
        print("ERROR Error sending message: %s" % e, file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())

        auth = login(payload.get('configuration'))
        if (auth == None):
            print("FATAL Failed trying to connect with t-Triage", file=sys.stderr)
            sys.exit(2)
        sendEvents(auth[0], auth[1], payload)
        print("INFO Events succesfully sent to t-Triage", file=sys.stderr)
    else:
        print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)

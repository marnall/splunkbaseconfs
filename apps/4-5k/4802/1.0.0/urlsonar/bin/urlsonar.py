import sys
import json
import csv
import gzip
from collections import OrderedDict
from future.moves.urllib.request import urlopen, Request
from future.moves.urllib.error import HTTPError, URLError

#####
## Script adapated from Splunk webhook alert. Modified to send POST to URLSonar. See www.groundsecurity.com for details.
#####

def urlsonar_request(apiurl, body, user_agent=None):
    if apiurl is None:
        sys.stderr.write("ERROR No URLSonar Endpoint provided\n")
        return False
    sys.stderr.write("INFO Sending POST request to URLSonar Endpoint %s with payload= %s \n" % (apiurl, body))
    sys.stderr.write("DEBUG Body: %s\n" % body)
    try:
        req = Request(apiurl, body, {"Content-Type": "application/json"})
        res = urlopen(req)
        if 200 <= res.code < 300:
            sys.stderr.write("INFO URLSonar API responded with HTTP status=%d\n" % res.code)
            return True
        else:
            sys.stderr.write("ERROR URLSonar API responded with HTTP status=%d\n" % res.code)
            return False
    except HTTPError as e:
        sys.stderr.write("ERROR Error sending URLSonar request: %s\n" % e)
    except URLError as e:
        sys.stderr.write("ERROR Error sending URLSonar request: %s\n" % e)
    except ValueError as e:
        sys.stderr.write("ERROR Invalid URLSonar Endpoint: %s\n" % e)
    return False

def build_request(vtkey, lickey, responsehost, checkurl):
    urlsonarendpoint = "https://urlsonar.azurewebsites.net/api/httptrigger"
    urlsonaraccess = "?code=VwutI1vLsbmbBtYagqnJFYkHrdzVqKIzmaOpv7z6X0Gb81RPoo8JVg=="
    urlsonarhost = urlsonarendpoint + urlsonaraccess
    if vtkey is None:
        sys.stderr.write("ERROR No VT API key provided\n")
        return False
    elif lickey is None:
        sys.stderr.write("ERROR No license key provided\n")
        return False
    elif responsehost is None:
        sys.stderr.write("ERROR No response target provided\n")
        return False
    elif checkurl is None:
        sys.stderr.write("ERROR No URL to check provided\n")
        return False
    else:
        body = {"apikey":vtkey,"appkey":lickey,"responseto":responsehost,"url":checkurl}
        jsonbytes = json.dumps(body).encode('utf-8')
        urlsonar_request(urlsonarhost, jsonbytes)
        return True
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        sys.stderr.write("FATAL Unsupported execution mode (expected --execute flag)\n")
        sys.exit(1)
    try:
        payload = json.loads(sys.stdin.read())
        vtkey=payload['configuration'].get('vtkey')
        appkey=payload['configuration'].get('appkey')
        responsehost=payload['configuration'].get('responsehost')
        checkurl=payload['result'].get('url')
        if not build_request(vtkey, appkey, responsehost, checkurl):
            sys.exit(2)
    except Exception as e:
        sys.stderr.write("ERROR Unexpected error: %s\n" % e)
        sys.exit(3)

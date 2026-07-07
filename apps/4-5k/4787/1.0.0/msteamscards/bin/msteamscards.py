import sys
import json
import csv
import gzip
from collections import OrderedDict
from future.moves.urllib.request import urlopen, Request
from future.moves.urllib.error import HTTPError, URLError

#####
## Script adapated from Splunk webhook alert. Modified to send an Office 365 Card to a Teams Incoming Webhook connector.
## See www.groundsecurity.com for details.
#####

def webhook(url, body, user_agent=None):
    if url is None:
        sys.stderr.write("ERROR No Teams Connector URL provided\n")
        return False
    sys.stderr.write("INFO Sending POST request to Teams, body= %s \n" % body)
    sys.stderr.write("DEBUG Body: %s\n" % body)
    try:
        req = Request(url, body, {"Content-Type": "application/json"})
        res = urlopen(req)
        if 200 <= res.code < 300:
            sys.stderr.write("INFO Teams responded with HTTP status=%d\n" % res.code)
            return True
        else:
            sys.stderr.write("ERROR Teams responded with HTTP status=%d\n" % res.code)
            return False
    except HTTPError as e:
        sys.stderr.write("ERROR Error sending POST request: %s\n" % e)
    except URLError as e:
        sys.stderr.write("ERROR Error sending POST request: %s\n" % e)
    except ValueError as e:
        sys.stderr.write("ERROR Invalid Teams URL: %s\n" % e)
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        sys.stderr.write("FATAL Unsupported execution mode (expected --execute flag)\n")
        sys.exit(1)
    try:
        payload = json.loads(sys.stdin.read())
        teamsurl = payload['configuration'].get('webhookurl')
        typevar = "@type"
        contextvar = "@context"
        targetsdict = {"os":"default","uri":payload.get('results_link')}
        actiondict = {typevar:"OpenUri","name":"Go to Search","targets":[targetsdict]}
        sectionsdict = {"startGroup": "true","activityImage":payload['configuration'].get('imgurl'),"activityTitle":payload['configuration'].get('title'),"activitySubtitle":payload['configuration'].get('subtitle'),"text":payload['result'].get('messagetext'),"potentialAction":[actiondict]}
        body = {typevar:"MessageCard",contextvar:"https://schema.org/extensions","summary":payload['configuration'].get('title'),"themeColor":payload['configuration'].get('theme'),"sections":[sectionsdict]}
        jsonbytes = json.dumps(body).encode('utf-8')
        if not webhook(teamsurl, jsonbytes):
            sys.exit(2)
    except Exception as e:
        sys.stderr.write("ERROR Unexpected error: %s\n" % e)
        sys.exit(3)

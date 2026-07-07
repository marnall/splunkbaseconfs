import sys
import json
import urllib2
import urllib
import base64
from collections import OrderedDict


def forward_log_ls(settings):
    url = settings['configuration'].get('logsentinelurl')
    orgId = settings['configuration'].get('orgId')
    appId = settings['configuration'].get('appId')
    secret = settings['configuration'].get('secret')
    user_agent = settings['configuration'].get('user_agent', 'Splunk')

    auth = 'Basic ' + base64.b64encode(orgId + ':' + secret)

    if not url.endswith('/'):
        url += '/'

    url = url + 'api/log'

    result = settings.get('result')
    details = result.get('_raw')
    body = json.dumps(details)

    actorId = result.get('actorId')
    if not actorId:
        url = url + '/simple'
    else:
        url = url + '/' + urllib2.quote(actorId)
        action = result.get('action')
        if not action:
            action = 'missing_action'
        url = url + '/' + urllib2.quote(action)

    entityType = result.get('entityType')
    entityId = result.get('entityId')
    if entityType:
        if entityId:
            url = url + '/' + urllib2.quote(entityId)
            url = url + '/' + urllib2.quote(entityType)

    reqParams = OrderedDict()

    actorDisplayName = result.get('actorDisplayName')
    if actorDisplayName:
        reqParams['actorDisplayName'] = actorDisplayName
    loglevel = result.get('logLevel')
    if loglevel:
        reqParams['logLevel'] = loglevel
    binaryContent = result.get('binaryContent')
    if binaryContent:
        reqParams['binaryContent'] = binaryContent
    actorDepartment = result.get('actorDepartment')
    if actorDepartment:
        reqParams['actorDepartment'] = actorDepartment

    if len(reqParams):
        url += '?' + urllib.urlencode(reqParams)

    headers = {"Content-Type": "application/json", "User-Agent": user_agent,
               "Application-Id": appId, "Authorization": auth}

    entryType = result.get('entryType')
    if entryType:
        headers['Audit-Log-Entry-Type'] = entryType

    if url is None:
        sys.stderr.write("ERROR No URL provided\n")
        return False
    # sys.stderr.write("INFO Sending POST request to url=%s with size=%d bytes payload\n" % (url, len(body)))
    # sys.stdout.write("DEBUG Body: %s\n" % body)
    try:
        req = urllib2.Request(url, body, headers)
        res = urllib2.urlopen(req)
        if 200 <= res.code < 300:
            # sys.stdout.write("INFO Logsentinel responded with HTTP status=%d\n" % res.code)
            return True
        else:
            sys.stderr.write("WARN headers: %s\n" % headers)
            sys.stderr.write("ERROR Logsentinel responded with HTTP status=%d\n" % res.code)
            return False
    except urllib2.HTTPError as e:
        sys.stderr.write("WARN headers: %s\n" % headers)
        sys.stderr.write("ERROR HTTPError sending Logsentinel request: %s\n" % e)
    except urllib2.URLError as e:
        sys.stderr.write("ERROR URLError sending Logsentinel request: %s\n" % e)
    except ValueError as e:
        sys.stderr.write("ERROR Invalid URL: %s\n" % e)
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        sys.stderr.write("FATAL Unsupported execution mode (expected --execute flag)\n")
        sys.exit(1)
    try:
        settings = json.loads(sys.stdin.read())

        if not forward_log_ls(settings):
            sys.exit(2)
    except Exception as e:
        sys.stderr.write("ERROR Unexpected error: %s\n" % e)
        sys.exit(3)

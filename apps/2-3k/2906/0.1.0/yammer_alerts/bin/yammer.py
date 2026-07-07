import sys
import json
import urllib2


def send_yammer_message(settings):
    params = dict()
    params['body'] = settings.get('body')
    params['group_id'] = settings.get('group_id')
    token = settings.get('token')

    url = 'https://www.yammer.com/api/v1/messages.json'
    body = json.dumps(params)
    print >> sys.stderr, 'DEBUG Calling url="%s" with body=%s' % (url, body)
    req = urllib2.Request(url, body, headers={
                          "Content-Type": "application/json", "Authorization": "Bearer " + token})
    try:
        res = urllib2.urlopen(req)
        body = res.read()
        print >> sys.stderr, "INFO Yammer API responded with HTTP status=%d" % res.code
        print >> sys.stderr, "DEBUG Yammer API response: %s" % json.dumps(body)
        return 200 <= res.code < 300
    except urllib2.HTTPError, e:
        print >> sys.stderr, "ERROR Error sending message: %s" % e
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        config = payload.get('configuration')
        if not send_yammer_message(config):
            print >> sys.stderr, "FATAL Sending the Yammer message failed"

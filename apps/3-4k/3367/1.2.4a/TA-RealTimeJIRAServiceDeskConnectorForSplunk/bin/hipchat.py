import sys, json, urllib2


def send_message(settings):
    print >> sys.stderr, "DEBUG Sending message with settings %s" % settings
    room = settings.get('room')
    auth_token = settings.get('auth_token')
    base_url = settings.get('base_url').rstrip('/')
    fmt = settings.get('format', 'text')
    print >> sys.stderr, "INFO Sending message to hipchat room=%s with format=%s" % (room, fmt)
    url = "%s/room/%s/notification?auth_token=%s" % (
        base_url, urllib2.quote(room), urllib2.quote(auth_token)
    )
    body = json.dumps(dict(
        message=settings.get('message'),
        message_format=fmt,
        color=settings.get('color', "green")
    ))
    print >> sys.stderr, 'DEBUG Calling url="%s" with body=%s' % (url, body)
    req = urllib2.Request(url, body, {"Content-Type": "application/json"})
    try:
        res = urllib2.urlopen(req)
        body = res.read()
        print >> sys.stderr, "INFO HipChat server responded with HTTP status=%d" % res.code
        print >> sys.stderr, "DEBUG HipChat server response: %s" % json.dumps(body)
        return 200 <= res.code < 300
    except urllib2.HTTPError, e:
        print >> sys.stderr, "ERROR Error sending message: %s" % e
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        if not send_message(payload.get('configuration')):
            print >> sys.stderr, "FATAL Failed trying to send room notification"
            sys.exit(2)
        else:
            print >> sys.stderr, "INFO Room notification successfully sent"
    else:
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)

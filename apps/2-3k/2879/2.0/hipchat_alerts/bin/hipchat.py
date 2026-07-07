import sys
import json
import urllib2

from fnmatch import fnmatch


def send_notification(payload):
    settings = payload.get('configuration')
    print >> sys.stderr, "DEBUG Sending message with settings %s" % settings
    room = settings.get('room')
    auth_token = settings.get('auth_token_override')
    if not auth_token:
        auth_token = settings.get('auth_token')
    base_url = settings.get('base_url').rstrip('/')
    fmt = settings.get('format', 'text')
    print >> sys.stderr, "INFO Sending message to hipchat room=%s with format=%s" % (room, fmt)
    url = "%s/room/%s/notification?auth_token=%s" % (
        base_url, urllib2.quote(room), urllib2.quote(auth_token)
    )
    msg = settings.get('message')
    notification_type = settings.get('notification_type', 'message')
    send_card = notification_type == 'card'
    msg_limit = 500 if send_card else 10000
    if len(msg) > msg_limit:
        print >> sys.stderr, "WARN Message is longer than limit of %d characters and will be truncated" % msg_limit
        msg = msg[0:msg_limit - 3] + '...'
    data = dict(
        message=msg,
        message_format=fmt,
        color=settings.get('color', 'gray'),
        notify=normalize_bool(settings.get('notify', 'false')),
    )
    if send_card:
        data['card'] = dict(
            style="application",
            url=payload.get('results_link'),
            id=payload.get('sid'),
            title=payload.get('search_name') or 'Untitled Alert',
            description=msg,
            icon=dict(
                url=settings.get('card_icon')
            ),
            attributes=format_attributes(payload.get('result'), settings.get('card_attributes', ''))
        )

    body = json.dumps(data)
    print >> sys.stderr, 'DEBUG Calling url="%s" with body=%s' % (url, body)
    req = urllib2.Request(url, body, {"Content-Type": "application/json"})
    try:
        res = urllib2.urlopen(req)
        body = res.read()
        print >> sys.stderr, "INFO HipChat server responded with HTTP status=%d" % res.code
        print >> sys.stderr, "DEBUG HipChat server response: %s" % json.dumps(body)
        return 200 <= res.code < 300
    except urllib2.HTTPError, e:
        print >> sys.stderr, "ERROR Error sending message: %s (%s)" % (e, str(dir(e)))
        print >> sys.stderr, "ERROR Server response: %s" % e.read()
        return False


def format_attributes(result, allowed_attrs):
    patterns = allowed_attrs.split(',')
    if not len(patterns):
        return []
    attrs = []
    for field, value in result.items():
        if value and any([fnmatch(field, pattern.strip()) for pattern in patterns]):
            value = value if type(value) is str else json.dumps(value)
            attrs.append(dict(label=field, value=dict(label=value)))
    return attrs


def normalize_bool(value):
    return True if value.lower() in ('1', 'true') else False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        success = send_notification(payload)
        if not success:
            print >> sys.stderr, "FATAL Failed trying to send room notification"
            sys.exit(2)
        else:
            print >> sys.stderr, "INFO Room notification successfully sent"
    else:
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)

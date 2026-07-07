import fix_path
import sys
import os
import datetime
import json
import urllib2
import splunklib.client as client
from splunklib.binding import _spliturl as spliturl
from splunklib.binding import namespace as namespace
import gzip
import csv
from alert_action_utils import iterate_callbacks_from_string

alert_count = 0
callback_url_count = 0
callback_invocation_attempts = 0
callback_invocation_errors = 0


def call_workato(payload, allow_insecure_callback):

    config = payload.get('configuration')
    callback_urls = config.get('callback_urls')
    if callback_urls is None:
        callback_urls = ""
    callback_urls = list(iterate_callbacks_from_string(callback_urls))

    sid = payload.get('sid')

    def log(level, msg):
        print >> sys.stderr, "%s sid=\"%s\" %s" % (level, sid, msg)

    def log_info(msg):
        log("INFO", msg)

    def log_debug(msg):
        log("DEBUG", msg)

    def log_error(msg):
        log("ERROR", msg)

    global alert_count
    global callback_url_count
    global callback_invocation_attempts
    global callback_invocation_errors
    callback_url_count = len(callback_urls)

    def invoke_callbacks(data={}):
        global alert_count
        global callback_url_count
        global callback_invocation_attempts
        global callback_invocation_errors
        alert_count += 1
        for callback_url in callback_urls:
            callback_invocation_attempts += 1
            try:
                if not callback_url.startswith("https://") and not allow_insecure_callback:
                    log_error("insecure callback url: \"%s\"" %
                              callback_url)
                else:
                    req = urllib2.Request(callback_url, json.dumps(data), {
                        "Content-Type": "application/json"})
                    res = urllib2.urlopen(req)
                    body_bytes = len(str(res.read()))
                    log_info("callback=\"%s\" status=%d body_length=\"%d\"" % (
                        callback_url, res.code, body_bytes))
            except urllib2.HTTPError, e:
                callback_invocation_errors += 1
                log_error("callback=\"%s\" error=\"%s\"" %
                          (callback_url, str(e)))

    results_file = payload.get('results_file')
    if os.path.isfile(results_file):
        with gzip.open(results_file, 'rb') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                payload = {}
                for name, value in row.iteritems():
                    if not name.startswith('__mv'):
                        payload[name] = value
                invoke_callbacks(payload)
    else:
        invoke_callbacks({})

    log_info("alert_count=%d callback_url_count=%d callback_invocation_attempts=%d callback_invocation_errors=%d" % (
        alert_count, callback_url_count, callback_invocation_attempts, callback_invocation_errors))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = sys.stdin.read()
        payload = json.loads(payload)
        allow_insecure_callback = False
        if len(sys.argv) > 2 and sys.argv[2] == "--allow_insecure_callback":
            allow_insecure_callback = True
        call_workato(payload, allow_insecure_callback)
    else:
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)

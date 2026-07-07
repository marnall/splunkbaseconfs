#!/usr/bin/env python
import sys
import urllib2
try:
    import simplejson as json
except:
    import json


def send_bp_alert(payload):
    """
    Send Alert to the BigPanda REST Alert API
    """

    configuration = payload.get("configuration")
    headers = {
        'content-type': 'application/json',
        'Authorization': 'Bearer %s' % configuration.get('api_token')
        }
    url = "%s/data/integrations/splunk?app_key=%s" % (configuration.get('api_url'), configuration.get('app_key'))
    data = dict(payload)

    override_keys = [k for k in ["primary_override", "secondary_override", "description_override"] if configuration.get(k, None)]
    if override_keys and len(override_keys) > 0:
        data["overrides"] = {}
        for key in override_keys:
            data["overrides"][key.replace("_override", "")] = configuration.get(key)

    del data['configuration']

    try:
        req = urllib2.Request(url, json.dumps(data), headers)
        response = urllib2.urlopen(req, timeout=30)
        if response.code >= 400:
            error_message = 'ERROR HTTP Error code: %s.' % response.code
            text = response.read()
            if text:
                error_message += 'Message: %s.' % text
            print >> sys.stderr, error_message
            return False
        return True
    except Exception as error:
        print >> sys.stderr, "ERROR %s" % error
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        try:
            if not send_bp_alert(payload):
                sys.exit(2)
            else:
                print >> sys.stderr, "INFO Alert succesfully sent to BigPanda"
        except Exception as e:
            print >> sys.stderr, "ERROR Unexpected error: %s" % e
            sys.exit(3)
    else:
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)

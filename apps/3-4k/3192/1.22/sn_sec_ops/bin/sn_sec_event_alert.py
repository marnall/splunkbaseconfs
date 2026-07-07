
import sys
import json
import time
import uuid
import traceback
import requests
import sn_sec_util as snutil
    
def createAlertEvent(sessionKey, settings, resultLink):
    datamap = {} 
    additionalinfo = {}
    snutil.addCorrelationValues(additionalinfo)
    additionalinfo["external_url"] = resultLink
    datamap["node"] = settings.get('node')
    datamap["resource"] = settings.get('resource')
    datamap["type"] = settings.get('type')
    datamap["severity"] = settings.get('severity')
    datamap["additional_info"] = json.dumps(additionalinfo)
    snutil.addEventValues(datamap)
    snutil.createEventFromData(sessionKey, json.dumps(datamap))
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:
            inputData = sys.stdin.read()
            payload = json.loads(inputData)
            if not createAlertEvent(payload["session_key"], payload["configuration"], payload["results_link"]):
                print >> sys.stderr, "ERROR: Unable to create ServiceNow Security event"
                sys.exit(2)
        except Exception:
            print >> sys.stderr, "ERROR: Unexpected error: {}".format(traceback.format_exc())
    else:
        print >> sys.stderr, "ERROR: Unsupported mode calling sn_sec_event_alert (expected --execute flag)"
        sys.exit(1)
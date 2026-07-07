from __future__ import print_function
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
    datamap["source"] = settings.get('source')
    datamap["type"] = settings.get('type')
    datamap["severity"] = settings.get('severity')
    datamap["description"] = settings.get('description')
    datamap["time_of_event"] = snutil.parseTime(settings.get('time_of_event'))
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
                print("ERROR: Unable to create ServiceNow Security event", file=sys.stderr)
                sys.exit(2)
        except Exception:
            print("ERROR: Unexpected error: {}".format(traceback.format_exc()), file=sys.stderr)
    else:
        print("ERROR: Unsupported mode calling sn_sec_event_alert (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
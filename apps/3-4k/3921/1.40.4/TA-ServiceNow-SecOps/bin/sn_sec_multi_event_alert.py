from __future__ import print_function
import os
import os.path as op
import sys
import json
import time
import uuid
import gzip
import csv
import traceback
import requests
import sn_sec_util as snutil
    
standardArgs = ["source", "node", "type", "resource", "severity", "description", "time_of_event"]

def createAlertEvent(sessionKey, settings, resultLink, alertResult):
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
    for field in alertResult:
        if field in standardArgs:
            if field == "time_of_event":
                datamap[field] = snutil.parseTime(alertResult[field])
            else:
                datamap[field] = alertResult[field]
        elif not field.startswith("__mv"):
            additionalinfo[field] = alertResult[field]
    datamap["additional_info"] = json.dumps(additionalinfo)
    snutil.addEventValues(datamap)
    snutil.createEventFromData(sessionKey, json.dumps(datamap))
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:
            inputData = sys.stdin.read()
            payload = json.loads(inputData)
            resultFile = payload["results_file"]
            sessionKey = payload["session_key"]
            configuration = payload["configuration"]
            resultsLink = payload["results_link"]
            if not op.exists(resultFile):
                print("ERROR: Missing result file {0} found for alert".format(resultFile), file=sys.stderr)
                sys.exit(2)
                
            csvResult = gzip.open(resultFile, 'rt')
            allSucceeded = True
            allFailed = True
            try:
                for result in csv.DictReader(csvResult):
                    if not createAlertEvent(sessionKey, configuration, resultsLink, result):
                        allSucceeded = False
                    else:
                        allFailed = False
            finally:
                csvResult.close()
            if allFailed:
                print("ERROR: No ServiceNow Security events created", file=sys.stderr)
                sys.exit(2)
            if not allSucceeded:
                print("ERROR: Some results failed to create a ServiceNow Security event", file=sys.stderr)
                sys.exit(2)
        except Exception:
            print("ERROR: Unexpected error: {}".format(traceback.format_exc()), file=sys.stderr)
    else:
        print("ERROR: Unsupported mode calling sn_sec_event_alert (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
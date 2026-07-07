from __future__ import print_function
import os
import os.path as op
import sys
import json
import gzip
import csv
import traceback
import sn_sec_util as snutil

def createAlertIncident(sessionKey, settings, resultLink, alertResult):
    datamap = {} 
    datamap["external_url"] = resultLink
    datamap["short_description"] = settings.get('shortdescription')
    datamap["cmdb_ci"] = settings.get('ci')
    datamap["category"] = settings.get('category')
    datamap["subcategory"] = settings.get('subcategory')
    datamap["assignment_group"] = settings.get('assignmentgroup')
    datamap["contact_type"] = settings.get('source')
    datamap["priority"] = settings.get('priority')
    datamap["description"] = settings.get('description')
    snutil.addCorrelationValues(datamap)
    
    for field in alertResult:
        datamap[field] = alertResult[field]

    snutil.createIncidentFromData(sessionKey, json.dumps(datamap))
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
                    if not createAlertIncident(sessionKey, configuration, resultsLink, result):
                        allSucceeded = False
                    else:
                        allFailed = False
            finally:
                csvResult.close()
            if allFailed:
                print("ERROR: No ServiceNow Security incidents created", file=sys.stderr)
                sys.exit(2)
            if not allSucceeded:
                print("ERROR: Some results failed to create a ServiceNow Security incident", file=sys.stderr)
                sys.exit(2)
        except Exception:
            print("ERROR: Unexpected error: {}".format(traceback.format_exc()), file=sys.stderr) 
    else:
        print("ERROR: Unsupported mode calling sn_sec_incident_alert (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
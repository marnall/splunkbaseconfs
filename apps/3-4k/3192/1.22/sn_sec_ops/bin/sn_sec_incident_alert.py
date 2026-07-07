import sys
import json
import traceback
import sn_sec_util as snutil

def createAlertIncident(sessionKey, settings, resultLink):
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
    snutil.createIncidentFromData(sessionKey, json.dumps(datamap))
    return True 

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:
            inputData = sys.stdin.read()
            payload = json.loads(inputData)
            if not createAlertIncident(payload["session_key"], payload["configuration"], payload["results_link"]):
                print >> sys.stderr, "ERROR: Unable to create ServiceNow Security incident"
                sys.exit(2)
        except Exception:
            print >> sys.stderr, "ERROR: Unexpected error: {}".format(traceback.format_exc()) 
    else:
        print >> sys.stderr, "ERROR: Unsupported mode calling sn_sec_incident_alert (expected --execute flag)"
        sys.exit(1)
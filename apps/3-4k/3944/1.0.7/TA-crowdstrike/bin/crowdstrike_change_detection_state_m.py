# Python imports
import sys
import json
import os
import base64


# Splunk imports
import splunk.rest
import splunk.Intersplunk

LIB_FOLDER_NAME = 'ta_crowdstrike'
folder_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(folder_path, LIB_FOLDER_NAME))

# Local imports
import crowdstrike_utils as csutils
from ta_crowdstrike import requests
import crowdstrike_consts as consts

logger = csutils.get_logger('cs_change_state_custom_command')


# Get results of the search
results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
# Obtain session key
sessionKey = settings.get("sessionKey")
# Obtain credentials for Query API
username, password = csutils.get_credentials(sessionKey)
# Obtain proxy configurations
proxies = csutils.get_proxy_info(sessionKey)

# Log error and exit if username or password is not available
if not username or not password:
    logger.error("CrowdStrike Error: Failed to obtain credentials required to execute the request")
    splunk.Intersplunk.parseError("Failed to obtain credentials required to execute the request")
    sys.exit(-1)

# REST endpoint to request to update the status of detection id
endpoint = consts.CHANGE_DETECTION_STATE

# Validate that required number of arguments are provided
if len(sys.argv) != 3:
    logger.error("CrowdStrike Error: Invalid number of arguments provided")
    splunk.Intersplunk.parseError("Invalid number of arguments provided")
    sys.exit(-1)


# Get detection id from arguments
detection_id_arg = sys.argv[1]
# Get detection status from arguments
detection_status_arg = sys.argv[2]


# Validate the provided arguments and return if validation fails
if "detection_id=" not in detection_id_arg or "detection_status=" not in detection_status_arg:
    logger.error("CrowdStrike Error: Invalid arguments provided")
    splunk.Intersplunk.parseError("Invalid arguments provided")
    sys.exit(-1)

detection_status = detection_status_arg.split("detection_status=")[1]
if detection_status not in ["new", "in_progress", "true_positive", "false_positive", "ignored"]:
    logger.error("CrowdStrike Error: Invalid value for detection status '%s'" % detection_status)
    splunk.Intersplunk.parseError("Invalid value for detection status '%s'" % detection_status)
    sys.exit(-1)

value_list = detection_id_arg.split("detection_id=")

ids_list = list()

try:
    # Iterate over each value in value_list
    for value in value_list:
        # If value is found
        if value:
            # Prepare list of detection ids by splitting the value by ','
            detection_ids_list = value.split(',')
            # Iterate over each IOC
            for detection_id in detection_ids_list:
                # Strip out any white spaces present in detection id
                detection_id = detection_id.strip()
                ids_list.append(detection_id)
            break
except Exception as e:
    logger.error("CrowdStrike Error: Error encountered while preparing request data '%s'" % str(e))
    splunk.Intersplunk.parseError("Error encountered while preparing request data. "
                                  "Please check $SPLUNK_HOME/var/log/crowdstrike/cs_change_state_custom_command.log"
                                  " for more information.")
    sys.exit(-1)

# If data to be posted is non empty
if detection_status and ids_list:
    # Prepare request data
    data = {"ids": ids_list, "status": detection_status}
    request_func = getattr(requests, "patch")
    # Encode username and password
    base64string = base64.b64encode('%s:%s' % (username, password))
    # Prepare request headers
    headers = {"Authorization": "Basic " + base64string, "Content-Type": "application/json"}
    try:
        # Make REST call
        rest_resp = request_func(consts.FALCON_URL + endpoint, headers=headers, data=json.dumps(data)
                                 , proxies=proxies)
        # Prepare output to be displayed
        output_result = [{"Detection IDs": json.dumps(ids_list), "Status": detection_status,
                          "Response": json.dumps(rest_resp.json())}]
        splunk.Intersplunk.outputResults(output_result)
    except Exception as e:
        logger.error("CrowdStrike Error: Error encountered while executing command '%s'" % str(e))
        splunk.Intersplunk.parseError("Error encountered while executing command. "
                                      "Please check $SPLUNK_HOME/var/log/crowdstrike/cs_change_state_custom_command.log"
                                      " for more information.")
        sys.exit(-1)

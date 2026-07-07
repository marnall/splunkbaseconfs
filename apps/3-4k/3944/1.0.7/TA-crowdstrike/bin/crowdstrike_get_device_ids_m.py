# Python imports
import sys
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

logger = csutils.get_logger('cs_get_device_id_custom_command')

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


# REST endpoint to get device ids corresponding to the IOC value provided
endpoint = consts.GET_DEVICE_IDS_ASSOCIATED_WITH_IOC

# Validate that required number of arguments are provided
if len(sys.argv) != 2:
    logger.error("CrowdStrike Error: Invalid number of arguments provided")
    splunk.Intersplunk.parseError("Invalid number of arguments provided")
    sys.exit(-1)


ioc_value_arg = sys.argv[1]


# Validate the provided argument
if "value=" not in ioc_value_arg:
    logger.error("CrowdStrike Error: Invalid argument provided '%s'" % ioc_value_arg)
    splunk.Intersplunk.parseError("Invalid argument provided '%s'" % ioc_value_arg)
    sys.exit(-1)

ioc_value = ioc_value_arg.split("value=")[1]

ioc_type = csutils.get_ioc_type_from_value(ioc_value)
# Throw an error and exit if not able to determine the IOC type
if not ioc_type:
    logger.error("CrowdStrike Error: Invalid value for IOC '%s'" % ioc_value)
    splunk.Intersplunk.parseError("Invalid value for IOC '%s'" % ioc_value)
    sys.exit(-1)

request_func = getattr(requests, "get")
# Encode username and password
base64string = base64.b64encode('%s:%s' % (username, password))
# Prepare request headers
headers = {"Authorization": "Basic " + base64string, "Content-Type": "application/json"}
# Prepare request params
params = {"value": ioc_value, "type": ioc_type}

output_result_list = list()
try:
    # Make REST call
    rest_resp = request_func(consts.FALCON_URL + endpoint, headers=headers, params=params,
                             proxies=proxies)
    # Log error and exit if the response status code is not equal to 200
    if rest_resp.status_code != 200:
            logger.error("CrowdStrike Error: Error encountered while getting device list: '%s'"
                         % str(rest_resp.json()))
            splunk.Intersplunk.parseError("CrowdStrike Error: Error encountered while getting device list,"
                                          " status code: '%s'"% str(rest_resp.status_code))
            sys.exit(-1)
    # Prepare output to be displayed
    resources = rest_resp.json().get("resources")
    if resources:
        for resource in resources:
            output_result_list.append({"device_id": resource["device_id"]})
    splunk.Intersplunk.outputResults(output_result_list)
except Exception as e:
    logger.error("CrowdStrike Error: Error encountered while executing command '%s'" % str(e))
    splunk.Intersplunk.parseError("Error encountered while executing command."
                                  " Please check $SPLUNK_HOME/var/log/crowdstrike/cs_get_device_id_custom_command.log"
                                  " for more information.")
    sys.exit(-1)

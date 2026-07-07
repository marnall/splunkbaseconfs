# Python imports
import sys
import os
import base64
import re

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

# Get logger
logger = csutils.get_logger('cs_get_device_info_custom_command')
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

# Validate that required number of arguments are provided
if len(sys.argv) != 2:
    logger.error("CrowdStrike Error: Invalid number of arguments provided")
    splunk.Intersplunk.parseError("Invalid number of arguments provided")
    sys.exit(-1)

# Fetch the first argument ideally value=<hostname> or value=<device_id>
value_arg = sys.argv[1]
# Validate the provided argument
if "value=" not in value_arg:
    logger.error("CrowdStrike Error: Invalid argument provided '%s'" % value_arg)
    splunk.Intersplunk.parseError("Invalid argument provided '%s'" % value_arg)
    sys.exit(-1)

# Fetch the actual value from the argument
actual_value = value_arg.split("value=")[1]
# Log error and exit if actual value is null
if not actual_value:
    logger.error("CrowdStrike Error: Please provide a value for which device information needs to be fetched.")
    splunk.Intersplunk.parseError("Please provide a value for which device information needs to be fetched.")
    sys.exit(-1)

request_func = getattr(requests, "get")
# Encode username and password
base64string = base64.b64encode('%s:%s' % (username, password))
# Prepare request headers
headers = {"Authorization": "Basic " + base64string, "Content-Type": "application/json"}
# Prepare request params
params = {"ids": actual_value}
# Regex to match device_id
regex = '^[0-9a-fA-F]{32}$'
# Match regex with actual_value to validate if it is device_id or not
m = re.match(regex, actual_value)

if m is None:
    # Value would be considered as hostname, in that case we would need an additional call to fetch device_ids list
    # Prepare REST endpoint to get device ids corresponding to the value provided
    filter_endpoint = consts.GET_DEVICE_IDS_USING_FILTER + "?filter=hostname:'" + actual_value + "'"
    try:
        # Make REST call
        device_id_resp = request_func(consts.FALCON_URL + filter_endpoint, headers=headers, proxies=proxies)
        # Log error and exit if the response status code is not equal to 200
        if device_id_resp.status_code != 200:
            logger.error("CrowdStrike Error: Error encountered while searching device: '%s'"
                         % str(device_id_resp.json()))
            splunk.Intersplunk.parseError("CrowdStrike Error: Error encountered while searching device,"
                                          " status code: '%s'" % str(device_id_resp.status_code))
            sys.exit(-1)
        # Get list of device_ids matching the actual_value
        device_ids = device_id_resp.json().get("resources")
    # Log error and exit in case of any exception
    except Exception as e:
        logger.error("CrowdStrike Error: Error encountered while executing command '%s'" % str(e))
        splunk.Intersplunk.parseError("Error encountered while executing command."
                                      " Please check $SPLUNK_HOME/var/log/crowdstrike/cs_get_device_info_custom_command.log"
                                      " for more information.")
        sys.exit(-1)

    # Override params with None
    params = None
    if device_ids:
        # Prepare request params containing list of all device_ids as value
        params = {"ids": device_ids}

output_result_list = list()
try:
    # Make REST call
    if not (m is None and params is None):
        rest_resp = request_func(consts.FALCON_URL + consts.DEVICE_ENTITY_ENDPOINT, headers=headers, params=params,
                                 proxies=proxies)
        # Log error and exit if the response status code is not equal to 200
        if rest_resp.status_code != 200:
                logger.error("CrowdStrike Error: Error encountered while getting device details: '%s'"
                             % str(rest_resp.json()))
                splunk.Intersplunk.parseError("CrowdStrike Error: Error encountered while getting device details,"
                                              " status code: '%s'"% str(rest_resp.status_code))
                sys.exit(-1)
        # Prepare output to be displayed
        resources = rest_resp.json().get("resources")
        if resources:
            for resource in resources:
                # Convert list object within resource to string so as to avoid errors while displaying output in Splunk
                resource["policies"] = str(resource.get("policies", ""))
                output_result_list.append(resource)
        # Output results
        splunk.Intersplunk.outputResults(output_result_list)
# Log error and exit in case of any exception
except Exception as e:
    logger.error("CrowdStrike Error: Error encountered while executing command '%s'" % str(e))
    splunk.Intersplunk.parseError("Error encountered while executing command."
                                  " Please check $SPLUNK_HOME/var/log/crowdstrike/cs_get_device_info_custom_command.log"
                                  " for more information.")
    sys.exit(-1)

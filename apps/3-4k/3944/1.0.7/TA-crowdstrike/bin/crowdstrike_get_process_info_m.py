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

logger = csutils.get_logger('cs_get_process_info_custom_command')

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


# REST endpoint to search IOC
search_endpoint = consts.GET_DEVICE_IDS_ASSOCIATED_WITH_IOC


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
output_results_list = list()
try:
    # Make REST call
    rest_resp = request_func(consts.FALCON_URL + search_endpoint, headers=headers,
                             params={"type": ioc_type, "value": ioc_value}, proxies=proxies)

    if rest_resp.status_code != 200:
        logger.error("CrowdStrike Error: Error encountered while searching indicator, status code: '%s'"
                     % str(rest_resp.status_code))
        splunk.Intersplunk.parseError("CrowdStrike Error: Error encountered while executing command, status code: '%s'"
                                      % str(rest_resp.status_code))
        sys.exit(-1)

    # Get list of devices associated with the indicator
    devices = rest_resp.json().get("resources", [])
    # Iterate over each device
    for device in devices:
        # Obtain URL from path key of each resource
        ioc_and_device_info = device["path"]
        # Make REST call to that URL to obtain detailed information corresponding to the provided IOC on that device
        ioc_and_device_info_resp = request_func(ioc_and_device_info, headers=headers, proxies=proxies)
        # Continue the loop if HTTP status code is other than 200
        if ioc_and_device_info_resp.status_code != 200:
            continue
        # Obtain resources from the ioc_and_device_info_resp
        device_resp_json = ioc_and_device_info_resp.json()
        resources = device_resp_json.get("resources", [])
        # Iterate over each resource
        for resource in resources:
            # Get edges dictionary for each resource
            edges = resource.get("edges", {})
            # Iterate over each edge_type in edges (ex. dns)
            for edge_type in edges:
                edge_type_info = edges[edge_type]
                # Try to find out the URLs from path key which holds the process information
                for info in edge_type_info:
                    if "/combined/processes" in info["path"]:
                        # Make REST call to obtain process information
                        process_info = request_func(info["path"], headers=headers, proxies=proxies)
                        if process_info.status_code == 200:
                            # Parse response and append the required data to output_results_list
                            process_resources = process_info.json().get("resources", [])
                            for process_resource in process_resources:
                                process_resource["properties"]["DeviceID"] = process_resource["device_id"]
                                output_results_list.append(process_resource["properties"])

    if output_results_list:
        # Display results
        splunk.Intersplunk.outputResults(output_results_list)

except Exception as e:
    logger.error("CrowdStrike Error: Error encountered while executing command '%s'" % str(e))
    splunk.Intersplunk.parseError("Error encountered while executing command."
                                  " Please check"
                                  " $SPLUNK_HOME/var/log/crowdstrike/cs_get_process_info_custom_command.log"
                                  " for more information.")
    sys.exit(-1)

# Python imports
import sys
import json
import os
import base64
from xml.dom.minidom import parseString

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

logger = csutils.get_logger('cs_upload_ioc_custom_command')

# Get results of the search
results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
# Obtain session key
sessionKey = settings.get("sessionKey")
# Obtain Splunk username
auth_string = settings.get("authString")
parsed_xml_content = parseString(auth_string)
splunk_username_tag = parsed_xml_content.getElementsByTagName("username")[0]
splunk_username = str(splunk_username_tag.firstChild.data)
# Obtain credentials for Query API
username, password = csutils.get_credentials(sessionKey)
# Obtain proxy configurations
proxies = csutils.get_proxy_info(sessionKey)

# Log error and exit if username or password is not available
if not username or not password:
    logger.error("CrowdStrike Error: Failed to obtain credentials required to execute the request")
    splunk.Intersplunk.parseError("Failed to obtain credentials required to execute the request")
    sys.exit(-1)


# REST endpoint to upload IOC
endpoint = consts.UPLOAD_IOC

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

value_list = ioc_value_arg.split("value=")

ioc_list = None
# Prepare request data
data = list()
# List of IOC types uploaded
ioc_type_list = list()

try:
    # Iterate over each value in value_list
    for value in value_list:
        # If value is found
        if value:
            # Prepare list of IOCs by splitting the value by ','
            ioc_list = value.split(',')
            # Iterate over each IOC
            for ioc in ioc_list:
                # Strip out any white spaces present in IOC value
                ioc_value = ioc.strip()
                # Obtain IOC type
                ioc_type = csutils.get_ioc_type_from_value(ioc_value)
                # Throw an error and exit if not able to determine the IOC type
                if not ioc_type:
                    logger.error("CrowdStrike Error: Invalid value for IOC '%s'" % ioc_value)
                    splunk.Intersplunk.parseError("Invalid value for IOC '%s'" % ioc_value)
                    sys.exit(-1)
                ioc_type_list.append(ioc_type)
                data.append({"type": ioc_type, "value": ioc_value, "policy": "detect", "share_level": "red",
                             "source": "Splunk", "description": "IOC Uploaded from Splunk by user " + splunk_username + ".",
                             "expiration_days": 30})
            break

except Exception as e:
    logger.error("CrowdStrike Error: Error encountered while preparing request data '%s'" % str(e))
    splunk.Intersplunk.parseError("Error encountered while preparing request data."
                                  " Please check $SPLUNK_HOME/var/log/crowdstrike/cs_upload_ioc_custom_command.log"
                                  " for more information.")
    sys.exit(-1)

# If data to be posted is non empty
if data:
    request_func = getattr(requests, "post")
    # Encode username and password
    base64string = base64.b64encode('%s:%s' % (username, password))
    # Prepare request headers
    headers = {"Authorization": "Basic " + base64string, "Content-Type": "application/json"}
    try:
        # Make REST call
        rest_resp = request_func(consts.FALCON_URL + endpoint, headers=headers,
                                 data=json.dumps(data), proxies=proxies)
        # Prepare output to be displayed
        output_result = [{"IOC Value": json.dumps(ioc_list), "IOC Type": json.dumps(ioc_type_list),
                          "Response": json.dumps(rest_resp.json())}]
        splunk.Intersplunk.outputResults(output_result)
    except Exception as e:
        logger.error("CrowdStrike Error: Error encountered while executing command '%s'" % str(e))
        splunk.Intersplunk.parseError("Error encountered while executing command."
                                      " Please check $SPLUNK_HOME/var/log/crowdstrike/cs_upload_ioc_custom_command.log"
                                      " for more information.")
        sys.exit(-1)

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

logger = csutils.get_logger('cs_upload_ioc_stream_custom_command')

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


# REST endpoint to upload IOC
endpoint = consts.UPLOAD_IOC

# Total IOCs to be uploaded
total_uploads_initiated = len(results)
# Total failed uploads (initially 0)
failed_uploads = 0
# List containing iocs that failed to upload along with error code and error message
error_list = list()
# Query results
results_list = list()

# Iterate over query results
for result in results:
    # Convert each result into dict object
    result = dict(result)
    # If "indicator_source" key is found assign its value to "source" key and delete "indicator_source" key
    try:
        result["share_level"] = "red"
        result["policy"] = "detect"
        result["source"] = result["indicator_source"]
        del result["indicator_source"]
    except:
        pass
    # If expiration_days key is found convert into integer, if any error is encountered assign default value 30
    try:
        result["expiration_days"] = int(result["expiration_days"])
    except:
        result["expiration_days"] = 30

    results_list.append(result)

# Split iocs to be uploaded into chunks of 200 each
chunks = [results_list[x:x+200] for x in xrange(0, len(results_list), 200)]

# Iterate over each chunk and upload it
for chunk in chunks:
    request_func = getattr(requests, "post")
    # Encode username and password
    base64string = base64.b64encode('%s:%s' % (username, password))
    # Prepare request headers
    headers = {"Authorization": "Basic " + base64string, "Content-Type": "application/json"}
    try:
        # Make REST call
        rest_resp = request_func(consts.FALCON_URL + endpoint, headers=headers,
                                 data=json.dumps(chunk), proxies=proxies)
        if rest_resp.status_code != 200:
            logger.error("CrowdStrike Error: IOC upload failed '%s'" % str(rest_resp.json()))
            splunk.Intersplunk.parseError("IOC upload failed '%s'" % str(rest_resp.status_code))
            sys.exit(-1)

        errors = rest_resp.json()["errors"]
        if errors:
            # Increment failed uploads count if any error are encountered
            failed_uploads += len(errors)
            # Append errors to error_list
            error_list += errors
    except Exception as e:
        logger.error("CrowdStrike Error: Error encountered while executing command '%s'" % str(e))
        splunk.Intersplunk.parseError("Error encountered while executing command."
                                      " Please check $SPLUNK_HOME/var/log/crowdstrike/cs_upload_ioc_stream_custom_command.log"
                                      " for more information.")
        sys.exit(-1)

# Dump error list into log file for debugging purpose
if error_list:
    logger.error("CrowdStrike Error: Failed to upload some IOCs '%s'" % str(error_list))

# Prepare output to be displayed
output_results = [{"Total Initiated Uploads": total_uploads_initiated, "Total Failed Uploads": failed_uploads}]
splunk.Intersplunk.outputResults(output_results)
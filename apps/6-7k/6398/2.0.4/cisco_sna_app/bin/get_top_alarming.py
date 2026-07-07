# ==========================================================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# get_top_ports.py script for use with Splunk enterprise to fetch top peers
# from StealthWatch using the RESTx appliance REST API extension service
# ==========================================================================================================

# |topalarming [report_type=<hosts|users>] [host_group_id=<host_group_id>] [domain_id=<domain_id>] [smc_ip=<smc_ip>]

############################################################################################################
# Get some libraries we will need
############################################################################################################

import splunk_utility
import traceback
import splunk
import splunk.Intersplunk

import stealthwatch_api_client


############################################################################################################
# process each row in the alarm report.
############################################################################################################
def process_row(row, host_group_dict):
    this_row = {}
    # import json
    # this_row["raw_row"] = str(json.dumps(row))
    if "hostGroups" in row and row["hostGroups"] is not None and len(row["hostGroups"]) > 0:
        this_row["host_group_ids"] = ""
        this_row["host_group_names"] = ""
        for this_host_group in row["hostGroups"]:
            this_row["host_group_ids"] += ", " + str(this_host_group["id"])
            if int(this_host_group["id"]) in host_group_dict:
                this_row["host_group_names"] += "; " + str(host_group_dict[int(this_host_group["id"])])
            else:
                this_row["host_group_names"] += "; [Unknown Host Group ID: " + str(this_host_group["id"]) + "]"
        this_row["host_group_names"] = this_row["host_group_names"][2:]
        this_row["host_group_ids"] = this_row["host_group_ids"][2:]
    if "securityCategories" in row and row["securityCategories"] is not None:
        for security_index, values in list(row["securityCategories"].items()):
            this_row[security_index] = values["percentOfThreshold"]
    if "badness" in row:
        this_row["badness"] = row["badness"]
    if "hostName" in row:
        this_row["hostname"] = row["hostName"]
    if "ipAddress" in row:
        this_row["ip_address"] = row["ipAddress"]
    if "timeLastSeen" in row:
        this_row["time_last_seen"] = row["timeLastSeen"]
    if "activeDeviceCount" in row:
        this_row["active_device_count"] = row["activeDeviceCount"]
    if "activeSessionCount" in row:
        this_row["active_session_count"] = row["activeSessionCount"]
    if "deviceCount" in row:
        this_row["device_count"] = row["deviceCount"]
    if "lastSessionEnd" in row:
        this_row["time_session_end"] = row["lastSessionEnd"]
    if "lastSessionStart" in row:
        this_row["time_session_start"] = row["lastSessionStart"]
    if "sessionCount" in row:
        this_row["session_count"] = row["sessionCount"]
        if "activeSessionCount" in row:
            this_row["session_count_str"] = str(row["activeSessionCount"]) + " / " + str(row["sessionCount"])
    if "userName" in row:
        this_row["username"] = row["userName"]
    return this_row


def main():
    ############################################################################################################
    # Set up logging
    ############################################################################################################
    logger = splunk_utility.setup_logging(splunk_utility.myapp)
    logger.info("")
    logger.info("API process started...")


    ############################################################################################################
    # Process the arguments
    ############################################################################################################
    args, kwargs = splunk_utility.parse_args()
    report_type = kwargs.get('report_type')
    domain_id = kwargs.get('domain_id')
    host_group_id = kwargs.get('host_group_id')
    smc_ip = kwargs.get('smc_ip')

    if host_group_id is None or len(str(host_group_id)) <= 0 or str(host_group_id) == "all" or int(host_group_id) <= -1:
        host_group_id = None

    if report_type is None or len(str(report_type)) <= 0:
        report_type = "hosts"
    report_type = str(report_type).lower().strip()

    ############################################################################################################
    # Read and parse config file for additional parameters required.
    ############################################################################################################
    logger.info("Getting config...")
    config = splunk_utility.get_config(logger)
    logger.info("Done getting config.")

    if smc_ip is None or len(smc_ip) <= 0:
        smc_ip = config["smcIP"].replace("%2C", ",").split(",")[0].strip()

    if domain_id is None or len(domain_id) == 0:
        domain_id = config["smcDomainID"]

    ############################################################################################################
    # Storage for the results
    ############################################################################################################
    results = []
    host_group_dict = {}

    try:

        ############################################################################################################
        # LOGIN to RESTx API Extension appliance
        ############################################################################################################
        logger.info("Authenticating API connection...")
        api = stealthwatch_api_client.stealthwatch_api()
        api.login(smc_ip, config["smcID"], config["smcPW"], requests_disable_warnings=False)
        api.set_domain_id(int(domain_id))
        logger.info("Done authenticating API connection.")

        ############################################################################################################
        # FETCH the necessary data_all by issuing a REST request to the RESTx
        ############################################################################################################
        if report_type == "hosts":
            logger.info("Executing \"get_top_alarming_hosts\" API call...")
            data = api.get_top_alarming_hosts(host_group_id=host_group_id)
            logger.info("Done executing \"get_top_alarming_hosts\" API call.")
        elif report_type == "users":
            logger.info("Executing \"get_top_alarming_users\" API call...")
            data = api.get_top_alarming_users(host_group_id=host_group_id)
            logger.info("Done executing \"get_top_alarming_users\" API call.")

        ############################################################################################################
        # Get Host Group Data for Mapping
        ############################################################################################################
        if data is not None and len(data) > 0 and report_type == "hosts":
            sw_version = api.get_version_info()
            if sw_version[0] < 6 or (sw_version[0] == 6 and sw_version[1] < 10):
                host_group_dict = {1: 'Inside Hosts', 0: 'Outside Hosts'}
                raw_host_groups = api.get_host_groups()
                host_group_dict = splunk_utility.process_host_group_dict(host_group_dict, 'Inside Hosts',
                                                                        raw_host_groups['inside-hosts']['host-group'])
                host_group_dict = splunk_utility.process_host_group_dict(host_group_dict, 'Outside Hosts',
                                                                        raw_host_groups['outside-hosts']['host-group'])
            else:
                internal_host_group_tree = api.get_internal_hosts_tree()
                if internal_host_group_tree is not None:
                    host_group_dict = splunk_utility.traverse_host_groups(internal_host_group_tree, "", host_group_dict)

                external_host_group_tree = api.get_external_hosts_tree()
                if external_host_group_tree is not None:
                    host_group_dict = splunk_utility.traverse_host_groups(external_host_group_tree, "", host_group_dict)

                external_geo_tree = api.get_external_geo_tree()
                if external_geo_tree is not None:
                    host_group_dict = splunk_utility.traverse_host_groups(external_geo_tree, "", host_group_dict)

        ############################################################################################################
        # LOGOUT the session
        ############################################################################################################
        logger.info("De-authenticating API connection...")
        api.logout()
        logger.info("Done de-authenticating API connection.")

        if data is not None and "results" in data and len(data["results"]) > 0:
            for row in data["results"]:
                this_row = process_row(row, host_group_dict)
                results.append(this_row)

    except:

        ############################################################################################################
        # Bad things happened. Get backtrace and pump to splunk
        ############################################################################################################
        stack = traceback.format_exc()
        logger.error("Error : Traceback: " + str(stack))
        logger.error("Aborting API process.")
        results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

    ############################################################################################################
    # Pump the results to splunk
    ############################################################################################################
    logger.info("Printing API results...")
    splunk.Intersplunk.outputResults(results)
    logger.info("Done printing API results.")
    logger.info("Done with API Process.")


if __name__ == "__main__":
    main()

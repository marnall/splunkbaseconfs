# ==========================================================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# get_top_ports.py script for use with Splunk enterprise to fetch top peers
# from StealthWatch using the RESTx appliance REST API extension service
# ==========================================================================================================

# |usersessions username=<username> [domain_id=<domain_id>] [smc_ip=<smc_ip>]

############################################################################################################
# Get some libraries we will need
############################################################################################################

import splunk_utility
import traceback
import splunk
import splunk.Intersplunk

import stealthwatch_api_client


############################################################################################################
# process each row in the top report.
############################################################################################################
def process_row(row, host_group_dict):
    this_row = {}
    if "lastActiveSessionIp" in row:
        this_row["last_active_session_ip"] = row["lastActiveSessionIp"]
    if "deviceType" in row:
        this_row["device_type"] = row["deviceType"]
    if "macAddress" in row:
        this_row["mac_address"] = row["macAddress"]
    if "hostName" in row:
        this_row["hostname"] = row["hostName"]
    if "vendor" in row:
        this_row["vendor"] = row["vendor"]
    if "lastActiveTime" in row:
        this_row["last_active_time"] = row["lastActiveTime"]
    if "badness" in row:
        this_row["badness"] = row["badness"]
    if "startTime" in row:
        this_row["start_time"] = row["startTime"]
    if "endTime" in row:
        this_row["end_time"] = row["endTime"]
    if "sessionCount" in row:
        this_row["session_count"] = row["sessionCount"]
    if "ipAddress" in row:
        this_row["ip_address"] = row["ipAddress"]
    if "hostGroups" in row and len(row["hostGroups"]) > 0:
        host_group_id_string = ""
        host_group_name_string = ""
        for this_group in row["hostGroups"]:
            host_group_id_string += str(this_group["id"]) + ","
        host_group_id_string = host_group_id_string[:-1]
        for host_group_id in host_group_id_string.split(","):
            if int(host_group_id) in host_group_dict:
                host_group_name_string += str(host_group_dict[int(host_group_id)]) + "; "
            else:
                host_group_name_string += "[Unknown Host Group ID: " + str(host_group_id) + "]; "
        host_group_id_string = host_group_id_string.replace(",", ", ")
        host_group_name_string = host_group_name_string[:-2]
        this_row["host_group_ids"] = host_group_id_string
        this_row["host_group_names"] = host_group_name_string

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
    domain_id = kwargs.get('domain_id')
    smc_ip = kwargs.get('smc_ip')
    username = kwargs.get('username')

    if not username:
        logger.error("Missing required arguments")
        logger.error("Aborting RESTx API process")
        # Following line calls sys.exit()
        splunk.Intersplunk.parseError("Missing required arguments! (Usage: |usersessions username=<username> [domain_id=<domain_id>] [smc_ip=<smc_ip>]")

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
        logger.info("Executing \"get_device_sessions_by_username\" API call...")
        data = api.get_device_sessions_by_username(username=username)
        logger.info("Done executing \"get_device_sessions_by_username\" API call.")

        ############################################################################################################
        # Get Host Group Data for Mapping
        ############################################################################################################
        if data is not None and len(data) > 0:
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
        else:
            # Catch the case when the ISE/AD integration is not configured
            logger.error("No User Device Session Data found.")
            # Following line calls sys.exit()
            splunk.Intersplunk.parseError("No User Device Session Data found, domain_id={} "
                                          "username={}".format(domain_id, username))

        ############################################################################################################
        # LOGOUT the session
        ############################################################################################################
        logger.info("De-authenticating API connection...")
        api.logout()
        logger.info("Done de-authenticating API connection.")

        if data is not None:
            if "devices" in data and len(data["devices"]) > 0:
                for device in data["devices"]:
                    if "hosts" in device and len(device["hosts"]) > 0:
                        for row in device["hosts"]:
                            if "deviceType" in device:
                                row["deviceType"] = device["deviceType"]
                            if "macAddress" in device:
                                row["macAddress"] = device["macAddress"]
                            if "vendor" in device:
                                row["vendor"] = device["vendor"]
                            if "lastActiveSessionIp" in data:
                                row["lastActiveSessionIp"] = data["lastActiveSessionIp"]
                            this_row = process_row(row, host_group_dict)
                            results.append(this_row)
            if "unknownSessions" in data and len(data["unknownSessions"]) > 0:
                for row in data["unknownSessions"]:
                    if "lastActiveSessionIp" in data:
                        row["lastActiveSessionIp"] = data["lastActiveSessionIp"]
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

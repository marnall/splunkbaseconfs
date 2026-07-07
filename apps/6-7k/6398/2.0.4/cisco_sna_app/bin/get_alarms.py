# ==========================================================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# get_top_ports.py script for use with Splunk enterprise to fetch top peers
# from StealthWatch using the RESTx appliance REST API extension service
# ==========================================================================================================

# Usage: |alarms earliest=<earliest> latest=<latest> [alarm_status=<alarm_status>] [ip_address=<ip_address>] [alarm_category_id=<alarm_category_id>] [domain_id=<domain_id>] [smc_ip=<smc_ip>]

############################################################################################################
# Get some libraries we will need
############################################################################################################

import datetime
import splunk_utility
import traceback
import splunk
import splunk.Intersplunk

import stealthwatch_api_client


############################################################################################################
# process each row in the alarm report.
############################################################################################################
def process_row(row, host_group_dict, fc_map):
    this_row = {}
    if "deviceId" in row and row["deviceId"] is not None:
        this_row["fc_id"] = row["deviceId"]
        if int(row["deviceId"]) in fc_map:
            this_row["fc_name"] = fc_map[int(row["deviceId"])]
    if "source" in row and row["source"] is not None:
        if "ipAddress" in row["source"]:
            if row["source"]["ipAddress"] == "0.0.0.0":
                this_row["source_ip"] = "Multiple Hosts"
            elif "ipRange" in row["source"]:
                this_row["source_ip"] = row["source"]["ipRange"]
            else:
                this_row["source_ip"] = row["source"]["ipAddress"]
        if "hostGroupIds" in row["source"]:
            if row["source"]["ipAddress"] != "0.0.0.0":
                this_row["source_host_group_ids"] = str(row["source"]["hostGroupIds"])
                this_row["source_host_group_names"] = ""
                for host_group_id in row["source"]["hostGroupIds"]:
                    if int(host_group_id) in host_group_dict:
                        this_row["source_host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                    else:
                        this_row["source_host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                this_row["source_host_group_names"] = this_row["source_host_group_names"][2:]
        if "name" in row["source"]:
            this_row["source_hostname"] = row["source"]["name"]
        if "macAddress" in row["source"]:
            this_row["source_mac"] = row["source"]["macAddress"]
    if "target" in row and row["target"] is not None:
        if "ipAddress" in row["target"]:
            if row["target"]["ipAddress"] == "0.0.0.0":
                this_row["target_ip"] = "Multiple Hosts"
            elif "ipRange" in row["target"]:
                this_row["target_ip"] = row["target"]["ipRange"]
            else:
                this_row["target_ip"] = row["target"]["ipAddress"]
        if "hostGroupIds" in row["target"]:
                this_row["target_host_group_ids"] = str(row["target"]["hostGroupIds"])
                this_row["target_host_group_names"] = ""
                for host_group_id in row["target"]["hostGroupIds"]:
                    if int(host_group_id) in host_group_dict:
                        this_row["target_host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                    else:
                        this_row["target_host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                this_row["target_host_group_names"] = this_row["target_host_group_names"][2:]
        if "name" in row["target"]:
            this_row["target_hostname"] = row["target"]["name"]
        if "macAddress" in row["target"]:
            this_row["target_mac"] = row["target"]["macAddress"]
    if "policyDisplay" in row and row["policyDisplay"] is not None:
        if "description" in row["policyDisplay"]:
            this_row["policy_description"] = row["policyDisplay"]["description"]
        if "policyId" in row["policyDisplay"]:
            this_row["policy_id"] = row["policyDisplay"]["policyId"]
        if "policyName" in row["policyDisplay"]:
            this_row["policy_name"] = row["policyDisplay"]["policyName"]
        if "policyType" in row["policyDisplay"]:
            this_row["policy_type"] = row["policyDisplay"]["policyType"]
    if "type" in row and row["type"] is not None:
        if isinstance(row["type"], str) or isinstance(row["type"], str):
            if "alarmClass" in row:
                this_row["alarm_class"] = row["alarmClass"]
            if "alarmClassId" in row:
                this_row["alarm_class_id"] = row["alarmClassId"]
            if "defaultSeverity" in row:
                this_row["alarm_default_severity"] = row["defaultSeverity"]
            if "type" in row:
                this_row["alarm_name"] = row["type"]
            if "typeId" in row:
                this_row["alarm_type_id"] = row["typeId"]
        else:
            if "alarmClass" in row["type"]:
                this_row["alarm_class"] = row["type"]["alarmClass"]
            if "alarmClassId" in row["type"]:
                this_row["alarm_class_id"] = row["type"]["alarmClassId"]
            if "defaultSeverity" in row["type"]:
                this_row["alarm_default_severity"] = row["type"]["defaultSeverity"]
            if "displayName" in row["type"]:
                this_row["alarm_name"] = row["type"]["displayName"]
            if "id" in row["type"]:
                this_row["alarm_type_id"] = row["type"]["id"]
            if "key" in row["type"]:
                this_row["alarm_type_name"] = row["type"]["key"]
            if "toolTip" in row["type"]:
                this_row["alrm_type_description"] = row["type"]["toolTip"]
    if "acked" in row:
        this_row["acked"] = row["acked"]
    if "ackedTime" in row and int(row["ackedTime"]) > 0:
        this_row["acked_time"] = datetime.datetime.utcfromtimestamp(int(str(row["ackedTime"])[:-3])).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "active" in row:
        this_row["active"] = row["active"]
        if str(this_row["active"]).lower() == "true":
            this_row["status"] = "Active"
        else:
            this_row["status"] = "Inactive"
    if "baseline" in row:
        this_row["baseline"] = row["baseline"]
    if "clearedTime" in row and int(row["clearedTime"]) > 0:
        this_row["cleared_time"] = datetime.datetime.utcfromtimestamp(int(str(row["clearedTime"])[:-3])).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "closed" in row:
        this_row["closed"] = row["closed"]
    if "closedTime" in row and int(row["closedTime"]) > 0:
        this_row["closed_time"] = datetime.datetime.utcfromtimestamp(int(str(row["closedTime"])[:-3])).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "currentValue" in row:
        this_row["current_value"] = row["currentValue"]
    if "detailsString" in row:
        this_row["details"] = row["detailsString"]
    elif "detail" in row:
        this_row["details"] = row["detail"]
    if "formattedBaseline" in row:
        this_row["formatted_baseline"] = row["formattedBaseline"]
    if "formattedCurrentValue" in row:
        this_row["formatted_current_value"] = row["formattedCurrentValue"]
    if "formattedThreshold" in row:
        this_row["formatted_threshold"] = row["formattedThreshold"]
    if "id" in row:
        this_row["id"] = row["id"]
    if "idString" in row:
        this_row["id_string"] = row["idString"]
    if "lastActiveTime" in row and int(row["lastActiveTime"]) > 0:
        this_row["last_active_time"] = datetime.datetime.utcfromtimestamp(int(str(row["lastActiveTime"])[:-3])).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "mostRecentActiveTime" in row and int(row["mostRecentActiveTime"]) > 0:
        this_row["most_recent_active_time"] = datetime.datetime.utcfromtimestamp(int(str(row["mostRecentActiveTime"])[:-3])).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "scaledBaseline" in row:
        this_row["scaled_baseline"] = row["scaledBaseline"]
    if "scaledCurrentValue" in row:
        this_row["scaled_current_value"] = row["scaledCurrentValue"]
    if "scaledThreshold" in row:
        this_row["scaled_threshold"] = row["scaledThreshold"]
    if "startActiveTime" in row and int(row["startActiveTime"]) > 0:
        this_row["start_active_time"] = datetime.datetime.utcfromtimestamp(int(str(row["startActiveTime"])[:-3])).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "threshold" in row:
        this_row["threshold"] = row["threshold"]
    if "sourceUsername" in row:
        this_row["source_username"] = row["sourceUsername"]
    if "targetUsername" in row:
        this_row["target_username"] = row["targetUsername"]
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
    earliest = kwargs.get('earliest')
    latest = kwargs.get('latest')
    alarm_status = kwargs.get('alarm_status')
    ip_address = kwargs.get('ip_address')
    alarm_category_id = kwargs.get('alarm_category_id')
    domain_id = kwargs.get('domain_id')
    smc_ip = kwargs.get('smc_ip')

    if earliest is None or latest is None:
        logger.error("Missing required arguments")
        logger.error("Aborting RESTx API process")
        # Following line calls sys.exit()
        splunk.Intersplunk.parseError("Missing required arguments! (Usage: |alarms earliest=<earliest> latest=<latest> [alarm_status=<alarm_status>] [ip_address=<ip_address>] [alarm_category_id=<alarm_category_id>] [domain_id=<domain_id>] [smc_ip=<smc_ip>])")

    if ip_address is None or len(ip_address) <= 0:
        ip_address = None
    is_active = None
    if alarm_status is None or len(alarm_status) <= 0:
        is_active = None
    elif alarm_status == "active":
        is_active = True
    elif alarm_status == "inactive":
        is_active = False
    if alarm_category_id is None or len(str(alarm_category_id)) <= 0 or (str(alarm_category_id) != "%" and int(alarm_category_id) <= 0):
        alarm_category_id = "%"  # Default to all/None depending on version

    start_datetime = None
    end_datetime = None
    datetimes = splunk_utility.get_timerange(earliest=earliest, latest=latest, logger=logger)
    if "start_datetime" in list(datetimes.keys()) and datetimes["start_datetime"] is not None:
        start_datetime = datetimes["start_datetime"]
    if "end_datetime" in list(datetimes.keys()) and datetimes["end_datetime"] is not None:
        end_datetime = datetimes["end_datetime"]

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
    data = []
    host_group_dict = {}
    fc_map = {}

    try:

        ############################################################################################################
        # LOGIN to RESTx API Extension appliance
        ############################################################################################################
        logger.info("Authenticating API connection...")
        api = stealthwatch_api_client.stealthwatch_api()
        # logger.info("Setting DEBUG to True...")
        # api.DEBUG = True
        api.login(smc_ip, config["smcID"], config["smcPW"], requests_disable_warnings=False)
        api.set_domain_id(int(domain_id))
        logger.info("Done authenticating API connection.")

        ############################################################################################################
        # FETCH the necessary data by issuing a REST request to the RESTx
        ############################################################################################################
        logger.info("Executing \"get_alarms\" API call...")
        if str(alarm_category_id) == "%" and api.get_version_info()[0] >= 7:
            alarm_category_id = "all"
        elif str(alarm_category_id) == "%":
            alarm_category_id = None
        if str(alarm_category_id) == "all":
            data = None
            alarm_list = api.get_daily_alarm_types(ip_address=ip_address, number_of_days_back=7)
            for alarm_type in alarm_list["series"]:
                data_tmp = api.get_alarms(start_datetime=start_datetime, end_datetime=end_datetime, is_active=is_active,
                                          alarm_category_id=alarm_type["id"], ip_address=ip_address)
                if data is None:
                    data = data_tmp
                else:
                    data["results"] += data_tmp["results"]
        else:
            data = api.get_alarms(start_datetime=start_datetime, end_datetime=end_datetime, is_active=is_active, alarm_category_id=alarm_category_id, ip_address=ip_address)
        logger.info("Done executing \"get_alarms\" API call.")

        ############################################################################################################
        # Get Host Group Data for Mapping
        ############################################################################################################
        if data is not None and len(data) > 0:
            sw_version = api.get_version_info()
            if sw_version[0] < 6 or (sw_version[0] == 6 and sw_version[1] < 10):
                host_group_dict = {1: 'Inside Hosts', 0: 'Outside Hosts'}
                raw_host_groups = api.get_host_groups()
                host_group_dict = splunk_utility.process_host_group_dict(host_group_dict, 'Inside Hosts', raw_host_groups['inside-hosts']['host-group'])
                host_group_dict = splunk_utility.process_host_group_dict(host_group_dict, 'Outside Hosts', raw_host_groups['outside-hosts']['host-group'])
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

            fc_data = api.get_flow_collectors()
            if fc_data is not None and len(fc_data) > 0:
                for fc in fc_data:
                    if "id" in fc and id is not None:
                        fc_id = int(fc["id"])
                        fc_name = ""
                        fc_ip = ""
                        if "name" in fc and fc["name"] is not None and len(fc["name"]) > 0:
                            fc_name = fc["name"]
                        if "ipAddress" in fc and fc["ipAddress"] is not None and len(fc["ipAddress"]) > 0:
                            fc_ip = fc["ipAddress"]
                        if len(fc_name) > 0 and len(fc_ip) > 0:
                            fc_map[fc_id] = fc_name + " (" + fc_ip + ")"
                        elif len(fc_name) > 0:
                            fc_map[fc_id] = fc_name
                        elif len(fc_ip) > 0:
                            fc_map[fc_id] = fc_ip
                        else:
                            fc_map[fc_id] = " "


        ############################################################################################################
        # LOGOUT the session
        ############################################################################################################
        # Disabling Logout as it is causing 401 unauthenticated
        # logger.info("De-authenticating API connection...")
        # api.logout()
        # logger.info("Done de-authenticating API connection.")

        if data is not None and len(data) > 0:
            for row in data["results"]:
                this_row = process_row(row, host_group_dict, fc_map)
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

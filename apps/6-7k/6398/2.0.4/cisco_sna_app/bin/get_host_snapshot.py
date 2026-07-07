# ==========================================================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# get_top_ports.py script for use with Splunk enterprise to fetch top peers
# from StealthWatch using the RESTx appliance REST API extension service
# ==========================================================================================================

# Usage: |hostsnapshot earliest=<earliest> host_ip=<host_ip> [flow_collector_list=<flow,collector,list>] [domain_id=<domain_id>] [smc_ip=<smc_ip>]

############################################################################################################
# Get some libraries we will need
############################################################################################################

import splunk_utility
import traceback
import splunk
import splunk.Intersplunk

import stealthwatch_api_client


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
    host_ip = kwargs.get('host_ip')
    flow_collector_list = kwargs.get('flow_collector_list')
    domain_id = kwargs.get('domain_id')
    smc_ip = kwargs.get('smc_ip')

    if earliest is None or host_ip is None:
        logger.error("Missing required arguments")
        logger.error("Aborting RESTx API process")
        # Following line calls sys.exit()
        splunk.Intersplunk.parseError("Missing required arguments! (Usage: |hostsnapshot earliest=<earliest> host_ip=<host_ip> [flow_collector_list=<flow,collector,list>] [domain_id=<domain_id>] [smc_ip=<smc_ip>])")

    start_datetime = None
    datetimes = splunk_utility.get_timerange(earliest=earliest, latest="now", logger=logger)
    if "start_datetime" in list(datetimes.keys()) and datetimes["start_datetime"] is not None:
        start_datetime = datetimes["start_datetime"]

    if flow_collector_list is None or len(flow_collector_list) <= 0:
        flow_collector_list = None
    else:
        tmp_flow_collectors = []
        for swa_id in flow_collector_list.split(","):
            tmp_flow_collectors.append(int(swa_id.strip()))
        flow_collector_list = tmp_flow_collectors


    ############################################################################################################
    # Read and parse config file for additional parameters required.
    ############################################################################################################
    logger.info("Getting config...")
    config = splunk_utility.get_config(logger)
    logger.info("Done getting config.")

    if smc_ip is None or len(smc_ip) <= 0:
        smc_ip = config["smcIP"].replace("%2C", ",").split(",")[0].strip()

    ############################################################################################################
    # Storage for the results
    ############################################################################################################
    results = []
    host_group_dict = {}
    protocol_map = {}
    application_map = {}
    service_definitions = {}
    security_event_types = {}
    fc_map = {}
    alarm_type_map = {}
    default_alarm_type_map = {
        32 : "High Concern Index",
        15 : "High Target Index",
        51 : "Recon",
        46 : "Command & Control",
        56 : "Exploitation",
        54 : "DDoS Source",
        53 : "DDoS Target",
        52 : "Data Hoarding",
        45 : "Exfiltration",
        47 : "Policy Violation",
        57 : "Anomaly"
    }

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
        logger.info("Executing \"get_host_snapshot\" API call...")
        snapshot_data = api.get_host_snapshot(start_datetime=start_datetime, host_ip=host_ip, flow_collector_list=flow_collector_list)
        logger.info("Done executing \"get_host_snapshot\" API call.")

        logger.info("Executing \"get_host_report_by_ip\" API call...")
        host_report_data = api.get_host_report_by_ip(ip_address=host_ip)
        logger.info("Done executing \"get_host_report_by_ip\" API call.")


        ############################################################################################################
        # Get data to map in later
        ############################################################################################################
        if snapshot_data is not None and len(snapshot_data) > 0:
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

            service_definitions_tmp = api.get_service_definitions()
            for item in service_definitions_tmp["service-definitions"]["services"]["service"]:
                service_definitions[item["profile"]] = item["name"]
            protocol_map = api.get_protocol_list(surpress_std_out=True)

            default_applications = api.get_application_definitions()
            if default_applications is not None:
                for application in default_applications:
                    application_map[application["id"]] = application["name"]
            custom_applications = api.get_custom_applications()
            if custom_applications is not None:
                for application in custom_applications:
                    application_map[application["id"]] = application["name"]

            if not (sw_version[0] < 6 or sw_version[1] < 10):
                security_event_descriptions = api.get_security_event_descriptions()
                if security_event_descriptions is not None:
                    for event in security_event_descriptions:
                        security_event_types[event["id"]] = event["name"]
            else:
                security_event_descriptions = api.get_security_events_metadata()
                if security_event_descriptions is not None:
                    for event in security_event_descriptions:
                        security_event_types[int(event["id"])] = event["display-name"]
            custom_security_event_descriptions = api.get_custom_security_events()
            if custom_security_event_descriptions is not None and "customSecurityEvents" in custom_security_event_descriptions:
                for event in custom_security_event_descriptions["customSecurityEvents"]:
                    security_event_types[event["id"]] = event["name"]

            alarm_type_list_raw = api.get_daily_alarm_types(ip_address=host_ip, number_of_days_back=7)
            if alarm_type_list_raw is not None and "series" in alarm_type_list_raw and len(alarm_type_list_raw["series"]) > 0:
                for alarm_type in alarm_type_list_raw["series"]:
                    alarm_type_map[alarm_type["id"]] = alarm_type["name"]

            fc_data = api.get_flow_collectors()
            if fc_data is not None and len(fc_data) > 0:
                for fc in fc_data:
                    if "id" in fc and fc["id"] is not None:
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
        logger.info("De-authenticating API connection...")
        api.logout()
        logger.info("Done de-authenticating API connection.")


        if snapshot_data is not None and "ip-address" in snapshot_data:
            identification_data = {}
            identification_data["row_type"] = "host_identification"
            if "domain-id" in snapshot_data and snapshot_data["domain-id"] is not None:
                identification_data["domain_id"] = snapshot_data["domain-id"]
            if "ip-address" in snapshot_data and snapshot_data["ip-address"] is not None:
                identification_data["ip_address"] = snapshot_data["ip-address"]
            if "host-name" in snapshot_data and snapshot_data["host-name"] is not None:
                identification_data["host_name"] = snapshot_data["host-name"]
            else:
                identification_data["host_name"] = " "
            if "time" in snapshot_data and snapshot_data["time"] is not None:
                identification_data["time"] = snapshot_data["time"]
            results.append(identification_data)


            if "host-group-ids" in snapshot_data and snapshot_data["host-group-ids"] is not None:
                for id in snapshot_data["host-group-ids"].split(","):
                    hostgroup_data = {}
                    hostgroup_data["row_type"] = "host_groups"
                    hostgroup_data["host_group_id"] = str(id)
                    if int(id) in host_group_dict:
                        hostgroup_data["host_group_name"] = str(host_group_dict[int(id)])
                    else:
                        hostgroup_data["host_group_name"] = "[Unknown Host Group ID: " + str(id) + "]"
                    results.append(hostgroup_data)


            if "status-list" in snapshot_data and snapshot_data["status-list"] is not None and "status" in snapshot_data["status-list"] and snapshot_data["status-list"]["status"] is not None:
                if not isinstance(snapshot_data["status-list"]["status"], list):
                    snapshot_data["status-list"]["status"] = [snapshot_data["status-list"]["status"]]
                for status_update in snapshot_data["status-list"]["status"]:
                    status_data = {}
                    status_data["row_type"] = "host_status"
                    status_data["fc_id"] = status_update["device-id"]
                    if int(status_update["device-id"]) in fc_map:
                        status_data["fc_name"] = fc_map[int(status_update["device-id"])]
                    else:
                        status_data["fc_name"] = " "
                    if "first-seen" in status_update and status_update["first-seen"] is not None:
                        status_data["status_first_seen"] = status_update["first-seen"]
                    else:
                        status_data["status_first_seen"] = " "
                    if "last-seen" in status_update and status_update["last-seen"] is not None:
                        status_data["status_last_seen"] = status_update["last-seen"]
                    else:
                        status_data["status_last_seen"] = " "
                    if "value" in status_update and status_update["value"] is not None:
                        status_data["status_value"] = status_update["value"]
                    else:
                        status_data["status_value"] = " "
                    if "mac-address" in status_update and status_update["mac-address"] is not None:
                        if "value" in status_update["mac-address"] and status_update["mac-address"]["value"] is not None:
                            status_data["mac_address"] = status_update["mac-address"]["value"]
                        else:
                            status_data["mac_address"] = " "
                    else:
                        status_data["mac_address"] = " "
                    results.append(status_data)
            else:
                status_data = {}
                status_data["row_type"] = "host_status"
                status_data["fc_id"] = " "
                status_data["fc_name"] = " "
                status_data["status_first_seen"] = " "
                status_data["status_last_seen"] = " "
                status_data["status_value"] = " "
                status_data["mac_address"] = " "
                # results.append(status_data)


            if "host-information-list" in snapshot_data and snapshot_data["host-information-list"] is not None and "host-information" in snapshot_data["host-information-list"] and snapshot_data["host-information-list"]["host-information"] is not None:
                if not isinstance(snapshot_data["host-information-list"]["host-information"], list):
                    snapshot_data["host-information-list"]["host-information"] = [snapshot_data["host-information-list"]["host-information"]]
                for information in snapshot_data["host-information-list"]["host-information"]:
                    information_data = {}
                    information_data["row_type"] = "host_information"
                    information_data["fc_id"] = information["device-id"]
                    if int(information["device-id"]) in fc_map:
                        information_data["fc_name"] = fc_map[int(information["device-id"])]
                    else:
                        information_data["fc_name"] = " "
                    # if "alerts" in information and information["alerts"] is not None:
                    #     if information["alerts"].startswith(","):
                    #         information["alerts"] = information["alerts"][1:]
                    #     if information["alerts"].endswith(","):
                    #         information["alerts"] = information["alerts"][:-1]
                    #     information_data["alert_ids"] = information["alerts"].replace(",", ", ")
                    #     information_data["alert_names"] = "TEST ALERT NAMES"
                    # else:
                    #     information_data["alert_ids"] = " "
                    #     information_data["alert_names"] = " "
                    if "application-activity" in information and information["application-activity"] is not None:
                        if "client" in information["application-activity"] and information["application-activity"]["client"] is not None:


                            if information["application-activity"]["client"].startswith(","):
                                information["application-activity"]["client"] = information["application-activity"]["client"][1:]
                            if information["application-activity"]["client"].endswith(","):
                                information["application-activity"]["client"] = information["application-activity"]["client"][:-1]


                            information_data["client_application_ids"] = information["application-activity"]["client"].replace(",", ", ")
                            information_data["client_application_names"] = ""
                            for id in information["application-activity"]["client"].split(","):
                                if len(id) > 0 and int(id) in list(application_map.keys()):
                                    information_data["client_application_names"] += ", " + application_map[int(id)]
                                else:
                                    information_data["client_application_names"] += ", Unknown Application (ID: " + str(id) + ")"
                            information_data["client_application_names"] = information_data["client_application_names"][2:]
                        else:
                            information_data["client_application_ids"] = " "
                            information_data["client_application_names"] = " "
                        if "server" in information["application-activity"] and information["application-activity"]["server"] is not None:

                            if information["application-activity"]["server"].startswith(","):
                                information["application-activity"]["server"] = information["application-activity"]["server"][1:]
                            if information["application-activity"]["server"].endswith(","):
                                information["application-activity"]["server"] = information["application-activity"]["server"][:-1]

                            information_data["server_application_ids"] = information["application-activity"]["server"].replace(",", ", ")
                            information_data["server_application_names"] = ""
                            for id in information["application-activity"]["server"].split(","):
                                if len(id) > 0 and int(id) in list(application_map.keys()):
                                    information_data["server_application_names"] += ", " + application_map[int(id)]
                                else:
                                    information_data["server_application_names"] += ", Unknown Application (ID: " + str(id) + ")"
                            information_data["server_application_names"] = information_data["server_application_names"][2:]
                        else:
                            information_data["server_application_ids"] = " "
                            information_data["server_application_names"] = " "
                    else:
                        information_data["client_application_ids"] = " "
                        information_data["client_application_names"] = " "
                        information_data["server_application_ids"] = " "
                        information_data["server_application_names"] = " "
                    if "service-profile-status" in information and information["service-profile-status"] is not None:
                        if "client" in information["service-profile-status"] and information["service-profile-status"]["client"] is not None:

                            if information["service-profile-status"]["client"].startswith(","):
                                information["service-profile-status"]["client"] = information["service-profile-status"]["client"][1:]
                            if information["service-profile-status"]["client"].endswith(","):
                                information["service-profile-status"]["client"] = information["service-profile-status"]["client"][:-1]

                            information_data["client_service_ids"] = information["service-profile-status"]["client"].replace(",", ", ")
                            information_data["client_service_names"] = ""
                            for id in information["service-profile-status"]["client"].split(","):
                                if id.startswith("1:S"):
                                    id = id[3:]
                                if id.startswith("S"):
                                    id = id[1:]
                                if len(id) > 0 and id in list(service_definitions.keys()):
                                    information_data["client_service_names"] += ", " + service_definitions[id]
                                elif len(id) == 5 and id.startswith("6"):
                                    id = id[1:]
                                    while id.startswith("0"):
                                        id = id[1:]
                                    if protocol_map is not None and str(id) in list(protocol_map.keys()):
                                        information_data["client_service_names"] += ", " + protocol_map[str(id)]
                                    else:
                                        information_data["client_service_names"] += ", " + "Protocol " + id
                                elif id.startswith("O"):
                                    information_data["client_service_names"] += ", " + str(id)[1:]
                            information_data["client_service_names"] = information_data["client_service_names"][2:]
                        else:
                            information_data["client_service_ids"] = " "
                            information_data["client_service_names"] = " "
                        if "server" in information["service-profile-status"] and information["service-profile-status"]["server"] is not None:

                            if information["service-profile-status"]["server"].startswith(","):
                                information["service-profile-status"]["server"] = information["service-profile-status"]["server"][1:]
                            if information["service-profile-status"]["server"].endswith(","):
                                information["service-profile-status"]["server"] = information["service-profile-status"]["server"][:-1]

                            information_data["server_service_ids"] = information["service-profile-status"]["server"].replace(",", ", ")
                            information_data["server_service_names"] = ""
                            for id in information["service-profile-status"]["server"].split(","):
                                if id.startswith("1:S"):
                                    id = id[3:]
                                if id.startswith("S"):
                                    id = id[1:]
                                if len(id) > 0 and id in list(service_definitions.keys()):
                                    information_data["server_service_names"] += ", " + service_definitions[id]
                                elif len(id) == 5 and id.startswith("6"):
                                    id = id[1:]
                                    while id.startswith("0"):
                                        id = id[1:]
                                    if protocol_map is not None and str(id) in list(protocol_map.keys()):
                                        information_data["server_service_names"] += ", " + protocol_map[str(id)]
                                    else:
                                        information_data["server_service_names"] += ", " + "Protocol " + id
                                elif id.startswith("O"):
                                    information_data["server_service_names"] += ", " + str(id)[1:]
                            information_data["server_service_names"] = information_data["server_service_names"][2:]
                        else:
                            information_data["server_service_ids"] = " "
                            information_data["server_service_names"] = " "
                    else:
                        information_data["client_service_ids"] = " "
                        information_data["client_service_names"] = " "
                        information_data["server_service_ids"] = " "
                        information_data["server_service_names"] = " "
                    results.append(information_data)
            else:
                information_data = {}
                information_data["row_type"] = "host_information"
                information_data["fc_id"] = " "
                information_data["fc_name"] = " "
                # information_data["alert_ids"] = " "
                # information_data["alert_names"] = " "
                information_data["client_application_ids"] = " "
                information_data["client_application_names"] = " "
                information_data["server_application_ids"] = " "
                information_data["server_application_names"] = " "
                information_data["client_service_ids"] = " "
                information_data["client_service_names"] = " "
                information_data["server_service_ids"] = " "
                information_data["server_service_names"] = " "
                # results.append(information_data)


            alarm_count_summary_data = {}
            alarm_count_summary_data["row_type"] = "host_alarm_count_summary"
            alarm_count_summary_data["source_alarm_count"] = 0
            alarm_count_summary_data["target_alarm_count"] = 0
            alarm_count_details_map = {}
            if "alarm-counts-list" in snapshot_data and snapshot_data["alarm-counts-list"] is not None and "alarm-counts" in snapshot_data["alarm-counts-list"] and snapshot_data["alarm-counts-list"]["alarm-counts"] is not None:
                if not isinstance(snapshot_data["alarm-counts-list"]["alarm-counts"], list):
                    snapshot_data["alarm-counts-list"]["alarm-counts"] = [snapshot_data["alarm-counts-list"]["alarm-counts"]]
                for alarm_count in snapshot_data["alarm-counts-list"]["alarm-counts"]:
                    if "source" in alarm_count:
                        alarm_count_summary_data["source_alarm_count"] += int(alarm_count["source"])
                    if "target" in alarm_count:
                        alarm_count_summary_data["target_alarm_count"] += int(alarm_count["target"])
                    if "details" in alarm_count and len(alarm_count["details"]) > 0:
                        if not isinstance(alarm_count["details"], list):
                            alarm_count["details"] = [alarm_count["details"]]
                        for alarm_details in alarm_count["details"]:
                            if "alarm-type" in alarm_details:
                                if alarm_details["alarm-type"] not in alarm_count_details_map:
                                    alarm_count_details_map[alarm_details["alarm-type"]] = {}
                                    if int(alarm_details["alarm-type"]) in alarm_type_map:
                                        alarm_count_details_map[alarm_details["alarm-type"]]["alarm_type_name"] = alarm_type_map[int(alarm_details["alarm-type"])]
                                    elif int(alarm_details["alarm-type"]) in security_event_types:
                                        alarm_count_details_map[alarm_details["alarm-type"]]["alarm_type_name"] = security_event_types[int(alarm_details["alarm-type"])]
                                    elif int(alarm_details["alarm-type"]) in default_alarm_type_map:
                                        alarm_count_details_map[alarm_details["alarm-type"]]["alarm_type_name"] = default_alarm_type_map[int(alarm_details["alarm-type"])]
                                    else:
                                        alarm_count_details_map[alarm_details["alarm-type"]]["alarm_type_name"] = "Unknown Alarm Type (ID: " + str(alarm_details["alarm-type"]) + ")"
                                    alarm_count_details_map[alarm_details["alarm-type"]]["source_alarm_type_count"] = 0
                                    alarm_count_details_map[alarm_details["alarm-type"]]["target_alarm_type_count"] = 0
                                if "source" in alarm_details:
                                    alarm_count_details_map[alarm_details["alarm-type"]]["source_alarm_type_count"] += int(alarm_details["source"])
                                if "target" in alarm_details:
                                    alarm_count_details_map[alarm_details["alarm-type"]]["target_alarm_type_count"] += int(alarm_details["target"])

            if len(alarm_count_details_map) > 0:
                for id,details in list(alarm_count_details_map.items()):
                    alarm_count_details_data = {}
                    alarm_count_details_data["row_type"] = "host_alarm_count_details"
                    alarm_count_details_data["alarm_type_id"] = id
                    alarm_count_details_data["alarm_type_name"] = details["alarm_type_name"]
                    alarm_count_details_data["source_alarm_type_count"] = str(details["source_alarm_type_count"])
                    alarm_count_details_data["target_alarm_type_count"] = str(details["target_alarm_type_count"])
                    results.append(alarm_count_details_data)
            else:
                alarm_count_details_data = {}
                alarm_count_details_data["row_type"] = "host_alarm_count_details"
                alarm_count_details_data["alarm_type_id"] = " "
                alarm_count_details_data["alarm_type_name"] = " "
                alarm_count_details_data["source_alarm_type_count"] = " "
                alarm_count_details_data["target_alarm_type_count"] = " "
                results.append(alarm_count_details_data)
            alarm_count_summary_data["source_alarm_count"] = str(alarm_count_summary_data["source_alarm_count"])
            alarm_count_summary_data["target_alarm_count"] = str(alarm_count_summary_data["target_alarm_count"])
            results.append(alarm_count_summary_data)




            if "alarm-list" in snapshot_data and snapshot_data["alarm-list"] is not None and "alarm" in snapshot_data["alarm-list"] and snapshot_data["alarm-list"]["alarm"] is not None:
                if not isinstance(snapshot_data["alarm-list"]["alarm"], list):
                    snapshot_data["alarm-list"]["alarm"] = [snapshot_data["alarm-list"]["alarm"]]
                for alarm in snapshot_data["alarm-list"]["alarm"]:
                    alarm_data = {}
                    alarm_data["row_type"] = "host_alarms"
                    if "device-id" in alarm:
                        alarm_data["fc_id"] = alarm["device-id"]
                        if int(alarm["device-id"]) in fc_map:
                            alarm_data["fc_name"] = fc_map[int(alarm["device-id"])]
                        else:
                            alarm_data["fc_name"] = " "
                    else:
                        alarm_data["fc_id"] = " "
                        alarm_data["fc_name"] = " "
                    if "active" in alarm:
                        if str(alarm["active"]).lower() == "true":
                            alarm_data["alarm_status"] = "Active"
                        else:
                            alarm_data["alarm_status"] = "Inactive"
                    else:
                        alarm_data["alarm_status"] = " "
                    if "start-time" in alarm:
                        alarm_data["alarm_start_time"] = alarm["start-time"]
                    else:
                        alarm_data["alarm_start_time"] = " "
                    if "end-time" in alarm:
                        alarm_data["alarm_end_time"] = alarm["end-time"]
                    else:
                        alarm_data["alarm_end_time"] = " "
                    if "id" in alarm:
                        alarm_data["alarm_id"] = alarm["id"]
                    else:
                        alarm_data["alarm_id"] = " "
                    if "type" in alarm:
                        alarm_data["alarm_type_id"] = alarm["type"]
                        if int(alarm["type"]) in alarm_type_map:
                            alarm_data["alarm_type_name"] = alarm_type_map[int(alarm["type"])]
                        elif int(alarm["type"]) in security_event_types:
                            alarm_data["alarm_type_name"] = security_event_types[int(alarm["type"])]
                        elif int(alarm["type"]) in default_alarm_type_map:
                            alarm_data["alarm_type_name"] = default_alarm_type_map[int(alarm["type"])]
                        else:
                            alarm_data["alarm_type_name"] = "Unknown Alarm Type (ID: " + str(alarm["type"]) + ")"
                    else:
                        alarm_data["alarm_type_id"] = " "
                        alarm_data["alarm_type_name"] = " "
                    if "source" in alarm:
                        if "ip-address" in alarm["source"]:
                            alarm_data["alarm_source_ip"] = alarm["source"]["ip-address"]
                        else:
                            alarm_data["alarm_source_ip"] = " "
                        if "host-group-ids" in alarm["source"]:
                            if alarm["source"]["host-group-ids"].startswith(","):
                                alarm["source"]["host-group-ids"] = alarm["source"]["host-group-ids"][1:]
                            if alarm["source"]["host-group-ids"].endswith(","):
                                alarm["source"]["host-group-ids"] = alarm["source"]["host-group-ids"][:-1]
                            alarm_data["alarm_source_host_group_ids"] = alarm["source"]["host-group-ids"].replace(",", ", ")
                            alarm_data["alarm_source_host_group_names"] = ""
                            for host_group_id in alarm["source"]["host-group-ids"].split(","):
                                if int(host_group_id) in host_group_dict:
                                    alarm_data["alarm_source_host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                                else:
                                    alarm_data["alarm_source_host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                            alarm_data["alarm_source_host_group_names"] = alarm_data["alarm_source_host_group_names"][2:]
                        else:
                            alarm_data["alarm_source_host_group_ids"] = " "
                            alarm_data["alarm_source_host_group_names"] = " "
                    else:
                        alarm_data["alarm_source_ip"] = " "
                        alarm_data["alarm_source_host_group_ids"] = " "
                        alarm_data["alarm_source_host_group_names"] = " "
                    if "target" in alarm:
                        if "ip-address" in alarm["target"]:
                            alarm_data["alarm_target_ip"] = alarm["target"]["ip-address"]
                        else:
                            alarm_data["alarm_target_ip"] = " "
                        if "host-group-ids" in alarm["target"]:
                            if alarm["target"]["host-group-ids"].startswith(","):
                                alarm["target"]["host-group-ids"] = alarm["target"]["host-group-ids"][1:]
                            if alarm["target"]["host-group-ids"].endswith(","):
                                alarm["target"]["host-group-ids"] = alarm["target"]["host-group-ids"][:-1]
                            alarm_data["alarm_target_host_group_ids"] = alarm["target"]["host-group-ids"].replace(",", ", ")
                            alarm_data["alarm_target_host_group_names"] = ""
                            for host_group_id in alarm["target"]["host-group-ids"].split(","):
                                if int(host_group_id) in host_group_dict:
                                    alarm_data["alarm_target_host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                                else:
                                    alarm_data["alarm_target_host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                            alarm_data["alarm_target_host_group_names"] = alarm_data["alarm_target_host_group_names"][2:]
                        else:
                            alarm_data["alarm_target_host_group_ids"] = " "
                            alarm_data["alarm_target_host_group_names"] = " "
                    else:
                        alarm_data["alarm_target_ip"] = " "
                        alarm_data["alarm_target_host_group_ids"] = " "
                        alarm_data["alarm_target_host_group_names"] = " "
                    results.append(alarm_data)
            else:
                alarm_data = {}
                alarm_data["row_type"] = "host_alarms"
                alarm_data["fc_id"] = " "
                alarm_data["fc_name"] = " "
                alarm_data["alarm_status"] = " "
                alarm_data["alarm_start_time"] = " "
                alarm_data["alarm_end_time"] = " "
                alarm_data["alarm_id"] = " "
                alarm_data["alarm_type_id"] = " "
                alarm_data["alarm_type_name"] = " "
                alarm_data["alarm_source_ip"] = " "
                alarm_data["alarm_source_host_group_ids"] = " "
                alarm_data["alarm_source_host_group_names"] = " "
                alarm_data["alarm_target_ip"] = " "
                alarm_data["alarm_target_host_group_ids"] = " "
                alarm_data["alarm_target_host_group_names"] = " "
                # results.append(alarm_data)


            security_index_map = {
                "concern-index" : "Concern Index",
                "target-index": "Target Index",
                "recon-index": "Recon",
                "command-and-control-index": "C&C",
                "attack-index": "Exploitation",
                "high-ddos-source-index": "DDoS Source",
                "high-ddos-target-inde": "DDoS Target",
                "data-hoarding-index": "Data Hoarding",
                "exfiltration-index": "Exfiltration",
                "policy-violation-index": "Policy Violation",
                "anomaly-index": "Anomaly",
                "file-sharing-index" : "File Sharing"
            }

            if "security-list" in snapshot_data and snapshot_data["security-list"] is not None and "security" in snapshot_data["security-list"] and snapshot_data["security-list"]["security"] is not None:
                if not isinstance(snapshot_data["security-list"]["security"], list):
                    snapshot_data["security-list"]["security"] = [snapshot_data["security-list"]["security"]]
                for security in snapshot_data["security-list"]["security"]:
                    security_summary_data = {}
                    security_summary_data["row_type"] = "host_security_summary"
                    if "device-id" in security:
                        security_summary_data["fc_id"] = security["device-id"]
                        if int(security["device-id"]) in fc_map:
                            security_summary_data["fc_name"] = fc_map[int(security["device-id"])]
                        else:
                            security_summary_data["fc_name"] = " "
                    else:
                        security_summary_data["fc_id"] = " "
                        security_summary_data["fc_name"] = " "
                    for key,val in list(security.items()):
                        if key.endswith("-index"):
                            security_data = {}
                            security_data["row_type"] = "host_security"
                            security_data["security_index"] = key
                            security_data["fc_id"] = security_summary_data["fc_id"]
                            security_data["fc_name"] = security_summary_data["fc_name"]
                            if key in security_index_map:
                                security_data["security_index_name"] = security_index_map[key]
                            else:
                                security_data["security_index_name"] = key
                            security_data["security_index_value"] = val["value"]
                            security_data["security_index_threshold"] = val["threshold"]
                            if int(val["threshold"]) == 0:
                                security_data["security_index_percent"] = "N/A"
                                security_summary_data["security_" + key.replace("-", "_")] = "N/A"
                            else:
                                security_data["security_index_percent"] = (int(val["value"]) * 100) // int(val["threshold"])
                                security_summary_data["security_" + key.replace("-", "_")] = security_data["security_index_percent"]
                            if "severity" in val:
                                security_data["security_index_severity"] = val["severity"]
                            else:
                                security_data["security_index_severity"] = " "
                            results.append(security_data)
                    results.append(security_summary_data)
            else:
                security_summary_data = {}
                security_summary_data["row_type"] = "host_security_summary"
                security_summary_data["fc_id"] = " "
                security_summary_data["fc_name"] = " "
                for key in list(security_index_map.keys()):
                    security_summary_data["security_" + key.replace("-", "_")] = 0
                results.append(security_summary_data)
                security_data = {}
                security_data["row_type"] = "host_security"
                security_data["security_index"] = " "
                security_data["fc_id"] = " "
                security_data["fc_name"] = " "
                security_data["security_index_name"] = " "
                security_data["security_index_value"] = " "
                security_data["security_index_threshold"] = " "
                security_data["security_index_percent"] = " "
                security_data["security_index_severity"] = " "
                # results.append(security_data)


            security_event_list = []
            if "ci-events" in snapshot_data and snapshot_data["ci-events"] is not None and "source-high-ci-list" in snapshot_data["ci-events"] and snapshot_data["ci-events"]["source-high-ci-list"] is not None and "ci-event" in snapshot_data["ci-events"]["source-high-ci-list"] and snapshot_data["ci-events"]["source-high-ci-list"]["ci-event"] is not None:
                if not isinstance(snapshot_data["ci-events"]["source-high-ci-list"]["ci-event"], list):
                    snapshot_data["ci-events"]["source-high-ci-list"]["ci-event"] = [snapshot_data["ci-events"]["source-high-ci-list"]["ci-event"]]
                for event in snapshot_data["ci-events"]["source-high-ci-list"]["ci-event"]:
                    event["origin-list"] = "source-high-ci-list"
                    security_event_list.append(event)
            if "ci-events" in snapshot_data and snapshot_data["ci-events"] is not None and "source-list" in snapshot_data["ci-events"] and snapshot_data["ci-events"]["source-list"] is not None and "ci-event" in snapshot_data["ci-events"]["source-list"] and snapshot_data["ci-events"]["source-list"]["ci-event"] is not None:
                if not isinstance(snapshot_data["ci-events"]["source-list"]["ci-event"], list):
                    snapshot_data["ci-events"]["source-list"]["ci-event"] = [snapshot_data["ci-events"]["source-list"]["ci-event"]]
                for event in snapshot_data["ci-events"]["source-list"]["ci-event"]:
                    event["origin-list"] = "source-list"
                    security_event_list.append(event)
            if "ci-events" in snapshot_data and snapshot_data["ci-events"] is not None and "target-list" in snapshot_data["ci-events"] and snapshot_data["ci-events"]["target-list"] is not None and "ci-event" in snapshot_data["ci-events"]["target-list"] and snapshot_data["ci-events"]["target-list"]["ci-event"] is not None:
                if not isinstance(snapshot_data["ci-events"]["target-list"]["ci-event"], list):
                    snapshot_data["ci-events"]["target-list"]["ci-event"] = [snapshot_data["ci-events"]["target-list"]["ci-event"]]
                for event in snapshot_data["ci-events"]["target-list"]["ci-event"]:
                    event["origin-list"] = "target-list"
                    security_event_list.append(event)
            if len(security_event_list) > 0:
                for event in security_event_list:
                    event_data = {}
                    event_data["row_type"] = "host_security_events"
                    event_data["origin_list"] = event["origin-list"]
                    if "device-id" in event and event["device-id"] is not None:
                        event_data["fc_id"] = event["device-id"]
                        if int(event["device-id"]) in fc_map:
                            event_data["fc_name"] = fc_map[int(event["device-id"])]
                        else:
                            event_data["fc_name"] = " "
                    else:
                        event_data["fc_id"] = " "
                        event_data["fc_name"] = " "
                    if "last-time" in event and event["last-time"] is not None:
                        event_data["last_time"] = event["last-time"]
                    else:
                        event_data["last_time"] = " "
                    if "start-time" in event and event["start-time"] is not None:
                        event_data["start_time"] = event["start-time"]
                    else:
                        event_data["start_time"] = " "
                    if "details-list" in event and event["details-list"] is not None and "details" in event["details-list"] and event["details-list"]["details"]:
                        if not isinstance(event["details-list"]["details"], list):
                            event["details-list"]["details"] = [event["details-list"]["details"]]
                        for detail in event["details-list"]["details"]:
                            if "type" in detail:
                                event_data["event_type_id"] = detail["type"]
                                if int(detail["type"]) in security_event_types:
                                    event_data["event_type_name"] = security_event_types[int(detail["type"])]
                                    if "port" in detail:
                                        event_data["event_type_name"] += "-" + str(detail["port"])
                                else:
                                    event_data["event_type_name"] = "Unknown Event Type (ID: " + str(detail["type"]) + ")"
                            else:
                                event_data["event_type_id"] = " "
                                event_data["event_type_name"] = " "
                            if "hit-count" in detail:
                                event_data["hit_count"] = detail["hit-count"]
                            else:
                                event_data["hit_count"] = " "
                            if "ci-points" in event:
                                event_data["ci_points"] = event["ci-points"]
                            elif "ci-points" in detail:
                                event_data["ci_points"] = detail["ci-points"]
                            else:
                                event_data["ci_points"] = " "
                            if "port" in detail:
                                event_data["port"] = detail["port"]
                            else:
                                event_data["port"] = " "
                            results.append(event_data)
                    if "source" in event and event["source"] is not None:
                        if "ip-address" in event["source"]:
                            if event["source"]["ip-address"] == "0.0.0.0":
                                event_data["source_ip"] = "Multiple Hosts"
                            else:
                                event_data["source_ip"] = event["source"]["ip-address"]
                                # if event_data["source_ip"].endswith(".0.0"):
                                #     event_data["source_ip"] = event_data["source_ip"] + "/16"
                                # elif event_data["source_ip"].endswith(".0"):
                                #     event_data["source_ip"] = event_data["source_ip"] + "/24"
                        else:
                            event_data["source_ip"] = " "
                        if "host-group-ids" in event["source"]:
                            if event["source"]["ip-address"] == "0.0.0.0":
                                event_data["source_host_group_ids"] = " "
                                event_data["source_host_group_names"] = " "
                            else:
                                event_data["source_host_group_ids"] = event["source"]["host-group-ids"]
                                event_data["source_host_group_names"] = ""
                                for host_group_id in event["source"]["host-group-ids"].split(","):
                                    if int(host_group_id) in host_group_dict:
                                        event_data["source_host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                                    else:
                                        event_data["source_host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                                event_data["source_host_group_names"] = event_data["source_host_group_names"][2:]
                        else:
                            event_data["source_host_group_ids"] = " "
                            event_data["source_host_group_names"] = " "
                        if "host-name" in event["source"]:
                            event_data["source_hostname"] = event["source"]["host-name"]
                        else:
                            event_data["source_hostname"] = " "
                    else:
                        event_data["source_ip"] = " "
                        event_data["source_host_group_ids"] = " "
                        event_data["source_host_group_names"] = " "
                        event_data["source_hostname"] = " "
                    if "target" in event and event["target"] is not None:
                        if "ip-address" in event["target"]:
                            if event["target"]["ip-address"] == "0.0.0.0":
                                event_data["target_ip"] = "Multiple Hosts"
                            else:
                                event_data["target_ip"] = event["target"]["ip-address"]
                                if event_data["target_ip"].endswith(".0.0") and "scan" in event_data["event_type_name"].lower():
                                    event_data["target_ip"] = event_data["target_ip"] + "/16"
                                elif event_data["target_ip"].endswith(".0") and "scan" in event_data["event_type_name"].lower():
                                    event_data["target_ip"] = event_data["target_ip"] + "/24"
                        else:
                            event_data["target_ip"] = " "
                        if "host-group-ids" in event["target"]:
                            if event["target"]["ip-address"] == "0.0.0.0":
                                event_data["target_host_group_ids"] = " "
                                event_data["target_host_group_names"] = " "
                            else:
                                event_data["target_host_group_ids"] = event["target"]["host-group-ids"]
                                event_data["target_host_group_names"] = ""
                                for host_group_id in event["target"]["host-group-ids"].split(","):
                                    if int(host_group_id) in host_group_dict:
                                        event_data["target_host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                                    else:
                                        event_data["target_host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                                event_data["target_host_group_names"] = event_data["target_host_group_names"][2:]
                        else:
                            event_data["target_host_group_ids"] = " "
                            event_data["target_host_group_names"] = " "
                        if "host-name" in event["target"]:
                            event_data["target_hostname"] = event["target"]["host-name"]
                        else:
                            event_data["target_hostname"] = " "
                    else:
                        event_data["target_ip"] = " "
                        event_data["target_host_group_ids"] = " "
                        event_data["target_host_group_names"] = " "
                        event_data["target_hostname"] = " "
            else:
                event_data = {}
                event_data["row_type"] = "host_security_events"
                event_data["origin_list"] = "source-high-ci-list"
                event_data["fc_id"] = " "
                event_data["fc_name"] = " "
                event_data["last_time"] = " "
                event_data["start_time"] = " "
                event_data["source_ip"] = " "
                event_data["source_host_group_ids"] = " "
                event_data["source_host_group_names"] = " "
                event_data["source_hostname"] = " "
                event_data["target_ip"] = " "
                event_data["target_host_group_ids"] = " "
                event_data["target_host_group_names"] = " "
                event_data["target_hostname"] = " "
                event_data["event_type_id"] = " "
                event_data["event_type_name"] = " "
                event_data["hit_count"] = " "
                event_data["ci_points"] = " "
                event_data["port"] = " "
                # results.append(event_data)
                event_data = {}
                event_data["row_type"] = "host_security_events"
                event_data["origin_list"] = "source-list"
                event_data["fc_id"] = " "
                event_data["fc_name"] = " "
                event_data["last_time"] = " "
                event_data["start_time"] = " "
                event_data["source_ip"] = " "
                event_data["source_host_group_ids"] = " "
                event_data["source_host_group_names"] = " "
                event_data["source_hostname"] = " "
                event_data["target_ip"] = " "
                event_data["target_host_group_ids"] = " "
                event_data["target_host_group_names"] = " "
                event_data["target_hostname"] = " "
                event_data["event_type_id"] = " "
                event_data["event_type_name"] = " "
                event_data["hit_count"] = " "
                event_data["ci_points"] = " "
                event_data["port"] = " "
                # results.append(event_data)
                event_data = {}
                event_data["row_type"] = "host_security_events"
                event_data["origin_list"] = "target-list"
                event_data["fc_id"] = " "
                event_data["fc_name"] = " "
                event_data["last_time"] = " "
                event_data["start_time"] = " "
                event_data["source_ip"] = " "
                event_data["source_host_group_ids"] = " "
                event_data["source_host_group_names"] = " "
                event_data["source_hostname"] = " "
                event_data["target_ip"] = " "
                event_data["target_host_group_ids"] = " "
                event_data["target_host_group_names"] = " "
                event_data["target_hostname"] = " "
                event_data["event_type_id"] = " "
                event_data["event_type_name"] = " "
                event_data["hit_count"] = " "
                event_data["ci_points"] = " "
                event_data["port"] = " "
                # results.append(event_data)

            tmp_total_bytes = 0
            tmp_total_bytes_data = 0
            tmp_total_packets = 0

            if "traffic-list" in snapshot_data and snapshot_data["traffic-list"] is not None and "traffic" in snapshot_data["traffic-list"] and snapshot_data["traffic-list"]["traffic"] is not None:
                if not isinstance(snapshot_data["traffic-list"]["traffic"], list):
                    snapshot_data["traffic-list"]["traffic"] = [snapshot_data["traffic-list"]["traffic"]]
                for traffic in snapshot_data["traffic-list"]["traffic"]:
                    traffic_data = {}
                    traffic_data["row_type"] = "host_traffic"
                    if "device-id" in traffic and traffic["device-id"] is not None:
                        traffic_data["fc_id"] = traffic["device-id"]
                        if int(traffic["device-id"]) in fc_map:
                            traffic_data["fc_name"] = fc_map[int(traffic["device-id"])]
                        else:
                            traffic_data["fc_name"] = " "
                    else:
                        traffic_data["fc_id"] = " "
                        traffic_data["fc_name"] = " "
                    if "day" in traffic:
                        if "threshold" in traffic["day"]:
                            traffic_data["threshold"] = traffic["day"]["threshold"]
                            traffic_data["threshold_str"] = splunk_utility.convert_bytes_to_string(traffic["day"]["threshold"])
                        else:
                            traffic_data["threshold"] = " "
                            traffic_data["threshold_str"] = " "
                        if "data-loss-threshold" in traffic["day"]:
                            traffic_data["data_loss_threshold"] = traffic["day"]["data-loss-threshold"]
                            traffic_data["data_loss_threshold_str"] = splunk_utility.convert_bytes_to_string(traffic["day"]["data-loss-threshold"])
                        else:
                            traffic_data["data_loss_threshold"] = " "
                            traffic_data["data_loss_threshold_str"] = " "
                        if "in" in traffic["day"]:
                            if "total-bytes" in traffic["day"]["in"]:
                                traffic_data["total_bytes_received"] = traffic["day"]["in"]["total-bytes"]
                                tmp_total_bytes += int(traffic["day"]["in"]["total-bytes"])
                                traffic_data["total_bytes_received_str"] = splunk_utility.convert_bytes_to_string(traffic["day"]["in"]["total-bytes"])
                            else:
                                traffic_data["total_bytes_received"] = " "
                                traffic_data["total_bytes_received_str"] = " "
                            if "total-data-bytes" in traffic["day"]["in"]:
                                traffic_data["total_bytes_data_received"] = traffic["day"]["in"]["total-data-bytes"]
                                tmp_total_bytes_data += int(traffic["day"]["in"]["total-data-bytes"])
                                traffic_data["total_bytes_data_received_str"] = splunk_utility.convert_bytes_to_string(traffic["day"]["in"]["total-data-bytes"])
                            else:
                                traffic_data["total_bytes_data_received"] = " "
                                traffic_data["total_bytes_data_received_str"] = " "
                            if "total-packets" in traffic["day"]["in"]:
                                traffic_data["total_packets_received"] = traffic["day"]["in"]["total-packets"]
                                tmp_total_packets += int(traffic["day"]["in"]["total-packets"])
                            else:
                                traffic_data["total_packets_received"] = " "
                        else:
                            traffic_data["total_bytes_received"] = " "
                            traffic_data["total_bytes_received_str"] = " "
                            traffic_data["total_bytes_data_received"] = " "
                            traffic_data["total_bytes_data_received_str"] = " "
                            traffic_data["total_packets_received"] = " "
                        if "out" in traffic["day"]:
                            if "total-bytes" in traffic["day"]["out"]:
                                traffic_data["total_bytes_sent"] = traffic["day"]["out"]["total-bytes"]
                                tmp_total_bytes += int(traffic["day"]["out"]["total-bytes"])
                                traffic_data["total_bytes_sent_str"] = splunk_utility.convert_bytes_to_string(traffic["day"]["out"]["total-bytes"])
                            else:
                                traffic_data["total_bytes_sent"] = " "
                                traffic_data["total_bytes_sent_str"] = " "
                            if "total-data-bytes" in traffic["day"]["out"]:
                                traffic_data["total_bytes_data_sent"] = traffic["day"]["out"]["total-data-bytes"]
                                tmp_total_bytes_data += int(traffic["day"]["out"]["total-data-bytes"])
                                traffic_data["total_bytes_data_sent_str"] = splunk_utility.convert_bytes_to_string(traffic["day"]["out"]["total-data-bytes"])
                            else:
                                traffic_data["total_bytes_data_sent"] = " "
                                traffic_data["total_bytes_data_sent_str"] = " "
                            if "total-packets" in traffic["day"]["out"]:
                                traffic_data["total_packets_sent"] = traffic["day"]["out"]["total-packets"]
                                tmp_total_packets += int(traffic["day"]["out"]["total-packets"])
                            else:
                                traffic_data["total_packets_sent"] = " "
                            if "data-loss" in traffic["day"]["out"]:
                                traffic_data["data_loss"] = traffic["day"]["out"]["data-loss"]
                                traffic_data["data_loss_str"] = splunk_utility.convert_bytes_to_string(traffic["day"]["out"]["data-loss"])
                            else:
                                traffic_data["data_loss"] = " "
                                traffic_data["data_loss_str"] = " "
                        else:
                            traffic_data["total_bytes_sent"] = " "
                            traffic_data["total_bytes_sent_str"] = " "
                            traffic_data["total_bytes_data_sent"] = " "
                            traffic_data["total_bytes_data_sent_str"] = " "
                            traffic_data["total_packets_sent"] = " "
                            traffic_data["data_loss"] = " "
                            traffic_data["data_loss_str"] = " "
                    else:
                        traffic_data["threshold"] = " "
                        traffic_data["threshold_str"] = " "
                        traffic_data["data_loss_threshold"] = " "
                        traffic_data["data_loss_threshold_str"] = " "
                        traffic_data["total_bytes_received"] = " "
                        traffic_data["total_bytes_received_str"] = " "
                        traffic_data["total_bytes_data_received"] = " "
                        traffic_data["total_bytes_data_received_str"] = " "
                        traffic_data["total_packets_received"] = " "
                        traffic_data["total_bytes_sent"] = " "
                        traffic_data["total_bytes_sent_str"] = " "
                        traffic_data["total_bytes_data_sent"] = " "
                        traffic_data["total_bytes_data_sent_str"] = " "
                        traffic_data["total_packets_sent"] = " "
                        traffic_data["data_loss"] = " "
                        traffic_data["data_loss_str"] = " "
                        traffic_data["total_bytes"] = "N/A"
                        traffic_data["total_bytes_data"] = "N/A"
                        traffic_data["total_packets"] = "N/A"
                    if "five-min" in traffic:
                        if "threshold" in traffic["five-min"]:
                            traffic_data["threshold_bps"] = traffic["five-min"]["threshold"]
                            traffic_data["threshold_bps_str"] = splunk_utility.convert_bytes_to_string(traffic["five-min"]["threshold"])
                        else:
                            traffic_data["threshold_bps"] = " "
                            traffic_data["threshold_bps_str"] = " "
                        if "udp-percent" in traffic["five-min"]:
                            traffic_data["udp_percentage"] = traffic["five-min"]["udp-percent"]
                        else:
                            traffic_data["udp_percentage"] = " "
                        if "in" in traffic["five-min"]:
                            if "max-bps" in traffic["five-min"]["in"]:
                                traffic_data["max_bps_received"] = traffic["five-min"]["in"]["max-bps"]
                                traffic_data["max_bps_received_str"] = splunk_utility.convert_bytes_to_string(traffic["five-min"]["in"]["max-bps"])
                            else:
                                traffic_data["max_bps_received"] = " "
                                traffic_data["max_bps_received_str"] = " "
                        else:
                            traffic_data["max_bps_received"] = " "
                            traffic_data["max_bps_received_str"] = " "
                        if "out" in traffic["five-min"]:
                            if "max-bps" in traffic["five-min"]["out"]:
                                traffic_data["max_bps_sent"] = traffic["five-min"]["out"]["max-bps"]
                                traffic_data["max_bps_sent_str"] = splunk_utility.convert_bytes_to_string(traffic["five-min"]["out"]["max-bps"])
                            else:
                                traffic_data["max_bps_sent"] = " "
                                traffic_data["max_bps_sent_str"] = " "
                        else:
                            traffic_data["max_bps_sent"] = " "
                            traffic_data["max_bps_sent_str"] = " "
                    else:
                        traffic_data["threshold_bps"] = " "
                        traffic_data["threshold_bps_str"] = " "
                        traffic_data["udp_percentage"] = " "
                        traffic_data["max_bps_received"] = " "
                        traffic_data["max_bps_received_str"] = " "
                        traffic_data["max_bps_sent"] = " "
                        traffic_data["max_bps_sent_str"] = " "
                    results.append(traffic_data)
            else:
                traffic_data = {}
                traffic_data["row_type"] = "host_traffic"
                traffic_data["fc_id"] = " "
                traffic_data["fc_name"] = " "
                traffic_data["threshold"] = " "
                traffic_data["threshold_str"] = " "
                traffic_data["data_loss_threshold"] = " "
                traffic_data["data_loss_threshold_str"] = " "
                traffic_data["total_bytes_received"] = " "
                traffic_data["total_bytes_received_str"] = " "
                traffic_data["total_bytes_data_received"] = " "
                traffic_data["total_bytes_data_received_str"] = " "
                traffic_data["total_packets_received"] = " "
                traffic_data["total_bytes_sent"] = " "
                traffic_data["total_bytes_sent_str"] = " "
                traffic_data["total_bytes_data_sent"] = " "
                traffic_data["total_bytes_data_sent_str"] = " "
                traffic_data["total_packets_sent"] = " "
                traffic_data["data_loss"] = " "
                traffic_data["data_loss_str"] = " "
                traffic_data["threshold_bps"] = " "
                traffic_data["threshold_bps_str"] = " "
                traffic_data["udp_percentage"] = " "
                traffic_data["max_bps_received"] = " "
                traffic_data["max_bps_received_str"] = " "
                traffic_data["max_bps_sent"] = " "
                traffic_data["max_bps_sent_str"] = " "
                # results.append(traffic_data)

            traffic_summary_data = {}
            traffic_summary_data["row_type"] = "host_traffic_summary"
            if tmp_total_bytes > 0:
                traffic_summary_data["total_bytes"] = splunk_utility.convert_bytes_to_string(tmp_total_bytes)
            else:
                traffic_summary_data["total_bytes"] = "0B"
            if tmp_total_bytes_data > 0:
                traffic_summary_data["total_bytes_data"] = splunk_utility.convert_bytes_to_string(tmp_total_bytes_data)
            else:
                traffic_summary_data["total_bytes_data"] = "0B"
            if tmp_total_packets > 0:
                traffic_summary_data["total_packets"] = tmp_total_packets
            else:
                traffic_summary_data["total_packets"] = 0
            results.append(traffic_summary_data)

            flows_list = []
            if "flows" in snapshot_data and snapshot_data["flows"] is not None and "most-recent" in snapshot_data["flows"] and snapshot_data["flows"]["most-recent"] is not None and "flow" in snapshot_data["flows"]["most-recent"] and snapshot_data["flows"]["most-recent"]["flow"] is not None:
                if not isinstance(snapshot_data["flows"]["most-recent"]["flow"], list):
                    snapshot_data["flows"]["most-recent"]["flow"] = [snapshot_data["flows"]["most-recent"]["flow"]]
                for flow in snapshot_data["flows"]["most-recent"]["flow"]:
                    flow["origin-list"] = "most-recent"
                    flows_list.append(flow)
            if "flows" in snapshot_data and snapshot_data["flows"] is not None and "highest-traffic" in snapshot_data["flows"] and snapshot_data["flows"]["highest-traffic"] is not None and "flow" in snapshot_data["flows"]["highest-traffic"] and snapshot_data["flows"]["highest-traffic"]["flow"] is not None:
                if not isinstance(snapshot_data["flows"]["highest-traffic"]["flow"], list):
                    snapshot_data["flows"]["highest-traffic"]["flow"] = [snapshot_data["flows"]["highest-traffic"]["flow"]]
                for flow in snapshot_data["flows"]["highest-traffic"]["flow"]:
                    flow["origin-list"] = "highest-traffic"
                    flows_list.append(flow)
            if len(flows_list) > 0:
                for flow in flows_list:
                    flow_data = {}
                    flow_data["row_type"] = "host_flows"
                    flow_data["origin_list"] = flow["origin-list"]
                    if "connected" in flow:
                        flow_data["connected"] = flow["connected"]
                    else:
                        flow_data["connected"] = " "
                    if "connected-host-group-ids" in flow:
                        flow_data["connected_host_group_ids"] = flow["connected-host-group-ids"]
                        flow_data["connected_host_group_names"] = ""
                        for host_group_id in flow["connected-host-group-ids"].split(","):
                            if int(host_group_id) in host_group_dict:
                                flow_data["connected_host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                            else:
                                flow_data["connected_host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                        flow_data["connected_host_group_names"] = flow_data["connected_host_group_names"][2:]
                    else:
                        flow_data["connected_host_group_ids"] = " "
                        flow_data["connected_host_group_names"] = " "
                    if "start-time" in flow:
                        flow_data["start_time"] = flow["start-time"]
                    else:
                        flow_data["start_time"] = " "
                    if "last-time" in flow:
                        flow_data["last_time"] = flow["last-time"]
                    else:
                        flow_data["last_time"] = " "
                    if "protocol" in flow:
                        flow_data["protocol"] = flow["protocol"]
                    else:
                        flow_data["protocol"] = " "
                    if "service" in flow:
                        flow_data["service"] = flow["service"]
                    else:
                        flow_data["service"] = " "
                    if "service-id" in flow:
                        flow_data["service_id"] = flow["service-id"]
                    else:
                        flow_data["service_id"] = " "
                    flow_data["bytes_total"] = 0
                    if "bytes-sent" in flow:
                        flow_data["bytes_sent"] = flow["bytes-sent"]
                        flow_data["bytes_sent_str"] = splunk_utility.convert_bytes_to_string(flow["bytes-sent"])
                        flow_data["bytes_total"] = int(flow_data["bytes_total"]) + int(flow["bytes-sent"])
                    else:
                        flow_data["bytes_sent"] = " "
                        flow_data["bytes_sent_str"] = " "
                    if "bytes-received" in flow:
                        flow_data["bytes_received"] = flow["bytes-received"]
                        flow_data["bytes_received_str"] = splunk_utility.convert_bytes_to_string(flow["bytes-received"])
                        flow_data["bytes_total"] = int(flow_data["bytes_total"]) + int(flow["bytes-received"])
                    else:
                        flow_data["bytes_received"] = " "
                        flow_data["bytes_received_str"] = " "
                    flow_data["bytes_total_str"] = splunk_utility.convert_bytes_to_string(flow_data["bytes_total"])
                    if flow_data["bytes_sent"] == " " and flow_data["bytes_received"] == " ":
                        flow_data["bytes_total"] = " "
                        flow_data["bytes_total_str"] = " "
                        flow_data["bytes_ratio"] = " "
                    elif flow_data["bytes_sent"] == " ":
                        flow_data["bytes_ratio"] = "0.0%"
                    elif flow_data["bytes_received"] == " ":
                        flow_data["bytes_ratio"] = "100.0%"
                    elif float(flow_data["bytes_total"]) > 0:
                        flow_data["bytes_ratio"] = str(round((float(flow_data["bytes_sent"]) * 100.0) / float(flow_data["bytes_total"]), splunk_utility.number_of_decimal_places)) + "%"
                    else:
                        flow_data["bytes_ratio"] = "0.0%"
                    flow_data["packets_total"] = 0
                    if "pkts-sent" in flow:
                        flow_data["packets_sent"] = flow["pkts-sent"]
                        flow_data["packets_total"] = int(flow_data["packets_total"]) + int(flow["pkts-sent"])
                    else:
                        flow_data["packets_sent"] = " "
                    if "pkts-received" in flow:
                        flow_data["packets_received"] = flow["pkts-received"]
                        flow_data["packets_total"] = int(flow_data["packets_total"]) + int(flow["pkts-received"])
                    else:
                        flow_data["packets_received"] = " "
                    if flow_data["packets_sent"] == " " and flow_data["packets_received"] == " ":
                        flow_data["packets_total"] = " "
                    if "average-bps" in flow:
                        flow_data["average_bps"] = flow["average-bps"]
                        flow_data["average_bps_str"] = splunk_utility.convert_bytes_to_string(flow["average-bps"])
                    else:
                        flow_data["average_bps"] = " "
                        flow_data["average_bps_str"] = " "
                    if "role" in flow:
                        flow_data["role"] = flow["role"]
                    else:
                        flow_data["role"] = " "
                    if "total-conn" in flow:
                        flow_data["total_connections"] = flow["total-conn"]
                    else:
                        flow_data["total_connections"] = " "
                    if "total-retrans" in flow:
                        flow_data["total_retransmissions"] = flow["total-retrans"]
                    else:
                        flow_data["total_retransmissions"] = " "
                    if "min-rtt" in flow:
                        flow_data["min_rtt"] = flow["min-rtt"]
                    else:
                        flow_data["min_rtt"] = " "
                    if "max-rtt" in flow:
                        flow_data["max_rtt"] = flow["max-rtt"]
                    else:
                        flow_data["max_rtt"] = " "
                    if "avg-rtt" in flow:
                        flow_data["avg_rtt"] = flow["avg-rtt"]
                    else:
                        flow_data["avg_rtt"] = " "
                    if "min-srt" in flow:
                        flow_data["min_srt"] = flow["min-srt"]
                    else:
                        flow_data["min_srt"] = " "
                    if "max-srt" in flow:
                        flow_data["max_srt"] = flow["max-srt"]
                    else:
                        flow_data["max_srt"] = " "
                    if "avg-srt" in flow:
                        flow_data["avg_srt"] = flow["avg-srt"]
                    else:
                        flow_data["avg_srt"] = " "
                    results.append(flow_data)
            else:
                for origin_list in ["most-recent", "highest-traffic"]:
                    flow_data = {}
                    flow_data["row_type"] = "host_flows"
                    flow_data["origin_list"] = origin_list
                    flow_data["connected"] = " "
                    flow_data["connected_host_group_ids"] = " "
                    flow_data["connected_host_group_names"] = " "
                    flow_data["start_time"] = " "
                    flow_data["last_time"] = " "
                    flow_data["protocol"] = " "
                    flow_data["service"] = " "
                    flow_data["service_id"] = " "
                    flow_data["bytes_sent"] = " "
                    flow_data["bytes_received"] = " "
                    flow_data["bytes_total"] = " "
                    flow_data["bytes_sent_str"] = " "
                    flow_data["bytes_received_str"] = " "
                    flow_data["bytes_total_str"] = " "
                    flow_data["bytes_ratio"] = " "
                    flow_data["packets_sent"] = " "
                    flow_data["packets_received"] = " "
                    flow_data["packets_total"] = " "
                    flow_data["average_bps"] = " "
                    flow_data["average_bps_str"] = " "
                    flow_data["role"] = " "
                    flow_data["total_connections"] = " "
                    flow_data["total_retransmissions"] = " "
                    flow_data["min_rtt"] = " "
                    flow_data["max_rtt"] = " "
                    flow_data["avg_rtt"] = " "
                    flow_data["min_srt"] = " "
                    flow_data["max_srt"] = " "
                    flow_data["avg_srt"] = " "
                    # results.append(flow_data)


            if "identity-session-list" in snapshot_data and snapshot_data["identity-session-list"] is not None and "identity-session" in snapshot_data["identity-session-list"] and snapshot_data["identity-session-list"]["identity-session"] is not None:
                if not isinstance(snapshot_data["identity-session-list"]["identity-session"], list):
                    snapshot_data["identity-session-list"]["identity-session"] = [snapshot_data["identity-session-list"]["identity-session"]]
                for identity_session in snapshot_data["identity-session-list"]["identity-session"]:
                    identity_session_data = {}
                    identity_session_data["row_type"] = "host_identity_session"
                    if "device-id" in identity_session:
                        identity_session_data["fc_id"] = identity_session["device-id"]
                        if int(identity_session["device-id"]) in fc_map:
                            identity_session_data["fc_name"] = fc_map[int(identity_session["device-id"])]
                        else:
                            identity_session_data["fc_name"] = " "
                    else:
                        identity_session_data["fc_id"] = " "
                        identity_session_data["fc_name"] = " "
                    if "ip-address" in identity_session:
                        identity_session_data["ip_address"] = identity_session["ip-address"]
                    else:
                        identity_session_data["ip_address"] = " "
                    if "host-group-ids" in identity_session:
                        identity_session_data["host_group_ids"] = identity_session["host-group-ids"]
                        identity_session_data["host_group_names"] = ""
                        for host_group_id in identity_session["host-group-ids"].split(","):
                            if int(host_group_id) in host_group_dict:
                                identity_session_data["host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                            else:
                                identity_session_data["host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                        identity_session_data["host_group_names"] = identity_session_data["host_group_names"][2:]
                    else:
                        identity_session_data["host_group_ids"] = " "
                        identity_session_data["host_group_names"] = " "
                    if "host-name" in identity_session:
                        identity_session_data["hostname"] = identity_session["host-name"]
                    else:
                        identity_session_data["hostname"] = " "
                    if "country" in identity_session:
                        identity_session_data["country"] = identity_session["country"]
                    else:
                        identity_session_data["country"] = " "
                    if "start-time" in identity_session:
                        identity_session_data["start_time"] = identity_session["start-time"]
                        identity_session_data["status"] = "Active"
                    else:
                        identity_session_data["start_time"] = " "
                    if "end-time" in identity_session:
                        identity_session_data["end_time"] = identity_session["end-time"]
                        identity_session_data["status"] = "Inactive"
                    else:
                        identity_session_data["end_time"] = " "
                    if "active" in identity_session:
                        if str(identity_session["active"]).lower() == "true":
                            identity_session_data["status"] = "Active"
                        else:
                            identity_session_data["status"] = "Inactive"
                    if "user-name" in identity_session:
                        identity_session_data["username"] = identity_session["user-name"]
                    else:
                        identity_session_data["username"] = " "
                    if "vlan" in identity_session:
                        identity_session_data["vlan"] = identity_session["vlan"]
                    else:
                        identity_session_data["vlan"] = " "
                    if "device-type" in identity_session:
                        identity_session_data["device_type"] = identity_session["device-type"]
                    else:
                        identity_session_data["device_type"] = " "
                    if "ad-domain" in identity_session:
                        identity_session_data["ad_domain"] = identity_session["ad-domain"]
                    else:
                        identity_session_data["ad_domain"] = " "
                    if "vpn-ip" in identity_session:
                        identity_session_data["vpn_ip"] = identity_session["vpn-ip"]
                    else:
                        identity_session_data["vpn_ip"] = " "
                    if "sgt-id" in identity_session:
                        identity_session_data["sgt_id"] = identity_session["sgt-id"]
                    else:
                        identity_session_data["sgt_id"] = " "
                    if "mac-address" in identity_session:
                        if "value" in identity_session["mac-address"]:
                            identity_session_data["mac_address"] = identity_session["mac-address"]["value"]
                        else:
                            identity_session_data["mac_address"] = " "
                        if "vendor" in identity_session["mac-address"]:
                            identity_session_data["mac_address_vendor"] = identity_session["mac-address"]["vendor"]
                        else:
                            identity_session_data["mac_address_vendor"] = " "
                    else:
                        identity_session_data["mac_address"] = " "
                        identity_session_data["mac_address_vendor"] = " "
                    if "network-access-device" in identity_session:
                        if "ip-address" in identity_session["network-access-device"]:
                            identity_session_data["network_access_device_ip"] = identity_session["network-access-device"]["ip-address"]
                        else:
                            identity_session_data["network_access_device_ip"] = " "
                        if "name" in identity_session["network-access-device"]:
                            identity_session_data["network_access_device_name"] = identity_session["network-access-device"]["name"] + " (" + identity_session["network-access-device"]["ip-address"] + ")"
                        elif "ip-address" in identity_session["network-access-device"]:
                            identity_session_data["network_access_device_name"] = identity_session["network-access-device"]["ip-address"]
                        else:
                            identity_session_data["network_access_device_name"] = " "
                        if "interface" in identity_session["network-access-device"]:
                            identity_session_data["network_access_device_interface"] = identity_session["network-access-device"]["interface"]
                        else:
                            identity_session_data["network_access_device_interface"] = " "
                    else:
                        identity_session_data["network_access_device_ip"] = " "
                        identity_session_data["network_access_device_name"] = " "
                        identity_session_data["network_access_device_interface"] = " "
                    if "user-groups" in identity_session:
                        if "identity" in identity_session["user-groups"]:
                            identity_session_data["identity_group"] = identity_session["user-groups"]["identity"]
                        else:
                            identity_session_data["identity_group"] = " "
                        if "security" in identity_session["user-groups"]:
                            identity_session_data["security_group"] = identity_session["user-groups"]["security"]
                        else:
                            identity_session_data["security_group"] = " "
                    else:
                        identity_session_data["identity_group"] = " "
                        identity_session_data["security_group"] = " "
                    results.append(identity_session_data)
            else:
                identity_session_data = {}
                identity_session_data["row_type"] = "host_identity_session"
                identity_session_data["fc_id"] = " "
                identity_session_data["fc_name"] = " "
                identity_session_data["ip_address"] = " "
                identity_session_data["host_group_ids"] = " "
                identity_session_data["host_group_names"] = " "
                identity_session_data["hostname"] = " "
                identity_session_data["country"] = " "
                identity_session_data["start_time"] = " "
                identity_session_data["end_time"] = " "
                identity_session_data["status"] = " "
                identity_session_data["username"] = " "
                identity_session_data["vlan"] = " "
                identity_session_data["device_type"] = " "
                identity_session_data["ad_domain"] = " "
                identity_session_data["vpn_ip"] = " "
                identity_session_data["sgt_id"] = " "
                identity_session_data["mac_address"] = " "
                identity_session_data["mac_address_vendor"] = " "
                identity_session_data["network_access_device_ip"] = " "
                identity_session_data["network_access_device_name"] = " "
                identity_session_data["network_access_device_interface"] = " "
                identity_session_data["identity_group"] = " "
                identity_session_data["security_group"] = " "
                # results.append(identity_session_data)


            if "user-activity-list" in snapshot_data and snapshot_data["user-activity-list"] is not None and "user-activity" in snapshot_data["user-activity-list"] and snapshot_data["user-activity-list"]["user-activity"] is not None:
                if not isinstance(snapshot_data["user-activity-list"]["user-activity"], list):
                    snapshot_data["user-activity-list"]["user-activity"] = [snapshot_data["user-activity-list"]["user-activity"]]
                for user_activity in snapshot_data["user-activity-list"]["user-activity"]:
                    user_activity_data = {}
                    user_activity_data["row_type"] = "host_user_activity"
                    if "device-id" in user_activity:
                        user_activity_data["fc_id"] = user_activity["device-id"]
                        if int(user_activity["device-id"]) in fc_map:
                            user_activity_data["fc_name"] = fc_map[int(user_activity["device-id"])]
                        else:
                            user_activity_data["fc_name"] = " "
                    else:
                        user_activity_data["fc_id"] = " "
                        user_activity_data["fc_name"] = " "
                    if "ip-address" in user_activity:
                        user_activity_data["ip_address"] = user_activity["ip-address"]
                    else:
                        user_activity_data["ip_address"] = " "
                    if "host-group-ids" in user_activity:
                        user_activity_data["host_group_ids"] = user_activity["host-group-ids"]
                        user_activity_data["host_group_names"] = ""
                        for host_group_id in user_activity["host-group-ids"].split(","):
                            if int(host_group_id) in host_group_dict:
                                user_activity_data["host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                            else:
                                user_activity_data["host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                        user_activity_data["host_group_names"] = user_activity_data["host_group_names"][2:]
                    else:
                        user_activity_data["host_group_ids"] = " "
                        user_activity_data["host_group_names"] = " "
                    if "host-name" in user_activity:
                        user_activity_data["hostname"] = user_activity["host-name"]
                    else:
                        user_activity_data["hostname"] = " "
                    if "country" in user_activity:
                        user_activity_data["country"] = user_activity["country"]
                    else:
                        user_activity_data["country"] = " "
                    if "start-time" in user_activity:
                        user_activity_data["start_time"] = user_activity["start-time"]
                    else:
                        user_activity_data["start_time"] = " "
                    if "end-time" in user_activity:
                        user_activity_data["end_time"] = user_activity["end-time"]
                    else:
                        user_activity_data["end_time"] = " "
                    if "active" in user_activity:
                        user_activity_data["active"] = user_activity["active"]
                    else:
                        user_activity_data["active"] = " "
                    if "username" in user_activity:
                        user_activity_data["username"] = user_activity["username"]
                    else:
                        user_activity_data["username"] = " "
                    ### MORE TO ADD LATER ###
                    results.append(user_activity_data)
            else:
                user_activity_data = {}
                user_activity_data["row_type"] = "host_user_activity"
                user_activity_data["fc_id"] = " "
                user_activity_data["fc_name"] = " "
                user_activity_data["ip_address"] = " "
                user_activity_data["host_group_ids"] = " "
                user_activity_data["host_group_names"] = " "
                user_activity_data["hostname"] = " "
                user_activity_data["country"] = " "
                user_activity_data["start_time"] = " "
                user_activity_data["end_time"] = " "
                user_activity_data["active"] = " "
                user_activity_data["username"] = " "
                # results.append(user_activity_data)


            if "dhcp-lease-list" in snapshot_data and snapshot_data["dhcp-lease-list"] is not None and "dhcp-lease" in snapshot_data["dhcp-lease-list"] and snapshot_data["dhcp-lease-list"]["dhcp-lease"] is not None:
                if not isinstance(snapshot_data["dhcp-lease-list"]["dhcp-lease"], list):
                    snapshot_data["dhcp-lease-list"]["dhcp-lease"] = [snapshot_data["dhcp-lease-list"]["dhcp-lease"]]
                for dhcp_lease in snapshot_data["dhcp-lease-list"]["dhcp-lease"]:
                    dhcp_lease_data = {}
                    dhcp_lease_data["row_type"] = "host_dhcp_lease"
                    if "device-id" in dhcp_lease:
                        dhcp_lease_data["fc_id"] = dhcp_lease["device-id"]
                        if int(dhcp_lease["device-id"]) in fc_map:
                            dhcp_lease_data["fc_name"] = fc_map[int(dhcp_lease["device-id"])]
                        else:
                            dhcp_lease_data["fc_name"] = " "
                    else:
                        dhcp_lease_data["fc_id"] = " "
                        dhcp_lease_data["fc_name"] = " "
                    if "ip-address" in dhcp_lease:
                        dhcp_lease_data["ip_address"] = dhcp_lease["ip-address"]
                    else:
                        dhcp_lease_data["ip_address"] = " "
                    if "host-group-ids" in dhcp_lease:
                        dhcp_lease_data["host_group_ids"] = dhcp_lease["host-group-ids"]
                        dhcp_lease_data["host_group_names"] = ""
                        for host_group_id in dhcp_lease["host-group-ids"].split(","):
                            if int(host_group_id) in host_group_dict:
                                dhcp_lease_data["host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                            else:
                                dhcp_lease_data["host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                        dhcp_lease_data["host_group_names"] = dhcp_lease_data["host_group_names"][2:]
                    else:
                        dhcp_lease_data["host_group_ids"] = " "
                        dhcp_lease_data["host_group_names"] = " "
                    if "host-name" in dhcp_lease:
                        dhcp_lease_data["hostname"] = dhcp_lease["host-name"]
                    else:
                        dhcp_lease_data["hostname"] = " "
                    if "country" in dhcp_lease:
                        dhcp_lease_data["country"] = dhcp_lease["country"]
                    else:
                        dhcp_lease_data["country"] = " "
                    if "start-time" in dhcp_lease:
                        dhcp_lease_data["start_time"] = dhcp_lease["start-time"]
                    else:
                        dhcp_lease_data["start_time"] = " "
                    if "end-time" in dhcp_lease:
                        dhcp_lease_data["end_time"] = dhcp_lease["end-time"]
                    else:
                        dhcp_lease_data["end_time"] = " "
                    if "active" in dhcp_lease:
                        dhcp_lease_data["active"] = dhcp_lease["active"]
                    else:
                        dhcp_lease_data["active"] = " "
                    if "server" in dhcp_lease and "name" in dhcp_lease["server"]:
                        dhcp_lease_data["assigning_server"] = dhcp_lease["server"]["name"]
                    else:
                        dhcp_lease_data["assigning_server"] = " "
                    if "client" in dhcp_lease and "mac-address" in dhcp_lease["client"]:
                        dhcp_lease_data["mac_address"] = dhcp_lease["client"]["mac-address"]
                    else:
                        dhcp_lease_data["mac_address"] = " "
                    if "client" in dhcp_lease and "vendor" in dhcp_lease["client"]:
                        dhcp_lease_data["mac_vendor"] = dhcp_lease["client"]["vendor"]
                    else:
                        dhcp_lease_data["mac_vendor"] = " "
                    results.append(dhcp_lease_data)
            else:
                dhcp_lease_data = {}
                dhcp_lease_data["row_type"] = "host_dhcp_lease"
                dhcp_lease_data["fc_id"] = " "
                dhcp_lease_data["fc_name"] = " "
                dhcp_lease_data["ip_address"] = " "
                dhcp_lease_data["host_group_ids"] = " "
                dhcp_lease_data["host_group_names"] = " "
                dhcp_lease_data["hostname"] = " "
                dhcp_lease_data["country"] = " "
                dhcp_lease_data["start_time"] = " "
                dhcp_lease_data["end_time"] = " "
                dhcp_lease_data["active"] = " "
                dhcp_lease_data["assigning_server"] = " "
                dhcp_lease_data["mac_address"] = " "
                dhcp_lease_data["mac_vendor"] = " "
                # results.append(dhcp_lease_data)


            if "host-note-list" in snapshot_data and snapshot_data["host-note-list"] is not None and "host-note" in snapshot_data["host-note-list"] and snapshot_data["host-note-list"]["host-note"] is not None:
                if not isinstance(snapshot_data["host-note-list"]["host-note"], list):
                    snapshot_data["host-note-list"]["host-note"] = [snapshot_data["host-note-list"]["host-note"]]
                for host_note in snapshot_data["host-note-list"]["host-note"]:
                    host_note_data = {}
                    host_note_data["row_type"] = "host_notes"
                    if "ip-address" in host_note:
                        host_note_data["ip_address"] = host_note["ip-address"]
                    else:
                        host_note_data["ip_address"] = " "
                    if "host-group-ids" in host_note:
                        host_note_data["host_group_ids"] = host_note["host-group-ids"]
                        host_note_data["host_group_names"] = ""
                        for host_group_id in host_note["host-group-ids"].split(","):
                            if int(host_group_id) in host_group_dict:
                                host_note_data["host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                            else:
                                host_note_data["host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                        host_note_data["host_group_names"] = host_note_data["host_group_names"][2:]
                    else:
                        host_note_data["host_group_ids"] = " "
                        host_note_data["host_group_names"] = " "
                    if "country" in host_note:
                        host_note_data["country"] = host_note["country"]
                    else:
                        host_note_data["country"] = " "
                    if "time" in host_note:
                        host_note_data["time"] = host_note["time"]
                    else:
                        host_note_data["time"] = " "
                    if "user" in host_note:
                        host_note_data["user"] = host_note["user"]
                    else:
                        host_note_data["user"] = " "
                    if "#text" in host_note:
                        host_note_data["note"] = host_note["#text"]
                    else:
                        host_note_data["note"] = " "
                    ### MORE TO ADD LATER ###
                    results.append(host_note_data)
            else:
                host_note_data = {}
                host_note_data["row_type"] = "host_notes"
                host_note_data["ip_address"] = " "
                host_note_data["host_group_ids"] = " "
                host_note_data["host_group_names"] = " "
                host_note_data["country"] = " "
                host_note_data["time"] = " "
                host_note_data["user"] = " "
                host_note_data["note"] = " "
                # results.append(host_note_data)


            if "exporters" in snapshot_data and snapshot_data["exporters"] is not None and "closest-interface-list" in snapshot_data["exporters"] and snapshot_data["exporters"]["closest-interface-list"] is not None and "closest-interface" in snapshot_data["exporters"]["closest-interface-list"] and snapshot_data["exporters"]["closest-interface-list"]["closest-interface"] is not None:
                if not isinstance(snapshot_data["exporters"]["closest-interface-list"]["closest-interface"], list):
                    snapshot_data["exporters"]["closest-interface-list"]["closest-interface"] = [snapshot_data["exporters"]["closest-interface-list"]["closest-interface"]]
                for interface in snapshot_data["exporters"]["closest-interface-list"]["closest-interface"]:
                    interface_data = {}
                    interface_data["row_type"] = "host_interface_closest"
                    if "device-id" in interface:
                        interface_data["fc_id"] = interface["device-id"]
                        if int(interface["device-id"]) in fc_map:
                            interface_data["fc_name"] = fc_map[int(interface["device-id"])]
                        else:
                            interface_data["fc_name"] = " "
                    else:
                        interface_data["fc_id"] = " "
                        interface_data["fc_name"] = " "
                    if "exporter-ip" in interface:
                        interface_data["exporter_ip"] = interface["exporter-ip"]
                    else:
                        interface_data["exporter_ip"] = " "
                    if "if-index" in interface:
                        interface_data["if_index"] = "ifIndex-" + str(interface["if-index"])
                    else:
                        interface_data["if_index"] = " "
                    if "confidence" in interface:
                        interface_data["confidence"] = interface["confidence"]
                        interface_data["confidence_str"] = interface["confidence"] + "%"
                    else:
                        interface_data["confidence"] = " "
                        interface_data["confidence_str"] = " "
                    results.append(interface_data)
            else:
                interface_data = {}
                interface_data["row_type"] = "host_interface_closest"
                interface_data["fc_id"] = " "
                interface_data["fc_name"] = " "
                interface_data["exporter_ip"] = " "
                interface_data["if_index"] = " "
                interface_data["confidence"] = " "
                interface_data["confidence_str"] = " "
                # results.append(interface_data)


            interface_list = []
            if "exporters" in snapshot_data and snapshot_data["exporters"] is not None and "active-source-list" in snapshot_data["exporters"] and snapshot_data["exporters"]["active-source-list"] is not None and "interface-status" in snapshot_data["exporters"]["active-source-list"] and snapshot_data["exporters"]["active-source-list"]["interface-status"] is not None:
                if not isinstance(snapshot_data["exporters"]["active-source-list"]["interface-status"], list):
                    snapshot_data["exporters"]["active-source-list"]["interface-status"] = [snapshot_data["exporters"]["active-source-list"]["interface-status"]]
                for interface in snapshot_data["exporters"]["active-source-list"]["interface-status"]:
                    interface["row_type"] = "host_interface_active_source"
                    interface_list.append(interface)
            if "exporters" in snapshot_data and snapshot_data["exporters"] is not None and "active-dest-list" in snapshot_data["exporters"] and snapshot_data["exporters"]["active-dest-list"] is not None and "interface-status" in snapshot_data["exporters"]["active-dest-list"] and snapshot_data["exporters"]["active-dest-list"]["interface-status"] is not None:
                if not isinstance(snapshot_data["exporters"]["active-dest-list"]["interface-status"], list):
                    snapshot_data["exporters"]["active-dest-list"]["interface-status"] = [snapshot_data["exporters"]["active-dest-list"]["interface-status"]]
                for interface in snapshot_data["exporters"]["active-dest-list"]["interface-status"]:
                    interface["row_type"] = "host_interface_active_destination"
                    interface_list.append(interface)
            if "exporters" in snapshot_data and snapshot_data["exporters"] is not None and "today-list" in snapshot_data["exporters"] and snapshot_data["exporters"]["today-list"] is not None and "interface-status" in snapshot_data["exporters"]["today-list"] and snapshot_data["exporters"]["today-list"]["interface-status"] is not None:
                if not isinstance(snapshot_data["exporters"]["today-list"]["interface-status"], list):
                    snapshot_data["exporters"]["today-list"]["interface-status"] = [snapshot_data["exporters"]["today-list"]["interface-status"]]
                for interface in snapshot_data["exporters"]["today-list"]["interface-status"]:
                    interface["row_type"] = "host_interface_today"
                    interface_list.append(interface)


            if len(interface_list) > 0:
                for interface in interface_list:
                    interface_data = {}
                    interface_data["row_type"] = interface["row_type"]
                    interface_data["direction"] = "Inbound"
                    if "device-id" in interface:
                        interface_data["fc_id"] = interface["device-id"]
                        if int(interface["device-id"]) in fc_map:
                            interface_data["fc_name"] = fc_map[int(interface["device-id"])]
                        else:
                            interface_data["fc_name"] = " "
                    else:
                        interface_data["fc_id"] = " "
                        interface_data["fc_name"] = " "
                    if "exporter-ip" in interface:
                        interface_data["exporter_ip"] = interface["exporter-ip"]
                    else:
                        interface_data["exporter_ip"] = " "
                    if "if-index" in interface:
                        interface_data["if_index"] = "ifIndex-" + str(interface["if-index"])
                    else:
                        interface_data["if_index"] = " "
                    if "inbound" in interface:
                        if "inbound" in interface and "current-bps" in interface["inbound"]:
                            interface_data["current_bps"] = interface["inbound"]["current-bps"]
                            interface_data["current_bps_str"] = splunk_utility.convert_bytes_to_string(interface["inbound"]["current-bps"])
                        else:
                            interface_data["current_bps"] = " "
                            interface_data["current_bps_str"] = " "
                        if "inbound" in interface and "maximum-bps" in interface["inbound"]:
                            interface_data["maximum_bps"] = interface["inbound"]["maximum-bps"]
                            interface_data["maximum_bps_str"] = splunk_utility.convert_bytes_to_string(interface["inbound"]["maximum-bps"])
                        else:
                            interface_data["maximum_bps"] = " "
                            interface_data["maximum_bps_str"] = " "
                        if "inbound" in interface and "average-bps" in interface["inbound"]:
                            interface_data["average_bps"] = interface["inbound"]["average-bps"]
                            interface_data["average_bps_str"] = splunk_utility.convert_bytes_to_string(interface["inbound"]["average-bps"])
                        else:
                            interface_data["average_bps"] = " "
                            interface_data["average_bps_str"] = " "
                        if "inbound" in interface and "current-pps" in interface["inbound"]:
                            interface_data["current_pps"] = interface["inbound"]["current-pps"]
                        else:
                            interface_data["current_pps"] = " "
                        if "inbound" in interface and "maximum-pps" in interface["inbound"]:
                            interface_data["maximum_pps"] = interface["inbound"]["maximum-pps"]
                        else:
                            interface_data["maximum_pps"] = " "
                        if "inbound" in interface and "average-pps" in interface["inbound"]:
                            interface_data["average_pps"] = interface["inbound"]["average-pps"]
                        else:
                            interface_data["average_pps"] = " "
                        if "inbound" in interface and "current-util" in interface["inbound"]:
                            interface_data["current_util"] = interface["inbound"]["current-util"]
                            interface_data["current_util_str"] = str(round(float(interface["inbound"]["current-util"]), splunk_utility.number_of_decimal_places)) + "%"
                        else:
                            interface_data["current_util"] = " "
                            interface_data["current_util_str"] = " "
                        if "inbound" in interface and "maximum-util" in interface["inbound"]:
                            interface_data["maximum_util"] = interface["inbound"]["maximum-util"]
                            interface_data["maximum_util_str"] = str(round(float(interface["inbound"]["maximum-util"]), splunk_utility.number_of_decimal_places)) + "%"
                        else:
                            interface_data["maximum_util"] = " "
                            interface_data["maximum_util_str"] = " "
                        results.append(interface_data)
                    elif "outbound" in interface:
                        interface_data["current_bps"] = 0
                        interface_data["maximum_bps"] = 0
                        interface_data["average_bps"] = 0
                        interface_data["current_bps_str"] = "0"
                        interface_data["maximum_bps_str"] = "0"
                        interface_data["average_bps_str"] = "0"
                        interface_data["current_pps"] = 0
                        interface_data["maximum_pps"] = 0
                        interface_data["average_pps"] = 0
                        interface_data["current_util"] = 0.0
                        interface_data["maximum_util"] = 0.0
                        interface_data["current_util_str"] = "0.0%"
                        interface_data["maximum_util_str"] = "0.0%"
                        results.append(interface_data)

                    interface_data = {}
                    interface_data["row_type"] = interface["row_type"]
                    interface_data["direction"] = "Outbound"
                    if "device-id" in interface:
                        interface_data["fc_id"] = interface["device-id"]
                        if int(interface["device-id"]) in fc_map:
                            interface_data["fc_name"] = fc_map[int(interface["device-id"])]
                        else:
                            interface_data["fc_name"] = " "
                    else:
                        interface_data["fc_id"] = " "
                        interface_data["fc_name"] = " "
                    if "exporter-ip" in interface:
                        interface_data["exporter_ip"] = interface["exporter-ip"]
                    else:
                        interface_data["exporter_ip"] = " "
                    if "if-index" in interface:
                        interface_data["if_index"] = "ifIndex-" + str(interface["if-index"])
                    else:
                        interface_data["if_index"] = " "
                    if "outbound" in interface:
                        if "outbound" in interface and "current-bps" in interface["outbound"]:
                            interface_data["current_bps"] = interface["outbound"]["current-bps"]
                            interface_data["current_bps_str"] = splunk_utility.convert_bytes_to_string(interface["outbound"]["current-bps"])
                        else:
                            interface_data["current_bps"] = " "
                            interface_data["current_bps_str"] = " "
                        if "outbound" in interface and "maximum-bps" in interface["outbound"]:
                            interface_data["maximum_bps"] = interface["outbound"]["maximum-bps"]
                            interface_data["maximum_bps_str"] = splunk_utility.convert_bytes_to_string(interface["outbound"]["maximum-bps"])
                        else:
                            interface_data["maximum_bps"] = " "
                            interface_data["maximum_bps_str"] = " "
                        if "outbound" in interface and "average-bps" in interface["outbound"]:
                            interface_data["average_bps"] = interface["outbound"]["average-bps"]
                            interface_data["average_bps_str"] = splunk_utility.convert_bytes_to_string(interface["outbound"]["average-bps"])
                        else:
                            interface_data["average_bps"] = " "
                            interface_data["average_bps_str"] = " "
                        if "outbound" in interface and "current-pps" in interface["outbound"]:
                            interface_data["current_pps"] = interface["outbound"]["current-pps"]
                        else:
                            interface_data["current_pps"] = " "
                        if "outbound" in interface and "maximum-pps" in interface["outbound"]:
                            interface_data["maximum_pps"] = interface["outbound"]["maximum-pps"]
                        else:
                            interface_data["maximum_pps"] = " "
                        if "outbound" in interface and "average-pps" in interface["outbound"]:
                            interface_data["average_pps"] = interface["outbound"]["average-pps"]
                        else:
                            interface_data["average_pps"] = " "
                        if "outbound" in interface and "current-util" in interface["outbound"]:
                            interface_data["current_util"] = interface["outbound"]["current-util"]
                            interface_data["current_util_str"] = str(round(float(interface["outbound"]["current-util"]), splunk_utility.number_of_decimal_places)) + "%"
                        else:
                            interface_data["current_util"] = " "
                            interface_data["current_util_str"] = " "
                        if "outbound" in interface and "maximum-util" in interface["outbound"]:
                            interface_data["maximum_util"] = interface["outbound"]["maximum-util"]
                            interface_data["maximum_util_str"] = str(round(float(interface["outbound"]["maximum-util"]), splunk_utility.number_of_decimal_places)) + "%"
                        else:
                            interface_data["maximum_util"] = " "
                            interface_data["maximum_util_str"] = " "
                        results.append(interface_data)
                    elif "inbound" in interface:
                        interface_data["current_bps"] = 0
                        interface_data["maximum_bps"] = 0
                        interface_data["average_bps"] = 0
                        interface_data["current_bps_str"] = "0"
                        interface_data["maximum_bps_str"] = "0"
                        interface_data["average_bps_str"] = "0"
                        interface_data["current_pps"] = 0
                        interface_data["maximum_pps"] = 0
                        interface_data["average_pps"] = 0
                        interface_data["current_util"] = 0.0
                        interface_data["maximum_util"] = 0.0
                        interface_data["current_util_str"] = "0.0%"
                        interface_data["maximum_util_str"] = "0.0%"
                        results.append(interface_data)

            else:
                interface_data = {}
                interface_data["row_type"] = "host_interface_active_source"
                interface_data["direction"] = " "
                interface_data["fc_id"] = " "
                interface_data["fc_name"] = " "
                interface_data["exporter_ip"] = " "
                interface_data["if_index"] = " "
                interface_data["current_bps"] = " "
                interface_data["maximum_bps"] = " "
                interface_data["average_bps"] = " "
                interface_data["current_bps_str"] = " "
                interface_data["maximum_bps_str"] = " "
                interface_data["average_bps_str"] = " "
                interface_data["current_pps"] = " "
                interface_data["maximum_pps"] = " "
                interface_data["average_pps"] = " "
                interface_data["current_util"] = " "
                interface_data["maximum_util"] = " "
                interface_data["current_util_str"] = " "
                interface_data["maximum_util_str"] = " "
                # results.append(interface_data)
                interface_data = {}
                interface_data["row_type"] = "host_interface_active_destination"
                interface_data["direction"] = " "
                interface_data["fc_id"] = " "
                interface_data["fc_name"] = " "
                interface_data["exporter_ip"] = " "
                interface_data["if_index"] = " "
                interface_data["current_bps"] = " "
                interface_data["maximum_bps"] = " "
                interface_data["average_bps"] = " "
                interface_data["current_bps_str"] = " "
                interface_data["maximum_bps_str"] = " "
                interface_data["average_bps_str"] = " "
                interface_data["current_pps"] = " "
                interface_data["maximum_pps"] = " "
                interface_data["average_pps"] = " "
                interface_data["current_util"] = " "
                interface_data["maximum_util"] = " "
                interface_data["current_util_str"] = " "
                interface_data["maximum_util_str"] = " "
                # results.append(interface_data)
                interface_data = {}
                interface_data["row_type"] = "host_interface_today"
                interface_data["direction"] = " "
                interface_data["fc_id"] = " "
                interface_data["fc_name"] = " "
                interface_data["exporter_ip"] = " "
                interface_data["if_index"] = " "
                interface_data["current_bps"] = " "
                interface_data["maximum_bps"] = " "
                interface_data["average_bps"] = " "
                interface_data["current_bps_str"] = " "
                interface_data["maximum_bps_str"] = " "
                interface_data["average_bps_str"] = " "
                interface_data["current_pps"] = " "
                interface_data["maximum_pps"] = " "
                interface_data["average_pps"] = " "
                interface_data["current_util"] = " "
                interface_data["maximum_util"] = " "
                interface_data["current_util_str"] = " "
                interface_data["maximum_util_str"] = " "
                # results.append(interface_data)
                interface_data = {}


        if host_report_data is not None:
            country_data = {}
            country_data["row_type"] = "host_geo"
            if "country" in host_report_data and host_report_data["country"] is not None:
                if "code" in host_report_data["country"] and host_report_data["country"]["code"] is not None:
                    country_data["country_code"] = host_report_data["country"]["code"]
                if "name" in host_report_data["country"] and host_report_data["country"]["name"] is not None:
                    country_data["country_name"] = host_report_data["country"]["name"]
            if "geoLocation" in host_report_data and host_report_data["geoLocation"] is not None:
                if "address" in host_report_data["geoLocation"] and host_report_data["geoLocation"]["address"] is not None:
                    country_data["country_address"] = host_report_data["geoLocation"]["address"]
            if len(country_data) > 1:
                results.append(country_data)
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

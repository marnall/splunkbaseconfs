# ==========================================================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# get_top_ports.py script for use with Splunk enterprise to fetch top peers
# from StealthWatch using the RESTx appliance REST API extension service
# ==========================================================================================================

# Usage: |securityevents earliest=<earliest> latest=<latest> [subject_ip=<subject_ip>] [subject_host_group_id=<subject_host_group_id>] [subject_orientation=<subject_orientation>]
#            [peer_ip=<peer_ip>] [peer_host_group_id=<peer_host_group_id>] [security_event_type_id_list=<security,event,type,id,list>] [ports_list=<ports,list>] [hit_count_low_value=<hit_count_low_value>] [hit_count_high_value=<hit_count_high_value>]
#            [ci_points_low_value=<ci_points_low_value>] [ci_points_high_value=<ci_points_high_value>] [filter_by=<filter_by>] [flow_collector_list=<flow,collector,list>] [max_rows=<max_rows>] [domain_id=<domain_id>] [smc_ip=<smc_ip>]


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
def process_row(row, host_group_dict, protocol_map, service_definitions, security_event_types, fc_map):
    this_row = {}
    details_omit_list = ["targetIPAddress", "flow@flow_id", "flow@event_port",
                         "flow@protocol", "sourceIPAddress", "flow@source_port", "flow@target_port", "points", "flow@service",
                         "baseline@baseline", "baseline@tolerance", "baseline@current_value", "baseline@threshold",
                         "target_host@policy_id", "source_host@policy_id", "target_host@mac_address", "source_host@mac_address",
                         "target_host@username", "source_host@username"]
    if "device-id" in row and row["device-id"] is not None:
        this_row["fc_id"] = row["device-id"]
        if int(row["device-id"]) in fc_map:
            this_row["fc_name"] = fc_map[int(row["device-id"])]
        else:
            this_row["fc_name"] = " "
    else:
        this_row["fc_id"] = " "
        this_row["fc_name"] = " "
    if "last-time" in row and row["last-time"] is not None:
        this_row["last_time"] = row["last-time"]
    else:
        this_row["last_time"] = " "
    if "start-time" in row and row["start-time"] is not None:
        this_row["start_time"] = row["start-time"]
    else:
        this_row["start_time"] = " "
    if "details-list" in row and row["details-list"] is not None and "details" in row["details-list"] and \
            row["details-list"]["details"]:
        if not isinstance(row["details-list"]["details"], list):
            row["details-list"]["details"] = [row["details-list"]["details"]]
        for detail in row["details-list"]["details"]:
            if "type" in detail:
                this_row["event_type_id"] = detail["type"]
                if int(detail["type"]) in security_event_types:
                    this_row["event_type_name"] = security_event_types[int(detail["type"])]
                    if "port" in detail:
                        this_row["event_type_name"] += "-" + str(detail["port"])
                else:
                    this_row["event_type_name"] = "Unknown Event Type (ID: " + str(detail["type"]) + ")"
            else:
                this_row["event_type_id"] = " "
                this_row["event_type_name"] = " "
            if "hit-count" in detail:
                this_row["hit_count"] = detail["hit-count"]
            else:
                this_row["hit_count"] = " "
            if "ci-points" in row:
                this_row["ci_points"] = row["ci-points"]
            elif "ci-points" in detail:
                this_row["ci_points"] = detail["ci-points"]
            else:
                this_row["ci_points"] = " "
            if "port" in detail:
                this_row["port"] = detail["port"]
            else:
                this_row["port"] = " "
    if "source" in row and row["source"] is not None:
        if "ip-address" in row["source"]:
            if row["source"]["ip-address"] == "0.0.0.0":
                this_row["source_ip"] = "Multiple Hosts"
            else:
                this_row["source_ip"] = row["source"]["ip-address"]
                # if this_row["source_ip"].endswith(".0.0"):
                #     this_row["source_ip"] = this_row["source_ip"] + "/16"
                # elif this_row["source_ip"].endswith(".0"):
                #     this_row["source_ip"] = this_row["source_ip"] + "/24"
        else:
            this_row["source_ip"] = " "
        if "host-group-ids" in row["source"]:
            if row["source"]["ip-address"] == "0.0.0.0":
                this_row["source_host_group_ids"] = " "
                this_row["source_host_group_names"] = " "
            else:
                this_row["source_host_group_ids"] = row["source"]["host-group-ids"]
                this_row["source_host_group_names"] = ""
                for host_group_id in row["source"]["host-group-ids"].split(","):
                    if int(host_group_id) in host_group_dict:
                        this_row["source_host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                    else:
                        this_row["source_host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                this_row["source_host_group_names"] = this_row["source_host_group_names"][2:]
        else:
            this_row["source_host_group_ids"] = " "
            this_row["source_host_group_names"] = " "
        if "host-name" in row["source"]:
            this_row["source_hostname"] = row["source"]["host-name"]
        else:
            this_row["source_hostname"] = " "
    else:
        this_row["source_ip"] = " "
        this_row["source_host_group_ids"] = " "
        this_row["source_host_group_names"] = " "
        this_row["source_hostname"] = " "
    if "target" in row and row["target"] is not None:
        if "ip-address" in row["target"]:
            if row["target"]["ip-address"] == "0.0.0.0":
                this_row["target_ip"] = "Multiple Hosts"
            else:
                this_row["target_ip"] = row["target"]["ip-address"]
                if this_row["target_ip"].endswith(".0.0") and "scan" in this_row["event_type_name"].lower():
                    this_row["target_ip"] = this_row["target_ip"] + "/16"
                elif this_row["target_ip"].endswith(".0") and "scan" in this_row["event_type_name"].lower():
                    this_row["target_ip"] = this_row["target_ip"] + "/24"
        else:
            this_row["target_ip"] = " "
        if "host-group-ids" in row["target"]:
            if row["target"]["ip-address"] == "0.0.0.0":
                this_row["target_host_group_ids"] = " "
                this_row["target_host_group_names"] = " "
            else:
                this_row["target_host_group_ids"] = row["target"]["host-group-ids"]
                this_row["target_host_group_names"] = ""
                for host_group_id in row["target"]["host-group-ids"].split(","):
                    if int(host_group_id) in host_group_dict:
                        this_row["target_host_group_names"] += "; " + str(host_group_dict[int(host_group_id)])
                    else:
                        this_row["target_host_group_names"] += "; [Unknown Host Group ID: " + str(host_group_id) + "]"
                this_row["target_host_group_names"] = this_row["target_host_group_names"][2:]
        else:
            this_row["target_host_group_ids"] = " "
            this_row["target_host_group_names"] = " "
        if "host-name" in row["target"]:
            this_row["target_hostname"] = row["target"]["host-name"]
        else:
            this_row["target_hostname"] = " "
    else:
        this_row["target_ip"] = " "
        this_row["target_host_group_ids"] = " "
        this_row["target_host_group_names"] = " "
        this_row["target_hostname"] = " "


    if "security-event-details" in row and row["security-event-details"] is not None and "security-event-detail" in row["security-event-details"] and \
            row["security-event-details"]["security-event-detail"]:
        if not isinstance(row["security-event-details"]["security-event-detail"], list):
            row["security-event-details"]["security-event-detail"] = [event["security-event-details"]["security-event-detail"]]
        details_string = ""
        for detail in row["security-event-details"]["security-event-detail"]:
            if detail["value"] is not None and len(detail["value"]) > 0:
                if detail["key"] == "flow@service" and len(detail["value"].strip()) > 0 and detail["value"] != "60000":
                    this_row["serviceId"] = detail["value"]
                    this_service_id = str(detail["value"]).strip()
                    if this_service_id in list(service_definitions.keys()):
                        this_row["serviceName"] = service_definitions[this_service_id]
                    elif len(this_service_id) == 5 and this_service_id.startswith("6"):
                        this_service_id = this_service_id[1:]
                        while this_service_id.startswith("0"):
                            this_service_id = this_service_id[1:]
                        if str(this_service_id) in list(protocol_map.keys()):
                            this_row["serviceName"] = protocol_map[str(this_service_id)]
                        else:
                            this_row["serviceName"] = "Protocol " + this_service_id
                elif detail["key"] == "flow@source_is_server":
                    if detail["value"] == "0":
                        this_row["sourceIsServer"] = "Client"
                    elif detail["value"] == "1":
                        this_row["sourceIsServer"] = "Server"
                elif detail["key"] == "points":
                    this_row["points"] = int(detail["value"])
                elif detail["key"] == "source_host@mac_address" and len("source_host@mac_address") > 0:
                    this_row["source_mac"] = detail["value"]
                elif detail["key"] == "target_host@mac_address" and len("target_host@mac_address") > 0:
                    this_row["target_mac"] = detail["value"]
                elif detail["key"] == "source_host@username" and len("source_host@username") > 0:
                    this_row["source_username"] = detail["value"]
                elif detail["key"] == "target_host@username" and len("target_host@username") > 0:
                    this_row["target_username"] = detail["value"]
                elif detail["key"] not in details_omit_list:
                    details_string += "; " + detail["key"].replace("category_points@", "") + "=\"" + detail["value"] + "\""
        if len(details_string) > 0:
            this_row["details"] = details_string[2:]

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
    subject_ip = kwargs.get('subject_ip')
    subject_host_group_id = kwargs.get('subject_host_group_id')
    subject_orientation = kwargs.get('subject_orientation')
    peer_ip = kwargs.get('peer_ip')
    peer_host_group_id = kwargs.get('peer_host_group_id')
    security_event_type_id_list = kwargs.get('security_event_type_id_list')
    ports_list = kwargs.get('ports_list')
    hit_count_low_value = kwargs.get('hit_count_low_value')
    hit_count_high_value = kwargs.get('hit_count_high_value')
    ci_points_low_value = kwargs.get('ci_points_low_value')
    ci_points_high_value = kwargs.get('ci_points_high_value')
    filter_by = kwargs.get('filter_by')
    flow_collector_list = kwargs.get('flow_collector_list')
    max_rows = kwargs.get('max_rows')
    domain_id = kwargs.get('domain_id')
    smc_ip = kwargs.get('smc_ip')

    if earliest is None or latest is None:
        logger.error("Missing required arguments")
        logger.error("Aborting RESTx API process")
        # Following line calls sys.exit()
        splunk.Intersplunk.parseError(
            "Missing required arguments! (Usage: |securityevents earliest=<earliest> latest=<latest> [subject_ip=<subject_ip>] [subject_host_group_id=<subject_host_group_id>] [subject_orientation=<subject_orientation>]"
            " [peer_ip=<peer_ip>] [peer_host_group_id=<peer_host_group_id>] [security_event_type_id_list=<security,event,type,id,list>] [ports_list=<ports,list>] [hit_count_low_value=<hit_count_low_value>] [hit_count_high_value=<hit_count_high_value>]"
            " [ci_points_low_value=<ci_points_low_value>] [ci_points_high_value=<ci_points_high_value>] [filter_by=<filter_by>] [flow_collector_list=<flow,collector,list>] [max_rows=<max_rows>] [domain_id=<domain_id>] [smc_ip=<smc_ip>]"
        )

    start_datetime = None
    end_datetime = None
    datetimes = splunk_utility.get_timerange(earliest=earliest, latest=latest, logger=logger)
    if "start_datetime" in list(datetimes.keys()) and datetimes["start_datetime"] is not None:
        start_datetime = datetimes["start_datetime"]
    if "end_datetime" in list(datetimes.keys()) and datetimes["end_datetime"] is not None:
        end_datetime = datetimes["end_datetime"]

    if subject_ip is None or len(subject_ip) <= 0:
        subject_ip = None
    if subject_host_group_id is None or len(subject_host_group_id) <= 0:
        subject_host_group_id = None
    if peer_ip is None or len(peer_ip) <= 0:
        peer_ip = None
    if peer_host_group_id is None or len(peer_host_group_id) <= 0:
        peer_host_group_id = None
    if subject_orientation is None or len(subject_orientation) <= 0:
        subject_orientation = None

    if security_event_type_id_list is None or len(security_event_type_id_list) <= 0 or security_event_type_id_list == "all":
        security_event_type_id_list = None
    else:
        security_event_type_id_list = security_event_type_id_list.split(",")
        tmp_list = []
        for id in security_event_type_id_list:
            if id != "all":
                tmp_list.append(int(id))
        security_event_type_id_list = tmp_list

    if ports_list is None or len(ports_list) <= 0:
        ports_list = None
    else:
        ports_list = ports_list.split(",")
        tmp_list = []
        for port in ports_list:
            if "/" not in port.strip() and port.strip().isdigit():
                tmp_list.append(port.strip() + "/tcp")
                tmp_list.append(port.strip() + "/udp")
            else:
                tmp_list.append(port.strip())
        ports_list = tmp_list

    if hit_count_low_value is None or len(hit_count_low_value) <= 0 or int(hit_count_low_value) < 0:
        hit_count_low_value = None
    if hit_count_high_value is None or len(hit_count_high_value) <= 0 or int(hit_count_high_value) < 0:
        hit_count_high_value = None
    if ci_points_low_value is None or len(ci_points_low_value) <= 0 or int(ci_points_low_value) < 0:
        ci_points_low_value = None
    if ci_points_high_value is None or len(ci_points_high_value) <= 0 or int(ci_points_high_value) < 0:
        ci_points_high_value = None

    if flow_collector_list is None or len(flow_collector_list) <= 0:
        flow_collector_list = None
    else:
        tmp_flow_collectors = []
        for swa_id in flow_collector_list.split(","):
            tmp_flow_collectors.append(int(swa_id.strip()))
        flow_collector_list = tmp_flow_collectors

    if max_rows is None or len(max_rows) <= 0:
        max_rows = None


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
    data = None
    host_group_dict = {}
    service_definitions = {}
    protocol_map = {}
    security_event_types = {}
    fc_map = {}

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
        # FETCH the necessary data by issuing a REST request to the RESTx
        ############################################################################################################
        logger.info("Executing \"get_security_events_soap\" API call...")
        data = api.get_security_events_soap(start_datetime=start_datetime, end_datetime=end_datetime, subject_ip=subject_ip,
                                            subject_host_group_id=subject_host_group_id, subject_orientation=subject_orientation, peer_ip=peer_ip, peer_host_group_id=peer_host_group_id,
                                            security_event_type_id_list=security_event_type_id_list, ports_list=ports_list, hit_count_low_value=hit_count_low_value,
                                            hit_count_high_value=hit_count_high_value, ci_points_low_value=ci_points_low_value, ci_points_high_value=ci_points_high_value,
                                            filter_by=filter_by, flow_collector_list=flow_collector_list, max_rows=max_rows)
        logger.info("Done executing \"get_security_events_soap\" API call.")

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

            service_definitions_tmp = api.get_service_definitions()
            for item in service_definitions_tmp["service-definitions"]["services"]["service"]:
                service_definitions[item["profile"]] = item["name"]
            protocol_map = api.get_protocol_list(surpress_std_out=True)

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

            fc_data = api.get_flow_collectors()
            if fc_data is not None and len(fc_data) > 0:
                for fc in fc_data:
                    if "id" in fc and fc['id'] is not None:
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

        if data is not None and len(data) > 0:
            for row in data:
                this_row = process_row(row, host_group_dict, protocol_map, service_definitions, security_event_types, fc_map)
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

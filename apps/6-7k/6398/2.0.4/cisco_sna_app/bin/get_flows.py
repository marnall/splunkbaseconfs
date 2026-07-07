# ==========================================================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# get_top_ports.py script for use with Splunk enterprise to fetch top peers
# from StealthWatch using the RESTx appliance REST API extension service
# ==========================================================================================================

# Usage: |flows earliest=<earliest> latest=<latest> [subject_ip=<subject_ip>] [subject_host_group_id=<subject_host_group_id>] [subject_orientation=<subject_orientation>]
#   [peer_ip=<peer_ip>] [peer_host_group_id=<peer_host_group_id>] [remove_duplicate_flows=<true|false>] [includes_services_id_list=<includes_services_id_list>]
#   [excludes_services_id_list=<excludes_services_id_list>] [includes_ports_list=<includes,ports,list>] [excludes_ports_list=<excludes,ports,list>] [includes_applications_id_list=<includes,applications,id,list>]
#   [excludes_applications_id_list=<excludes,applications,id,list>] [filter_by=<filter_by>] [flow_collector_list=<flow,collector,list>] [order_by=<order_by>] [descending_order=<true|false>] [max_rows=<max_rows>]
#   [domain_id=<domain_id>] [smc_ip=<smc_ip>] [username_list=<username,list>]

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
def process_row(row, host_group_dict, protocol_map, application_map):
    this_row = {}
    for k, v in row.items():
        if 'applicationId' in k:
            if int(row["applicationId"]) in list(application_map.keys()):
                this_row["application-name"] = application_map[int(v)]

        elif isinstance(v, dict):
            for k2, v2 in v.items():
                if isinstance(v2, dict):
                    for k3, v3 in v2.items():
                        this_row[str(k) + '-' + str(k2) + '-' + str(k3)] = v3
                else:
                    if "activeDuration" in k2:
                        this_row[k2] = int(v2) // 1000
                    elif 'firstActiveTime' in k2:
                        this_row[str(k2)] = str(v2.replace(".000+0000", ""))
                    elif 'lastActiveTime' in k2:
                        this_row[str(k2)] = str(v2.replace(".000+0000", ""))
                    elif 'hostGroupIds' in k2:
                        host_group_string = ""
                        for h_id in v2:
                            if h_id in host_group_dict:
                                host_group_string += host_group_dict[h_id] + "; "
                        this_row[str(k) + '-host_group_names'] = host_group_string
                    elif 'percentBytes' in k2:
                        percent_bytes = str(round(v2, 2)) + "%"
                        this_row[str(k) + '-percentBytes'] = percent_bytes
                    else:
                        this_row[str(k) + '-' + str(k2)] = v2

        else:
            this_row[k] = v


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
    remove_duplicate_flows = kwargs.get('remove_duplicate_flows')
    includes_services_id_list = kwargs.get('includes_services_id_list')
    excludes_services_id_list = kwargs.get('excludes_services_id_list')
    includes_ports_list = kwargs.get('includes_ports_list')
    excludes_ports_list = kwargs.get('excludes_ports_list')
    includes_applications_id_list = kwargs.get('includes_applications_id_list')
    excludes_applications_id_list = kwargs.get('excludes_applications_id_list')
    filter_by = kwargs.get('filter_by')
    flow_collector_list = kwargs.get('flow_collector_list')
    order_by = kwargs.get('order_by')
    descending_order = kwargs.get('descending_order')
    max_rows = kwargs.get('max_rows')
    domain_id = kwargs.get('domain_id')
    smc_ip = kwargs.get('smc_ip')
    username_list = kwargs.get('username_list')

    if earliest is None or latest is None:
        logger.error("Missing required arguments")
        logger.error("Aborting RESTx API process")
        # Following line calls sys.exit()
        splunk.Intersplunk.parseError(
            "Missing required arguments! (|flows earliest=<earliest> latest=<latest> [subject_ip=<subject_ip>] [subject_host_group_id=<subject_host_group_id>] [subject_orientation=<subject_orientation>]"
            " [peer_ip=<peer_ip>] [peer_host_group_id=<peer_host_group_id>] [remove_duplicate_flows=<true|false>] [includes_services_id_list=<includes_services_id_list>] [excludes_services_id_list=<excludes_services_id_list>]"
            " [includes_ports_list=<includes,ports,list>] [excludes_ports_list=<excludes,ports,list>] [includes_applications_id_list=<includes,applications,id,list>] [excludes_applications_id_list=<excludes,applications,id,list>]"
            " [filter_by=<filter_by>] [flow_collector_list=<flow,collector,list>] [order_by=<order_by>] [descending_order=<true|false>] [max_rows=<max_rows>] [domain_id=<domain_id>] [smc_ip=<smc_ip>] [username_list=<username,list>])"
        )

    # TODO #
    flow_collector_id = None
    exporter_ip_list = None
    exporter_ip = None
    interface_id_list = None
    includes_protocols_number_list = None
    excludes_protocols_number_list = None
    includes_asn_list = None
    excludes_asn_list = None
    includes_dscp_list = None
    excludes_dscp_list = None
    includes_vlan_id_list = None
    excludes_vlan_id_list = None
    includes_mpls_vlan_id_list = None
    excludes_mpls_vlan_id_list = None
    includes_client_ports_list = None
    excludes_client_ports_list = None
    client_bytes_greater_than = None
    client_bytes_less_than = None
    client_packets_greater_than = None
    client_packets_less_than = None
    server_bytes_greater_than = None
    server_bytes_less_than = None
    server_packets_greater_than = None
    server_packets_less_than = None
    total_bytes_greater_than = None
    total_bytes_less_than = None
    total_packets_greater_than = None
    total_packets_less_than = None
    total_connections_greater_than = None
    total_connections_less_than = None
    total_retransmissions_greater_than = None
    total_retransmissions_less_than = None
    minimum_rtt_greater_than = None
    minimum_rtt_less_than = None
    average_rtt_greater_than = None
    average_rtt_less_than = None
    maximum_rtt_greater_than = None
    maximum_rtt_less_than = None
    minimum_srt_greater_than = None
    minimum_srt_less_than = None
    average_srt_greater_than = None
    average_srt_less_than = None
    maximum_srt_greater_than = None
    maximum_srt_less_than = None
    payload_includes = None
    payload_exclude = None
    payload_match_any = None

    start_datetime = None
    end_datetime = None
    datetimes = splunk_utility.get_timerange(earliest=earliest, latest=latest, logger=logger)
    if "start_datetime" in list(datetimes.keys()) and datetimes["start_datetime"] is not None:
        start_datetime = datetimes["start_datetime"]
    if "end_datetime" in list(datetimes.keys()) and datetimes["end_datetime"] is not None:
        end_datetime = datetimes["end_datetime"]

    if subject_ip is None or len(subject_ip) <= 0:
        subject_ip = None
    if username_list is None or len(username_list) <= 0:
        username_list = None
    if subject_host_group_id is None or len(subject_host_group_id) <= 0:
        subject_host_group_id = None
    if subject_orientation is None or len(subject_orientation) <= 0:
        subject_orientation = None
    if peer_ip is None or len(peer_ip) <= 0:
        peer_ip = None
    if peer_host_group_id is None or len(peer_host_group_id) <= 0:
        peer_host_group_id = None

    remove_duplicate_flows = splunk_utility.str_to_bool(remove_duplicate_flows)

    if includes_services_id_list is None or len(includes_services_id_list) <= 0 or includes_services_id_list.lower() == "all":
        includes_services_id_list = None
    else:
        tmp_list = []
        for item in includes_services_id_list.split(","):
            if item.lower() != "all":
                tmp_list.append(item.strip())
        includes_services_id_list = tmp_list

    if excludes_services_id_list is None or len(excludes_services_id_list) <= 0 or excludes_services_id_list.lower() == "none":
        excludes_services_id_list = None
    else:
        tmp_list = []
        for item in excludes_services_id_list.split(","):
            if item.lower() != "none":
                tmp_list.append(item.strip())
        excludes_services_id_list = tmp_list

    if includes_ports_list is None or len(includes_ports_list) <= 0 or includes_ports_list.lower() == "all":
        includes_ports_list = None
    else:
        tmp_list = []
        for item in includes_ports_list.split(","):
            if item.lower() != "all":
                if "/" not in item.strip() and item.strip().isdigit():
                    tmp_list.append(item.strip() + "/tcp")
                    tmp_list.append(item.strip() + "/udp")
                else:
                    tmp_list.append(item.strip())

        includes_ports_list = tmp_list

    if excludes_ports_list is None or len(excludes_ports_list) <= 0 or excludes_ports_list.lower() == "none":
        excludes_ports_list = None
    else:
        tmp_list = []
        for item in excludes_ports_list.split(","):
            if item.lower() != "none":
                if "/" not in item.strip() and item.strip().isdigit():
                    tmp_list.append(item.strip() + "/tcp")
                    tmp_list.append(item.strip() + "/udp")
                else:
                    tmp_list.append(item.strip())
        excludes_ports_list = tmp_list

    if includes_applications_id_list is None or len(includes_applications_id_list) <= 0 or includes_applications_id_list.lower() == "all":
        includes_applications_id_list = None
    else:
        tmp_list = []
        for item in includes_applications_id_list.split(","):
            if item.lower() != "all":
                tmp_list.append(item.strip())
        includes_applications_id_list = tmp_list

    if excludes_applications_id_list is None or len(excludes_applications_id_list) <= 0 or excludes_applications_id_list.lower() == "none":
        excludes_applications_id_list = None
    else:
        tmp_list = []
        for item in excludes_applications_id_list.split(","):
            if item.lower() != "none":
                tmp_list.append(item.strip())
        excludes_applications_id_list = tmp_list

    if flow_collector_list is None or len(flow_collector_list) <= 0:
        flow_collector_list = None
    else:
        tmp_flow_collectors = []
        for swa_id in flow_collector_list.split(","):
            tmp_flow_collectors.append(int(swa_id.strip()))
        flow_collector_list = tmp_flow_collectors
    if order_by is None or len(order_by) <= 0:
        order_by = None

    descending_order = splunk_utility.str_to_bool(descending_order)

    if max_rows is None or len(max_rows) <= 0:
        max_rows = {"recordLimit": 3000}

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
    protocol_map = {}
    application_map = {}

    try:

        ############################################################################################################
        # LOGIN to RESTx API Extension appliance
        ############################################################################################################
        logger.info("Authenticating API connection...")
        api = stealthwatch_api_client.stealthwatch_api()
        api.login(smc_ip, config["smcID"], config["smcPW"], requests_disable_warnings=False)
        api.set_domain_id(int(domain_id))
        logger.info("Done authenticating API connection.")

        # New FETCH via the get_flows_rest() call
        # Reformatting data parameters for REST data dict
        DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
        start_datetime = {"startDateTime": start_datetime.strftime(DATETIME_FORMAT)}
        end_datetime = {"endDateTime": end_datetime.strftime(DATETIME_FORMAT)}

        if not isinstance(max_rows, dict):
            record_limit = {"recordLimit": int(max_rows)}
        else:
            record_limit = max_rows

        subject_orientation = {"orientation": subject_orientation}
        # Only supports one IP as an include, could be improved later
        if subject_ip:
            subject_ips = {"ipAddresses": {"includes": subject_ip.split()}}
        else:
            subject_ips = None

        # Only supports one IP as an include, could be improved later
        if subject_host_group_id:
            subject_hg = {"hostGroups": {"includes": subject_host_group_id.split()}}
        else:
            subject_hg = None

        if includes_ports_list and excludes_ports_list:
            subject_tcp_udp_ports = {"tcpUdpPorts": {"includes": includes_ports_list,"excludes": excludes_ports_list}}
        elif includes_ports_list and not excludes_ports_list:
            subject_tcp_udp_ports = {"tcpUdpPorts": {"includes": includes_ports_list}}
        elif not includes_ports_list and excludes_ports_list:
            subject_tcp_udp_ports = {"tcpUdpPorts": {"excludes": excludes_ports_list_ports_list}}
        else:
            subject_tcp_udp_ports = None

        # Guessing the old 'username' field maps to just the subject username, could be wrong here, could be both subject and peer
        if username_list:
            subject_username = {"username": {"includes": username_list.split()}}
        else:
            subject_username = None

        # subject_mac = {"macAddress": {"includes": subject}}

        if peer_ip:
            peer_ips = {"ipAddresses": {"includes": peer_ip.split()}}
        else:
            peer_ips = None

        if peer_host_group_id:
            peer_hg = {"hostGroups": {"includes": peer_host_group_id.split()}}
        else:
            peer_hg = None
        if includes_applications_id_list and excludes_applications_id_list:
            flow_applications = {"applications": {"includes": includes_applications_id_list,"excludes": excludes_applications_id_list}}
        elif includes_applications_id_list and not excludes_applications_id_list:
            flow_applications = {"applications": {"includes": includes_applications_id_list}}
        elif not includes_applications_id_list and excludes_applications_id_list:
            flow_applications = {"applications": {"excludes": excludes_applications_id_list}}
        else:
            flow_applications = None

        logger.info("Executing \"get_flows_REST\" API call...")

        data = api.get_flows_rest(start_datetime=start_datetime, end_datetime=end_datetime, record_limit=record_limit,
                                  subject_orientation=subject_orientation, subject_ips=subject_ips, subject_hg=subject_hg,
                                  subject_tcp_udp_ports=subject_tcp_udp_ports, subject_username=subject_username,
                                  peer_ips=peer_ips, peer_hg=peer_hg, flow_applications=flow_applications)

        # logger.info(data)

        logger.info("Done executing \"get_flows\" API call.")

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

            protocol_map = api.get_protocol_list(surpress_std_out=True)

            default_applications = api.get_application_definitions()
            if default_applications is not None:
                for application in default_applications:
                    application_map[application["id"]] = application["name"]
            custom_applications = api.get_custom_applications()
            if custom_applications is not None:
                for application in custom_applications:
                    application_map[application["id"]] = application["name"]

        ############################################################################################################
        # LOGOUT the session
        ############################################################################################################
        logger.info("De-authenticating API connection...")
        api.logout()
        logger.info("Done de-authenticating API connection.")

        if data is not None and len(data) > 0:
            for row in data:
                this_row = process_row(row, host_group_dict, protocol_map, application_map)
                results.append(this_row)

        logger.info('Row Processing Complete. results:')

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

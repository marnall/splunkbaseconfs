# ==========================================================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# get_top_ports.py script for use with Splunk enterprise to fetch top peers
# from StealthWatch using the RESTx appliance REST API extension service
# ==========================================================================================================

# Usage: |topreport report_type=<filter> earliest=<earliest> latest=<latest> [subject_tags_includes=<subject_tags_includes>] [subject_tags_excludes=<subject_tags_excludes>]
#   [subject_addresses_includes=<subject_addresses_includes>] [subject_addresses_excludes=<subject_addresses_excludes>] [peer_tags_includes=<peer_tags_includes>] [peer_tags_excludes=<peer_tags_excludes>]
#   [peer_addresses_includes=<peer_addresses_includes>] [peer_addresses_excludes=<peer_addresses_excludes>] [subject_orientation=<subject_orientation>] [connection_direction=<connection_direction>]
#   [connection_applications_includes=<connection_applications_includes>] [connection_applications_excludes=<connection_applications_excludes>] [connection_ports_protocols_includes=<connection_ports_protocols_includes>]
#   [connection_ports_protocols_excludes=<connection_ports_protocols_excludes>] [flow_collectors=<flow,collectors>] [order_by=<order_by>] [max_rows=<max_rows>] [exclude_bps_pps=<exclude_bps_pps>]
#   [exclude_others=<exclude_others>] [exclude_counts=<exclude_counts>] [status_check_frequency=<status_check_frequency>] [domain_id=<domain_id>] [smc_ip=<smc_ip>]

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
def process_row(report_type, row_type, row, host_group_dict, protocol_map, service_definitions, max_rows):
    this_row = {}
    if report_type is None or row_type is None or row is None:
        return None
    this_row["reportType"] = report_type
    if row_type == "results" and "rank" in row and int(row["rank"]) == 0:
        this_row["rowType"] = "summary"
    elif row_type == "results" and "rank" in row and int(row["rank"]) > int(max_rows):
        this_row["rowType"] = "others"
    else:
        this_row["rowType"] = row_type
    if "bytes" in row:
        this_row["bytes"] = row["bytes"]
        this_row["bytes_str"] = splunk_utility.convert_bytes_to_string(row["bytes"])
    if "clientBytesRatio" in row:
        this_row["clientBytesRatio"] = round(float(row["clientBytesRatio"]), splunk_utility.number_of_decimal_places)
    if "connections" in row:
        this_row["connections"] = row["connections"]
    if "deviceId" in row:
        this_row["deviceId"] = row["deviceId"]
    if "flows" in row:
        this_row["flows"] = row["flows"]
    if "hostBytes" in row:
        this_row["hostBytes"] = row["hostBytes"]
        this_row["hostBytes_str"] = splunk_utility.convert_bytes_to_string(row["hostBytes"])
    if "hostBytesRatio" in row:
        this_row["hostBytesRatio"] = round(float(row["hostBytesRatio"]), splunk_utility.number_of_decimal_places)
        this_row["hostBytesRatio_str"] = str(round(float(row["hostBytesRatio"]), splunk_utility.number_of_decimal_places)) + "%"
    if "hostClientBytes" in row:
        this_row["hostClientBytes"] = row["hostClientBytes"]
        this_row["hostClientBytes_str"] = splunk_utility.convert_bytes_to_string(row["hostClientBytes"])
    if "hostClientPackets" in row:
        this_row["hostClientPackets"] = row["hostClientPackets"]
    if "hostClients" in row:
        this_row["hostClients"] = row["hostClients"]
    if "hostConnections" in row:
        this_row["hostConnections"] = row["hostConnections"]
    if "hostFlows" in row:
        this_row["hostFlows"] = row["hostFlows"]
    if "hostPackets" in row:
        this_row["hostPackets"] = row["hostPackets"]
    if "hostRole" in row:
        this_row["hostRole"] = row["hostRole"]
    if "hostServerBytes" in row:
        this_row["hostServerBytes"] = row["hostServerBytes"]
        this_row["hostServerBytes_str"] = splunk_utility.convert_bytes_to_string(row["hostServerBytes"])
    if "hostServerPackets" in row:
        this_row["hostServerPackets"] = row["hostServerPackets"]
    if "hostServers" in row:
        this_row["hostServers"] = row["hostServers"]
    if "hosts" in row:
        this_row["hosts"] = row["hosts"]
    if "packetRate95th" in row:
        this_row["packetRate95th"] = round(float(row["packetRate95th"]), splunk_utility.number_of_decimal_places)
    if "packetRateAvg" in row:
        this_row["packetRateAvg"] = round(float(row["packetRateAvg"]), splunk_utility.number_of_decimal_places)
    if "packetRateMax" in row:
        this_row["packetRateMax"] = round(float(row["packetRateMax"]), splunk_utility.number_of_decimal_places)
    if "packetRateMin" in row:
        this_row["packetRateMin"] = round(float(row["packetRateMin"]), splunk_utility.number_of_decimal_places)
    if "packets" in row:
        this_row["packets"] = row["packets"]
    if "peerBytes" in row:
        this_row["peerBytes"] = row["peerBytes"]
        this_row["peerBytes_str"] = splunk_utility.convert_bytes_to_string(row["peerBytes"])
    if "peerBytesRatio" in row:
        this_row["peerBytesRatio"] = round(float(row["peerBytesRatio"]), splunk_utility.number_of_decimal_places)
        this_row["peerBytesRatio_str"] = str(round(float(row["peerBytesRatio"]), splunk_utility.number_of_decimal_places)) + "%"
    if "peerClientBytes" in row:
        this_row["peerClientBytes"] = row["peerClientBytes"]
        this_row["peerClientBytes_str"] = splunk_utility.convert_bytes_to_string(row["peerClientBytes"])
    if "peerClientPackets" in row:
        this_row["peerClientPackets"] = row["peerClientPackets"]
    if "peerClients" in row:
        this_row["peerClients"] = row["peerClients"]
    if "peerConnections" in row:
        this_row["peerConnections"] = row["peerConnections"]
    if "peerFlows" in row:
        this_row["peerFlows"] = row["peerFlows"]
    if "peerPackets" in row:
        this_row["peerPackets"] = row["peerPackets"]
    if "peerRole" in row:
        this_row["peerRole"] = row["peerRole"]
    if "peerServerBytes" in row:
        this_row["peerServerBytes"] = row["peerServerBytes"]
        this_row["peerServerBytes_str"] = splunk_utility.convert_bytes_to_string(row["peerServerBytes"])
    if "peerServerPackets" in row:
        this_row["peerServerPackets"] = row["peerServerPackets"]
    if "peerServers" in row:
        this_row["peerServers"] = row["peerServers"]
    if "peers" in row:
        this_row["peers"] = row["peers"]
    if "percent" in row:
        this_row["percent"] = round(float(row["percent"]), splunk_utility.number_of_decimal_places)
        this_row["percent_str"] = str(round(float(row["percent"]), splunk_utility.number_of_decimal_places)) + "%"
    if "rank" in row:
        this_row["rank"] = row["rank"]
    if "records" in row:
        this_row["records"] = row["records"]
    if "serverBytesRatio" in row:
        this_row["serverBytesRatio"] = round(float(row["serverBytesRatio"]), splunk_utility.number_of_decimal_places)
    if "trafficRate95th" in row:
        this_row["trafficRate95th"] = round(float(row["trafficRate95th"]), splunk_utility.number_of_decimal_places)
    if "trafficRateAvg" in row:
        this_row["trafficRateAvg"] = round(float(row["trafficRateAvg"]), splunk_utility.number_of_decimal_places)
    if "trafficRateMax" in row:
        this_row["trafficRateMax"] = round(float(row["trafficRateMax"]), splunk_utility.number_of_decimal_places)
    if "trafficRateMin" in row:
        this_row["trafficRateMin"] = round(float(row["trafficRateMin"]), splunk_utility.number_of_decimal_places)
    if "application" in row:
        this_row["applicationId"] = row["application"]["id"]
        this_row["applicationName"] = row["application"]["name"]
    if "host" in row:
        this_row["hostCountry"] = row["host"]["country"]
        this_row["hostIp"] = row["host"]["ipAddress"]
        if "name" in row["host"]:
            this_row["hostName"] = row["host"]["name"]
        host_group_id_string = ""
        host_group_name_string = ""
        for host_group_id in row["host"]["hostGroupIds"]:
            host_group_id_string += str(host_group_id) + ", "
            if host_group_id in host_group_dict:
                host_group_name_string += str(host_group_dict[host_group_id]) + "; "
            else:
                host_group_name_string += "[Unknown Host Group ID: " + str(host_group_id) + "]; "
        host_group_id_string = host_group_id_string[:-2]
        host_group_name_string = host_group_name_string[:-2]
        this_row["hostHostGroupIds"] = host_group_id_string
        this_row["hostHostGroupNames"] = host_group_name_string
    if "peer" in row:
        this_row["peerCountry"] = row["peer"]["country"]
        this_row["peerIp"] = row["peer"]["ipAddress"]
        if "name" in row["peer"]:
            this_row["peerName"] = row["peer"]["name"]
        host_group_id_string = ""
        host_group_name_string = ""
        for host_group_id in row["peer"]["hostGroupIds"]:
            host_group_id_string += str(host_group_id) + ", "
            if host_group_id in host_group_dict:
                host_group_name_string += str(host_group_dict[host_group_id]) + "; "
            else:
                host_group_name_string += "[Unknown Host Group ID: " + str(host_group_id) + "]; "
        host_group_id_string = host_group_id_string[:-2]
        host_group_name_string = host_group_name_string[:-2]
        this_row["peerHostGroupIds"] = host_group_id_string
        this_row["peerHostGroupNames"] = host_group_name_string
    if "port" in row and row["port"] > 0:
        this_row["port"] = row["port"]
    if "protocol" in row:
        this_row["protocol"] = row["protocol"]
    if "protocolNumber" in row:
        this_row["protocolNumber"] = row["protocolNumber"]
        this_service_id = str(this_row["protocolNumber"])
        while len(this_service_id) < 4:
            this_service_id = "0" + this_service_id
        this_row["serviceId"] = "6" + this_service_id
    if "portProtocol" in row and "service" in row["portProtocol"]:
        this_row["serviceId"] = row["portProtocol"]["service"]["id"]
    if "serviceId" in row:
        this_row["serviceId"] = row["serviceId"]
    if "service" in row:
        if "id" in row["service"]:
            this_row["serviceId"] = row["service"]["id"]
        if "name" in row["service"]:
            if "Protocol " in row["service"]["name"]:
                if protocol_map is not None and str(row["service"]["name"].replace("Protocol ", "")) in list(protocol_map.keys()):
                    this_row["serviceName"] = protocol_map[str(row["service"]["name"].replace("Protocol ", ""))]
                else:
                    this_row["serviceName"] = row["service"]["name"]
            else:
                this_row["serviceName"] = row["service"]["name"]
    if "serviceId" in list(this_row.keys()) and "serviceName" not in list(this_row.keys()):
        this_service_id = str(this_row["serviceId"])
        if this_service_id in list(service_definitions.keys()):
            this_row["serviceName"] = service_definitions[this_service_id]
        elif len(this_service_id) == 5 and this_service_id.startswith("6"):
            this_service_id = this_service_id[1:]
            while this_service_id.startswith("0"):
                this_service_id = this_service_id[1:]
            if protocol_map is not None and str(this_service_id) in list(protocol_map.keys()):
                this_row["serviceName"] = protocol_map[str(this_service_id)]
            else:
                this_row["serviceName"] = "Protocol " + this_service_id
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
    earliest = kwargs.get('earliest')
    latest = kwargs.get('latest')
    subject_tags_includes = kwargs.get('subject_tags_includes')
    subject_tags_excludes = kwargs.get('subject_tags_excludes')
    subject_addresses_includes = kwargs.get('subject_addresses_includes')
    subject_addresses_excludes = kwargs.get('subject_addresses_excludes')
    peer_tags_includes = kwargs.get('peer_tags_includes')
    peer_tags_excludes = kwargs.get('peer_tags_excludes')
    peer_addresses_includes = kwargs.get('peer_addresses_includes')
    peer_addresses_excludes = kwargs.get('peer_addresses_excludes')
    subject_orientation = kwargs.get('subject_orientation')
    connection_direction = kwargs.get('connection_direction')
    connection_applications_includes = kwargs.get('connection_applications_includes')
    connection_applications_excludes = kwargs.get('connection_applications_excludes')
    connection_ports_protocols_includes = kwargs.get('connection_ports_protocols_includes')
    connection_ports_protocols_excludes = kwargs.get('connection_ports_protocols_excludes')
    flow_collectors = kwargs.get('flow_collectors')
    order_by = kwargs.get('order_by')
    max_rows = kwargs.get('max_rows')
    exclude_bps_pps = kwargs.get('exclude_bps_pps')
    exclude_others = kwargs.get('exclude_others')
    exclude_counts = kwargs.get('exclude_counts')
    status_check_frequency = kwargs.get('status_check_frequency')
    domain_id = kwargs.get('domain_id')
    smc_ip = kwargs.get('smc_ip')

    if report_type is None or earliest is None or latest is None or max_rows is None:
        logger.error("Missing required arguments")
        logger.error("Aborting RESTx API process")
        # Following line calls sys.exit()
        splunk.Intersplunk.parseError(
            "Missing required arguments! (Usage: |topreport report_type=<filter> earliest=<earliest> latest=<latest> max_rows=<num_rows> [subject_tags_includes=<subject_tags_includes>]"
            " [subject_tags_excludes=<subject_tags_excludes>] [subject_addresses_includes=<subject_addresses_includes>] [subject_addresses_excludes=<subject_addresses_excludes>] [peer_tags_includes=<peer_tags_includes>]"
            " [peer_tags_excludes=<peer_tags_excludes>] [peer_addresses_includes=<peer_addresses_includes>] [peer_addresses_excludes=<peer_addresses_excludes>] [subject_orientation=<subject_orientation>]"
            " [connection_direction=<connection_direction>] [connection_applications_includes=<connection_applications_includes>] [connection_applications_excludes=<connection_applications_excludes>]"
            " [connection_ports_protocols_includes=<connection_ports_protocols_includes>] [connection_ports_protocols_excludes=<connection_ports_protocols_excludes>] [flow_collectors=<flow,collectors>]"
            " [order_by=<order_by>] [exclude_bps_pps=<exclude_bps_pps>] [exclude_others=<exclude_others>] [exclude_counts=<exclude_counts>] [status_check_frequency=<status_check_frequency>]"
            " [domain_id=<domain_id>] [smc_ip=<smc_ip>]"
        )

    start_datetime = None
    end_datetime = None
    datetimes = splunk_utility.get_timerange(earliest=earliest, latest=latest, logger=logger)
    if "start_datetime" in list(datetimes.keys()) and datetimes["start_datetime"] is not None:
        start_datetime = datetimes["start_datetime"]
    if "end_datetime" in list(datetimes.keys()) and datetimes["end_datetime"] is not None:
        end_datetime = datetimes["end_datetime"]

    if subject_tags_includes is None or len(subject_tags_includes) <= 0 or subject_tags_includes.lower().strip() == "all":
        subject_tags_includes = None
    else:
        tmp_subject_tags_includes = []
        for tag in subject_tags_includes.split(","):
            if tag.lower().strip() != "all":
                tmp_subject_tags_includes.append(int(tag.strip()))
        subject_tags_includes = tmp_subject_tags_includes
    if subject_tags_excludes is None or len(subject_tags_excludes) <= 0 or subject_tags_excludes.lower().strip() == "none":
        subject_tags_excludes = None
    else:
        tmp_subject_tags_excludes = []
        for tag in subject_tags_excludes.split(","):
            if tag.lower().strip() != "none":
                tmp_subject_tags_excludes.append(int(tag.strip()))
        subject_tags_excludes = tmp_subject_tags_excludes
    if subject_addresses_includes is None or len(subject_addresses_includes) <= 0:
        subject_addresses_includes = None
    else:
        tmp_subject_addresses_includes = []
        for address in subject_addresses_includes.split(","):
            tmp_subject_addresses_includes.append(address.strip())
        subject_addresses_includes = tmp_subject_addresses_includes
    if subject_addresses_excludes is None or len(subject_addresses_excludes) <= 0:
        subject_addresses_excludes = None
    else:
        tmp_subject_addresses_excludes = []
        for address in subject_addresses_excludes.split(","):
            tmp_subject_addresses_excludes.append(address.strip())
        subject_addresses_excludes = tmp_subject_addresses_excludes

    if peer_tags_includes is None or len(peer_tags_includes) <= 0 or peer_tags_includes.lower().strip() == "all":
        peer_tags_includes = None
    else:
        tmp_peer_tags_includes = []
        for tag in peer_tags_includes.split(","):
            if tag.lower().strip() != "all":
                tmp_peer_tags_includes.append(int(tag.strip()))
        peer_tags_includes = tmp_peer_tags_includes
    if peer_tags_excludes is None or len(peer_tags_excludes) <= 0 or peer_tags_excludes.lower().strip() == "none":
        peer_tags_excludes = None
    else:
        tmp_peer_tags_excludes = []
        for tag in peer_tags_excludes.split(","):
            if tag.lower().strip() != "none":
                tmp_peer_tags_excludes.append(int(tag.strip()))
        peer_tags_excludes = tmp_peer_tags_excludes
    if peer_addresses_includes is None or len(peer_addresses_includes) <= 0:
        peer_addresses_includes = None
    else:
        tmp_peer_addresses_includes = []
        for address in peer_addresses_includes.split(","):
            tmp_peer_addresses_includes.append(address.strip())
        peer_addresses_includes = tmp_peer_addresses_includes
    if peer_addresses_excludes is None or len(peer_addresses_excludes) <= 0:
        peer_addresses_excludes = None
    else:
        tmp_peer_addresses_excludes = []
        for address in peer_addresses_excludes.split(","):
            tmp_peer_addresses_excludes.append(address.strip())
        peer_addresses_excludes = tmp_peer_addresses_excludes

    if subject_orientation is None or len(subject_orientation) <= 0:
        subject_orientation = None
    if connection_direction is None or len(connection_direction) <= 0:
        connection_direction = None
    if connection_applications_includes is None or len(
            connection_applications_includes) <= 0 or connection_applications_includes.lower() == "all":
        connection_applications_includes = None
    else:
        tmp_connection_applications_includes = []
        for app_id in connection_applications_includes.split(","):
            if app_id.lower() != "all":
                tmp_connection_applications_includes.append(int(app_id.strip()))
        connection_applications_includes = tmp_connection_applications_includes
    if connection_applications_excludes is None or len(
            connection_applications_excludes) <= 0 or connection_applications_excludes.lower() == "none":
        connection_applications_excludes = None
    else:
        tmp_connection_applications_excludes = []
        for app_id in connection_applications_excludes.split(","):
            if app_id.lower() != "none":
                tmp_connection_applications_excludes.append(int(app_id.strip()))
        connection_applications_excludes = tmp_connection_applications_excludes
    if connection_ports_protocols_includes is None or len(connection_ports_protocols_includes) <= 0:
        connection_ports_protocols_includes = None
    else:
        tmp_connection_ports_protocols_includes = []
        for address in connection_ports_protocols_includes.split(","):
            if "/" not in address.strip() and address.strip().isdigit():
                tmp_connection_ports_protocols_includes.append(address.strip() + "/tcp")
                tmp_connection_ports_protocols_includes.append(address.strip() + "/udp")
            else:
                tmp_connection_ports_protocols_includes.append(address.strip())
        connection_ports_protocols_includes = tmp_connection_ports_protocols_includes
    if connection_ports_protocols_excludes is None or len(connection_ports_protocols_excludes) <= 0:
        connection_ports_protocols_excludes = None
    else:
        tmp_connection_ports_protocols_excludes = []
        for address in connection_ports_protocols_excludes.split(","):
            if "/" not in address.strip() and address.strip().isdigit():
                tmp_connection_ports_protocols_excludes.append(address.strip() + "/tcp")
                tmp_connection_ports_protocols_excludes.append(address.strip() + "/udp")
            else:
                tmp_connection_ports_protocols_excludes.append(address.strip())
        connection_ports_protocols_excludes = tmp_connection_ports_protocols_excludes

    if flow_collectors is None or len(flow_collectors) <= 0:
        flow_collectors = None
    else:
        tmp_flow_collectors = []
        for swa_id in flow_collectors.split(","):
            tmp_flow_collectors.append(int(swa_id.strip()))
        flow_collectors = tmp_flow_collectors

    if order_by is None or len(order_by) <= 0:
        order_by = None

    if max_rows is None or len(max_rows) <= 0:
        max_rows = None
    else:
        max_rows = int(max_rows.strip())

    exclude_bps_pps = splunk_utility.str_to_bool(exclude_bps_pps)
    exclude_others = splunk_utility.str_to_bool(exclude_others)
    exclude_counts = splunk_utility.str_to_bool(exclude_counts)

    if status_check_frequency is None or len(status_check_frequency) <= 0:
        status_check_frequency = 0
    else:
        status_check_frequency = int(status_check_frequency)

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
    service_definitions = {}
    protocol_map = {}

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
        if report_type.lower() == "applications":
            logger.info("Executing \"get_top_applications\" API call...")
            data = api.get_top_applications(start_datetime=start_datetime, end_datetime=end_datetime,
                                            subject_tags_includes=subject_tags_includes,
                                            subject_tags_excludes=subject_tags_excludes,
                                            subject_addresses_includes=subject_addresses_includes,
                                            subject_addresses_excludes=subject_addresses_excludes,
                                            peer_tags_includes=peer_tags_includes, peer_tags_excludes=peer_tags_excludes,
                                            peer_addresses_includes=peer_addresses_includes,
                                            peer_addresses_excludes=peer_addresses_excludes,
                                            subject_orientation=subject_orientation,
                                            connection_direction=connection_direction,
                                            connection_applications_includes=connection_applications_includes,
                                            connection_applications_excludes=connection_applications_excludes,
                                            connection_ports_protocols_includes=connection_ports_protocols_includes,
                                            connection_ports_protocols_excludes=connection_ports_protocols_excludes,
                                            flow_collectors=flow_collectors, order_by=order_by, max_rows=max_rows,
                                            exclude_bps_pps=exclude_bps_pps, exclude_others=exclude_others,
                                            exclude_counts=exclude_counts, status_check_frequency=status_check_frequency)
            logger.info("Done executing \"get_top_applications\" API call.")
        if report_type.lower() == "conversations":
            logger.info("Executing \"get_top_conversations\" API call...")
            data = api.get_top_conversations(start_datetime=start_datetime, end_datetime=end_datetime,
                                             subject_tags_includes=subject_tags_includes,
                                             subject_tags_excludes=subject_tags_excludes,
                                             subject_addresses_includes=subject_addresses_includes,
                                             subject_addresses_excludes=subject_addresses_excludes,
                                             peer_tags_includes=peer_tags_includes, peer_tags_excludes=peer_tags_excludes,
                                             peer_addresses_includes=peer_addresses_includes,
                                             peer_addresses_excludes=peer_addresses_excludes,
                                             subject_orientation=subject_orientation,
                                             connection_direction=connection_direction,
                                             connection_applications_includes=connection_applications_includes,
                                             connection_applications_excludes=connection_applications_excludes,
                                             connection_ports_protocols_includes=connection_ports_protocols_includes,
                                             connection_ports_protocols_excludes=connection_ports_protocols_excludes,
                                             flow_collectors=flow_collectors, order_by=order_by, max_rows=max_rows,
                                             exclude_bps_pps=exclude_bps_pps, exclude_others=exclude_others,
                                             exclude_counts=exclude_counts, status_check_frequency=status_check_frequency)
            logger.info("Done executing \"get_top_conversations\" API call.")
        if report_type.lower() == "hosts":
            logger.info("Executing \"get_top_hosts\" API call...")
            data = api.get_top_hosts(start_datetime=start_datetime, end_datetime=end_datetime,
                                     subject_tags_includes=subject_tags_includes,
                                     subject_tags_excludes=subject_tags_excludes,
                                     subject_addresses_includes=subject_addresses_includes,
                                     subject_addresses_excludes=subject_addresses_excludes,
                                     peer_tags_includes=peer_tags_includes, peer_tags_excludes=peer_tags_excludes,
                                     peer_addresses_includes=peer_addresses_includes,
                                     peer_addresses_excludes=peer_addresses_excludes,
                                     subject_orientation=subject_orientation, connection_direction=connection_direction,
                                     connection_applications_includes=connection_applications_includes,
                                     connection_applications_excludes=connection_applications_excludes,
                                     connection_ports_protocols_includes=connection_ports_protocols_includes,
                                     connection_ports_protocols_excludes=connection_ports_protocols_excludes,
                                     flow_collectors=flow_collectors, order_by=order_by, max_rows=max_rows,
                                     exclude_bps_pps=exclude_bps_pps, exclude_others=exclude_others,
                                     exclude_counts=exclude_counts, status_check_frequency=status_check_frequency)
            logger.info("Done executing \"get_top_hosts\" API call.")
        if report_type.lower() == "peers":
            logger.info("Executing \"get_top_peers\" API call...")
            data = api.get_top_peers(start_datetime=start_datetime, end_datetime=end_datetime,
                                     subject_tags_includes=subject_tags_includes,
                                     subject_tags_excludes=subject_tags_excludes,
                                     subject_addresses_includes=subject_addresses_includes,
                                     subject_addresses_excludes=subject_addresses_excludes,
                                     peer_tags_includes=peer_tags_includes, peer_tags_excludes=peer_tags_excludes,
                                     peer_addresses_includes=peer_addresses_includes,
                                     peer_addresses_excludes=peer_addresses_excludes,
                                     subject_orientation=subject_orientation, connection_direction=connection_direction,
                                     connection_applications_includes=connection_applications_includes,
                                     connection_applications_excludes=connection_applications_excludes,
                                     connection_ports_protocols_includes=connection_ports_protocols_includes,
                                     connection_ports_protocols_excludes=connection_ports_protocols_excludes,
                                     flow_collectors=flow_collectors, order_by=order_by, max_rows=max_rows,
                                     exclude_bps_pps=exclude_bps_pps, exclude_others=exclude_others,
                                     exclude_counts=exclude_counts, status_check_frequency=status_check_frequency)
            logger.info("Done executing \"get_top_peers\" API call.")
        if report_type.lower() == "ports":
            logger.info("Executing \"get_top_ports\" API call...")
            data = api.get_top_ports(start_datetime=start_datetime, end_datetime=end_datetime,
                                     subject_tags_includes=subject_tags_includes,
                                     subject_tags_excludes=subject_tags_excludes,
                                     subject_addresses_includes=subject_addresses_includes,
                                     subject_addresses_excludes=subject_addresses_excludes,
                                     peer_tags_includes=peer_tags_includes, peer_tags_excludes=peer_tags_excludes,
                                     peer_addresses_includes=peer_addresses_includes,
                                     peer_addresses_excludes=peer_addresses_excludes,
                                     subject_orientation=subject_orientation, connection_direction=connection_direction,
                                     connection_applications_includes=connection_applications_includes,
                                     connection_applications_excludes=connection_applications_excludes,
                                     connection_ports_protocols_includes=connection_ports_protocols_includes,
                                     connection_ports_protocols_excludes=connection_ports_protocols_excludes,
                                     flow_collectors=flow_collectors, order_by=order_by, max_rows=max_rows,
                                     exclude_bps_pps=exclude_bps_pps, exclude_others=exclude_others,
                                     exclude_counts=exclude_counts, status_check_frequency=status_check_frequency)
            logger.info("Done executing \"get_top_ports\" API call.")
        if report_type.lower() == "protocols":
            logger.info("Executing \"get_top_protocols\" API call...")
            data = api.get_top_protocols(start_datetime=start_datetime, end_datetime=end_datetime,
                                         subject_tags_includes=subject_tags_includes,
                                         subject_tags_excludes=subject_tags_excludes,
                                         subject_addresses_includes=subject_addresses_includes,
                                         subject_addresses_excludes=subject_addresses_excludes,
                                         peer_tags_includes=peer_tags_includes, peer_tags_excludes=peer_tags_excludes,
                                         peer_addresses_includes=peer_addresses_includes,
                                         peer_addresses_excludes=peer_addresses_excludes,
                                         subject_orientation=subject_orientation, connection_direction=connection_direction,
                                         connection_applications_includes=connection_applications_includes,
                                         connection_applications_excludes=connection_applications_excludes,
                                         connection_ports_protocols_includes=connection_ports_protocols_includes,
                                         connection_ports_protocols_excludes=connection_ports_protocols_excludes,
                                         flow_collectors=flow_collectors, order_by=order_by, max_rows=max_rows,
                                         exclude_bps_pps=exclude_bps_pps, exclude_others=exclude_others,
                                         exclude_counts=exclude_counts, status_check_frequency=status_check_frequency)
            logger.info("Done executing \"get_top_protocols\" API call.")
        if report_type.lower() == "services":
            logger.info("Executing \"get_top_services\" API call...")
            data = api.get_top_services(start_datetime=start_datetime, end_datetime=end_datetime,
                                        subject_tags_includes=subject_tags_includes,
                                        subject_tags_excludes=subject_tags_excludes,
                                        subject_addresses_includes=subject_addresses_includes,
                                        subject_addresses_excludes=subject_addresses_excludes,
                                        peer_tags_includes=peer_tags_includes, peer_tags_excludes=peer_tags_excludes,
                                        peer_addresses_includes=peer_addresses_includes,
                                        peer_addresses_excludes=peer_addresses_excludes,
                                        subject_orientation=subject_orientation, connection_direction=connection_direction,
                                        connection_applications_includes=connection_applications_includes,
                                        connection_applications_excludes=connection_applications_excludes,
                                        connection_ports_protocols_includes=connection_ports_protocols_includes,
                                        connection_ports_protocols_excludes=connection_ports_protocols_excludes,
                                        flow_collectors=flow_collectors, order_by=order_by, max_rows=max_rows,
                                        exclude_bps_pps=exclude_bps_pps, exclude_others=exclude_others,
                                        exclude_counts=exclude_counts, status_check_frequency=status_check_frequency)
            logger.info("Done executing \"get_top_services\" API call.")

        ############################################################################################################
        # Get Host Group Data for Mapping
        ############################################################################################################
        if data is not None and "results" in data and report_type.lower() in ["conversations", "hosts", "peers"]:
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

        if data is not None and "results" in data and report_type.lower() in ["conversations", "ports"]:
            service_definitions_tmp = api.get_service_definitions()
            for item in service_definitions_tmp["service-definitions"]["services"]["service"]:
                service_definitions[item["profile"]] = item["name"]
            protocol_map = api.get_protocol_list(surpress_std_out=True)

        ############################################################################################################
        # LOGOUT the session
        ############################################################################################################
        logger.info("De-authenticating API connection...")
        api.logout()
        logger.info("Done de-authenticating API connection.")

        if data is not None and "results" in data:
            if "summary" in data:
                this_row = process_row(report_type.lower(), "summary", data["summary"], host_group_dict, protocol_map,
                                       service_definitions, max_rows)
                results.append(this_row)
            if "others" in data:
                this_row = process_row(report_type.lower(), "others", data["others"], host_group_dict, protocol_map,
                                       service_definitions, max_rows)
                results.append(this_row)

            data = data["results"]
            for row in data:
                this_row = process_row(report_type.lower(), "results", row, host_group_dict, protocol_map,
                                       service_definitions, max_rows)
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

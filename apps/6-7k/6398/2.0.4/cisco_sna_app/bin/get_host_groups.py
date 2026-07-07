# ==========================================================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# get_top_ports.py script for use with Splunk enterprise to fetch top peers
# from StealthWatch using the RESTx appliance REST API extension service
# ==========================================================================================================

# Usage: |hostgroups [group_type=<internal|external|geos|threats|custom|all>] [domain_id=<domain_id>]

############################################################################################################
# Get some libraries we will need
############################################################################################################

import splunk_utility
import traceback
import splunk
import splunk.Intersplunk

import stealthwatch_api_client


def traverse_all_host_groups(results, parent_host_group, children, include_countries=None):
    if not isinstance(children, list):
        children = [children]
    for child in children:
        this_group_name = parent_host_group + "/" + child['name']
        if (include_countries is None or include_countries is False) and this_group_name == "Outside Hosts/Countries":
            return results
        results.append({'hostGroupPath': this_group_name, "id": int(child['id'])})
        if 'host-group' in child:
            if not isinstance(child['host-group'], list):
                child['host-group'] = [child['host-group']]
            results = traverse_all_host_groups(results, this_group_name, child['host-group'])
    return results


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
    group_type = kwargs.get('group_type')
    domain_id = kwargs.get('domain_id')
    smc_ip = kwargs.get('smc_ip')

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
        sw_version = api.get_version_info()
        if sw_version[0] < 6 or (sw_version[0] == 6 and sw_version[1] < 10):
            logger.info("Executing \"get_host_groups\" API call...")
            data = api.get_host_groups()
            logger.info("Done executing \"get_host_groups\" API call.")
        else:
            if group_type is None:
                group_type = "all"

            if group_type.lower() == "internal":
                logger.info("Executing \"get_internal_hosts_tree\" API call...")
                data = api.get_internal_hosts_tree()
                logger.info("Done executing \"get_internal_hosts_tree\" API call.")
            if group_type.lower() == "external":
                logger.info("Executing \"get_external_hosts_tree\" API call...")
                data = api.get_external_hosts_tree()
                logger.info("Done executing \"get_external_hosts_tree\" API call.")
            if group_type.lower() == "geos":
                logger.info("Executing \"get_external_geo_tree\" API call...")
                data = api.get_external_geo_tree()
                logger.info("Done executing \"get_external_geo_tree\" API call.")

            if group_type.lower() == "threats":
                logger.info("Executing \"get_external_threats_tree\" API call...")
                data = api.get_external_threats_tree()
                logger.info("Done executing \"get_external_threats_tree\" API call.")

            if group_type.lower() == "custom":
                logger.info("Executing \"get_custom_hosts_tree\" API call...")
                data = api.get_custom_hosts_tree()
                logger.info("Done executing \"get_custom_hosts_tree\" API call.")

            if group_type.lower() == "all":
                logger.info("Executing \"get_external_geo_tree\" API call...")
                data = api.get_host_groups()
                logger.info("Done executing \"get_external_geo_tree\" API call.")

        ############################################################################################################
        # LOGOUT the session
        ############################################################################################################
        logger.info("De-authenticating API connection...")
        api.logout()
        logger.info("Done de-authenticating API connection.")

        if data is not None:
            if (sw_version[0] < 6 or (sw_version[0] == 6 and sw_version[1] < 10)) and group_type.lower() != "all":
                if group_type.lower() == "internal":
                    results.append({'hostGroupPath': "Inside Hosts", "id": 1})
                    results = traverse_all_host_groups(results, "Inside Hosts", data['inside-hosts']['host-group'])
                if group_type.lower() == "external":
                    results.append({'hostGroupPath': "Outside Hosts", "id": 0})
                    results = traverse_all_host_groups(results, "Outside Hosts", data['outside-hosts']['host-group'])
                if group_type.lower() == "geos":
                    for host_group in data['outside-hosts']['host-group']:
                        country_base_id = 60000
                        if host_group['name'] == "Countries":
                            country_host_group = host_group
                    results.append({'hostGroupPath': "Countries", "id": country_host_group["id"]})
                    results = traverse_all_host_groups(results, "Countries", country_host_group['host-group'])
            elif group_type.lower() == "all":
                results.append({'hostGroupPath': "Inside Hosts", "id": 1})
                results = traverse_all_host_groups(results, "Inside Hosts", data['inside-hosts']['host-group'])
                results.append({'hostGroupPath': "Outside Hosts", "id": 0})
                results = traverse_all_host_groups(results, "Outside Hosts", data['outside-hosts']['host-group'], include_countries=True)
            else:
                results = [{'hostGroupPath': host_group, 'id': id} for id, host_group in splunk_utility.traverse_host_groups(data, "", {}).items()]

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

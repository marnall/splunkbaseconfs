# ==========================================================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# get_top_ports.py script for use with Splunk enterprise to fetch top peers
# from StealthWatch using the RESTx appliance REST API extension service
# ==========================================================================================================

# Usage: |flowtrends [smc_ip=<smc_ip>] [domain_id=<domain_id>] [number_days_back=<number_days_back>]

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
    smc_ip = kwargs.get('smc_ip')
    domain_id = kwargs.get('domain_id')
    number_days_back = kwargs.get('number_days_back')

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
        logger.info("Executing \"get_flow_trend\" API call...")
        data = api.get_flow_trend(number_days_back=number_days_back)
        logger.info("Done executing \"get_flow_trend\" API call.")

        ############################################################################################################
        # LOGOUT the session
        ############################################################################################################
        logger.info("De-authenticating API connection...")
        api.logout()
        logger.info("Done de-authenticating API connection.")

        totals_trends = {}

        if data is not None and len(data) > 0:
            for collector in data:
                if "trend" in collector and len(collector["trend"]) > 0:
                    for trend in collector["trend"]:
                        this_result = {
                            "deviceId": collector["deviceId"],
                            "deviceName": collector["deviceName"],
                            "domainId": collector["domainId"],
                            "flowCount": trend["flowCount"],
                            "fps": trend["fps"],
                            "time": trend["time"]
                        }
                        results.append(this_result)
                        if trend["time"] not in list(totals_trends.keys()):
                            totals_trends[trend["time"]] = {
                                "deviceId": 0,
                                "deviceName": "(Total)",
                                "domainId": collector["domainId"],
                                "flowCount": 0,
                                "fps": 0,
                                "time": trend["time"]
                            }
                        totals_trends[trend["time"]]["flowCount"] += trend["flowCount"]
                        totals_trends[trend["time"]]["fps"] += trend["fps"]
            for val in list(totals_trends.values()):
                results.append(val)

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

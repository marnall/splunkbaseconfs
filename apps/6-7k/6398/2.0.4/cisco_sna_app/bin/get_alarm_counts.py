# ==========================================================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# get_top_ports.py script for use with Splunk enterprise to fetch top peers
# from StealthWatch using the RESTx appliance REST API extension service
# ==========================================================================================================

# Usage: |alarmcounts [smc_ip=<smc_ip>] [domain_id=<domain_id>] [ip_address=<ip_address>] [number_of_days_back=<number_of_days_back>]

############################################################################################################
# Get some libraries we will need
############################################################################################################

import splunk_utility
import traceback
import splunk
import splunk.Intersplunk

import stealthwatch_api_client


def main():
    logger = splunk_utility.setup_logging(splunk_utility.myapp)
    logger.info("")
    logger.info("API process started...")

    ############################################################################################################
    # Process the arguments
    ############################################################################################################
    args, kwargs = splunk_utility.parse_args()
    smc_ip = kwargs.get('smc_ip')
    domain_id = kwargs.get('domain_id')
    ip_address = kwargs.get('ip_address')
    number_of_days_back = kwargs.get('number_of_days_back')

    if ip_address is None or len(str(ip_address)) <= 0:
        ip_address = None

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
        logger.info("Executing \"get_daily_alarm_types\" API call...")
        data = api.get_daily_alarm_types(ip_address=ip_address, number_of_days_back=number_of_days_back)
        logger.info("Done executing \"get_daily_alarm_types\" API call.")

        ############################################################################################################
        # LOGOUT the session
        ############################################################################################################
        # Disabling Logout as it is causing 401 unauthenticated
        # logger.info("De-authenticating API connection...")
        # api.logout()
        # logger.info("Done de-authenticating API connection.")

        if data is not None and "series" in data and len(data["series"]) > 0:
            for row in data["series"]:
                date_count = 0
                for alarm_count in row["data"]:
                    this_row = {}
                    this_row["id"] = row["id"]
                    this_row["name"] = row["name"]
                    this_row["count"] = alarm_count
                    this_row["display_date"] = data["categories"][date_count]["displayDay"]
                    this_row["date"] = data["categories"][date_count]["startDay"]
                    results.append(this_row)
                    date_count += 1

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

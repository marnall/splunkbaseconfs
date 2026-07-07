# ==========================================================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# get_top_ports.py script for use with Splunk enterprise to fetch top peers
# from StealthWatch using the RESTx appliance REST API extension service
# ==========================================================================================================

# Usage: |securityeventdescriptions [domain_id=<domain_id>] [smc_ip=<smc_ip>]

############################################################################################################
# Get some libraries we will need
############################################################################################################

import splunk_utility
import traceback
import splunk
import splunk.Intersplunk
import html.parser

import stealthwatch_api_client

class MLStripper(html.parser.HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)


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
        seen_event_ids = set()
        sw_version = api.get_version_info()
        if sw_version[0] < 6 or (sw_version[0] == 6 and sw_version[1] < 10):
            logger.info("Executing \"get_security_events_metadata\" API call...")
            results_tmp = api.get_security_events_metadata()
            logger.info("Done executing \"get_security_events_metadata\" API call.")
            if results_tmp is not None:
                for event in results_tmp:
                    tag_stripper = MLStripper()
                    tag_stripper.feed(tag_stripper.unescape(event["description"]))
                    description = tag_stripper.get_data()
                    results.append({"name" : event["display-name"], "description" : description, "id" : int(event["id"])})
                    seen_event_ids.add(int(event["id"]))
        else:
            logger.info("Executing \"get_security_event_descriptions\" API call...")
            results = api.get_security_event_descriptions()
            logger.info("Done executing \"get_security_event_descriptions\" API call.")
            for event in results:
                seen_event_ids.add(int(event["id"]))

        logger.info("Executing \"get_custom_security_events\" API call...")
        custom_security_event_descriptions = api.get_custom_security_events()
        logger.info("Done executing \"get_custom_security_events\" API call.")
        if custom_security_event_descriptions is not None and "customSecurityEvents" in custom_security_event_descriptions:
            for event in custom_security_event_descriptions["customSecurityEvents"]:
                if not int(event["id"]) in seen_event_ids:
                    description = " "
                    if "description" in event:
                        description = event["description"]
                    event_name = ""
                    if "display-name" in event:
                        event_name = event["display-name"]
                    else:
                        event_name = event["name"]
                    results.append({"name": event_name, "description": description, "id": int(event["id"])})

        ############################################################################################################
        # LOGOUT the session
        ############################################################################################################
        logger.info("De-authenticating API connection...")
        api.logout()
        logger.info("Done de-authenticating API connection.")


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

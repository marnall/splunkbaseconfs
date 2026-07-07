# ==========================================================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# get_top_ports.py script for use with Splunk enterprise to fetch top peers
# from StealthWatch using the RESTx appliance REST API extension service
# ==========================================================================================================

# Usage: |domainlist [smc_ip=<smc_ip>]

############################################################################################################
# Get some libraries we will need
############################################################################################################
import traceback

# splunkhome = os.environ['SPLUNK_HOME']
# apphome = os.path.join(splunkhome, 'etc', 'apps', 'cisco_sna_app')
# sys.path.append(os.path.join(apphome, 'bin'))

import splunk
import splunk.Intersplunk
import splunk_utility
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

    try:

        ############################################################################################################
        # LOGIN to RESTx API Extension appliance
        ############################################################################################################
        logger.info("Authenticating API connection...")
        api = stealthwatch_api_client.stealthwatch_api()
        api.login(smc_ip, config["smcID"], config["smcPW"], requests_disable_warnings=False)
        logger.info("Done authenticating API connection.")

        ############################################################################################################
        # FETCH the necessary data_all by issuing a REST request to the RESTx
        ############################################################################################################
        logger.info("Executing \"get_domains\" API call...")
        data = api.get_domains()
        logger.info("Done executing \"get_domains\" API call.")

        ############################################################################################################
        # LOGOUT the session
        ############################################################################################################
        # Disabling Logout as it is causing 401 unauthenticated
        # logger.info("De-authenticating API connection...")
        # api.logout()
        # logger.info("Done de-authenticating API connection.")

        if data is not None:
            for domain in data:
                domain_id = domain['id']
                domain_name = domain['displayName']
                if "smcDomainID" in config and str(config["smcDomainID"]) == str(domain_id):
                    results.insert(0, {"id": domain_id, "name": domain_name})
                else:
                    results.append({"id": domain_id, "name": domain_name})

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

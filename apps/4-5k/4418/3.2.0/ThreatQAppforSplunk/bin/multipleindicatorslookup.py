import threatquotient_app_declare
import sys
import json
import re
import traceback
import logger_manager as log
import splunk.Intersplunk
import threatq_utils as tq_utils
from solnlib.utils import is_true
from threatq_const import VERIFY_SSL
import requests

logger = log.setup_logging("threatquotient_app_multiple_indicator_lookup")

def main_():
    try:
        logger.info("starting_the_execution | Starting the execution to fetch lookup for multiple indicators.")
        results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
        sessionKey = settings.get("sessionKey")

        if len(sys.argv) == 1 and (not results or ((len(results) == 1 and not results[0]))):
            splunk.Intersplunk.parseError("No results found for the provided Splunk search query.")
            sys.exit(-1)

        logger.info("fetching_account_details | Fetching the details of configured account.")
        account_info = tq_utils.get_credentials(sessionKey)
        proxies = tq_utils.get_proxy_info(sessionKey)
        if not account_info:
            logger.error(
                "ThreatQuotient Error: Failed to obtain App's Account configuration to execute the request."
            )
            splunk.Intersplunk.parseError(
                "Failed to obtain App's Account configuration to execute the request."
            )
            sys.exit(-1)
        logger.info("fetched_sucessfully | Account details fetched successfully.")

        list_of_iocs = []
        if len(sys.argv) == 1: 
            logger.debug("search_query_option_selected | Enter Search Query option has been selected.")
            keys = list(results[0].keys())
            if len(keys) == 0:
                splunk.Intersplunk.parseError("No results found for the provided Splunk search query.")
                sys.exit(-1)
            original_key = keys[0] if keys[0] != 'Select' else keys[1] if len(keys) > 1 else None
            regular_dict_list = [{ 'value': item[original_key] } for item in results]
            list_of_iocs = json.dumps(regular_dict_list)
            list_of_iocs = json.loads(list_of_iocs)
        else:
            logger.debug("manual_indicator_option_selected | Enter Indicators Manually option has been selected.")
            ioc_value_arg = sys.argv[1]
            ioc_value = ioc_value_arg.split("value=")[1]
            list_of_iocs = [{"value": ip.strip()} for ip in ioc_value.split(",")]

        verify_cert = VERIFY_SSL
        verify_cert = is_true(verify_cert)
        access_token = tq_utils.get_access_token(account_info=account_info, proxies=proxies)
        if not access_token:
            logger.error("ThreatQuotient Error: Error while generating token")
            splunk.Intersplunk.parseError(
                "Error while generating token. Please check the configuration"
            )
            sys.exit(-1)
        logger.debug("fetched_access_token | Successfully fetched the access token.")

        endpoint = "/api/indicators/query"
        request_url = "{scheme}{url}{endpoint}".format(
            scheme="https://", url=account_info["server_url"], endpoint=endpoint
        )
        request_headers = {"Authorization": "Bearer {}".format(access_token)}
        limit = 100 
        offset = 0
        results = []
        body = {
            "fields": ["id", "value", "updated_at", "type", "status", "adversaries", "sources" ,"attributes", "score"],
            "criteria": {
                "+or": list_of_iocs
            }
        }
        auth_type = account_info.get('authorization_type', 'basic_auth')
        logger.debug("fetching_results | Fetching the result for multiple indicators.")
        while True:
            params = {
                "limit": limit,
                "offset": offset
            }
            if auth_type == "cac_auth":
                request_response = requests.post(
                    request_url,
                    json=body,
                    params=params,
                    headers=request_headers,
                    cert=tq_utils._get_cac_cert_tuple(logger),
                    verify=verify_cert,
                    proxies=proxies,
                )
            else:
                request_response = requests.post(
                    request_url,
                    json=body,
                    params=params,
                    headers=request_headers,
                    verify=verify_cert,
                    proxies=proxies,
                )
            if request_response.status_code != 200:
                logger.error("error_occured | An Error occured. Response: {}".format(request_response.text))
                break
            response_json = request_response.json()
            results.extend(response_json.get("data", []))
            if len(response_json.get("data", [])) < limit:
                break
            offset += limit
        final_response = results
        tq_utils.process_multi_lookup_events(final_response)
        splunk.Intersplunk.outputResults(final_response)
        if final_response:
            logger.info("fetched_results | Successfully fetched the result for multiple indicators.")
        else:
            logger.info("no_results_fetched | No results fetched.")
        logger.info("execution_completed | Successfully completed the execution.")
    except Exception:
        logger.error("error_occured | Error occured while getting indicators = {}".format(traceback.format_exc()))
        splunk.Intersplunk.parseError(
            "Error while getting indicators. Please check the 'threatquotient_app_multiple_indicator_lookup.log' log file."
        )
        sys.exit(-1)

if __name__ == "__main__":
    main_()

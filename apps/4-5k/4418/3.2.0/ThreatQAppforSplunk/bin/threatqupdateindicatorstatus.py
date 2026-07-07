import threatquotient_app_declare
import sys

import requests

import logger_manager as log
import splunk.Intersplunk
import threatq_utils as tq_utils
from solnlib.utils import is_true
from threatq_const import VERIFY_SSL

MACRO_CRED_CONF = "workflow_action_using_conf"


def _update_indicator(auth_type, access_token, server_url, proxies, indicator_id, verify_cert, status, logger):
    """Use to update the indicator on ThreatQ based on its ID."""
    endpoint = "/api/indicators/{id}".format(id=indicator_id)
    request_url = "{scheme}{url}{endpoint}".format(
        scheme="https://", url=server_url, endpoint=endpoint
    )
    
    request_body = {"status_id": status}

    request_headers = {"Authorization": "Bearer {}".format(access_token)}

    request_params = {"with": "type,status,score,adversaries,sources,attributes"}

    if auth_type == "cac_auth":
        response = requests.put(
            request_url,
            headers=request_headers,
            verify=verify_cert,
            params=request_params,
            data=request_body,
            cert=tq_utils._get_cac_cert_tuple(logger),
            proxies=proxies,
        )
    else:
        response = requests.put(
            request_url,
            headers=request_headers,
            verify=verify_cert,
            params=request_params,
            data=request_body,
            proxies=proxies,
        )

    # If response is not success
    if response.status_code != 201:
        try:
            response_json = response.json()
            errors = ", ".join(response_json.get("data").get("errors").get("value"))
        except Exception:
            raise Exception(str(response.text))
        raise Exception(str(errors))

    response = response.json()

    return [response["data"]]


def main_():

    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    sessionKey = settings.get("sessionKey")

    logger = log.setup_logging("threatquotient_update_indicator")
 
    serviceobj = tq_utils.create_service(sessionKey)
    try:
        is_conf_parse = is_true(tq_utils.get_macro_definition(serviceobj, MACRO_CRED_CONF))
        account_info = tq_utils.get_credentials(sessionKey, conf_parse=is_conf_parse)
        proxies = tq_utils.get_proxy_info(sessionKey, proxy_config_parse=is_conf_parse)
        access_token = tq_utils.get_access_token(account_info=account_info, proxies=proxies)
        verify_cert = VERIFY_SSL
        verify_cert = is_true(verify_cert)

        if not account_info:
            logger.error(
                "ThreatQuotient Error: Failed to obtain App's Account configuration to execute the request."
            )
            splunk.Intersplunk.parseError(
                 "Failed to obtain App's Account configuration to execute the request."
            )
            sys.exit(-1)
        if len(sys.argv) != 4:
            logger.error("ThreatQuotient Error: Invalid number of arguments provided")
            splunk.Intersplunk.parseError("Invalid number of arguments provided")
            sys.exit(-1)

        indicator_status_id = None
        indicator_value = None
        indicator_source = None

        for i in range(1, 4):
            if "status_id=" in sys.argv[i]:
                indicator_status_id = sys.argv[i].split("status_id=")[1]
            elif "value=" in sys.argv[i]:
                indicator_value = sys.argv[i].split("value=")[1]
            elif "source=" in sys.argv[i]:
                indicator_source = sys.argv[i].split("source=")[1]
        
        indicator_list = tq_utils.get_indicator_from_value(
            auth_type=account_info.get('authorization_type', 'basic_auth'),
            access_token=access_token,
            server_url=account_info["server_url"],
            proxies=proxies,
            indicator_value=indicator_value,
            verify_cert=verify_cert,
        )

        indicator_id = None
        for indicator in indicator_list:
            if indicator["value"] == indicator_value:
                indicator_id = indicator["id"]
                break

        # Validate the provided argument
        if not (indicator_value and indicator_status_id and indicator_source):
            logger.error(
                "ThreatQuotient Error: Invalid arguments provided. Please provide "
                "required arguments value, status_id, source"
            )
            splunk.Intersplunk.parseError(
                "Invalid arguments provided. Please provide required arguments value,"
                " status_id, source"
            )
            sys.exit(-1)

        try:
            indicator_status_id = int(indicator_status_id)
            if indicator_status_id < 1:
                raise Exception("Invalid status_id provided")
        except Exception:
            logger.error("ThreatQuotient Error: Invalid status_id provided")
            splunk.Intersplunk.parseError("Invalid status_id provided")
            sys.exit(-1)

        if not access_token:
            logger.error("ThreatQuotient Error: Error while generating token")
            splunk.Intersplunk.parseError(
                "Error while generating token. Please check the configuration"
            )
            sys.exit(-1)


        try:
            output_result = _update_indicator(
                auth_type=account_info.get('authorization_type', 'basic_auth'),
                access_token=access_token,
                server_url=account_info["server_url"],
                proxies=proxies,
                indicator_id=indicator_id,
                verify_cert=verify_cert,
                status=indicator_status_id,
                logger=logger
            )
        except Exception as e:
            logger.error("ThreatQuotient Error: Error while updating indicator. {}".format(e))
            splunk.Intersplunk.parseError("Error while updating indicator. {}".format(e))
            sys.exit(-1)

        if output_result:
            tq_utils.process_events(output_result)
            output_result[0]["url"] = tq_utils.get_indicator_url(
                account_info["server_url"], indicator_id
            )
            splunk.Intersplunk.outputResults(output_result)
    except Exception:
        import traceback
        logger.error("Traceback : {}".format(traceback.format_exc()))

if __name__ == "__main__":
    main_()

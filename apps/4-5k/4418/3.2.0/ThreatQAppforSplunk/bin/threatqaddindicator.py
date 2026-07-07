import threatquotient_app_declare
import sys
import splunk.clilib.cli_common
import requests

import logger_manager as log
import splunk.Intersplunk
import threatq_utils as tq_utils
from solnlib.utils import is_true
from threatq_const import VERIFY_SSL

MACRO_CRED_CONF = "workflow_action_using_conf"


def _create_indicator(
    account_info, proxies, access_token, logger, value, type_id, status_id, source,
):
    """Create an indicator on ThreatQ based on the value provided."""
    server_url = account_info["server_url"]
    server_url = server_url.strip("/")
    endpoint = "/api/indicators"
    request_url = "{scheme}{url}{endpoint}".format(
        scheme="https://", url=server_url, endpoint=endpoint
    )
    verify_cert = VERIFY_SSL
    verify_cert = is_true(verify_cert)

    request_data = {
        "value": value,
        "status_id": status_id,
        "type_id": type_id,
        "sources": [{"name": source}],
    }

    request_headers = {"Authorization": "Bearer {}".format(access_token)}
    auth_type = account_info.get('authorization_type', 'basic_auth')
    if auth_type == "cac_auth":
        response = requests.post(
            request_url,
            json=request_data,
            headers=request_headers,
            verify=verify_cert,
            cert=tq_utils._get_cac_cert_tuple(logger),
            proxies=proxies,
        )
    else:
        response = requests.post(
            request_url,
            json=request_data,
            headers=request_headers,
            verify=verify_cert,
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

    return response["data"]


def main_():
    
    logger = log.setup_logging("threatquotient_add_indicator")
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    sessionKey = settings.get("sessionKey")
    serviceobj = tq_utils.create_service(sessionKey)
    is_conf_parse = is_true(tq_utils.get_macro_definition(serviceobj, MACRO_CRED_CONF))
    account_info = tq_utils.get_credentials(sessionKey, conf_parse=is_conf_parse)
    proxies = tq_utils.get_proxy_info(sessionKey, proxy_config_parse=is_conf_parse)
    if not account_info:
        logger.error(
            "ThreatQuotient Error: Failed to obtain App's Account configuration to execute the request."
        )
        splunk.Intersplunk.parseError(
            "Failed to obtain App's Account configuration to execute the request."
        )
        sys.exit(-1)

    if len(sys.argv) != 5:
        logger.error("ThreatQuotient Error: Invalid number of arguments provided")
        splunk.Intersplunk.parseError("Invalid number of arguments provided")
        sys.exit(-1)

    indicator_value = None
    indicator_type_id = None
    indicator_status_id = None
    indicator_source = None
    for i in range(1, 5):
        if "value=" in sys.argv[i]:
            indicator_value = sys.argv[i].split("value=")[1]
        elif "type_id=" in sys.argv[i]:
            indicator_type_id = sys.argv[i].split("type_id=")[1]
        elif "status_id=" in sys.argv[i]:
            indicator_status_id = sys.argv[i].split("status_id=")[1]
        elif "source=" in sys.argv[i]:
            indicator_source = sys.argv[i].split("source=")[1]

    # Validate the provided argument
    if not (indicator_value and indicator_type_id and indicator_status_id and indicator_source):
        logger.error(
            "ThreatQuotient Error: Invalid arguments provided. Please provide "
            "required arguments value, type_id, status_id, source"
        )
        splunk.Intersplunk.parseError(
            "Invalid arguments provided. Please provide required arguments value,"
            " type_id, status_id, source"
        )
        sys.exit(-1)

    try:
        indicator_type_id = int(indicator_type_id)
        if indicator_type_id < 1:
            raise Exception("Invalid type_id provided")
    except Exception:
        logger.error("ThreatQuotient Error: Invalid type_id provided")
        splunk.Intersplunk.parseError("Invalid type_id provided")
        sys.exit(-1)

    try:
        indicator_status_id = int(indicator_status_id)
        if indicator_status_id < 1:
            raise Exception("Invalid status_id provided")
    except Exception:
        logger.error("ThreatQuotient Error: Invalid status_id provided")
        splunk.Intersplunk.parseError("Invalid status_id provided")
        sys.exit(-1)

    access_token = tq_utils.get_access_token(account_info=account_info, proxies=proxies)

    if not access_token:
        logger.error("ThreatQuotient Error: Error while generating token")
        splunk.Intersplunk.parseError(
            "Error while generating token. Please check the configuration"
        )
        sys.exit(-1)

    try:
        output_result = _create_indicator(
            account_info,
            proxies,
            access_token,
            logger,
            indicator_value,
            indicator_type_id,
            indicator_status_id,
            indicator_source,
        )
    except Exception as e:
        logger.error("ThreatQuotient Error: Error while adding indicator. {}".format(e))
        splunk.Intersplunk.parseError("Error while adding indicator. {}".format(e))
        sys.exit(-1)

    if output_result:
        output_result[0]["type"] = output_result[0].get("type", {}).get("name")
        output_result[0]["sources"] = [
            "name: {}, tlp_id: {}".format(src.get("name"), src.get("tlp_id"))
            for src in output_result[0].get("sources", [])
            if src
        ]
        output_result[0]["url"] = tq_utils.get_indicator_url(
            account_info["server_url"], output_result[0]["id"]
        )
        splunk.Intersplunk.outputResults(output_result)


if __name__ == "__main__":
    main_()

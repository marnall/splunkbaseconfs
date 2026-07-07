import threatquotient_app_declare
import sys

import requests

import logger_manager as log
import splunk.Intersplunk
import threatq_utils as tq_utils
from solnlib.utils import is_true
from threatq_const import VERIFY_SSL

MACRO_CRED_CONF = "workflow_action_using_conf"


def _add_indicator_attribute(
    access_token, server_url, proxies, indicator_id, attribute_name, attribute_value, verify_cert, auth_type, logger
):
    """Use to whitelist the indicator on ThreatQ based on its ID."""
    endpoint = "/api/indicators/{id}/attributes".format(id=indicator_id)
    request_url = "{scheme}{url}{endpoint}".format(
        scheme="https://", url=server_url, endpoint=endpoint
    )
    request_headers = {"Authorization": "Bearer {}".format(access_token)}

    request_body = {
        "name": attribute_name,
        "value": attribute_value,
        "sources": [{"name": "Splunk"}],
    }
    if auth_type == "cac_auth":
        response = requests.post(
            request_url,
            headers=request_headers,
            verify=verify_cert,
            cert=tq_utils._get_cac_cert_tuple(logger),
            json=request_body,
            proxies=proxies,
        )
    else:
        response = requests.post(
            request_url,
            headers=request_headers,
            verify=verify_cert,
            json=request_body,
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
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()

    logger = log.setup_logging("threatquotient_app_add_indicator_attribute")
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

    if len(sys.argv) != 4:
        logger.error("ThreatQuotient Error: Invalid number of arguments provided")
        splunk.Intersplunk.parseError("Invalid number of arguments provided")
        sys.exit(-1)

    indicator_value = None
    attribute_name = None
    attribute_value = None
    for i in range(1, 4):
        if "indicator_value=" in sys.argv[i]:
            indicator_value = sys.argv[i].split("indicator_value=")[1]
        elif "attribute_name=" in sys.argv[i]:
            attribute_name = sys.argv[i].split("attribute_name=")[1]
        elif "attribute_value=" in sys.argv[i]:
            attribute_value = sys.argv[i].split("attribute_value=")[1]

    # Validate the provided argument
    if not (indicator_value and attribute_name and attribute_value):
        logger.error(
            "ThreatQuotient Error: Invalid arguments provided. Please provide "
            "required arguments indicator_value, attribute_name, attribute_value"
        )
        splunk.Intersplunk.parseError(
            "Invalid arguments provided. Please provide required arguments "
            "indicator_value, attribute_name, attribute_value"
        )
        sys.exit(-1)

    access_token = tq_utils.get_access_token(account_info=account_info, proxies=proxies)

    verify_cert = VERIFY_SSL
    verify_cert = is_true(verify_cert)

    if not access_token:
        logger.error("ThreatQuotient Error: Error while generating token")
        splunk.Intersplunk.parseError(
            "Error while generating token. Please check the configuration"
        )
        sys.exit(-1)

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

    output_result = None
    if not indicator_id:
        logger.error(
            "ThreatQuotient Error: No indicator found with value {} on "
            "ThreatQuotient".format(indicator_value)
        )
        splunk.Intersplunk.parseError(
            "No indicator found with value {} on ThreatQuotient".format(indicator_value)
        )
        sys.exit(-1)

    try:
        output_result = _add_indicator_attribute(
            access_token=access_token,
            server_url=account_info["server_url"],
            proxies=proxies,
            indicator_id=indicator_id,
            attribute_name=attribute_name,
            attribute_value=attribute_value,
            verify_cert=verify_cert,
            auth_type=account_info.get('authorization_type', 'basic_auth'),
            logger=logger
        )
    except Exception as e:
        logger.error("ThreatQuotient Error: Error while adding attributes. {}".format(e))
        splunk.Intersplunk.parseError("Error while adding attributes. {}".format(e))
        sys.exit(-1)

    if (
        output_result
        and isinstance(output_result, list)
        and output_result[0]
        and isinstance(output_result[0], dict)
    ):
        output_result[0].pop("attribute", None)
        output_result[0]["sources"] = [
            "name: {}, tlp_id: {}".format(src.get("name"), src.get("tlp_id"))
            for src in output_result[0].get("sources", [])
            if src
        ]
        output_result[0]["indicator_value"] = indicator_value
        output_result[0]["url"] = tq_utils.get_indicator_url(
            account_info["server_url"], indicator_id
        )
        splunk.Intersplunk.outputResults(output_result)
    else:
        logger.error("ThreatQuotient Error: Error while adding attributes")
        splunk.Intersplunk.parseError("Error while adding attributes")
        sys.exit(-1)


if __name__ == "__main__":
    main_()

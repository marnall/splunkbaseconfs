import threatquotient_app_declare
import sys

import logger_manager as log
import splunk.Intersplunk
import threatq_utils as tq_utils
from solnlib.utils import is_true
from threatq_const import VERIFY_SSL

MACRO_CRED_CONF = "workflow_action_using_conf"


def main_():
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    sessionKey = settings.get("sessionKey")

    logger = log.setup_logging("threatquotient_app_lookup_indicator")
 
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

    if len(sys.argv) != 2:
        logger.error("ThreatQuotient Error: Invalid number of arguments provided")
        splunk.Intersplunk.parseError("Invalid number of arguments provided")
        sys.exit(-1)

    ioc_value_arg = sys.argv[1]

    # Validate the provided argument
    if "value=" not in ioc_value_arg:
        logger.error("ThreatQuotient Error: Invalid argument provided {}".format(ioc_value_arg))
        splunk.Intersplunk.parseError("Invalid argument provided {}".format(ioc_value_arg))
        sys.exit(-1)

    ioc_value = ioc_value_arg.split("value=")[1]

    verify_cert = VERIFY_SSL
    verify_cert = is_true(verify_cert)

    access_token = tq_utils.get_access_token(account_info=account_info, proxies=proxies)

    if not access_token:
        logger.error("ThreatQuotient Error: Error while generating token")
        splunk.Intersplunk.parseError(
            "Error while generating token. Please check the configuration"
        )
        sys.exit(-1)

    output_result = tq_utils.get_indicator_from_value(
        auth_type=account_info.get('authorization_type', 'basic_auth'),
        access_token=access_token,
        server_url=account_info["server_url"],
        proxies=proxies,
        indicator_value=ioc_value,
        verify_cert=verify_cert,
    )

    if output_result:
        tq_utils.process_events(output_result)
        output_result[0]["url"] = tq_utils.get_indicator_url(
            account_info["server_url"], output_result[0]["id"]
        )
        splunk.Intersplunk.outputResults(output_result)
    else:
        logger.error(
            "ThreatQuotient Error: No indicator found with value {} on "
            "ThreatQuotient".format(ioc_value)
        )
        splunk.Intersplunk.parseError(
            "No indicator found with value {} on ThreatQuotient".format(ioc_value)
        )
        sys.exit(-1)


if __name__ == "__main__":
    main_()

import ta_intsights_declare     # noqa: F401
import sys
import os
import json
import requests
from base64 import b64encode

from log_manager import setup_logging
import splunk.Intersplunk
import intsights_utils as int_utils
import constants as const


def _whitelist_indicator(header, url, proxies, indicator_value, verify_cert, logger):
    """Use to whitelist the indicator on IntSights based on its value."""
    post_data = json.dumps({
        "iocs": [
            {
                "value": str(indicator_value),
                "whitelisted": True
            }
        ]
    })
    response = requests.post(url, verify=verify_cert, headers=header, proxies=proxies, data=post_data)
    if response.status_code == 200 or response.status_code == 201:
        output_result = [{'Value': indicator_value, 'Whitelist': True,
                          'Note': 'IOC marked as Whitelist successfully!.'}]
        logger.info("IOC marked as Whitelist successfully!")
    else:
        output_result = [{'Value': indicator_value, 'Whitelist': False,
                          'Note': 'Failed to mark IOC as Whitelist!.'}]
        logger.error(
            "Failed to mark IOC as Whitelist!: Status Code: {} Error: {}".format(
                response.status_code, (response.content).decode()))
    return output_result


def main_():
    """Setup code."""
    logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0])

    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    sessionKey = settings.get("sessionKey")

    account_info = int_utils.get_credentials("account", sessionKey)
    proxies = int_utils.get_proxy_info(sessionKey)
    if not account_info:
        logger.error(
            "IntSights Error: Failed to obtain credentials required to execute the request"
        )
        splunk.Intersplunk.parseError(
            "Failed to obtain credentials required to execute the request"
        )
        sys.exit(-1)

    if len(sys.argv) != 2:
        logger.error("IntSights Error: Invalid number of arguments provided")
        splunk.Intersplunk.parseError("Invalid number of arguments provided")
        sys.exit(-1)

    ioc_value_arg = sys.argv[1]

    # Validate the provided argument
    if "value=" not in ioc_value_arg:
        logger.error("IntSights Error: Invalid argument provided {}".format(ioc_value_arg))
        splunk.Intersplunk.parseError("Invalid argument provided {}".format(ioc_value_arg))
        sys.exit(-1)

    ioc_value = ioc_value_arg.split("value=")[1]

    verify_cert = const.VERIFY_SSL
    encoded_cred = b64encode("{}:{}".format(account_info.get("account_id"),
                                            account_info.get("api_key")).encode()).decode()
    header = {
        "Content-type": "application/json",
        "Accept": "application/json",
        "Authorization": "Basic {}".format(encoded_cred)
    }
    api_url = "/public/v2/app/splunk/iocs/whitelist"
    url = int_utils.build_url(account_info.get("server_address"), api_url)
    try:
        output_result = _whitelist_indicator(
            header=header,
            url=url,
            proxies=proxies,
            indicator_value=ioc_value,
            verify_cert=verify_cert,
            logger=logger
        )
    except Exception as e:
        logger.error("IntSights Error: Error while whitelisting indicator. {}".format(e))
        splunk.Intersplunk.parseError("Error while whitelisting indicator. {}".format(e))
        sys.exit(-1)
    if output_result:
        splunk.Intersplunk.outputResults(output_result)


if __name__ == "__main__":
    """Driving function."""
    main_()

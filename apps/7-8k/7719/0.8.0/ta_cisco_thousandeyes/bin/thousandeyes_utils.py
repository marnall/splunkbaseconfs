import os
import json
import requests
from urllib.parse import urlparse
from requests.compat import quote_plus
from datetime import datetime, timedelta, timezone

import splunk.rest as rest
from solnlib import conf_manager
from solnlib.utils import is_true, is_false

from thousandeyes_constant import (  # noqa E402
    DATETIME_FORMAT,
    LOCAL_FOLDER,
    CERT_FOLDER,
    PROXY_CERT_FILE_NAME,
    VERIFY_SSL,
    THOUSANDEYES_TA_NAME,
    LOCAL_HOSTNAMES,
    SEVERITY_MAPPING,
)


def get_proxy_info(session_key, logger):
    """Get proxy information.

    :param session_key: Splunk session key
    :param logger: logger object

    :return: proxy details dictionary, custom proxy certificate path if applicable else the verify parameter value.
    """
    proxy_info_dict = {}
    # Retrieve proxy configurations
    _, content = rest.simpleRequest(
        f"/servicesNS/nobody/{THOUSANDEYES_TA_NAME}/{THOUSANDEYES_TA_NAME}_settings/proxy",
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json", "--cred--": "1"},
        raiseAllErrors=True,
    )
    # Parse response
    content = json.loads(content)

    for item in content["entry"]:
        proxy_info_dict = item["content"]
        break

    # Return None if proxy_enabled is false or proxy hostname or proxy port is not found
    if (
        not is_true(proxy_info_dict.get("proxy_enabled"))
        or not proxy_info_dict.get("proxy_port")  # noqa: W503
        or not proxy_info_dict.get("proxy_url")  # noqa: W503
    ):
        logger.info("Proxy is disabled")
        return None, VERIFY_SSL

    proxy_user_pass = ""
    # Quote username and password if available
    if proxy_info_dict.get("proxy_username") and proxy_info_dict.get("proxy_password"):
        proxy_username = quote_plus(proxy_info_dict["proxy_username"], safe="")
        proxy_password = quote_plus(proxy_info_dict["proxy_password"], safe="")
        proxy_user_pass = f"{proxy_username}:{proxy_password}@"

    logger.info("Proxy is enabled")

    # Prepare proxy string
    proxy = "{proxy_type}://{proxy_user_pass}{proxy_host}:{proxy_port}".format(
        proxy_type=proxy_info_dict["proxy_type"],
        proxy_user_pass=proxy_user_pass,
        proxy_host=proxy_info_dict["proxy_url"],
        proxy_port=proxy_info_dict["proxy_port"],
    )
    proxies = {
        "http": proxy,
        "https": proxy,
    }

    if (
        proxy_info_dict.get("proxy_cert", None) is None
        or proxy_info_dict.get("proxy_cert").strip() == ""
    ):
        proxy_cert_file = VERIFY_SSL
    else:
        proxy_cert = proxy_info_dict.get("proxy_cert")
        if proxy_cert.strip().startswith("-----BEGIN CERTIFICATE-----"):
            proxy_cert_file = write_proxy_cert_file(proxy_cert.strip())
        else:
            proxy_cert_file = proxy_cert

    return proxies, proxy_cert_file


def get_credentials(account_name, session_key):
    """
    Get credentials from API Query.

    :param account_name: Account name to fetch credentials for.
    :param session_key: Splunk session key

    :return: dictionary containing account details.
    """
    account_cfm = conf_manager.ConfManager(
        session_key,
        THOUSANDEYES_TA_NAME,
        realm=f"__REST_CREDENTIAL__#{THOUSANDEYES_TA_NAME}#configs/conf-{THOUSANDEYES_TA_NAME}_account",
    )
    account_conf = account_cfm.get_conf(f"{THOUSANDEYES_TA_NAME}_account", refresh=True)
    return account_conf.get(account_name)


def get_hec_tokens(session_key):
    """
    Get configured HEC tokens from API Query.

    :param session_key: Splunk session key

    :return: dictionary containing HEC Tokens.
    """
    hec_url = "/servicesNS/nobody/-/data/inputs/http"
    hec_list = {}
    _, content = rest.simpleRequest(
        hec_url,
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json", "count": "0"},
        raiseAllErrors=True,
    )
    content = json.loads(content)
    for http_stanza in content["entry"]:
        if 'name' in http_stanza and 'content' in http_stanza and 'token' in http_stanza["content"]:
            hec_list[http_stanza["name"].replace("http://", "")] = http_stanza["content"][
                "token"
            ]
    return hec_list


def get_single_hec_token(session_key, token_name):
    """
    Get HEC token details for given token from API Query.

    :param session_key: Splunk session key
    :param token_name: HEC token name

    :return: dictionary containing HEC Token data.
    """
    hec_url = f"/servicesNS/nobody/-/data/inputs/http/{token_name}"
    _, content = rest.simpleRequest(
        hec_url,
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )
    content = json.loads(content)
    return content["entry"][0]["content"]


def get_event_indexes(session_key):
    """
    Get Event indexes.

    :param session_key: Splunk session key

    :return: List of event indexes.
    """
    index_url = "data/indexes"
    indexes = []
    _, content = rest.simpleRequest(
        index_url,
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json", "datatype": "event", "count": "0"},
        raiseAllErrors=True,
    )
    content = json.loads(content)
    for index in content["entry"]:
        if is_false(index.get("content").get("isInternal")) and is_false(
            index.get("content").get("disabled")
        ):
            indexes.append(index.get("name"))
    return indexes


def get_current_date():
    """
    Get current time in format.

    :return: DateTime string.
    """
    return datetime.now(timezone.utc).strftime(DATETIME_FORMAT)


def calculate_start_date(current_date_str, delta_seconds):
    """
    Calcuate start time.

    :param current_date_str : current date time string
    :param delta_seconds : seconds to deduct for start time

    :return: DateTime string.
    """
    current_date = datetime.strptime(current_date_str, DATETIME_FORMAT)
    formatted_datetime = (current_date - timedelta(seconds=delta_seconds)).strftime(
        DATETIME_FORMAT
    )
    return formatted_datetime


def is_https(url):
    """
    Check if url starts with https.

    :param url : url to check
    """
    if not url.startswith("https://"):
        raise Exception("Paginated url does not use secure https url.")


def get_account_id(acc_group):
    """
    Get the account id from account group configured.

    :param acc_group : Account group string

    :return : Account Id string
    """
    return acc_group.split("(")[-1].split(")")[0]


def get_test_id(test):
    """
    Get the test id from test configured.

    :param test : Test string

    :return : Test Id string
    """
    return test.split("(")[-1].split(")")[0].split("|")[0].strip()


def get_test_details(test):
    """
    Parse test details from configured test string.
    
    Expected format: "TestName (testId | type)" or "TestName (testId | type | subtype)"
    
    :param test: Test string from configuration
    
    :return: Dictionary with test_id, type, and optional endpoint_test_category
    """
    if not test or test.strip() == "":
        return None
    
    # Extract content within parentheses
    try:
        paren_content = test.split("(")[-1].split(")")[0]
        parts = [part.strip() for part in paren_content.split("|")]
        
        result = {
            "test_id": parts[0] if len(parts) > 0 else None,
            "type": parts[1] if len(parts) > 1 else None,
        }
        
        # If there's a third part, it's the endpoint subtype
        if len(parts) > 2:
            result["endpoint_test_category"] = parts[2]
        
        return result if result["test_id"] else None
    except Exception:
        # Fallback to old behavior if parsing fails
        test_id = get_test_id(test)
        return {"test_id": test_id, "type": None} if test_id else None


def write_proxy_cert_file(cert_content):
    """
    Write the proxy certificate content to a file.

    :param cert_content: The content of the proxy certificate.

    :return: Path to the written certificate file.
    """
    cert_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        LOCAL_FOLDER,
        CERT_FOLDER,
    )
    os.makedirs(cert_dir, exist_ok=True)
    cert_file_path = os.path.join(cert_dir, PROXY_CERT_FILE_NAME)
    with open(cert_file_path, "w") as f:
        f.write(cert_content)
    return cert_file_path


def is_url_valid(url, logger, timeout=5, verify_ssl=True):
    """
    Check if URL is valid using a HEAD request.
    Returns False if the URL is localhost.

    :param url : URL to check
    :param timeout : timeout, default=5
    :param verify_ssl : verify SSL flag, default=True

    :return : bool
    """
    try:
        if urlparse(url).hostname in LOCAL_HOSTNAMES:
            logger.debug(f"Failed validating url: {url}, LOCAL_HOSTNAMES={LOCAL_HOSTNAMES}")
            return False

        requests.head(url, timeout=timeout, verify=verify_ssl)
        logger.debug(f"Succeed validating url: {url}")
        return True # if request does not throw any error the URL is valid
    except Exception as e:
        logger.debug(f"Failed validating url: {url}, Error: {e}")
        return False


def parse_boolean(value: str) -> bool:
    """
    Parse string to boolean.

    Args:
        value: String value to parse.

    Returns:
        bool: Parsed boolean value.
    """
    return str(value).lower() in ("true", "True", "TRUE", "1", "yes", "Yes", "YES", "on", "On", "ON")


def get_severity_mapping(session_key, logger):
    """
    Get severity mapping from ITSI configuration.

    :param session_key: Splunk session key
    :param logger: logger object

    :return: dictionary containing severity mapping from ITSI.
    """
    try:
        # Read ITSI severity configuration from SA-ITOA app
        _, content = rest.simpleRequest(
            "/servicesNS/nobody/SA-ITOA/configs/conf-itsi_notable_event_severity",
            sessionKey=session_key,
            method="GET",
            getargs={"output_mode": "json", "count": "0"},
            raiseAllErrors=True,
        )
        content = json.loads(content)

        severity_mapping = {}
        for item in content.get("entry", []):
            stanza_name = item.get("name")
            stanza_content = item.get("content", {})

            # Map severity level (stanza name) to label
            if stanza_name and stanza_content.get("label"):
                severity_level = stanza_name.lower()
                severity_label = stanza_content.get("label")
                severity_mapping[severity_level] = severity_label

                # Also map common severity names to levels
                label_lower = severity_label.lower()
                if label_lower not in severity_mapping:
                    severity_mapping[label_lower] = severity_label

        if not severity_mapping:
            logger.warning("No ITSI severity mapping found, using default mappings")
            severity_mapping = SEVERITY_MAPPING

        logger.debug(f"Loaded ITSI severity mapping: {severity_mapping}")
        return severity_mapping

    except Exception as e:
        logger.error(f"Error loading ITSI severity mapping: {e}")
        logger.info("Using default severity mapping")
        return SEVERITY_MAPPING

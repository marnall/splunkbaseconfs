import json
import traceback

import requests
import splunk.admin as admin
import splunk.rest as rest
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import ta_cycognito_constants as constants
import ta_cycognito_declare  # noqa: F401
from ta_cycognito_logger_manager import setup_logging

logger = setup_logging("ta_cycognito_utils")


class GetSessionKey(admin.MConfigHandler):
    """Session key."""

    def __init__(self):
        """Initialize Session Key."""
        self.session_key = self.getSessionKey()


def get_proxy(session_key=None):
    """
    Give information of proxy if proxy is enable.

    return: dictionary having proxy information
    """
    __URL_FORMAT = (
        "__REST_CREDENTIAL__#TA-CyCognito#configs"
        "/conf-ta_cycognito_settings:proxy``splunk_cred_sep``1:"
    )
    __URL_ENCODE = requests.compat.quote_plus(__URL_FORMAT)

    if session_key is None:
        session_key = GetSessionKey().session_key

    proxy_settings = None

    _, response_content = rest.simpleRequest(
        "/servicesNS/nobody/TA-CyCognito/configs/conf-ta_cycognito_settings/proxy",
        sessionKey=session_key,
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )

    proxy_info = json.loads(response_content)["entry"][0]["content"]
    if int(proxy_info.get("proxy_enabled", 0)) == 0:
        logger.info("CyCognito Proxy: Proxy is disabled, returning None.")
        return proxy_settings

    proxy_port = proxy_info.get("proxy_port")
    proxy_url = proxy_info.get("proxy_url")
    proxy_type = proxy_info.get("proxy_type")
    proxy_username = proxy_info.get("proxy_username", "")
    proxy_password = ""

    if proxy_username:
        try:
            _, response_content = rest.simpleRequest(
                "/servicesNS/nobody/TA-CyCognito/storage/passwords/"
                + __URL_ENCODE,
                sessionKey=session_key,
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )
            response_dict = json.loads(response_content)["entry"][0]["content"]
            cred = json.loads(response_dict.get("clear_password", "{}"))
            proxy_password = cred.get("proxy_password", None)
        except Exception:
            logger.error(
                "CyCognito Proxy: Error While fetching Proxy details.")
            logger.debug(
                "CyCognito Proxy: Error While fetching proxy details : {}"
                .format(traceback.format_exc())
            )
            return False
    proxy_settings = get_proxy_setting(
        proxy_type, proxy_username, proxy_password, proxy_url, proxy_port
    )
    logger.info("CyCognito Proxy: Successfully fetched Proxy details.")
    return proxy_settings


def get_proxy_setting(
    proxy_type,
    proxy_username,
    proxy_password,
    proxy_url,
    proxy_port
):
    """Get Proxy Settings."""
    if proxy_username and proxy_password:
        proxy_username = requests.compat.quote_plus(proxy_username)
        proxy_password = requests.compat.quote_plus(proxy_password)
        proxy_uri = "%s://%s:%s@%s:%s" % (
            proxy_type,
            proxy_username,
            proxy_password,
            proxy_url,
            proxy_port,
        )
    else:
        proxy_uri = "%s://%s:%s" % (proxy_type, proxy_url, proxy_port)
    proxy_settings = {"http": proxy_uri, "https": proxy_uri}

    return proxy_settings


def requests_retry_session(
    retries=3, backoff_factor=30, status_forcelist=constants.STATUS_FORCELIST, session=None
):
    """Create and return a session object.

    :param retries: Maximum number of retries to attempt
    :param backoff_factor: Backoff factor used to calculate time between retries.
    :param status_forcelist: A tuple containing the response status codes that should trigger a retry.
    :param session: Session object
    :return: Session Object
    """
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def validate_input_params(helper, logger, input_type=None):
    """Provide the validation logic to validate the input stanza configurations."""
    input_name = helper.get_arg('name')

    cycognito_account = helper.get_arg('cycognito_account')

    try:
        interval = int(helper.get_arg('interval'))
    except ValueError:
        logger.error("CyCognito Validation Error: Invalid Interval for input_name= {}.".format(input_name))
        return False

    if interval < 86400:
        logger.error("CyCongito Validation Error: Minimum value of interval should be 86400"
                     " for input_name= {}.".format(input_name))
        return False

    if not cycognito_account or cycognito_account is None:
        logger.warning("CyCognito Data_Collection: The input configuration is not sufficient "
                       "please provide complete valid details for \"cycognito_account\" "
                       "field for data collection of input_name=\"{}\"".format(input_name))
        logger.error("CyCognito Validation Error: Account not found "
                     "for input_name={}.".format(input_name))
        return False
    if input_type == "asset_types":
        asset_types = helper.get_arg('asset_types')
        if not asset_types:
            logger.warning("CyCognito Data_Collection: The input configuration is not sufficient "
                           "please provide complete valid details for \"asset_types\" field for data collection of "
                           "input_name=\"{}\" & cycognito_account=\"{}\"".format(input_name, cycognito_account['name']))
            return False
    return True

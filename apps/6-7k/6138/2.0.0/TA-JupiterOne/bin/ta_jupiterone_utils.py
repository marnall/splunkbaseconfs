"""This file contains utilities related to modular inputs."""
import ta_jupiterone_declare  # noqa: F401
import requests
import json
import os
import splunk.admin as admin
import splunk.rest as rest
import traceback
from solnlib import conf_manager
from ta_jupiterone_log_manager import setup_logging

logger = setup_logging("ta_jupiterone_utils")


class GetSessionKey(admin.MConfigHandler):
    """Session key."""

    def __init__(self):
        """Initialize Session Key."""
        self.session_key = self.getSessionKey()


def get_proxy(self, sessionKey=None):
    """
    Give information of proxy if proxy is enable.

    return: dictionary having proxy information
    """
    __URL_FORMAT = (
        "__REST_CREDENTIAL__#TA-JupiterOne#configs"
        "/conf-ta_jupiterone_settings:proxy``splunk_cred_sep``1:"
    )
    __URL_ENCODE = requests.compat.quote_plus(__URL_FORMAT)

    if sessionKey is None:
        session_key = GetSessionKey().session_key
    else:
        session_key = sessionKey
    proxy_settings = None

    _, response_content = rest.simpleRequest(
        "/servicesNS/nobody/TA-JupiterOne/configs/conf-ta_jupiterone_settings/proxy",
        sessionKey=session_key,
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )

    proxy_info = json.loads(response_content)["entry"][0]["content"]
    if int(proxy_info.get("proxy_enabled", 0)) == 0:
        logger.info("Proxy is disabled. returning None.")
        return proxy_settings

    proxy_port = proxy_info.get("proxy_port")
    proxy_url = proxy_info.get("proxy_url")
    proxy_type = proxy_info.get("proxy_type")
    proxy_username = proxy_info.get("proxy_username", "")
    proxy_password = ""

    if proxy_username:
        try:
            _, response_content = rest.simpleRequest(
                "/servicesNS/nobody/TA-JupiterOne/storage/passwords/"
                + __URL_ENCODE,
                sessionKey=session_key,
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )
            response_dict = json.loads(response_content)["entry"][0]["content"]
            cred = json.loads(response_dict.get("clear_password", "{}"))
            proxy_password = cred.get("proxy_password", None)
        except Exception:
            self.put_msg("Error While Fetching Proxy details.")
            logger.error("JupiterOne Error: Error While Fetching Proxy details.")
            logger.debug(
                "JupiterOne Debug: Error While Fetching Proxy details : {}"
                .format(traceback.format_exc())
            )
            return False
    proxy_settings = get_proxy_setting(
        proxy_type, proxy_username, proxy_password, proxy_url, proxy_port
    )
    logger.info("Successfully Fetched Proxy details.")
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


def post_api_expiration_msg(session_key, account_name):
    """Post the msg when API key will expire."""
    try:
        rest.simpleRequest("/services/messages", method='POST',
                           sessionKey=session_key,
                           postargs={
                               "name": "API_Key_Expired",
                               "value": "Please update your JupiterOne account :: {} "
                               "with new API key.".format(account_name)
                           },
                           raiseAllErrors=True)
        logger.info("JupiterOne Info: Added message regarding expiration of API key on UI.")
    except Exception as e:
        logger.error("JupiterOne Error: Exception occcured while posting message on UI. Error: {}".format(e))
        logger.debug("JupiterOne Debug: Exception occcured while posting message on UI. "
                     "Error trace: {}".format(traceback.format_exc()))


def get_cpu_count():
    """Return CPU count/2 or 1 if gets any exception."""
    try:
        return os.cpu_count() // 2
    except Exception:
        return 1


def get_thread_count(session_key):
    """Return thread count if configured in conf else CPU count/2."""
    try:
        cfm = conf_manager.ConfManager(session_key, 'TA-JupiterOne')
        conf = cfm.get_conf('ta_jupiterone_settings')
        stanza = conf.get('threads')
        thread_count = stanza.get('no_of_threads', None)
        thread_count = get_cpu_count() if thread_count is None else int(thread_count)
    except Exception as e:
        logger.error("JupiterOne Error: Exception occcured while getting conf stanza. Error: {}".format(e))
        thread_count = get_cpu_count()
    if thread_count < 1:
        thread_count = 1
        logger.error("JupiterOne Error: Number of threads should be greater than zero.")
    elif thread_count > 16:
        thread_count = 16
        logger.error("JupiterOne Error: Number of threads should be less than or equal to 16.")
    logger.info("JupiterOne Info: Used {} threads to get alert related entities.".format(thread_count))
    return thread_count

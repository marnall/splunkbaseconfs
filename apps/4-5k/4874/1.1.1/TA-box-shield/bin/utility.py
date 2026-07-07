"""
utility.py
Helper file containing useful methods
"""
import logging
import traceback
import json
from requests.compat import quote_plus
import splunk.rest as rest
from splunk.clilib.bundle_paths import make_splunkhome_path
from boxsdk.config import Proxy
from boxsdk.session.session import Session, AuthorizedSession
from ta_box_shield_declare import ta_name as APP_NAME
from six.moves.urllib.parse import quote

# global variables
g_helper = None
g_account_name = None


def create_session_from_proxy(proxy_args, helper, config, helper_log):
    """
    Create session object of Box SDK using the existing proxy configurations and oAuth credentials.
    This needs to be done manually as there's no direct way of passing proxy settings to box SDK.

    Args:
        config (dict): token obtained through JWT Authentication
        proxy_args (dict): dictionary containing proxy parameters
        helper (obj): This object could be helper object of splunk
                      or it could be our logger object
        helper_log (bool): True ---> its helper object of splunk
                           False --> its logger object
    Returns:
        session : Session object of Box SDK with proxy configured
    """
    try:
        proxy_obj = Proxy()
        proxy_obj.URL = "{}://{}:{}".format(proxy_args.get("proxy_type"), proxy_args.get("proxy_url"), proxy_args.get("proxy_port"))
        proxy_obj.AUTH = {
            'user': quote_plus(proxy_args.get("proxy_username")),
            'password': quote_plus(proxy_args.get("proxy_password"))
        } if proxy_args.get("proxy_username") else None

        unauth_session = Session(proxy_config=proxy_obj)
        if config:
            session = AuthorizedSession(config, **unauth_session.get_constructor_kwargs())
            return session
        else:
            return unauth_session
    except Exception:
        if helper_log:
            helper.log_error(traceback.format_exc())
        else:
            helper.error(traceback.format_exc())
        return None

def setup_logger(log_name, log_level=logging.INFO):
    """ 
    Setup logger.

    Args:
        log_name (string): name for logger
        log_level (log level object): log level to configure

    Returns:
        logger (obj): logger object
    """
    logger = logging.getLogger(log_name)

    # Prevent the log messages from being duplicated in the python.log file
    logger.propagate = False
    logger.setLevel(log_level)

    log_name = log_name + '.log'
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(
        ['var', 'log', 'splunk', log_name]), maxBytes=25000000, backupCount=5)
    
    log_format = "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s"
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)

    logger.handlers = []
    logger.addHandler(file_handler)

    return logger


def save_tokens(access_token,refresh_token):
    """This function save the access token and refresh token

    Args:
        access_token (string) : newly generated access token
        refresh token (string) : newly generated refresh token

    """
    global g_helper, g_account_name
    if g_helper and g_account_name:
        password = {}
        password['client_id'] = (g_helper.get_arg("box_account"))['client_id']
        password['client_secret'] = (g_helper.get_arg("box_account"))['client_secret']
        password['access_token'] = access_token
        password['refresh_token'] = refresh_token
        session_key = g_helper.context_meta['session_key']
        postargs = {
            "password": json.dumps(password)
        }
        g_account_name = g_account_name.replace(":", r"\:")

        rest_url = "__REST_CREDENTIAL__#{}#configs%2Fconf-ta_box_shield_account".format(APP_NAME)
        realm = quote(rest_url + ":" + g_account_name + ":", safe='')
        try:
            rest.simpleRequest(
                "/servicesNS/nobody/" + APP_NAME + "/storage/passwords/" + realm,
                session_key, postargs=postargs, method='POST', raiseAllErrors=True)
            g_helper.log_info("Access token and Refresh token are generated and saved successfully.")
            return True
        except Exception as e:
            g_helper.log_error("Error occurred while updating the new tokens. Kindly reconfigure the account from UI. Error: {}".format(e))


def set_globals(helper, account_name):
    """This function is only set the global variables so at the time of saving credentials we can use these variables

    Args:
        helper(obj): This object could be helper object of splunk
        account_name(string): Name of the configured Box account in Splunk

    """
    global g_account_name, g_helper
    g_helper = helper
    g_account_name = account_name + "``splunk_cred_sep``1"

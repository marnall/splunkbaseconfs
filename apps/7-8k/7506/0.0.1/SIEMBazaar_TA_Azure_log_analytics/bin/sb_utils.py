import os.path
import traceback
import sys
import requests
import logging


from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import binding

APP_NAME = __file__.split(os.path.sep)[-3]
CONF_NAME_PREFIX = APP_NAME.lower()


# Checkpointing related functions
def _init_ckpt(self, cp_id=None):
    try:
        ckpt = checkpointer.KVStoreCheckpointer(
            APP_NAME + "_" + cp_id,
            self.session_key,
            APP_NAME
        )
        return ckpt
    except Exception:
        self.logger.error(
            f"Error while initializing checkpoint. {traceback.format_exc()}"
        )
        return None
def get_check_point(self, key, cp_id=None):
    """Get checkpoint.
    :param key: `string`
    :return: Checkpoint state if exists else None.
    """
    try:
        ckpt = _init_ckpt(self, cp_id)
        if ckpt is not None:
            return ckpt.get(key)
    except binding.HTTPError:
        self.logger.error(
            f"Error while getting checkpoint_name={key}. {traceback.format_exc()}"
        )
 

def save_check_point(self, key, state, cp_id=None):
    """Update checkpoint.
    :param key: Checkpoint key. `string`
    :param state: Checkpoint state.
    """
    try:
        ckpt = _init_ckpt(self, cp_id)
        if ckpt is not None:
            ckpt.update(key, state)
    except binding.HTTPError:
        self.logger.error(
            f"Error while saving checkpoint_name={key}. {traceback.format_exc()}"
        )

def batch_save_check_point(self, states, cp_id=None):
    """Batch update checkpoint.
    :param states: a `dict` states with checkpoint key as key and checkpoint state as value.
    """
    try:
        ckpt = _init_ckpt(self, cp_id)
        if ckpt is not None:
            ckpt.batch_update(states)
    except binding.HTTPError:
        self.logger.error(
            f"Error while batch saving checkpoint_name={states}. {traceback.format_exc()}"
        )

def delete_check_point(self, key, cp_id=None):
    """Delete checkpoint.
    :param key: Checkpoint key. `string`
    """
    try:
        ckpt = _init_ckpt(self, cp_id)
        if ckpt is not None:
            ckpt.delete(key)
    except binding.HTTPError:
        self.logger.error(
            f"Error while deleting checkpoint_name={key}. {traceback.format_exc()}"
        )

def _normalize_from_full_name(full_input_name: str):
    # Full input name is in form of "<input_type>://<input_name>"
    return full_input_name.replace("://","_")

def set_logger(session_key, full_input_name: str) -> logging.Logger:
    """
    This function sets up a logger with configured log level.
    :param filename: Name of the log file
    :return logger: logger object
    """
    input_name = _normalize_from_full_name(full_input_name)
    logger = log.Logs().get_logger(f"{APP_NAME.lower()}_{input_name}")
    log_level = conf_manager.get_log_level(
        logger=logger,
        session_key=session_key,
        app_name=APP_NAME,
        conf_name= f"{CONF_NAME_PREFIX}_settings",
        default_log_level="INFO",
    )
    logger.setLevel(log_level)
    logger.info("log level is set to : {}".format(log_level))
    return logger


def get_conf_details(session_key, logger, conf_filename):
    """
    This function reads the configuration file
    """
    try:
        settings_cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
                APP_NAME, conf_filename
            ),
        )
        ta_conf_file = settings_cfm.get_conf(conf_filename).get_all()

        #logger.debug("ta_conf_file:{}".format(ta_conf_file))
        return ta_conf_file

    except Exception:
        logger.error(
            "Failed to read the configuration file. {}".format(traceback.format_exc())
        )
        sys.exit(1)


def get_account_details(session_key, logger, conf_type ,token_label):
    """
    This function reads api token details
    :param session_key: Session key for the particular modular input
    :return: A dictionary having token details
    """
    try:
        api_token_details = get_conf_details(
            session_key, logger, f"{CONF_NAME_PREFIX}_{conf_type}"
        )
        token_data = api_token_details.get(token_label)
        if not conf_type == "license":
            logger.debug(
            "Reading data for label {} from conf={}".format(token_label,f"{CONF_NAME_PREFIX}_{conf_type}.conf")
            )
        if token_data:
            return token_data
    except Exception as e:
        logger.error(
            "Failed to fetch data for label {} from conf={}. error={}".format(token_label,f"{CONF_NAME_PREFIX}_{conf_type}.conf",e)
            )
        sys.exit(1)

def get_l_details(session_key, logger, token_label):
    """
    This function reads api token details
    :param session_key: Session key for the particular modular input
    :return: A dictionary having token details
    """
    try:
        l_details = get_conf_details(
            session_key, logger, f"{CONF_NAME_PREFIX}_license"
        )
        token_data = l_details.get(token_label)
        token_details = {
            "key": token_data.get("licensekey")
        }
        return token_details
    except Exception:
        logger.error(
            "Failed to fetch the license key details"
        )
        sys.exit("Error while fetching license key details. Terminating modular input.")



def get_proxy_settings(session_key, logger):
    """
    This function reads proxy settings if any, otherwise returns None
    :param session_key: Session key for the particular modular input
    :return: A dictionary having proxy settings
    """

    try:
        ta_settings_conf = get_conf_details(
            session_key, logger, f"{CONF_NAME_PREFIX}_settings"
        )
        proxy_settings = None
        proxy_stanza = {}
        for key, value in ta_settings_conf["proxy"].items():
            proxy_stanza[key] = value

        if proxy_stanza.get("proxy_enabled") in  [None, "0"]:
            logger.info("Proxy is disabled. Returning None")
            return proxy_settings
        proxy_port = proxy_stanza.get("proxy_port")
        proxy_url = proxy_stanza.get("proxy_url")
        proxy_type = proxy_stanza.get("proxy_type")
        proxy_username = proxy_stanza.get("proxy_username", "")
        proxy_password = proxy_stanza.get("proxy_password", "")

        if proxy_type == "socks5":
            proxy_type += "h"
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
        logger.info("Successfully fetched configured proxy details.")
        return proxy_settings

    except Exception:
        logger.error(
            "Failed to fetch proxy details from configuration. {}".format(
                traceback.format_exc()
            )
        )
        sys.exit(1)


def clone(*, dictionary, exclude_keys=None):
    if not exclude_keys:
        exclude_keys = []
    return {k: v for k, v in dictionary.items() if k not in exclude_keys}

from splunklib import modularinput as smi
from solnlib import log
from solnlib.conf_manager import ConfManager

APP_NAME = "TA-Zscaler_CIM"
CONF_NAME = "ta_zscaler_cim"
ACCOUNT_CONF_FILE = "ta_zscaler_cim_account"
PROXY_CONF_FILE = "ta_zscaler_cim_settings"

def get_account_config(session_key: str, account_stanza: str, logger):
    """
    Return API access token for a specific account_name.

    :param helper: base modinput class
    :param session_key: session key for particular modular input.
    :param conf_file: conf file name without '.conf' (e.g., 'ta_zscaler_cim_account')
    :param account_stanza: account stanza name configured in the addon.
    """
    
    try:
        logger.debug(f"Getting conf file '{ACCOUNT_CONF_FILE}' stanza '{account_stanza}'.")
        cfm = ConfManager(session_key, APP_NAME, realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{ACCOUNT_CONF_FILE}")
        conf = cfm.get_conf(ACCOUNT_CONF_FILE)
        account_stanza_details = conf.get(account_stanza)
        logger.debug(f"Successfully received conf file '{ACCOUNT_CONF_FILE}'->'{account_stanza}' information.")
        return account_stanza_details

    except Exception as ex:
        logger.error(f"Error occurred while reading {ACCOUNT_CONF_FILE}.conf. {ex}")
        return


def get_proxy_config(session_key: str, logger):
    """
    Return proxy settings for the ZScaler TA
    
    :param helper: base modinput class
    :param session_key: session key for particular modular input
    :param conf_file: conf file name without '.conf'
    """

    try:
        logger.debug(f"Getting proxy settings from conf file '{PROXY_CONF_FILE}.")
        cfm = ConfManager(session_key, APP_NAME, realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{PROXY_CONF_FILE}")
        conf = cfm.get_conf(PROXY_CONF_FILE)
        logger.debug(f"Successfully received conf file '{PROXY_CONF_FILE}'")
    except Exception as ex:
        logger.debug(f"Unable to retrieve details from {PROXY_CONF_FILE}'")
    
    try:
        proxy_stanza_details = conf.get("proxy")
        logger.debug(f"Successfully received conf file '{PROXY_CONF_FILE}'->'proxy' information.")
        return proxy_stanza_details
    except Exception as ex: 
        logger.debug(f"No proxy stanza exists in '{PROXY_CONF_FILE}")
        return None


def get_log_level(session_key: str, logger):
    """
    This function returns the log level for the addon from configuration file.
    :param session_key: session key for particular modular input.
    :return : log level configured in addon.
    """
    try:
        
        settings_cfm = ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}_settings".format(APP_NAME, CONF_NAME))

        logging_details = settings_cfm.get_conf(CONF_NAME+"_settings").get("logging")

        log_level = logging_details.get('loglevel') if (logging_details.get('loglevel')) else 'INFO'
        return log_level

    except Exception:
        logger.error("Failed to fetch the log details from the configuration taking INFO as default level.")
        return 'INFO'


def create_logger(input_name: str, session_key: str):
    """
    Creates and returns a logger object for the application
    
    :param input_name: Name of the current input
    :param session_key: session key for current Splunk session
    """

    logger = log.Logs().get_logger(f"{APP_NAME}_{input_name}")
    log_level = get_log_level(session_key, logger)
    logger.setLevel(log_level)
    return logger


def get_input_name_and_items(inputs: smi.InputDefinition):
    """Get input name and input items object from input definition
    
    :param inputs: Input Definition
    :param logger: logger object
    :return: tupple with input_name and input_items
    """
    
    # Get the first input name from the inputs definition
    input_name = list(inputs.inputs.keys())[0] 

    # Retrieve the input items (parameters) associated with the input_name
    input_items = inputs.inputs[input_name]
    
    # If the input_name contains '//' (as in a modular input), split to extract the actual input name
    if '//' in input_name:
        _, input_name = input_name.split('//', 1)  # Splitting only once

    return input_name, input_items


def zscaler_api_login(z, username: str, password: str, apikey: str, cloud: str, logger):
    """Authenticates against the ZScaler API on the selected cloud endpoint
    
    :param z: zscaler API
    :param username: username string
    :param password: password string
    :param apikey: API Key string
    :param cloud: Zscaler cloud API url to use
    :param logger: logger object
    :return: True when successful, False when failed. 
    """
    try:
        # Connect to ZScaler API
        logger.debug("Starting Login to ZScaler API")
        z.get_settings_from_vars(username, password, apikey)
        z.set_cloud(cloud)
        z.authenticate_zia_api()
        return True
    except Exception as ex:
        logger.error(f"Error logging into ZScaler API.   ({ex})")
        return False

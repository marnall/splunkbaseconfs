import os
import sys
from solnlib import conf_manager
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from log_manager import setup_logging
from cloudknox_consts import settings_conf_file
from ta_cloudknox_declare import ta_name

logger = setup_logging("ta_cloudknox_utility")


def check_has_upgraded_value(cfm, stanza):
    """
    Check the value of has_upgraded parameter in ta_cloudknox_settings.conf file.

    :param cfm: Object of the ConfManager to perform operations on the conf files.
    :param stanza: Name of the stanza to be created in the conf file.
    :return has_upgraded param value from the ta_cloudknox_settings.conf file.
    """
    has_upgraded = "0"
    try:
        cfm_settings_conf_file = cfm.get_conf(settings_conf_file)
        settings_conf_dict_obj = cfm_settings_conf_file.get_all()
        settings_conf_items = list(settings_conf_dict_obj.items())
        if settings_conf_items:
            for stanza_name, stanza_info in settings_conf_items:
                if stanza_name == stanza and "has_upgraded" in stanza_info:
                    has_upgraded = stanza_info['has_upgraded']
        return has_upgraded
    except Exception as e:
        logger.error("Error inside ta_cloudknox_settings.conf read: {}".format(e))
        return has_upgraded


def get_session_key():
    """
    Get the session key.

    :return: This function returns the session_key value.
    """
    try:
        session_key = sys.stdin.readline().strip()
    except Exception as e:
        logger.error("inside session key exception: {}".format(e))

    return session_key


def file_exist(file_name, ta_name):
    """
    Check if the file exists or not.

    :param file_name: Name of the file which is to be checked if it exists or not.
    :param ta_name: Name of the app.
    :return boolean value after checking if the file exists or not.
    """
    file_path = make_splunkhome_path(["etc", "apps", ta_name, "local", file_name])
    file_name = "".join([file_path, ".conf"])
    if os.path.exists(file_name):
        return True
    else:
        return False


def update_settings_conf(session_key, stanza_name):
    """
    Upgrade stanza in ta_cloudknox_settings.conf file.

    :param session_key: The session key value.
    :param stanza_name: The name of the stanza for which the value needs to be updated.
    """
    update_dict = {}
    try:
        cfm_settings = conf_manager.ConfManager(
            session_key, ta_name, realm='__REST_CREDENTIAL__#TA-CloudKnox#configs/conf-ta_cloudknox_settings')
        cfm_settings_conf = cfm_settings.get_conf(settings_conf_file)
        update_dict['has_upgraded'] = 1
        cfm_settings_conf.update(stanza_name, update_dict)
        logger.info("Updated ta_cloudknox_settings.conf file, setting has_upgraded key to 1.")
    except Exception as e:
        raise Exception("Exception occured while updating ta_cloudknox_settings.conf stanza {}".format(e))

import json
import splunk.clilib.cli_common as scc
import splunk.admin as admin

import tab_splunktalib.common.util as utils
from tab_splunktalib.conf_manager import ta_conf_manager as ta_conf
from tab_splunktalib.conf_manager import conf_manager as conf
import TA_AlgoSec_Incident_Handling_consts as c


'''
Usage Examples:
setup_util = Setup_Util(uri, session_key)
setup_util.get_log_level()
setup_util.get_customized_setting("my_customized_field_name")
'''

class Setup_Util(object):

    def __init__(self, uri, session_key, logger=None):
        self.__uri = uri
        self.__session_key = session_key
        self.__logger = logger
        self.encrypt_fields_customized = (c.password,)

    def log_error(self, msg):
        if self.__logger:
            self.__logger.error(msg)

    def log_info(self, msg):
        if self.__logger:
            self.__logger.info(msg)

    def log_debug(self, msg):
        if self.__logger:
            self.__logger.debug(msg)

    def _parse_conf(self):
        conf_mgr = conf.ConfManager(self.__uri, self.__session_key)
        conf_mgr.set_appname("TA-AlgoSec_Incident_Handling")
        conf_mgr.reload_conf(c.myta_conf)
        conf_mgr.reload_conf(c.myta_customized_conf)
        # read global and proxy settings
        all_settings = conf_mgr.all_stanzas_as_dicts(c.myta_conf)
        if not all_settings:
            all_settings = {}
        self._setNoneValues(all_settings.get(c.global_settings, {}))
        # read customized settings
        ta_conf_mgr = ta_conf.TAConfManager(
            c.myta_customized_conf, self.__uri, self.__session_key, "TA-AlgoSec_Incident_Handling")
        ta_conf_mgr.set_encrypt_keys(self.encrypt_fields_customized)
        customized_settings = ta_conf_mgr.all(return_acl=False)
        for stanza_name, stanza_content in customized_settings.iteritems():
            self._setNoneValues(stanza_content)
        all_settings.update({c.myta_customized_settings: customized_settings})
        return all_settings

    @staticmethod
    def _setNoneValues(stanza):
        for k, v in stanza.iteritems():
            if v is None:
                stanza[k] = ""

    def get_log_level(self):
        log_level = "INFO"
        global_settings = self._parse_conf().get('global_settings', None)
        if not global_settings:
            self.log_error("Log level is not set")
        else:
            log_level = global_settings.get('log_level', None)
            if not log_level:
                self.log_error("Log level is not set")
                log_level = "INFO"
        return log_level



    def get_customized_setting(self, key):
        customized_settings = self._parse_conf().get('customized_settings', None)
        if not customized_settings:
            self.__logger.error("Customized setting is not set")
            return None
        if not key in customized_settings:
            self.__logger.error("Customized key can not be found")
            return None
        customized_setting = customized_settings.get(key, {})
        _type = customized_setting.get("type", None)
        if not _type:
            self.__logger.error("Type of this customized setting is not set")
            return None
        if _type == "bool":
            return utils.is_true(customized_setting.get("bool", '0'))
        elif _type == "text":
            return customized_setting.get("content", "")
        elif _type == "password":
            return customized_setting.get("password", "")
        else:
            raise Exception("Type of this customized setting is corrupted")
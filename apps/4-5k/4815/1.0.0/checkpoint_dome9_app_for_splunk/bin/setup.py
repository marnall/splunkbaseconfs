import splunk.admin as admin
import time
import json
import xml.sax.saxutils as xss
import re

import dome9_utils


import logging
from logger_manager import setup_logging
LOGGER = setup_logging("checkpoint_dome9_setup", logging.INFO)


class SetupRestcall(admin.MConfigHandler):

    @staticmethod
    def remove_whitespaces(param):
        if param:
            param = param.strip()
        else:
            param = ''
        return param

    '''
    Set up supported arguments
    '''
    def setup(self):
        """
        Sets the input arguments
        :return: None
        """
        # Set up the valid parameters
        for arg in ['show_settings', 'api_key', 'secret_key', 'error_msg', 'is_proxy_enabled', 'proxy_scheme', 'proxy_is_auth_required', 'proxy_ip',
                    'proxy_port', 'proxy_username', 'proxy_password']:
            self.supportedArgs.addOptArg(arg)


    def handleList(self, conf_info):
        """
        handles GET method request
        """
        LOGGER.debug("handleList")
        conf_info[dome9_utils.STANZA_NAME].append("show_settings", True)

        # Endpoint can only be requested through current app's namespace as it requires to access conf file of the App.
        LOGGER.debug("App: " + str(self.context != admin.CONTEXT_NONE and self.appName  or "-") + " - User: " + str(self.context == admin.CONTEXT_APP_AND_USER and self.userName or "-"))
        conf_dict = self.readConf(dome9_utils.CONF_FILE_NAME)
        if None != conf_dict:
            for stanza, settings in conf_dict.items():
                if stanza == dome9_utils.STANZA_NAME:
                    for key, val in settings.items():
                        if key in ['show_settings', 'api_key', 'secret_key', 'error_msg', 'is_proxy_enabled', 'proxy_scheme', 'proxy_is_auth_required', 'proxy_ip',
                                'proxy_port', 'proxy_username', 'proxy_password'] and val in [None, '']:
                            val = ''
                        conf_info[stanza].append(key, val)
        conf_info[dome9_utils.STANZA_NAME]["is_proxy_enabled"] = dome9_utils.convert_to_bool(conf_info[dome9_utils.STANZA_NAME]['is_proxy_enabled'])
        conf_info[dome9_utils.STANZA_NAME]["proxy_is_auth_required"] = dome9_utils.convert_to_bool(conf_info[dome9_utils.STANZA_NAME]['proxy_is_auth_required'])

    def handleEdit(self, conf_info):
        """
        handles POST method request
        """
        LOGGER.debug("handleEdit")
        args = self.callerArgs.data
        configure_api_key = dome9_utils.convert_to_bool(str(args["show_settings"][0]))
        if not configure_api_key:
            # user don't want to configure the API Key and Secret Key
            data = {
                "setup_error": " ",
                "setup_success": "App configured without API Key and Secret Key.",
                "msg_time": str(time.time())
            }
            self.writeConf(dome9_utils.CONF_FILE_NAME, dome9_utils.STANZA_NAME, data)
            return

        api_key = str(args["api_key"][0])
        secret_key = str(args["secret_key"][0])
        is_proxy_enabled = dome9_utils.convert_to_bool(args['is_proxy_enabled'][0])

        proxy_scheme = xss.escape(
            self.remove_whitespaces(args['proxy_scheme'][0]))
        proxy_is_auth_required = dome9_utils.convert_to_bool(args['proxy_is_auth_required'][0])
        proxy_ip = xss.escape(self.remove_whitespaces(args['proxy_ip'][0]))
        proxy_port = xss.escape(self.remove_whitespaces(args['proxy_port'][0]))
        proxy_username = xss.escape(
            self.remove_whitespaces(args['proxy_username'][0]))
        proxy_password = self.remove_whitespaces(args['proxy_password'][0])
        isValid = True

        if is_proxy_enabled:
            if (not proxy_scheme or proxy_scheme == ''):
                LOGGER.error("Proxy scheme is required")
                setup_error = "Proxy scheme is required"
                isValid = False

            if (not proxy_ip or proxy_ip.strip == ''):
                LOGGER.error("Proxy IP/hostname is required")
                setup_error = "Proxy IP/hostname is required"
                isValid = False

            if (not proxy_port or not re.match("^([0-9]{1,4}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$",
                                               proxy_port)):
                LOGGER.error("Proxy Port is invalid")
                setup_error = "Invalid Proxy port specified"
                isValid = False

            if proxy_is_auth_required:
                if (not proxy_username or proxy_username == '') or (not proxy_password or proxy_password == ''):
                    LOGGER.error(
                        "Proxy username and password are required when proxy auth is enabled")
                    setup_error = "Proxy username and password are required when proxy auth is enabled"
                    isValid = False
            else:
                proxy_username = proxy_password = ''
        else:
            proxy_scheme = proxy_ip = proxy_port = proxy_username = proxy_password = ''

        if not isValid:
            data = {
                "setup_error": setup_error,
                "setup_success": " ",
                "msg_time": str(time.time())
            }
            self.writeConf(dome9_utils.CONF_FILE_NAME, dome9_utils.STANZA_NAME, data)
            return

        proxies = dome9_utils.get_proxy_struct(is_proxy_enabled, proxy_ip, proxy_port, proxy_scheme, proxy_is_auth_required, proxy_username, proxy_password)
        connection_params = dome9_utils.get_connection_params(LOGGER, self.readConf(dome9_utils.CONF_FILE_NAME))
        api_validator = dome9_utils.ValidateAPIKey(LOGGER, api_key, secret_key, connection_params, proxies)
        (_, _, error) = api_validator.validate()

        if error:
            LOGGER.info("Incorrect information is provided.")
            data = {
                "setup_error": error,
                "setup_success": " ",
                "msg_time": str(time.time())
            }
            self.writeConf(dome9_utils.CONF_FILE_NAME, dome9_utils.STANZA_NAME, data)
        else:
            LOGGER.info("Correct information is provided, storing it in conf file.")
            credential_manager = dome9_utils.CredentialManager(self.getSessionKey(), LOGGER)
            credential_manager.store_password(api_key, secret_key)
            if proxy_is_auth_required:
                credential_manager.store_password(proxy_username, proxy_password)

            data = {
                "setup_error": " ",
                "setup_success": "API Key and Secret Key stored successfully.",
                "msg_time": str(time.time()),
                "api_key": api_key,
                "is_proxy_enabled": is_proxy_enabled,
                "proxy_scheme": proxy_scheme,
                "proxy_ip": proxy_ip,
                "proxy_port": proxy_port,
                "proxy_is_auth_required": proxy_is_auth_required,
                "proxy_username": proxy_username,
            }
            self.writeConf(dome9_utils.CONF_FILE_NAME, dome9_utils.STANZA_NAME, data)


if __name__ == "__main__":
    admin.init(SetupRestcall, admin.CONTEXT_APP_AND_USER)

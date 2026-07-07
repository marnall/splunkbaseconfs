
import ta_cisco_ni_declare
import requests
import os
import json

import splunk.admin as admin
import splunk.rest as rest
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from solnlib import conf_manager
import cisco_ni_constants as const

util.remove_http_proxy_env_vars()

from logger_manager import setup_logging
_Logger = setup_logging("ta_cisco_ni_account_validation")


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server
    :param ConfigMigrationHandler: inhereting ConfigMigrationHandler
    """
    __URL_FORMAT = (
        "__REST_CREDENTIAL__#TA_cisco-NI#configs"
        "/conf-ta_cisco_ni_settings:proxy``splunk_cred_sep``1:"
    )
    __URL_ENCODE = requests.compat.quote_plus(__URL_FORMAT)
    my_app = __file__.split(os.sep)[-3]

    def get_proxy(self):
        """
        Information of proxy whenever proxy is enabled.

        :return: dictionary having proxy information
        """
        session_key = GetSessionKey().session_key
        proxy_settings = None
        _, response_content = rest.simpleRequest(
            "/servicesNS/nobody/{}/configs/conf-ta_cisco_ni_settings/proxy".format(self.my_app),
            sessionKey=session_key,
            getargs={"output_mode": "json"},
            raiseAllErrors=True,
        )

        proxy_info = json.loads(response_content)["entry"][0]["content"]
        if int(proxy_info.get("proxy_enabled", 0)) == 0:
            return proxy_settings

        proxy_port = proxy_info.get("proxy_port")
        proxy_url = proxy_info.get("proxy_url")
        proxy_type = proxy_info.get("proxy_type")
        proxy_username = proxy_info.get("proxy_username", "")
        proxy_password = ""

        if proxy_username:
            try:
                _, response_content = rest.simpleRequest(
                    "/servicesNS/nobody/{}/storage/passwords/".format(self.my_app)
                    + self.__URL_ENCODE,
                    sessionKey=session_key,
                    getargs={"output_mode": "json"},
                    raiseAllErrors=True,
                )
                response_dict = json.loads(response_content)["entry"][0]["content"]
                cred = json.loads(response_dict.get("clear_password", "{}"))
                proxy_password = cred.get("proxy_password", None)
            except Exception as e:
                _Logger.exception("Error While fetching proxy \n Error: {}".format(str(e)))
                raise admin.ArgValidationException("Error While Fetching Proxy")

        proxy_settings = self.get_proxy_setting(
            proxy_type, proxy_username, proxy_password, proxy_url, proxy_port
        )
        return proxy_settings

    def get_proxy_setting(self, proxy_type, proxy_username, proxy_password, proxy_url, proxy_port):
        """Fetch the Proxy Setting."""
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

    def account_validation(self):
        """ validate the account configuration cardential """
        try:
            _Logger.debug("Account Validation started")
            proxy_settings = self.get_proxy()
        except Exception as exception:
            _Logger.exception(
                "Error while fetching proxy information.\n Error: {}".format(exception)
            )
            raise admin.ArgValidationException("Error while fetching proxy information.")

        ni_hosts = self.payload.get("ni_hostname").split(",")

        for index in range(len(ni_hosts)):
            ni_hosts[index] = ni_hosts[index].strip()

        user_name = self.payload.get("username")
        password = self.payload.get("password")
        account_type = self.payload.get("account_type")
        login_domain = self.payload.get("login_domain", "")

        if (account_type == "remote_user_authentication") and (login_domain == ""):
            raise admin.ArgValidationException("Field Login Domain is required")

        if login_domain == "":
            login_domain = "DefaultAuth"
        error_msg_prefix = "Connection Unsuccessful."
        verify_ssl = const.VERIFY_SSL
        time_out = const.TIMEOUT
        data = {"userName": user_name, "userPasswd": password, "domain": login_domain}
        is_valid_host = False
        for host_name in ni_hosts:
            try:
                response = requests.post(
                    "https://{}/login".format(host_name),
                    data=json.dumps(data),
                    verify=verify_ssl,
                    proxies=proxy_settings,
                    timeout=time_out,
                )
                msg = None
                if response.status_code not in (200, 201):
                    msg = "{} Please verify Hostname/IP Address and Username, \
                        Password are correct.".format(
                        error_msg_prefix
                    )
                    _Logger.error(
                        "Could not validate account provided IP Address {}.".format(host_name)
                    )
                else:
                    try:
                        json.loads(response.content)
                    except Exception as e:
                        msg = "{} Please verify Login Domain is correct.".format(error_msg_prefix)
                        _Logger.error(
                            "Please verify Login Domain is correct for IP Address {}. \
                                Error: {}".format(
                                host_name, str(e)
                            )
                        )
                    else:
                        is_valid_host = True
                        _Logger.info(f"Successfully validated provided IP Address {host_name}")
            except requests.exceptions.SSLError:
                msg = "SSL certificate verification failed. \
                    Please add a valid SSL Certificate or Change VERIFY_SSL flag to False"
                _Logger.error(
                    "SSL certificate verification failed. "
                    "Please add a valid SSL Certificate or Change VERIFY_SSL flag to False"
                )
            except requests.exceptions.ProxyError:
                msg = "{} Please verify Proxy Settings are correct.".format(error_msg_prefix)
                _Logger.error(
                    "{} Please verify Proxy Settings are correct.".format(error_msg_prefix)
                )
            except Exception as e:
                msg = "{} Please verify Hostname/IP Address and Username, \
                    Password are correct.".format(
                    error_msg_prefix
                )
                _Logger.error(
                    "Could not validate account provided IP Address {}. Error: {}".format(
                        host_name, str(e)
                    )
                )

            if (not is_valid_host) and host_name == ni_hosts[-1] and msg:
                raise admin.ArgValidationException(msg)

        _Logger.info("Account Validation of {}: success".format(self.callerArgs.id))


    def read_conf_file(self, session_key, conf_file, stanza=None):
        """
        Get conf file content with conf_manager.

        :param session_key: Splunk session key
        :param conf_file: conf file name
        :param stanza: If stanza name is present then return only that stanza,
                        otherwise return all stanza
        """
        conf_file = conf_manager.ConfManager(
            session_key,
            self.my_app,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(self.my_app, conf_file),
        ).get_conf(conf_file)

        if stanza:
            return conf_file.get(stanza)
        return conf_file.get_all()

    def handleCreate(self, confInfo):
        """Handle creation of account in config file."""
        self.account_validation()
        super(CustomConfigMigrationHandler, self).handleCreate(confInfo)

    def handleEdit(self, confInfo):
        """Handles the edit operation. """
        self.account_validation()
        super(CustomConfigMigrationHandler, self).handleEdit(confInfo)

    def handleRemove(self, confInfo):
        """Handle the delete operation."""
        session_key = GetSessionKey().session_key
        inputs_file = self.read_conf_file(session_key, "inputs")
        created_inputs = list(inputs_file.keys())
        input_list = []
        input_type_list = ["cisco_ni"]
        for _input in created_inputs:
            cisco_ni_input = _input.split('://')
            if cisco_ni_input[0] in input_type_list:
                configured_account = inputs_file.get(_input).get('global_account')
                if configured_account == self.callerArgs.id:
                    input_list.append(cisco_ni_input[1])
        if len(input_list) > 0:
            msg = "\"{}\" cannot be deleted because it is in use by the following inputs: {}".format(
                self.callerArgs.id, input_list
                )
            _Logger.error(msg)
            raise admin.ArgValidationException(msg)
        else:
            _Logger.info("Account Deletion of {}: success".format(self.callerArgs.id))
            super(ConfigMigrationHandler, self).handleRemove(confInfo)


fields = [
    field.RestField(
        'ni_hostname',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        )
    ),
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        )
    ),
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    ),
    field.RestField(
        'login_domain',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        )
    ),
    field.RestField(
        'account_type',
        required=True,
        encrypted=False,
        default="local_user_authentication",
        validator=None
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_cisco_ni_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )

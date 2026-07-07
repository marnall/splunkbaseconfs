import websocket
import ssl
import os
import io
import json
from six.moves import configparser

from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.entity as entity
import splunk.admin as admin
from splunktaucclib.rest_handler.endpoint.validator import Validator
import logger_manager as log

_LOGGER = log.setup_logging("ta_pps_ondemand_account_validation")


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class ValidateAccount(Validator):
    def __init__(self, *args, **kwargs):
        """
        Do account validation.

        :param validator: user-defined validating function
        """
        super(ValidateAccount, self).__init__()
        self.my_app = __file__.split(os.sep)[-3]

    def validate(self, value, data):
        """
        Check if the given value is valid.

        :param value: value to validate.
        :param data: whole payload in request.
        :return True or False
        """
        # Get proxy settings information
        try:
            proxy_settings = self.get_proxy_settings()
        except Exception as e:
            msg = "Error while fetching proxy information. Cause -> " + str(e)
            self.put_msg(msg)
            _LOGGER.error("Error while fetching proxy information : {}".format(str(e)))
            return False

        # Set parameters
        cluster_id = data["username"]
        api_key = data["password"]
        http_proxy_host = proxy_settings.get("proxy_url")
        http_proxy_port = proxy_settings.get("proxy_port")
        if http_proxy_port:
            http_proxy_port = int(http_proxy_port)
        http_proxy_username = proxy_settings.get("proxy_username")
        http_proxy_password = proxy_settings.get("proxy_password")
        http_proxy_auth = None
        if http_proxy_username or http_proxy_password:
            http_proxy_auth = (http_proxy_username, http_proxy_password)

        url = "wss://logstream.proofpoint.com:443/v1/stream?type=message&cid=" + str(cluster_id)
        header = {"Authorization": "Bearer %s" % (api_key,)}
        sslopt = {"cert_reqs": ssl.CERT_NONE}

        # Create Connection
        try:
            ws = websocket.create_connection(
                url,
                header=header,
                sslopt=sslopt,
                http_proxy_host=http_proxy_host,
                http_proxy_port=http_proxy_port,
                http_proxy_auth=http_proxy_auth,
            )
        except Exception as e:
            msg = (
                "Unable to create connection. Please enter valid"
                + "account information or check proxy settings. Cause -> "
                + str(e)
            )
            self.put_msg(msg)
            _LOGGER.error(msg)
            return False
        ws.close()
        return True

    def get_proxy_settings(self):
        """
        Get information of proxy.

        :return: dictionary having proxy information
        """
        entities = entity.getEntities(
            ["admin", "passwords"],
            namespace=self.my_app,
            owner="nobody",
            sessionKey=GetSessionKey().session_key,
            search=self.my_app,
        )
        config = configparser.ConfigParser()
        proxy_settings_conf = os.path.join(
            make_splunkhome_path(
                ["etc", "apps", self.my_app, "local", "ta_pps_ondemand_settings.conf"]
            )
        )
        proxy_settings = {}
        if os.path.isfile(proxy_settings_conf):
            with io.open(proxy_settings_conf, "r", encoding="utf_8_sig") as inputconffp:
                config.readfp(inputconffp)
            if config.has_section("proxy"):
                proxy_enabled = int(config.get("proxy", "proxy_enabled"))
                if proxy_enabled:
                    proxy_settings["proxy_port"] = config.get("proxy", "proxy_port")
                    proxy_settings["proxy_url"] = config.get("proxy", "proxy_url")
                    proxy_settings["proxy_type"] = config.get("proxy", "proxy_type")
                    try:
                        proxy_settings["proxy_username"] = config.get("proxy", "proxy_username")
                        proxy_settings["proxy_password"] = ""
                        for _, value in entities.items():
                            if value["username"].partition("`")[0] == "proxy" and not value[
                                "clear_password"
                            ].startswith("`"):
                                cred = json.loads(value.get("clear_password", "{}"))
                                proxy_settings["proxy_password"] = cred.get("proxy_password", "")
                                break
                    except Exception:
                        pass
        return proxy_settings

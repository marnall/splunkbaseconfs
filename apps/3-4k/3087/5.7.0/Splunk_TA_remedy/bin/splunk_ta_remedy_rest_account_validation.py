#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import traceback

import requests
import splunk.admin as admin
from logger_manager import get_logger
from remedy_helper import get_sslconfig
from solnlib import conf_manager, utils
from remedy_helper import execute_with_retries
from remedy_consts import APP_NAME
from splunktaucclib.rest_handler.endpoint.validator import Validator

_LOGGER = get_logger("rest_account_validation")

JWT_LOGIN_ENDPOINT = "{}/api/jwt/login"

UNREACHABLE_URL_MSG = "Unable to reach BMC Remedy server at '{}'. Check configurations and network settings"

RESPONSE_CODE_WISE_MSG = {
    401: "Failed to verify BMC Remedy username and password",
    407: "Failed to verify proxy username and password",
}


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class RestAccountValidation(Validator):
    def __init__(self, *args, **kwargs):
        super(RestAccountValidation, self).__init__(*args, **kwargs)
        self.session_key = None

    def getProxySettings(self):
        # Obtain proxy settings, if proxy has been configured, by reading splunk_ta_remedy_settings.conf
        session_key_obj = GetSessionKey()
        session_key = session_key_obj.session_key

        settings_cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_remedy_settings".format(
                APP_NAME
            ),
        )

        splunk_ta_remedy_settings_conf = settings_cfm.get_conf(
            "splunk_ta_remedy_settings"
        ).get_all()

        proxies = {
            key: value for key, value in splunk_ta_remedy_settings_conf["proxy"].items()
        }

        if utils.is_true(proxies.get("proxy_enabled", "")):
            _LOGGER.info("Proxy is enabled")
            proxy_type = proxies.get("proxy_type")
            proxy_url = proxies.get("proxy_url")
            proxy_port = proxies.get("proxy_port")
            proxy_username = proxies.get("proxy_username", "")
            proxy_password = proxies.get("proxy_password", "")

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

            return {"http": proxy_uri, "https": proxy_uri}

        return None

    def validate(self, value, data):
        _LOGGER.info(
            "Verifying the credentials for the BMC Remedy Server {}.".format(
                data["server_url"]
            )
        )

        session_key_obj = GetSessionKey()
        self.session_key = session_key_obj.session_key

        proxy_config = self.getProxySettings()

        url = JWT_LOGIN_ENDPOINT.format(data["server_url"])
        body = {"username": data["username"], "password": data.get("password", "")}

        verify_ssl = get_sslconfig(
            self.session_key,
            utils.is_true(data.get("disable_ssl_certificate_validation", False)),
            _LOGGER,
        )
        try:
            resp = execute_with_retries(
                "POST",
                url,
                logger=_LOGGER,
                data=body,
                proxies=proxy_config,
                verify=verify_ssl,
            )

        except requests.exceptions.SSLError:
            msg = "SSLError occured. Please look into the {} file for more details.".format(
                "splunk_ta_remedy_rest_account_validation.log"
            )
            self.put_msg(msg, True)
            _LOGGER.error(
                "SSLError occurred. If you are using self signed certificate "
                "and your certificate is at /etc/ssl/ca-bundle.crt, "
                "please refer the troubleshooting section in add-on documentation. Traceback = {}".format(
                    traceback.format_exc()
                )
            )
            return False
        except Exception:
            msg = UNREACHABLE_URL_MSG.format(url)
            _LOGGER.error(
                "{0}. The reason for failure is={1}".format(msg, traceback.format_exc())
            )
            self.put_msg(msg, True)
            return False

        if resp.status_code in (401, 407):
            msg = "{0} code={1} reason={2}".format(
                RESPONSE_CODE_WISE_MSG.get(resp.status_code),
                resp.status_code,
                resp.reason,
            )
            _LOGGER.error(msg)
            self.put_msg(msg, True)
            return False

        if resp.status_code not in (200, 201):
            msg = UNREACHABLE_URL_MSG.format(url)
            _LOGGER.error(
                "{0}. The reason for failure is={1}".format(msg, traceback.format_exc())
            )
            self.put_msg(msg, True)
            return False

        # Check the Content-Type of the response
        content_type = resp.headers.get("Content-Type", "")
        if "text/plain" not in content_type:
            _LOGGER.error(
                "Unexpected Content-Type received: '{}'. Expected 'text/plain' for a valid JWT token response.".format(
                    content_type
                )
            )
            msg = "Authentication Failed, status code is {} but the server response is not of type 'text/plain'. Please check the server configuration".format(
                resp.status_code
            )
            self.put_msg(msg, True)
            return False

        _LOGGER.info("Successfully generated jwt token")
        data["jwt_token"] = resp.text
        return True

import ta_sophos_central_addon_for_splunk_declare  # noqa: F401

import os
import re
import sophos_consts
import sophos_common_utils as utils
from sophos_collect import SophosCollect

from log_manager import setup_logging
from solnlib.utils import is_true
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunk_aoblib.rest_helper import TARestHelper
from splunk_aoblib.rest_migration import ConfigMigrationHandler

_LOGGER = setup_logging("sophos_validators")


class SessionKeyProvider(ConfigMigrationHandler):
    """Provides Splunk session key to custom validator."""

    def __init__(self):
        """Save session key in class instance."""
        self.session_key = self.getSessionKey()


class SophosAuth(Validator):
    """Validator for Sophos account credentials."""

    def validate(self, value, data):
        """Credential validation method for Sophos account configuration."""
        sophos_auth_url = sophos_consts.AUTH_BASE_URL
        sophos_client_id = data.get("client_id").strip()
        sophos_client_secret = data.get("client_secret").strip()
        sophos_verify_cert = is_true(data.get("verify_cert"))
        app_name = __file__.split(os.sep)[-3]
        splunk_session_key = SessionKeyProvider().session_key
        guid_regex = r"""^[{]?[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}[}]?$"""
        invalid_creds_msg = "Invalid credentials!"

        sophos_config_param = utils.get_sophos_config_params(splunk_session_key)
        old_client_id = sophos_config_param.get('client_id')
        # _LOGGER.info("old_client_id: {}".format(old_client_id))

        if not all([sophos_client_id, sophos_client_secret]):
            return False

        if not re.match(r"{}".format(guid_regex), sophos_client_id):
            self.put_msg(invalid_creds_msg)
            _LOGGER.error(invalid_creds_msg)
            return False

        if len(sophos_client_secret) > 100:
            self.put_msg(invalid_creds_msg)
            _LOGGER.error(invalid_creds_msg)
            return False

        proxy_uri = utils.get_proxy_uri(app_name, splunk_session_key)

        try:
            response = SophosCollect.request_sophos_access_token(
                sophos_auth_url, sophos_client_id, sophos_client_secret, sophos_verify_cert, proxy_uri,
            )
        except Exception as e:
            message = "Invalid Sophos/Proxy details. Please enter the correct configuration details."
            self.put_msg(message)
            _LOGGER.error("{} Error: {}".format(message, str(e)))
            return False
        else:
            if response.ok:
                pass
            elif response.status_code == 400:
                message = "Bad Request."
                self.put_msg(message)
                _LOGGER.error(message)
                return False
            elif response.status_code == 401:
                self.put_msg(invalid_creds_msg)
                _LOGGER.error(invalid_creds_msg)
                return False
            elif response.status_code == 403:
                message = "Forbidden. Not having permission to perform this action."
                self.put_msg(message)
                _LOGGER.error(message)
                return False
            elif response.status_code > 500:
                message = "Internal Server error."
                self.put_msg(message)
                _LOGGER.error(message)
                return False
            else:
                message = "Unexpected error. Status code: {}, reason: {}".format(
                    response.status_code, response.reason
                )
                self.put_msg(message)
                _LOGGER.error(message)
                return False

        try:
            response = response.json()
            _LOGGER.info("Sophos account validation successful. Going to fetch whoami response.")

            # Add whoami response into ta_sophos_central_addon_for_splunk_settings.conf
            who_am_i_request_url = "{scheme}{url}{endpoint}".format(
                scheme="https://", url=sophos_consts.WHO_AM_I_BASE_URL, endpoint=sophos_consts.WHO_AM_I_ENDPOINT
            )
            who_am_i_headers = {
                "Authorization": "Bearer {}".format((str(response["access_token"])))
            }
            who_am_i_response = TARestHelper().send_http_request(
                who_am_i_request_url,
                "get",
                headers=who_am_i_headers,
                verify=is_true("true"),
                proxy_uri=utils.get_proxy_uri(app_name, splunk_session_key),
                payload={},
                timeout=(sophos_consts.CONNECT_TIMEOUT, sophos_consts.READ_TIMEOUT),
            )

            if who_am_i_response.ok:
                whoami_response = who_am_i_response.json()
                parsed_whoami = {
                    "account_id": whoami_response.get("id", None),
                    "account_id_type": whoami_response.get("idType", None),
                    "apihost_global": whoami_response.get("apiHosts", {}).get("global", None),
                    "apihost_dataregion": whoami_response.get("apiHosts", {}).get("dataRegion", None)
                }
                utils.save_whoami_response(
                    splunk_session_key,
                    "additional_parameters",
                    "ta_sophos_central_addon_for_splunk_settings",
                    parsed_whoami
                )
                utils.save_sophos_credentials(app_name, splunk_session_key, response["access_token"])

                if sophos_client_id != old_client_id :
                    _LOGGER.info("Sophos client id updated, will remove the inputs if exists.")
                    all_inputs = utils.read_conf_file(splunk_session_key, "inputs")
                    for input in all_inputs.keys():
                        if input.startswith("sophos_alert_input://") or input.startswith("sophos_endpoint_input://") or input.startswith("sophos_event_input://") or input.startswith("sophos_tenant_input://"):
                            utils.delete_stanza(splunk_session_key, "inputs", input)
                            _LOGGER.info("Deleted input: {}".format(input))

        except Exception as e:
            message = "Unexpected error occurred: {}".format(e)
            self.put_msg(message)
            _LOGGER.error(message)
            return False

        self.put_msg("Credentials saved successfully!")
        _LOGGER.info("Stored access token and whoami response successfully.")
        return True

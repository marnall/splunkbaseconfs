import sys
import os
import json
import traceback
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..')))
import import_declare_test  # noqa: E402 F401
from silent_push_helpers.logger_manager import setup_logging  # noqa: E402

from requests.compat import quote_plus  # noqa: E402
from solnlib.credentials import CredentialManager  # noqa: E402
from solnlib.utils import is_true  # noqa: E402
from splunk.persistconn.application import PersistentServerConnectionApplication  # noqa: E402
import splunk.rest as rest  # noqa: E402
from splunk import ResourceNotFound  # noqa: E402

APP_NAME = import_declare_test.ta_name


logger = setup_logging("ta_silent_push_get_credentials")


class SilentPushGetCredentials(PersistentServerConnectionApplication):
    """Custom Encryption Handler."""

    def __init__(self, _command_line, _command_arg):
        """Initialize object with given parameters."""
        self.auth_type = None
        self.key = None
        self.proxy_key = None
        self.session_key = None
        self.admin_session_key = None
        self.payload = {}
        self.status = None
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a synchronous from splunkd.
    def handle(self, in_string):
        """
        For using any custom command, Called for a simple synchronous request.

        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                it will automatically be JSON encoded before being returned.
        """
        try:
            req_data = json.loads(in_string)
            self.admin_session_key = req_data.get('system_authtoken', None)
            form_data = dict(req_data.get("form"))
            self.account_name = form_data.get("name", None)
            proxy = self.get_proxy_info(self.admin_session_key)
            proxy_checked = True

            if self.account_name is None:
                logger.debug("Getting all account configurations from account.conf .")
                _, account_response_content = rest.simpleRequest(
                    "/servicesNS/nobody/{}/configs/conf-silentpushappforsplunk_account".format(APP_NAME),
                    sessionKey=self.admin_session_key,
                    getargs={"output_mode": "json", "--cred--": 1},
                    raiseAllErrors=False,
                )
                account_config_json = json.loads(account_response_content)

                account_configs = {}
                for account_config_json in account_config_json.get("entry", []):
                    account_name = account_config_json.get('name')
                    account_config = account_config_json.get("content")
                    account_manager = CredentialManager(
                        self.admin_session_key,
                        app=APP_NAME,
                        realm="__REST_CREDENTIAL__#{}#configs/conf-silentpushappforsplunk_account".format(APP_NAME),
                    )
                    account_password = json.loads(account_manager.get_password(account_name))
                    for k, v in account_password.items():
                        account_config.update({k: v})
                    account_config["proxy"] = proxy
                    account_config["proxy_checked"] = proxy_checked
                    account_config["account_name"] = account_name
                    account_configs[account_name] = account_config

                self.status = 200
                return {
                    'payload': account_configs,
                    'status': self.status
                }
            else:
                logger.debug("Getting account configurations from account.conf .")
                # Get account settings from conf
                _, account_response_content = rest.simpleRequest(
                    "/servicesNS/nobody/{}/configs/conf-silentpushappforsplunk_account/{}".format(
                        APP_NAME, self.account_name
                    ),
                    sessionKey=self.admin_session_key,
                    getargs={"output_mode": "json", "--cred--": 1},
                    raiseAllErrors=False,
                )
                account_config_json = json.loads(account_response_content)
                account_config = account_config_json.get("entry")[0].get("content")
                logger.debug("Account configurations read successfully from account.conf .")

                # Get clear account password from passwords.conf
                account_manager = CredentialManager(
                    self.admin_session_key,
                    app=APP_NAME,
                    realm="__REST_CREDENTIAL__#{}#configs/conf-silentpushappforsplunk_account".format(APP_NAME),
                )
                account_password = json.loads(account_manager.get_password(self.account_name))
                for k, v in account_password.items():
                    account_config.update({k: v})

                self.status = 200
                account_config["proxy"] = proxy
                account_config["proxy_checked"] = proxy_checked

                return {
                    'payload': account_config,
                    'status': self.status
                }

        except ResourceNotFound:
            error_msg = "SilentPush Error: Account '{}' not found.".format(self.account_name)
            logger.error(error_msg)
            payload = {
                'error': error_msg,
                'proxy': proxy,
                'proxy_checked': proxy_checked
            }
            return {
                'payload': payload,
                'status': 500
            }

        except Exception:
            error_msg = "SilentPush Error: Error occured while retrieving account and proxy configurations - {}".format(
                traceback.format_exc())
            logger.error(error_msg)
            return {
                'payload': error_msg,
                'status': 500
            }

    def get_proxy_info(self, session_key):
        """Get proxy info."""
        # Get proxy settings from conf
        try:
            proxy_info_dict = {}
            _, content = rest.simpleRequest(
                "/servicesNS/nobody/{}/SilentPushAppForSplunk_settings/proxy".format(APP_NAME),
                sessionKey=session_key,
                getargs={"output_mode": "json", "--cred--": "1"},
            )
            # Parse response
            content = json.loads(content)
        except Exception:
            logger.exception(
                "message=get_proxy_info_error |"
                " Could not get proxy settings from the rest endpoint")
            raise

        for item in content["entry"]:
            proxy_info_dict = item["content"]
            break

        # Return None if proxy_enabled is false or proxy hostname or proxy port is not found
        if (
            not is_true(proxy_info_dict.get("proxy_enabled"))
            or not proxy_info_dict.get("proxy_port")
            or not proxy_info_dict.get("proxy_url")
        ):
            return None

        # Quote username and password if available
        user_pass = ""
        if proxy_info_dict.get("proxy_username") and proxy_info_dict.get("proxy_password"):
            username = quote_plus(proxy_info_dict["proxy_username"], safe="")
            password = quote_plus(proxy_info_dict["proxy_password"], safe="")
            user_pass = "{user}:{password}@".format(user=username, password=password)

        # Prepare proxy string
        proxy = "{proxy_type}://{user_pass}{host}:{port}".format(
            proxy_type=proxy_info_dict["proxy_type"],
            user_pass=user_pass,
            host=proxy_info_dict["proxy_url"],
            port=proxy_info_dict["proxy_port"],
        )
        proxies = {
            "http": proxy,
            "https": proxy,
        }
        return proxies

    def handleStream(self, handle, in_string):
        """For future use."""
        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self):
        """Virtual method which can be optionally overridden to receive a callback after the request completes."""
        pass

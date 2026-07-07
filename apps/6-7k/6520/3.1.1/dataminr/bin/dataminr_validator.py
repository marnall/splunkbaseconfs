import traceback
import import_declare_test  # noqa: F401
import requests
import json
import splunk.admin as admin
from splunktaucclib.rest_handler.endpoint.validator import Validator
from solnlib.utils import is_true
from solnlib.server_info import ServerInfo
from solnlib.hec_config import HECConfig
from dataminr_constants import (
    DATAMINR_BASE_URL,
    DATAMINR_AUTH_ENDPOINT,
    GRANT_TYPE,
    VERIFY_SSL,
    ALL_ALERT_TYPES,
    REQUEST_TIMEOUT,
    SPLUNK_CLOUD_HEC_PORT,
    DATAMINR_BASE_URL_V4,
    DATAMINR_AUTH_ENDPOINT_V4,
    INTEGRATION_VERSION,
    APPLICATION_TYPE
)
from dataminr_utils import (
    get_proxy_info,
    get_hec_tokens,
    get_watchlist_ids
)
from dataminr_client import DataminrClient
from log_helper import setup_logging
import splunk.rest as rest


class SessionKeyProvider(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class AccountValidator(Validator):
    def __init__(self, *args, **kwargs):
        super(AccountValidator, self).__init__(*args, **kwargs)
        self.logger = setup_logging("account_validator")

    def validate(self, value, data):
        """Validate the account details."""
        session_key = SessionKeyProvider().session_key
        try:
            self.logger.info("Validating the provided account credentials.")
            proxy = get_proxy_info(session_key, self.logger)
            if data.get("api_version", "") == "v4":
                auth_url = f"{DATAMINR_BASE_URL_V4}{DATAMINR_AUTH_ENDPOINT_V4}"
            else:
                auth_url = f"{DATAMINR_BASE_URL}{DATAMINR_AUTH_ENDPOINT}"
            data_body = {"grant_type": GRANT_TYPE,
                         "client_id": data.get("client_id", None),
                         "client_secret": data.get("client_secret", None)}
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            if data.get("api_version", "") == "v4":
                headers.update({
                    "application_version": INTEGRATION_VERSION,
                    "integration_version": INTEGRATION_VERSION,
                    "application": APPLICATION_TYPE
                })
            response = requests.post(
                auth_url, headers=headers, data=data_body, verify=VERIFY_SSL,
                proxies=proxy, timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                response = response.json()
                access_token = response.get("dmaToken", None)
                refresh_token = response.get("refreshToken", None)
                data["access_token"] = access_token
                data["refresh_token"] = refresh_token
                self.logger.info("Successfully validated the provided account credentials.")
                return True
            elif response.status_code == 401:
                self.logger.error("Incorrect credentials provided. Please verify the provided credentials.")
                self.put_msg("Incorrect credentials. Please verify the provided credentials.")
                return False
            elif response.status_code == 429:
                self.logger.error("API rate limit exceeded. Please try after sometime.")
                self.put_msg("API rate limit exceeded. Please try after sometime.")
                return False
            else:
                self.logger.error(
                    "Error occured while validating credentials."
                    f" Response status code : {response.status_code}. Message: {response.text}"
                )
                self.put_msg(
                    "Error occured while validating credentials."
                    f" Response status code : {response.status_code}."
                    " Please check the logs."
                )
                return False
        except requests.exceptions.ProxyError as e:
            self.logger.error(
                f"Proxy error occurred : {e}. {traceback.format_exc()}"
            )
            self.put_msg("Please verify the provided proxy credentials.")
            return False
        except requests.exceptions.SSLError as e:
            self.logger.error(
                f"SSL error occurred : {e}. {traceback.format_exc()})"
            )
            self.put_msg(
                "Please verify the SSL certificate(s) for the provided configuration."
            )
            return False
        except Exception as e:
            self.logger.error(
                f"Error occured while validating the account : {e}."
                f" {traceback.format_exc()}"
            )
            self.put_msg("Error occured while validating the account. Please check the logs.")
            return False


class HECTokenValidator(Validator):
    def __init__(self, *args, **kwargs):
        super(HECTokenValidator, self).__init__(*args, **kwargs)
        self.logger = setup_logging("HEC_token_validator")

    def validate(self, value, data):
        """Validate HEC token Configured."""
        session_key = SessionKeyProvider().session_key
        try:
            self.logger.info("Validating the provided HEC Token.")
            if (data["hec_token"] in get_hec_tokens(session_key)):
                self.logger.info("Successfully validated the provided HEC Token.")
                server = ServerInfo(session_key=session_key)
                if server.is_cloud_instance():
                    hec_stack_name = server.server_name.split(".", 1)[-1]
                    hec_host = f"http-inputs-{hec_stack_name}"
                    hec_port = SPLUNK_CLOUD_HEC_PORT
                    hec_scheme = "https"
                else:
                    hec_host = server.server_name
                    hec_settings = HECConfig(session_key=session_key).get_settings()
                    hec_port = hec_settings.get("port")
                    hec_ssl = hec_settings.get("enableSSL")
                    hec_scheme = "https" if is_true(hec_ssl) else "http"
                HEC_webhook_url = f"{hec_scheme}://{hec_host}:{hec_port}/services/collector/raw"
                payload = {
                    "watchlists": [],
                    "deliveryType": "splunk_siem",
                    "deliveryInfo": {
                        "webhook": "",
                        "token": ""
                    }
                }
                dataminr_account = data.get("dataminr_account", None)
                dataminr_client = DataminrClient(session_key, dataminr_account)
                self.logger.info("Fetching watchlist Ids of configured watchlist names.")
                all_watchlists = dataminr_client.get_all_watchlists()
                input_watchlist_ids = get_watchlist_ids(all_watchlists, data["lists_names"])
                self.logger.info("Successfully fetched configured watchlist Ids.")
                if "All" in data.get("alert_type"):
                    alert_type = [a_type.upper() for a_type in ALL_ALERT_TYPES]
                else:
                    alert_type = data.get("alert_type").upper().split(",")
                for list_id in input_watchlist_ids:
                    payload["watchlists"].append(
                        {
                            "id": list_id,
                            "brands": alert_type
                        }
                    )
                payload["deliveryInfo"]["webhook"] = HEC_webhook_url
                payload["deliveryInfo"]["token"] = f"Splunk {data['hec_token']}"
                if (data.get("dataminr_webhook_id", None) is None or data["dataminr_webhook_id"] == ""):
                    self.logger.info("Adding webhook on Dataminr.")
                    dataminr_webhook_id = dataminr_client.add_update_dataminr_webhook(payload).get("deliverySettingId")
                    self.logger.info("Successfully added webhook on Dataminr.")
                else:
                    self.logger.info("Updating webhook on Dataminr.")
                    dataminr_webhook_id = dataminr_client.add_update_dataminr_webhook(
                        payload, data["dataminr_webhook_id"]
                    ).get("deliverySettingId")
                    self.logger.info("Successfully updated webhook on Dataminr.")
                data["dataminr_webhook_id"] = dataminr_webhook_id
                return True
            else:
                self.logger.error("Configured HEC token is not valid. Please verify.")
                self.put_msg("Configured HEC token not valid. Please verify.")
            return False
        except Exception as e:
            self.logger.error(
                f"Error occured while configuring the input. {e}."
                f" {traceback.format_exc()}"
            )
            self.put_msg("Error occured while configuring the input. Please check the logs.")
            return False


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class V4AccValidator(Validator):
    def __init__(self, *args, **kwargs):
        super(V4AccValidator, self).__init__()

    def validate(self, value, data):
        """Validate Configured Creds."""
        try:
            acc_name = data.get("dataminr_account")
            s_key = GetSessionKey().session_key
            _, content = rest.simpleRequest(
                "/servicesNS/nobody/dataminr/configs/conf-dataminr_account/{}".format(acc_name),
                sessionKey=s_key,
                getargs={"output_mode": "json"},
                raiseAllErrors=True)
            account_data = json.loads(content)["entry"]
            content = account_data[0]["content"]
            apiv = content.get("api_version", "")
            if apiv != "v4":
                self.put_msg("Please select the correct account (v4).")
                return False
            return True
        except Exception as e:
            self.put_msg("Some Error occured while creating the input. Error: {}".format(e))
            return False


class V3AccValidator(Validator):
    def __init__(self, *args, **kwargs):
        super(V3AccValidator, self).__init__()

    def validate(self, value, data):
        """Validate Configured Creds."""
        try:
            acc_name = data.get("dataminr_account")
            s_key = GetSessionKey().session_key
            _, content = rest.simpleRequest(
                "/servicesNS/nobody/dataminr/configs/conf-dataminr_account/{}".format(acc_name),
                sessionKey=s_key,
                getargs={"output_mode": "json"},
                raiseAllErrors=True)
            account_data = json.loads(content)["entry"]
            content = account_data[0]["content"]
            apiv = content.get("api_version", "")
            if apiv == "v4":
                self.put_msg("Please select the correct account (v3).")
                return False
            return True
        except Exception as e:
            self.put_msg("Some Error occured while creating the input. Error: {}".format(e))
            return False

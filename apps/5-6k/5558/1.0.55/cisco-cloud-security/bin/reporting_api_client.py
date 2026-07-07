import sys
from os.path import dirname, abspath

sys.path.append(dirname(abspath(__file__)))
import json
import time
import requests
from logger import Logger
from enums import Constants, OAuthSettingsStatus
from exceptions import ReportingAPIClientException
from service.app_kvstore_service import KVStoreService
from token_service import TokenService
from utils import decode_jwt_payload, get_org_id_from_token
from collections_schema import OAuthSettingsFields
from global_org_client import GlobalOrgClient


def refresh_token(decorated):
    """This is the decorator function used to refresh the access token"""

    def wrapper(*args, **kwargs):
        decoded_payload = decode_jwt_payload(args[0].token)
        exp = decoded_payload["exp"]
        if exp < time.time() or (exp - time.time()) <= Constants.TOKEN_EXPIRY.value:
            Logger().info("Token is expired or about to expire. Regenerating token...")
            args[0].token = args[0].generate_token()
        return decorated(*args, **kwargs)

    return wrapper


class ReportingAPIClient:
    """This class is a shared library to perform oauth operations and handle reporting API calls"""

    # Note: Added set_token parameter to avoid setting access_token during validation of oauth credentials.
    def __init__(
        self,
        session_token,
        api_key=None,
        api_secret=None,
        base_url=None,
        storage_region=None,
        set_token: bool = True,
        org_id: str = None,
    ):
        """This is constructor of singleton class ReportingAPIClient."""

        self.session_token = session_token
        self._org_id = org_id
        self._global_org_client = GlobalOrgClient(session_token)
        if api_key is None or api_secret is None or base_url is None:
            api_key, api_secret, base_url, storage_region = (
                self.__get_oauth_credentials()
            )
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.storage_region = storage_region
        self.token_url = base_url + Constants.OAUTH_TOKEN_ENDPOINT.value
        if set_token:
            self.token = self.__get_access_token()
        else:
            self.token = self.generate_token(set_token=False)

    @property
    def org_id(self) -> str:
        """This method is used to get org id from reporting API."""
        return self._org_id or get_org_id_from_token(self.token)

    def __get_oauth_credentials(self):
        """This private method is used to fetch oauth credentials."""
        Logger().info("__get_oauth_credentials called.")
        query = {
            OAuthSettingsFields.STATUS.value: OAuthSettingsStatus.ACTIVE.value,
        }
        if self._org_id:
            query.update({OAuthSettingsFields.ORG_ID.value: self._org_id})
        else:
            query.update(
                {OAuthSettingsFields.ORG_ID.value: self._global_org_client.global_org}
            )
        oauth_settings = KVStoreService(self.session_token)
        oauth_settings = json.loads(
            oauth_settings.query_items(
                "oauth_settings", self.session_token, query_conditions=query
            )
        )
        if len(oauth_settings) == 0:
            Logger().error(
                "Umbrella API settings are not configured or not in active state."
            )
            raise ReportingAPIClientException(
                error_code=400,
                error_msg="Umbrella API settings are not "
                "configured or not in active state.",
            )
        oauth_settings = oauth_settings[-1]
        self._org_id = oauth_settings["orgId"] if not self._org_id else self._org_id
        # Moved credentials fetching logic to prevent uncecessary token service calls
        # Only need to fetch the credentials when access token is not present or expired
        return (
            oauth_settings["apiKey"],
            oauth_settings["apiSecret"],
            oauth_settings["baseURL"],
            oauth_settings["storageRegion"],
        )

    def __set_credentials(self):
        """This private method is used to set oauth credentials."""
        if not self._org_id:
            Logger().error("Org ID not found. Unable to set oauth credentials.")
            raise ReportingAPIClientException(
                error_code=400,
                error_msg="Org ID is required to set oauth credentials.",
            )
        api_key = TokenService.get_token(
            self.session_token, "api_key", org_id=self._org_id
        )
        api_secret = TokenService.get_token(
            self.session_token, "api_secret", org_id=self._org_id
        )
        if api_key["payload"] is None or api_secret["payload"] is None:
            Logger().error("api_key or api_secret is not configured.")
            raise ReportingAPIClientException(
                error_code=400, error_msg="Umbrella API settings are not configured."
            )
        self.api_key = api_key["payload"]["clear_token"]
        self.api_secret = api_secret["payload"]["clear_token"]

    def __get_access_token(self):
        """This private method is used to fetch access token."""

        access_token = TokenService.get_token(
            self.session_token, "access_token", org_id=self._org_id
        )
        if access_token["payload"] is None:
            access_token = self.generate_token()
        else:
            access_token = access_token["payload"]["clear_token"]

        return access_token

    def generate_token(self, set_token: bool = True):
        """This method is used to generate the access token."""
        # Note: Added set_token parameter to avoid setting access_token during validation of oauth credentials.
        try:
            if not self.api_key or not self.api_secret:
                self.__set_credentials()
            payload = {}
            headers = {
                "User-Agent": "CiscoCloudSecurityAppForSplunk/python-requests/3x"
            }
            response = requests.post(
                self.token_url,
                data=payload,
                auth=(self.api_key, self.api_secret),
                headers=headers,
            )
            response.raise_for_status()
            if set_token:
                TokenService.set_token(
                    self.session_token,
                    response.json()["access_token"],
                    "access_token",
                    org_id=self._org_id,
                )
            return response.json()["access_token"]
        except Exception as e:
            Logger().error("Exception raised from generate_token")
            if e.response is not None:
                error_msg = e.response.text
                if "message" in e.response.text:
                    error_msg = json.loads(e.response.text)["message"]
                error_code = e.response.status_code
                if e.response.status_code == 401:
                    error_code = 500
                    error_msg = "Unauthorized: Please configure the valid API Key and Key Secret in Application settings"
                raise ReportingAPIClientException(
                    error_code=error_code, error_msg=error_msg
                )
            else:
                raise ReportingAPIClientException(error_code=500, error_msg=str(e))

    @refresh_token
    def send_request(self, path, method, payload=None, params=None, headers=None):
        """This method is used to send request to reporting API and return the response received."""

        try:
            if not headers:
                headers = {}
            headers["Authorization"] = "Bearer " + self.token
            response = None
            request_url = self.base_url + "/reports/v2" + path
            if self.storage_region in ("us", "eu") and ("apiUsage") not in path:
                request_url = (
                    self.base_url + f"/reports.{self.storage_region}/v2" + path
                )
            if (
                "appDiscoveryStats" in path or "/policies/v2" in path
            ) and "apiUsage" not in path:
                request_url = self.base_url + path
            if "investigate" in path and "apiUsage" not in path:
                request_url = self.base_url + path
            # Alerting API uses direct path without /reports prefix
            if "/admin/v2/alerting" in path:
                request_url = self.base_url + path

            if method == "get":
                response = getattr(requests, method)(
                    request_url, headers=headers, params=params, allow_redirects=False
                )
            else:
                response = getattr(requests, method)(
                    request_url,
                    data=payload,
                    params=params,
                    headers=headers,
                    allow_redirects=False,
                )
            
            if response.status_code == 302:
                if method == "get":
                    response = getattr(requests, method)(
                        response.headers["Location"], params=params, headers=headers
                    )
                else:
                    response = getattr(requests, method)(
                        response.headers["Location"],
                        data=payload,
                        params=params,
                        headers=headers,
                    )
            response.raise_for_status()
            return response
        except Exception as e:
            Logger().error("Exception raised from send_request")
            if e.response is not None:
                error_msg = e.response.text
                if "message" in e.response.text:
                    error_msg = json.loads(e.response.text)["message"]
                error_code = e.response.status_code
                if e.response.status_code == 500:
                    error_msg = e.response.reason
                if e.response.status_code == 401:
                    error_code = 500
                if e.response.status_code == 429:
                    error_code = 429
                if (
                    e.response.status_code == 403
                    and "access forbidden" in error_msg.lower()
                ):
                    error_msg = "Secure Access/Umbrella API access forbidden."

                raise ReportingAPIClientException(
                    error_code=error_code, error_msg=error_msg
                )
            else:
                raise ReportingAPIClientException(error_code=500, error_msg=str(e))

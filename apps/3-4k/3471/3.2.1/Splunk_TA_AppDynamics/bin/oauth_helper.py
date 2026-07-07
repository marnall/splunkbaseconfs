import json
import requests
import base64
from datetime import datetime, timedelta

from ucc_utils import Util
from appdynamics_utils import normalize_controller_url, get_account_name_from_controller_url


class Auth(object):
    def __init__(self, account_name):
        self._account_name = account_name
        self._token = None

    def get_header(self):
        raise NotImplementedError("Please Implement this method")


class OAuth(Auth):
    def __init__(self, helper=None, account_name=None, timeout=15.0, proxies=None, controller_url=None,
                 client_name=None, client_secret=None, verify_ssl=True):
        super().__init__(account_name)
        self._helper = helper
        if helper is not None:
            self._proxies = Util.get_proxy(helper.context_meta["session_key"])
            self._timeout = Util.get_timeout(helper.context_meta["session_key"])
            self._verify_ssl = Util.get_verify_ssl(helper.context_meta["session_key"])
        else:
            self._proxies = proxies
            self._timeout = timeout
            self._verify_ssl = verify_ssl
        self._token_exp = datetime.now()
        if account_name:
            self._controller_url = self._account_name["appd_controller_url"]
            self._client_name = self._account_name["appd_client_name"]
            self._client_secret = self._account_name["appd_client_secret"]
        else:
            self._controller_url = controller_url
            self._client_name = client_name
            self._client_secret = client_secret

        self._authenticate()

    def _log_debug(self, msg):
        if self._helper is not None:
            self._helper.log_debug(msg)

    def _log_info(self, msg):
        if self._helper is not None:
            self._helper.log_info(msg)

    def _log_error(self, msg):
        if self._helper is not None:
            self._helper.log_error(msg)

    def _handle_response(self, response):
        # Check the response status, if the status is not sucessful, raise requests.HTTPError
        if response.status_code != requests.codes.ok:
            # An error occurred. Printing details out and leaving.
            response.raise_for_status()

        try:
            r_json = json.loads(response.text)
        except Exception as err:
            self._log_debug(response.text)
            self._log_error("Could not parse response: {}, terminating execution.".format(err))
            raise

        return r_json

    def _authenticate(self):
        self._log_debug("Authenticating")
        opt_client_id = self._client_name
        opt_client_secret = self._client_secret
        opt_controller_url = normalize_controller_url(self._controller_url)
        opt_account_name = get_account_name_from_controller_url(opt_controller_url)

        self._log_debug("Requesting Access Token for account {0} and client ID {1}".format(
            opt_account_name, opt_client_id))

        response = requests.post(f"{opt_controller_url}/controller/api/oauth/access_token",
                                 headers={
                                     'Content-Type': 'application/x-www-form-urlencoded'
                                 },
                                 data={
                                     "grant_type": "client_credentials",
                                     "client_id": f"{opt_client_id}@{opt_account_name}",
                                     "client_secret": opt_client_secret
                                 },
                                 auth=(opt_client_id, opt_client_secret),
                                 verify=self._verify_ssl,
                                 proxies=self._proxies,
                                 timeout=self._timeout)
        self._log_debug(
            f"Request URL '{response.request.url}' Payload '{response.request.body}' Response: {response.status_code} - {response.text}")
        if response.status_code >= 300:
            self._log_error(
                f"Error Request URL '{response.request.url}' Payload '{response.request.body}' Response: {response.status_code} - {response.text}")
        r_json = self._handle_response(response)

        # Get token and calculate its expiration time
        self._token_exp = datetime.now() + timedelta(seconds=r_json['expires_in'])
        self._token = r_json['access_token']
        self._log_debug(f"Token expires at {self._token_exp}")

    def _refresh_token(self):
        self._log_info("Refreshing token")
        self._authenticate()
        return self._token

    def get_token(self):
        self._log_debug("Checking token validity")
        if self._token is None or datetime.now() >= self._token_exp:
            return self._refresh_token()

        return self._token

    def get_header(self):
        return {'Authorization': 'Bearer {}'.format(self.get_token())}

    def get_client_id(self):
        return self._client_name
        pass


class BasicAuth(Auth):
    def __init__(self, account_name):
        super().__init__(account_name)

        connect_string = "{}@{}:{}".format(
            self._account_name['appd_client_name'],
            self._account_name['appd_account_name'],
            self._account_name['appd_client_secret'])

        self._token = base64.b64encode(connect_string.encode("ascii")).decode("ascii")

    def get_header(self):
        return {'Authorization': 'Basic {}'.format(self._token)}

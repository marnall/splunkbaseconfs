"""Client module for interacting with the XM Cyber API."""
import import_declare_test  # noqa: F401
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from xmcyber_utils import (
    get_proxy_info,
    get_account,
    get_xmcyber_session_headers,
    update_access_token,
)

from xmcyber_constants import (
    PROTOCOL,
    VERIFY,
    STATUS_FORCELIST,
    ALL_ENTITIES_ENDPOINT,
    ALL_INVENTORY_ENTITIES_ENDPOINT,
    API_REQUEST_TIMEOUT,
    GET_SENSORS_ENDPOINT,
    GET_SCENARIOS_ENDPOINT,
    GET_SECURITY_RISK_SCORE_ENDPOINT,
    GET_FINDINGS_EXPOSURES_ENDPOINT,
    GET_AUDIT_TRAIL_ENDPOINT,
    GET_DEVICES_ENDPOINT,
    GET_PRODUCTS_ENDPOINT,
    GET_VULNERABILITIES_ENDPOINT,
    REGENERATE_TOKEN_ENDPOINT,
    OAUTH_ENDPOINT,
    CHOKEPOINT_ENDPOINT
)


class XMCyberClient:
    """XMCyber Client for all XMCyber API related transactions."""

    def __init__(self, session_key, account_name, logger, input_name):
        """Initialize an object."""
        self.session_key = session_key
        self.logger = logger
        self.account_name = account_name
        self.account = get_account(account_name, self.session_key)
        self.auth_type = self.account.get("auth_type")
        self.base_url = f"{PROTOCOL}://{self.account.get('base_url')}"
        self.proxy = get_proxy_info(self.session_key, self.logger)
        self.session = self.get_session()
        self.session.verify = VERIFY
        self.session.proxies = self.proxy
        headers = get_xmcyber_session_headers(self.account)
        self.session.headers.update(headers)
        self.input_name = input_name

    def get_session(
        self,
        retries=3,
        backoff_factor=60,
        status_forcelist=STATUS_FORCELIST,
        method_whitelist=["GET", "POST", "PUT", "DELETE"],
    ):
        """
        Create and return a session object with retry mechanism.

        Args:
            retries: Maximum number of retries to attempt.
            backoff_factor: Backoff factor used to calculate time between retries.
            status_forcelist: A list containing the response status codes that should trigger a retry.
            method_whiltelist: HTTP methods on which retry will be performed.

        Returns:
            Session Object
        """
        session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            method_whitelist=method_whitelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        return session

    def handle_standard_response_codes(self, response):
        """
        Handle standards response status codes.

        Args:
            response: Response object.

        Returns:
            Exception.
        """
        if response.status_code == 429:
            self.logger.error(
                f"input_name={self.input_name} Error from endpoint: API rate limit exceeded."
            )
            raise Exception("API rate limit exceeded.")
        elif response.status_code == 400:
            resp = response.json()
            self.logger.error(f"input_name={self.input_name} Error from endpoint: {resp.get('message')}.")
            raise Exception("Bad Request.")
        elif response.status_code == 404:
            self.logger.error(f"input_name={self.input_name} Error from endpoint: Resource not found.")
            raise Exception("Resource not found.")
        elif response.status_code == 403:
            self.logger.error(f"input_name={self.input_name} Error from endpoint: Insufficient permission.")
            raise Exception("Insufficient permission.")
        else:
            self.logger.error(
                f"input_name={self.input_name} Error from endpoint. Response status code: {response.status_code}."
            )
            raise Exception(f"Response status code : {response.status_code}.")

    def handle_auth_fail(self, response, func, *args, **kwargs):
        """
        Handle authentication fail status code.

        Args:
            response: Response object.
            func: function reference to be called after success tokens regenerated
            *args:  arguments for the functon referenced by func
            **kwargs: keyword arguments for the functon referenced by func

        Returns:
            Response object or Exception.
        """
        if response.status_code in (401, 419):
            if self.auth_type == "basic":
                self.logger.error(f"input_name={self.input_name} Basic Auth type not supported. Please use OAuth.")
                raise Exception("Invalid API Key.")
            # Regenerate access token here
            self.logger.info(
                f"input_name={self.input_name} Access token expired for user {self.account_name}."
                " Regenerating access token."
            )
            access_token, refresh_token = self.regenerate_access_tokens()
            self.logger.info(
                f"input_name={self.input_name} Sucessfully regenerated access token for user {self.account_name}."
            )
            self.logger.info(f"input_name={self.input_name} Updating access token for user {self.account_name}.")
            update_access_token(
                self.session_key,
                self.account_name,
                self.account.get("api_key"),
                access_token,
                refresh_token,
            )
            self.logger.info(
                f"input_name={self.input_name} Sucessfully updated access token for user {self.account_name}."
            )
            self.account = get_account(self.account_name, self.session_key)
            self.logger.info(
                f"input_name={self.input_name} Sucessfully fetched new access token for user {self.account_name}."
            )
            headers = get_xmcyber_session_headers(self.account)
            self.session.headers = headers
            # Make the API call again with the new access token
            try:
                response = func(self, *args, **kwargs)
            except requests.exceptions.ProxyError as e:
                self.logger.error(f"input_name={self.input_name} Proxy Error: {e}.")
                raise Exception(
                    "Proxy Error occured, Please verify the configured proxy details."
                )
            except requests.exceptions.SSLError as e:
                self.logger.error(f"input_name={self.input_name} SSL Error: {e}.")
                raise Exception(
                    "SSL Error occured, Please verify the certificate for provided configuration."
                )
        return response

    def handle_response(func):
        """Handle common errors in API response."""  # noqa: D202

        fname = func.__name__

        def wrapper(self, *args, **kwargs):
            self.logger.debug(f"input_name={self.input_name} Function {fname} called.")
            try:
                response = func(self, *args, **kwargs)
            except requests.exceptions.ProxyError as e:
                self.logger.error(f"input_name={self.input_name} Proxy Error: {e}.")
                raise Exception(
                    "Proxy Error occured, Please verify the configured proxy details."
                )
            except requests.exceptions.SSLError as e:
                self.logger.error(f"input_name={self.input_name} SSL Error: {e}.")
                raise Exception(
                    "SSL Error occured, Please verify the certificate for provided configuration."
                )
            self.logger.debug(f"input_name={self.input_name} Response status code: {response.status_code}")
            response = self.handle_auth_fail(response, func, *args, *kwargs)
            if response.status_code in (200, 201, 204):
                return response.json()
            self.handle_standard_response_codes(response)

        # Store the original function name as an attribute of the wrapper
        wrapper.original_func_name = fname
        return wrapper

    @handle_response
    def get_all_entities(self, parameters):
        """
        Fetch compromised Entities data.

        Returns:
            Response object.
        """
        url = f"{self.base_url}{ALL_ENTITIES_ENDPOINT}"
        self.log_details(url, parameters)
        response = self.session.get(url, params=parameters, timeout=API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def get_all_inventory_entities(self, parameters):
        """
        Fetch All Inventory Entities data.

        Returns:
            Response object.
        """
        url = f"{self.base_url}{ALL_INVENTORY_ENTITIES_ENDPOINT}"
        self.log_details(url, parameters)
        response = self.session.get(url, params=parameters, timeout=API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def get_chokepoint_stats(self):
        """
        Fetch chokepoint stats.

        Returns:
            Response object.
        """
        url = f"{self.base_url}{CHOKEPOINT_ENDPOINT}"
        self.log_details(
            url,
            None
        )
        response = self.session.get(url, timeout=API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def get_sensors(self, parameters):
        """
        Fetch Sensors data.

        Returns:
            Response object.
        """
        url = f"{self.base_url}{GET_SENSORS_ENDPOINT}"
        self.log_details(url, parameters)
        response = self.session.get(url, params=parameters, timeout=API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def get_products(self, parameters):
        """
        Fetch Products data.

        Returns:
            Response object.
        """
        url = f"{self.base_url}{GET_PRODUCTS_ENDPOINT}"
        self.log_details(url, parameters)
        response = self.session.get(url, params=parameters, timeout=API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def get_devices(self, parameters):
        """
        Fetch Devices data.

        Returns:
            Response object.
        """
        url = f"{self.base_url}{GET_DEVICES_ENDPOINT}"
        self.log_details(url, parameters)
        response = self.session.get(url, params=parameters, timeout=API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def get_vulnerabilities(self, parameters):
        """
        Fetch Vulnerabilities data.

        Returns:
            Response object.
        """
        url = f"{self.base_url}{GET_VULNERABILITIES_ENDPOINT}"
        self.log_details(url, parameters)
        response = self.session.get(url, params=parameters, timeout=API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def get_scenarios(self, parameters):
        """
        Fetch Scenarios data.

        Returns:
            Response object.
        """
        url = f"{self.base_url}{GET_SCENARIOS_ENDPOINT}"
        self.log_details(url, parameters)
        response = self.session.get(url, params=parameters, timeout=API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def get_security_risk_score(self, parameters):
        """
        Fetch Security Risk Score data.

        Returns:
            Response object.
        """
        url = f"{self.base_url}{GET_SECURITY_RISK_SCORE_ENDPOINT}"
        self.log_details(url, parameters)
        response = self.session.get(url, params=parameters, timeout=API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def get_findings_exposures(self, parameters):
        """
        Fetch Finding Exposures data.

        Returns:
            Response object.
        """
        url = f"{self.base_url}{GET_FINDINGS_EXPOSURES_ENDPOINT}"
        self.log_details(url, parameters)
        response = self.session.get(url, params=parameters, timeout=API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def get_audit_trail(self, parameters):
        """
        Fetch Audit Trails data.

        Returns:
            Response object.
        """
        url = f"{self.base_url}{GET_AUDIT_TRAIL_ENDPOINT}"
        self.log_details(url, parameters)
        response = self.session.get(url, params=parameters, timeout=API_REQUEST_TIMEOUT)
        return response

    def regenerate_access_tokens(self):
        """
        Regenerate and return Access token for authentication.

        Returns:
            Regenerated Token values.
        """
        token_url = f"{self.base_url}{REGENERATE_TOKEN_ENDPOINT}"

        data = {"refreshToken": self.account.get("refresh_token")}

        headers = {"Content-type": "application/json"}
        self.log_details(token_url, None)
        response = requests.post(
            token_url,
            headers=headers,
            data=data,
            verify=VERIFY,
            proxies=self.proxy,
            timeout=API_REQUEST_TIMEOUT,
        )
        self.logger.debug(f"input_name={self.input_name} Response status code: {response.status_code}")
        if response.status_code in (400, 401):
            self.logger.debug(f"input_name={self.input_name} Refresh Token expired.")
            oauth_url = f"{self.base_url}{OAUTH_ENDPOINT}"
            headers = {"x-api-key": self.account.get("api_key")}
            self.log_details(oauth_url, None)
            response = requests.post(
                oauth_url,
                headers=headers,
                verify=VERIFY,
                proxies=self.proxy,
                timeout=API_REQUEST_TIMEOUT,
            )
            self.logger.debug(f"input_name={self.input_name} Response status code: {response.status_code}")
        if response.status_code == 200:
            self.logger.debug(f"input_name={self.input_name} Regenerating Access token and Refresh token.")
            response = response.json()
            access_token = response.get("accessToken", None)
            refresh_token = response.get("refreshToken", None)
            return access_token, refresh_token
        else:
            self.logger.error(
                f"input_name={self.input_name} Error while re-generating tokens. Status code: {response.status_code}"
            )
            raise Exception(
                f"Unable to regenerate access token. Status code :{response.status_code}."
            )

    def log_details(self, url, params):
        """Log API request details.

        Args:
            url (str): URLs
            params (dict): Parameters
        """
        message = f"input_name={self.input_name} API Request details. URL: {url}. Params: {params}."
        self.logger.debug(message)

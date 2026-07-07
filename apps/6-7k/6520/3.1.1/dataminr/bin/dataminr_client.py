import json
import os
import traceback
import import_declare_test    # noqa: F401
import requests
from requests.adapters import HTTPAdapter
from urllib.parse import urlparse, parse_qs
from requests.packages.urllib3.util.retry import Retry
from dataminr_constants import (
    VERIFY_SSL,
    DATAMINR_BASE_URL,
    DATAMINR_BASE_URL_V4,
    DATAMINR_AUTH_ENDPOINT,
    DATAMINR_AUTH_ENDPOINT_V4,
    GRANT_TYPE,
    HEADER_AUTH_PREFIX,
    HEADER_AUTH_PREFIX_V4,
    NOT_SUPPORTED_WATCHLIST_TYPES,
    REQUEST_TIMEOUT,
    APPLICATION_TYPE
)
from dataminr_utils import (
    get_proxy_info,
    update_access_token,
    get_credentials
)
from log_helper import setup_logging

logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0].lower())


class DataminrClient:
    """Dataminr API client for all Dataminr API related transactions."""

    API_REQUEST_TIMEOUT = REQUEST_TIMEOUT
    STATUS_FORCELIST = list(range(500, 600)) + [429]
    BASE_URL = DATAMINR_BASE_URL
    AUTH_ENDPOINT = DATAMINR_AUTH_ENDPOINT
    AUTH_GRANT_TYPE = GRANT_TYPE
    AUTH_PREFIX = HEADER_AUTH_PREFIX
    VERIFY = VERIFY_SSL
    WATCHLIST_ENDPOINT = "account/2/get_lists"
    WEBHOOK_ENDPOINT = "integration/1/settings"
    ALERTS_ENDPOINT = "api/3/alerts"
    ALERT_VERSION = 14
    INTEGRATION_VERSION = "3.1.0"
    PAGE_SIZE = 100

    def __init__(self, session_key, account_name):
        """Initialize an object."""
        self.session_key = session_key
        self.account_name = account_name
        self.account = get_credentials(account_name, self.session_key)
        self.proxy = get_proxy_info(self.session_key, logger)
        self.session = self.get_session()
        self.session.verify = self.VERIFY
        self.session.proxies = self.proxy
        self.session.headers.update({
            "Authorization": f"{self.AUTH_PREFIX} {self.account.get('access_token')}",
            "Content-type": "application/json",
            "Accept": "application/json"
        })
        # check if this needs to be removed

    def get_session(
        self,
        retries=3,
        backoff_factor=60,
        status_forcelist=STATUS_FORCELIST,
        method_whitelist=["GET", "POST", "PUT", "DELETE"]
    ):
        """
        Create and return a session object with retry mechanism.

        :param retries: Maximum number of retries to attempt.
        :param backoff_factor: Backoff factor used to calculate time between retries.
        :param status_forcelist: A list containing the response status codes that should trigger a retry.
        :param method_whiltelist: HTTP methods on which retry will be performed.

        :return: Session Object
        """
        session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            method_whitelist=method_whitelist
        )
        adapter = HTTPAdapter(max_retries=retry)
        # session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def handle_response(func):
        """Handle common errors in API response."""  # noqa: D202

        fname = func.__name__

        def wrapper(self, *args, **kwargs):
            logger.info(f"Function {fname} called.")
            response = func(self, *args, **kwargs)
            if response.status_code in (200, 201):
                return response.json()
            elif response.status_code == 204:
                return response
            elif response.status_code == 401:
                # Regenerate access token here
                logger.info("Regenerating access token.")
                regenerated_access_token = self.regenerate_access_tokens()
                logger.info("Successfully regenerated access token.")
                logger.info("Updating access token.")
                update_access_token(
                    self.account_name, self.account,
                    regenerated_access_token, self.session_key
                )
                logger.info("Successfully updated access token.")
                self.account = get_credentials(self.account_name, self.session_key)
                logger.info("Successfully fetched updated access token.")
                self.session.headers.update({
                    "Authorization": f"{self.AUTH_PREFIX} {self.account.get('access_token')}",
                    "Content-type": "application/json",
                    "Accept": "application/json"
                })
                # Make the API call again with the new access token
                response = func(self, *args, **kwargs)
                return response.json()
            elif response.status_code == 429:
                logger.error(f"API rate limit exceeded: {traceback.format_exc()}")
                raise Exception("API rate limit exceeded.")
            else:
                logger.error(f"Error occured: {traceback.format_exc()}")
                raise Exception(
                    f"Unexpected Error occurred in function {fname} : {response.status_code} : {response.text}"
                )
        return wrapper

    def parse_watchlist_response(func):
        """Parse Dataminr watchlist API response."""
        def wrapper(self, *args, **kwargs):
            response = func(self, *args, **kwargs)
            watch_lists = []
            for list_type, lists in response.get("watchlists").items():
                if list_type not in NOT_SUPPORTED_WATCHLIST_TYPES:
                    watch_lists.extend(lists)
            if not len(watch_lists):
                raise Exception("No watchlists created.")
            return watch_lists
        return wrapper

    def regenerate_access_tokens(self):
        """
        Regenerate and return Access token for authentication.

        :return: Regenerated Access Token value.
        """
        token_url = (f"{self.BASE_URL}{self.AUTH_ENDPOINT}")

        data = {"grant_type": self.AUTH_GRANT_TYPE,
                "client_id": self.account.get("client_id"),
                "client_secret": self.account.get("client_secret")}

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = requests.post(
                token_url, headers=headers, data=data, verify=VERIFY_SSL,
                proxies=self.proxy, timeout=self.API_REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                response = response.json()
                access_token = response.get("dmaToken", None)
                return access_token
            else:
                raise Exception(f"Unable to regenerate access token. Status code :{response.status_code}")
        except Exception:
            raise

    @handle_response
    def add_update_dataminr_webhook(self, payload, webhook_id=None):
        """
        Add / Update the Dataminr Pulse webhook URL.

        :param payload : Payload for creating / updating webhook.
        :param webhook_id (Optional) : Webhook Id of webhook to be updated.

        :return: Response Object.
        """
        payload = json.dumps(payload)
        if webhook_id is None:
            webhook_url = f"{self.BASE_URL}{self.WEBHOOK_ENDPOINT}"
            response = self.session.post(webhook_url, data=payload, timeout=self.API_REQUEST_TIMEOUT)
        else:
            webhook_url = f"{self.BASE_URL}{self.WEBHOOK_ENDPOINT}/{webhook_id}"
            response = self.session.put(webhook_url, data=payload, timeout=self.API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def delete_dataminr_webhook(self, webhook_id):
        """
        Delete the Dataminr Pulse webhook URL.

        :param webhook_id : Webhook Id of webhook to be deleted.

        :return: Response Object.
        """
        payload = json.dumps({})
        webhook_url = f"{self.BASE_URL}{self.WEBHOOK_ENDPOINT}/{webhook_id}"
        response = self.session.delete(webhook_url, data=payload, timeout=self.API_REQUEST_TIMEOUT)
        return response

    @parse_watchlist_response
    @handle_response
    def get_all_watchlists(self):
        """
        Fetch all the Dataminr Pulse watchlists.

        :return: Response Object.
        """
        watchlist_url = f"{self.BASE_URL}{self.WATCHLIST_ENDPOINT}"
        return self.session.get(watchlist_url, data={}, timeout=self.API_REQUEST_TIMEOUT)

    @handle_response
    def get_alerts(self, list_ids, from_cursor=None):
        """
        Fetch Alert events from Dataminr Pulse.

        :param list_ids : Watchlist Ids to fetch alerts from.
        :param from_cursor (Optional) : Begining cursor from where to collect Alerts.

        :return: Response Object.
        """
        alerts_url = f"{self.BASE_URL}{self.ALERTS_ENDPOINT}"
        params = {
            "alertversion": self.ALERT_VERSION,
            "lists": ','.join(map(str, list_ids)),
            "num": self.PAGE_SIZE,
            "application": APPLICATION_TYPE,
            "application_version": self.INTEGRATION_VERSION,
            "integration_version": self.INTEGRATION_VERSION
        }
        if from_cursor:
            params["from"] = from_cursor
        return self.session.get(alerts_url, params=params, data={}, timeout=self.API_REQUEST_TIMEOUT)


class DataminrClientV4:
    """Dataminr API client for all Dataminr API related transactions."""

    API_REQUEST_TIMEOUT = REQUEST_TIMEOUT
    STATUS_FORCELIST = list(range(500, 600)) + [429]
    BASE_URL = DATAMINR_BASE_URL_V4
    AUTH_ENDPOINT = DATAMINR_AUTH_ENDPOINT_V4
    AUTH_GRANT_TYPE = GRANT_TYPE
    AUTH_PREFIX = HEADER_AUTH_PREFIX_V4
    VERIFY = VERIFY_SSL
    WATCHLIST_ENDPOINT = "pulse/v1/lists"
    ALERTS_ENDPOINT = "pulse/v1/alerts"
    INTEGRATION_VERSION = "3.1.0"
    PAGE_SIZE = 100

    def __init__(self, session_key, account_name):
        """Initialize an object."""
        self.session_key = session_key
        self.account_name = account_name
        self.account = get_credentials(account_name, self.session_key)
        self.proxy = get_proxy_info(self.session_key, logger)
        self.session = self.get_session()
        self.session.verify = self.VERIFY
        self.session.proxies = self.proxy
        self.session.headers.update({
            "Authorization": f"{self.AUTH_PREFIX} {self.account.get('access_token')}",
            "Content-type": "application/json",
            "Accept": "application/json",
            "X-Application-Name": APPLICATION_TYPE,
            "application_version": self.INTEGRATION_VERSION,
            "integration_version": self.INTEGRATION_VERSION
        })
        # check if this needs to be removed

    def get_session(
        self,
        retries=3,
        backoff_factor=60,
        status_forcelist=STATUS_FORCELIST,
        method_whitelist=["GET", "POST", "PUT", "DELETE"]
    ):
        """
        Create and return a session object with retry mechanism.

        :param retries: Maximum number of retries to attempt.
        :param backoff_factor: Backoff factor used to calculate time between retries.
        :param status_forcelist: A list containing the response status codes that should trigger a retry.
        :param method_whiltelist: HTTP methods on which retry will be performed.

        :return: Session Object
        """
        session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            method_whitelist=method_whitelist
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        return session

    def handle_response(func):
        """Handle common errors in API response."""  # noqa: D202

        fname = func.__name__

        def wrapper(self, *args, **kwargs):
            logger.info(f"Function {fname} called.")
            response = func(self, *args, **kwargs)
            if response.status_code in (200, 201):
                return response.json()
            elif response.status_code == 204:
                return response
            elif response.status_code == 401:
                # Regenerate access token here
                logger.info("Regenerating access token.")
                regenerated_access_token = self.regenerate_access_tokens()
                logger.info("Successfully regenerated access token.")
                logger.info("Updating access token.")
                update_access_token(
                    self.account_name, self.account,
                    regenerated_access_token, self.session_key
                )
                logger.info("Successfully updated access token.")
                self.account = get_credentials(self.account_name, self.session_key)
                logger.info("Successfully fetched updated access token.")
                self.session.headers.update({
                    "Authorization": f"{self.AUTH_PREFIX} {self.account.get('access_token')}",
                    "Content-type": "application/json",
                    "Accept": "application/json",
                    "X-Application-Name": APPLICATION_TYPE,
                    "application_version": self.INTEGRATION_VERSION,
                    "integration_version": self.INTEGRATION_VERSION
                })
                # Make the API call again with the new access token
                response = func(self, *args, **kwargs)
                return response.json()
            elif response.status_code == 429:
                logger.error(f"API rate limit exceeded: {traceback.format_exc()}")
                raise Exception("API rate limit exceeded.")
            else:
                logger.error(f"Error occured: {traceback.format_exc()}")
                raise Exception(
                    f"Unexpected Error occurred in function {fname} : {response.status_code} : {response.text}"
                )
        return wrapper

    def parse_watchlist_response(func):
        """Parse Dataminr watchlist API response."""
        def wrapper(self, *args, **kwargs):
            response = func(self, *args, **kwargs)
            watch_lists = []
            for list_type, lists in response.get("lists").items():
                if list_type not in NOT_SUPPORTED_WATCHLIST_TYPES:
                    watch_lists.extend(lists)
            if not len(watch_lists):
                raise Exception("No watchlists created.")
            return watch_lists
        return wrapper

    def regenerate_access_tokens(self):
        """
        Regenerate and return Access token for authentication.

        :return: Regenerated Access Token value.
        """
        token_url = (f"{self.BASE_URL}{self.AUTH_ENDPOINT}")

        data = {"grant_type": self.AUTH_GRANT_TYPE,
                "client_id": self.account.get("client_id"),
                "client_secret": self.account.get("client_secret")}

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = requests.post(
                token_url, headers=headers, data=data, verify=VERIFY_SSL,
                proxies=self.proxy, timeout=self.API_REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                response = response.json()
                access_token = response.get("dmaToken", None)
                return access_token
            else:
                raise Exception(f"Unable to regenerate access token. Status code :{response.status_code}")
        except Exception:
            raise

    @parse_watchlist_response
    @handle_response
    def get_all_watchlists(self):
        """
        Fetch all the Dataminr Pulse watchlists.

        :return: Response Object.
        """
        watchlist_url = f"{self.BASE_URL}{self.WATCHLIST_ENDPOINT}"
        return self.session.get(watchlist_url, timeout=self.API_REQUEST_TIMEOUT)

    @handle_response
    def get_alerts(self, list_ids, next_page=None):
        """
        Fetch Alert events from Dataminr Pulse.

        :param list_ids : Watchlist Ids to fetch alerts from.
        :param next_page (Optional) : Cursor URL for paginated results.

        :return: Response Object.
        """
        alerts_url = f"{self.BASE_URL}{self.ALERTS_ENDPOINT}"
        params = {
            "lists": ','.join(map(str, list_ids)),
            "pageSize": self.PAGE_SIZE
        }

        if next_page:
            parsed = urlparse(next_page)
            query_params = parse_qs(parsed.query)
            # parse_qs returns values as lists
            if "from" in query_params:
                params["from"] = query_params["from"][0]
            if "pageSize" in query_params:
                params["pageSize"] = query_params["pageSize"][0]

        return self.session.get(alerts_url, params=params, timeout=self.API_REQUEST_TIMEOUT)

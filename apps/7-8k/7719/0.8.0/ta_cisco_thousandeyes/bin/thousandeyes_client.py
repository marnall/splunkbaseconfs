import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests import Response

import import_declare_test  # noqa: F401
from thousandeyes_account_manager import ThousandEyesAccountManager
from thousandeyes_constant import (
    CEA_TEST_TYPES,
    CEA_TEST_TYPES_FOR_METRICS,
    CEA_TEST_TYPES_FOR_TRACES,
    CLIENT_ID,
    DEFAULT_ENDPOINT_DYNAMIC_TEST_TYPE,
    ENDPOINT_TEST_TYPES,
    HEADER_AUTH_PREFIX,
    REGENERATE_GRANT_TYPE,
    REQUEST_TIMEOUT,
    THOUSANDEYES_ACC_GROUP_ENDPOINT,
    THOUSANDEYES_ACTIVITY_URL,
    THOUSANDEYES_ALERTS_RULES_ENDPOINT,
    THOUSANDEYES_AUTH_ENDPOINT,
    THOUSANDEYES_BASE_URL,
    THOUSANDEYES_CEA_PATH_INFO_URL,
    THOUSANDEYES_CEA_TEST_ENDPOINT,
    THOUSANDEYES_CONNECTORS_ENDPOINT,
    THOUSANDEYES_CREATE_STREAM,
    THOUSANDEYES_ENDPOINT_SCHEDULED_PATH_INFO_URL,
    THOUSANDEYES_ENDPOINT_DYNAMIC_PATH_INFO_URL,
    THOUSANDEYES_ENDPOINT_SCHEDULED_TEST_ENDPOINT,
    THOUSANDEYES_ENDPOINT_DYNAMIC_TEST_ENDPOINT,
    THOUSANDEYES_EVENT_URL,
    THOUSANDEYES_TAGS_ENDPOINT,
    TAGS_EXPAND_ASSIGNMENTS,
    THOUSANDEYES_TOKEN_API_ENDPOINT,
    THOUSANDEYES_WEBHOOKS_OPERATIONS_ENDPOINT,
    THOUSANDEYES_INGEST_ENDPOINT,
)
from thousandeyes_utils import get_credentials, get_proxy_info, is_https
from exceptions import InsufficientPermissionsError


class ThousandEyesClient:
    """ThousandEyes Client for all ThousandEyes API related transactions."""

    API_REQUEST_TIMEOUT = REQUEST_TIMEOUT
    BASE_URL = THOUSANDEYES_BASE_URL
    AUTH_ENDPOINT = THOUSANDEYES_AUTH_ENDPOINT
    TOKEN_ENDPOINT = THOUSANDEYES_TOKEN_API_ENDPOINT
    ACC_GROUP_ENDPOINT = THOUSANDEYES_ACC_GROUP_ENDPOINT
    CEA_TEST_ENDPOINT = THOUSANDEYES_CEA_TEST_ENDPOINT
    ENDPOINT_SCHEDULED_TEST_ENDPOINT = THOUSANDEYES_ENDPOINT_SCHEDULED_TEST_ENDPOINT
    ENDPOINT_DYNAMIC_TEST_ENDPOINT = THOUSANDEYES_ENDPOINT_DYNAMIC_TEST_ENDPOINT
    CREATE_STREAM = THOUSANDEYES_CREATE_STREAM
    CEA_PATH_URL = THOUSANDEYES_CEA_PATH_INFO_URL
    ENDPOINT_SCHEDULED_PATH_URL = THOUSANDEYES_ENDPOINT_SCHEDULED_PATH_INFO_URL
    ENDPOINT_DYNAMIC_PATH_URL = THOUSANDEYES_ENDPOINT_DYNAMIC_PATH_INFO_URL
    EVENT_URL = THOUSANDEYES_EVENT_URL
    ACTIVITY_URL = THOUSANDEYES_ACTIVITY_URL
    AUTH_PREFIX = HEADER_AUTH_PREFIX
    INGEST_EVENT_ENDPOINT = THOUSANDEYES_INGEST_ENDPOINT
    TAGS_ENDPOINT = THOUSANDEYES_TAGS_ENDPOINT
    STATUS_FORCELIST = list(range(500, 600)) + [429]

    def __init__(self, session_key, account_name, logger):
        """
        Initialize object.

        :param session_key: Session key.
        :param account_name: Configured Thousandeyes user.
        :param logger: Logger object.

        :return: ThousandEyesClient Object
        """
        self.session_key = session_key
        self.account_name = account_name
        self.logger = logger
        self.account = get_credentials(account_name, self.session_key)
        self.proxy, self.verify = get_proxy_info(self.session_key, self.logger)
        self.session = self.get_session()
        self.session.verify = self.verify
        self.session.proxies = self.proxy
        access_token = self.account.get("access_token")
        self.session.headers.update(
            {
                "Authorization": f"{self.AUTH_PREFIX} {access_token}",
                "Content-type": "application/json",
                "Accept": "application/hal+json",
            }
        )

    def get_session(
        self,
        retries=3,
        backoff_factor=60,
        status_forcelist=STATUS_FORCELIST,
        method_whitelist=["GET", "POST", "PUT", "DELETE"],
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
            method_whitelist=method_whitelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        return session

    def parse_cea_test_data(self, response_data, allowed_types=None):
        """
        Filter CEA Test data.

        :param response_data: CEA Tests API response.
        :param allowed_types: List of allowed test types. Defaults to CEA_TEST_TYPES.

        :return: CEA tests dict.
        """
        if allowed_types is None:
            allowed_types = CEA_TEST_TYPES

        self.logger.info("Parsing Cloud & Enterprise Agent Tests list.")
        tests_list = [
            test
            for test in response_data.get("tests")
            if test.get("savedEvent") is False
            and test.get("liveShare") is False
            and test.get("type").lower() in allowed_types
        ]
        return {"tests": tests_list}

    def parse_endpoint_test_data(self, response_data):
        """
        Filter Endpoint Test data.

        :param response_data: Endpoint Tests API response.

        :return: Endpoint tests dict.
        """
        self.logger.info("Parsing Endpoint Agent Tests list.")
        tests_list = [
            test
            for test in response_data.get("tests")
            # Filter out saved events. Dynamic tests don't have isSavedEvent field
            # because the dynamic endpoint already filters for isSavedEvent=false
            if test.get("isSavedEvent", False) is False
            and test.get("type", DEFAULT_ENDPOINT_DYNAMIC_TEST_TYPE).lower() in ENDPOINT_TEST_TYPES
        ]
        
        return {"tests": tests_list}

    def handle_success(self, response, fname):
        """
        Handle successful API response.

        :param response: API response object.
        :param fname: function name called.

        :return: Response json.
        """
        if response.status_code == 204 or not response.content:
            return True
        elif fname == "get_all_cea_tests_for_metrics":
            return self.parse_cea_test_data(response.json(), CEA_TEST_TYPES_FOR_METRICS)
        elif fname == "get_cea_tests_for_traces":
            return self.parse_cea_test_data(response.json(), CEA_TEST_TYPES_FOR_TRACES)
        else:
            return response.json()

    def handle_status_400(self, response, fname):
        """
        Handle API response status code 400.

        :param response: API response object.
        :param fname: function name called.

        :return: Exception.
        """
        try:
            resp = response.json()
        except ValueError:
            self.logger.error(f'Got 400 when calling {fname}: non-json body {response.content!r}')
            resp = {}

        err_msg = (resp.get("errors") or [resp.get("title", "Bad Request.")])[0]
        self.logger.error(f"Error occurred from endpoint - {err_msg}: {resp}.")

        if fname in ("add_new_stream", "update_stream"):
            if "TLS/SSL" in err_msg:
                raise Exception("The TLS/SSL certificate for the splunk instance is incorrect or not set correctly.")
            elif "I/O issue" in err_msg or "connection issue" in err_msg:
                raise Exception(
                    "The Server Name, Host Name and Host is not reachable from Cisco Thousandeyes. One of these needs to be configured so that it is reachable from Cisco Thousandeyes."
                )
        raise Exception(err_msg)

    def handle_status_404(self, fname):
        """
        Handle API response status code 404.

        :param fname: function name called.

        :return: Boolean or Exception.
        """
        if fname == "delete_stream":
            self.logger.warning("The stream is already deleted.")
            return True
        else:
            self.logger.error("Error occurred from endpoint: Resource not found.")
            raise Exception("Resource not found.")

    def handle_response(func):
        """
        Handle common errors from API response.

        :param fname: function name called.

        :return: Parsed API response.
        """
        fname = func.__name__

        def wrapper(self, *args, **kwargs):
            self.logger.info(f"Function {fname} called.")
            try:
                response = func(self, *args, **kwargs)
                self.logger.debug(f"Function {fname} executed with response {response}.")
            except requests.exceptions.ProxyError as e:
                self.logger.error(f"Proxy Error: {e}.")
                raise Exception(
                    "Proxy Error occured, Please verify the configured proxy details."
                )
            except requests.exceptions.SSLError as e:
                self.logger.error(f"SSL Error: {e}.")
                raise Exception(
                    "SSL Error occured, Please verify the certificate for provided configuration."
                )
            if response.status_code == 401:
                # Regenerate access token here
                self.logger.info(
                    f"Access token expired for user {self.account_name}. Regenerating access token."
                )
                access_token, refresh_token = self.regenerate_access_tokens()
                self.logger.info(
                    f"Sucessfully regenerated access token for user {self.account_name}."
                )
                self.logger.info(f"Updating access token for user {self.account_name}.")
                ThousandEyesAccountManager(self.session_key).update_access_token(
                    access_token,
                    refresh_token,
                    self.account_name,
                )
                self.logger.info(
                    f"Sucessfully updated access token for user {self.account_name}."
                )
                self.account = get_credentials(self.account_name, self.session_key)
                self.logger.info(
                    f"Sucessfully fetched updated access token for user {self.account_name}."
                )
                self.session.headers.update(
                    {
                        "Authorization": f"{self.AUTH_PREFIX} {self.account.get('access_token')}",
                        "Content-type": "application/json",
                        "Accept": "application/hal+json",
                    }
                )
                # Make the API call again with the new access token
                response = func(self, *args, **kwargs)

            if response.status_code in (200, 201, 204):
                return self.handle_success(response, fname)
            elif response.status_code == 429:
                self.logger.error(
                    "Error occurred from endpoint: API rate limit exceeded."
                )
                raise Exception("API rate limit exceeded.")
            elif response.status_code == 400:
                return self.handle_status_400(response, fname)
            elif response.status_code == 403:
                self.logger.error(
                    "Error occurred from endpoint: Insufficient permissions to query endpoint."
                )
                raise InsufficientPermissionsError("Insufficient permissions to query endpoint.")
            elif response.status_code == 404:
                return self.handle_status_404(fname)
            elif response.status_code == 412 and fname == "add_new_stream":
                resp = response.json()
                error_msg = resp.get("errors", ["Maximum limit reached."])[0]
                self.logger.error(f"Error occurred from endpoint: {error_msg}.")
                raise Exception(error_msg)
            else:
                self.logger.error(
                    f"Error occurred from endpoint. Response status code: {response.status_code}."
                )
                raise Exception(f"Response status code: {response.status_code}.")

        return wrapper

    @handle_response
    def get_all_acc_groups(self):
        """
        Fetch all the Account Groups of ThousandEyes.

        :return: Response Object.
        """
        url = f"{self.BASE_URL}{self.ACC_GROUP_ENDPOINT}"
        response = self.session.get(url, timeout=self.API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def get_all_cea_tests_for_metrics(self, aid):
        """
        Fetch all the CEA Tests of a given Account Group ID.

        :param aid: Account group Id.

        :return: Response Object.
        """
        self.logger.debug(f"Cloud & Enterprise Agent tests for account id: {aid}")
        url = f"{self.BASE_URL}{self.CEA_TEST_ENDPOINT}"
        response = self.session.get(
            url,
            params={"aid": aid},
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    def _get_endpoint_tests(self, endpoint, aid):
        """
        Generic method to fetch endpoint tests from a given endpoint.

        :param endpoint: API endpoint path.
        :param aid: Account group Id.

        :return: Response Object.
        """
        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.get(
            url, params={"aid": aid}, timeout=self.API_REQUEST_TIMEOUT
        )
        return response

    @handle_response
    def _get_scheduled_endpoint_tests(self, aid):
        """
        Fetch scheduled endpoint tests for a given Account Group ID.

        :param aid: Account group Id.

        :return: Response Object.
        """
        return self._get_endpoint_tests(self.ENDPOINT_SCHEDULED_TEST_ENDPOINT, aid)

    @handle_response
    def _get_dynamic_endpoint_tests(self, aid):
        """
        Fetch dynamic endpoint tests for a given Account Group ID.

        :param aid: Account group Id.

        :return: Response Object.
        """
        return self._get_endpoint_tests(self.ENDPOINT_DYNAMIC_TEST_ENDPOINT, aid)

    def _fetch_with_context(self, fetch_func, endpoint_name, *args, **kwargs):
        """
        Wrapper to call a fetch function with contextual error logging.
        
        :param fetch_func: The function to call.
        :param endpoint_name: Name of the endpoint for error logging.
        :param args: Arguments to pass to fetch_func.
        :param kwargs: Keyword arguments to pass to fetch_func.
        
        :return: Result from fetch_func.
        :raises: Exception with generic user message while logging specific details.
        """
        try:
            return fetch_func(*args, **kwargs)
        except Exception as e:
            self.logger.error(
                f"Failed to fetch {endpoint_name}. "
                f"Error: {str(e)}"
            )
            # Re-raise with generic user-facing message
            raise Exception("Unable to retrieve endpoint tests. Please try again later.") from e

    def get_all_endpoint_tests(self, aid):
        """
        Fetch all the Endpoint Tests (scheduled and dynamic) of a given Account Group ID.

        Both API calls use separate decorated helper methods (_get_scheduled_endpoint_tests
        and _get_dynamic_endpoint_tests) to ensure consistent error handling via the
        @handle_response decorator.
        The results from both endpoints are merged before filtering to provide
        a complete list of endpoint tests. Each test is tagged with its subtype
        ("scheduled" or "dynamic") for proper path URL routing.

        :param aid: Account group Id.

        :return: Parsed and filtered endpoint tests dict.
        """
        scheduled_tests_data = self._fetch_with_context(
            self._get_scheduled_endpoint_tests,
            f"scheduled endpoint tests (Endpoint: {self.ENDPOINT_SCHEDULED_TEST_ENDPOINT}, Account Group ID: {aid})",
            aid
        )
        
        dynamic_tests_data = self._fetch_with_context(
            self._get_dynamic_endpoint_tests,
            f"dynamic endpoint tests (Endpoint: {self.ENDPOINT_DYNAMIC_TEST_ENDPOINT}, Account Group ID: {aid})",
            aid
        )
        
        # Tag tests with their subtype before merging
        scheduled_tests = scheduled_tests_data.get("tests", [])
        for test in scheduled_tests:
            test["_endpointTestCategory"] = "scheduled"
        
        dynamic_tests = dynamic_tests_data.get("tests", [])
        for test in dynamic_tests:
            test["_endpointTestCategory"] = "dynamic"
        
        merged_tests = {
            "tests": scheduled_tests + dynamic_tests
        }
        
        # Parse and filter the merged data using existing logic
        return self.parse_endpoint_test_data(merged_tests)

    @handle_response
    def delete_stream(self, aid, stream_id):
        """
        Delete the given Stream Id.

        :param aid: Account group Id.
        :param stream_id: Stream Id to delete.

        :return: Response Object.
        """
        self.logger.debug(f"Deleting stream: {stream_id} from account id: {aid}")
        url = f"{self.BASE_URL}{self.CREATE_STREAM}/{stream_id}"
        response = self.session.delete(
            url, params={"aid": aid}, timeout=self.API_REQUEST_TIMEOUT
        )
        return response

    @handle_response
    def update_stream(self, aid, stream_id, payload):
        """
        Update the given Stream Id.

        :param aid: Account group Id.
        :param stream_id: Stream Id to delete.
        :param payload: Updated payload.

        :return: Response Object.
        """
        self.logger.debug(f"Update stream: {stream_id} for account id: {aid}")
        url = f"{self.BASE_URL}{self.CREATE_STREAM}/{stream_id}"
        response = self.session.put(
            url, params={"aid": aid}, data=payload, timeout=self.API_REQUEST_TIMEOUT
        )
        return response

    @handle_response
    def add_new_stream(self, aid, payload):
        """
        Create the given Stream Id.

        :param aid: Account group Id.
        :param payload: Create stream payload.

        :return: Response Object.
        """
        self.logger.debug(f"Add stream for account id: {aid}")
        url = f"{self.BASE_URL}{self.CREATE_STREAM}"
        response = self.session.post(
            url, params={"aid": aid}, data=payload, timeout=self.API_REQUEST_TIMEOUT
        )
        return response

    @handle_response
    def get_path_info(self, test_id, aid, test_type, endpoint_test_category=None):
        """
        Fetch the path visualization data for given Account Group.

        :param test_id: Test Id to fetch data for.
        :param aid: Account group Id to fetch data from.
        :param test_type: Test type of given Test Id ("cea" or "endpoint").
        :param endpoint_test_category: For endpoint tests, specifies "scheduled" or "dynamic".

        :return: Response Object.
        """

        if test_type == "endpoint":
            if endpoint_test_category == "dynamic":
                url = self.ENDPOINT_DYNAMIC_PATH_URL.format(self.BASE_URL, test_id)
            else:
                # Default to scheduled for backward compatibility
                url = self.ENDPOINT_SCHEDULED_PATH_URL.format(self.BASE_URL, test_id)
        else:
            url = self.CEA_PATH_URL.format(self.BASE_URL, test_id)
        
        parameters = {"aid": aid}
        self.logger.debug(f"parameters: {parameters}")
        response = self.session.get(
            url, params=parameters, timeout=self.API_REQUEST_TIMEOUT
        )
        return response

    @handle_response
    def get_paginated_data(self, url):
        """
        Fetch the paginated data.

        :param url: Cursor to get the paginated data.

        :return: Response Object.
        """
        self.logger.debug(f"page url: {url}")
        is_https(url)
        response = self.session.get(url, timeout=self.API_REQUEST_TIMEOUT)
        return response

    @handle_response
    def get_events(self, aid, start_date, end_date):
        """
        Fetch the Events data for given Account Group.

        :param aid: Account group Id.
        :param start_date: Start date to fetch data from.
        :param end_date: End date to fetch data upto.

        :return: Response Object.
        """
        url = self.EVENT_URL.format(self.BASE_URL)
        parameters = {"aid": aid, "startDate": start_date, "endDate": end_date}
        self.logger.debug(f"parameters: {parameters}")
        response = self.session.get(
            url, params=parameters, timeout=self.API_REQUEST_TIMEOUT
        )
        return response

    @handle_response
    def get_activity(self, aid, start_date, end_date):
        """
        Fetch the Activity data for given Account Group.

        :param aid: Account group Id.
        :param start_date: Start date to fetch data from.
        :param end_date: End date to fetch data upto.

        :return: Response Object.
        """
        url = self.ACTIVITY_URL.format(self.BASE_URL)
        if aid:
            parameters = {"aid": aid, "startDate": start_date, "endDate": end_date}
        else:
            parameters = {
                "useAllPermittedAids": True,
                "startDate": start_date,
                "endDate": end_date,
            }
        self.logger.debug(f"parameters: {parameters}")
        response = self.session.get(
            url, params=parameters, timeout=self.API_REQUEST_TIMEOUT
        )
        return response


    @handle_response
    def forward_splunk_event(self, alert, aid):
        """
        Forward the alert to ThousandEyes.

        :param alert: Alert data to forward.

        :return: Response Object.
        """
        url = f"{self.BASE_URL}{self.INGEST_EVENT_ENDPOINT}?aid={aid}"
        self.logger.debug(f"Forwarding event {alert} to {url}.")
        response = self.session.post(
            url, json=alert, timeout=self.API_REQUEST_TIMEOUT
        )
        return response


    def regenerate_access_tokens(self):
        """
        Regenerate and return Access token for authentication.

        :return: Regenerated Tokens.
        """
        token_url = f"{self.BASE_URL}{self.TOKEN_ENDPOINT}"

        data = {
            "grant_type": REGENERATE_GRANT_TYPE,
            "client_id": CLIENT_ID,
            "refresh_token": self.account.get("refresh_token"),
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = requests.post(
                token_url,
                headers=headers,
                data=data,
                verify=self.verify,
                proxies=self.proxy,
                timeout=self.API_REQUEST_TIMEOUT,
            )
        except requests.exceptions.ProxyError as e:
            self.logger.error(f"Proxy Error: {e}.")
            raise Exception(
                "Proxy Error occured, Please verify the configured proxy details."
            )
        except requests.exceptions.SSLError as e:
            self.logger.error(f"SSL Error: {e}.")
            raise Exception(
                "SSL Error occured, Please verify the certificate for provided configuration."
            )
        if response.status_code == 200:
            response = response.json()
            access_token = response.get("access_token", None)
            refresh_token = response.get("refresh_token", None)
            return access_token, refresh_token
        else:
            raise Exception(
                f"Unable to regenerate access token. Status code: {response.status_code}."
            )

    @handle_response
    def get_cea_tests_for_traces(self, aid):
        """
        Fetch CEA Tests filtered for traces (page-load and web-transactions only).

        :param aid: Account group Id.

        :return: Response Object.
        """
        self.logger.debug(
            f"Cloud & Enterprise Agent tests for trace, account id: {aid}"
        )
        url = f"{self.BASE_URL}{self.CEA_TEST_ENDPOINT}"
        response = self.session.get(
            url,
            params={"aid": aid},
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def get_alert_rules(self, aid):
        """
        Fetch Alert Rules.

        :param aid: Account group Id (optional).

        :return: Response Object.
        """
        self.logger.debug(f"Fetching alert rules, account id: {aid}")
        url = f"{self.BASE_URL}{THOUSANDEYES_ALERTS_RULES_ENDPOINT}"
        params = {}
        if aid:
            params["aid"] = aid
        response = self.session.get(
            url,
            params=params,
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def get_alert_rule(self, rule_id, aid):
        """
        Fetch specific Alert Rule.

        :param rule_id: Alert rule ID.
        :param aid: Account group Id (optional).

        :return: Response Object.
        """
        self.logger.debug(f"Fetching alert rule: {rule_id}")
        url = f"{self.BASE_URL}{THOUSANDEYES_ALERTS_RULES_ENDPOINT}/{rule_id}"
        params = {}
        if aid:
            params["aid"] = aid
        response = self.session.get(
            url,
            params=params,
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def update_alert_rule(self, rule_id, payload, aid):
        """
        Update Alert Rule.

        :param rule_id: Alert rule ID.
        :param payload: Rule data to update.
        :param aid: Account group Id (optional).

        :return: Response Object.
        """
        self.logger.debug(f"Updating alert rule: {rule_id}")
        url = f"{self.BASE_URL}{THOUSANDEYES_ALERTS_RULES_ENDPOINT}/{rule_id}"
        params = {}
        if aid:
            params["aid"] = aid
        response = self.session.put(
            url,
            json=payload,
            params=params,
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def create_webhook_operation(self, payload, aid):
        """
        Create Webhook Operation.

        :param payload: Webhook operation data.
        :param aid: Account group Id (optional).

        :return: Response Object.
        """
        self.logger.debug("Creating webhook operation")
        url = f"{self.BASE_URL}{THOUSANDEYES_WEBHOOKS_OPERATIONS_ENDPOINT}"
        params = {}
        if aid:
            params["aid"] = aid
        response = self.session.post(
            url,
            json=payload,
            params=params,
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def update_webhook_operation(self, operation_id, payload, aid):
        """
        Update Webhook Operation.

        :param payload: Webhook operation data.
        :param operation_id: Operation ID.
        :param aid: Account group Id (optional).

        :return: Response Object.
        """
        self.logger.debug(f"Updating webhook operation: {operation_id}")
        url = f"{self.BASE_URL}{THOUSANDEYES_WEBHOOKS_OPERATIONS_ENDPOINT}/{operation_id}"
        params = {}
        if aid:
            params["aid"] = aid
        response = self.session.put(
            url,
            json=payload,
            params=params,
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def get_webhooks(self, aid):
        """
        Get Webhooks for checking AUTH_SCOPE to be able to create alerts.

        :param aid: Account group Id (optional).

        :return: Response Object.
        """
        url = f"{self.BASE_URL}{THOUSANDEYES_WEBHOOKS_OPERATIONS_ENDPOINT}"
        params = {}
        if aid:
            params["aid"] = aid
        response = self.session.get(
            url,
            params=params,
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def get_webhook_operation(self, operation_id, aid):
        """
        Get a specific Webhook Operation by ID.

        :param operation_id: Operation ID.
        :param aid: Account group Id (optional).

        :return: Response Object.
        """
        self.logger.debug(f"Fetching webhook operation: {operation_id}")
        url = (
            f"{self.BASE_URL}{THOUSANDEYES_WEBHOOKS_OPERATIONS_ENDPOINT}/{operation_id}"
        )
        params = {}
        if aid:
            params["aid"] = aid
        response = self.session.get(
            url,
            params=params,
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def delete_webhook_operation(self, operation_id, aid):
        """
        Delete Webhook Operation.

        :param operation_id: Operation ID.
        :param aid: Account group Id (optional).

        :return: Response Object.
        """
        self.logger.debug(f"Deleting webhook operation: {operation_id}")
        url = (
            f"{self.BASE_URL}{THOUSANDEYES_WEBHOOKS_OPERATIONS_ENDPOINT}/{operation_id}"
        )
        params = {}
        if aid:
            params["aid"] = aid
        response = self.session.delete(
            url,
            params=params,
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def create_connector(self, payload, aid):
        """
        Create Connector.

        :param payload: Connector data.
        :param aid: Account group Id (optional).

        :return: Response Object.
        """
        self.logger.debug("Creating connector")
        url = f"{self.BASE_URL}{THOUSANDEYES_CONNECTORS_ENDPOINT}"
        params = {}
        if aid:
            params["aid"] = aid
        response = self.session.post(
            url,
            json=payload,
            params=params,
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def update_connector(self, connector_id, payload, aid):
        """
        Update Connector.

        :param connector_id: Connector ID.
        :param payload: Connector data to update.
        :param aid: Account group Id (optional).

        :return: Response Object.
        """
        self.logger.debug(f"Updating connector: {connector_id}")
        url = f"{self.BASE_URL}{THOUSANDEYES_CONNECTORS_ENDPOINT}/{connector_id}"
        params = {}
        if aid:
            params["aid"] = aid
        response = self.session.put(
            url,
            json=payload,
            params=params,
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def delete_connector(self, connector_id, aid):
        """
        Delete Connector.

        :param connector_id: Connector ID.
        :param aid: Account group Id (optional).

        :return: Response Object.
        """
        self.logger.debug(f"Deleting connector: {connector_id}")
        url = f"{self.BASE_URL}{THOUSANDEYES_CONNECTORS_ENDPOINT}/{connector_id}"
        params = {}
        if aid:
            params["aid"] = aid
        response = self.session.delete(
            url,
            params=params,
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def assign_operations_to_connector(self, operation_ids, connector_id, aid):
        """
        Assign Connectors to Operation.

        :param operation_ids: List of Operation IDs.
        :param connector_id: Connector ID.
        :param aid: Account group Id (optional).

        :return: Response Object.
        """
        self.logger.debug(
            f"Assigning operations {operation_ids} to connector: {connector_id}"
        )
        url = (
            f"{self.BASE_URL}{THOUSANDEYES_CONNECTORS_ENDPOINT}/{connector_id}/operations"
        )

        self.logger.debug(f"Assign operations URL: {url}")

        params = {}
        if aid:
            params["aid"] = aid
        response = self.session.put(
            url,
            json=operation_ids,
            params=params,
            timeout=self.API_REQUEST_TIMEOUT,
        )
        return response

    @handle_response
    def get_all_tags(self, aid):
        """
        Fetch all the Tags of a given Account Group ID.

        :param aid: Account group Id.

        :return: Response Object.
        """
        self.logger.debug(f"Tags for account id: {aid}")
        response = self._fetch_tags(aid)

        if response.status_code == 200:
            return self._filter_and_prepare_response(response)

        return response

    def _fetch_tags(self, aid):
        """Fetch tags from the API."""
        url = f"{self.BASE_URL}{self.TAGS_ENDPOINT}"
        return self.session.get(
            url,
            params={"aid": aid, "expand": TAGS_EXPAND_ASSIGNMENTS},
            timeout=self.API_REQUEST_TIMEOUT,
        )

    def _filter_and_prepare_response(self, response):
        """Filter tags and prepare the response object."""
        tags_data = response.json()
        filtered_tags = [
            tag for tag in tags_data.get("tags", [])
            if self._is_valid_tag(tag)
        ]
        tags_data["tags"] = filtered_tags

        return self._create_filtered_response(response, tags_data)

    def _is_valid_tag(self, tag):
        """Check if the tag is valid based on given criteria."""
        return (
            tag.get("objectType") in ("test", "endpoint-test") and
            tag.get("accessType") != "system"
        )

    def _create_filtered_response(self, original_response, tags_data):
        """Create a new response object with filtered tags."""
        filtered_response = Response()
        filtered_response.status_code = original_response.status_code
        filtered_response._content = json.dumps(tags_data).encode("utf-8")
        filtered_response.headers = original_response.headers
        filtered_response.url = original_response.url

        return filtered_response
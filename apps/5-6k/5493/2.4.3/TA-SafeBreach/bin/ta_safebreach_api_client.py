"""This is API client used for calling the customers API."""
import ta_safebreach_declare  # noqa: F401
import requests

from six.moves import urllib
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from ta_safebreach_utils import get_proxy_setting
from ta_safebreach_errors import (
    APIError,
    ConfigurationError,
    InvalidAPICredentialsError,
)
from solnlib.server_info import ServerInfo

STATUS_FORCELIST = list(range(500, 600)) + [
    429,
]
REQUEST_TIMEOUT = 120  # in seconds
REQUEST_POLL_TIME = 3  # in seconds
ACCOUNT_STANZA_NAME = "account"
COMMON_URL = "api"
ENDPOINTS = {
    "simulation": "data/v1/accounts/",
    "insights": "insights",
    "remediation": "remediation",
    "test_summaries": "testsummaries",
    "audit": "audit/v1/auditlogs/logs",
    "mitre_attck": "kb/v12/mitreAttacks"
}
SUCCESSFUL_STATUSCODE = list(range(200, 299))


class APIClient(object):
    """A Client for all IntSights API related transactions."""

    def __init__(self, session_key, helper):
        """Initialize an object."""
        self.session_key = session_key
        self.account = helper.get_arg('safebreach_account')
        self.domain = self.account.get('host_name')
        self.base_url = "https://{}/{}".format(self.domain.strip("/"), COMMON_URL)
        self.session = self.get_requests_retry_session()
        self.session.headers.update({"User-Agent":"Splunk-Addon/2.4.3 (Python; SafeBreach; Build/1.0.0)"})
        self.session.proxies = get_proxy_setting(helper.get_proxy())
        self.session.verify = True if (self.account.get('verify_ssl') == "1" or ServerInfo(self.session_key).is_cloud_instance()) else False

    @classmethod
    def validate_account(cls, account):
        """Validate the given account."""
        if not (
            isinstance(account, dict)
            and account.get("api_key")
            and account.get("account_id")
        ):
            err_msg = (
                "Could not retrieve API Credentials."
                " Please recheck that API Credentials are configured properly."
            )
            raise ConfigurationError(message=err_msg, reason=err_msg)
        return True

    def get_requests_retry_session(
        self,
        retries=3,
        backoff_factor=60,
        status_forcelist=STATUS_FORCELIST,
        method_whitelist=["GET", "POST", "HEAD"],
    ):
        """
        Create and return a session object with retry mechanism.

        :param retries: Maximum number of retries to attempt
        :param backoff_factor: Backoff factor used to calculate time between retries. e.g. For 10 - 5, 10, 20, 40,...
        :param status_forcelist: A tuple containing the response status codes that should trigger a retry.
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
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    # Decorator
    def handle_common_errors(method):
        """Handle common errors in API response."""

        def wrapper(self, *args, **kwargs):
            err = None
            err_msg = None
            try:
                res = method(self, *args, **kwargs)

                if res is None:
                    raise APIError(
                        "APIError: Did not receive response from API.", response=res
                    )

                if res.status_code == 401:
                    raise InvalidAPICredentialsError(response=res)

                return res

            except requests.exceptions.Timeout as ex:
                err_msg = "TimeoutError: Timeout while requesting data from Safebreach Platform."
                err = ex

            except requests.exceptions.SSLError as ex:
                err_msg = "SSLError: Please verify the SSL certificate for the provided configuration."
                err = ex

            except requests.exceptions.ProxyError as ex:
                err_msg = "ProxyError: Invalid Proxy credentials. Please recheck your Proxy settings."
                err = ex

            except requests.exceptions.ConnectionError as ex:
                err_msg = (
                    "ConnectionError: Error while connecting to Safebreach Platform."
                )
                err = ex

            except requests.exceptions.RequestException as ex:
                err_msg = (
                    "RequestError: Error while fetching data from Safebreach Platform."
                )
                err = ex

            raise APIError(err_msg, err)
        return wrapper

    # Decorator
    def jsonify(method):
        """Convert the response to json objects."""
        def wrapper(self, *args, **kwargs):
            res = method(self, *args, **kwargs)
            return res.json()
        return wrapper

    # Decorator
    def handle_get_errors(method):
        """Handle errors in API response."""

        def wrapper(self, *args, **kwargs):
            res = method(self, *args, **kwargs)

            if res is None:
                raise APIError(
                    "APIError: Did not receive response from API.", response=res
                )
            if res.status_code not in SUCCESSFUL_STATUSCODE:
                raise APIError(
                    reason="URL: {} | Status code: {} | Response: {}".format(
                        res.url, res.status_code, res.text
                    ),
                    response=res,
                )
            return res
        return wrapper

    def build_url(self, endpoint, *objects):
        """Build full url."""
        objects = [urllib.parse.quote_plus(arg, safe="") for arg in objects]

        return "{}/{}/{}".format(
            self.base_url,
            endpoint.strip("/"),
            "/".join(objects),
        ).rstrip("/")

    @jsonify
    @handle_get_errors
    @handle_common_errors
    def get_simulation_data(self, params, header, account_id):
        """Get simulation data from the API."""
        url = self.build_url(ENDPOINTS["simulation"])
        url = "{}/{}/executionsHistoryResults".format(url, account_id)
        return((self.session.get(url, headers=header, params=params, timeout=REQUEST_TIMEOUT)))

    @jsonify
    @handle_get_errors
    @handle_common_errors
    def get_insights_data(self, params, header, account_id):
        """Get insights data from the API."""
        url = self.build_url(ENDPOINTS["simulation"])
        url = "{}/{}/{}".format(url, account_id, ENDPOINTS["insights"])
        return(self.session.post(url, headers=header, data=params, timeout=REQUEST_TIMEOUT))

    @jsonify
    @handle_get_errors
    @handle_common_errors
    def get_remediation_data(self, params, header, account_id, rule_id):
        """Get remediation data from the API."""
        url = self.build_url(ENDPOINTS["simulation"])
        url = "{}/{}/{}/{}/{}".format(url, account_id, ENDPOINTS["insights"], rule_id, ENDPOINTS["remediation"])
        return(self.session.post(url, headers=header, data=params, timeout=REQUEST_TIMEOUT))

    @jsonify
    @handle_get_errors
    @handle_common_errors
    def get_summaries(self, params, header, account_id):
        """Get test summaries data from the API."""
        url = self.build_url(ENDPOINTS["simulation"])
        url = "{}/{}/{}".format(url, account_id, ENDPOINTS["test_summaries"])
        return(self.session.get(url, headers=header, params=params, timeout=REQUEST_TIMEOUT))
    
    @jsonify
    @handle_get_errors
    @handle_common_errors
    def get_audit_log(self, params, header):
        """Get audit log data from the API."""
        url = self.build_url(ENDPOINTS["audit"])
        return((self.session.get(url, headers=header, params=params, timeout=REQUEST_TIMEOUT)))

    @jsonify
    @handle_get_errors
    @handle_common_errors
    def get_mitre_attck_data(self, header):
        """Get audit log data from the API."""
        url = self.build_url(ENDPOINTS["mitre_attck"])
        return((self.session.get(url, headers=header, timeout=REQUEST_TIMEOUT)))

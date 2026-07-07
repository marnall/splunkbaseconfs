import functools
import json
import requests
import time
import common.utility as utility
from common import proxy as SonraiProxy
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

TIMEOUT = 60
RETRIES = 3
BACKOFF_FACTOR = 30
STATUS_FORCELIST = list(range(500, 600)) + [
    429,
]
METHOD_WHILTELIST = ["POST"]


class SonraiTicketClient(object):
    """SonraiTicketClient is a simple wrapper around Requests.

    Session to save authentication and connection data.
    """

    def __init__(self, organization_id, sonrai_host, helper, verify_certs, query_name, logger):
        """Init method for Client class."""
        self.host_url = utility.get_host_url(organization_id, sonrai_host)
        self.query_name = query_name

        self.session = requests.Session()
        self.session = SonraiTicketClient.set_timeout_globally(self.session)
        self.session = SonraiTicketClient.add_retry_mechanism(self.session, RETRIES, BACKOFF_FACTOR)
        try:
            if helper._get_proxy_uri():
                proxy_settings = SonraiProxy.read_proxies_from_conf(helper.context_meta["session_key"])
                self.session.proxies = proxy_settings
                if proxy_settings is not None:
                    logger.info("Proxy is enabled.")
                else:
                    logger.info("Proxy is disabled.")
        except ValueError as ve:
            raise ValueError(ve)
        self.set_header_value(helper, organization_id, logger)
        self.session.verify = verify_certs

    @staticmethod
    def set_timeout_globally(session):
        """Set the timeout globally on each requests sent from session to avoid setting it individually."""
        session.request = functools.partial(session.request, timeout=TIMEOUT)
        return session

    @staticmethod
    def add_retry_mechanism(
        session,
        retries,
        backoff_factor,
        status_forcelist=STATUS_FORCELIST,
        method_whitelist=METHOD_WHILTELIST,
    ):
        """
        Create and return a session object with retry mechanism.

        :param retries: Maximum number of retries to attempt
        :param backoff_factor: Backoff factor used to calculate time between retries. e.g. For 10 - 5, 10, 20, 40,...
        :param status_forcelist: A tuple containing the response status codes that should trigger a retry.
        :param method_whiltelist: HTTP methods on which retry will be performed.

        :return: Session Object
        """
        retry = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            method_whitelist=method_whitelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def post_hook(method):
        """Handle custom post hooks on top of API response."""

        def wrapper(self, *args, jsonify=True, **kwargs):
            res = method(self, *args, **kwargs)
            res.raise_for_status()
            return res

        return wrapper

    def renew_sonrai_account_token(self, helper, sonrai_account, logger):
        """Renew Sonrai account token."""
        try:
            url = self.host_url
            headers = utility.get_headers(sonrai_account["sonrai_token"], "SonraiAPIClient_TokenRenew")
            iat_time, exp_time = utility.sonrai_token_decode(sonrai_account["sonrai_token"])
            token_expiration_in_seconds = exp_time - iat_time
            payload = utility.get_renew_account_payload(token_expiration_in_seconds)
            proxy_settings = self.session.proxies
            response = requests.post(url, data=payload, headers=headers, proxies=proxy_settings, timeout=30)
            response.raise_for_status()
            if response.status_code in (200, 201):
                data = json.loads(response.content)
                session_key = helper.context_meta["session_key"]
                sonrai_token = data.get("data", {}).get("GenerateSonraiUserToken", {}).get("token")
                utility.save_sonrai_credentials(session_key, sonrai_token, sonrai_account["name"])
                logger.info("Successfully renewed Sonrai token for the account {}".format(sonrai_account["name"]))
                return sonrai_token
            else:
                raise Exception("Token not found from the response.")
        except Exception as e:
            msg = "Unable to renew Sonrai token. {}".format(str(e))
            raise Exception(msg)
        return False

    def set_header_value(self, helper, organization_id, logger):
        """Returns header for making validatoin request call."""
        try:
            sonrai_token = False
            iat_time, exp_time = utility.sonrai_token_decode(helper.get_arg("sonrai_account").get("sonrai_token"))
            token_half_cycle = (iat_time + exp_time) / 2
            logger.debug("Current time: {}, Token Half cycle time: {}".format(time.time(), token_half_cycle))
            if time.time() >= token_half_cycle:
                logger.info("Token has exceeded half life time. Renewing Token")
                sonrai_token = self.renew_sonrai_account_token(helper, helper.get_arg("sonrai_account"), logger)
            token = sonrai_token if sonrai_token else helper.get_arg("sonrai_account").get("sonrai_token")
            self.session.headers = utility.get_headers(token, self.query_name)
        except Exception as e:
            self.session.headers = None
            logger.error("Something went wrong while making request header. Error - {}".format(e))

    @post_hook
    def post(self, data):
        """Send POST request to Sonrai API."""
        return self._api_request("post", data)

    def _api_request(self, method, data=None):
        """Handle API requests to Sonrai API."""
        if method == "post":
            data = """{}""".format(data)
            rsp = self.session.post(self.host_url, data=data)
        else:
            raise ValueError("Unsupported HTTP method {}".format(method))
        try:
            rsp.raise_for_status()
        except Exception:
            raise Exception(
                f"Request to Sonrai appliance resulted in an error: {rsp.text} ({rsp.status_code})"
            )

        return rsp

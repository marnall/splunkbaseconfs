import requests
from solnlib import log
from splunktaucclib.rest_handler import error
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from ucc_utils import Util
from appdynamics_utils import normalize_controller_url

logger = log.Logs().get_logger("appdynamics_analytics_validation")

def _validate_credentials(url, opt_url, account_name, client_secret, session_key, query="select count(*) from transactions"):
    if url == "None" or url == "0":
        url = opt_url
    url = normalize_controller_url(url)

    logger.info(f"Validating Analytics Query url: '{url}'")

    proxy = Util.get_proxy(session_key)
    request_timeout = Util.get_timeout(session_key)
    verify_ssl = Util.get_verify_ssl(session_key)

    response = requests.post(
        url=f"{url}/events/query",
        headers={
            'X-Events-API-AccountName': f"{account_name}",
            'X-Events-API-Key': f"{client_secret}",
            'Content-Type': 'application/vnd.appd.events+json;v=2',
            'Accept': 'application/vnd.appd.events+json;v=2'
        },
        json={
            "label": "verify_auth",
            "query": f"{query}",
            "mode": "scroll"
        },
        timeout=request_timeout,
        proxies=proxy,
        verify=verify_ssl
    )
    status = response.status_code
    logger.info(f"{url}/events/query returned status code: {status}, response: {response.text}")
    if status > 300:
        raise error.RestError(status,f"Validation failed, either the url is wrong or invalid API Key or Secret for this controller, please verify your configuration. A response of 'status: {status} - {response.text}' was returned for request POST {url}/events/query query: '{query}'")

class CustomRestHandler(AdminExternalHandler):

    def handleEdit(self, confInfo):
        _validate_credentials(
            self.payload.get("appd_analytics_endpoint"),
            self.payload.get("appd_onprem_analytics_url"),
            self.payload.get("appd_analytics_account_name"),
            self.payload.get("appd_analytics_secret"),
            self.getSessionKey()
        )
        super().handleEdit(confInfo)

    def handleCreate(self, confInfo):
        _validate_credentials(
            self.payload.get("appd_analytics_endpoint"),
            self.payload.get("appd_onprem_analytics_url"),
            self.payload.get("appd_analytics_account_name"),
            self.payload.get("appd_analytics_secret"),
            self.getSessionKey()
        )
        super().handleCreate(confInfo)

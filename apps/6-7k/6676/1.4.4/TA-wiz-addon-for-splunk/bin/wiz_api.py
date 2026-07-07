"""Wiz API client: auth, HTTP session, GraphQL POST, environment URLs."""
import json
from dataclasses import dataclass
from urllib.parse import quote, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from timestamp_utils import is_cluster_mode

WIZ_VERSION = '1.4.4'
INTEGRATION_GUID = "0c061406-def4-4144-cc7b-642f6fedc8b1"
INTEGRATION_NAME = "splunk"

DEFAULT_CONNECT_TIMEOUT_SECONDS = 10
DEFAULT_READ_TIMEOUT_SECONDS = 180
DEFAULT_REQUEST_TIMEOUT = (DEFAULT_CONNECT_TIMEOUT_SECONDS, DEFAULT_READ_TIMEOUT_SECONDS)

MAX_RETRIES_FOR_QUERY = 3
RETRY_TIME_FOR_QUERY = 1


def resolve_request_timeout(helper):
    raw = helper.get_arg('request_timeout')
    if raw is None or str(raw).strip() == '':
        return DEFAULT_REQUEST_TIMEOUT
    try:
        read = int(raw)
    except (ValueError, TypeError):
        return DEFAULT_REQUEST_TIMEOUT
    if read <= 0:
        return DEFAULT_REQUEST_TIMEOUT
    return (DEFAULT_CONNECT_TIMEOUT_SECONDS, read)

AUTH0_URLS = [
    "auth.wiz.io",
    "auth0.gov.wiz.io",
    "auth0.test.wiz.io",
    "auth0.demo.wiz.io",
]
URL = 'https://app.wiz.io'

# 4xx-except-429 fail fast: retrying auth/validation errors wastes budget.
_RETRY_STATUS_FORCELIST = frozenset({429, 500, 502, 503, 504})

_AUTH_HOST_PREFIXES = ("auth.", "auth0.")
_WIZ_ENV_HOSTS = ("wiz.io", "wiz.us")
_WIZ_ENV_SUFFIXES = tuple(f".{host}" for host in _WIZ_ENV_HOSTS)


@dataclass(frozen=True)
class ObjectType:
    """GraphQL response field + Splunk sourcetype identifier per Wiz object."""
    api_field: str        # top-level field in the GraphQL response
    splunk_event: str     # used to build sourcetype = f"wiz:{splunk_event}"


ISSUES     = ObjectType("issues",                "issues")
VULNS      = ObjectType("vulnerabilityFindings", "vulnerabilities")
AUDIT      = ObjectType("auditLogEntries",       "userAuditLogs")
DETECTIONS = ObjectType("detections",            "detections")


def _build_retry():
    return Retry(
        total=MAX_RETRIES_FOR_QUERY - 1,  # extra attempts on top of the first try
        backoff_factor=RETRY_TIME_FOR_QUERY,
        status_forcelist=list(_RETRY_STATUS_FORCELIST),
        allowed_methods=frozenset({'POST'}),
        raise_on_status=False,
    )


def _build_session():
    s = requests.Session()
    adapter = HTTPAdapter(max_retries=_build_retry())
    s.mount('http://', adapter)
    s.mount('https://', adapter)
    return s


# Module-level so connection pools are shared across polls.
_SESSION = _build_session()


def get_integration_user_agent(helper=None):
    name = INTEGRATION_NAME
    if helper is not None and is_cluster_mode(helper):
        name = f"{INTEGRATION_NAME}-cluster"
    return f'{INTEGRATION_GUID}/{name}/{WIZ_VERSION}'


def _build_proxies(helper):
    source_name = helper.get_arg('name')
    proxy_settings = helper.get_proxy()
    if not proxy_settings.get('proxy_url'):
        return {"http": None, "https": None}
    helper.log_debug(f"Source name = {source_name}. Using proxy settings")
    proxy_auth = ""
    if proxy_settings.get("proxy_username"):
        # safe="" so @ : / # % in passwords don't corrupt the URL.
        # `or ""` because Splunk returns absent optional secrets as None, not missing keys.
        proxy_user = quote(proxy_settings.get("proxy_username") or "", safe="")
        proxy_pass = quote(proxy_settings.get("proxy_password") or "", safe="")
        proxy_auth = f"{proxy_user}:{proxy_pass}@"
    proxy_url = (
        f"{proxy_settings['proxy_type']}://{proxy_auth}"
        f"{proxy_settings['proxy_url']}:{proxy_settings['proxy_port']}"
    )
    return {"http": proxy_url, "https": proxy_url}


def extract_wiz_env(url):
    """Strip auth./auth0. prefix from a Wiz token URL host, e.g. auth.wiz.io -> wiz.io.

    Raises ValueError when the host is not a Wiz auth host.
    """
    host = urlparse(url or "").hostname or ""
    for prefix in _AUTH_HOST_PREFIXES:
        if host.startswith(prefix):
            env = host[len(prefix):]
            if env in _WIZ_ENV_HOSTS or env.endswith(_WIZ_ENV_SUFFIXES):
                return env
            break
    raise ValueError(f"Could not extract Wiz environment from the provided URL: {url}")


def get_wiz_url(helper):
    wiz_account = helper.get_arg('wiz_account')
    auth_domain = wiz_account['jwt_generation_url']
    try:
        return f"https://{extract_wiz_env(auth_domain)}"
    except ValueError as e:
        raise Exception(f"Source name = {helper.get_arg('name')}. {e}")


def call_wiz_api(helper, api_endpoint, query, variables, access_token, requests_timeout=DEFAULT_REQUEST_TIMEOUT):
    source_name = helper.get_arg('name')
    try:
        api_endpoint = api_endpoint.replace("http://", "").replace("https://", "")
        proxies = _build_proxies(helper)
        helper.log_debug(f'Source name = {source_name}. Sending a query to Wiz API. Query = {query}, Vars = {variables}')
        result = _SESSION.post(
            f"https://{api_endpoint}",
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + access_token,
                'User-Agent': get_integration_user_agent(helper),
            },
            proxies=proxies,
            json={'query': query, 'variables': variables},
            timeout=requests_timeout,
        )
        if result.status_code != requests.codes.ok:
            raise Exception(f'Wiz API error [{result.status_code}] - {result.text}')

        response_json = result.json()
        helper.log_debug(f'Source name = {source_name}. Result from Wiz API: {response_json}')
        # GraphQL returns 200 + `errors: [...]` for quota/permission/query failures — raise.
        if response_json.get('errors'):
            raise Exception(f'Wiz GraphQL returned errors: {response_json["errors"]}')
        data = response_json.get('data')
        if not data:
            raise Exception(f'Could not get entries from Wiz: {response_json}')
        return data
    except Exception as e:
        helper.log_error(f"Source name = {source_name}. wiz_api.py - call_wiz_api() - Exception encountered {e}")
        raise


def request_wiz_api_token(helper):
    source_name = helper.get_arg('name')
    wiz_account = helper.get_arg('wiz_account')
    # REST handler regex guards this; defense-in-depth for direct .conf edits.
    auth_domain = urlparse(wiz_account['jwt_generation_url']).hostname
    if not auth_domain:
        raise ValueError(f"Invalid jwt_generation_url: {wiz_account['jwt_generation_url']!r}")
    audience = "beyond-api" if auth_domain.lower() in AUTH0_URLS else "wiz-api"
    payload = {
        'grant_type': 'client_credentials',
        'audience': audience,
        'client_id': wiz_account['client_id'],
        'client_secret': wiz_account['client_secret'],
    }

    res = _SESSION.post(
        f"https://{auth_domain}/oauth/token",
        headers={
            "content-type": "application/x-www-form-urlencoded",
            'User-Agent': get_integration_user_agent(helper),
        },
        proxies=_build_proxies(helper),
        data=payload,
        timeout=DEFAULT_REQUEST_TIMEOUT,
    )
    helper.log_debug(f"Source name = {source_name}. Received the result from the request for token generation")
    if res.status_code != requests.codes.ok:
        raise Exception(f"Error Fetching Token from {auth_domain}\n Response Status {res.status_code} : {res.reason}")
    token_res = res.json()
    if "access_token" not in token_res:
        raise Exception(f"Failed requesting API token. Error:\n{json.dumps(token_res)}")
    return token_res["access_token"]

import requests
from typing import Dict, Optional
from urllib.parse import urlencode, urlparse, parse_qsl

from solnlib import conf_manager
from solnlib.modular_input import checkpointer


# ---- Add-on constants ----
ADDON_NAME = "usta_account_takeover_prevention_for_splunk"

CONF_SETTINGS = "usta_account_takeover_prevention_for_splunk_settings"
CONF_ACCOUNT = "usta_account_takeover_prevention_for_splunk_account"
CHECKPOINT_COLLECTION_NAME = "compromised_credentials_checkpoint"

API = {
    "compromised_credentials": "https://usta.prodaft.com/api/threat-stream/v4/security-intelligence/account-takeover-prevention/compromised-credentials-tickets",
}

PAGINATION_SIZE = 100


# ---------- Proxy helpers ----------
def _proxy_uri(proxy: dict) -> Optional[str]:
    if not proxy or not proxy.get("proxy_url") or not proxy.get("proxy_type"):
        return None
    host = proxy["proxy_url"]
    if proxy.get("proxy_port"):
        host = f"{host}:{proxy['proxy_port']}"
    if proxy.get("proxy_username") and proxy.get("proxy_password"):
        return f"{proxy['proxy_type']}://{proxy['proxy_username']}:{proxy['proxy_password']}@{host}/"
    return f"{proxy['proxy_type']}://{host}"


def _get_proxy_config(session_key: str) -> dict:
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{CONF_SETTINGS}",
    )
    return cfm.get_conf(CONF_SETTINGS).get("proxy")


# ---------- HTTP client ----------
def build_http_client(session_key: str, api_key: str) -> requests.Session:
    s = requests.Session()
    proxy = _get_proxy_config(session_key)
    if proxy and str(proxy.get("proxy_enabled", "0")) == "1":
        uri = _proxy_uri(proxy)
        if uri:
            s.proxies = {"http": uri, "https": uri}

    s.headers.update({
        "Accept": "application/json",
        "User-Agent": f"{ADDON_NAME}/1.0.6",
        "Authorization": f"Token {api_key}",
    })
    s.timeout = 30
    return s


# ---------- Account helpers ----------
def get_account_credentials(session_key: str, account_name: str) -> dict:
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{CONF_ACCOUNT}",
    )
    account = cfm.get_conf(CONF_ACCOUNT).get(account_name)
    return {
        "api_key": account.get("api_key"),
    }


# ---------- API helpers ----------
def validate_api_key(http: requests.Session) -> None:
    url = _merge_query(API["compromised_credentials"], {"page_size": "1"})
    resp = http.get(url, timeout=http.timeout)
    if resp.status_code in (401, 403):
        raise Exception("API key invalid or unauthorized.")
    resp.raise_for_status()


def _merge_query(url: str, extra: Dict[str, str]) -> str:
    parts = urlparse(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q.update({k: v for k, v in extra.items() if v is not None})
    return parts._replace(query=urlencode(q)).geturl()


def build_compromised_credentials_url(created_at_after: Optional[str] = None) -> str:
    params = {
        "ordering": "created_at",
        "size": str(PAGINATION_SIZE),
    }
    if created_at_after:
        params["start"] = created_at_after
    return _merge_query(API["compromised_credentials"], params)


# ---------- Checkpoint (KVStore) ----------
def _get_checkpointer(session_key: str) -> checkpointer.KVStoreCheckpointer:
    cp = checkpointer.KVStoreCheckpointer(
        collection_name=CHECKPOINT_COLLECTION_NAME,
        session_key=session_key,
        app=ADDON_NAME,
    )
    if not cp:
        raise Exception("Checkpoint service is not available.")
    return cp


def load_checkpoint(session_key: str, input_name: str) -> Optional[str]:
    cp = _get_checkpointer(session_key)
    doc = cp.get(input_name) or {}
    return doc.get("last_visited")


def save_checkpoint(session_key: str, input_name: str, payload: list) -> None:
    cp = _get_checkpointer(session_key)
    last_item = payload[-1]
    cp.update(input_name, {"last_visited": last_item["created"]})

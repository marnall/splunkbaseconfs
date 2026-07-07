import requests
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode, urlparse, parse_qsl

from solnlib import conf_manager
from solnlib.modular_input import checkpointer


# ---- Add-on constants ----
ADDON_NAME = "cvefeed_for_splunk"

CONF_SETTINGS = "cvefeed_for_splunk_settings"
CONF_ACCOUNT = "cvefeed_for_splunk_account"
CHECKPOINT_COLLECTION = "cvefeed_for_splunk_checkpoint"

PROJECTS_API = "https://cvefeed.io/api/projects"


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
def build_http_client(session_key: str, api_token: str) -> requests.Session:
    s = requests.Session()
    proxy = _get_proxy_config(session_key)
    if proxy and str(proxy.get("proxy_enabled", "0")) == "1":
        uri = _proxy_uri(proxy)
        if uri:
            s.proxies = {"http": uri, "https": uri}

    s.headers.update({
        "Accept": "application/json",
        "User-Agent": f"{ADDON_NAME}/1.0.1",
        "Authorization": f"Bearer {api_token}",
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
        "api_token": account.get("api_token"),
        "project_id": account.get("project_id"),
    }


# ---------- API helpers ----------
def validate_api_token(http: requests.Session, project_id: str) -> str:
    url = f"{PROJECTS_API}/{project_id}/"
    resp = http.get(url, timeout=http.timeout)
    if resp.status_code in (401, 403):
        raise Exception("API token invalid or unauthorized.")
    resp.raise_for_status()
    return resp.json().get("slug", "")


def get_project_slug(http: requests.Session, project_id: str) -> str:
    url = f"{PROJECTS_API}/{project_id}/"
    resp = http.get(url, timeout=http.timeout)
    resp.raise_for_status()
    return resp.json().get("slug", "")


def _merge_query(url: str, extra: Dict[str, str]) -> str:
    parts = urlparse(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q.update({k: v for k, v in extra.items() if v is not None})
    return parts._replace(query=urlencode(q)).geturl()


def build_alerts_url(project_id: str, created_at_after: Optional[str] = None) -> str:
    base = f"{PROJECTS_API}/{project_id}/alerts/?order_by=created_at"
    if created_at_after:
        base = _merge_query(base, {"created_at_after": created_at_after})
    return base


# ---------- Checkpoint (KVStore) ----------
def load_checkpoint(session_key: str, input_name: str) -> Tuple[Optional[str], Optional[int]]:
    cp = checkpointer.KVStoreCheckpointer(
        collection_name=CHECKPOINT_COLLECTION,
        session_key=session_key,
        app=ADDON_NAME,
    )

    if not cp:
        raise Exception("Checkpoint service is not available.")

    doc = cp.get(input_name) or {}

    if not doc:
        return None, None

    return doc.get("created_at"), doc.get("alert_id")


def save_checkpoint(session_key: str, input_name: str, payload: list) -> None:
    cp = checkpointer.KVStoreCheckpointer(
        collection_name=CHECKPOINT_COLLECTION,
        session_key=session_key,
        app=ADDON_NAME,
    )

    if not cp:
        raise Exception("Checkpoint service is not available.")

    last_alert = payload[-1]

    cp.update(
        input_name,
        {
            "created_at": last_alert["created_at"],
            "alert_id": last_alert["id"],
        },
    )

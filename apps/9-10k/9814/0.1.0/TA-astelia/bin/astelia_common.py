import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote

from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer

from astelia_api import AsteliaClient

APP_NAME = "TA-astelia"
REST_ROOT = "ta_astelia"
ACCOUNT_CONF = f"{REST_ROOT}_account"
SETTINGS_CONF = f"{REST_ROOT}_settings"
CHECKPOINT_COLLECTION = f"{REST_ROOT}_checkpoints"
ACCOUNT_CREDENTIAL_REALM = f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{ACCOUNT_CONF}"

TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
RFC3339_FRACTION = re.compile(r"\.(\d+)")


def get_logger(input_name: str, session_key: Optional[str] = None) -> logging.Logger:
    logger = log.Logs().get_logger(f"{REST_ROOT}_{input_name}")
    if session_key:
        level = conf_manager.get_log_level(
            logger=logger,
            session_key=session_key,
            app_name=APP_NAME,
            conf_name=SETTINGS_CONF,
        )
        logger.setLevel(level)
    return logger


def get_account(session_key: str, account_name: str) -> dict[str, Any]:
    manager = conf_manager.ConfManager(session_key, APP_NAME, realm=ACCOUNT_CREDENTIAL_REALM)
    return manager.get_conf(ACCOUNT_CONF).get(account_name)


def get_proxies(session_key: str, logger: logging.Logger) -> Optional[dict[str, str]]:
    settings = conf_manager.get_proxy_dict(
        logger=logger,
        session_key=session_key,
        app_name=APP_NAME,
        conf_name=SETTINGS_CONF,
    )
    return proxies_from_settings(settings)


def proxies_from_settings(settings: Optional[dict[str, Any]]) -> Optional[dict[str, str]]:
    if not settings or str(settings.get("proxy_enabled", "")).lower() not in TRUE_VALUES:
        return None
    host = settings.get("proxy_url")
    if not host:
        return None
    scheme = str(settings.get("proxy_type") or "http").lower()
    if scheme == "socks5" and str(settings.get("proxy_rdns", "")).lower() in TRUE_VALUES:
        scheme = "socks5h"
    username = settings.get("proxy_username")
    password = settings.get("proxy_password")
    credentials = ""
    if username:
        credentials = quote(str(username), safe="")
        if password:
            credentials += ":" + quote(str(password), safe="")
        credentials += "@"
    port = settings.get("proxy_port")
    authority = f"{host}:{port}" if port else str(host)
    proxy_url = f"{scheme}://{credentials}{authority}"
    return {"http": proxy_url, "https": proxy_url}


def get_checkpointer(session_key: str) -> checkpointer.KVStoreCheckpointer:
    return checkpointer.KVStoreCheckpointer(CHECKPOINT_COLLECTION, session_key, APP_NAME)


def build_client(session_key: str, account_name: str, logger: logging.Logger) -> AsteliaClient:
    account = get_account(session_key, account_name)
    return AsteliaClient(
        account["base_url"],
        account["api_key"],
        proxies=get_proxies(session_key, logger),
    )


def parse_rfc3339(value: str) -> float:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    text = RFC3339_FRACTION.sub(lambda match: "." + match.group(1)[:6].ljust(6, "0"), text, count=1)
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def input_name_from_stanza(stanza: str) -> str:
    return stanza.split("://", 1)[-1]

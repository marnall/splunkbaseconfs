"""Credential helper for Whisper Security TA.

Retrieves the Whisper API key and account configuration from Splunk's
storage/passwords endpoint. Credentials are never stored in .conf files,
KV Store, or log output.

When the UCC Framework manages accounts, encrypted fields (like api_key)
are stored in storage/passwords under a realm derived from the app name
and conf file. This module provides a clean interface for other modules
to retrieve credentials without needing to understand UCC internals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import splunklib.client as client

from whisper_api_client import WhisperAPIClient
from whisper_api_errors import WhisperAPIRequestError
from whisper_logging import get_logger

logger = get_logger("credential_helper")

REALM_PREFIX = "__REST_CREDENTIAL__#TA-whisper-graph#configs/conf-ta_whisper_graph_account"
APP_NAME = "TA-whisper-graph"
CONF_NAME = "ta_whisper_graph_account"
DEFAULT_BASE_URL = "https://graph.whisper.security"


def get_api_key(service: client.Service, account_name: str = "default") -> str | None:
    """Retrieve the Whisper API key from Splunk storage/passwords.

    UCC stores encrypted fields in storage/passwords using a realm that
    includes the app name and conf file name. This function searches for
    the matching entry and extracts the api_key value.

    Args:
        service: Authenticated Splunk SDK service connection.
        account_name: Name of the account stanza in the UCC config.

    Returns:
        The API key string, or None if not configured.
    """
    import json

    # List all passwords via REST and filter, avoiding SDK iteration auth issues.
    try:
        response = service.get(
            "/servicesNS/nobody/TA-whisper-graph/storage/passwords",
            output_mode="json",
            count=0,
            search="TA-whisper-graph",
        )
        body = response.body.read()
        data = json.loads(body)
        for entry in data.get("entry", []):
            content = entry.get("content", {})
            realm = content.get("realm", "")
            username = content.get("username", "")
            base_username = username.split("``splunk_cred_sep``")[0] if "``splunk_cred_sep``" in username else username
            if realm == REALM_PREFIX and base_username == account_name:
                clear_password = content.get("clear_password", "")
                if clear_password:
                    try:
                        parsed = json.loads(clear_password)
                        api_key = parsed.get("api_key", "")
                        if api_key:
                            logger.info("action=get_api_key, status=success, account=%s, method=rest", account_name)
                            return api_key
                    except (json.JSONDecodeError, TypeError):
                        return clear_password
    except Exception as exc:
        logger.info("action=get_api_key, method=rest_list, account=%s, error=%s", account_name, exc)

    # Fallback: iterate all passwords via SDK
    try:
        for password in service.storage_passwords:
            content = password.content
            realm = content.get("realm", "")
            username = content.get("username", "")
            base_username = username.split("``splunk_cred_sep``")[0] if "``splunk_cred_sep``" in username else username
            if realm == REALM_PREFIX and base_username == account_name:
                clear_password = content.get("clear_password", "")
                if clear_password:
                    try:
                        data = json.loads(clear_password)
                        api_key = data.get("api_key", "")
                        if api_key:
                            logger.debug("API key retrieved for account %s", account_name)
                            return api_key
                    except (json.JSONDecodeError, TypeError):
                        return clear_password
    except Exception:
        logger.debug("action=get_api_key, status=sdk_fallback_failed, account=%s", account_name)

    logger.warning("action=get_api_key, status=not_found, account=%s", account_name)
    return None


def get_account_config(service: client.Service, account_name: str = "default") -> dict[str, Any]:
    """Retrieve the full account configuration from UCC-managed conf.

    Reads the non-encrypted fields (base_url, name) from the account
    conf stanza. The API key is retrieved separately via get_api_key()
    since it is stored encrypted in storage/passwords.

    Args:
        service: Authenticated Splunk SDK service connection.
        account_name: Name of the account stanza.

    Returns:
        Dictionary with account configuration fields. Returns defaults
        if the account is not found.
    """
    config: dict[str, Any] = {
        "name": account_name,
        "base_url": DEFAULT_BASE_URL,
    }

    try:
        conf = service.confs[CONF_NAME]
        stanza = conf[account_name]
        content = stanza.content
        config["base_url"] = content.get("base_url", DEFAULT_BASE_URL)
        config["name"] = content.get("name", account_name)
    except (KeyError, AttributeError):
        logger.info("action=get_account_config, status=info, account=%s, reason=using_defaults", account_name)

    return config


def validate_api_key(api_key: str, base_url: str = DEFAULT_BASE_URL) -> bool:
    """Validate an API key by calling an authenticated endpoint.

    Uses WhisperAPIClient to call /api/query/stats with the provided
    API key. This endpoint requires authentication, so a successful
    response confirms the key is valid. Using the shared client ensures
    consistent SSL, proxy, timeout, and header handling, and avoids
    AppInspect ``check_for_insecure_http_calls_in_python`` warnings.

    Args:
        api_key: The API key to validate.
        base_url: The Whisper API base URL.

    Returns:
        True if the authenticated request succeeds, False otherwise.
    """

    api_client = WhisperAPIClient(
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        timeout=10,
        max_retries=0,
        rate_limit=0,
    )
    try:
        api_client.stats()
        return True
    except WhisperAPIRequestError as exc:
        error = exc.error
        if error.status_code == 408:
            logger.warning("action=validate_api_key, status=timeout, base_url=%s", base_url)
        elif error.status_code == 0:
            logger.warning("action=validate_api_key, status=connection_error, base_url=%s", base_url)
        else:
            logger.warning("action=validate_api_key, status=error, http_status=%d", error.status_code)
        return False
    except Exception as exc:
        logger.warning("action=validate_api_key, status=error, error=%s", exc)
        return False
    finally:
        api_client.close()

"""Configuration helper for Whisper Security TA.

Reads and validates API connection settings from UCC-managed conf files
and storage/passwords. Provides a unified WhisperConfig dataclass for
use by search commands, modular inputs, and the API client.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import splunklib.client as client

from whisper_api_client import WhisperAPIClient
from whisper_api_errors import WhisperAPIRequestError
from whisper_credential_helper import get_account_config, get_api_key
from whisper_logging import get_logger

logger = get_logger("config")

DEFAULT_BASE_URL = "https://graph.whisper.security"
DEFAULT_TIMEOUT = 120
MIN_TIMEOUT = 5
MAX_TIMEOUT = 300

SETTINGS_CONF_NAME = "ta_whisper_security_settings"
SETTINGS_STANZA = "settings"


@dataclass
class WhisperConfig:
    """Whisper API connection configuration.

    Attributes:
        base_url: API base URL.
        api_key: API key for authentication.
        timeout: Request timeout in seconds.
        proxy_url: Optional HTTP proxy URL.
    """

    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    timeout: int = DEFAULT_TIMEOUT
    proxy_url: str | None = None


def _discover_first_account(service: client.Service) -> str | None:
    """Discover the first available account name from UCC conf.

    Args:
        service: Authenticated Splunk SDK service connection.

    Returns:
        The first account name found, or None.
    """
    account_conf = SETTINGS_CONF_NAME.replace("_settings", "_account")
    try:
        conf = service.confs[account_conf]
        for stanza in conf:
            name = stanza.name
            if name and not name.startswith("_"):
                logger.info("action=discover_account, status=success, account=%s", name)
                return name
    except (KeyError, AttributeError):
        pass
    return None


def get_config(service: client.Service, account_name: str = "default") -> WhisperConfig:
    """Read Whisper configuration from UCC-managed conf and credentials.

    Combines account settings (base_url, api_key from storage/passwords)
    with connection settings (timeout, ssl_verify, proxy_url from the
    settings conf file) into a single WhisperConfig object.

    If the specified account_name is not found, attempts to auto-discover
    the first available account.

    Args:
        service: Authenticated Splunk SDK service connection.
        account_name: Name of the account stanza to use.

    Returns:
        WhisperConfig with current settings or defaults.
    """
    # Try to read API key for the requested account first
    api_key = get_api_key(service, account_name)

    # If not found, auto-discover the first available account
    if not api_key and account_name == "default":
        discovered = _discover_first_account(service)
        if discovered:
            account_name = discovered
            api_key = get_api_key(service, account_name)

    # Read account config (base_url, name)
    account = get_account_config(service, account_name)

    # Finalize API key
    api_key = api_key or ""

    # Read connection settings from settings conf
    timeout = DEFAULT_TIMEOUT
    proxy_url = None

    try:
        conf = service.confs[SETTINGS_CONF_NAME]
        stanza = conf[SETTINGS_STANZA]
        content = stanza.content

        raw_timeout = content.get("timeout", str(DEFAULT_TIMEOUT))
        try:
            timeout = int(raw_timeout)
        except (ValueError, TypeError):
            logger.warning(
                "action=read_config, status=warning, field=timeout, invalid_value=%r, default=%d",
                raw_timeout,
                DEFAULT_TIMEOUT,
            )
            timeout = DEFAULT_TIMEOUT

        proxy_url = content.get("proxy_url") or None
    except (KeyError, AttributeError):
        logger.info("action=read_config, status=info, reason=no_custom_settings")

    return WhisperConfig(
        base_url=account.get("base_url", DEFAULT_BASE_URL),
        api_key=api_key,
        timeout=timeout,
        proxy_url=proxy_url,
    )


def validate_config(config: WhisperConfig) -> list[str]:
    """Validate configuration values.

    Args:
        config: Configuration to validate.

    Returns:
        List of validation error messages. Empty list means valid.
    """
    errors: list[str] = []

    if not config.base_url.startswith("https://"):
        errors.append("base_url must use HTTPS (Splunk Cloud requires encrypted communication)")

    if not MIN_TIMEOUT <= config.timeout <= MAX_TIMEOUT:
        errors.append(f"timeout must be between {MIN_TIMEOUT} and {MAX_TIMEOUT} seconds")

    if config.proxy_url and not config.proxy_url.startswith(("http://", "https://", "socks5://")):
        errors.append("proxy_url must start with http://, https://, or socks5://")

    return errors


def check_connectivity(config: WhisperConfig) -> dict[str, Any]:
    """Test API connectivity and return health and stats data.

    Uses WhisperAPIClient for consistent SSL, proxy, timeout, and header
    handling. This avoids raw ``requests.get`` calls which trigger
    AppInspect ``check_for_insecure_http_calls_in_python`` warnings.

    Args:
        config: Configuration to test.

    Returns:
        Dictionary with health status, node/edge counts, response time,
        and any error information.
    """

    result: dict[str, Any] = {
        "success": False,
        "health_status": None,
        "node_count": None,
        "edge_count": None,
        "virtual_node_count": None,
        "virtual_edge_count": None,
        "total_node_count": None,
        "total_edge_count": None,
        "object_count": None,
        "threat_intel_available": None,
        "feed_source_count": None,
        "asn_enrichment_loaded": None,
        "prefix_bgp_enrichment_loaded": None,
        "response_time_ms": None,
        "error": None,
    }

    base_url = config.base_url.rstrip("/")
    client = WhisperAPIClient(
        base_url=base_url,
        api_key=config.api_key,
        timeout=config.timeout,
        max_retries=0,
        rate_limit=0,
        proxy=config.proxy_url,
    )

    start = time.monotonic()

    try:
        # Health check
        health_data = client.health()
        result["health_status"] = health_data.get("status")

        # Stats check
        stats_data = client.stats()

        physical = stats_data.get("physical", {})
        virtual = stats_data.get("virtual", {})
        total = stats_data.get("total", {})

        result["node_count"] = physical.get("nodeCount", stats_data.get("nodeCount"))
        result["edge_count"] = physical.get("edgeCount", stats_data.get("edgeCount"))
        result["virtual_node_count"] = virtual.get("nodeCount")
        result["virtual_edge_count"] = virtual.get("edgeCount")
        result["total_node_count"] = total.get("nodeCount")
        result["total_edge_count"] = total.get("edgeCount")
        result["object_count"] = stats_data.get("objectCount")
        threat_intel = stats_data.get("threatIntel", {})
        result["threat_intel_available"] = threat_intel.get("available")
        result["feed_source_count"] = threat_intel.get("feedSourceCount")
        result["asn_enrichment_loaded"] = threat_intel.get("asnEnrichmentLoaded")
        result["prefix_bgp_enrichment_loaded"] = threat_intel.get("prefixBgpEnrichmentLoaded")
        result["success"] = True

    except WhisperAPIRequestError as exc:
        error = exc.error
        if error.status_code == 0:
            result["error"] = f"Connection failed to {base_url}"
        elif error.status_code == 408:
            result["error"] = f"Request timed out after {config.timeout}s"
        else:
            result["error"] = f"HTTP {error.status_code}: {error.message[:200]}"
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        client.close()

    elapsed_ms = int((time.monotonic() - start) * 1000)
    result["response_time_ms"] = elapsed_ms

    return result

"""Shared helpers for Whisper Security search commands and modular inputs.

Provides a unified way to initialize the WhisperAPIClient from a Splunk
search command's service context or modular input configuration. Used by
whisperlookup, whisperquery, and attack surface modular inputs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from whisper_api_client import WhisperAPIClient
from whisper_config import get_config, validate_config
from whisper_logging import get_logger

if TYPE_CHECKING:
    import splunklib.client as client

logger = get_logger("command_helpers")


def get_api_client_from_service(
    service: client.Service,
    account_name: str = "default",
) -> WhisperAPIClient:
    """Initialize a WhisperAPIClient from a Splunk service connection.

    Reads configuration from UCC-managed conf files and storage/passwords,
    validates the configuration, and returns a ready-to-use API client.

    Args:
        service: Authenticated Splunk SDK service connection.
        account_name: Name of the account stanza to use.

    Returns:
        Configured WhisperAPIClient instance.

    Raises:
        RuntimeError: If configuration is invalid.
    """
    config = get_config(service, account_name=account_name)
    errors = validate_config(config)
    if errors:
        raise RuntimeError(f"Whisper configuration errors: {', '.join(errors)}")

    if not config.api_key:
        raise RuntimeError("Whisper API key not configured — add credentials via the app setup page")

    return WhisperAPIClient(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout,
        rate_limit=0,
        proxy=config.proxy_url,
    )


def get_api_client_from_inputs(
    input_item: dict[str, Any],
    service: client.Service,
) -> WhisperAPIClient:
    """Initialize a WhisperAPIClient from modular input configuration.

    Uses the account reference from the input stanza to resolve API
    credentials via the Splunk service connection, then builds the client.

    Args:
        input_item: Input stanza configuration dictionary.
        service: Authenticated Splunk SDK service connection.

    Returns:
        Configured WhisperAPIClient instance.

    Raises:
        RuntimeError: If configuration is invalid.
    """
    account_name = input_item.get("account", "default")
    return get_api_client_from_service(service, account_name=account_name)

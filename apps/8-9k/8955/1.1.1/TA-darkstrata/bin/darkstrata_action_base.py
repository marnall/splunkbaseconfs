"""
DarkStrata Adaptive Response Action Base Class

Provides common functionality for all DarkStrata alert actions in Splunk ES.
"""

from __future__ import annotations

import json
import logging
import ssl
import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import requests
from requests.adapters import HTTPAdapter

if TYPE_CHECKING:
    pass

# UCC-generated imports
try:
    import import_declare_test  # noqa: F401
    from solnlib import conf_manager
except ImportError:
    pass


# Constants
API_TIMEOUT = 30
USER_AGENT = "Splunk/TA-DarkStrata/1.1.1 (AdaptiveResponse)"

# Logger setup
logger = logging.getLogger(__name__)


class TLS12Adapter(HTTPAdapter):
    """HTTPS adapter that enforces TLS 1.2 as the minimum protocol version."""

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        super().init_poolmanager(*args, **kwargs)


class DarkStrataActionError(Exception):
    """Custom exception for DarkStrata action errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class DarkStrataActionBase(ABC):
    """Base class for DarkStrata Adaptive Response actions."""

    def __init__(self, session_key: str, logger: logging.Logger | None = None) -> None:
        self.session_key = session_key
        self.logger = logger or logging.getLogger(__name__)
        self._account_cache: dict[str, dict[str, Any]] = {}

    def get_account_config(self, account_name: str) -> dict[str, Any]:
        """Retrieve account configuration from Splunk."""
        if account_name in self._account_cache:
            return self._account_cache[account_name]

        try:
            cfm = conf_manager.ConfManager(
                self.session_key,
                "TA-darkstrata",
                realm="__REST_CREDENTIAL__#TA-darkstrata#configs/conf-ta_darkstrata_account",
            )

            # Get account settings
            account_conf = cfm.get_conf("ta_darkstrata_account")
            account = account_conf.get(account_name, only_current_app=False)

            if not account:
                raise DarkStrataActionError(f"Account '{account_name}' not found")

            config = {
                "api_base_url": account.get("api_base_url", "").rstrip("/"),
                "api_key": account.get("api_key", ""),
            }

            # Get proxy settings
            proxy_conf = cfm.get_conf("ta_darkstrata_settings")
            proxy_settings = proxy_conf.get("proxy", only_current_app=False)

            if proxy_settings and proxy_settings.get("proxy_enabled") == "1":
                config["proxy_settings"] = {
                    "proxy_enabled": True,
                    "proxy_type": proxy_settings.get("proxy_type", "http"),
                    "proxy_url": proxy_settings.get("proxy_url", ""),
                    "proxy_port": proxy_settings.get("proxy_port", ""),
                    "proxy_username": proxy_settings.get("proxy_username", ""),
                    "proxy_password": proxy_settings.get("proxy_password", ""),
                }
            else:
                config["proxy_settings"] = None

            self._account_cache[account_name] = config
            return config

        except Exception as e:
            self.logger.error("Failed to get account config: %s", e)
            raise DarkStrataActionError(f"Failed to get account configuration: {e}") from e

    def make_api_request(
        self,
        account_config: dict[str, Any],
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated API request to DarkStrata."""
        session = requests.Session()
        # Enforce TLS 1.2+ and verify server certificates (requests verifies by
        # default; kept explicit so the secure posture is unambiguous).
        session.mount("https://", TLS12Adapter())
        session.verify = True

        # Set up headers
        session.headers.update(
            {
                "x-api-key": account_config["api_key"],
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            }
        )

        # Configure proxy if provided
        proxy_settings = account_config.get("proxy_settings")
        if proxy_settings and proxy_settings.get("proxy_enabled"):
            proxy_type = proxy_settings.get("proxy_type", "http")
            proxy_host = proxy_settings.get("proxy_url", "")
            proxy_port = proxy_settings.get("proxy_port", "")
            proxy_username = proxy_settings.get("proxy_username", "")
            proxy_password = proxy_settings.get("proxy_password", "")

            if proxy_host and proxy_port:
                if proxy_username and proxy_password:
                    proxy_url = f"{proxy_type}://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
                else:
                    proxy_url = f"{proxy_type}://{proxy_host}:{proxy_port}"

                session.proxies = {"http": proxy_url, "https": proxy_url}

        # Build URL
        url = f"{account_config['api_base_url']}{endpoint}"
        self.logger.info("Making %s request to %s", method, url)

        try:
            if method.upper() == "GET":
                response = session.get(url, timeout=API_TIMEOUT)
            elif method.upper() == "POST":
                response = session.post(url, json=data, timeout=API_TIMEOUT)
            elif method.upper() == "PATCH":
                response = session.patch(url, json=data, timeout=API_TIMEOUT)
            elif method.upper() == "PUT":
                response = session.put(url, json=data, timeout=API_TIMEOUT)
            elif method.upper() == "DELETE":
                response = session.delete(url, timeout=API_TIMEOUT)
            else:
                raise DarkStrataActionError(f"Unsupported HTTP method: {method}")

            if response.status_code == 401:
                raise DarkStrataActionError(
                    "Authentication failed. Check your API key.",
                    status_code=401,
                )
            elif response.status_code == 403:
                raise DarkStrataActionError(
                    "Access denied. API key may lack required permissions.",
                    status_code=403,
                )
            elif response.status_code == 404:
                raise DarkStrataActionError(
                    "Resource not found.",
                    status_code=404,
                )
            elif response.status_code >= 400:
                error_msg = response.text or f"HTTP {response.status_code}"
                raise DarkStrataActionError(
                    f"API error: {error_msg}",
                    status_code=response.status_code,
                )

            return response.json() if response.text else {}

        except requests.exceptions.Timeout as e:
            raise DarkStrataActionError("Request timed out", status_code=None) from e
        except requests.exceptions.RequestException as e:
            raise DarkStrataActionError(f"Request failed: {e}", status_code=None) from e

    @abstractmethod
    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the action. Must be implemented by subclasses."""
        pass

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Parse payload and execute the action."""
        try:
            configuration = payload.get("configuration", {})
            result = self.execute(configuration)

            return {
                "success": True,
                "message": "Action completed successfully",
                "result": result,
            }

        except DarkStrataActionError as e:
            self.logger.error("DarkStrata action error: %s", e)
            return {
                "success": False,
                "message": str(e),
                "status_code": e.status_code,
            }
        except Exception as e:
            self.logger.error("Unexpected error: %s", e)
            return {
                "success": False,
                "message": f"Unexpected error: {e}",
            }


def parse_payload() -> dict[str, Any]:
    """Parse the payload from stdin (Splunk passes JSON payload)."""
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload_str = sys.stdin.read()
        return json.loads(payload_str)
    return {}


def write_result(result: dict[str, Any]) -> None:
    """Write result to stdout for Splunk."""
    print(json.dumps(result))

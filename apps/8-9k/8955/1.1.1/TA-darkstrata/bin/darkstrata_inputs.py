"""
DarkStrata Modular Inputs for Splunk

Ingests threat intelligence from DarkStrata API endpoints:
- /stix/indicators - Compromised credential indicators
- /stix/alerts - Credential exposure alerts

Uses checkpoint-based incremental sync to efficiently fetch only new data.
"""

from __future__ import annotations

import json
import logging
import ssl
import sys
from collections.abc import Generator
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import requests
from requests.adapters import HTTPAdapter
from splunktaucclib.rest_handler.endpoint.validator import Validator

if TYPE_CHECKING:
    pass

# UCC-generated imports - these are created by ucc-gen build
try:
    import import_declare_test  # noqa: F401
    from solnlib import conf_manager
    from solnlib.modular_input import checkpointer
    from splunktaucclib.modinput_wrapper import base_modinput
except ImportError:
    # Allow running tests without full Splunk environment
    pass


# Constants
API_TIMEOUT = 30
DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 500
SOURCETYPE_OBSERVED_DATA = "darkstrata:stix:observed-data"
SOURCETYPE_ALERT = "darkstrata:stix:alert"
USER_AGENT = "Splunk/TA-DarkStrata/1.1.1"


class TLS12Adapter(HTTPAdapter):
    """HTTPS adapter that enforces TLS 1.2 as the minimum protocol version."""

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        super().init_poolmanager(*args, **kwargs)


class DarkStrataAPIClient:
    """Client for interacting with DarkStrata STIX API endpoints."""

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        proxy_settings: dict[str, Any] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.logger = logger or logging.getLogger(__name__)

        # Configure session with TLS 1.2 minimum
        self.session = requests.Session()
        self.session.mount("https://", TLS12Adapter())
        self.session.headers.update(
            {
                "x-api-key": api_key,
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            }
        )

        # Configure proxy if provided
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
                self.session.proxies = {
                    "http": proxy_url,
                    "https": proxy_url,
                }
                self.logger.info("Proxy configured: %s:%s", proxy_host, proxy_port)

    def _make_request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request to the DarkStrata API."""
        url = f"{self.api_base_url}{endpoint}"
        self.logger.debug("Making request to %s", url)

        try:
            response = self.session.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error("Request error: %s", e)
            raise

    def _get_response_headers(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Make a request and return both body and headers for pagination."""
        url = f"{self.api_base_url}{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            return response.json(), dict(response.headers)
        except requests.exceptions.RequestException as e:
            self.logger.error("Request error: %s", e)
            raise

    def fetch_indicators(
        self,
        since: str | None = None,
        confidence_threshold: int = 0,
        hash_emails: bool = False,
        page: int = 1,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Fetch indicators from the /stix/indicators endpoint.

        Yields individual observed-data objects from the STIX bundle.
        Uses pagination to handle large datasets.
        """
        params: dict[str, Any] = {
            "format": "splunk",
            "page": page,
            "limit": min(limit, MAX_PAGE_LIMIT),
        }

        if since:
            params["since"] = since
        if confidence_threshold > 0:
            params["confidence_threshold"] = confidence_threshold
        if hash_emails:
            params["hash_emails"] = "true"

        while True:
            self.logger.info(
                "Fetching indicators page %d (limit=%d, since=%s)",
                params["page"],
                params["limit"],
                since,
            )

            data, headers = self._get_response_headers("/stix/indicators", params)

            # Process STIX bundle - yield each observed-data object
            if "objects" in data:
                for obj in data["objects"]:
                    if obj.get("type") == "observed-data":
                        yield obj

            # Check pagination headers
            total_pages = int(headers.get("X-Total-Pages", 1))
            current_page = int(headers.get("X-Page", params["page"]))

            self.logger.info("Processed page %d of %d", current_page, total_pages)

            if current_page >= total_pages:
                break

            params["page"] = current_page + 1

    def fetch_alerts(
        self,
        since: str | None = None,
        detail: str = "full",
        include_identities: bool = True,
        confidence_threshold: int = 0,
        hash_emails: bool = False,
        page: int = 1,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Fetch alerts from the /stix/alerts endpoint.

        Yields individual STIX bundles (one per alert).
        Uses pagination to handle large datasets.
        """
        params: dict[str, Any] = {
            "format": "splunk",
            "detail": detail,
            "page": page,
            "limit": min(limit, DEFAULT_PAGE_LIMIT),
        }

        if since:
            params["since"] = since
        if include_identities:
            params["include"] = "identities"
        if confidence_threshold > 0:
            params["confidence_threshold"] = confidence_threshold
        if hash_emails:
            params["hash_emails"] = "true"

        while True:
            self.logger.info(
                "Fetching alerts page %d (limit=%d, since=%s)",
                params["page"],
                params["limit"],
                since,
            )

            data, headers = self._get_response_headers("/stix/alerts", params)

            # Response is an array of STIX bundles
            if isinstance(data, list):
                yield from data
            else:
                # Single bundle response
                yield data

            # Check pagination headers
            total_pages = int(headers.get("X-Total-Pages", 1))
            current_page = int(headers.get("X-Page", params["page"]))

            self.logger.info("Processed page %d of %d", current_page, total_pages)

            if current_page >= total_pages:
                break

            params["page"] = current_page + 1


class DarkStrataIndicatorsInput(base_modinput.BaseModInput):
    """Modular input for DarkStrata indicators."""

    app = "TA-darkstrata"
    name = "darkstrata_indicators"
    title = "DarkStrata Indicators"
    description = "Collect compromised credential indicators from DarkStrata"
    use_external_validation = True
    use_single_instance = False

    def extra_arguments(self) -> list[dict[str, Any]]:
        """Define additional input arguments."""
        return [
            {
                "name": "account",
                "title": "Account",
                "description": "DarkStrata account to use",
                "required_on_create": True,
            },
            {
                "name": "confidence_threshold",
                "title": "Confidence Threshold",
                "description": "Minimum STIX confidence score (0-100)",
                "required_on_create": False,
            },
            {
                "name": "hash_emails",
                "title": "Hash Emails",
                "description": "Hash email addresses for privacy",
                "required_on_create": False,
            },
        ]

    def get_account_fields(self) -> list[str]:
        """Return list of account field names."""
        return ["api_base_url", "api_key"]

    def get_scheme(self) -> None:
        """Return the scheme for the modular input."""
        pass

    def get_app_name(self) -> str:
        """Return the app name."""
        return self.app

    def get_session_key(self) -> str:
        """Return the session key from the input."""
        return self._input_definition.metadata.get("session_key", "")

    def collect_events(self, ew: Any) -> None:
        """Collect events from DarkStrata API."""
        input_name = list(self._input_definition.inputs.keys())[0]
        input_item = self._input_definition.inputs[input_name]

        # Get configuration
        account_name = input_item.get("account")
        confidence_threshold = int(input_item.get("confidence_threshold", 0))
        hash_emails = input_item.get("hash_emails", "0") in ("1", "true", True)
        index = input_item.get("index", "default")

        self.logger.info("Starting indicators collection for account: %s", account_name)

        # Get account credentials
        account_config = self._get_account_config(account_name)
        if not account_config:
            self.logger.error("Account configuration not found: %s", account_name)
            return

        api_base_url = account_config.get("api_base_url")
        api_key = account_config.get("api_key")

        if not api_base_url or not api_key:
            self.logger.error("Missing API configuration for account: %s", account_name)
            return

        # Get proxy settings
        proxy_settings = self._get_proxy_settings()

        # Initialise API client
        client = DarkStrataAPIClient(
            api_base_url=api_base_url,
            api_key=api_key,
            proxy_settings=proxy_settings,
            logger=self.logger,
        )

        # Get checkpoint for incremental sync
        checkpoint_key = f"darkstrata_indicators_{input_name}"
        checkpoint = self._get_checkpoint(checkpoint_key)
        since = checkpoint.get("last_sync") if checkpoint else None

        self.logger.info("Starting sync from checkpoint: %s", since)

        # Fetch and write events
        event_count = 0
        latest_timestamp = since

        try:
            for observed_data in client.fetch_indicators(
                since=since,
                confidence_threshold=confidence_threshold,
                hash_emails=hash_emails,
            ):
                # Create Splunk event
                event_time = self._parse_timestamp(observed_data.get("modified") or observed_data.get("created"))

                event = self._create_event(
                    data=json.dumps(observed_data),
                    time=event_time,
                    index=index,
                    sourcetype=SOURCETYPE_OBSERVED_DATA,
                )
                ew.write_event(event)
                event_count += 1

                # Track latest timestamp for checkpoint
                obj_time = observed_data.get("modified") or observed_data.get("created")
                if obj_time and (not latest_timestamp or obj_time > latest_timestamp):
                    latest_timestamp = obj_time

        except Exception as e:
            self.logger.error("Error collecting indicators: %s", e)
            raise

        # Update checkpoint
        if latest_timestamp:
            self._save_checkpoint(
                checkpoint_key,
                {
                    "last_sync": latest_timestamp,
                    "last_run": datetime.now(timezone.utc).isoformat(),
                    "event_count": event_count,
                },
            )

        self.logger.info("Collected %d indicator events", event_count)

    def _get_account_config(self, account_name: str) -> dict[str, Any] | None:
        """Get account configuration from Splunk."""
        try:
            cfm = conf_manager.ConfManager(
                self.get_session_key(),
                self.app,
                realm=f"__REST_CREDENTIAL__#{self.app}#configs/conf-ta_darkstrata_account",
            )
            account_conf = cfm.get_conf("ta_darkstrata_account")
            return account_conf.get(account_name, {})
        except Exception as e:
            self.logger.error("Failed to get account config: %s", e)
            return None

    def _get_proxy_settings(self) -> dict[str, Any] | None:
        """Get proxy settings from Splunk."""
        try:
            cfm = conf_manager.ConfManager(
                self.get_session_key(),
                self.app,
            )
            settings_conf = cfm.get_conf("ta_darkstrata_settings")
            return settings_conf.get("proxy", {})
        except Exception as e:
            self.logger.debug("No proxy settings found: %s", e)
            return None

    def _get_checkpoint(self, key: str) -> dict[str, Any] | None:
        """Get checkpoint data."""
        try:
            ckpt = checkpointer.KVStoreCheckpointer(
                collection_name="ta_darkstrata_checkpoints",
                session_key=self.get_session_key(),
                app=self.app,
            )
            return ckpt.get(key)
        except Exception as e:
            self.logger.debug("Checkpoint not found for %s: %s", key, e)
            return None

    def _save_checkpoint(self, key: str, data: dict[str, Any]) -> None:
        """Save checkpoint data."""
        try:
            ckpt = checkpointer.KVStoreCheckpointer(
                collection_name="ta_darkstrata_checkpoints",
                session_key=self.get_session_key(),
                app=self.app,
            )
            ckpt.update(key, data)
            self.logger.debug("Checkpoint saved: %s", key)
        except Exception as e:
            self.logger.error("Failed to save checkpoint: %s", e)

    def _parse_timestamp(self, timestamp_str: str | None) -> float | None:
        """Parse ISO 8601 timestamp to epoch."""
        if not timestamp_str:
            return None
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return dt.timestamp()
        except ValueError:
            return None

    def _create_event(
        self,
        data: str,
        time: float | None,
        index: str,
        sourcetype: str,
    ) -> Any:
        """Create a Splunk event."""
        from splunklib.modularinput import Event

        event = Event()
        event.data = data
        event.time = time
        event.index = index
        event.sourcetype = sourcetype
        return event


class DarkStrataAlertsInput(base_modinput.BaseModInput):
    """Modular input for DarkStrata alerts."""

    app = "TA-darkstrata"
    name = "darkstrata_alerts"
    title = "DarkStrata Alerts"
    description = "Collect credential exposure alerts from DarkStrata"
    use_external_validation = True
    use_single_instance = False

    def extra_arguments(self) -> list[dict[str, Any]]:
        """Define additional input arguments."""
        return [
            {
                "name": "account",
                "title": "Account",
                "description": "DarkStrata account to use",
                "required_on_create": True,
            },
            {
                "name": "detail",
                "title": "Detail Level",
                "description": "Level of detail in alert reports",
                "required_on_create": False,
            },
            {
                "name": "include_identities",
                "title": "Include Identities",
                "description": "Include STIX Identity objects",
                "required_on_create": False,
            },
            {
                "name": "confidence_threshold",
                "title": "Confidence Threshold",
                "description": "Minimum STIX confidence score (0-100)",
                "required_on_create": False,
            },
            {
                "name": "hash_emails",
                "title": "Hash Emails",
                "description": "Hash email addresses for privacy",
                "required_on_create": False,
            },
        ]

    def get_account_fields(self) -> list[str]:
        """Return list of account field names."""
        return ["api_base_url", "api_key"]

    def get_scheme(self) -> None:
        """Return the scheme for the modular input."""
        pass

    def get_app_name(self) -> str:
        """Return the app name."""
        return self.app

    def get_session_key(self) -> str:
        """Return the session key from the input."""
        return self._input_definition.metadata.get("session_key", "")

    def collect_events(self, ew: Any) -> None:
        """Collect events from DarkStrata API."""
        input_name = list(self._input_definition.inputs.keys())[0]
        input_item = self._input_definition.inputs[input_name]

        # Get configuration
        account_name = input_item.get("account")
        detail = input_item.get("detail", "full")
        include_identities = input_item.get("include_identities", "1") in (
            "1",
            "true",
            True,
        )
        confidence_threshold = int(input_item.get("confidence_threshold", 0))
        hash_emails = input_item.get("hash_emails", "0") in ("1", "true", True)
        index = input_item.get("index", "default")

        self.logger.info("Starting alerts collection for account: %s", account_name)

        # Get account credentials
        account_config = self._get_account_config(account_name)
        if not account_config:
            self.logger.error("Account configuration not found: %s", account_name)
            return

        api_base_url = account_config.get("api_base_url")
        api_key = account_config.get("api_key")

        if not api_base_url or not api_key:
            self.logger.error("Missing API configuration for account: %s", account_name)
            return

        # Get proxy settings
        proxy_settings = self._get_proxy_settings()

        # Initialise API client
        client = DarkStrataAPIClient(
            api_base_url=api_base_url,
            api_key=api_key,
            proxy_settings=proxy_settings,
            logger=self.logger,
        )

        # Get checkpoint for incremental sync
        checkpoint_key = f"darkstrata_alerts_{input_name}"
        checkpoint = self._get_checkpoint(checkpoint_key)
        since = checkpoint.get("last_sync") if checkpoint else None

        self.logger.info("Starting sync from checkpoint: %s", since)

        # Fetch and write events
        event_count = 0
        latest_timestamp = since

        try:
            for bundle in client.fetch_alerts(
                since=since,
                detail=detail,
                include_identities=include_identities,
                confidence_threshold=confidence_threshold,
                hash_emails=hash_emails,
            ):
                # Find the report object to get timestamp
                report_obj = None
                for obj in bundle.get("objects", []):
                    if obj.get("type") == "report":
                        report_obj = obj
                        break

                event_time = None
                if report_obj:
                    event_time = self._parse_timestamp(report_obj.get("published"))

                # Write the entire bundle as a single event
                event = self._create_event(
                    data=json.dumps(bundle),
                    time=event_time,
                    index=index,
                    sourcetype=SOURCETYPE_ALERT,
                )
                ew.write_event(event)
                event_count += 1

                # Also write individual observed-data objects for searching
                for obj in bundle.get("objects", []):
                    if obj.get("type") == "observed-data":
                        obj_time = self._parse_timestamp(obj.get("modified") or obj.get("created"))
                        event = self._create_event(
                            data=json.dumps(obj),
                            time=obj_time,
                            index=index,
                            sourcetype=SOURCETYPE_OBSERVED_DATA,
                        )
                        ew.write_event(event)

                        # Track latest timestamp
                        ts = obj.get("modified") or obj.get("created")
                        if ts and (not latest_timestamp or ts > latest_timestamp):
                            latest_timestamp = ts

        except Exception as e:
            self.logger.error("Error collecting alerts: %s", e)
            raise

        # Update checkpoint
        if latest_timestamp:
            self._save_checkpoint(
                checkpoint_key,
                {
                    "last_sync": latest_timestamp,
                    "last_run": datetime.now(timezone.utc).isoformat(),
                    "event_count": event_count,
                },
            )

        self.logger.info("Collected %d alert bundles", event_count)

    def _get_account_config(self, account_name: str) -> dict[str, Any] | None:
        """Get account configuration from Splunk."""
        try:
            cfm = conf_manager.ConfManager(
                self.get_session_key(),
                self.app,
                realm=f"__REST_CREDENTIAL__#{self.app}#configs/conf-ta_darkstrata_account",
            )
            account_conf = cfm.get_conf("ta_darkstrata_account")
            return account_conf.get(account_name, {})
        except Exception as e:
            self.logger.error("Failed to get account config: %s", e)
            return None

    def _get_proxy_settings(self) -> dict[str, Any] | None:
        """Get proxy settings from Splunk."""
        try:
            cfm = conf_manager.ConfManager(
                self.get_session_key(),
                self.app,
            )
            settings_conf = cfm.get_conf("ta_darkstrata_settings")
            return settings_conf.get("proxy", {})
        except Exception as e:
            self.logger.debug("No proxy settings found: %s", e)
            return None

    def _get_checkpoint(self, key: str) -> dict[str, Any] | None:
        """Get checkpoint data."""
        try:
            ckpt = checkpointer.KVStoreCheckpointer(
                collection_name="ta_darkstrata_checkpoints",
                session_key=self.get_session_key(),
                app=self.app,
            )
            return ckpt.get(key)
        except Exception as e:
            self.logger.debug("Checkpoint not found for %s: %s", key, e)
            return None

    def _save_checkpoint(self, key: str, data: dict[str, Any]) -> None:
        """Save checkpoint data."""
        try:
            ckpt = checkpointer.KVStoreCheckpointer(
                collection_name="ta_darkstrata_checkpoints",
                session_key=self.get_session_key(),
                app=self.app,
            )
            ckpt.update(key, data)
            self.logger.debug("Checkpoint saved: %s", key)
        except Exception as e:
            self.logger.error("Failed to save checkpoint: %s", e)

    def _parse_timestamp(self, timestamp_str: str | None) -> float | None:
        """Parse ISO 8601 timestamp to epoch."""
        if not timestamp_str:
            return None
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return dt.timestamp()
        except ValueError:
            return None

    def _create_event(
        self,
        data: str,
        time: float | None,
        index: str,
        sourcetype: str,
    ) -> Any:
        """Create a Splunk event."""
        from splunklib.modularinput import Event

        event = Event()
        event.data = data
        event.time = time
        event.index = index
        event.sourcetype = sourcetype
        return event


# Validator for API key testing
class DarkStrataAPIValidator(Validator):
    """Validate DarkStrata API credentials."""

    def validate(self, value: str, data: dict[str, Any]) -> bool:
        """Test API connection with provided credentials."""
        api_base_url = data.get("api_base_url", "")
        api_key = data.get("api_key", "")

        if not api_base_url or not api_key:
            self.put_msg("API Base URL and API Key are required")
            return False

        try:
            client = DarkStrataAPIClient(
                api_base_url=api_base_url,
                api_key=api_key,
            )
            # Make a simple test request
            client._make_request("/stix/indicators", {"limit": 1, "format": "splunk"})
            return True
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                self.put_msg("Invalid API key")
            elif e.response is not None and e.response.status_code == 403:
                self.put_msg("API key does not have required permissions (siem:read)")
            else:
                self.put_msg(f"API error: {e}")
            return False
        except Exception as e:
            self.put_msg(f"Connection error: {e}")
            return False


if __name__ == "__main__":
    # Determine which input to run based on script name
    import os

    script_name = os.path.basename(sys.argv[0])

    if "alerts" in script_name:
        exit_code = DarkStrataAlertsInput().run(sys.argv)
    else:
        exit_code = DarkStrataIndicatorsInput().run(sys.argv)

    sys.exit(exit_code)

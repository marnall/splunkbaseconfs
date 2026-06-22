import logging
import sys
import time
from datetime import datetime
from time import sleep
from typing import Any, Dict, Optional, cast

import requests
from requests.exceptions import RequestException
from zoneinfo import ZoneInfo

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

class MethodAuditClient:
    """
    Handles interfacing with the Method Security audit API: token acquisition,
    paging, retries, etc.
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        timezone: str = "UTC",
        token_ttl_margin: float = 30.0,
        max_retries: int = 3,
        backoff_delay_base: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timezone = timezone
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0
        self.token_ttl_margin = token_ttl_margin
        self.max_retries = max_retries
        self.backoff_delay_base = backoff_delay_base

    def _normalize_datetime(self, dt_str: str) -> str:
        """
        Normalize datetime string to ISO 8601 format in UTC: YYYY-MM-DDTHH:MM:SSZ

        Handles various input formats:
        - "YYYY-MM-DD HH:MM:SS" (Splunk config format, interpreted in configured timezone)
        - "YYYY-MM-DDTHH:MM:SS.ffffffZ" (ISO with microseconds, already UTC)
        - "YYYY-MM-DDTHH:MM:SSZ" (already correct UTC)
        """
        # Try to parse with various formats
        formats_naive = [
            "%Y-%m-%d %H:%M:%S",           # Splunk config format (no TZ info)
            "%Y-%m-%dT%H:%M:%S",           # ISO without Z (no TZ info)
        ]

        formats_utc = [
            "%Y-%m-%dT%H:%M:%S.%fZ",       # ISO with microseconds and Z
            "%Y-%m-%dT%H:%M:%SZ",          # ISO without microseconds and Z
        ]

        # Try formats that already indicate UTC
        for fmt in formats_utc:
            try:
                dt = datetime.strptime(dt_str, fmt)
                # Already UTC, just ensure no microseconds
                dt_utc = dt.replace(tzinfo=ZoneInfo("UTC"), microsecond=0)
                return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue

        # Try formats without timezone info - interpret in configured timezone
        for fmt in formats_naive:
            try:
                dt_naive = datetime.strptime(dt_str, fmt)
                # Treat as being in the configured timezone
                dt_local = dt_naive.replace(tzinfo=ZoneInfo(self.timezone))
                # Convert to UTC
                dt_utc = dt_local.astimezone(ZoneInfo("UTC"))
                return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue
            except Exception as e:
                logger.warning(f"Timezone conversion error for '{dt_str}' with timezone '{self.timezone}': {e}")
                continue

        # If no format matches, return as-is and let the API reject it
        logger.warning(f"Could not parse datetime string: {dt_str}, passing as-is")
        return dt_str


    def _backoff_delay_for(self, attempt: int) -> float:
        """
        Calculate the backoff delay for the given attempt.
        """
        return float(self.backoff_delay_base * 2 ** attempt)

    def _fetch_token(self) -> None:
        """
        Fetch a fresh OAuth token and record expiry.
        Adjust this method based on how your auth works.
        """
        for attempt in range(self.max_retries):
          try:
            token_url = f"{self.base_url}/method-api-gateway/api/auth/getToken"
            logger.debug(f"Attempting to fetch token from {token_url}")
            resp = requests.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10,
            )
            logger.debug(f"Token response status: {resp.status_code}")
            resp.raise_for_status()

            # Check if response is JSON before parsing
            content_type = resp.headers.get('content-type', '')
            if 'application/json' not in content_type:
                response_preview = resp.text[:200] if resp.text else "(empty)"
                raise RuntimeError(
                    f"Expected JSON response but got content-type '{content_type}'. "
                    f"Response preview: {response_preview}"
                )

            data = resp.json()
            access_token = data.get("access_token")
            expires_in = data.get("expires_in", 0)
            if not access_token:
                raise RuntimeError("OAuth token response missing access_token")
            self._access_token = access_token
            # Compute expiry (current time + expires_in) minus margin
            self._token_expiry = time.time() + expires_in - self.token_ttl_margin
            logger.debug("Successfully fetched OAuth token")
            return
          except RequestException as e:
            logger.warning(f"Token fetch attempt {attempt + 1}/{self.max_retries} failed: {e}")
            if attempt < self.max_retries - 1:
                sleep(self._backoff_delay_for(attempt))
                continue
            else:
                raise


    def _ensure_token(self) -> str:
        """
        Return a valid token, refreshing it if necessary.
        """
        if self._access_token is None or time.time() >= self._token_expiry:
            logger.debug("Fetching new OAuth token")
            self._fetch_token()
        if self._access_token is None:
            raise RuntimeError("Failed to fetch OAuth token")
        return self._access_token

    def validate_credentials(self) -> None:
        """
        Validate credentials by attempting to fetch an OAuth token.
        Raises an exception if credentials are invalid or the endpoint is unreachable.
        """
        try:
            self._fetch_token()
        except RequestException as e:
            raise ValueError(f"Failed to authenticate with the Method Security API: {e}") from e
        except RuntimeError as e:
            raise ValueError(f"Invalid authentication response: {e}") from e

    def fetch_audit_events(
        self,
        start_time: str,
        end_time: Optional[str] = None,
        paging_token: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Fetch a single page of audit events. Returns a dict with keys:
        - "auditEvents": list of events
        - "pagingToken": optional token for next page
        """
        token = self._ensure_token()

        # Normalize datetime to API expected format (ISO 8601 without microseconds)
        normalized_start_time = self._normalize_datetime(start_time)

        body: Dict[str, Any] = {"startTime": normalized_start_time}

        # Add end_time if provided
        if end_time is not None:
            normalized_end_time = self._normalize_datetime(end_time)
            body["endTime"] = normalized_end_time

        if paging_token is not None:
            body["token"] = paging_token
        if page_size is not None:
            body["pageSize"] = page_size

        url = f"{self.base_url}/method-api-gateway/api/v1/audit/getAuditEvents"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())

    def stream_events(
        self,
        start_time: str,
        end_time: Optional[str] = None,
        page_size: int = 1000,
    ):
        """
        A generator that yields all events from `start_time` to `end_time`,
        handling paging automatically.
        """
        paging_token = None
        attempt = 0
        while True:
            try:
              resp = self.fetch_audit_events(
                  start_time,
                  end_time=end_time,
                  paging_token=paging_token,
                  page_size=page_size
              )
              events = resp.get("auditEvents", [])
              next_token = resp.get("pagingToken")
              yield from events
              if not next_token:
                  break
              paging_token = next_token
              attempt = 0
            except RequestException as e:
              if attempt < self.max_retries - 1:
                  sleep(self._backoff_delay_for(attempt))
                  attempt += 1
                  continue
              else:
                  logger.error("Failed to fetch audit events after %d attempts", self.max_retries)
                  raise e

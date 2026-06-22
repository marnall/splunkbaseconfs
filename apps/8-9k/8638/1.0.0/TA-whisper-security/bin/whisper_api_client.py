"""Shared API client for the Whisper Security Knowledge Graph.

Provides a resilient HTTP client with exponential backoff, rate limiting,
connection pooling, and structured error handling. Used by all search
commands and modular inputs in the TA.

Error types are defined in whisper_api_errors.py and retry/backoff logic
is in whisper_api_retry.py.
"""

from __future__ import annotations

import time
from typing import Any

import requests
from whisper_api_errors import WhisperAPIError, WhisperAPIRequestError
from whisper_api_retry import calculate_backoff, parse_error
from whisper_logging import get_logger

logger = get_logger("api_client")

# Version -- kept in sync with pyproject.toml and app.conf
__version__ = "1.0.0"

# API endpoints
QUERY_ENDPOINT = "/api/query"
STATS_ENDPOINT = "/api/query/stats"
HEALTH_ENDPOINT = "/actuator/health"
THREAT_INTEL_STATUS_ENDPOINT = "/api/graph/threat-intel/status"

# Retry defaults
DEFAULT_MAX_RETRIES = 3

# Rate limiting defaults
DEFAULT_RATE_LIMIT = 10  # requests per second

# Timeout defaults
DEFAULT_CONNECT_TIMEOUT = 5
DEFAULT_READ_TIMEOUT = 30


def get_user_agent() -> str:
    """Return the User-Agent string for all Whisper API requests.

    Returns:
        User-Agent header value in the format ``whisper-splunk/<version>``.
    """
    return f"whisper-splunk/{__version__}"


class WhisperAPIClient:
    """Client for the Whisper Security Knowledge Graph API.

    Provides methods for querying the graph, health checks, and
    statistics retrieval. Includes exponential backoff with jitter,
    rate limiting, and connection pooling.

    Supports the context manager protocol for automatic resource cleanup::

        with WhisperAPIClient(base_url=url, api_key=key) as client:
            result = client.query("MATCH (n:IPV4 {name: $ip}) RETURN n", {"ip": "8.8.8.8"})
        # client.close() called automatically

    Args:
        base_url: API base URL (must use HTTPS).
        api_key: API key for authentication.
        timeout: Read timeout in seconds (also accepts tuple of (connect, read)).
        max_retries: Maximum retry attempts for retryable errors.
        rate_limit: Maximum requests per second (0 = unlimited).
        proxy: HTTP proxy URL or None.

    Example:
        client = WhisperAPIClient(
            base_url="https://graph.whisper.security",
            api_key="your-key",
        )
        result = client.query("MATCH (n:IPV4 {name: $ip}) RETURN n", {"ip": "8.8.8.8"})
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int | tuple[int, int] = DEFAULT_READ_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        rate_limit: int = DEFAULT_RATE_LIMIT,
        proxy: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._max_retries = max_retries
        self._rate_limit = rate_limit
        self._last_request_time = 0.0

        # Parse timeout
        if isinstance(timeout, tuple):
            self._timeout = timeout
        else:
            self._timeout = (DEFAULT_CONNECT_TIMEOUT, timeout)

        # Set up session with connection pooling
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "User-Agent": get_user_agent(),
            }
        )
        # SSL/TLS always enforced — no option to disable
        self._session.verify = True
        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}

        logger.debug(
            "WhisperAPIClient initialized: base_url=%s, timeout=%s, rate_limit=%d/s",
            self._base_url,
            self._timeout,
            self._rate_limit,
        )

    def query(self, cypher: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a Cypher query against the Knowledge Graph.

        Args:
            cypher: The Cypher query string.
            parameters: Optional query parameters (parameterized queries).

        Returns:
            Response dict with 'columns', 'rows', and 'statistics' keys.

        Raises:
            WhisperAPIRequestError: If the query fails after retries.
        """
        payload: dict[str, Any] = {"query": cypher}
        if parameters:
            payload["parameters"] = parameters
        return self._request("POST", QUERY_ENDPOINT, json=payload)

    def health(self) -> dict[str, Any]:
        """Check API health status.

        Returns:
            Health response dict with 'status' key.

        Raises:
            WhisperAPIRequestError: If the health check fails.
        """
        return self._request("GET", HEALTH_ENDPOINT)

    def stats(self) -> dict[str, Any]:
        """Get Knowledge Graph statistics.

        Returns:
            Stats response dict with physical/virtual/total sub-objects,
            each containing nodeCount and edgeCount. Also includes
            objectCount, threatIntel, and timestamp.

        Raises:
            WhisperAPIRequestError: If the stats request fails.
        """
        return self._request("GET", STATS_ENDPOINT)

    def quota(self) -> dict[str, Any]:
        """Get API quota and usage information via CALL whisper.quota().

        The procedure returns rows of ``{key: ..., value: ...}`` pairs.
        This method flattens them into a single dictionary.

        Returns:
            Quota response dict with plan, daily/hourly limits and usage,
            timeout/response limits, and concurrent query info.

        Raises:
            WhisperAPIRequestError: If the request fails.
        """
        response = self.query("CALL whisper.quota()")
        rows = response.get("rows", [])
        # Rows are key-value pair dicts: [{"key": "plan", "value": "Professional"}, ...]
        result: dict[str, Any] = {}
        for row in rows:
            if isinstance(row, dict) and "key" in row and "value" in row:
                result[row["key"]] = row["value"]
        # Preserve timing metadata (#405)
        if "_timing" in response:
            result["_timing"] = response["_timing"]
        return result

    def threat_intel_status(self) -> dict[str, Any]:
        """Get threat intelligence layer status.

        Returns:
            Dict with threat intel status including refreshInProgress,
            lastStatus, lastStatusTime, and feed details.

        Raises:
            WhisperAPIRequestError: If the request fails.
        """
        return self._request("GET", THREAT_INTEL_STATUS_ENDPOINT)

    def history(self, indicator: str) -> dict[str, Any]:
        """Retrieve historical WHOIS and BGP snapshots for an indicator.

        Uses the ``whisper.history()`` procedure to get timestamped
        snapshots of domain WHOIS records and IP BGP routing history.

        Args:
            indicator: The indicator value (registrable domain or IP prefix).

        Returns:
            History response with 'columns' and 'rows' keys containing
            timestamped snapshots of WHOIS/BGP changes.

        Raises:
            WhisperAPIRequestError: If the request fails.
        """
        safe_indicator = indicator.replace("\\", "\\\\").replace('"', '\\"')
        return self.query(f'CALL whisper.history("{safe_indicator}")')

    def explain(self, indicator: str) -> dict[str, Any]:
        """Run threat assessment on an indicator via CALL explain().

        Args:
            indicator: The indicator value (IP, domain, ASN, CIDR).

        Returns:
            Explain response with score, level, factors, sources.

        Raises:
            WhisperAPIRequestError: If the request fails.
        """
        # Sanitize indicator to prevent Cypher injection via quotes
        safe_indicator = indicator.replace("\\", "\\\\").replace('"', '\\"')
        return self.query(f'CALL explain("{safe_indicator}")')

    def __enter__(self) -> WhisperAPIClient:
        """Enter the context manager, returning the client instance."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the context manager and close the underlying session."""
        self.close()

    def close(self) -> None:
        """Close the underlying session and release connections."""
        self._session.close()

    def _parse_error(self, response: requests.Response) -> WhisperAPIError:
        """Parse an error response into a structured error object.

        Delegates to whisper_api_retry.parse_error.

        Args:
            response: The HTTP response with non-2xx status.

        Returns:
            Structured error with retry classification.
        """
        return parse_error(response)

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute an HTTP request with retry and rate limiting.

        Delegates error parsing to whisper_api_retry.parse_error and
        backoff calculation to whisper_api_retry.calculate_backoff.

        Args:
            method: HTTP method (GET, POST).
            endpoint: API endpoint path.
            **kwargs: Additional arguments passed to requests.

        Returns:
            Parsed JSON response.

        Raises:
            WhisperAPIRequestError: On non-retryable error or exhausted retries.
        """
        url = f"{self._base_url}{endpoint}"
        last_error: WhisperAPIError | None = None

        for attempt in range(self._max_retries + 1):
            self._rate_limit_wait()
            try:
                logger.debug(
                    "API request: %s %s (attempt %d/%d)",
                    method,
                    endpoint,
                    attempt + 1,
                    self._max_retries + 1,
                )
                response = self._session.request(method, url, timeout=self._timeout, **kwargs)
                logger.debug(
                    "API response: %s %s -> %d (%dms)",
                    method,
                    endpoint,
                    response.status_code,
                    int(response.elapsed.total_seconds() * 1000),
                )

                if response.ok:
                    data = response.json()
                    # Inject timing metadata for callers (#405)
                    round_trip_ms = int(response.elapsed.total_seconds() * 1000)
                    statistics = data.get("statistics", {})
                    query_time_ms = statistics.get("executionTimeMs", 0) if isinstance(statistics, dict) else 0
                    data["_timing"] = {
                        "round_trip_ms": round_trip_ms,
                        "query_time_ms": query_time_ms,
                        "network_latency_ms": max(0, round_trip_ms - query_time_ms),
                    }
                    return data

                error = self._parse_error(response)
                last_error = error
                if not error.retryable or attempt == self._max_retries:
                    raise WhisperAPIRequestError(error)

                delay = calculate_backoff(attempt, response)
                logger.warning(
                    "Retryable error %d on %s %s, retrying in %.1fs (attempt %d/%d)",
                    error.status_code,
                    method,
                    endpoint,
                    delay,
                    attempt + 1,
                    self._max_retries + 1,
                )
                time.sleep(delay)

            except requests.ConnectionError as exc:
                last_error = WhisperAPIError(
                    status_code=0,
                    error_type="ConnectionError",
                    message=str(exc),
                    retryable=True,
                )
                if attempt == self._max_retries:
                    raise WhisperAPIRequestError(last_error) from exc
                delay = calculate_backoff(attempt)
                logger.warning("action=api_request, status=retry, reason=connection_error, delay_s=%.1f", delay)
                time.sleep(delay)

            except requests.Timeout as exc:
                last_error = WhisperAPIError(
                    status_code=408,
                    error_type="Timeout",
                    message=f"Request timed out after {self._timeout}s",
                    retryable=False,
                )
                raise WhisperAPIRequestError(last_error) from exc

        raise WhisperAPIRequestError(
            last_error
            or WhisperAPIError(
                status_code=0,
                error_type="Unknown",
                message="Request failed after retries",
                retryable=False,
            )
        )

    def _rate_limit_wait(self) -> None:
        """Enforce rate limiting between requests."""
        if self._rate_limit <= 0:
            return
        min_interval = 1.0 / self._rate_limit
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.monotonic()

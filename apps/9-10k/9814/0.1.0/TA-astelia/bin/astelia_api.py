import time
from collections.abc import Callable
from typing import Any, Optional
from urllib.parse import urlsplit

import requests

ADDON_VERSION = "0.1.0"
USER_AGENT = f"TA-astelia/{ADDON_VERSION}"
API_VERSION_PATH = "v1"

DEFAULT_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 2
MAX_RETRY_AFTER_SECONDS = 120
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR_FLOOR = 500

INVALID_CURSOR_CODE = "invalid_cursor"


class AsteliaApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        retry_after_seconds: Optional[int] = None,
    ) -> None:
        super().__init__(f"{status_code} {code}: {message}")
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retry_after_seconds = retry_after_seconds


class AsteliaAuthError(AsteliaApiError):
    pass


class AsteliaInvalidCursorError(AsteliaApiError):
    pass


class AsteliaRateLimitedError(AsteliaApiError):
    pass


class AsteliaUnavailableError(AsteliaApiError):
    pass


def normalize_base_url(raw_url: str) -> str:
    candidate = (raw_url or "").strip().rstrip("/")
    if candidate.endswith(f"/{API_VERSION_PATH}"):
        candidate = candidate[: -len(API_VERSION_PATH) - 1]
    parts = urlsplit(candidate)
    if parts.scheme != "https" or not parts.netloc or parts.path not in ("", "/") or parts.query or parts.fragment:
        raise ValueError(f"API URL must be an https:// origin with no path, got {raw_url!r}")
    return f"https://{parts.netloc}"


def _parse_error_body(response: requests.Response) -> tuple[str, str]:
    try:
        body = response.json()
    except ValueError:
        return "http_error", (response.text or "")[:500]
    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return "http_error", str(body)[:500]
    return str(error.get("code") or "http_error"), str(error.get("message") or "")


def _retry_after_seconds(response: requests.Response) -> Optional[int]:
    header = response.headers.get("Retry-After")
    if header is None:
        return None
    try:
        return max(0, int(header))
    except ValueError:
        return None


class AsteliaClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        session: Optional[requests.Session] = None,
        proxies: Optional[dict[str, str]] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self._api_key = api_key
        self._session = session or requests.Session()
        self._proxies = proxies
        self._timeout_seconds = timeout_seconds
        self._sleep = sleep

    @property
    def host(self) -> str:
        return urlsplit(self.base_url).hostname or self.base_url

    def ping(self) -> dict[str, Any]:
        return self._get("ping", {})

    def list_audit_logs(
        self,
        cursor: Optional[str] = None,
        since: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        elif since:
            params["since"] = since
        return self._get("audit-logs", params)

    def list_connectors(self, stale_after_hours: Optional[int] = None) -> dict[str, Any]:
        return self._get("connectors", {"stale_after_hours": stale_after_hours})

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/{API_VERSION_PATH}/{path}"
        query = {key: value for key, value in params.items() if value is not None}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        last_error: Optional[AsteliaApiError] = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self._session.get(
                    url,
                    params=query,
                    headers=headers,
                    timeout=self._timeout_seconds,
                    proxies=self._proxies,
                    verify=True,
                )
            except requests.RequestException as exc:
                last_error = AsteliaUnavailableError(0, "connection_error", str(exc))
                self._sleep(self._backoff_seconds(attempt))
                continue

            if response.status_code == HTTP_OK:
                return response.json()

            code, message = _parse_error_body(response)
            status = response.status_code
            if status == HTTP_TOO_MANY_REQUESTS:
                retry_after = _retry_after_seconds(response)
                last_error = AsteliaRateLimitedError(status, code, message, retry_after)
                self._sleep(min(retry_after or self._backoff_seconds(attempt), MAX_RETRY_AFTER_SECONDS))
                continue
            if status in (HTTP_UNAUTHORIZED, HTTP_FORBIDDEN):
                raise AsteliaAuthError(status, code, message)
            if status == HTTP_BAD_REQUEST:
                if code == INVALID_CURSOR_CODE:
                    raise AsteliaInvalidCursorError(status, code, message)
                raise AsteliaApiError(status, code, message)
            if status >= HTTP_SERVER_ERROR_FLOOR:
                last_error = AsteliaUnavailableError(status, code, message, _retry_after_seconds(response))
                self._sleep(self._backoff_seconds(attempt))
                continue
            raise AsteliaApiError(status, code, message)

        assert last_error is not None
        raise last_error

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        return float(BACKOFF_BASE_SECONDS ** (attempt - 1))

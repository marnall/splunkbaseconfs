"""
Talks to one Cisodium tenant's SIEM feed API.

    GET /api/v2/siem/whoami                 who the API key belongs to, which feeds exist
    GET /api/v2/siem/feeds/<feed>?cursor=…  one page of records, oldest change first

Every page carries `next_cursor`, the position after its last record. The
add-on stores it (KV store checkpoint) and asks from there on the next run, so
a record is read once for every change made to it, in the order the changes
happened. `has_more` says whether another page is waiting right now.

This module knows nothing about Splunk: the modular input and the account
validation handler both use it, and the tests drive it with a fake session.
It must run on the Python that ships with Splunk (3.9 and later).
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterator, Optional
from urllib.parse import quote, urlsplit

import requests

ADDON_VERSION = "1.0.1"
USER_AGENT = "Cisodium-Splunk-AddOn/" + ADDON_VERSION

API_PREFIX = "/api/v2/siem"
DEFAULT_TIMEOUT = 60
DEFAULT_PAGE_SIZE = 500
MAX_PAGE_SIZE = 1000

#: The feeds a Cisodium tenant serves, and the sourcetype each is indexed as.
#: `whoami` returns the tenant's own list; this one is what the add-on offers.
FEEDS: Dict[str, Dict[str, str]] = {
    "incidents": {"sourcetype": "cisodium:incident", "label": "Incidents"},
    "vulnerabilities": {"sourcetype": "cisodium:vulnerability", "label": "Vulnerabilities"},
    "risks": {"sourcetype": "cisodium:risk", "label": "Risks"},
    "assets": {"sourcetype": "cisodium:asset", "label": "Assets"},
    "controls": {"sourcetype": "cisodium:control", "label": "Security controls"},
    "audit": {"sourcetype": "cisodium:audit", "label": "Audit log"},
}

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504, 520, 521, 522, 523, 524})
_API_KEY_RE = re.compile(r"^cso_[0-9a-f]{64}$")
_CF_RAY_IN_PAGE_RE = re.compile(r"Ray ID:?\s*(?:<[^>]+>\s*)*([0-9a-f]{12,20})", re.I)


class CisodiumError(Exception):
    """A request to Cisodium failed; `str()` is written for the Splunk admin."""

    def __init__(
        self,
        message: str,
        status: Optional[int] = None,
        retryable: bool = False,
        ray_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retryable = retryable
        self.ray_id = ray_id


def normalize_base_url(url: str) -> str:
    """`https://host[:port][/prefix]` without a trailing slash, or ValueError.

    Only HTTPS: the API key travels in a header, and Splunk Cloud refuses
    add-ons that talk to the outside world in clear text.
    """
    url = (url or "").strip()
    parts = urlsplit(url)
    if parts.scheme.lower() != "https":
        raise ValueError("The Cisodium URL must start with https://")
    if not parts.hostname:
        raise ValueError("The Cisodium URL has no host name")
    if parts.query or parts.fragment:
        raise ValueError("The Cisodium URL must not contain ? or #")
    if parts.username or parts.password:
        raise ValueError("The Cisodium URL must not contain a user name or password")
    netloc = parts.hostname.lower()
    if parts.port:
        netloc += ":%d" % parts.port
    path = parts.path.rstrip("/")
    return "https://" + netloc + path


def looks_like_api_key(value: str) -> bool:
    """A Cisodium platform API key is `cso_` followed by 64 hex characters."""
    return bool(_API_KEY_RE.match((value or "").strip()))


def parse_timestamp(value: Any) -> Optional[float]:
    """ISO 8601 (`…Z`, `…+00:00` or naive = UTC) → epoch seconds, else None."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    # Python 3.9's fromisoformat takes 3 or 6 fraction digits only.
    match = re.match(r"^(.*T\d{2}:\d{2}:\d{2})\.(\d+)(.*)$", text)
    if match:
        text = match.group(1) + "." + (match.group(2) + "000000")[:6] + match.group(3)
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def start_date_to_since(value: Optional[str]) -> Optional[str]:
    """The input's optional start date → the `since` the API takes.

    `YYYY-MM-DD` means midnight UTC. Empty means the whole history.
    """
    text = (value or "").strip()
    if not text:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        text += "T00:00:00Z"
    if parse_timestamp(text) is None:
        raise ValueError(
            "Start date must look like 2026-01-31 or 2026-01-31T08:00:00Z, got %r" % value
        )
    return text


def proxies_from_settings(settings: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """The add-on's proxy tab → a `requests` proxies mapping (None = direct)."""
    if not settings:
        return None
    enabled = str(settings.get("proxy_enabled", "")).strip().lower()
    if enabled not in ("1", "true", "yes", "t", "y"):
        return None
    host = (settings.get("proxy_url") or "").strip()
    port = str(settings.get("proxy_port") or "").strip()
    if not host:
        return None
    scheme = (settings.get("proxy_type") or "http").strip().lower()
    if scheme == "socks5":
        rdns = str(settings.get("proxy_rdns", "")).strip().lower() in ("1", "true", "yes", "t", "y")
        scheme = "socks5h" if rdns else "socks5"
    elif scheme not in ("http", "socks4"):
        scheme = "http"
    user = settings.get("proxy_username") or ""
    password = settings.get("proxy_password") or ""
    auth = ""
    if user:
        auth = quote(user, safe="")
        if password:
            auth += ":" + quote(password, safe="")
        auth += "@"
    uri = "%s://%s%s" % (scheme, auth, host)
    if port:
        uri += ":" + port
    return {"http": uri, "https": uri}


def _cloudflare_ray(response: requests.Response) -> Optional[str]:
    ray = response.headers.get("CF-RAY") or response.headers.get("cf-ray")
    if ray:
        return ray.split("-")[0]
    text = response.text or ""
    match = _CF_RAY_IN_PAGE_RE.search(text)
    return match.group(1) if match else None


def _is_cloudflare_page(response: requests.Response) -> bool:
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "text/html" not in content_type and "text/plain" not in content_type:
        return False
    head = (response.text or "")[:4000].lower()
    return "cloudflare" in head or head.startswith("error code:")


def _detail(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    if isinstance(body, dict):
        detail = body.get("detail") or body.get("message") or body.get("error")
        if isinstance(detail, (dict, list)):
            return json.dumps(detail)[:300]
        return str(detail or "")[:300]
    return ""


def describe_http_error(response: requests.Response) -> CisodiumError:
    """Turn a non-2xx answer into an error a Splunk admin can act on."""
    status = response.status_code
    if _is_cloudflare_page(response):
        ray = _cloudflare_ray(response)
        return CisodiumError(
            "Cloudflare in front of Cisodium refused the request (HTTP %d%s). The "
            "request never reached Cisodium; send the Ray ID to Cisodium support."
            % (status, ", Ray ID " + ray if ray else ""),
            status=status,
            retryable=status in _RETRYABLE_STATUS,
            ray_id=ray,
        )
    detail = _detail(response)
    if status == 401:
        message = (
            "Cisodium rejected the API key (HTTP 401). Check that the key is typed "
            "correctly, is active, has not expired, and that its IP allowlist (if any) "
            "includes this Splunk server's outbound address."
        )
    elif status == 403:
        message = (
            "The API key is not allowed to read this data (HTTP 403%s). Create a key "
            "with the 'SIEM Feeds (read)' scope in Cisodium → Settings → Integrations → "
            "Splunk → Splunk Add-on." % (": " + detail if detail else "")
        )
    elif status == 404:
        message = (
            "This Cisodium does not answer on %s (HTTP 404). Check the URL, or ask your "
            "Cisodium administrator to update the platform." % API_PREFIX
        )
    elif status == 429:
        message = "Cisodium is rate-limiting this API key (HTTP 429)."
    elif status >= 500:
        message = "Cisodium answered with a server error (HTTP %d%s)." % (
            status, ": " + detail if detail else "")
    else:
        message = "Cisodium refused the request (HTTP %d%s)." % (
            status, ": " + detail if detail else "")
    return CisodiumError(message, status=status, retryable=status in _RETRYABLE_STATUS)


class CisodiumClient:
    """One tenant, one API key. Thread-unsafe, cheap to create."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        proxies: Optional[Dict[str, str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 4,
        max_backoff: float = 60.0,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
        logger: Any = None,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self.api_key = (api_key or "").strip()
        if not self.api_key:
            raise ValueError("An API key is required")
        self.proxies = proxies
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self.max_backoff = max_backoff
        self.session = session or requests.Session()
        self._sleep = sleep
        self._logger = logger

    @property
    def host(self) -> str:
        return urlsplit(self.base_url).hostname or ""

    # ---------------------------------------------------------------- calls

    def whoami(self) -> Dict[str, Any]:
        """Which organisation and key this is, and the feeds the tenant serves."""
        return self._get(API_PREFIX + "/whoami", {})

    def fetch_page(
        self,
        feed: str,
        *,
        cursor: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> Dict[str, Any]:
        """One page of a feed. With a cursor, `since` is ignored by the server."""
        if feed not in FEEDS:
            raise ValueError("Unknown Cisodium feed %r" % feed)
        params: Dict[str, Any] = {"limit": max(1, min(int(limit), MAX_PAGE_SIZE))}
        if cursor:
            params["cursor"] = cursor
        elif since:
            params["since"] = since
        page = self._get(API_PREFIX + "/feeds/" + feed, params)
        items = page.get("items")
        if not isinstance(items, list):
            raise CisodiumError("Cisodium answered without an item list for feed %r" % feed)
        return page

    def iter_pages(
        self,
        feed: str,
        *,
        cursor: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = DEFAULT_PAGE_SIZE,
        max_pages: Optional[int] = None,
        deadline: Optional[float] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Pages from `cursor` (or `since`) until the feed is drained.

        Stops early after `max_pages`, or once `time.monotonic()` passes
        `deadline`, so one run never outlives its interval; the next run goes on
        from the checkpoint.
        """
        pages = 0
        while True:
            page = self.fetch_page(feed, cursor=cursor, since=since, limit=limit)
            pages += 1
            yield page
            next_cursor = page.get("next_cursor") or cursor
            if not page.get("has_more"):
                return
            if not next_cursor or next_cursor == cursor:
                raise CisodiumError(
                    "Cisodium said more %s records are waiting but did not move the "
                    "cursor; stopping to avoid reading the same page forever." % feed
                )
            cursor = next_cursor
            if max_pages is not None and pages >= max_pages:
                return
            if deadline is not None and time.monotonic() >= deadline:
                return

    # ------------------------------------------------------------- plumbing

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = self.base_url + path
        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        attempt = 0
        while True:
            try:
                response = self.session.request(
                    "GET",
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    proxies=self.proxies,
                    verify=True,
                    allow_redirects=False,
                )
            except requests.exceptions.SSLError as exc:
                raise CisodiumError(
                    "The TLS certificate of %s could not be verified: %s" % (self.host, exc)
                ) from exc
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                error = CisodiumError(
                    "Could not reach %s: %s" % (self.host, exc), retryable=True
                )
                if attempt >= self.max_retries:
                    raise error from exc
                self._backoff(attempt, None, error)
                attempt += 1
                continue

            if 300 <= response.status_code < 400:
                raise CisodiumError(
                    "Cisodium redirected the request (HTTP %d to %s). Use the tenant's "
                    "exact https:// address as the URL."
                    % (response.status_code, response.headers.get("Location", "?")),
                    status=response.status_code,
                )
            if response.status_code >= 400:
                error = describe_http_error(response)
                if error.retryable and attempt < self.max_retries:
                    self._backoff(attempt, response.headers.get("Retry-After"), error)
                    attempt += 1
                    continue
                raise error
            try:
                body = response.json()
            except ValueError as exc:
                raise CisodiumError(
                    "Cisodium answered HTTP %d with something that is not JSON; is the "
                    "URL the Cisodium tenant itself?" % response.status_code,
                    status=response.status_code,
                ) from exc
            if not isinstance(body, dict):
                raise CisodiumError("Cisodium answered with unexpected JSON")
            return body

    def _backoff(self, attempt: int, retry_after: Optional[str], error: CisodiumError) -> None:
        delay = min(self.max_backoff, 2.0 ** attempt * 2.0)
        if retry_after:
            try:
                delay = min(self.max_backoff, max(0.0, float(retry_after)))
            except ValueError:
                pass
        if self._logger is not None:
            self._logger.warning(
                "Retrying in %.0fs (attempt %d of %d): %s",
                delay, attempt + 1, self.max_retries, error,
            )
        self._sleep(delay)

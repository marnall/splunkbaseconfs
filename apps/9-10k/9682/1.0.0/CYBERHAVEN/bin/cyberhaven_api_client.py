"""Shared Cyberhaven Incidents API client.

Used by the cyberhaven_update_status and cyberhaven_update_owner adaptive
response actions.

Auth flow (see the "Cyberhaven API" Postman collection):

  1. POST {tenant_url}/public/v2/auth/token/access
     header:  Authorization: <api_key>
     body:    {"refresh_token": "<api_key>"}
     ->       {"errors": [...], "access_token": "<jwt>"}

  2. PATCH {tenant_url}/public/v2/incidents/{incident_id}
     header:  Authorization: Bearer <access_token>
     body:    caller-supplied fields, e.g. {"status": ...} or {"assigned_to": ...}

Status-code handling and retry policy:
  - 429 / 5xx: transient. Retried automatically by the requests.Session's
    mounted urllib3 Retry adapter -- exponential backoff with full jitter,
    capped delay, capped attempts, honoring Retry-After when present. If still
    non-2xx after retries are exhausted, raised as CyberhavenRetryExhaustedError
    -- distinct from the codes below because a later scheduled run may still
    succeed with no change on our side, unlike the others.
  - 401: the access token from step 1 is short-lived and is fetched once per
    run, then reused across every triggering event. If it expires or is
    rejected mid-batch, this can't be fixed by resending the same request (as
    the Session's Retry would), so it's handled in Python: refresh the token
    once and retry that one event once. If the retry also gets a 401, the
    caller should treat the Cyberhaven credential as broken for the rest of
    that run and stop calling the API (do not keep re-authenticating per
    event).
  - 403: CyberhavenPermissionError. The token is valid but lacks permission for
    this request -- refreshing it (as done for 401) won't help; the fix is to
    check the API key's scope/tenant, not the token's validity.
  - 404: CyberhavenNotFoundError. The incident_id doesn't exist on the
    Cyberhaven platform -- most likely a deleted incident, or a stale/incorrect
    id recovered from the notable event's join against Cyberhaven ingestion
    data (see the NOTE in each sync saved search's description).
  - 409: CyberhavenConflictError. The requested change conflicts with the
    incident's current state on the Cyberhaven platform (e.g. an invalid
    status transition).
  - 400 / other 4xx not covered above: CyberhavenPermanentError. Permanent for
    that event, with no differentiated remediation beyond reading the logged
    response body; fail without retrying.
  - Proxy connection failures (bad host/port, proxy auth rejected, etc., when
    TA-CYBERHAVEN's Proxy configuration is enabled): raised as
    CyberhavenProxyError after the Session's Retry adapter exhausts its
    attempts, so callers can log/report this distinctly from the Cyberhaven
    platform itself being unreachable.
"""
import random

import requests
from requests.adapters import HTTPAdapter
from splunk.clilib import cli_common as cli
from splunk.clilib.bundle_paths import make_splunkhome_path
from urllib3.util.retry import Retry

API_TIMEOUT = 30
MAX_RETRIES = 5
BACKOFF_FACTOR_SECONDS = 1.0
BACKOFF_CAP_SECONDS = 30.0
RESPONSE_LOG_LIMIT = 500
RETRYABLE_STATUSES = (429, 500, 502, 503, 504)

APP_NAME = "CYBERHAVEN"
_DEFAULT_APP_VERSION = "1.0.0"


def _get_app_version():
    """Read this app's own version from app.conf's [launcher] stanza.

    Reads directly from the file (local overriding default) rather than via a
    btool subprocess -- this runs on every adaptive response invocation, so it
    needs to be cheap. Falls back to _DEFAULT_APP_VERSION if app.conf can't be
    read for any reason.
    """
    try:
        app_path = make_splunkhome_path(["etc", "apps", APP_NAME])
        conf = cli.getAppConf("app", APP_NAME, use_btool=False, app_path=app_path)
        return conf["launcher"]["version"]
    except Exception:
        return _DEFAULT_APP_VERSION


USER_AGENT = f"Splunk-{APP_NAME}/{_get_app_version()}"


class CyberhavenAPIError(Exception):
    """Base class for errors returned by the Cyberhaven API.

    Carries the HTTP status code and (redacted/truncated) response body as
    attributes, not just baked into the message string, so callers can format
    log lines or branch on them without re-parsing the message.
    """

    def __init__(self, message, status_code=None, response_body=None):
        """Store the status code and response body alongside the exception message."""
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class CyberhavenAuthError(CyberhavenAPIError):
    """401 - the access token is missing, expired, or rejected."""


class CyberhavenPermissionError(CyberhavenAPIError):
    """403 - the token is valid but lacks permission for this request.

    Refreshing it (like 401 handling does) won't help; the fix is checking
    the API key's scope/tenant, not its validity.
    """


class CyberhavenNotFoundError(CyberhavenAPIError):
    """404 - the incident_id doesn't exist on the Cyberhaven platform.

    Most likely a deleted incident, or a stale/incorrect id recovered from
    the notable event's join against Cyberhaven ingestion data.
    """


class CyberhavenConflictError(CyberhavenAPIError):
    """409 - the requested change conflicts with the incident's current state.

    E.g. an invalid status transition on the Cyberhaven platform.
    """


class CyberhavenRetryExhaustedError(CyberhavenAPIError):
    """429/5xx - transient, but the Session's Retry adapter already exhausted its attempts.

    Unlike the other CyberhavenAPIError subclasses, a later scheduled run may
    still succeed with no change on our side.
    """


class CyberhavenProxyError(CyberhavenAPIError):
    """The configured proxy (TA-CYBERHAVEN's Proxy tab) could not be reached, or refused.

    Refused the connection/credentials -- distinct from the Cyberhaven platform
    itself being unreachable, so callers can point the user at the proxy
    settings specifically.
    """


class CyberhavenPermanentError(CyberhavenAPIError):
    """400, or any other 4xx not covered above.

    No differentiated remediation beyond reading the logged response body;
    fail without retrying.
    """


class _FullJitterRetry(Retry):
    """urllib3 Retry with full jitter layered on top of its deterministic backoff.

    This vendored urllib3 (1.26.x) has no native jitter/backoff_max support.
    """

    def get_backoff_time(self):
        backoff = super().get_backoff_time()
        if not backoff:
            return backoff
        return random.uniform(0, min(BACKOFF_CAP_SECONDS, backoff))


def _build_session():
    """Build a requests.Session with 429/5xx retry, backoff, jitter, and Retry-After handling.

    Mounted at the transport level and shared across calls in this process for
    connection reuse.
    """
    session = requests.Session()
    retry = _FullJitterRetry(
        total=MAX_RETRIES,
        status_forcelist=RETRYABLE_STATUSES,
        allowed_methods=frozenset({"POST", "PATCH"}),
        backoff_factor=BACKOFF_FACTOR_SECONDS,
        respect_retry_after_header=True,
        raise_on_status=False,  # always return the final response; we classify it ourselves
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


_session = _build_session()


def _redacted_body(resp):
    """Return a length-capped response body for logging; never includes request headers."""
    try:
        return resp.text[:RESPONSE_LOG_LIMIT]
    except Exception:
        return "<response body unavailable>"


def _raise_for_cyberhaven_status(resp):
    """Translate the final HTTP response into the typed exceptions above; no-op on 2xx.

    By the time this runs, the Session's Retry adapter has already exhausted its
    429/5xx retries, so any non-2xx status left here (including 429/5xx) is terminal
    for this call.
    """
    status = resp.status_code
    if 200 <= status < 300:
        return
    body = _redacted_body(resp)
    if status == 401:
        raise CyberhavenAuthError(f"401 Unauthorized: {body}", status_code=status, response_body=body)
    if status == 403:
        raise CyberhavenPermissionError(f"403 Forbidden: {body}", status_code=status, response_body=body)
    if status == 404:
        raise CyberhavenNotFoundError(f"404 Not Found: {body}", status_code=status, response_body=body)
    if status == 409:
        raise CyberhavenConflictError(f"409 Conflict: {body}", status_code=status, response_body=body)
    if status in RETRYABLE_STATUSES:
        raise CyberhavenRetryExhaustedError(
            f"{status} (retries exhausted): {body}", status_code=status, response_body=body
        )
    raise CyberhavenPermanentError(f"{status}: {body}", status_code=status, response_body=body)


def get_access_token(base_url, api_key, proxies=None):
    """Exchange the configured Cyberhaven API key for a short-lived access token."""
    try:
        resp = _session.post(
            f"{base_url}/v2/auth/token/access",
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={"refresh_token": api_key},
            timeout=API_TIMEOUT,
            proxies=proxies,
        )
    except requests.exceptions.ProxyError as e:
        raise CyberhavenProxyError(f"Could not connect through the configured proxy: {e}") from e
    _raise_for_cyberhaven_status(resp)
    data = resp.json()
    errors = data.get("errors") or []
    if errors:
        raise CyberhavenPermanentError(
            f"Cyberhaven auth error: {errors}", status_code=resp.status_code, response_body=_redacted_body(resp)
        )
    access_token = data.get("access_token")
    if not access_token:
        raise CyberhavenPermanentError(
            "Cyberhaven auth response did not include an access_token.",
            status_code=resp.status_code,
            response_body=_redacted_body(resp),
        )
    return access_token


def patch_incident(base_url, access_token, incident_id, payload, proxies=None):
    """Call PATCH /v2/incidents/:id with the given payload dict."""
    try:
        resp = _session.patch(
            f"{base_url}/v2/incidents/{incident_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=API_TIMEOUT,
            proxies=proxies,
        )
    except requests.exceptions.ProxyError as e:
        raise CyberhavenProxyError(f"Could not connect through the configured proxy: {e}") from e
    _raise_for_cyberhaven_status(resp)
    return resp


def sync_incident(base_url, api_key, access_token_box, incident_id, payload, helper, proxies=None):
    """Apply `payload` to one incident, refreshing the access token once on a 401.

    access_token_box is a 1-item list shared across events in a run, so a
    mid-batch token refresh is reused by subsequent events instead of
    re-fetched every time. Raises CyberhavenAuthError if the retry-after-refresh
    also fails, and any other CyberhavenAPIError for non-retryable failures --
    callers are expected to catch these per event. proxies, if given, is a
    requests-style proxies dict (see cyberhaven_settings.get_proxy_settings)
    applied to every request this call makes.
    """
    try:
        patch_incident(base_url, access_token_box[0], incident_id, payload, proxies=proxies)
        return
    except CyberhavenAuthError:
        pass  # fall through to the single refresh-and-retry below

    helper.log_warn(f"Cyberhaven access token rejected for incident {incident_id}; refreshing once.")
    access_token_box[0] = get_access_token(base_url, api_key, proxies=proxies)  # raises => terminal, not caught here
    # retry once; raises on failure
    patch_incident(base_url, access_token_box[0], incident_id, payload, proxies=proxies)

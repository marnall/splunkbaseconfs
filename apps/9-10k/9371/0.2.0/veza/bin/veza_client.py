"""Veza export-endpoint client shared by the veza_events and veza_audit_logs
modular inputs.

Drains a cursor-paginated /api/v1/{events,system/audit}/export endpoint into
a caller-supplied event sink. Persists the cursor between invocations so each
scheduled run picks up exactly where the previous run left off.

Splunk Enterprise ships Python 3.7+ and the `requests` library; this module
relies on both and bundles no additional dependencies, so it stays compatible
with Splunk Cloud's vetted runtime.
"""

import json
import logging
import os
import random
import time
import urllib.parse
from datetime import datetime, timezone

_log = logging.getLogger(__name__)

import requests

# Endpoints --------------------------------------------------------------------
EVENTS_PATH = "/api/v1/events/export"
AUDIT_PATH = "/api/v1/system/audit/export"
OAUTH_TOKEN_PATH = "/oauth/token"

# Two response shapes — events:export uses "events", audit/export uses "values".
ITEMS_KEY = {
    EVENTS_PATH: "events",
    AUDIT_PATH: "values",
}

# OAuth refresh buffer — refresh a cached token this many seconds before its
# server-reported expiry so requests never race the expiry deadline mid-page.
OAUTH_REFRESH_BUFFER_SECONDS = 300

# Behaviour --------------------------------------------------------------------
DEFAULT_PAGE_SIZE = 1000
# Cap pages drained per scheduled cycle. At page_size=1000 this is up to 50K
# items in one cycle — comfortably above steady-state, and on a backlogged
# cold start the remaining work spreads across subsequent cycles rather than
# hammering the API in one long burst.
MAX_PAGES_PER_CYCLE = 50
HTTP_TIMEOUT = (10, 60)  # (connect, read) seconds
RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0


# ---- internal helpers --------------------------------------------------------


def _atomic_write_json(path, doc):
    """Write `doc` to `path` via a temp file + rename so concurrent readers
    never see a torn file."""
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f)
    os.replace(tmp, path)


def _load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _utc_iso_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- exceptions --------------------------------------------------------------


class VezaAuthError(Exception):
    """401/403 from Veza — token is invalid or lacks the Auditor role. Fatal."""


class VezaOAuthError(Exception):
    """The OAuth token endpoint returned a non-2xx — usually a bad client_id
    /client_secret, a scope the client isn't allowed to request, or a client
    that isn't configured for the client_credentials grant. Fatal."""


class VezaCheckpointExpired(Exception):
    """400 with a body that signals the saved cursor aged out."""


# ---- OAuth client_credentials -----------------------------------------------


class OAuthTokenManager:
    """Issues an OAuth bearer token via Veza's `POST /oauth/token`
    client_credentials grant and holds it in-process for the lifetime of the
    modular-input invocation.

    splunkd respawns each modular input every `interval` seconds, so the
    in-memory cache covers all page fetches inside a single drain cycle and
    is then discarded. We do not persist the token across cycles — the
    one-cycle TTL keeps clock-skew and cache-staleness concerns out of the
    design at the cost of one extra token issuance per cycle (~1440/day per
    input, each writing an audit-log entry on the Veza side).

    `force_refresh()` invalidates the cached token immediately and re-fetches.
    The transport calls it on a 401 to absorb secret rotation mid-drain.
    """

    def __init__(
        self,
        tenant_url,
        client_id,
        client_secret,
        scope=None,
        verify_tls=True,
        clock=time.time,
    ):
        self.tenant_url = tenant_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope or ""
        self.verify_tls = verify_tls
        self._clock = clock
        self._cached = None  # (access_token, expires_at)

    def get_token(self):
        if self._cached and self._cached[1] - OAUTH_REFRESH_BUFFER_SECONDS > self._clock():
            return self._cached[0]
        return self._fetch()

    def force_refresh(self):
        self._cached = None
        return self._fetch()

    def _fetch(self):
        url = self.tenant_url + OAUTH_TOKEN_PATH
        form = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.scope:
            form["scope"] = self.scope

        try:
            resp = requests.post(
                url,
                data=form,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "User-Agent": "Veza-TA-Splunk/0.1",
                },
                verify=self.verify_tls,
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise VezaOAuthError("OAuth token request failed: {0}".format(exc))

        if resp.status_code != 200:
            raise VezaOAuthError(
                "OAuth token request returned HTTP {0}: {1}".format(
                    resp.status_code, (resp.text or "")[:200]
                )
            )

        try:
            doc = resp.json()
        except ValueError as exc:
            raise VezaOAuthError("OAuth response was not JSON: {0}".format(exc))

        access_token = doc["access_token"] if "access_token" in doc else None
        expires_in = doc["expires_in"] if "expires_in" in doc else None
        if not access_token or not isinstance(expires_in, (int, float)):
            raise VezaOAuthError(
                "OAuth response missing access_token or expires_in: {0}".format(
                    list(doc.keys())
                )
            )

        self._cached = (access_token, int(self._clock()) + int(expires_in))
        return access_token


# ---- HTTP transport ----------------------------------------------------------


class VezaTransport:
    """Wraps requests.Session with auth, retry/backoff, and typed error
    classification.

    `token_provider` must expose `.get_token()` and `.force_refresh()`. On a 401
    the transport calls `force_refresh()` once before failing — this absorbs
    secret rotation or in-flight token expiry without operator intervention."""

    def __init__(self, tenant_url, token_provider, verify_tls=True, logger=None):
        self.tenant_url = tenant_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Veza-TA-Splunk/0.1",
                "Accept": "application/json",
            }
        )
        self.token_provider = token_provider
        self.verify_tls = verify_tls
        self.logger = logger

    def get_page(self, path, params):
        url = self.tenant_url + path
        last_exc = None
        refreshed_once = False
        for attempt in range(RETRY_MAX_ATTEMPTS):
            headers = {"Authorization": "Bearer " + self.token_provider.get_token()}

            try:
                resp = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    verify=self.verify_tls,
                    timeout=HTTP_TIMEOUT,
                )
            except requests.RequestException as exc:
                last_exc = exc
                self._sleep_backoff(attempt)
                continue

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 401 and not refreshed_once:
                refreshed_once = True
                self.token_provider.force_refresh()
                continue

            if resp.status_code in (401, 403):
                raise VezaAuthError(
                    "HTTP {0} from {1}: {2}".format(
                        resp.status_code, url, resp.text[:200]
                    )
                )

            if resp.status_code == 400 and _looks_like_expired_cursor(resp):
                raise VezaCheckpointExpired(resp.text[:200])

            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                last_exc = requests.HTTPError(
                    "HTTP {0}: {1}".format(resp.status_code, resp.text[:200])
                )
                self._sleep_backoff(attempt, resp=resp)
                continue

            resp.raise_for_status()

        raise last_exc if last_exc else RuntimeError("retries exhausted")

    def _sleep_backoff(self, attempt, resp=None):
        # Cap at 30s so a transient burst cannot stall a 60s polling cycle past
        # its next scheduled wake-up.
        retry_after = resp.headers.get("Retry-After") if resp is not None else None
        try:
            delay = float(retry_after) if retry_after else RETRY_BASE_DELAY * (2 ** attempt)
        except (TypeError, ValueError):
            delay = RETRY_BASE_DELAY * (2 ** attempt)
        delay = min(delay, 30.0) * (0.5 + random.random() * 0.5)
        if self.logger:
            self.logger.warning(
                "veza-ta backoff attempt=%d delay=%.2fs", attempt + 1, delay
            )
        time.sleep(delay)


def _looks_like_expired_cursor(resp):
    # Both a cursor-token mention AND "expired" must appear together — matching
    # either alone would also catch unrelated 400s like an "invalid page_token
    # format" validation error and silently turn them into recoverable
    # checkpoint-expired events.
    body = (resp.text or "").lower()
    return ("page_token" in body or "cursor" in body) and "expired" in body


# ---- checkpoint persistence --------------------------------------------------


class Checkpoint:
    """Per-input cursor stored as JSON on disk under Splunk's checkpoint
    directory. Updated atomically after every successful page write so a
    mid-cycle crash never leaves a torn file.

    File layout: {"page_token": "<opaque-cursor>", "updated_at": "<iso8601>"}
    """

    def __init__(self, checkpoint_dir, kind, input_name):
        safe_name = urllib.parse.quote(input_name, safe="")
        self.path = os.path.join(
            checkpoint_dir, "veza_{0}_{1}.json".format(kind, safe_name)
        )
        self._last_saved = None

    def load(self):
        doc = _load_json(self.path)
        token = doc.get("page_token") if doc else None
        self._last_saved = token
        return token

    def save(self, page_token):
        # Skip the write when the token has not advanced — cold-start backlogs
        # can otherwise hit dozens of identical writes per cycle.
        if not page_token or page_token == self._last_saved:
            return
        _atomic_write_json(
            self.path,
            {"page_token": page_token, "updated_at": _utc_iso_now()},
        )
        self._last_saved = page_token

    def clear(self):
        try:
            os.remove(self.path)
        except OSError:
            pass
        self._last_saved = None


# ---- pagination loop ---------------------------------------------------------


def drain(transport, path, checkpoint, page_size, sink):
    """Pull all available pages from `path` and hand each item to `sink(item)`.

    Stops when the page returns no items, the response has no cursor, or the
    cursor did not advance past the value we sent — any of those indicate the
    consumer has caught up to the server's tail.

    Returns the number of items emitted.
    """
    items_key = ITEMS_KEY[path]
    cursor = checkpoint.load()
    total = 0

    for _ in range(MAX_PAGES_PER_CYCLE):
        params = {"page_size": page_size}
        if cursor:
            params["page_token"] = cursor

        # VezaCheckpointExpired is intentionally NOT caught here. Silent
        # auto-recovery would paper over a real data-gap incident: the input
        # was offline long enough for its cursor to age past the server's
        # retention window. The caller surfaces the error and a human decides
        # whether to accept the gap and reset, or restore from a backup.
        doc = transport.get_page(path, params)

        items = doc.get(items_key) or []
        next_token = doc.get("next_page_token") or ""

        for item in items:
            sink(item)
            total += 1

        if next_token:
            checkpoint.save(next_token)

        if not items or not next_token or next_token == (cursor or ""):
            break

        cursor = next_token

    return total


# ---- encrypted credential storage --------------------------------------------


CREDENTIAL_REALM = "veza"
SECRET_PLACEHOLDER = "__stored_in_credential_store__"


def is_placeholder(value):
    return value == SECRET_PLACEHOLDER


def resolve_client_secret(service, input_name, plaintext_value):
    """Return the real OAuth client_secret for `input_name`.

    First-run flow (`plaintext_value` is the real secret):
      1. Write the secret to Splunk's `storage_passwords` under realm=veza,
         username=<input_name>.
      2. Rewrite the input's `client_secret` field to a placeholder so the
         cleartext never persists to inputs.conf. This is the pattern Splunk
         AppInspect requires for Splunkbase publishing.
      3. Return the plaintext for use in the current invocation.

    Subsequent-run flow (placeholder seen):
      4. Look up the credential by realm/username and return its clear_password.
    """
    if not is_placeholder(plaintext_value):
        _store_secret(service, input_name, plaintext_value)
        _rewrite_input_secret(service, input_name, SECRET_PLACEHOLDER)
        return plaintext_value

    return _fetch_stored_secret(service, input_name)


def _store_secret(service, input_name, secret):
    # Try create first. The old delete-then-create pattern was vulnerable to a
    # transient failure on `create` permanently destroying the only stored
    # credential — `_fetch_stored_secret` would then raise VezaAuthError on
    # every subsequent invocation with no self-healing path.
    storage = service.storage_passwords
    try:
        storage.create(secret, input_name, CREDENTIAL_REALM)
        return
    except Exception:  # noqa: BLE001  — splunklib raises HTTPError(409) on duplicate
        pass
    for sp in storage:
        if sp.realm == CREDENTIAL_REALM and sp.username == input_name:
            sp.delete()
            break
    try:
        storage.create(secret, input_name, CREDENTIAL_REALM)
    except Exception as exc:  # noqa: BLE001
        # Stale credential was deleted but the replacement failed. Without
        # this explicit signal, the next invocation would silently report
        # "no stored credential" with no context. Raise with a clear hint
        # so the operator knows to re-enter the secret.
        raise VezaAuthError(
            "failed to recreate credential for input '{0}' after delete; "
            "the previous secret has been removed and must be re-entered "
            "via Settings -> Data Inputs: {1}".format(input_name, exc)
        ) from exc


def _fetch_stored_secret(service, input_name):
    for sp in service.storage_passwords:
        if sp.realm == CREDENTIAL_REALM and sp.username == input_name:
            return sp.clear_password
    raise VezaAuthError(
        "no stored credential for input '{0}' in realm '{1}'".format(
            input_name, CREDENTIAL_REALM
        )
    )


def _rewrite_input_secret(service, input_name, new_value):
    # Splunk hands us input names as "<kind>://<stanza>"; the REST API needs
    # them split.
    kind, stanza = input_name.split("://", 1)
    try:
        item = service.inputs[stanza, kind]
        item.update(client_secret=new_value).refresh()
    except KeyError:
        # Input was renamed/deleted between read and write — next scheduled
        # invocation re-reads the (now correct) config.
        return
    except Exception as exc:  # noqa: BLE001 — splunklib HTTPError, network errors, etc.
        # Rewrite failed but the secret is already safely in storage_passwords.
        # Returning silently would let a permanently-failing rewrite hide; log
        # a warning so the operator can spot a persistent loop in
        # $SPLUNK_HOME/var/log/splunk/python.log. Propagating instead would
        # cause an infinite credential-churn loop (every cycle: re-store,
        # fail to rewrite, plaintext still in inputs.conf, re-enter first-run
        # path).
        _log.warning(
            "veza-ta: could not rewrite client_secret placeholder for '%s': "
            "%s (secret is stored; will retry next cycle)",
            input_name, exc,
        )
        return



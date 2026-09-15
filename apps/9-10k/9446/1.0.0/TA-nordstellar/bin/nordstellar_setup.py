"""
Persistent REST handler for the Splunk Add-on for NordStellar setup page.

Endpoint (via Splunk Web proxy): nordstellar/setup

  GET  -> returns current HEC status (enabled?, whether the NordStellar token
          already exists, and the suggested HEC collector URL).
  POST -> enables HEC globally (best effort), creates (or reuses) a HEC token
          dedicated to NordStellar with sourcetype=nordstellar:security:event,
          and returns the token value + collector URL to copy into NordStellar.

All management-API calls reuse the calling user's session key, so splunkd
enforces permissions: a user without edit_httpinputs gets a permission error.
"""

import json

import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

APP_NAME = "TA-nordstellar"
TOKEN_NAME = "nordstellar"
HEC_SOURCETYPE = "nordstellar:security:event"
DEFAULT_HEC_PORT = "8088"

# Namespaced management paths (run as 'nobody' so the object is app-owned).
HEC_COLLECTION = "/servicesNS/nobody/%s/data/inputs/http" % APP_NAME
HEC_GLOBAL = "/servicesNS/nobody/%s/data/inputs/http/http" % APP_NAME
APP_LOCAL = "/servicesNS/nobody/%s/apps/local/%s" % (APP_NAME, APP_NAME)


class SetupHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None):
        super(SetupHandler, self).__init__()

    # -- entry point ---------------------------------------------------------
    def handle(self, in_string):
        try:
            args = json.loads(in_string)
        except (ValueError, TypeError):
            return _response(400, {"error": "Invalid request payload."})

        session_key = args.get("session", {}).get("authtoken")
        if not session_key:
            return _response(401, {"error": "Missing session key."})

        method = args.get("method", "GET").upper()
        host = _detect_host(args)

        if method == "POST":
            index = _read_param(args, "index") or "main"

            return self._generate_token(session_key, index, host)

        return self._status(session_key, host)

    # -- GET: report current state ------------------------------------------
    def _status(self, session_key, host):
        enabled, scheme, port = self._hec_settings(session_key)
        token_content, listing_status = self._find_token_entry(session_key)
        token = (token_content or {}).get("token")

        return _response(200, {
            "hecEnabled": enabled,
            "tokenExists": token is not None,
            "token": token,
            "index": _token_index(token_content),
            "collectorUrl": _collector_url(host, scheme, port),
            # The caller lacks the capability to read HEC tokens (splunkd
            # answered the listing with 401/403) - the UI shows a dedicated
            # message instead of the first-run setup form.
            "permissionDenied": listing_status in (401, 403)
        })

    # -- POST: enable HEC + create/reuse token ------------------------------
    def _generate_token(self, session_key, index, host):
        self._enable_hec_global(session_key)  # best effort

        postargs = {
            "name": TOKEN_NAME,
            "index": index,
            "indexes": index,
            "sourcetype": HEC_SOURCETYPE,
            "disabled": "0"
        }
        try:
            resp, content = rest.simpleRequest(
                HEC_COLLECTION,
                sessionKey=session_key,
                method="POST",
                postargs=postargs,
                getargs={"output_mode": "json"},
                raiseAllErrors=False)
        except Exception as exc:  # noqa: BLE001 - surface any splunkd error
            return _response(500, {"error": "Failed to call Splunk management API.",
                                   "detail": str(exc)})

        token = None
        if resp.status in (200, 201):
            token = _extract_token(content)
        elif resp.status == 409:
            # Already created on a previous run -> reuse the existing token.
            token = self._find_token(session_key)

        if not token:
            # Last resort: the create may have failed because it already exists.
            token = self._find_token(session_key)

        if not token:
            return _response(resp.status if resp.status >= 400 else 500, {
                "error": "Could not create or read the NordStellar HEC token.",
                "detail": _safe_text(content)
            })

        self._mark_configured(session_key)  # best effort

        # Read the settings AFTER enabling HEC so the URL reflects the actual
        # listener configuration (an admin may have changed the port or SSL).
        _, scheme, port = self._hec_settings(session_key)

        return _response(200, {
            "token": token,
            "index": index,
            "collectorUrl": _collector_url(host, scheme, port)
        })

    # -- helpers that touch splunkd -----------------------------------------
    def _hec_settings(self, session_key):
        """Read the actual HEC global settings from splunkd.

        Returns an (enabled, scheme, port) tuple built from the configured
        values (disabled, enableSSL, port) rather than guessing, falling back
        to Splunk's defaults (disabled, https, 8088) only when the settings
        cannot be read."""
        try:
            resp, content = rest.simpleRequest(
                HEC_GLOBAL,
                sessionKey=session_key,
                getargs={"output_mode": "json"},
                method="GET",
                raiseAllErrors=False)
            if resp.status != 200:
                return False, "https", DEFAULT_HEC_PORT
            parsed = json.loads(content)
            entry = parsed.get("entry", [])
            if not entry:
                return False, "https", DEFAULT_HEC_PORT
            settings = entry[0].get("content", {})
            enabled = not _as_bool(settings.get("disabled", True))
            scheme = "https" if _as_bool(settings.get("enableSSL", True)) else "http"
            port = str(settings.get("port") or DEFAULT_HEC_PORT)

            return enabled, scheme, port
        except Exception:  # noqa: BLE001
            return False, "https", DEFAULT_HEC_PORT

    def _enable_hec_global(self, session_key):
        try:
            rest.simpleRequest(
                HEC_GLOBAL,
                sessionKey=session_key,
                method="POST",
                postargs={"disabled": "0"},
                getargs={"output_mode": "json"},
                raiseAllErrors=False)
        except Exception:  # noqa: BLE001 - non-fatal, reported via status
            pass

    def _find_token_entry(self, session_key):
        """Locate the NordStellar HEC token.

        Returns an (entry content dict or None, listing HTTP status) tuple so
        callers can tell "token does not exist" (None, 200) apart from "caller
        may not list tokens" (None, 401/403)."""
        try:
            resp, content = rest.simpleRequest(
                HEC_COLLECTION,
                sessionKey=session_key,
                method="GET",
                getargs={"output_mode": "json", "count": "0"},
                raiseAllErrors=False)
            if resp.status != 200:
                return None, resp.status
            parsed = json.loads(content)
            for entry in parsed.get("entry", []):
                name = entry.get("name", "")
                if name == TOKEN_NAME or name.endswith("/" + TOKEN_NAME):
                    return entry.get("content", {}), 200

            return None, 200
        except Exception:  # noqa: BLE001
            return None, 500

    def _find_token(self, session_key):
        token_content, _ = self._find_token_entry(session_key)

        return (token_content or {}).get("token")

    def _mark_configured(self, session_key):
        try:
            rest.simpleRequest(
                APP_LOCAL,
                sessionKey=session_key,
                method="POST",
                postargs={"configured": "1"},
                getargs={"output_mode": "json"},
                raiseAllErrors=False)
        except Exception:  # noqa: BLE001 - cosmetic only
            pass


# -- module-level pure helpers ----------------------------------------------
def _read_param(args, key):
    for bucket in ("form", "query"):
        for pair in args.get(bucket, []) or []:
            if len(pair) == 2 and pair[0] == key:
                return pair[1]
    payload = args.get("payload")
    if payload:
        try:
            body = json.loads(payload)
            if isinstance(body, dict) and key in body:
                return body[key]
        except (ValueError, TypeError):
            pass

    return None


def _token_index(content):
    """Default index of the token, falling back to the first allowed index.

    A token created or edited outside this app may have allowed indexes set
    but no default index - splunkd then returns an empty 'index' while
    'indexes' still holds the allowed list (as a list or a CSV string)."""
    if not content:
        return None
    index = content.get("index")
    if index:
        return index
    indexes = content.get("indexes")
    if isinstance(indexes, list):
        return indexes[0] if indexes else None
    if isinstance(indexes, str) and indexes.strip():
        return indexes.split(",")[0].strip()

    return None


def _detect_host(args):
    for pair in args.get("headers", []) or []:
        if len(pair) == 2 and pair[0].lower() == "host":
            return pair[1].split(":")[0]

    return "localhost"


def _collector_url(host, scheme, port):
    return "%s://%s:%s/services/collector" % (scheme, host, port)


def _extract_token(content):
    try:
        parsed = json.loads(content)
        entry = parsed.get("entry", [])
        if entry:
            return entry[0].get("content", {}).get("token")
    except (ValueError, TypeError):
        pass

    return None


def _as_bool(value):
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in ("1", "true", "yes")


def _safe_text(content):
    if content is None:
        return ""
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")

    return str(content)


def _response(status, body):
    return {
        "status": status,
        "payload": json.dumps(body),
        "headers": {"Content-Type": "application/json"}
    }

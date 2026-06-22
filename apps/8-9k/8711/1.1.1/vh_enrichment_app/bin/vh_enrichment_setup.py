#!/usr/bin/env python3

"""Persistent REST handler for the Setup page's modular-input save/load.

Why this exists:
    The Splunk Web /en-US/splunkd/__raw/ proxy applies setup-mode
    restrictions when an app's [install] is_configured=0.  In that state
    the proxy refuses to forward certain `servicesNS/.../data/inputs/...`
    paths from the browser, returning a generic 404 "Not Found" — even
    though the same paths return 200 when called directly against
    splunkd on port 8089 by an authenticated session.

    Custom app-owned REST handlers under /services/<app>/... are NOT
    subject to that filter (they share the proxy path used by the
    overview dashboard's working /vh_enrichment/control/* actions).

    So the Setup page now delegates the modular-input CRUD work to
    this backend, which talks to splunkd's data/inputs handler via
    loopback using the caller's session_key.  Browser-side JS only
    calls /services/vh_enrichment/setup/* paths.

Routes (all POST; output_modes=json):
    input_config_get
        Request body: (none)
        Response: {"success":true, "exists":<bool>, "disabled":<bool>,
                   "interval":"<n>"}
    input_config_save
        Request body: form-urlencoded interval=<int>&enabled=<0|1>
        Response: {"success":true, "interval":"<n>", "enabled":<bool>}
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vh_http  # noqa: E402

from splunk.persistconn.application import PersistentServerConnectionApplication


APP_NAME = "vh_enrichment_app"
SPLUNKD_BASE = "https://127.0.0.1:8089"
INPUT_TYPE = "vh_enrichment_modinput"
INPUT_NAME = "default"


def _splunkd_request(session_key, method, path, body=None, timeout=30):
    """Perform a splunkd loopback REST call using the caller's session.

    Returns (status_code, body_text).  Caller is responsible for
    interpreting non-2xx responses.  The proxy_cfg=None on urlopen
    explicitly bypasses any HTTP_PROXY env vars so loopback never
    leaks through a corporate proxy.
    """
    url = SPLUNKD_BASE + path
    headers = {"Authorization": "Splunk " + session_key}
    payload = None
    if body is not None:
        payload = body.encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url=url, data=payload, headers=headers, method=method)

    ctx = ssl.create_default_context()
    cafile = os.path.join(os.environ.get("SPLUNK_HOME", ""), "etc/auth/cacert.pem")
    ctx.load_verify_locations(cafile=cafile)
    ctx.check_hostname = False

    try:
        with vh_http.urlopen(req, context=ctx, timeout=timeout, proxy_cfg=None) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode("utf-8") if e.fp else "")


def _json_response(status, payload):
    return {
        "status": status,
        "payload": json.dumps(payload),
        "headers": {"Content-Type": "application/json"},
    }


def _parse_form(payload_str):
    """Parse a form-urlencoded POST body into a single-value dict."""
    if not payload_str:
        return {}
    parsed = urllib.parse.parse_qs(payload_str, keep_blank_values=True)
    return {k: (v[0] if v else "") for k, v in parsed.items()}


def _get_instance(session_key):
    """GET /data/inputs/<scheme>/<name>.  Returns (status, parsed_body_or_text)."""
    path = ("/servicesNS/nobody/{app}/data/inputs/{type}/{name}"
            "?output_mode=json").format(app=APP_NAME, type=INPUT_TYPE, name=INPUT_NAME)
    return _splunkd_request(session_key, "GET", path)


def _update_instance(session_key, interval):
    path = ("/servicesNS/nobody/{app}/data/inputs/{type}/{name}"
            "?output_mode=json").format(app=APP_NAME, type=INPUT_TYPE, name=INPUT_NAME)
    body = urllib.parse.urlencode({"interval": str(interval)})
    return _splunkd_request(session_key, "POST", path, body=body)


def _create_instance(session_key, interval):
    path = ("/servicesNS/nobody/{app}/data/inputs/{type}"
            "?output_mode=json").format(app=APP_NAME, type=INPUT_TYPE)
    body = urllib.parse.urlencode({"name": INPUT_NAME, "interval": str(interval)})
    return _splunkd_request(session_key, "POST", path, body=body)


def _set_enabled(session_key, enabled):
    action = "enable" if enabled else "disable"
    path = ("/servicesNS/nobody/{app}/data/inputs/{type}/{name}/{action}"
            "?output_mode=json").format(app=APP_NAME, type=INPUT_TYPE,
                                         name=INPUT_NAME, action=action)
    return _splunkd_request(session_key, "POST", path)


def _coerce_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return False


class VHEnrichmentSetupHandler(PersistentServerConnectionApplication):
    """Backend for the Setup page's modular-input lifecycle.

    Splunk's persistconn dispatcher calls handle(in_string) with a JSON
    string that includes session.authtoken, method, path_info, and
    payload (because passPayload=true / passSession=true in restmap).
    """

    def __init__(self, command_line, command_arg):
        super().__init__()

    def handle(self, in_string):
        try:
            req = json.loads(in_string)
            method = req.get("method", "GET").upper()
            path_info = req.get("path_info", "")
            session_key = req["session"]["authtoken"]

            if method != "POST":
                return _json_response(405, {
                    "success": False,
                    "error": "POST only",
                })

            action = path_info.rstrip("/").split("/")[-1]
            if action == "input_config_get":
                return self._handle_get(session_key)
            if action == "input_config_save":
                return self._handle_save(session_key, req)

            return _json_response(400, {
                "success": False,
                "error": "Unknown action: " + action,
            })

        except Exception as e:  # noqa: BLE001
            return _json_response(500, {
                "success": False,
                "error": str(e),
            })

    def _handle_get(self, session_key):
        status, body = _get_instance(session_key)
        if status == 200:
            try:
                doc = json.loads(body)
                content = doc["entry"][0].get("content", {})
                return _json_response(200, {
                    "success": True,
                    "exists": True,
                    "disabled": _coerce_bool(content.get("disabled")),
                    "interval": content.get("interval"),
                })
            except Exception as e:  # noqa: BLE001
                return _json_response(500, {
                    "success": False,
                    "error": "Parse error: " + str(e),
                })
        if status == 404:
            # Either scheme not registered yet OR instance missing —
            # both are "not configured yet" from the UI's perspective.
            # Setup form should render defaults; Save will create.
            return _json_response(200, {
                "success": True,
                "exists": False,
            })
        return _json_response(status if status >= 400 else 500, {
            "success": False,
            "error": "splunkd GET data/inputs returned HTTP {s}: {b}".format(
                s=status, b=body[:300]),
        })

    def _handle_save(self, session_key, req):
        form = _parse_form(req.get("payload") or "")
        try:
            interval = int(form.get("interval") or 60)
        except ValueError:
            return _json_response(400, {
                "success": False,
                "error": "interval must be an integer",
            })
        if interval < 60:
            return _json_response(400, {
                "success": False,
                "error": "interval must be >= 60",
            })
        enabled = _coerce_bool(form.get("enabled"))

        # 1. Try UPDATE first.  If splunkd says the instance does not
        # exist (HTTP 400 + "does not exist" OR 404), fall back to CREATE.
        u_status, u_body = _update_instance(session_key, interval)
        instance_missing = (
            (u_status == 404)
            or (u_status == 400 and "does not exist" in u_body)
        )
        if instance_missing:
            c_status, c_body = _create_instance(session_key, interval)
            # Race recovery: if another writer materialised the instance
            # in between, retry UPDATE once.
            if c_status == 400 and "already exists" in c_body:
                u_status, u_body = _update_instance(session_key, interval)
                if u_status not in (200, 201):
                    return _json_response(u_status, {
                        "success": False,
                        "error": "UPDATE after race failed: HTTP {s}: {b}".format(
                            s=u_status, b=u_body[:300]),
                    })
            elif c_status not in (200, 201):
                return _json_response(c_status, {
                    "success": False,
                    "error": "CREATE failed: HTTP {s}: {b}".format(
                        s=c_status, b=c_body[:300]),
                })
        elif u_status not in (200, 201):
            return _json_response(u_status, {
                "success": False,
                "error": "UPDATE failed: HTTP {s}: {b}".format(
                    s=u_status, b=u_body[:300]),
            })

        # 2. Apply enable/disable.
        e_status, e_body = _set_enabled(session_key, enabled)
        if e_status not in (200, 201):
            return _json_response(e_status, {
                "success": False,
                "error": "{a} failed: HTTP {s}: {b}".format(
                    a=("enable" if enabled else "disable"),
                    s=e_status, b=e_body[:300]),
            })

        return _json_response(200, {
            "success": True,
            "interval": str(interval),
            "enabled": enabled,
        })

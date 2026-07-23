#!/usr/bin/env python3
"""
SA-Data-Heartbeat custom REST handler.

Splunk's splunkweb /__raw/ proxy intermittently drops POST writes for some
saved searches (the "disabled=0 returned 200 but didn't persist" bug we
verified end-to-end). This handler runs INSIDE splunkd via the persist
script mechanism, talking to localhost:8089 directly — which is reliable.

Endpoint:  /services/data_heartbeat/admin
Methods:   POST action=enable_all   →  enables all 8 monitoring searches
           POST action=disable_all  →  disables all 3
           POST action=test_alert   →  fires the dispatcher with a synthetic
                                       result row for the named alert action
"""
import json
import logging
import os
import sys
import time
import urllib.parse

# Splunk bundles splunklib with the platform; persist scripts get a session
# key + a Splunkd connection without us needing pip-installed deps.
import splunk.persistconn.application as application
import splunk.rest as rest

APP_NAME = "SA-Data-Heartbeat"

# Splunk built-in capabilities that gate the destructive endpoints. The
# handler refuses requests from users that don't hold at least one of these.
#
# `edit_search_scheduler` is the right least-privilege match for toggling
# scheduled-search state (Splunk's own UI requires it). `admin_all_objects`
# is the standard catch-all that the `admin` and `sc_admin` roles hold.
# Without this gate, any authenticated user (incl. the default `user` role)
# could call our admin endpoint to enable/disable monitoring or trigger
# arbitrary outbound HTTP POSTs via the test-alert path — i.e. SSRF +
# control-plane tampering by a low-priv account.
_REQUIRED_CAPABILITIES = ("edit_search_scheduler", "admin_all_objects")
# Every scheduled search in the app (each has a cron_schedule). "Enable
# Monitoring" turns on the whole monitoring pipeline — detection, alerting,
# discovery, self-monitoring (Health Metrics + Detection Stalled), and the
# nightly backup. The CSV->KV Migration search is intentionally excluded: it
# has no cron and is a one-shot.
SEARCH_NAMES = [
    "Data Heartbeat - Source Type Monitor",
    "Data Heartbeat Alert - Flagged Sources",
    "Data Heartbeat - Auto Discovery",
    "Data Heartbeat - Health Metrics",
    "Data Heartbeat - Detection Stalled",
    "Data Heartbeat - Nightly KV Backup",
    "Data Heartbeat - Prune Deletion Tombstones",
    "Data Heartbeat - Usage Refresh",
]

LOG_PATH = os.path.join(
    os.environ.get("SPLUNK_HOME", "/opt/splunk"),
    "var", "log", "splunk", "heartbeat_admin.log",
)
logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s level=%(levelname)s %(message)s")
log = logging.getLogger("heartbeat_admin")


def _current_user_capabilities(session_key):
    """Return the capability set of the authenticated user (by session key).
    Returns an empty set if the lookup fails — we fail closed."""
    try:
        resp, content = rest.simpleRequest(
            "/services/authentication/current-context",
            sessionKey=session_key,
            getargs={"output_mode": "json"},
            method="GET",
            raiseAllErrors=False,
        )
        if int(getattr(resp, "status", 0) or 0) != 200:
            return set()
        if isinstance(content, (bytes, bytearray)):
            content = content.decode("utf-8", "ignore")
        data = json.loads(content)
        caps = (data.get("entry") or [{}])[0].get("content", {}).get("capabilities") or []
        return set(caps)
    except Exception as e:  # noqa: BLE001 — must fail closed, not crash
        # splunk.rest raises splunk.AuthenticationFailed / AuthorizationFailed /
        # SplunkdConnectionException even with raiseAllErrors=False; none of
        # them derive from the json/OS error classes. An uncaught exception
        # here kills the whole persist process — the opposite of fail-closed.
        log.warning("capability lookup failed: %s", e)
        return set()


def _is_free_license(session_key):
    """Splunk Free ships without the Auth feature: current-context returns an
    empty capability list even for admin, which would brick the capability
    gate. Free also has no RBAC to protect, so an explicit isFree check is
    the correct unbrick (only consulted when the capability list is empty)."""
    try:
        resp, content = rest.simpleRequest(
            "/services/server/info", sessionKey=session_key,
            getargs={"output_mode": "json"}, method="GET", raiseAllErrors=False,
        )
        if int(getattr(resp, "status", 0) or 0) != 200:
            return False
        if isinstance(content, (bytes, bytearray)):
            content = content.decode("utf-8", "ignore")
        info = (json.loads(content).get("entry") or [{}])[0].get("content", {})
        return bool(info.get("isFree"))
    except Exception as e:  # noqa: BLE001 — default to the strict gate
        log.warning("isFree check failed: %s", e)
        return False


def _post_search_state(session_key, name, enabled):
    """POST disabled + is_scheduled to a saved-search entity via splunkd local REST."""
    # URL-encode the name: spaces only work today because Splunk's bundled
    # httplib2 >= 0.17 percent-encodes them itself; early 8.0.x bundles don't,
    # and http.client rejects raw spaces with InvalidURL.
    path = "/servicesNS/nobody/{app}/saved/searches/{name}".format(
        app=APP_NAME, name=urllib.parse.quote(name, safe=""),
    )
    body = {
        "disabled": "0" if enabled else "1",
        "is_scheduled": "1" if enabled else "0",
    }
    # rest.simpleRequest goes through splunkd directly (port 8089), not splunkweb.
    # This is the reliable path that bypasses the proxy filter on disabled-field POSTs.
    # Returns (Response-like-object, content); we read .status off the response.
    try:
        resp, _content = rest.simpleRequest(path, sessionKey=session_key, method="POST",
                                            postargs=body, raiseAllErrors=False)
    except Exception as e:  # noqa: BLE001 — splunk.* exceptions bypass raiseAllErrors=False
        # e.g. AuthorizationFailed (403 on the entity ACL) or
        # SplunkdConnectionException — report per-search failure instead of
        # crashing the persist process mid-toggle.
        log.warning("post_search_state[%s] raised: %s", name, e)
        return False, 0
    status = int(getattr(resp, "status", 0) or 0)
    return 200 <= status < 300, status


def _do_enable_all(session_key, enabled):
    results = {}
    all_ok = True
    for name in SEARCH_NAMES:
        ok, status = _post_search_state(session_key, name, enabled)
        results[name] = {"ok": ok, "http": status}
        if not ok:
            all_ok = False
            log.warning("enable_all[%s]: http=%s", name, status)
    return all_ok, results


def _do_test_alert(session_key, action_type, target_config, splunkd_uri=""):
    """Invoke the dispatcher's slack/teams/webhook/email path with a synthetic
    row, in-process — no subprocess.

    Splunk Cloud forbids modular code from spawning child processes, so the
    previous `subprocess.run(splunk cmd python3 heartbeat_dispatch.py)` would
    have failed AppInspect's cloud_compatible tag and been rejected at
    Splunkbase submission. We import the dispatcher's per-action functions
    directly and call them inline. Same code path; no fork/exec.
    """
    # bin/ is already on sys.path inside a persistent REST handler — splunkd
    # adds it when loading the handler script. But add it defensively for
    # local test invocations.
    bin_dir = os.path.dirname(os.path.abspath(__file__))
    if bin_dir not in sys.path:
        sys.path.insert(0, bin_dir)
    try:
        import heartbeat_dispatch as hd
    except ImportError as e:
        log.error("could not import heartbeat_dispatch: %s", e)
        return False, {"error": "dispatcher import failed: {}".format(e)}

    payload = hd.build_payload(
        {
            "sourcetype": "heartbeat:test",
            "threshold_minutes": 60,
            # Realistic synthetic flagged source: seen ~65 min ago, past its 60-min
            # threshold. last_seen MUST be set (non-zero) — the digest's "Last event"
            # text keys off it; a missing/zero last_seen renders "never (no events on
            # record)" instead of a real elapsed time (see _fmt_since).
            "minutes_since_seen": 65,
            "last_seen": int(time.time()) - 3900,
            "status": "test",
            "importance": "high",
        },
        {
            "search_name": "Data Heartbeat - Test Alert",
            "fired_at": "now",
            "splunk_url": "",
        },
    )
    action_type = (action_type or "").strip().lower()
    # A test alert must return fast — it runs synchronously inside the splunkd
    # persist handler, behind the splunkweb proxy's request timeout. Use a
    # single attempt (max_retries=1): the full 3-retry + backoff budget could
    # block the handler 30-90s and blow past the proxy timeout.
    try:
        # The dispatchers take a LIST of source payloads (digest model); a test
        # alert is just a one-element digest.
        if action_type == "slack":
            ok = hd.dispatch_slack_digest([payload], target_config, max_retries=1)
        elif action_type == "teams":
            ok = hd.dispatch_teams_digest([payload], target_config, max_retries=1)
        elif action_type == "webhook":
            ok = hd.dispatch_webhook_digest([payload], target_config, max_retries=1)
        elif action_type == "email":
            # submit_timeout_s=15: this runs synchronously inside the persist
            # handler behind splunkweb's ~30s proxy window — the full 30s
            # blocking submit + 10s verify could outlive it.
            ok = hd.dispatch_email_digest([payload], target_config, session_key,
                                          splunkd_uri=splunkd_uri, max_retries=1,
                                          submit_timeout_s=15)
        else:
            return False, {"error": "unknown action_type: {}".format(action_type)}
    except Exception as e:
        log.error("test_alert exception (%s): %s", action_type, e)
        # Generic message to the caller — raw exception text leaks fs paths,
        # mgmt-port refusal, and SSL detail to the browser toast.
        return False, {"error": "dispatch failed — see heartbeat_admin.log"}
    return bool(ok), {"sent": bool(ok), "action": action_type}


class HeartbeatAdminHandler(application.PersistentServerConnectionApplication):
    """Splunk persist REST handler. Reachable at /services/data_heartbeat/admin."""

    def __init__(self, command_line, command_arg):
        pass

    def handle(self, in_string):
        # Top-level safety net: the persistconn loop has no try/except of its
        # own, so any exception escaping handle() kills the persist process
        # and the client gets an opaque 500 while splunkd respawns us.
        try:
            return self._handle(in_string)
        except Exception as e:  # noqa: BLE001
            log.error("unhandled exception in handle(): %s", e, exc_info=True)
            return self._reply(500, {"error": "internal_error"})

    def _handle(self, in_string):
        # in_string is bytes on Splunk 10.x persist handlers; json.loads handles both.
        try:
            req = json.loads(in_string) if isinstance(in_string, (str, bytes, bytearray)) else in_string
        except (json.JSONDecodeError, ValueError):
            return self._reply(400, {"error": "bad_json"})
        if not isinstance(req, dict):
            return self._reply(400, {"error": "bad_request_shape"})

        log.info("handle: top-level keys = %s", list(req.keys()))

        session_key = (req.get("session") or {}).get("authtoken") or req.get("session_key", "")
        if not session_key:
            return self._reply(401, {"error": "no_session"})

        # POST-only. Every action this handler exposes mutates scheduled-search
        # state or triggers outbound dispatch — a GET-reachable mutating
        # endpoint is CSRF-able via <img src=...>. web.conf already restricts
        # the expose to POST/OPTIONS; this rejects anything else defensively
        # and, critically, means parameters are NOT read from the query string.
        method = str(req.get("method", "")).upper()
        if method and method != "POST":
            log.warning("rejected non-POST request: method=%s", method)
            return self._reply(405, {"error": "method_not_allowed"})

        # Splunk persist handler shapes the request differently between versions.
        # Accept form (list-of-{name,value} dicts, or dict) or a top-level
        # "payload" JSON body. The query string is deliberately NOT consulted —
        # all params must arrive in the POST body so they cannot be smuggled
        # via a CSRF GET/URL.
        post = {}
        form = req.get("form")
        if isinstance(form, list):
            for kv in form:
                if isinstance(kv, dict) and "name" in kv:
                    post[kv["name"]] = kv.get("value", "")
                elif isinstance(kv, (list, tuple)) and len(kv) == 2:
                    post[kv[0]] = kv[1]
        elif isinstance(form, dict):
            post = dict(form)
        # also accept raw JSON body
        raw_payload = req.get("payload")
        if isinstance(raw_payload, str) and raw_payload:
            try:
                body_obj = json.loads(raw_payload)
                if isinstance(body_obj, dict):
                    for k, v in body_obj.items():
                        post.setdefault(k, v)
            except (json.JSONDecodeError, ValueError):
                pass

        # Log only the action and the set of parameter NAMES — never values.
        # The `target` value is a webhook URL / recipient list and several
        # callers pass it under varying keys, so allowlist instead of masking
        # one literal key.
        log.info("handle: action=%s param_keys=%s",
                 post.get("action", ""), sorted(post.keys()))
        action = post.get("action", "")

        # Capability gate. Every action this handler exposes is privileged.
        #   - enable_all / disable_all flip scheduled-search state — gated on
        #     {edit_search_scheduler, admin_all_objects}, matching Splunk's own
        #     RBAC for toggling scheduled searches.
        #   - test_alert takes a caller-supplied target URL and drives the
        #     dispatcher to POST to it — i.e. an outbound-HTTP / SSRF primitive.
        #     It therefore requires the stricter `admin_all_objects` (full
        #     admin) and is NOT available to holders of `edit_search_scheduler`
        #     alone.
        if action in ("enable_all", "disable_all", "test_alert"):
            caps = _current_user_capabilities(session_key)
            required = ({"admin_all_objects"} if action == "test_alert"
                        else _REQUIRED_CAPABILITIES)
            if not caps.intersection(required):
                # Splunk Free reports an empty capability list for every user
                # (no Auth feature) and has no RBAC to protect — allow there
                # instead of bricking the Enable Monitoring / Test Alert
                # buttons on Free or trial-expired installs.
                if caps or not _is_free_license(session_key):
                    log.warning(
                        "denied action=%s — caller lacks %s (has %d caps)",
                        action, "/".join(sorted(required)), len(caps),
                    )
                    return self._reply(403, {
                        "error": "insufficient_capability",
                        "required_any_of": sorted(required),
                    })
                log.info("capability gate bypassed: Splunk Free license (no RBAC)")

        if action == "enable_all":
            ok, results = _do_enable_all(session_key, True)
            return self._reply(200 if ok else 207, {"ok": ok, "results": results})

        if action == "disable_all":
            ok, results = _do_enable_all(session_key, False)
            return self._reply(200 if ok else 207, {"ok": ok, "results": results})

        if action == "test_alert":
            action_type = post.get("action_type", "")
            target_config = post.get("target", "")
            if not action_type or not target_config:
                return self._reply(400, {"error": "missing action_type or target"})
            # Splunk persist handlers carry the splunkd URI in the request's
            # "server" block (verified: top-level server_uri/splunk_uri keys
            # do not exist) — pass it through so the email path uses the real
            # management port rather than assuming 8089.
            splunkd_uri = (
                (req.get("server") or {}).get("rest_uri", "")
                or os.environ.get("SPLUNKD_URI", "")
            )
            ok, detail = _do_test_alert(session_key, action_type, target_config,
                                        splunkd_uri=splunkd_uri)
            return self._reply(200 if ok else 500, {"ok": ok, "detail": detail})

        return self._reply(400, {"error": "unknown action"})

    @staticmethod
    def _reply(status, body):
        return {"status": status, "payload": json.dumps(body)}

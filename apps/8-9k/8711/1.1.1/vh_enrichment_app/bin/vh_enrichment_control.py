#!/usr/bin/env python3

import json
import os
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Same bin/ directory — used here only to inherit the env-var-proxy
# disablement on splunkd loopback calls.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vh_http  # noqa: E402

try:
    import pytz as _pytz
    _PYTZ_AVAILABLE = True
except ImportError:
    _PYTZ_AVAILABLE = False


def _is_valid_tz(tz_name):
    """Return True if tz_name is a valid IANA timezone string recognized by pytz."""
    if not tz_name:
        return False
    if not _PYTZ_AVAILABLE:
        # Can't validate — accept anything that looks like a tz string.
        return bool(tz_name.strip())
    try:
        _pytz.timezone(tz_name)
        return True
    except Exception:
        return False

from splunk.persistconn.application import PersistentServerConnectionApplication


APP_NAME = "vh_enrichment_app"
DATA_COLLECTION = "vh_enrichment_kv_collection_app"
CONTROL_COLLECTION = "vh_enrichment_control_state"
CONTROL_KEY = "state"
SPLUNKD_BASE = "https://127.0.0.1:8089"
INPUT_TYPE = "vh_enrichment_modinput"
INPUT_NAME = "default"

STALE_RUN_SECONDS = 600  # treat a running/queued state as stale if no heartbeat for 10 min


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _get_query_param(query, key):
    """Extract a single query-string value from the Splunk REST handler request.

    Splunk's PersistentServerConnectionApplication delivers request["query"]
    as a list of [key, value] pairs, e.g. [["time_hhmm", "14:30"]], NOT as
    a plain dict.  This function handles all three shapes that can appear:
      - list of [k, v] pairs  (normal Splunk delivery)
      - dict                  (defensive fallback, should not occur in practice)
      - None / missing        (no query string at all)
    Returns the first matching value as a string, or "" if not found.
    """
    if not query:
        return ""
    if isinstance(query, dict):
        return str(query.get(key) or "")
    if isinstance(query, list):
        for item in query:
            try:
                k, v = item[0], item[1]
                if k == key:
                    return str(v) if v is not None else ""
            except (IndexError, TypeError):
                continue
    return ""


def splunkd_request(session_key, method, path, data=None, timeout=60):
    url = f"{SPLUNKD_BASE}{path}"
    headers = {
        "Authorization": f"Splunk {session_key}",
    }

    payload = None
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=url,
        data=payload,
        headers=headers,
        method=method,
    )

    context = ssl.create_default_context()
    context.load_verify_locations(cafile=os.path.join(os.environ.get("SPLUNK_HOME", ""), "etc/auth/cacert.pem"))
    context.check_hostname = False

    try:
        # splunkd loopback — proxy_cfg=None so HTTP_PROXY env vars and any
        # configured corporate proxy are explicitly bypassed.
        with vh_http.urlopen(request, context=context, timeout=timeout,
                             proxy_cfg=None) as response:
            body = response.read().decode("utf-8")
            return response.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return e.code, body


def get_control_state(session_key):
    path = (
        f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/"
        f"{CONTROL_COLLECTION}/{CONTROL_KEY}"
    )
    status, body = splunkd_request(session_key, "GET", path)

    if status == 200:
        state = json.loads(body)
        if state.get("run_status") in ("running", "queued") and _is_run_stale(state):
            state["run_status"] = "failed"
            state["run_error"] = "Stale run detected (no active process)"
            state["run_completed_at"] = utc_now()
            try:
                save_control_state(session_key, state)
            except Exception:
                pass
        return state

    if status == 404:
        return {
            "_key": CONTROL_KEY,
            "last_action": "initialized",
            "updated_at": utc_now(),
        }

    raise RuntimeError(f"Failed to read control state: HTTP {status} {body}")


def save_control_state(session_key, state_doc):
    state_doc["_key"] = CONTROL_KEY
    path = (
        f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/"
        f"{CONTROL_COLLECTION}/batch_save"
    )
    status, body = splunkd_request(session_key, "POST", path, [state_doc])

    if status not in (200, 201):
        raise RuntimeError(f"Failed to save control state: HTTP {status} {body}")


def clear_kv_store(session_key):
    path = (
        f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/"
        f"{DATA_COLLECTION}"
    )
    try:
        # Use a short timeout so the full handler returns well within
        # SplunkWeb's 30-second proxy timeout (splunkdConnectionTimeout).
        # Splunk processes large-collection DELETEs asynchronously; a
        # socket timeout here means the delete is in progress, not failed.
        status, body = splunkd_request(session_key, "DELETE", path, timeout=20)
        if status not in (200, 201):
            raise RuntimeError(f"Failed to clear KV Store: HTTP {status} {body}")
    except RuntimeError:
        raise
    except Exception:
        # DELETE on a large collection exceeds the read timeout — treat as success.
        pass

    state = get_control_state(session_key)
    state["last_action"] = "clear_kv"
    state["updated_at"] = utc_now()
    # Reset all run/progress fields so stale state doesn't linger after a clear
    state["run_status"] = "idle"
    state["run_started_at"] = ""
    state["run_completed_at"] = ""
    state["run_error"] = ""
    state["current_phase"] = ""
    state["records_inserted_so_far"] = ""
    state["last_record_count"] = ""
    state["last_heartbeat_at"] = ""
    save_control_state(session_key, state)
    return state


def get_api_base_url(session_key):
    """Return the resolved canonical API base URL via vh_http.load_api_base.

    Uses the same KV → default precedence as the modular input and the
    `vhipmetadata` search command, so this pre-flight check on /run_now
    agrees with the runtime that will actually execute the ingestion.
    Returns None only if the loader returns an empty string — defensive;
    not possible with the shipped default.
    """
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=os.path.join(
        os.environ.get("SPLUNK_HOME", ""), "etc/auth/cacert.pem"))
    context.check_hostname = False
    try:
        api_base = vh_http.load_api_base(
            session_key=session_key,
            splunkd_base=SPLUNKD_BASE,
            ssl_context=context,
            app_name=APP_NAME,
        )
    except Exception as e:
        print(f"get_api_base_url: load_api_base failed: {e}", file=sys.stderr)
        return None
    return api_base.url or None


def _is_run_stale(state):
    """True if run_status=running but last_heartbeat_at is older than STALE_RUN_SECONDS."""
    last_hb = state.get("last_heartbeat_at", "")
    if not last_hb:
        return True
    try:
        hb_dt = datetime.fromisoformat(last_hb.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - hb_dt).total_seconds()
        return age > STALE_RUN_SECONDS
    except Exception:
        return True


class VHEnrichmentControlHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super().__init__()
        self.command_line = command_line
        self.command_arg = command_arg

    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            method = request.get("method", "GET").upper()
            path_info = request.get("path_info", "")
            session_key = request["session"]["authtoken"]

            if method != "POST":
                return {
                    "status": 405,
                    "payload": json.dumps({"success": False, "error": "POST only"}),
                    "headers": {"Content-Type": "application/json"},
                }

            action = path_info.rstrip("/").split("/")[-1]

            # Note: enable/disable of the modular input is owned by
            # [vh_enrichment_modinput://default] disabled in inputs.conf,
            # written by the Setup UI checkbox.  This handler intentionally
            # does NOT expose start/stop actions — they would create a
            # second source of truth that can drift from the splunkd
            # execution gate.  Mid-flight cancellation is handled by
            # `stop_run` below, which writes stop_requested into KV.

            if action == "status":
                state = get_control_state(session_key)

            elif action == "clear_kv":
                state = get_control_state(session_key)
                if state.get("run_status") in ("running", "queued"):
                    if not _is_run_stale(state):
                        return {
                            "status": 409,
                            "payload": json.dumps({
                                "success": False,
                                "error": "Cannot clear KV Store while ingestion is running",
                            }),
                            "headers": {"Content-Type": "application/json"},
                        }
                    state["run_status"] = "failed"
                    state["run_error"] = "Stale run detected (no active process)"
                    state["run_completed_at"] = utc_now()
                    try:
                        save_control_state(session_key, state)
                    except Exception as e:
                        print(f"clear_kv: could not mark stale run failed: {e}", file=sys.stderr)
                state = clear_kv_store(session_key)

            elif action == "run_now":
                state = get_control_state(session_key)

                if state.get("run_status") in ("running", "queued"):
                    if not _is_run_stale(state):
                        return {
                            "status": 409,
                            "payload": json.dumps({
                                "success": False,
                                "error": "already_running",
                                "state": state,
                            }),
                            "headers": {"Content-Type": "application/json"},
                        }

                    # Stale: the modular input process died without writing a
                    # terminal state.  Mark it failed before queuing a new run.
                    print(
                        f"Stale run detected "
                        f"(last_heartbeat={state.get('last_heartbeat_at')}), "
                        "marking as failed and restarting.",
                        file=sys.stderr,
                    )
                    state["run_status"] = "failed"
                    state["run_error"] = (
                        "Run was interrupted — stale heartbeat detected on restart. "
                        f"Last heartbeat: {state.get('last_heartbeat_at', 'unknown')}"
                    )
                    state["run_completed_at"] = utc_now()
                    try:
                        save_control_state(session_key, state)
                    except Exception as e:
                        print(f"run_now: could not mark stale run failed: {e}", file=sys.stderr)

                if not get_api_base_url(session_key):
                    return {
                        "status": 400,
                        "payload": json.dumps({
                            "success": False,
                            "error": "API base URL not configured. Please complete setup.",
                        }),
                        "headers": {"Content-Type": "application/json"},
                    }

                # Signal the modular input to run. It polls for run_requested=true
                # and executes ingestion in its own stable process.
                state["run_requested"] = True
                state["run_status"] = "queued"
                state["run_started_at"] = utc_now()
                state["run_completed_at"] = ""
                state["run_error"] = ""
                state["current_phase"] = "queued"
                state["records_inserted_so_far"] = ""
                state["last_record_count"] = state.get("last_record_count", "")
                state["last_heartbeat_at"] = utc_now()
                state["last_action"] = "run_now"
                state["updated_at"] = utc_now()
                save_control_state(session_key, state)

            elif action == "set_schedule":
                # Query params: time_hhmm=HH:MM, tz=IANA_timezone_name
                # request["query"] arrives as a list of [k,v] pairs from Splunk.
                raw_query = request.get("query")
                time_hhmm = _get_query_param(raw_query, "time_hhmm").strip()
                tz_name   = _get_query_param(raw_query, "tz").strip() or "UTC"

                # Validate HH:MM
                valid_time = False
                try:
                    parts = time_hhmm.split(":")
                    if len(parts) == 2:
                        hh, mm = int(parts[0]), int(parts[1])
                        valid_time = 0 <= hh <= 23 and 0 <= mm <= 59
                except Exception:
                    valid_time = False
                if not valid_time:
                    return {
                        "status": 400,
                        "payload": json.dumps({
                            "success": False,
                            "error": (
                                f"Invalid time '{time_hhmm}'. "
                                "Expected HH:MM in 24-hour format (e.g. 14:30)."
                            ),
                        }),
                        "headers": {"Content-Type": "application/json"},
                    }

                # Validate timezone
                if not _is_valid_tz(tz_name):
                    return {
                        "status": 400,
                        "payload": json.dumps({
                            "success": False,
                            "error": (
                                f"Unknown timezone '{tz_name}'. "
                                "Use a valid IANA timezone name (e.g. America/New_York)."
                            ),
                        }),
                        "headers": {"Content-Type": "application/json"},
                    }

                state = get_control_state(session_key)
                state["schedule_enabled"] = True
                state["scheduled_time_hhmm"] = time_hhmm
                state["schedule_tz"] = tz_name
                state["last_action"] = "set_schedule"
                state["updated_at"] = utc_now()
                save_control_state(session_key, state)

            elif action == "stop_run":
                state = get_control_state(session_key)
                run_status = state.get("run_status", "")

                if run_status == "queued":
                    # The modinput hasn't started yet — cancel the request directly.
                    # Also set stop_requested=True to handle the narrow race where the
                    # modinput process read run_requested=True just before we cleared it.
                    state["run_requested"] = False
                    state["run_status"] = "stopped"
                    state["run_completed_at"] = utc_now()
                    state["run_error"] = ""
                    state["current_phase"] = "stopped"
                    state["stop_requested"] = False
                    state["last_action"] = "stop_run"
                    state["updated_at"] = utc_now()
                    save_control_state(session_key, state)

                elif run_status == "running":
                    # Signal the active modinput to stop cleanly.
                    # It will detect this within the next STOP_CHECK_INTERVAL seconds,
                    # finish the current batch, and write run_status=stopped.
                    state["stop_requested"] = True
                    state["last_action"] = "stop_run"
                    state["updated_at"] = utc_now()
                    save_control_state(session_key, state)

                else:
                    return {
                        "status": 409,
                        "payload": json.dumps({
                            "success": False,
                            "error": f"No active run to stop (run_status='{run_status}').",
                            "state": state,
                        }),
                        "headers": {"Content-Type": "application/json"},
                    }

            elif action == "disable_schedule":
                state = get_control_state(session_key)
                state["schedule_enabled"] = False
                state["scheduled_time_hhmm"] = ""
                state["schedule_tz"] = ""
                state["last_scheduled_run_date"] = ""
                state["last_action"] = "disable_schedule"
                state["updated_at"] = utc_now()
                save_control_state(session_key, state)

            else:
                return {
                    "status": 400,
                    "payload": json.dumps({"success": False, "error": f"Unknown action: {action}"}),
                    "headers": {"Content-Type": "application/json"},
                }

            return {
                "status": 200,
                "payload": json.dumps({"success": True, "action": action, "state": state}),
                "headers": {"Content-Type": "application/json"},
            }

        except Exception as e:
            return {
                "status": 500,
                "payload": json.dumps({"success": False, "error": str(e)}),
                "headers": {"Content-Type": "application/json"},
            }

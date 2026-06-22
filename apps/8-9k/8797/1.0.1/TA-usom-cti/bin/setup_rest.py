#!/usr/bin/env python
# Copyright 2026 DataVira Teknoloji A.Ş.
# Licensed under the Apache License, Version 2.0
"""Persistent REST handler backing the TA-usom-cti setup view.

GET  /services/usom_ti/setup -> returns the current [usom_ti://default]
                                inputs.conf stanza
POST /services/usom_ti/setup -> updates the same stanza (and toggles
                                `disabled` based on the `enabled` boolean)

Uses splunk.rest.simpleRequest (always bundled with Splunk Enterprise)
rather than the SDK splunklib.client, which is NOT shipped with stock
Splunk and would otherwise require vendoring into bin/lib/.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import traceback
_BIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _BIN_DIR not in sys.path:
    sys.path.insert(0, _BIN_DIR)


def _configure_logging():
    log = logging.getLogger("ta_usom_cti.setup")
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    splunk_home = os.environ.get("SPLUNK_HOME", "")
    log_dir = os.path.join(splunk_home, "var", "log", "splunk") if splunk_home else "."
    try:
        os.makedirs(log_dir, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "ta_usom_cti.log"),
            maxBytes=5_000_000, backupCount=3, encoding="utf-8",
        )
    except OSError:
        handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    ))
    log.addHandler(handler)
    return log


LOG = _configure_logging()

try:
    from splunk.persistconn.application import PersistentServerConnectionApplication
    import splunk  # for splunk.ResourceNotFound, splunk.AuthorizationFailed, etc.
    import splunk.rest as splunk_rest
except Exception:
    LOG.exception("setup_rest: import failed")
    raise


# APP_NAME is derived from __file__ so the handler works under any folder
# Splunk installed the app as.
APP_NAME = os.path.basename(os.path.dirname(_BIN_DIR))
INPUT_KIND = "usom_ti"
INPUT_NAME = "default"

# /data/inputs/<kind>/<name> is the endpoint Settings > Data inputs uses;
# a default-only stanza GETs 404 so the Save branch creates via the
# collection endpoint, otherwise updates the stanza directly.
INPUT_ENDPOINT = "/servicesNS/nobody/{app}/data/inputs/{kind}/{name}".format(
    app=APP_NAME, kind=INPUT_KIND, name=INPUT_NAME,
)
INPUT_COLLECTION = "/servicesNS/nobody/{app}/data/inputs/{kind}".format(
    app=APP_NAME, kind=INPUT_KIND,
)

DEBUG_FIELD = "setup_debug"

WRITABLE_FIELDS = (
    "criticality_threshold",
    "types",
    "interval",
    "api_base_url",
    "request_delay_seconds",
    "http_proxy",
    "stats_index",
    DEBUG_FIELD,
)


class _LogLevelState:
    """Module-level toggle driven by the setup_debug stanza field.
    Persistent REST handlers stay resident between requests, so flipping
    this once persists for the life of the handler process."""
    debug = False


def _apply_log_level():
    LOG.setLevel(logging.DEBUG if _LogLevelState.debug else logging.WARNING)

# Enterprise Security `threatlist://` stanzas managed by this setup. Each
# corresponds to one lookup CSV and one toggle in the setup view. The keys
# here are also the JSON keys read/written over the REST wire.
ES_THREATLISTS = (
    "usom_ip_intel",
    "usom_ip6_intel",
    "usom_ip6net_intel",
    "usom_domain_intel",
    "usom_url_intel",
)


# Mirrors default/inputs.conf so the form is never empty even if the
# configs/conf-inputs read fails for some reason.
SHIPPED_DEFAULTS = {
    "criticality_threshold": "7",
    "types": "ip,ip6,ip6net,domain,url",
    "interval": "14400",
    "api_base_url": "https://siberguvenlik.gov.tr/api/address/index",
    "request_delay_seconds": "5",
    "http_proxy": "",
    "stats_index": "_internal",
    DEBUG_FIELD: "false",
}


def _resp(status, body):
    try:
        payload = json.dumps(body, ensure_ascii=True)
    except (TypeError, ValueError):
        payload = json.dumps({"error": "unserializable response body"})
        status = 500
    return {"status": int(status), "payload": payload}


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return False


def _decode_post_body(args):
    """POST body arrives either as a JSON string in args['payload'] (when
    passPayload=true) or as form pairs in args['form']. Accept both.
    """
    raw_payload = args.get("payload")
    if raw_payload:
        try:
            decoded = json.loads(raw_payload)
            if isinstance(decoded, dict):
                return decoded
        except (TypeError, ValueError):
            pass
    form = args.get("form") or []
    out = {}
    for pair in form:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            out[pair[0]] = pair[1]
    return out


def _splunkd_call(path, session_key, method="GET", postargs=None):
    """Wrapper around splunk.rest.simpleRequest returning (status, parsed_json).
    parsed_json is None for non-JSON or empty responses.

    simpleRequest raises splunk.* exceptions on certain HTTP statuses (notably
    ResourceNotFound for 404 and AuthorizationFailed for 401) even with
    raiseAllErrors=False, so we translate those back into status codes the
    caller can branch on. It also calls .items() on postargs, so we hand it
    a dict -- a list of tuples breaks with "'list' object has no attribute
    'items'" on this Splunk version.
    """
    if isinstance(postargs, list):
        postargs = dict(postargs)
    try:
        response, content = splunk_rest.simpleRequest(
            path,
            sessionKey=session_key,
            method=method,
            getargs={"output_mode": "json"},
            postargs=postargs or None,
            raiseAllErrors=False,
        )
    except splunk.ResourceNotFound:
        LOG.debug("splunkd %s %s -> 404", method, path)
        return 404, None
    except splunk.AuthorizationFailed:
        LOG.warning("splunkd %s %s -> 403 (authz)", method, path)
        return 403, None
    except splunk.AuthenticationFailed:
        LOG.warning("splunkd %s %s -> 401 (authn)", method, path)
        return 401, None
    status = int(getattr(response, "status", 0) or 0)
    parsed = None
    text = ""
    if content:
        try:
            text = content.decode("utf-8") if isinstance(content, (bytes, bytearray)) else content
            parsed = json.loads(text) if text else None
        except (UnicodeDecodeError, ValueError):
            parsed = None
    if status >= 400:
        LOG.warning("splunkd %s %s -> %d body=%s",
                    method, path, status, (text or "")[:500])
    else:
        LOG.debug("splunkd %s %s -> %d", method, path, status)
    return status, parsed


def _entry_content(parsed):
    """Pull the single entry's content dict out of a Splunk REST list response."""
    if not parsed:
        return None
    entries = parsed.get("entry") or []
    if not entries:
        return None
    return entries[0].get("content") or {}


def _local_inputs_conf_path():
    return os.path.join(os.path.dirname(_BIN_DIR), "local", "inputs.conf")


# The threatlist:// modular input kind is registered by SA-ThreatIntelligence
# (Enterprise Security). When ES is absent the kind is unknown, so
# /data/inputs/threatlist/* returns 404. We therefore manage the disabled
# flag of our shipped threatlist stanzas by editing local/inputs.conf
# directly -- correct whether ES is installed or not, and picked up by ES
# once it is.
def _read_threatlist_disabled(stanza_name):
    """Return True iff the stanza's disabled flag in local/inputs.conf
    resolves to "off". Missing entry => True (matches the shipped default
    in default/inputs.conf)."""
    path = _local_inputs_conf_path()
    if not os.path.exists(path):
        return True
    target = "[threatlist://" + stanza_name + "]"
    in_section = False
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    in_section = (line == target)
                    continue
                if in_section and "=" in line:
                    k, _, v = line.partition("=")
                    if k.strip() == "disabled":
                        return _coerce_bool(v.strip())
    except OSError as exc:
        LOG.warning("could not read %s: %s", path, exc)
    return True


def _write_threatlist_disabled(stanza_name, disabled):
    """Set the disabled flag of [threatlist://<stanza_name>]. See
    _write_threatlist_kv for the file-edit mechanics."""
    return _write_threatlist_kv(stanza_name, {"disabled": "1" if disabled else "0"})


def _write_threatlist_kv(stanza_name, kv):
    """Apply key=value pairs to [threatlist://<stanza_name>] in
    local/inputs.conf. Creates the file/stanza/key if needed; preserves
    every other line and stanza. Returns True on success.

    Used both to toggle `disabled` and to keep `interval` in lockstep
    with the USOM input's poll cadence -- ES re-reads each threatlist
    on its own schedule, so a stale interval = the indexed KV store
    lags the lookup it's supposed to mirror.
    """
    if not kv:
        return True
    path = _local_inputs_conf_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except OSError as exc:
        LOG.error("could not create local/ dir: %s", exc)
        return False

    target_header = "[threatlist://" + stanza_name + "]"

    lines = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError as exc:
            LOG.error("could not read %s: %s", path, exc)
            return False

    section_start = None
    section_end = len(lines)
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped == target_header:
            section_start = i
        elif section_start is not None and stripped.startswith("[") and stripped.endswith("]"):
            section_end = i
            break

    if section_start is None:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append(target_header)
        for k, v in kv.items():
            lines.append(k + " = " + str(v))
    else:
        for key, value in kv.items():
            replaced = False
            for j in range(section_start + 1, section_end):
                stripped = lines[j].strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" in stripped:
                    k, _, _ = stripped.partition("=")
                    if k.strip() == key:
                        lines[j] = key + " = " + str(value)
                        replaced = True
                        break
            if not replaced:
                lines.insert(section_end, key + " = " + str(value))
                section_end += 1

    body = "\n".join(lines)
    if not body.endswith("\n"):
        body += "\n"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
    except OSError as exc:
        LOG.error("could not write %s: %s", path, exc)
        return False
    return True


def _reload_inputs_conf(session_key):
    """Ask splunkd to re-read inputs.conf for this app. Uses the generic
    admin reload endpoint, which works regardless of whether any specific
    input kind (e.g. threatlist://) is registered."""
    for path in (
        "/servicesNS/nobody/" + APP_NAME + "/admin/conf-inputs/_reload",
        "/services/admin/conf-inputs/_reload",
    ):
        st, _ = _splunkd_call(path, session_key, method="POST")
        if st < 400:
            return True
    return False


def _read_stanza(session_key):
    """Return the input stanza if Splunk has it (default + local merged),
    falling back to SHIPPED_DEFAULTS if /data/inputs/<kind>/<name> 404s
    -- which happens until the user first saves and a local override is
    materialised. Always populates every WRITABLE_FIELDS key so the form
    is never blank.
    """
    status, parsed = _splunkd_call(INPUT_ENDPOINT, session_key, method="GET")
    has_content = status < 400
    content = _entry_content(parsed) if has_content else {}
    if content is None:
        content = {}

    out = {
        "exists": has_content,
        "disabled": _coerce_bool(content.get("disabled", True)),
    }
    for k in WRITABLE_FIELDS:
        raw = content.get(k)
        if raw is None or raw == "":
            raw = SHIPPED_DEFAULTS.get(k, "")
        out[k] = str(raw)

    # Refresh the persistent log level from the stanza state so the rest
    # of the trace logs in this call match whatever the operator has set.
    _LogLevelState.debug = _coerce_bool(out.get(DEBUG_FIELD, False))
    _apply_log_level()

    if not has_content:
        LOG.debug("setup_rest: data/inputs GET returned %s; "
                  "form will show shipped defaults", status)

    out["es_push"] = {
        tl: not _read_threatlist_disabled(tl) for tl in ES_THREATLISTS
    }
    return out


def _write_stanza(session_key, payload):
    # Apply debug toggle from this request before we log anything else.
    if DEBUG_FIELD in payload:
        _LogLevelState.debug = _coerce_bool(payload[DEBUG_FIELD])
        _apply_log_level()

    update_args = [(k, str(payload[k])) for k in WRITABLE_FIELDS if k in payload]

    # Probe to decide create-vs-update. data/inputs/<kind>/<name> only
    # shows stanzas that have been written into local/, so a 404 here
    # means "the user is saving for the first time -- create".
    probe_status, _ = _splunkd_call(INPUT_ENDPOINT, session_key, method="GET")

    if probe_status == 404:
        # Splunk requires `name` for collection POST. If the user didn't
        # change anything from the defaults, still send the defaults so
        # something lands in local/.
        create_args = [("name", INPUT_NAME)]
        for k in WRITABLE_FIELDS:
            if k in payload:
                create_args.append((k, str(payload[k])))
            elif SHIPPED_DEFAULTS.get(k):
                create_args.append((k, SHIPPED_DEFAULTS[k]))
        LOG.debug("setup_rest: POST %s create with %d field(s)",
                  INPUT_COLLECTION, len(create_args))
        st, parsed = _splunkd_call(
            INPUT_COLLECTION, session_key, method="POST", postargs=create_args,
        )
        if st >= 400:
            raise RuntimeError(
                "create failed (" + str(st) + "): " + json.dumps(parsed)
            )
    elif probe_status < 400:
        if update_args:
            LOG.debug("setup_rest: POST %s update with %d field(s)",
                      INPUT_ENDPOINT, len(update_args))
            st, parsed = _splunkd_call(
                INPUT_ENDPOINT, session_key, method="POST", postargs=update_args,
            )
            if st >= 400:
                raise RuntimeError(
                    "update failed (" + str(st) + "): " + json.dumps(parsed)
                )
    else:
        raise RuntimeError("probe failed: " + str(probe_status))

    if "enabled" in payload:
        action = "enable" if _coerce_bool(payload.get("enabled")) else "disable"
        LOG.debug("setup_rest: POST %s/%s", INPUT_ENDPOINT, action)
        st, parsed = _splunkd_call(
            INPUT_ENDPOINT + "/" + action, session_key, method="POST",
        )
        if st >= 400:
            LOG.warning("setup_rest: %s returned %s (non-fatal): %s",
                        action, st, parsed)

    es_push = payload.get("es_push") or {}
    touched = False
    if isinstance(es_push, dict) and es_push:
        for tl, wanted in es_push.items():
            if tl not in ES_THREATLISTS:
                continue
            want_enabled = _coerce_bool(wanted)
            current_enabled = not _read_threatlist_disabled(tl)
            if want_enabled == current_enabled:
                continue
            ok = _write_threatlist_disabled(tl, disabled=not want_enabled)
            LOG.debug("setup_rest: threatlist %s -> %s (ok=%s)",
                      tl, "enabled" if want_enabled else "disabled", ok)
            if ok:
                touched = True

    # Keep every threatlist:// interval in lockstep with the usom_ti
    # input's poll interval. ES re-reads its threat lists on whatever
    # interval each stanza specifies, so a drift here means the
    # KV-store mirror lags behind the lookup CSV by however long the
    # difference is. Sync runs on every save (cheap: a single regex
    # replace per stanza in local/inputs.conf).
    if "interval" in payload:
        try:
            usom_interval = str(int(payload["interval"]))
            for tl in ES_THREATLISTS:
                if _write_threatlist_kv(tl, {"interval": usom_interval}):
                    touched = True
        except (TypeError, ValueError):
            pass

    if touched:
        _reload_inputs_conf(session_key)

    return _read_stanza(session_key)


class SetupHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None):  # noqa: ARG002
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            return self._handle_inner(in_string)
        except Exception:
            LOG.exception("setup_rest: unhandled error in handle()")
            return _resp(500, {"error": "internal error; see ta_usom_cti.log"})

    def _handle_inner(self, in_string):
        try:
            args = json.loads(in_string) if in_string else {}
        except (TypeError, ValueError) as exc:
            LOG.error("setup_rest: invalid request body: %s", exc)
            return _resp(400, {"error": "invalid request body"})

        # Some Splunk versions populate args["method"], others don't. If the
        # explicit method is missing or empty, fall back to inferring from
        # the request shape: a non-empty payload or form body means POST.
        raw_method = args.get("method") or ""
        has_body = bool(args.get("payload")) or bool(args.get("form"))
        if not raw_method:
            method = "POST" if has_body else "GET"
        else:
            method = str(raw_method).upper()

        session_key = (args.get("session") or {}).get("authtoken")
        LOG.debug(
            "setup_rest: %s request (raw_method=%r has_body=%s args_keys=%s) "
            "session=%s",
            method, raw_method, has_body, sorted(args.keys()),
            "present" if session_key else "MISSING",
        )

        if not session_key:
            return _resp(401, {"error": "missing session token"})

        if method == "GET":
            try:
                return _resp(200, _read_stanza(session_key))
            except Exception as exc:
                LOG.exception("setup_rest: read_stanza failed")
                return _resp(500, {"error": "read failed: " + str(exc)})

        if method == "POST":
            payload = _decode_post_body(args)
            LOG.debug("setup_rest: POST body keys=%s", sorted(payload.keys()))
            try:
                return _resp(200, _write_stanza(session_key, payload))
            except Exception as exc:
                LOG.exception("setup_rest: write_stanza failed")
                return _resp(500, {"error": "write failed: " + str(exc)})

        return _resp(405, {"error": "method " + method + " not allowed"})


_apply_log_level()
LOG.debug("setup_rest: module loaded")

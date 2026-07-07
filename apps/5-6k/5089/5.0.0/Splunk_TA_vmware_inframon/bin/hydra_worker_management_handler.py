#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.

import datetime
import json
import os
import re
import sys
from urllib.parse import parse_qs, quote_plus

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.rest import simpleRequest

try:
    _TA_BIN_DIR = make_splunkhome_path(["etc", "apps", "Splunk_TA_vmware_inframon", "bin"])
except Exception:
    _TA_BIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _TA_BIN_DIR not in sys.path:
    sys.path.append(_TA_BIN_DIR)

try:
    _HYDRA_BIN_DIR = make_splunkhome_path(["etc", "apps", "SA-Hydra-inframon", "bin"])
except Exception:
    _HYDRA_BIN_DIR = None
if _HYDRA_BIN_DIR and _HYDRA_BIN_DIR not in sys.path:
    sys.path.append(_HYDRA_BIN_DIR)

from hydra_inframon.models import HydraMetadataStanza, SplunkStoredCredential
from rest_utility import setup_logger

logger = setup_logger(
    log_name="splunk_for_vmware_setup.log",
    logger_name="hydra_worker_management",
)

_APP = "Splunk_TA_vmware_inframon"
_INPUT_TYPE = "ta_vmware_collection_worker_inframon"
_VALID_ACTIONS = frozenset(["enable", "disable"])
_VALID_METADATA_KEY_RE = re.compile(r"^metadata_[A-Za-z0-9_.:-]+$")
_VALID_INPUT_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
_VALID_SESSION_NAME_RE = re.compile(r"^[^\r\n/]+$")
_DATETIME_TAG = "__hydra_type"
_DATETIME_VALUE = "datetime"


def _first(value, default=None):
    if isinstance(value, list):
        return value[0] if value else default
    if value is None:
        return default
    return value


def _extract_args(request):
    args = {}

    form = request.get("form", {})
    if isinstance(form, dict):
        for key, value in form.items():
            args[key] = _first(value)

    query = request.get("query", {})
    if isinstance(query, dict):
        for key, value in query.items():
            args[key] = _first(value)
    elif isinstance(query, str) and query:
        for key, value in parse_qs(query, keep_blank_values=True).items():
            args[key] = _first(value)

    payload = request.get("payload", "")
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if isinstance(payload, str) and payload:
        form_args = parse_qs(payload, keep_blank_values=True)
        for key, value in form_args.items():
            args[key] = _first(value)
        if not form_args and payload.startswith("{"):
            try:
                json_payload = json.loads(payload)
                if isinstance(json_payload, dict):
                    args.update(json_payload)
            except Exception:
                pass

    return args


def _response(status, message, payload=None):
    body = {
        "status": int(status),
        "message": message,
        "payload": payload if payload is not None else {},
    }
    return {
        "status": int(status),
        "headers": {"Content-Type": "application/json"},
        "payload": json.dumps(body),
    }


def _normalized_route(path_info):
    if path_info is None:
        return ""
    if isinstance(path_info, bytes):
        path_info = path_info.decode("utf-8")
    return str(path_info).strip().strip("/")


def _validate_input_exists(session_key, input_name):
    path = "/servicesNS/nobody/{app}/data/inputs/{input_type}/{input_name}".format(
        app=_APP,
        input_type=_INPUT_TYPE,
        input_name=input_name,
    )
    try:
        rsp, _ = simpleRequest(
            path,
            method="GET",
            sessionKey=session_key,
            getargs={"output_mode": "json"},
            raiseAllErrors=False,
        )
        status = int(getattr(rsp, "status", 0))
        if status == 200:
            return True, None
        if status == 404:
            return False, "input stanza not found: {input_type}/{input_name}".format(
                input_type=_INPUT_TYPE, input_name=input_name
            )
        return False, "unexpected status {status} while validating input stanza".format(status=status)
    except Exception as exc:
        return False, "error validating input stanza: {error}".format(error=str(exc))


def _toggle_input(session_key, input_name, action):
    path = "/servicesNS/nobody/{app}/data/inputs/{input_type}/{input_name}/{action}".format(
        app=_APP,
        input_type=_INPUT_TYPE,
        input_name=input_name,
        action=action,
    )
    rsp, content = simpleRequest(
        path,
        method="POST",
        sessionKey=session_key,
        raiseAllErrors=False,
    )
    return int(getattr(rsp, "status", 0)), content


def _parse_datetime(value):
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError("invalid datetime value")


def _decode_metadata_value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_decode_metadata_value(item) for item in value]
    if isinstance(value, dict):
        if value.get(_DATETIME_TAG) is not None:
            if set(value.keys()) != set([_DATETIME_TAG, "value"]) or value[_DATETIME_TAG] != _DATETIME_VALUE:
                raise ValueError("unsupported metadata type tag")
            return _parse_datetime(value["value"])
        decoded = {}
        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise ValueError("metadata object keys must be strings")
            decoded[key] = _decode_metadata_value(nested_value)
        return decoded
    raise ValueError("unsupported metadata value type")


def _decode_metadata_entries(raw_entries):
    if isinstance(raw_entries, str):
        raw_entries = json.loads(raw_entries)
    if not isinstance(raw_entries, dict) or not raw_entries:
        raise ValueError("entries must be a non-empty object")
    decoded_entries = {}
    for metadata_key, metadata_value in raw_entries.items():
        if not isinstance(metadata_key, str) or not _VALID_METADATA_KEY_RE.match(metadata_key):
            raise ValueError("invalid metadata key")
        decoded_entries[metadata_key] = _decode_metadata_value(metadata_value)
    return decoded_entries


def _update_worker_input(session_key, args):
    input_name = args.get("input_name", "").strip()
    action = args.get("action", "").strip().lower()
    capabilities = args.get("capabilities", "").strip()
    log_level = args.get("log_level", "").strip()

    if not input_name:
        return _response(400, "input_name is required")
    if not _VALID_INPUT_NAME_RE.match(input_name):
        return _response(400, "input_name contains invalid characters")
    if action not in _VALID_ACTIONS:
        return _response(400, "action must be one of: enable, disable")

    logger.info("Worker input request received input_name=%s action=%s", input_name, action)

    exists, reason = _validate_input_exists(session_key, input_name)
    if not exists:
        logger.warning("Worker management input validation failed input_name=%s reason=%s", input_name, reason)
        return _response(404, reason)

    if action == "enable" and (capabilities or log_level):
        config_path = "/servicesNS/nobody/{app}/data/inputs/{input_type}/{input_name}".format(
            app=_APP,
            input_type=_INPUT_TYPE,
            input_name=input_name,
        )
        postargs = {}
        if capabilities:
            postargs["capabilities"] = capabilities
        if log_level:
            postargs["log_level"] = log_level
        rsp, _ = simpleRequest(
            config_path,
            method="POST",
            sessionKey=session_key,
            postargs=postargs,
            raiseAllErrors=False,
        )
        if int(getattr(rsp, "status", 0)) != 200:
            return _response(500, "failed to update worker input configuration")

    http_status, _ = _toggle_input(session_key, input_name, action)
    if http_status == 200:
        logger.info("Worker input toggled successfully input_name=%s action=%s", input_name, action)
        return _response(200, "ok", {"input_name": input_name, "action": action})
    logger.error("Worker input toggle failed input_name=%s action=%s status=%s", input_name, action, http_status)
    return _response(http_status or 500, "input toggle returned status {status}".format(status=http_status))


def _upsert_credential(session_key, args):
    realm = args.get("realm", "")
    username = args.get("username", "")
    password = args.get("password", "")
    if not realm:
        return _response(400, "realm is required")
    if not username:
        return _response(400, "username is required")
    if password in (None, ""):
        return _response(400, "password is required")

    logger.info("Worker credential upsert request received realm=%s username=%s", realm, username)

    credential = SplunkStoredCredential(_APP, "nobody", username, sessionKey=session_key)
    credential.realm = realm
    credential.username = username
    credential.password = password
    if not credential.passive_save():
        logger.error("Worker credential upsert failed realm=%s username=%s", realm, username)
        return _response(500, "failed to save credential")
    logger.info("Worker credential upsert succeeded realm=%s username=%s", realm, username)
    return _response(200, "ok", {"realm": realm, "username": username})


def _replace_metadata(session_key, args):
    try:
        decoded_entries = _decode_metadata_entries(args.get("entries"))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return _response(400, "invalid metadata payload: {error}".format(error=str(exc)))

    logger.info("Worker metadata replace request received metadata_count=%s", len(decoded_entries))

    old_metadata_stanza = HydraMetadataStanza.from_name("metadata", _APP, "nobody", session_key=session_key)
    if old_metadata_stanza and not old_metadata_stanza.passive_delete():
        logger.error("Worker metadata replace failed reason=delete_previous_metadata")
        return _response(500, "failed to delete previous metadata stanza")

    new_metadata_stanza = HydraMetadataStanza(_APP, "nobody", "metadata", sessionKey=session_key)
    for metadata_key, metadata_value in decoded_entries.items():
        setattr(new_metadata_stanza, metadata_key, metadata_value)

    if not new_metadata_stanza.passive_save():
        logger.error("Worker metadata replace failed reason=save_metadata")
        return _response(500, "failed to save metadata stanza")
    logger.info("Worker metadata replace succeeded metadata_count=%s", len(decoded_entries))
    return _response(200, "ok", {"metadata_count": len(decoded_entries)})


def _clear_sessions(session_key):
    list_path = "/servicesNS/nobody/{app}/configs/conf-inframon_hydra_session".format(app=_APP)
    logger.info("Worker session clear request received")
    rsp, session_content = simpleRequest(
        list_path,
        method="GET",
        sessionKey=session_key,
        getargs={"output_mode": "json", "count": "0"},
        raiseAllErrors=False,
    )
    if int(getattr(rsp, "status", 0)) != 200:
        logger.error("Worker session clear failed reason=list_sessions status=%s", int(getattr(rsp, "status", 0)))
        return _response(500, "failed to list session stanzas")

    decoded = session_content.decode("utf-8") if isinstance(session_content, bytes) else session_content
    payload = json.loads(decoded)
    deleted = 0
    for entry in payload.get("entry", []):
        session_name = entry.get("name")
        if not isinstance(session_name, str) or not _VALID_SESSION_NAME_RE.match(session_name):
            continue
        delete_path = list_path.rstrip("/") + "/" + quote_plus(session_name)
        delete_rsp, _ = simpleRequest(
            delete_path,
            method="DELETE",
            sessionKey=session_key,
            raiseAllErrors=False,
        )
        if int(getattr(delete_rsp, "status", 0)) == 200:
            deleted += 1
    logger.info("Worker session clear succeeded deleted=%s", deleted)
    return _response(200, "ok", {"deleted": deleted})


class HydraWorkerManagementHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None, *args, **kwargs):
        super(HydraWorkerManagementHandler, self).__init__()

    def handle(self, in_string):
        try:
            if isinstance(in_string, bytes):
                in_string = in_string.decode("utf-8")
            request = json.loads(in_string) if isinstance(in_string, str) else in_string
        except Exception:
            return _response(400, "invalid request payload")

        method = str(request.get("method", "GET")).upper()
        path_info = request.get("path_info", "")
        route = _normalized_route(path_info)
        system_session_key = request.get("system_authtoken", "")

        if not system_session_key:
            logger.error("Worker management request rejected: no system_authtoken in request")
            return _response(500, "internal error: system session key unavailable")

        if route == "ping":
            if method != "GET":
                logger.warning("Worker management ping rejected method=%s", method)
                return _response(405, "method not supported; use GET")
            logger.info("Worker management ping succeeded")
            return _response(200, "ok")

        if method != "POST":
            logger.warning("Worker management request rejected route=%s method=%s", route, method)
            return _response(405, "method not supported; use POST")

        args = _extract_args(request)

        try:
            if route == "input/toggle":
                return _update_worker_input(system_session_key, args)
            if route == "credential/upsert":
                return _upsert_credential(system_session_key, args)
            if route == "metadata/replace":
                return _replace_metadata(system_session_key, args)
            if route == "session/clear":
                return _clear_sessions(system_session_key)
            logger.warning("Worker management request rejected unknown_route=%s", route)
            return _response(404, "unknown worker management route")
        except Exception as exc:
            logger.exception("Worker management request failed path=%s route=%s error=%s", path_info, route, str(exc))
            return _response(500, "internal error")

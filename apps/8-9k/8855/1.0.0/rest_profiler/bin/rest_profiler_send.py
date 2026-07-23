"""
rest_profiler_send.py

Logic for the `restprofilersend` generating custom search command.

UCC generates the dispatcher wrapper from globalConfig and calls
`generate(self)`, where `self` exposes the `profile` and `mode` options and the
search metadata.

Usage:
    | restprofilersend profile="my_profile" mode="preview"
    | restprofilersend profile="my_profile" mode="send"

mode defaults to "send". "preview" makes no network call and returns the
composed request with secrets masked; "send" executes the request.
"""

import import_declare_test  # noqa: F401  (sets up sys.path for lib/)

import json
import time

import rest_profiler_client as client


def _event_to_raw(event):
    raw = {k: v for k, v in event.items() if not k.startswith("_")}
    return json.dumps(raw, default=str)


def generate(command):
    logger = client.get_logger()

    profile_name = getattr(command, "profile", None)
    mode = (getattr(command, "mode", None) or "send").strip().lower()
    if mode not in ("preview", "send"):
        mode = "send"

    try:
        session_key = command.metadata.searchinfo.session_key
    except AttributeError:
        session_key = None

    client.apply_log_level(session_key, logger)

    now = time.time()

    if not profile_name:
        yield {
            "_time": now,
            "profile": "",
            "mode": mode,
            "ok": False,
            "error": "The 'profile' argument is required.",
            "_raw": "The 'profile' argument is required.",
        }
        return

    try:
        profile = client.load_profile(session_key, profile_name)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "restprofilersend: failed to load profile '%s': %s", profile_name, exc
        )
        event = {
            "_time": now,
            "profile": profile_name,
            "mode": mode,
            "ok": False,
            "error": "Profile '{p}' could not be loaded: {e}".format(
                p=profile_name, e=exc
            ),
        }
        event["_raw"] = _event_to_raw(event)
        yield event
        return

    if mode == "preview":
        try:
            text, composed = client.preview_text(profile)
        except ValueError as exc:
            event = {
                "_time": now,
                "profile": profile_name,
                "mode": "preview",
                "ok": False,
                "error": str(exc),
            }
            event["_raw"] = _event_to_raw(event)
            yield event
            return
        yield {
            "_time": now,
            "profile": profile_name,
            "mode": "preview",
            "ok": True,
            "method": composed["method"],
            "url": composed["url"],
            "auth": composed["auth_note"],
            "verify_ssl": "1" if client._verify_enabled(profile) else "0",
            "request": text,
            "_raw": text,
        }
        return

    # mode == "send"
    logger.info("restprofilersend: sending profile '%s'", profile_name)
    result = client.send_request(profile)
    event = {
        "_time": now,
        "profile": profile_name,
        "mode": "send",
        "ok": result.get("ok"),
        "method": result.get("method"),
        "url": result.get("url"),
        "auth": result.get("auth"),
        "status": result.get("status"),
        "reason": result.get("reason"),
        "elapsed_ms": result.get("elapsed_ms"),
        "request_headers": json.dumps(result.get("request_headers", {}), default=str),
        "response_headers": json.dumps(result.get("response_headers", {}), default=str),
        "response_body": result.get("response_body"),
        "body_truncated": result.get("body_truncated"),
        "validated": result.get("validated"),
        "validation_error": result.get("validation_error"),
        "attempts": result.get("attempts"),
        "error_category": result.get("error_category"),
        "error": result.get("error"),
    }
    event["_raw"] = _event_to_raw(event)

    if not result.get("ok"):
        logger.error(
            "restprofilersend: profile '%s' failed (%s): %s",
            profile_name,
            result.get("error_category"),
            result.get("error"),
        )
    else:
        logger.info(
            "restprofilersend: profile '%s' -> %s %s in %sms",
            profile_name,
            result.get("status"),
            result.get("reason"),
            result.get("elapsed_ms"),
        )
    yield event

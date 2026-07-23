"""
rest_profiler_alert.py

Custom script for the `rest_profiler_send_alert` alert action (referenced by
`customScript` in globalConfig.json). When the alert fires, this sends the
selected profile's request and, optionally, writes the response back into
Splunk as an event.

`helper` is an instance of splunktaucclib.alert_actions_base.ModularAlertBase
and exposes: get_param(field), session_key, addevent(raw, sourcetype),
writeevents(index, source, host), log_info(msg), log_error(msg).

process_event() returns 0 on success, non-zero on failure (Splunk convention).
"""

import import_declare_test  # noqa: F401  (sets up sys.path for lib/)

import json
import time
import traceback

import rest_profiler_client as client


def _is_true(value):
    return str(value).strip().lower() in ("1", "true", "yes")


def process_event(helper, *args, **kwargs):
    logger = client.get_logger()
    try:
        return _run(helper, logger)
    except Exception as exc:  # noqa: BLE001 - surface the real cause of exit code 5
        tb = traceback.format_exc()
        try:
            helper.log_error(
                "rest_profiler_send_alert: unhandled error: %s\n%s" % (exc, tb)
            )
        except Exception:  # noqa: BLE001
            pass
        logger.error("rest_profiler_send_alert: unhandled error: %s\n%s", exc, tb)
        return 2


def _run(helper, logger):
    session_key = getattr(helper, "session_key", None)
    client.apply_log_level(session_key, logger)

    profile_name = helper.get_param("profile")
    store_response = _is_true(helper.get_param("store_response"))
    result_index = helper.get_param("result_index") or "main"

    helper.log_info(
        "rest_profiler_send_alert invoked: profile=%r store_response=%s result_index=%s"
        % (profile_name, store_response, result_index)
    )

    if not profile_name:
        helper.log_error("rest_profiler_send_alert: 'profile' is a required parameter.")
        return 3

    try:
        profile = client.load_profile(session_key, profile_name)
    except Exception as exc:  # noqa: BLE001
        helper.log_error(
            "rest_profiler_send_alert: could not load profile '{p}': {e}".format(
                p=profile_name, e=exc
            )
        )
        return 2

    send_results = str(profile.get("send_results", "0")).strip() == "1"
    result_format = (profile.get("result_format") or "json_body").lower()
    events = []
    if send_results:
        try:
            events = list(helper.get_events() or [])
        except Exception as exc:  # noqa: BLE001
            helper.log_error(
                "rest_profiler_send_alert: could not read triggering events: %s" % exc
            )
            events = []

    helper.log_info(
        "rest_profiler_send_alert: send_results=%s format=%s rows=%d first_row_fields=%s"
        % (
            send_results,
            result_format,
            len(events),
            sorted(events[0].keys()) if events else [],
        )
    )

    if send_results and events:
        return _send_per_row(helper, profile, profile_name, events, store_response, result_index)

    if send_results and not events:
        helper.log_info(
            "rest_profiler_send_alert: 'send results' is on but there were no "
            "triggering events; sending the static request once."
        )

    # Static single request (result-sending disabled or no triggering rows).
    result = client.send_request(profile)
    result["profile"] = profile_name

    validation_failed = client.validation_configured(profile) and not result.get(
        "validated", False
    )
    if not result.get("ok") or validation_failed:
        helper.log_error(
            "rest_profiler_send_alert: profile '{p}' failed ({c}): {e}".format(
                p=profile_name,
                c=result.get("error_category") or "validation",
                e=result.get("error") or result.get("validation_error"),
            )
        )
        return_code = 2
    else:
        status = result.get("status", 0) or 0
        message = "rest_profiler_send_alert: profile '{p}' -> {s} {r} in {ms}ms".format(
            p=profile_name,
            s=status,
            r=result.get("reason"),
            ms=result.get("elapsed_ms"),
        )
        helper.log_error(message) if status >= 400 else helper.log_info(message)
        return_code = 0

    if store_response:
        try:
            helper.addevent(
                json.dumps(result, default=str), sourcetype="rest_profiler:response"
            )
            helper.writeevents(index=result_index, source="rest_profiler_send_alert")
        except Exception as exc:  # noqa: BLE001
            helper.log_error(
                "rest_profiler_send_alert: failed to index response: {e}".format(e=exc)
            )

    return return_code


def _send_per_row(helper, profile, profile_name, events, store_response, result_index):
    total = len(events)
    if total > client.MAX_RESULT_ROWS:
        helper.log_error(
            "rest_profiler_send_alert: %d rows exceed the cap of %d; sending the "
            "first %d only." % (total, client.MAX_RESULT_ROWS, client.MAX_RESULT_ROWS)
        )
        events = events[: client.MAX_RESULT_ROWS]

    try:
        rate_limit = float(profile.get("rate_limit_seconds") or 0)
    except (TypeError, ValueError):
        rate_limit = 0.0
    rate_limit = min(max(rate_limit, 0), 3600)

    sent = 0
    failed = 0
    queued = False
    for idx, event in enumerate(events):
        if rate_limit > 0 and idx > 0:
            time.sleep(rate_limit)
        result = client.send_request(profile, event=event)
        result["profile"] = profile_name
        result["row"] = idx
        status = result.get("status", 0) or 0
        if result.get("validated", False):
            sent += 1
            helper.log_info(
                "rest_profiler_send_alert: profile '%s' row %d -> %s %s in %sms"
                % (profile_name, idx, status, result.get("reason"), result.get("elapsed_ms"))
            )
        else:
            failed += 1
            helper.log_error(
                "rest_profiler_send_alert: profile '%s' row %d failed: status=%s error=%s"
                % (
                    profile_name,
                    idx,
                    status,
                    result.get("error") or result.get("validation_error"),
                )
            )
        if store_response:
            try:
                helper.addevent(
                    json.dumps(result, default=str),
                    sourcetype="rest_profiler:response",
                )
                queued = True
            except Exception as exc:  # noqa: BLE001
                helper.log_error(
                    "rest_profiler_send_alert: failed to queue response row %d: %s"
                    % (idx, exc)
                )

    if store_response and queued:
        try:
            helper.writeevents(index=result_index, source="rest_profiler_send_alert")
        except Exception as exc:  # noqa: BLE001
            helper.log_error(
                "rest_profiler_send_alert: failed to index responses: %s" % exc
            )

    helper.log_info(
        "rest_profiler_send_alert: profile '%s' done: %d sent, %d failed of %d rows"
        % (profile_name, sent, failed, len(events))
    )
    return 0 if failed == 0 else 2

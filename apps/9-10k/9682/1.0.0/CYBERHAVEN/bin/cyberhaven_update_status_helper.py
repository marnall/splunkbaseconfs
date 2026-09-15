"""Helper logic for the cyberhaven_update_status adaptive response action.

Updates an incident's status via the shared cyberhaven_api_client. close_reason/
close_note (derived by the triggering saved search from the notable's disposition
field) are only included in the API payload when status is "Closed" -- a reopen
(status back to e.g. "Open") has no disposition to report, so those fields, their
log/comment mentions, and the synced_close_reason KV write are all skipped for any
other status. See cyberhaven_api_client for the auth flow and status-code handling/
retry policy.
"""
import time

from cyberhaven_api_client import (
    get_access_token,
    sync_incident,
    CyberhavenAuthError,
    CyberhavenProxyError,
    CyberhavenPermissionError,
    CyberhavenNotFoundError,
    CyberhavenConflictError,
    CyberhavenRetryExhaustedError,
)
from cyberhaven_settings import get_notable_automation_settings, get_logger, upsert_sync_state, get_proxy_settings

logger = get_logger("cyberhaven_update_status")


def _log_error(helper, msg):
    """Log to both the framework's modalert log (helper) and this app's own log (logger)."""
    helper.log_error(msg)
    logger.error(msg)


def _log_info(helper, msg):
    """Log to both the framework's modalert log (helper) and this app's own log (logger)."""
    helper.log_info(msg)
    logger.info(msg)


def _add_notable_comment(rule_id, comment, session_key):
    """Best-effort: record the outcome as a comment on the originating notable event."""
    if not rule_id:
        return
    try:
        import splunk.rest as rest
        rest.simpleRequest(
            "/services/notable_update",
            sessionKey=session_key,
            postargs={"comment": comment, "ruleUIDs": rule_id},
            method="POST",
            raiseAllErrors=False,
        )
    except Exception as e:
        logger.warning(f"Failed to add comment to notable rule_id={rule_id}: {e}")


def process_event(helper, *args, **kwargs):
    """Process the triggering search results and sync each incident's status to Cyberhaven."""
    logger.info("Alert action cyberhaven_update_status started.")
    start_time = time.time()

    session_key = helper.session_key
    settings = get_notable_automation_settings(session_key)
    tenant_url = settings.get("tenant_url")
    api_key = settings.get("api_key")

    if not tenant_url:
        _log_error(
            helper,
            "Cyberhaven Tenant URL is not configured in the TA-CYBERHAVEN add-on; cannot update incident status.",
        )
        return 3
    if not api_key:
        _log_error(
            helper,
            "Cyberhaven API Key is not configured in the TA-CYBERHAVEN add-on; cannot update incident status.",
        )
        return 3

    base_url = f"{tenant_url}/public"
    proxies = get_proxy_settings(session_key)

    events = list(helper.get_events())
    if not events:
        _log_info(helper, "No events to process.")
        return 0

    default_status = helper.get_param("status") or "Closed"
    default_close_reason = helper.get_param("close_reason") or "invalid_other"
    default_close_note = helper.get_param("close_note") or "Closed by Splunk SIEM Integration: Undetermined"

    try:
        access_token_box = [get_access_token(base_url, api_key, proxies=proxies)]
    except CyberhavenProxyError as e:
        _log_error(
            helper,
            f"Failed to reach the Cyberhaven platform through the configured proxy: {e}. "
            "Check the Proxy settings in the TA-CYBERHAVEN add-on configuration.",
        )
        for event in events:
            rule_id = event.get("notable_rule_id") or event.get("rule_id") or ""
            _add_notable_comment(
                rule_id,
                "Could not reach the Cyberhaven platform through the configured proxy; could not sync "
                "status to the Cyberhaven platform. Check the Proxy settings in the TA-CYBERHAVEN add-on "
                "configuration.",
                session_key,
            )
        return 3
    except Exception as e:
        _log_error(helper, f"Failed to obtain a Cyberhaven access token: {e}")
        for event in events:
            rule_id = event.get("notable_rule_id") or event.get("rule_id") or ""
            _add_notable_comment(
                rule_id,
                "Cyberhaven credential is invalid or was rejected; could not sync status to the "
                "Cyberhaven platform. Check the API key in the TA-CYBERHAVEN add-on configuration.",
                session_key,
            )
        return 3

    failures = 0
    auth_broken = False
    proxy_broken = False
    for event in events:
        incident_id = (event.get("cyberhaven_incident_id") or "").strip()
        # The Cyberhaven API's status field only accepts "closed"/"open" (case-sensitive
        # once lowercased below) -- always use the triggering saved search's own
        # param.status (Closed or Open, set deliberately per search), never the
        # notable's raw ES status_label (New/In Progress/Pending/Resolved/Closed/...),
        # which isn't a value Cyberhaven's API understands.
        status = default_status.strip()
        rule_id = event.get("notable_rule_id") or event.get("rule_id") or ""
        # close_reason/close_note only apply when actually closing the incident -- a
        # reopen (status back to e.g. "Open") has no disposition to report, so the API
        # payload, log/comment messages, and KV sync-state write below all omit them
        # entirely rather than send a meaningless default.
        is_closing = status.lower() == "closed"
        close_reason = (event.get("close_reason") or default_close_reason).strip() if is_closing else ""
        close_note = (event.get("close_note") or default_close_note).strip() if is_closing else ""

        if not incident_id:
            _log_error(helper, f"Skipping event with no cyberhaven_incident_id (rule_id={rule_id}).")
            failures += 1
            continue

        if auth_broken:
            # The credential already failed a refresh-and-retry this run; don't
            # keep hitting the auth endpoint for every remaining event.
            failures += 1
            _log_error(
                helper,
                f"Skipping Cyberhaven incident {incident_id}: API key already failed authentication this run.",
            )
            continue

        if proxy_broken:
            # The proxy already failed once this run; every remaining event would fail
            # identically, so don't keep retrying against a proxy that's already down.
            failures += 1
            _log_error(
                helper,
                f"Skipping Cyberhaven incident {incident_id}: configured proxy already failed this run.",
            )
            continue

        payload = {"status": status.lower()}
        if is_closing:
            payload["close_reason"] = close_reason
            payload["close_note"] = close_note

        try:
            sync_incident(base_url, api_key, access_token_box, incident_id, payload, helper, proxies=proxies)
            if is_closing:
                _log_info(
                    helper,
                    f"Updated Cyberhaven incident {incident_id} to status '{status}' "
                    f"(close_reason='{close_reason}').",
                )
            else:
                _log_info(helper, f"Updated Cyberhaven incident {incident_id} to status '{status}'.")
            sync_state_fields = {"synced_status": status}
            if is_closing:
                sync_state_fields["synced_close_reason"] = close_reason
            upsert_sync_state(session_key, rule_id, incident_id, **sync_state_fields)
            if is_closing:
                comment = (
                    f"Cyberhaven incident {incident_id} status updated to '{status}' "
                    f"(close_reason='{close_reason}') via Splunk adaptive response."
                )
            else:
                comment = (
                    f"Cyberhaven incident {incident_id} status updated to '{status}' "
                    "via Splunk adaptive response."
                )
            _add_notable_comment(rule_id, comment, session_key)
        except CyberhavenAuthError as e:
            failures += 1
            auth_broken = True
            _log_error(
                helper,
                f"Failed to update Cyberhaven incident {incident_id}: API key rejected even after refresh: {e}",
            )
            _add_notable_comment(
                rule_id,
                f"Failed to update Cyberhaven incident {incident_id}: authentication failed even after refresh.",
                session_key,
            )
        except CyberhavenProxyError as e:
            failures += 1
            proxy_broken = True
            _log_error(
                helper,
                f"Failed to update Cyberhaven incident {incident_id}: could not reach Cyberhaven through the "
                f"configured proxy: {e}. Check the Proxy settings in the TA-CYBERHAVEN add-on configuration.",
            )
            _add_notable_comment(
                rule_id,
                f"Failed to update Cyberhaven incident {incident_id}: could not reach the Cyberhaven platform "
                "through the configured proxy.",
                session_key,
            )
        except CyberhavenPermissionError as e:
            failures += 1
            _log_error(
                helper,
                f"Failed to update Cyberhaven incident {incident_id}: API key lacks permission for this "
                f"incident: {e}. Check the API key's scope/tenant in the TA-CYBERHAVEN add-on configuration.",
            )
            _add_notable_comment(
                rule_id,
                f"Failed to update Cyberhaven incident {incident_id}: the API key doesn't have permission "
                "to update this incident.",
                session_key,
            )
        except CyberhavenNotFoundError as e:
            failures += 1
            _log_error(
                helper,
                f"Failed to update Cyberhaven incident {incident_id}: not found on the Cyberhaven platform: {e}. "
                "It may have been deleted, or the incident id recovered from the notable event may be stale.",
            )
            _add_notable_comment(
                rule_id,
                f"Failed to update Cyberhaven incident {incident_id}: this incident could not be found on the "
                "Cyberhaven platform.",
                session_key,
            )
        except CyberhavenConflictError as e:
            failures += 1
            _log_error(
                helper,
                f"Failed to update Cyberhaven incident {incident_id}: rejected due to the incident's current "
                f"state on the Cyberhaven platform: {e}.",
            )
            _add_notable_comment(
                rule_id,
                f"Failed to update Cyberhaven incident {incident_id}: the requested change conflicts with the "
                "incident's current state on the Cyberhaven platform.",
                session_key,
            )
        except CyberhavenRetryExhaustedError as e:
            failures += 1
            _log_error(
                helper,
                f"Failed to update Cyberhaven incident {incident_id}: Cyberhaven was still unavailable after "
                f"retries: {e}. This may succeed on the next scheduled run.",
            )
            _add_notable_comment(
                rule_id,
                f"Failed to update Cyberhaven incident {incident_id}: the Cyberhaven platform was temporarily "
                "unavailable; this will be retried on the next scheduled run.",
                session_key,
            )
        except Exception as e:
            failures += 1
            _log_error(helper, f"Failed to update Cyberhaven incident {incident_id}: {e}")
            _add_notable_comment(
                rule_id,
                f"Failed to update Cyberhaven incident {incident_id} status to '{status}': {e}",
                session_key,
            )

    logger.info(
        "message=alert_end_execution | End of the alert execution. "
        f"Total time taken: elapsed_seconds={time.time() - start_time:.3f}"
    )
    return 3 if failures else 0

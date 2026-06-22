#!/usr/bin/env python3
# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.
"""
Script for periodic SCS connection health checks.

This modular input runs every 60 seconds, checks whether the SCS auth endpoint
and SCS API base URL are reachable, and mutates connectionState in
cloud-connection.conf based on the result:

  - SCS unreachable while connectionState == enabled   → set connectionState = unavailable
  - SCS reachable   while connectionState == unavailable → set connectionState = enabled
  - No state change when the check result already matches the current state.

An EVENT_CONNECTION_STATE_CHANGED audit record is written to the
cloud_connection_audit KVStore collection **only when the state actually transitions** —
not on every cycle. This keeps audit log volume low (one record per real event
rather than ~2,880 records/day).

The modinput runs when connectionState is enabled OR unavailable — both states
represent an established connection (one healthy, one degraded).

Design decisions:
- Only runs on the SHC captain to avoid duplicate writes in a cluster.
- Runs when state is enabled OR unavailable so recovery from degraded state
  is detected automatically.
- Mutates connectionState directly — no separate scsAvailable flag needed.
- State transition written only when result differs from current state to
  avoid redundant conf writes on every cycle.
- Audit record written only on state transition, not on every cycle.
- No retries within a single run — transient blips self-correct on the next
  60-second cycle.
- HEAD requests: minimal payload, no auth token required.
- 401/403 from the auth endpoint counts as reachable (SCS responded; network up).
- sys.exit(0) always — modinputs that exit non-zero produce Splunk UI errors.
"""

import sys
import http.client
import logging

from utils.scs_utils import SCSUtils
from utils.utils import (
    is_shc_captain,
    get_cloud_connection_config,
    get_splunk_user_for_audit,
    CloudConnectionConfigNotFoundError,
)
from utils.cloud_connection_event_log import CloudConnectionEventLog
from constants import (
    GENERAL_CONNECTION_STATE_KEY,
    CONNECTION_STATE_ENABLED,
    CONNECTION_STATE_UNAVAILABLE,
    SPLUNK_CLOUD_CONNECTION_CONF_URI,
    SCS_HEALTH_CHECK_OPERATION,
    AUDIT_EVENT_CONNECTION_STATE_CHANGED,
    AUDIT_EVENT_HEALTH_CHECK_SKIPPED,
    AUDIT_SEVERITY_INFO,
    AUDIT_SEVERITY_WARNING,
    AUDIT_SEVERITY_ERROR,
    HEALTH_CHECK_SKIP_SUBCODE_GENERAL_STANZA_NOT_FOUND,
    HEALTH_CHECK_SKIP_SUBCODE_CONFIG_RESPONSE_UNPARSEABLE,
    HEALTH_CHECK_SKIP_SUBCODE_SPLUNKD_CONF_API_CLIENT_ERROR,
    HEALTH_CHECK_SKIP_SUBCODE_SPLUNKD_CONF_API_UNAVAILABLE,
    HEALTH_CHECK_SKIP_SUBCODE_GENERAL_STANZA_INVALID,
    HEALTH_CHECK_SKIP_SUBCODE_SCS_STANZA_INVALID,
    HEALTH_CHECK_SKIP_SUBCODE_SCS_API_BASE_UNREACHABLE,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('scs_health_check')

# States in which the modinput is active
_ACTIVE_STATES = {CONNECTION_STATE_ENABLED, CONNECTION_STATE_UNAVAILABLE}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _head_check(session_key: str, url: str, label: str) -> bool:
    """
    Send a HEAD request to *url* and return True if any HTTP response is received.

    Any HTTP response (including 4xx/5xx) means the network path is up → True.
    Any exception means the endpoint is unreachable → False.

    No audit record is written here — audit logging is deferred to
    ``_set_connection_state()`` so records are only written when the state
    actually transitions.

    Args:
        session_key: Splunk session key.
        url: Fully-qualified URL to probe.
        label: Short human-readable name used in log messages (e.g. 'auth', 'status').

    Returns:
        True if the endpoint responded, False otherwise.
    """
    splunk_user = get_splunk_user_for_audit(session_key, logger, default_user='scs_health_check')
    try:
        logger.info('Checking SCS %s endpoint: HEAD %s', label, url)
        SCSUtils.request_with_splunkd_proxy(
            logger=logger,
            session_key=session_key,
            method='HEAD',
            url=url,
            splunk_user=splunk_user,
        )
        logger.info('SCS %s endpoint is reachable', label)
        return True

    except Exception as e:
        logger.warning('SCS %s endpoint is unreachable: %s', label, e)
        return False


def _check_auth_endpoint(session_key: str, config: dict) -> bool:
    """
    Check reachability of the SCS auth /token endpoint.

    401/403 count as reachable — they mean SCS responded; the network path is up.

    Args:
        session_key: Splunk session key.
        config: Cloud connection config dict.

    Returns:
        True if the auth endpoint responded, False otherwise.
    """
    try:
        url = SCSUtils.get_scs_auth_base_token_url(logger, session_key)
    except Exception as e:
        logger.warning('Failed to resolve SCS auth URL: %s', e)
        return False
    return _head_check(session_key, url, 'auth')


def _check_status_endpoint(session_key: str, config: dict) -> bool:
    """
    Check reachability of the SCS API base URL.

    Args:
        session_key: Splunk session key.
        config: Cloud connection config dict.

    Returns:
        True if the API base URL responded, False otherwise.
    """
    try:
        url = SCSUtils.resolve_scs_api_base_url(logger, session_key, config.get('tenantName'))
    except Exception as e:
        logger.warning('Failed to resolve SCS API base URL: %s', e)
        return False
    return _head_check(session_key, url, 'status')


def _skip(session_key: str, subcode: str, severity: str) -> None:
    """
    Write a health_check_skipped audit record and exit the modular input cleanly.

    Centralises the repeated audit → exit pattern used by every skip guard.

    Args:
        session_key: Splunk session key.
        subcode: Skip reason identifier written to the audit record.
        severity: Audit record severity (AUDIT_SEVERITY_INFO / WARNING / ERROR).
    """
    CloudConnectionEventLog(session_key, logger).log(
        operation=SCS_HEALTH_CHECK_OPERATION,
        event_type=AUDIT_EVENT_HEALTH_CHECK_SKIPPED,
        severity=severity,
        subcode=subcode,
    )
    sys.exit(0)


def _pre_activation_probe(session_key: str) -> str:
    """
    Probe api.scs.splunk.com when [general] stanza is absent (pre-activation).

    Reads base_template_api from [scs] and issues a HEAD request. Returns the
    appropriate skip subcode based on the outcome:

    - [scs] stanza missing or base_template_api blank → exits via _skip (scs_stanza_invalid, error)
    - api.scs.splunk.com unreachable                  → scs_api_base_unreachable
    - api.scs.splunk.com reachable                    → general_stanza_not_found

    Args:
        session_key: Splunk session key.

    Returns:
        Skip subcode string. Never returns if [scs] stanza is corrupt — exits via _skip.
    """
    try:
        api_base_url = SCSUtils.get_scs_api_base_url(logger, session_key)
        api_reachable = _head_check(session_key, api_base_url, 'api-base')
    except Exception:
        logger.error('[scs] stanza missing or base_template_api blank — conf is corrupt, skipping health check', exc_info=True)
        _skip(session_key, HEALTH_CHECK_SKIP_SUBCODE_SCS_STANZA_INVALID, AUDIT_SEVERITY_ERROR)

    if not api_reachable:
        logger.warning('SCS API base URL unreachable pre-activation: %s', api_base_url)
        return HEALTH_CHECK_SKIP_SUBCODE_SCS_API_BASE_UNREACHABLE
    logger.info('SCS API base URL reachable pre-activation: %s', api_base_url)
    return HEALTH_CHECK_SKIP_SUBCODE_GENERAL_STANZA_NOT_FOUND


def _set_connection_state(session_key: str, state: str) -> None:
    """
    Write connectionState to cloud-connection.conf [general] and emit an audit record.

    Uses the same SPLUNK_CLOUD_CONNECTION_CONF_URI POST endpoint as
    cloud_connection_service._update_connection_state().
    An EVENT_CONNECTION_STATE_CHANGED audit record is written to the
    cloud_connection_audit KVStore collection only when the conf write succeeds.
    Never raises; errors are logged so the modinput can continue.

    Args:
        session_key: Splunk session key.
        state: New connectionState value (e.g. CONNECTION_STATE_ENABLED).
    """
    try:
        resp, _ = SCSUtils.simple_request_with_retry(
            logger=logger,
            method='POST',
            path=SPLUNK_CLOUD_CONNECTION_CONF_URI,
            session_key=session_key,
            postargs={'connectionState': state},
        )
        status = getattr(resp, 'status', None)
        if status not in (http.client.OK, http.client.CREATED):
            logger.error(
                'Failed to set connectionState=%s, status=%s', state, status,
            )
        else:
            logger.info('connectionState set to %s', state)
            CloudConnectionEventLog(session_key, logger).log(
                operation=SCS_HEALTH_CHECK_OPERATION,
                event_type=AUDIT_EVENT_CONNECTION_STATE_CHANGED,
                severity=AUDIT_SEVERITY_INFO,
            )
    except Exception as e:
        logger.error('Unexpected error setting connectionState: %s', e, exc_info=True)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def perform_health_check(session_key: str, config: dict) -> bool:
    """
    Orchestrate both SCS endpoint checks and transition connectionState if needed.

    Overall reachability = auth endpoint AND status endpoint both reachable.

    State transition rules (write only when result differs from current state):
      - overall=True  AND current state == unavailable → set state to enabled
      - overall=False AND current state == enabled     → set state to unavailable
      - No write in all other combinations.

    Args:
        session_key: Splunk session key.
        config: Cloud connection config dict.

    Returns:
        True if both endpoints are reachable, False otherwise.
    """
    auth_ok = _check_auth_endpoint(session_key, config)
    status_ok = _check_status_endpoint(session_key, config)

    overall = auth_ok and status_ok
    current_state = config.get(GENERAL_CONNECTION_STATE_KEY)

    if overall and current_state == CONNECTION_STATE_UNAVAILABLE:
        logger.info('SCS reachable — restoring connectionState to enabled')
        _set_connection_state(session_key, CONNECTION_STATE_ENABLED)
    elif not overall and current_state == CONNECTION_STATE_ENABLED:
        logger.warning('SCS unreachable — setting connectionState to unavailable')
        _set_connection_state(session_key, CONNECTION_STATE_UNAVAILABLE)
    else:
        logger.info(
            'Health check complete — no state change needed '
            '(auth_ok=%s status_ok=%s current_state=%s)',
            auth_ok, status_ok, current_state,
        )

    return overall


# ---------------------------------------------------------------------------
# Modular-input entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    # Read session key from stdin (passed by Splunk)
    session_key = sys.stdin.read().strip()

    # Guard: only the SHC captain should run health checks
    if not is_shc_captain(session_key, logger):
        logger.info('Instance is not an SHC captain or has not been elected yet, skipping health check')
        sys.exit(0)

    # Guard: skip if the cloud connection config is missing or invalid
    try:
        config = get_cloud_connection_config(session_key, logger)
    except CloudConnectionConfigNotFoundError as e:
        # e.status carries the HTTP status returned by splunkd.
        # 404  → stanza absent; probe api.scs.splunk.com for pre-activation connectivity.
        # 4xx  → client error (auth/permission problem); not masked as missing stanza.
        # 5xx / None → server-side or transient availability problem.
        if e.status == 404:
            logger.warning('Configuration not found (404): %s', e)
            logger.info('[general] stanza absent — probing SCS API base URL for pre-activation connectivity')
            subcode = _pre_activation_probe(session_key)
            severity = AUDIT_SEVERITY_ERROR if subcode == HEALTH_CHECK_SKIP_SUBCODE_SCS_API_BASE_UNREACHABLE else AUDIT_SEVERITY_INFO
        elif e.status is not None and 400 <= e.status < 500:
            logger.warning('Configuration request rejected (status=%s): %s', e.status, e)
            subcode = HEALTH_CHECK_SKIP_SUBCODE_SPLUNKD_CONF_API_CLIENT_ERROR
            severity = AUDIT_SEVERITY_WARNING
        else:
            logger.error('Configuration unavailable (status=%s): %s', e.status, e)
            subcode = HEALTH_CHECK_SKIP_SUBCODE_SPLUNKD_CONF_API_UNAVAILABLE
            severity = AUDIT_SEVERITY_ERROR
        _skip(session_key, subcode, severity)
    except ValueError as e:
        logger.error('Configuration response unparseable: %s', e)
        _skip(session_key, HEALTH_CHECK_SKIP_SUBCODE_CONFIG_RESPONSE_UNPARSEABLE, AUDIT_SEVERITY_ERROR)
    except Exception as e:
        logger.error('Unexpected error reading configuration: %s', e)
        _skip(session_key, HEALTH_CHECK_SKIP_SUBCODE_SPLUNKD_CONF_API_UNAVAILABLE, AUDIT_SEVERITY_ERROR)

    # Guard: only run when an established connection exists (healthy or degraded)
    if config.get(GENERAL_CONNECTION_STATE_KEY) not in _ACTIVE_STATES:
        logger.info(
            'connectionState is not enabled or unavailable (state=%s), skipping health check',
            config.get(GENERAL_CONNECTION_STATE_KEY),
        )
        sys.exit(0)

    # Guard: required config fields must be present
    if not config.get('tenantName') or not config.get('regionAuthHostname'):
        logger.error('Missing required configuration (tenantName or regionAuthHostname), skipping health check')
        _skip(session_key, HEALTH_CHECK_SKIP_SUBCODE_GENERAL_STANZA_INVALID, AUDIT_SEVERITY_ERROR)

    # Perform health check — connectionState is mutated by perform_health_check
    # only when the result differs from the current state.
    perform_health_check(session_key, config)

    # Always exit cleanly — modinputs that exit non-zero cause Splunk UI errors.
    sys.exit(0)

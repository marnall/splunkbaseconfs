#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.2.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

"""
TrackMe Configuration Guardian — modular framework that detects misconfiguration
conditions, stores active alerts in a single global KV collection
(``kv_trackme_configuration_guardian_alerts``), and exposes them to the UI and REST
API (for admin surfacing and future AI-agent remediation).

Each alert record is keyed by SHA256 of ``check_type:scope_key`` so the same
(check, scope) combination upserts idempotently. Resolving an issue means the
next detection cycle clears the record (self-healing).

Severity tiers
--------------
* ``warning``  — attention needed, not urgent. Fallback / degraded state still
  works. Examples: tenant-owner capabilities missing; backup archive old.
* ``critical`` — active degradation. Data loss, dropped alerts, or a meta-failure
  (the health tracker itself not running). Renders as an error toast in the UI
  and always emits an audit event.

Audit trail
-----------
Every state transition (create, severity change, clear) writes a structured
event to the ``trackme_audit`` index (sourcetype ``trackme:audit:guardian``)
so an admin can reconstruct a timeline post-mortem — and so downstream agents
can consume the history as a time series.

Registered checks
-----------------
* ``insufficient_tenant_owner_capabilities`` (tenant, warning) — the service
  account owning a tenant is missing required Splunk capabilities.
* ``assigned_index_does_not_exist`` (tenant, warning) — a tenant is configured
  against one or more Splunk indexes that don't exist on the search head.
* ``remote_account_token_expiring_soon`` (system, warning→critical) — a remote
  bearer token's JWT ``exp`` claim is within the warning/critical band or has
  already passed. The check decodes the actual configured token rather than
  inferring expiry from the rotation cadence.
* ``health_tracker_not_executing`` (tenant, critical) — the per-tenant health
  tracker has not recorded a successful cycle in > 30 minutes. This is the
  meta-check; without it the whole per-tenant Guardian surface goes stale.
"""

# Standard library imports
import os
import sys
import json
import time
import base64
import hashlib
import logging

# Networking imports
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

GUARDIAN_COLLECTION_NAME = "kv_trackme_configuration_guardian_alerts"
DEFAULT_AUDIT_INDEX = "trackme_audit"
AUDIT_SOURCETYPE = "trackme:audit:guardian"
AUDIT_SOURCE = "trackme_libs_guardian"

# Severity tiers. Keep the set small and unambiguous; the UI maps them to
# toast colour (warning→yellow, critical→red) and the audit index keeps the
# value verbatim for post-mortem queries.
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"
VALID_SEVERITIES = (SEVERITY_WARNING, SEVERITY_CRITICAL)

# Capabilities the tenant_owner service account must hold (direct or through
# role inheritance) for a Virtual Tenant's scheduled operations to succeed.
REQUIRED_TENANT_OWNER_CAPABILITIES = [
    "trackmeuseroperations",
    "trackmepoweroperations",
    "trackmeadminoperations",
    "schedule_search",
    "list_settings",
    "list_storage_passwords",
    "admin_all_objects",
]

# Check-type identifiers. All string-literal; callers should import these
# constants rather than hardcoding the strings.
CHECK_TENANT_OWNER_CAPABILITIES = "insufficient_tenant_owner_capabilities"
CHECK_ASSIGNED_INDEX_EXISTS = "assigned_index_does_not_exist"
CHECK_REMOTE_ACCOUNT_TOKEN_EXPIRY = "remote_account_token_expiring_soon"
CHECK_REMOTE_ACCOUNT_CONNECTIVITY = "remote_account_connectivity_degraded"
CHECK_AI_PROVIDER_UNREACHABLE = "ai_provider_unreachable"
CHECK_BACKUP_ARCHIVE_TOO_OLD = "backup_archive_too_old"
CHECK_BACKUP_RUN_INCOMPLETE = "backup_run_incomplete"
CHECK_HEALTH_TRACKER_EXECUTING = "health_tracker_not_executing"
CHECK_AI_FEED_LIFECYCLE_DELAY_CONFLICT = "ai_feed_lifecycle_delay_conflict"
CHECK_THRESHOLD_INTENT_DRIFT = "delay_threshold_drift_corrected"

# Thresholds for the token-expiry check.
#
# The check reads the JWT ``exp`` claim of the configured bearer token (the
# authoritative expiry, set by the issuer) and computes ``remaining = exp - now``.
# Warning / critical boundaries are then computed per-account as the MIN of a
# fixed-time ceiling and a fraction of the token's actual lifetime
# (``exp - iat``). The ceiling handles long-lived tokens ("7 days out" feels
# urgent for a 30-day token); the fraction handles short-lived tokens
# ("7 days out" is meaningless for a 3-day token — the warning would fire
# immediately after issuance and never clear, breaking self-healing).
#
# Effective warning = min(WARNING_CEILING, lifetime * WARNING_FRACTION)
# Effective critical = min(CRITICAL_CEILING, lifetime * CRITICAL_FRACTION)
#
# Examples:
#   * 30-day token → warn at 7d (ceiling), critical at 1d (ceiling)
#   * 7-day token  → warn at 2.1d (30% of lifetime), critical at 0.7d (10% of lifetime)
#   * 3-day token  → warn at 0.9d (30%), critical at 0.3d (10%)
#   * 1-day token  → warn at 7.2h (30%), critical at 2.4h (10%)
#
# When the JWT lacks ``iat`` (rare for Splunk-issued tokens), we fall back to
# ``token_rotation_frequency_days × 86400`` for the proportional component so
# the thresholds stay sensible.
TOKEN_EXPIRY_WARNING_CEILING_SECONDS = 7 * 24 * 3600   # 7 days
TOKEN_EXPIRY_CRITICAL_CEILING_SECONDS = 24 * 3600      # 1 day
TOKEN_EXPIRY_WARNING_FRACTION = 0.30                   # last 30% of token lifetime
TOKEN_EXPIRY_CRITICAL_FRACTION = 0.10                  # last 10% of token lifetime

# The health tracker runs every 5 minutes; we treat 6 missed cycles (30 min)
# as a hard signal of breakage (TIER_1 tasks always run, so execution time
# should refresh roughly every cycle).
HEALTH_TRACKER_STALE_SECONDS = 30 * 60

# Remote-account connectivity check — escalate from `warning` to `critical`
# once the account has been failing for longer than this window. The check
# tracks "failing since when" in the alert's own metadata (preserved across
# upserts) so the signal is stable even though we probe daily.
REMOTE_CONNECTIVITY_CRITICAL_SECONDS = 24 * 3600  # 24 hours

# Timeout applied to the per-account connectivity probe HTTP call. Needs to
# be generous enough to tolerate the test_remote_account's own internal
# connect+search timeouts (defaults: 15s + 300s) without the Guardian giving
# up before the probe itself reports. One probe per account per day.
REMOTE_CONNECTIVITY_PROBE_TIMEOUT_SECONDS = 360

# Backup archive staleness thresholds. The "warning" threshold is computed
# per-install as `cadence × BACKUP_CADENCE_WARN_MULTIPLIER` from the cron of
# the `trackme_backup_scheduler` saved search — so a daily backup warns at
# 36h, a 12-hourly backup warns at 18h, etc. Everything past
# BACKUP_CRITICAL_AGE_SECONDS escalates to `critical` regardless of cadence
# — a week-old backup is catastrophic for DR even if the admin set the
# cadence loosely.
BACKUP_SCHEDULER_SAVEDSEARCH = "trackme_backup_scheduler"
BACKUP_CADENCE_WARN_MULTIPLIER = 1.5
BACKUP_CRITICAL_AGE_SECONDS = 7 * 24 * 3600  # 7 days
BACKUP_DEFAULT_CADENCE_SECONDS = 86400       # fallback when cron can't be parsed


# -----------------------------------------------------------------------------
# Key helpers
# -----------------------------------------------------------------------------


def make_alert_key(check_type, scope_key):
    """Return a deterministic SHA256 hash key for ``check_type:scope_key``.

    Upserts remain idempotent: the same (check, scope) pair always produces
    the same ``_key`` so repeated detections overwrite rather than duplicate.
    """
    token = f"{check_type}:{scope_key}"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# -----------------------------------------------------------------------------
# Audit trail
# -----------------------------------------------------------------------------


def resolve_audit_index_name(service, default=DEFAULT_AUDIT_INDEX):
    """Resolve the configured ``trackme_audit_idx`` from ``trackme_settings``.

    Callers without ready access to ``reqinfo["trackme_conf"]`` (e.g. REST
    handlers) should use this helper so audit events still land in whatever
    index the admin configured rather than in the hardcoded default. Fails
    open to ``default`` if the setting can't be read.
    """
    try:
        settings_conf = service.confs["trackme_settings"]
        stanza = settings_conf["index_settings"]
        value = stanza.content.get("trackme_audit_idx")
        if value:
            return value
    except Exception:
        pass
    return default


def _emit_audit_event(service, audit_index_name, action, payload):
    """Write a structured audit event for a Guardian state transition.

    ``action`` is one of ``guardian_alert_created``, ``guardian_alert_updated``
    (severity or metadata changed), ``guardian_alert_cleared`` (self-heal).
    Failures are logged but never propagate — the Guardian must stay functional
    even if the audit index is misconfigured.
    """
    try:
        record = {"action": action, "audit_ts": time.time()}
        record.update(payload or {})
        audit_target = service.indexes[audit_index_name or DEFAULT_AUDIT_INDEX]
        audit_target.submit(
            event=json.dumps(record),
            source=AUDIT_SOURCE,
            sourcetype=AUDIT_SOURCETYPE,
        )
    except Exception as e:
        get_effective_logger().warning(
            f'guardian_audit_emit_failed action="{action}", '
            f'index="{audit_index_name}", exception="{str(e)}"'
        )


# -----------------------------------------------------------------------------
# KV collection helpers
# -----------------------------------------------------------------------------


def _get_collection(service):
    return service.kvstore[GUARDIAN_COLLECTION_NAME]


def _coerce_metadata(metadata):
    if isinstance(metadata, (dict, list)):
        return json.dumps(metadata)
    if metadata is None:
        return ""
    return str(metadata)


# Metadata keys that are expected to change on every detection cycle but do
# NOT represent a semantic state change. The upsert audit-dedup compares
# metadata payloads with these keys stripped — otherwise `guardian_alert_updated`
# events would fire on every daily run of time-bearing checks (remaining_seconds
# on the token-expiry check ticks down every cycle even when the admin's
# situation is identical). Whenever a new check embeds a ticking clock in its
# metadata, add the key here.
_VOLATILE_METADATA_KEYS = frozenset({
    "remaining_seconds",       # check_remote_account_token_expiring_soon —
                               # ticks down every cycle as the JWT approaches
                               # its ``exp`` claim; not a state change.
    "last_rotation_epoch",     # check_remote_account_token_expiring_soon
                               # (legacy field, retained for backward compat
                               # with prior alerts that haven't yet cleared)
    "staleness_seconds",       # check_health_tracker_not_executing
                               # AND check_backup_archive_too_old (same field semantics)
    "last_execution_epoch",    # check_health_tracker_not_executing
    "last_execution_iso",      # check_health_tracker_not_executing (derived)
    "failure_duration_seconds",  # check_remote_account_connectivity_degraded
    "last_error_message",      # check_remote_account_connectivity_degraded AND
                               # check_ai_provider_unreachable — error text may vary
                               # cycle-to-cycle (different downstream errors) even
                               # when the underlying condition is unchanged; the
                               # stable state signals are first_failure_mtime
                               # (connectivity) / severity+presence (AI)
    "response_time_sec",       # check_ai_provider_unreachable — latency varies
})


def _stable_metadata_payload(metadata_str):
    """Return a canonical string of the metadata with volatile keys removed.

    Used for audit-dedup only — the stored KV record keeps the full payload.
    Falls back to the raw input on non-JSON / non-dict metadata so comparisons
    still happen (verbatim) and we never accidentally swallow a genuine change.
    """
    if not metadata_str:
        return ""
    try:
        payload = json.loads(metadata_str)
    except Exception:
        return metadata_str
    if not isinstance(payload, dict):
        return json.dumps(payload, sort_keys=True)
    stable = {k: v for k, v in payload.items() if k not in _VOLATILE_METADATA_KEYS}
    return json.dumps(stable, sort_keys=True)


def upsert_guardian_alert(
    service,
    *,
    check_type,
    scope_key,
    severity,
    scope,
    tenant_id,
    subject,
    title,
    message,
    remediation,
    metadata,
    audit_index_name=None,
):
    """Insert-or-update a guardian alert record and emit an audit event.

    Notes:
      * ``metadata`` may be a dict or list; it is serialised to JSON so the KV
        schema can keep it as a plain string field (easy to query from SPL).
      * ``severity`` is validated against ``VALID_SEVERITIES``; an unknown value
        falls back to ``warning`` with a log warning (defensive — never block a
        detection on a bad severity string).
      * Audit emission compares the new record against the existing one so we
        only write ``guardian_alert_updated`` when something meaningful changed
        (severity or metadata), avoiding audit-index noise on every cycle.
    """
    if severity not in VALID_SEVERITIES:
        get_effective_logger().warning(
            f'guardian_invalid_severity check_type="{check_type}", severity="{severity}" — '
            f'falling back to "{SEVERITY_WARNING}"'
        )
        severity = SEVERITY_WARNING

    metadata_str = _coerce_metadata(metadata)
    key = make_alert_key(check_type, scope_key)
    # scope_key is persisted in the KV record so `dismiss_guardian_alert_by_key`
    # can emit it back out on audit events — the SHA256 `_key` is one-way so
    # without this we'd have no way to recover the original scope_key on a
    # UI dismissal, breaking audit-trail correlation.
    record = {
        "_key": key,
        "check_type": check_type,
        "severity": severity,
        "scope": scope,
        "scope_key": scope_key,
        "tenant_id": tenant_id or "",
        "subject": subject or "",
        "title": title,
        "message": message,
        "remediation": remediation,
        "metadata": metadata_str,
        "mtime": time.time(),
    }

    collection = _get_collection(service)

    # Look up the prior state so we can distinguish "created" from "updated"
    # and avoid audit noise when nothing changed.
    prior = None
    try:
        prior = collection.data.query_by_id(key)
    except Exception:
        prior = None

    try:
        collection.data.insert(json.dumps(record))
        action = "guardian_alert_created"
    except Exception:
        try:
            collection.data.update(key, json.dumps(record))
            if prior is None:
                # Insert raced with another writer and the update succeeded
                action = "guardian_alert_created"
            elif (
                prior.get("severity") != severity
                or _stable_metadata_payload(prior.get("metadata") or "")
                != _stable_metadata_payload(metadata_str)
            ):
                # Meaningful change (severity transition, or semantically
                # stable metadata changed — e.g. missing_capabilities list
                # shrinking). Time-bearing fields like remaining_seconds are
                # excluded from the comparison so routine daily re-detections
                # don't flood the audit index.
                action = "guardian_alert_updated"
            else:
                # Same content — skip audit to avoid noise
                action = None
        except Exception as e:
            get_effective_logger().error(
                f'guardian_upsert_failed check_type="{check_type}", scope_key="{scope_key}", '
                f'exception="{str(e)}"'
            )
            raise

    if action is not None:
        audit_payload = {
            "alert_key": key,
            "check_type": check_type,
            "scope": scope,
            "scope_key": scope_key,
            "tenant_id": tenant_id or "",
            "subject": subject or "",
            "severity": severity,
            "prior_severity": (prior or {}).get("severity") if prior else None,
            "title": title,
        }
        _emit_audit_event(service, audit_index_name, action, audit_payload)

    return key


def clear_guardian_alert(
    service, check_type, scope_key, audit_index_name=None
):
    """Delete a specific guardian alert by (check_type, scope_key). Idempotent.

    Returns True if a record was deleted, False if nothing existed. On an
    actual deletion, emits a ``guardian_alert_cleared`` audit event.
    """
    key = make_alert_key(check_type, scope_key)
    collection = _get_collection(service)
    # Look up prior state so the audit event carries meaningful context.
    prior = None
    try:
        prior = collection.data.query_by_id(key)
    except Exception:
        prior = None

    if prior is None:
        return False

    try:
        collection.data.delete_by_id(key)
    except Exception:
        # Record disappeared between the lookup and the delete — treat as no-op
        return False

    _emit_audit_event(
        service,
        audit_index_name,
        "guardian_alert_cleared",
        {
            "alert_key": key,
            "check_type": check_type,
            "scope": prior.get("scope"),
            "scope_key": scope_key,
            "tenant_id": prior.get("tenant_id", ""),
            "subject": prior.get("subject", ""),
            "severity": prior.get("severity"),
            "title": prior.get("title"),
        },
    )
    return True


def _recover_scope_key(prior):
    """Best-effort reconstruction of ``scope_key`` from a KV record.

    New records written by ``upsert_guardian_alert`` carry ``scope_key``
    directly. For legacy records (written before the field was added to the
    schema) fall back to the scope-specific convention every runner follows:
    tenant-scoped checks use ``tenant_id`` as the scope_key, system-scoped
    checks use ``subject``.
    """
    if not isinstance(prior, dict):
        return ""
    stored = prior.get("scope_key")
    if stored:
        return stored
    if prior.get("scope") == "tenant":
        return prior.get("tenant_id") or ""
    return prior.get("subject") or ""


def dismiss_guardian_alert_by_key(service, alert_key, audit_index_name=None):
    """Delete a Guardian alert by its ``_key`` (e.g. from a UI dismiss) while
    still emitting the ``guardian_alert_cleared`` audit event. Idempotent.

    Returns True if a record was deleted, False otherwise.
    """
    if not alert_key:
        return False
    collection = _get_collection(service)
    prior = None
    try:
        prior = collection.data.query_by_id(alert_key)
    except Exception:
        prior = None
    if prior is None:
        return False
    try:
        collection.data.delete_by_id(alert_key)
    except Exception:
        return False

    _emit_audit_event(
        service,
        audit_index_name,
        "guardian_alert_cleared",
        {
            "alert_key": alert_key,
            "check_type": prior.get("check_type"),
            "scope": prior.get("scope"),
            "scope_key": _recover_scope_key(prior),
            "tenant_id": prior.get("tenant_id", ""),
            "subject": prior.get("subject", ""),
            "severity": prior.get("severity"),
            "title": prior.get("title"),
            "reason": "dismissed_by_admin",
        },
    )
    return True


def clear_guardian_alerts_for_tenant(service, tenant_id, audit_index_name=None):
    """Delete every guardian alert attached to ``tenant_id``.

    Called on tenant deletion so orphan alerts don't linger in the UI.
    Returns the number of records deleted. Emits one audit event per deletion.
    """
    if not tenant_id:
        return 0
    collection = _get_collection(service)
    deleted = 0
    try:
        query = json.dumps({"tenant_id": str(tenant_id)})
        records = collection.data.query(query=query)
        for record in records:
            key = record.get("_key")
            if not key:
                continue
            try:
                collection.data.delete_by_id(key)
                deleted += 1
                _emit_audit_event(
                    service,
                    audit_index_name,
                    "guardian_alert_cleared",
                    {
                        "alert_key": key,
                        "check_type": record.get("check_type"),
                        "scope": record.get("scope"),
                        "scope_key": _recover_scope_key(record),
                        "tenant_id": record.get("tenant_id", ""),
                        "subject": record.get("subject", ""),
                        "severity": record.get("severity"),
                        "title": record.get("title"),
                        "reason": "tenant_deleted",
                    },
                )
            except Exception as e:
                get_effective_logger().warning(
                    f'guardian_cleanup_failed tenant_id="{tenant_id}", _key="{key}", '
                    f'exception="{str(e)}"'
                )
    except Exception as e:
        get_effective_logger().error(
            f'guardian_cleanup_query_failed tenant_id="{tenant_id}", exception="{str(e)}"'
        )
    return deleted


# -----------------------------------------------------------------------------
# Splunk capability lookup
# -----------------------------------------------------------------------------


def get_user_effective_capabilities(session_key, splunkd_uri, username):
    """Return the set of effective capabilities for ``username``.

    Splunk's ``/services/authentication/users/<username>`` endpoint returns
    ``entries[0].content.capabilities`` which is already the full set of
    capabilities the user holds directly *and* through role inheritance — the
    role-hierarchy resolution is done server-side.

    Returns None if the user cannot be resolved (missing user, API error) —
    callers should treat None as "cannot verify" and skip the check rather
    than raising a false-positive alert.
    """
    if not username or username in ("nobody",):
        return None

    header = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
    }
    # urlencode the username defensively (service accounts occasionally use @ or .)
    safe_username = requests.utils.quote(str(username), safe="")
    url = f"{splunkd_uri}/services/authentication/users/{safe_username}?output_mode=json"
    try:
        response = requests.get(url, headers=header, verify=False, timeout=30)
    except Exception as e:
        get_effective_logger().error(
            f'guardian_user_lookup_failed username="{username}", exception="{str(e)}"'
        )
        return None

    if response.status_code != 200:
        get_effective_logger().warning(
            f'guardian_user_lookup_non200 username="{username}", status={response.status_code}, '
            f'text="{response.text[:200]}"'
        )
        return None

    try:
        payload = response.json()
        entries = payload.get("entry", [])
        if not entries:
            return None
        caps = entries[0].get("content", {}).get("capabilities", []) or []
        return set(caps)
    except Exception as e:
        get_effective_logger().error(
            f'guardian_user_lookup_parse_failed username="{username}", exception="{str(e)}"'
        )
        return None


# -----------------------------------------------------------------------------
# Splunk index / data helpers
# -----------------------------------------------------------------------------


# Index-role slots TrackMe manages on a per-tenant basis. Each slot maps to
# a Splunk index name in the vtenant's ``tenant_idx_settings`` JSON dict. Keep
# this list aligned with the sibling auto-revert task in
# ``trackmetrackerhealth.py#check_tenants_indexes_settings`` and the fallback
# table in ``get_fallback_indexes`` there.
TENANT_IDX_ROLES = (
    "trackme_summary_idx",
    "trackme_audit_idx",
    "trackme_metric_idx",
    "trackme_notable_idx",
)


def _parse_tenant_idx_settings(tenant_record):
    """Return the tenant's role → index-name mapping.

    The canonical storage is the top-level ``tenant_idx_settings`` field on
    the vtenant KV record, JSON-encoded. Shape:

        {
          "trackme_summary_idx":  "trackme_summary",
          "trackme_audit_idx":    "trackme_audit",
          "trackme_metric_idx":   "trackme_metrics",
          "trackme_notable_idx":  "trackme_notable"
        }

    The helper also understands the two legacy/degenerate cases emitted by
    ``trackme_idx_for_tenant``:

      * the literal string ``"global"``  → returns ``"global"`` (caller decides)
      * the field missing/empty          → returns ``{}`` (no per-tenant override)

    Returns ``"global"`` or a dict. Non-string index values are dropped
    silently (the sibling auto-revert task logs + replaces them with
    fallbacks; we don't want to emit a noisy Guardian alert on malformed
    records — that's a different check's job).
    """
    if not tenant_record:
        return {}

    raw = tenant_record.get("tenant_idx_settings")
    if raw in (None, ""):
        return {}

    # Accept either a JSON string (typical storage path) or a pre-parsed dict
    # (some code paths decode before handing us the record).
    if isinstance(raw, str):
        if raw.strip().lower() == "global":
            return "global"
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
    elif isinstance(raw, dict):
        parsed = raw
    else:
        return {}

    if not isinstance(parsed, dict):
        return {}

    result = {}
    for role, index_name in parsed.items():
        if not isinstance(index_name, str):
            continue
        name = index_name.strip()
        if name:
            result[role] = name
    return result


def fetch_declared_indexes(session_key, splunkd_uri):
    """Return ``{index_name: {"datatype": "event"|"metric"}}`` for every Splunk
    index declared on the search head.

    We used to return a plain set of names, but the assigned-index check also
    needs to validate that ``trackme_metric_idx`` points at an index whose
    ``datatype == metric`` (a text index silently produces empty metric
    results). Callers that only need existence can do ``name in declared``
    because dict membership tests against the keys.

    Returns ``None`` on REST failure — callers treat that as "cannot verify"
    and skip the check rather than emit a false positive.
    """
    url = (
        f"{splunkd_uri}/services/data/indexes"
        "?output_mode=json&count=0&datatype=all"
    )
    header = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=header, verify=False, timeout=30)
    except Exception as e:
        get_effective_logger().error(
            f'guardian_index_lookup_failed exception="{str(e)}"'
        )
        return None

    if response.status_code != 200:
        get_effective_logger().warning(
            f'guardian_index_lookup_non200 status={response.status_code}, '
            f'text="{response.text[:200]}"'
        )
        return None

    try:
        payload = response.json()
        entries = payload.get("entry", []) or []
        declared = {}
        for e in entries:
            name = e.get("name")
            if not name:
                continue
            content = e.get("content", {}) or {}
            declared[name] = {"datatype": content.get("datatype") or "event"}
        return declared
    except Exception as e:
        get_effective_logger().error(
            f'guardian_index_lookup_parse_failed exception="{str(e)}"'
        )
        return None


# -----------------------------------------------------------------------------
# Check: insufficient_tenant_owner_capabilities
# -----------------------------------------------------------------------------


def check_tenant_owner_capabilities(
    session_key, splunkd_uri, service, tenant_record, audit_index_name=None
):
    """Run the tenant-owner capability check for a single tenant record.

    Skipped when:
      * the tenant is disabled (the owner cannot degrade anything)
      * the tenant_owner is missing or equals "nobody" (no service account)
      * the capability lookup fails (no false positives)

    Returns a dict describing the outcome.
    """
    tenant_id = str(tenant_record.get("tenant_id", "")) if tenant_record else ""
    outcome = {
        "status": "skipped",
        "tenant_id": tenant_id,
        "subject": None,
        "missing_capabilities": None,
        "reason": None,
    }

    if not tenant_id:
        outcome["reason"] = "missing_tenant_id"
        return outcome

    tenant_status = str(tenant_record.get("tenant_status") or "").lower()
    if tenant_status != "enabled":
        outcome["reason"] = "tenant_disabled"
        if clear_guardian_alert(
            service, CHECK_TENANT_OWNER_CAPABILITIES, tenant_id, audit_index_name
        ):
            outcome["status"] = "alert_cleared"
        return outcome

    tenant_owner = tenant_record.get("tenant_owner")
    if not tenant_owner or str(tenant_owner).strip().lower() in ("", "nobody"):
        outcome["reason"] = "no_service_account"
        if clear_guardian_alert(
            service, CHECK_TENANT_OWNER_CAPABILITIES, tenant_id, audit_index_name
        ):
            outcome["status"] = "alert_cleared"
        return outcome

    outcome["subject"] = str(tenant_owner)

    capabilities = get_user_effective_capabilities(
        session_key, splunkd_uri, tenant_owner
    )
    if capabilities is None:
        outcome["reason"] = "capability_lookup_failed"
        return outcome

    missing = [
        cap for cap in REQUIRED_TENANT_OWNER_CAPABILITIES if cap not in capabilities
    ]
    outcome["missing_capabilities"] = missing

    if not missing:
        if clear_guardian_alert(
            service, CHECK_TENANT_OWNER_CAPABILITIES, tenant_id, audit_index_name
        ):
            outcome["status"] = "alert_cleared"
        else:
            outcome["status"] = "ok"
        return outcome

    tenant_alias = tenant_record.get("tenant_alias") or tenant_id
    title = "Insufficient capabilities for tenant owner"
    message = (
        f'The service account "{tenant_owner}" assigned as owner of tenant '
        f'"{tenant_alias}" is missing {len(missing)} required capabilit'
        f'{"y" if len(missing) == 1 else "ies"}. Scheduled TrackMe operations '
        f"running under this account will silently degrade until this is fixed."
    )
    remediation = (
        f'Grant the missing capabilit{"y" if len(missing) == 1 else "ies"} '
        f'({", ".join(missing)}) to "{tenant_owner}" — either directly or through '
        f"a role it inherits. Splunk role capabilities resolve transitively, so "
        f"adding them to any inherited role is sufficient."
    )
    metadata = {
        "tenant_alias": tenant_alias,
        "required_capabilities": REQUIRED_TENANT_OWNER_CAPABILITIES,
        "missing_capabilities": missing,
        "recommended_actions": [
            f'Open Splunk Settings → Access Controls → Roles and ensure a role inherited by '
            f'"{tenant_owner}" grants: {", ".join(missing)}.',
            f"Rerun the tenant health tracker or POST to /trackme/v2/configuration/admin/run_guardian_checks "
            f"with check_type='{CHECK_TENANT_OWNER_CAPABILITIES}' to confirm resolution.",
        ],
    }

    upsert_guardian_alert(
        service,
        check_type=CHECK_TENANT_OWNER_CAPABILITIES,
        scope_key=tenant_id,
        severity=SEVERITY_WARNING,
        scope="tenant",
        tenant_id=tenant_id,
        subject=str(tenant_owner),
        title=title,
        message=message,
        remediation=remediation,
        metadata=metadata,
        audit_index_name=audit_index_name,
    )
    outcome["status"] = "alert_created"
    return outcome


# -----------------------------------------------------------------------------
# Check: assigned_index_does_not_exist
# -----------------------------------------------------------------------------


def check_assigned_index_exists(
    session_key,
    splunkd_uri,
    service,
    tenant_record,
    declared_indexes=None,
    audit_index_name=None,
):
    """Verify each per-tenant index slot points at an index that exists on the
    search head (and, for the metric slot, that the datatype is metric).

    The tenant stores its index configuration in ``tenant_idx_settings`` —
    a JSON dict keyed by role:

        trackme_summary_idx  → summary events
        trackme_audit_idx    → audit events
        trackme_metric_idx   → scoring / KPI metrics (MUST have datatype=metric)
        trackme_notable_idx  → notable events

    For every slot whose value is either missing from the SH catalogue, or
    points at an index whose ``datatype`` doesn't match what the slot needs,
    the check emits a ``warning`` alert. Skipped conditions:

      * tenant disabled                         → clear stale alert
      * tenant_idx_settings empty or "global"   → nothing tenant-specific to
                                                  validate (global indexes are
                                                  validated by other code
                                                  paths); clear stale alert
      * /services/data/indexes call failed      → leave prior alert untouched

    ``declared_indexes`` is expected as ``{name: {"datatype": "event"|"metric"}}``
    and is pre-fetched fleet-wide by ``run_checks`` via the registry's
    ``pre_run`` hook. Callers invoking this runner directly can pass ``None``
    and the runner will fetch its own catalogue.
    """
    tenant_id = str(tenant_record.get("tenant_id", "")) if tenant_record else ""
    outcome = {
        "status": "skipped",
        "tenant_id": tenant_id,
        "subject": None,
        "assigned_index_settings": None,
        "misconfigured_roles": None,
        "missing_indexes": None,
        "reason": None,
    }

    if not tenant_id:
        outcome["reason"] = "missing_tenant_id"
        return outcome

    tenant_status = str(tenant_record.get("tenant_status") or "").lower()
    if tenant_status != "enabled":
        outcome["reason"] = "tenant_disabled"
        if clear_guardian_alert(
            service, CHECK_ASSIGNED_INDEX_EXISTS, tenant_id, audit_index_name
        ):
            outcome["status"] = "alert_cleared"
        return outcome

    parsed = _parse_tenant_idx_settings(tenant_record)
    if parsed == "global":
        outcome["reason"] = "uses_global_indexes"
        if clear_guardian_alert(
            service, CHECK_ASSIGNED_INDEX_EXISTS, tenant_id, audit_index_name
        ):
            outcome["status"] = "alert_cleared"
        return outcome
    if not parsed:
        outcome["reason"] = "no_indexes_configured"
        if clear_guardian_alert(
            service, CHECK_ASSIGNED_INDEX_EXISTS, tenant_id, audit_index_name
        ):
            outcome["status"] = "alert_cleared"
        return outcome

    outcome["assigned_index_settings"] = dict(parsed)

    if declared_indexes is None:
        declared_indexes = fetch_declared_indexes(session_key, splunkd_uri)
    if declared_indexes is None:
        outcome["reason"] = "index_lookup_failed"
        return outcome

    # Legacy shape support: an older caller may hand us a plain set of index
    # names rather than the name→datatype dict. Existence still checks via
    # ``in``, but the datatype enforcement on the metric slot is only
    # meaningful when we have the richer dict shape — track that flag for
    # the metric branch below.
    has_datatype_info = isinstance(declared_indexes, dict)

    misconfigured_roles = {}
    missing_index_names = []

    # Iterate the authoritative `TENANT_IDX_ROLES` contract rather than
    # `parsed.items()` — that way we:
    #   * silently ignore any spurious / unknown keys in `tenant_idx_settings`
    #     (which would otherwise get validated as if they were real slots),
    #   * only validate a role when the tenant has configured it; a missing
    #     slot is not a misconfiguration in itself (Splunk will fall back to
    #     TrackMe's default index for that role at runtime — logged by the
    #     sibling `check_tenants_indexes_settings` task, not Guardian-worthy).
    for role in TENANT_IDX_ROLES:
        idx_name = parsed.get(role)
        if not idx_name:
            continue

        if idx_name not in declared_indexes:
            misconfigured_roles[role] = {
                "configured_index": idx_name,
                "reason": "index_not_declared",
            }
            missing_index_names.append(idx_name)
            continue

        # Metric slot requires datatype=metric; only enforceable when the
        # caller handed us the richer `{name: {"datatype": ...}}` shape.
        if role == "trackme_metric_idx" and has_datatype_info:
            info = declared_indexes.get(idx_name) or {}
            if info.get("datatype") != "metric":
                misconfigured_roles[role] = {
                    "configured_index": idx_name,
                    "reason": "wrong_datatype",
                    "actual_datatype": info.get("datatype") or "event",
                    "expected_datatype": "metric",
                }

    # Dedup + sort once and reuse in both the REST-delta outcome and the
    # stored alert metadata — otherwise two role slots pointing at the same
    # missing index produce duplicate entries in the API response while the
    # KV record (which uses a second `sorted(set(...))` below) is clean.
    missing_indexes_unique = sorted(set(missing_index_names))
    outcome["misconfigured_roles"] = misconfigured_roles
    outcome["missing_indexes"] = missing_indexes_unique

    if not misconfigured_roles:
        if clear_guardian_alert(
            service, CHECK_ASSIGNED_INDEX_EXISTS, tenant_id, audit_index_name
        ):
            outcome["status"] = "alert_cleared"
        else:
            outcome["status"] = "ok"
        return outcome

    tenant_alias = tenant_record.get("tenant_alias") or tenant_id
    broken_roles = sorted(misconfigured_roles.keys())
    broken_count = len(broken_roles)

    # Build a compact per-role summary like:
    #   trackme_summary_idx → "trackme_summary_bad" (index not declared)
    per_role_lines = []
    for role in broken_roles:
        detail = misconfigured_roles[role]
        if detail["reason"] == "wrong_datatype":
            per_role_lines.append(
                f'{role} → "{detail["configured_index"]}" '
                f'(datatype is {detail.get("actual_datatype", "event")}, '
                f'must be metric)'
            )
        else:
            per_role_lines.append(
                f'{role} → "{detail["configured_index"]}" '
                f'(index not declared on this search head)'
            )

    title = "Tenant index-slot points at a missing or misconfigured index"
    message = (
        f'Tenant "{tenant_alias}" has {broken_count} index slot'
        f'{"" if broken_count == 1 else "s"} misconfigured: '
        f'{"; ".join(per_role_lines)}. The tenant health tracker falls back '
        f'to TrackMe\'s default indexes for these slots, so the admin\'s '
        f'original configuration is not in effect — any data written with '
        f'the expectation that it would land in the configured index is '
        f'being routed to the fallback (or, for a metric slot pointing at '
        f'an event index, silently discarded).'
    )
    remediation = (
        f'For each broken slot listed above, either (a) create the missing '
        f'Splunk index in Settings → Indexes with the correct datatype '
        f'(event for summary / audit / notable, metric for trackme_metric_idx), '
        f'or (b) re-assign the slot to an existing, correctly-typed index via '
        f'the tenant configuration. The next run of the check clears the alert.'
    )
    metadata = {
        "tenant_alias": tenant_alias,
        "tenant_idx_settings": dict(parsed),
        "misconfigured_roles": misconfigured_roles,
        "missing_indexes": missing_indexes_unique,
        "recommended_actions": [
            (
                f'Fix the {broken_count} misconfigured index slot'
                f'{"" if broken_count == 1 else "s"}: '
                + "; ".join(per_role_lines)
            ),
            "Verify the index exists in Settings → Indexes and has the right datatype (event vs metric).",
            (
                "Rerun POST /trackme/v2/configuration/admin/run_guardian_checks "
                f"with check_type='{CHECK_ASSIGNED_INDEX_EXISTS}' to confirm the fix."
            ),
        ],
    }

    upsert_guardian_alert(
        service,
        check_type=CHECK_ASSIGNED_INDEX_EXISTS,
        scope_key=tenant_id,
        severity=SEVERITY_WARNING,
        scope="tenant",
        tenant_id=tenant_id,
        subject=tenant_alias,
        title=title,
        message=message,
        remediation=remediation,
        metadata=metadata,
        audit_index_name=audit_index_name,
    )
    outcome["status"] = "alert_created"
    return outcome


# -----------------------------------------------------------------------------
# Check: remote_account_token_expiring_soon
# -----------------------------------------------------------------------------


def _fetch_remote_accounts(session_key, splunkd_uri):
    """Return the list of remote_account entries with their config content."""
    url = f"{splunkd_uri}/servicesNS/nobody/trackme/trackme_account?output_mode=json&count=0"
    header = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=header, verify=False, timeout=30)
    except Exception as e:
        get_effective_logger().error(
            f'guardian_remote_account_list_failed exception="{str(e)}"'
        )
        return None
    if response.status_code != 200:
        get_effective_logger().warning(
            f'guardian_remote_account_list_non200 status={response.status_code}'
        )
        return None
    try:
        return response.json().get("entry", []) or []
    except Exception as e:
        get_effective_logger().error(f'guardian_remote_account_list_parse_failed exception="{str(e)}"')
        return None


def _coerce_int(value, default=0):
    try:
        return int(float(value))
    except Exception:
        return default


def _coerce_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _decode_jwt_claims(token):
    """Return the JWT payload claims as a dict, or ``None`` if the input is not
    a decodable JWT.

    Splunk-issued bearer tokens (``POST /services/authorization/tokens``) are
    JWS-signed JWTs with three base64url-encoded segments separated by ``.``.
    We never verify the signature here — verification is the issuer's job and
    a tampered token would fail at the auth layer of the remote Splunk anyway.
    What we *do* need is the ``exp`` claim (and ideally ``iat`` and ``aud``),
    which lives in the middle segment.

    Defensive on purpose: an admin may have configured a non-JWT bearer
    credential (an opaque key from an external IdP, for example). In that
    case we return ``None`` so the caller can skip cleanly rather than
    forcing a misleading expiry alert.
    """
    if not token or not isinstance(token, str):
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload_segment = parts[1]
    if not payload_segment:
        return None
    # JWT uses base64url WITHOUT padding; restore padding before decoding.
    padding = "=" * (-len(payload_segment) % 4)
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_segment + padding)
        claims = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return None
    if not isinstance(claims, dict):
        return None
    return claims


def _hash_token_id(token):
    """Return a short SHA256 fingerprint of the token for traceability.

    The full token is sensitive material (raw bearer credential); the
    truncated hash is safe to embed in alert metadata, audit events, and
    the AI-Assistant context so admins can correlate "which token instance
    triggered this alert" without ever surfacing the credential itself.
    """
    if not token or not isinstance(token, str):
        return ""
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return digest[:12]


def _resolve_bearer_token(service, account_name):
    """Read the configured bearer token for ``account_name`` from
    ``storage_passwords``.

    Wraps the existing ``get_bearer_token`` helper from ``trackme_libs`` so we
    centralise the credential-realm format in one place. Returns ``None`` if
    the account has no stored token (configuration error) or if access fails.
    """
    try:
        from trackme_libs import get_bearer_token  # local import: avoids
        # circular import at module load time and keeps the Guardian library
        # self-contained for callers that only need its KV/audit helpers.
    except Exception as e:
        get_effective_logger().warning(
            f'guardian_bearer_token_import_failed exception="{str(e)}"'
        )
        return None
    try:
        return get_bearer_token(service.storage_passwords, account_name)
    except Exception as e:
        get_effective_logger().warning(
            f'guardian_bearer_token_read_failed account="{account_name}", '
            f'exception="{str(e)}"'
        )
        return None


def check_remote_account_token_expiry(
    session_key, splunkd_uri, service, audit_index_name=None
):
    """System-scoped: verify each remote account's actual bearer-token expiry.

    Authoritative source: the JWT ``exp`` claim of the configured bearer
    token. Splunk's ``/services/authorization/tokens`` issues JWS-signed JWTs;
    we decode the payload locally, read ``exp``, and compute
    ``remaining = exp - now``. This replaces the legacy
    ``mtime + rotation_frequency`` heuristic, which conflated TrackMe's
    rotation cadence with the token's actual lifetime and produced
    false-positive "expired" alerts whenever a rotation cycle drifted past
    the configured frequency (or duplicate KV rows skewed the picked mtime).

    Per-account decision matrix (rotation enabled):

      * JWT undecodable / not a JWT       → skip (``unable_to_decode_jwt``),
                                             clear any stale alert. Auth
                                             failures of non-JWT credentials
                                             are caught by the connectivity
                                             check.
      * JWT lacks ``exp`` claim           → skip (``missing_exp_claim``),
                                             clear any stale alert.
      * ``remaining <= 0``                → critical (``expired``)
      * ``remaining <= critical_threshold`` → critical (``expires_soon_critical``)
      * ``remaining <= warn_threshold``   → warning  (``expires_soon_warning``)
      * otherwise                         → clear

    Thresholds are proportional to the JWT's own lifetime (``exp - iat``)
    when ``iat`` is present, falling back to
    ``token_rotation_frequency_days × 86400`` otherwise. Capped by fixed
    ceilings (7d warning, 1d critical) so long-lived tokens still get an
    early heads-up without short-lived tokens permanently firing the warning
    band immediately after issuance.

    Returns a list of per-account outcomes (one element per account). The
    list shape is preserved across all early-exit paths so ``run_checks`` can
    flatten outcomes into accurate ``counts.created`` / ``cleared`` deltas
    without special-casing.
    """
    outcomes = []
    entries = _fetch_remote_accounts(session_key, splunkd_uri)
    if entries is None:
        return [{"status": "skipped", "reason": "remote_account_list_failed"}]

    now = time.time()

    for entry in entries:
        account_name = entry.get("name") or ""
        if not account_name:
            continue
        content = entry.get("content", {}) or {}

        rotation_enabled = str(content.get("token_rotation_enablement") or "0").lower() in (
            "1", "true", "yes", "on",
        )
        if not rotation_enabled:
            # Token rotation not enforced for this account — TrackMe never
            # generated a JWT for it and we have no expectation about the
            # underlying credential's lifetime. Clear any stale alert.
            cleared = clear_guardian_alert(
                service, CHECK_REMOTE_ACCOUNT_TOKEN_EXPIRY, account_name, audit_index_name
            )
            outcomes.append({
                "status": "alert_cleared" if cleared else "skipped",
                "account": account_name,
                "reason": "token_rotation_disabled",
            })
            continue

        # token_rotation_frequency is configured as a number of days by the UCC
        # globalConfig; treat it defensively (some builds store seconds). Used
        # only as a fallback for the proportional threshold when the JWT lacks
        # an ``iat`` claim.
        rotation_raw = content.get("token_rotation_frequency")
        rotation_days = _coerce_int(rotation_raw, default=0)
        if rotation_days <= 0:
            outcomes.append({
                "status": "skipped",
                "account": account_name,
                "reason": "invalid_rotation_frequency",
            })
            continue

        bearer_token = _resolve_bearer_token(service, account_name)
        if not bearer_token:
            # No stored credential — distinct from a non-JWT credential. Clear
            # any prior alert; the operator-visible signal here belongs to
            # whatever flow normally maintains the account configuration.
            cleared = clear_guardian_alert(
                service, CHECK_REMOTE_ACCOUNT_TOKEN_EXPIRY, account_name, audit_index_name
            )
            outcomes.append({
                "status": "alert_cleared" if cleared else "skipped",
                "account": account_name,
                "reason": "no_stored_bearer_token",
            })
            continue

        claims = _decode_jwt_claims(bearer_token)
        if claims is None:
            # Non-JWT credential (e.g. opaque IdP key). Skip cleanly — auth
            # failures are detected by the connectivity check
            # (``remote_account_connectivity_degraded``) end-to-end.
            cleared = clear_guardian_alert(
                service, CHECK_REMOTE_ACCOUNT_TOKEN_EXPIRY, account_name, audit_index_name
            )
            outcomes.append({
                "status": "alert_cleared" if cleared else "skipped",
                "account": account_name,
                "reason": "unable_to_decode_jwt",
            })
            continue

        exp = claims.get("exp")
        try:
            exp_epoch = int(exp)
        except (TypeError, ValueError):
            exp_epoch = None
        if not exp_epoch:
            # JWT without an ``exp`` claim is unusual (Splunk always sets one)
            # but possible for tokens issued by an external IdP with a
            # non-expiring policy. Treat as "no expiry to check".
            cleared = clear_guardian_alert(
                service, CHECK_REMOTE_ACCOUNT_TOKEN_EXPIRY, account_name, audit_index_name
            )
            outcomes.append({
                "status": "alert_cleared" if cleared else "skipped",
                "account": account_name,
                "reason": "missing_exp_claim",
            })
            continue

        iat = claims.get("iat")
        try:
            iat_epoch = int(iat)
        except (TypeError, ValueError):
            iat_epoch = None
        # Token lifetime drives proportional thresholds when available; fall
        # back to the configured rotation frequency to keep behaviour sane on
        # tokens that omit ``iat``.
        rotation_seconds_fallback = rotation_days * 24 * 3600
        if iat_epoch and exp_epoch > iat_epoch:
            lifetime_seconds = exp_epoch - iat_epoch
        else:
            lifetime_seconds = rotation_seconds_fallback

        remaining = exp_epoch - now

        # Compute per-account thresholds so short-lived tokens don't trip a
        # permanent warning the moment they're issued.
        warn_threshold = min(
            TOKEN_EXPIRY_WARNING_CEILING_SECONDS,
            lifetime_seconds * TOKEN_EXPIRY_WARNING_FRACTION,
        )
        critical_threshold = min(
            TOKEN_EXPIRY_CRITICAL_CEILING_SECONDS,
            lifetime_seconds * TOKEN_EXPIRY_CRITICAL_FRACTION,
        )

        severity = None
        if remaining <= 0:
            severity = SEVERITY_CRITICAL
            expiry_state = "expired"
        elif remaining <= critical_threshold:
            severity = SEVERITY_CRITICAL
            expiry_state = "expires_soon_critical"
        elif remaining <= warn_threshold:
            severity = SEVERITY_WARNING
            expiry_state = "expires_soon_warning"
        else:
            # Plenty of time left — clear any prior alert.
            cleared = clear_guardian_alert(
                service,
                CHECK_REMOTE_ACCOUNT_TOKEN_EXPIRY,
                account_name,
                audit_index_name,
            )
            outcomes.append({
                "status": "alert_cleared" if cleared else "ok",
                "account": account_name,
                "remaining_seconds": int(remaining),
                "exp_epoch": exp_epoch,
            })
            continue

        # Build a clear human-readable message. Python's floor division rounds
        # towards negative infinity, so we can't reuse ``remaining // 86400``
        # on an already-expired token (``remaining < 0``). Compute the
        # magnitude from ``abs(remaining)`` and carry the sign in the phrasing.
        abs_remaining = abs(remaining)
        abs_days = int(abs_remaining // 86400)
        abs_hours = int(abs_remaining // 3600)
        if remaining <= 0:
            if abs_days >= 1:
                human_remaining = f"{abs_days} day(s) ago"
            elif abs_hours >= 1:
                human_remaining = f"{abs_hours} hour(s) ago"
            else:
                human_remaining = "less than 1 hour ago"
        else:
            if abs_days >= 1:
                human_remaining = f"{abs_days} day(s)"
            elif abs_hours >= 1:
                human_remaining = f"{abs_hours} hour(s)"
            else:
                human_remaining = "less than 1 hour"

        title = (
            "Remote account token expired"
            if expiry_state == "expired"
            else "Remote account token expiring soon"
        )
        message = (
            f'The bearer token for remote account "{account_name}" '
            + ("has expired " + human_remaining if expiry_state == "expired"
               else f"will expire in {human_remaining}")
            + ". Once expired, all TrackMe operations that depend on this "
            "remote account (searches, entity tracking, alerting) will fail."
        )
        remediation = (
            f'Rotate the bearer token for "{account_name}" from Configuration → '
            f"Accounts. If you use an external identity provider, refresh the "
            f"token there first, then update the account's credentials in TrackMe. "
            f"After rotation the next daily maintenance cycle clears the alert."
        )

        # Best-effort ISO timestamp for human readers / log queries.
        try:
            exp_iso = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(exp_epoch)
            )
        except Exception:
            exp_iso = ""

        token_audience = claims.get("aud") or ""
        if not isinstance(token_audience, str):
            try:
                token_audience = json.dumps(token_audience)
            except Exception:
                token_audience = str(token_audience)

        metadata = {
            "account": account_name,
            "expiry_state": expiry_state,
            "token_exp_epoch": exp_epoch,
            "token_exp_iso": exp_iso,
            "token_iat_epoch": iat_epoch or 0,
            "token_audience": token_audience,
            # Truncated SHA256 of the bearer token — safe to surface in
            # metadata / audit events, lets admins correlate "which token
            # instance" without ever exposing the raw credential.
            "token_id_hash": _hash_token_id(bearer_token),
            "rotation_frequency_days": rotation_days,
            "remaining_seconds": int(remaining),
            # Per-account thresholds so AI agents / admins can reason about
            # why this specific account tripped at its specific remaining
            # time. Stable across cycles (depend only on token lifetime),
            # so they don't need to be in ``_VOLATILE_METADATA_KEYS``.
            "warn_threshold_seconds": int(warn_threshold),
            "critical_threshold_seconds": int(critical_threshold),
            "lifetime_seconds": int(lifetime_seconds),
            "recommended_actions": [
                f'Open Configuration → Accounts and rotate the bearer token for "{account_name}".',
                "Confirm the token is accepted by running POST /trackme/v2/configuration/test_remote_account.",
                f"Rerun POST /trackme/v2/configuration/admin/run_guardian_checks with check_type='{CHECK_REMOTE_ACCOUNT_TOKEN_EXPIRY}' to clear the alert.",
            ],
        }

        upsert_guardian_alert(
            service,
            check_type=CHECK_REMOTE_ACCOUNT_TOKEN_EXPIRY,
            scope_key=account_name,
            severity=severity,
            scope="system",
            tenant_id="",
            subject=account_name,
            title=title,
            message=message,
            remediation=remediation,
            metadata=metadata,
            audit_index_name=audit_index_name,
        )
        outcomes.append({
            "status": "alert_created",
            "account": account_name,
            "severity": severity,
            "expiry_state": expiry_state,
            "remaining_seconds": int(remaining),
            "exp_epoch": exp_epoch,
        })

    # Empty list only happens when there are zero remote accounts configured;
    # return a single-element list so callers don't have to special-case an
    # empty response.
    if not outcomes:
        return [{"status": "ok", "reason": "no_remote_accounts"}]
    return outcomes


# -----------------------------------------------------------------------------
# Check: remote_account_connectivity_degraded
# -----------------------------------------------------------------------------


def _probe_remote_account(session_key, splunkd_uri, account_name):
    """Call the user-level `test_remote_account` endpoint for a single account.

    Returns ``(success: bool, error_message: str or None)``. The endpoint
    already exercises the full connectivity path (URL resolution, auth,
    remote-search smoke test) so we don't need to replicate any of that
    here — we just interpret the response.
    """
    header = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
    }
    url = f"{splunkd_uri}/services/trackme/v2/configuration/test_remote_account"
    body = json.dumps({"account": account_name})
    try:
        response = requests.post(
            url,
            headers=header,
            data=body,
            verify=False,
            timeout=REMOTE_CONNECTIVITY_PROBE_TIMEOUT_SECONDS,
        )
    except Exception as e:
        return False, f"probe request exception: {str(e)}"

    # Parse the JSON payload best-effort so we can surface the handler's own
    # error message in the alert instead of just HTTP 500.
    parsed = None
    try:
        parsed = response.json()
    except Exception:
        parsed = None

    if response.status_code == 200:
        if isinstance(parsed, dict):
            # Splunk wraps the handler return in {"payload": {...}}; support
            # both the wrapped and un-wrapped shape since other code paths
            # in the codebase flip between the two.
            inner = parsed.get("payload") if "payload" in parsed else parsed
            if isinstance(inner, dict) and inner.get("status") == "success":
                return True, None
            error_message = (
                (inner.get("message") if isinstance(inner, dict) else None)
                or "probe returned a non-success payload"
            )
            return False, error_message
        return True, None  # 200 with an un-parseable body — treat as success

    # Non-200 path: prefer the handler-provided message when it's available.
    if isinstance(parsed, dict):
        inner = parsed.get("payload") if "payload" in parsed else parsed
        if isinstance(inner, dict):
            message = inner.get("message")
            if message:
                return False, str(message)
        if parsed.get("message"):
            return False, str(parsed["message"])
    return False, f"HTTP {response.status_code}: {response.text[:200]}"


def check_remote_account_connectivity(
    session_key, splunkd_uri, service, audit_index_name=None
):
    """System-scoped: probe every remote account's connectivity and alert on
    degraded / broken accounts.

    For each account with `trackme_account` stanza:
      * probe `POST /trackme/v2/configuration/test_remote_account`
      * on success                 → clear any prior alert (self-heal)
      * on first failure           → upsert a `warning` alert,
                                     stamp ``first_failure_mtime = now``
      * on continued failure       → preserve ``first_failure_mtime`` from
                                     the prior alert; promote to ``critical``
                                     once the failure window exceeds
                                     ``REMOTE_CONNECTIVITY_CRITICAL_SECONDS``
                                     (default 24h)

    The failure-since stamp lives in the alert's metadata (not the KV
    record's top-level fields) and is carried forward across upserts, so
    the severity transition is deterministic without needing to extend the
    remote-account token KV schema. ``first_failure_mtime`` is semantically
    stable (it does NOT update each cycle while the failure persists), so it
    stays out of ``_VOLATILE_METADATA_KEYS`` and participates in the normal
    audit-dedup — but since it only ever changes when a new failure cycle
    starts (i.e. after a prior clear), it never produces spurious
    `guardian_alert_updated` events.

    Returns a **list** of per-account outcomes so ``run_checks`` can flatten
    into accurate delta counts. Early-exit returns a single-element list so
    the contract stays uniform.
    """
    entries = _fetch_remote_accounts(session_key, splunkd_uri)
    if entries is None:
        return [{"status": "skipped", "reason": "remote_account_list_failed"}]

    collection = _get_collection(service)
    outcomes = []
    now = time.time()

    for entry in entries:
        account_name = entry.get("name") or ""
        if not account_name:
            continue

        probe_success, probe_error = _probe_remote_account(
            session_key, splunkd_uri, account_name
        )

        if probe_success:
            cleared = clear_guardian_alert(
                service,
                CHECK_REMOTE_ACCOUNT_CONNECTIVITY,
                account_name,
                audit_index_name,
            )
            outcomes.append({
                "status": "alert_cleared" if cleared else "ok",
                "account": account_name,
            })
            continue

        # Probe failed — look up prior alert to preserve first_failure_mtime
        # and decide on severity. If no prior alert exists, this is the first
        # failure in a new cycle.
        prior = None
        try:
            prior_key = make_alert_key(CHECK_REMOTE_ACCOUNT_CONNECTIVITY, account_name)
            prior = collection.data.query_by_id(prior_key)
        except Exception:
            prior = None

        first_failure_mtime = now
        if prior:
            try:
                prior_metadata = json.loads(prior.get("metadata") or "{}")
            except Exception:
                prior_metadata = {}
            prior_first_failure = _coerce_float(
                prior_metadata.get("first_failure_mtime"), default=0.0
            )
            if prior_first_failure > 0:
                first_failure_mtime = prior_first_failure

        failure_duration = now - first_failure_mtime
        if failure_duration >= REMOTE_CONNECTIVITY_CRITICAL_SECONDS:
            severity = SEVERITY_CRITICAL
            severity_rationale = (
                f"persistently failing for more than "
                f"{int(REMOTE_CONNECTIVITY_CRITICAL_SECONDS // 3600)} hours"
            )
        else:
            severity = SEVERITY_WARNING
            # Derive the rationale from the actual failure duration so an
            # alert that has been failing for 20h doesn't keep rendering
            # "first cycle of failure (may be transient)" in its user-facing
            # message. The "first cycle" wording is reserved for the fresh-
            # detection window (< 60s since first_failure_mtime was stamped,
            # which in practice means "this very invocation created it").
            if failure_duration < 60:
                severity_rationale = "first cycle of failure (may be transient)"
            else:
                crit_hours = int(REMOTE_CONNECTIVITY_CRITICAL_SECONDS // 3600)
                hours = int(failure_duration // 3600)
                if hours >= 1:
                    unit_label = f"{hours} hour(s)"
                else:
                    minutes = int(failure_duration // 60)
                    unit_label = f"{minutes} minute(s)"
                severity_rationale = (
                    f"failing for {unit_label} "
                    f"(below the {crit_hours}h critical threshold)"
                )

        first_failure_iso = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(first_failure_mtime)
        )

        title = (
            "Remote account connectivity degraded (persistent)"
            if severity == SEVERITY_CRITICAL
            else "Remote account connectivity degraded"
        )
        message = (
            f'The connectivity probe to remote account "{account_name}" is '
            f'failing ({severity_rationale}; first observed at '
            f'{first_failure_iso}). The tracker and alerting searches that '
            f'depend on this account will fail until connectivity is restored. '
            f'Last probe error: {probe_error or "unknown"}.'
        )
        remediation = (
            f'1) Verify the remote Splunk endpoint is reachable from this '
            f'search head (network, firewall, DNS). '
            f'2) Confirm the bearer token for "{account_name}" is still valid '
            f'on the remote deployment (rotate via Configuration → Accounts '
            f'if needed — see also the `remote_account_token_expiring_soon` '
            f'Guardian check). '
            f'3) Inspect $SPLUNK_HOME/var/log/splunk/splunkd.log and the '
            f'`splunkremotesearch` command logs for the full stack of errors. '
            f'4) Once fixed, run POST /trackme/v2/configuration/test_remote_account '
            f'with body {{"account": "{account_name}"}} to verify before '
            f'relying on the next scheduled cycle.'
        )
        metadata = {
            "account": account_name,
            "first_failure_mtime": first_failure_mtime,
            "first_failure_iso": first_failure_iso,
            "failure_duration_seconds": int(failure_duration),
            "severity_escalation_threshold_seconds": (
                REMOTE_CONNECTIVITY_CRITICAL_SECONDS
            ),
            "last_error_message": probe_error or "",
            "recommended_actions": [
                "Inspect network/firewall/DNS reachability to the remote "
                "Splunk endpoint from this search head.",
                f'Run POST /trackme/v2/configuration/test_remote_account '
                f'body={{"account": "{account_name}"}} for a fresh probe.',
                "Cross-check the `remote_account_token_expiring_soon` Guardian "
                "alert for this account — an expired token looks like a "
                "connectivity failure at the auth layer.",
                "Review $SPLUNK_HOME/var/log/splunk/splunkd.log for the last "
                "recorded remote-search exception.",
                f"Rerun POST /trackme/v2/configuration/admin/run_guardian_checks "
                f"with check_type='{CHECK_REMOTE_ACCOUNT_CONNECTIVITY}' to "
                f"confirm remediation.",
            ],
        }

        upsert_guardian_alert(
            service,
            check_type=CHECK_REMOTE_ACCOUNT_CONNECTIVITY,
            scope_key=account_name,
            severity=severity,
            scope="system",
            tenant_id="",
            subject=account_name,
            title=title,
            message=message,
            remediation=remediation,
            metadata=metadata,
            audit_index_name=audit_index_name,
        )
        outcomes.append({
            "status": "alert_created",
            "account": account_name,
            "severity": severity,
            "failure_duration_seconds": int(failure_duration),
            "last_error_message": probe_error or "",
        })

    if not outcomes:
        return [{"status": "ok", "reason": "no_remote_accounts"}]
    return outcomes


# -----------------------------------------------------------------------------
# Check: ai_provider_unreachable
# -----------------------------------------------------------------------------


def _read_enable_ai_assistant(service):
    """Return True if the AI Assistant is enabled (or cannot be determined).

    We default to "enabled" on read failure because the cost of running a
    probe against a provider that's actually disabled is tiny (skipped via
    the provider-config check anyway) whereas skipping a check because we
    couldn't read a boolean is a silent blind spot. Matches the idiomatic
    pattern in `trackme_rest_handler_ai_chat.py` which also defaults to
    "1" on read.
    """
    try:
        conf = service.confs["trackme_settings"]
        stanza = conf["trackme_general"]
        value = stanza.content.get("enable_ai_assistant", "1")
    except Exception:
        return True
    return str(value).strip().lower() not in ("0", "false", "no", "off")


def check_ai_provider_unreachable(
    session_key, splunkd_uri, service, audit_index_name=None
):
    """System-scoped: run a daily `test_llm_connectivity` probe for every
    configured AI provider. One alert per provider (`scope_key =
    provider_name`). Severity stays at ``warning`` by design — AI is
    opt-in and non-critical, an unreachable provider degrades features
    (AI status reports in stateful alerts, interactive chat jobs) but
    does not lose data.

    Skip reasons:
      * ``enable_ai_assistant`` flag is off       → skip entirely
      * ``list_ai_providers`` raises / returns [] → skip (no providers)
      * per-provider config / key lookup fails    → skip that provider only

    Returns a list of per-provider outcomes so ``run_checks`` can flatten
    into accurate delta counts. Early-exit returns a single-element list
    for uniform contract.
    """
    if not _read_enable_ai_assistant(service):
        return [{"status": "skipped", "reason": "ai_assistant_disabled"}]

    # Import lazily — the AI lib pulls in a number of provider SDK modules,
    # no need to load them on every Guardian run in deployments where AI
    # is off. (The enable-flag check above short-circuits that case too,
    # but this keeps the import local regardless.)
    try:
        from trackme_libs_ai import (
            list_ai_providers,
            get_ai_config,
            get_ai_api_key,
            test_llm_connectivity,
        )
    except Exception as e:
        return [{"status": "skipped", "reason": f"ai_lib_import_failed: {str(e)}"}]

    # Include disabled providers in the enumeration so we can self-heal any
    # stale `ai_provider_unreachable` alert when an admin disables a
    # previously-failing provider (the probe is skipped for disabled stanzas,
    # but any existing alert is cleared).
    try:
        providers = list_ai_providers(service, include_disabled=True)
    except Exception as e:
        return [{"status": "skipped", "reason": f"list_providers_failed: {str(e)}"}]

    if not providers:
        return [{"status": "skipped", "reason": "no_ai_providers"}]

    outcomes = []
    for entry in providers:
        provider_name = entry.get("name")
        if not provider_name:
            continue

        # Provider disabled by admin → skip probe and clear any stale alert.
        if entry.get("ai_enabled") == "0":
            cleared = clear_guardian_alert(
                service,
                CHECK_AI_PROVIDER_UNREACHABLE,
                provider_name,
                audit_index_name,
            )
            outcomes.append({
                "status": "alert_cleared" if cleared else "skipped",
                "provider": provider_name,
                "reason": "provider_disabled",
            })
            continue

        # Resolve config + key. `get_ai_config` and `get_ai_api_key` are the
        # canonical helpers; both may legitimately return None when a
        # provider is partially configured (e.g. mid-onboarding).
        # include_disabled=True matches the enumeration above — the disabled
        # short-circuit already ran, so only enabled stanzas reach here.
        try:
            config = get_ai_config(
                service, provider_name=provider_name, include_disabled=True
            )
        except Exception as e:
            outcomes.append({
                "status": "skipped",
                "provider": provider_name,
                "reason": f"config_lookup_failed: {str(e)}",
            })
            continue
        if not config:
            outcomes.append({
                "status": "skipped",
                "provider": provider_name,
                "reason": "config_not_found",
            })
            continue

        # `get_ai_api_key` catches its own exceptions internally and returns
        # None when the key isn't found (e.g. mid-onboarding, or a provider
        # type like `ollama` / `splunk_hosted` that doesn't need a key). We
        # keep a defensive try/except for the unexpected-SDK-failure case,
        # but we MUST also skip when the returned value is None — otherwise
        # we'd pass `api_key=None` straight to `test_llm_connectivity`, fire
        # a spurious warning alert and contradict the documented
        # "skip that provider only" behaviour.
        try:
            api_key = get_ai_api_key(service, provider_name)
        except Exception as e:
            outcomes.append({
                "status": "skipped",
                "provider": provider_name,
                "reason": f"api_key_lookup_failed: {str(e)}",
            })
            continue
        if not api_key:
            # Some provider types (ollama / splunk_hosted) legitimately do
            # not require an API key — but `test_llm_connectivity` is the
            # authority on what each provider needs, and it accepts an empty
            # string in those cases. Only skip when the provider type is
            # one that clearly needs a key; otherwise fall through so those
            # key-less providers still get probed.
            provider_type = (config.get("ai_provider") or "").lower()
            if provider_type not in ("ollama", "splunk_hosted"):
                outcomes.append({
                    "status": "skipped",
                    "provider": provider_name,
                    "reason": "api_key_not_configured",
                })
                continue
            api_key = ""  # normalised falsy value expected by the probe

        # Probe. `test_llm_connectivity` returns a dict with `success: bool`
        # and never raises for normal failures (it traps AIProviderError
        # internally), but defensively wrap in case an SDK bubbles an
        # unexpected exception.
        try:
            result = test_llm_connectivity(config, api_key, service=service)
        except Exception as e:
            result = {
                "success": False,
                "message": f"probe raised unexpectedly: {str(e)}",
            }

        probe_success = bool(result.get("success"))

        if probe_success:
            cleared = clear_guardian_alert(
                service,
                CHECK_AI_PROVIDER_UNREACHABLE,
                provider_name,
                audit_index_name,
            )
            outcomes.append({
                "status": "alert_cleared" if cleared else "ok",
                "provider": provider_name,
                "response_time_sec": result.get("response_time_sec"),
            })
            continue

        # Upsert warning alert
        ai_provider_type = config.get("ai_provider") or "unknown"
        ai_model = config.get("ai_model") or "unknown"
        error_msg = result.get("message") or "unknown error"

        title = "AI provider connectivity probe failed"
        message = (
            f'The daily connectivity probe to AI provider "{provider_name}" '
            f'(type: {ai_provider_type}, model: {ai_model}) failed. '
            f'AI-generated status reports embedded in stateful alerts will '
            f'be missing the AI paragraph, and interactive chat jobs will '
            f'fail per-request. Last probe error: {error_msg}.'
        )
        remediation = (
            f'1) Verify the remote LLM endpoint is reachable from this search '
            f'head (network / firewall / DNS). '
            f'2) Confirm the API key for "{provider_name}" is still valid at '
            f'the provider side (rotate via Configuration → AI Providers if '
            f'needed). '
            f'3) Check the provider\'s status page for an outage. '
            f'4) Inspect $SPLUNK_HOME/var/log/splunk/trackme_ai_chat.log for '
            f'the full error chain. '
            f'5) Run the admin test endpoint '
            f'POST /trackme/v2/ai/admin/test with '
            f'body={{"provider_name": "{provider_name}"}} for a fresh probe.'
        )
        metadata = {
            "provider_name": provider_name,
            "ai_provider_type": ai_provider_type,
            "ai_model": ai_model,
            "last_error_message": error_msg,
            "response_time_sec": result.get("response_time_sec"),
            "recommended_actions": [
                "Inspect network/firewall/DNS reachability to the AI provider "
                "endpoint from this search head.",
                "Confirm the provider's API key is still valid (check the "
                "provider-side dashboard).",
                f'Rotate the key for "{provider_name}" via Configuration → '
                f'AI Providers if it has been revoked.',
                f'Run POST /trackme/v2/ai/admin/test body='
                f'{{"provider_name": "{provider_name}"}} for an interactive '
                f'probe with full error output.',
                "Consult the provider's public status page to rule out a "
                "third-party outage.",
                f"Rerun POST /trackme/v2/configuration/admin/run_guardian_checks "
                f"with check_type='{CHECK_AI_PROVIDER_UNREACHABLE}' to confirm "
                f"remediation.",
            ],
        }

        upsert_guardian_alert(
            service,
            check_type=CHECK_AI_PROVIDER_UNREACHABLE,
            scope_key=provider_name,
            severity=SEVERITY_WARNING,
            scope="system",
            tenant_id="",
            subject=provider_name,
            title=title,
            message=message,
            remediation=remediation,
            metadata=metadata,
            audit_index_name=audit_index_name,
        )
        outcomes.append({
            "status": "alert_created",
            "provider": provider_name,
            "last_error_message": error_msg,
        })

    if not outcomes:
        return [{"status": "ok", "reason": "no_ai_providers"}]
    return outcomes


# -----------------------------------------------------------------------------
# Check: backup_archive_too_old
# -----------------------------------------------------------------------------


def _compute_backup_cadence_seconds(cron_expr):
    """Parse a cron expression via `croniter` and return the scheduled
    interval in seconds. Falls back to `BACKUP_DEFAULT_CADENCE_SECONDS`
    (daily) for unparseable input.

    We compute the delta between two consecutive firings rather than relying
    on a hardcoded "24h for any daily cron" — that way 12-hourly, 6-hourly
    and other non-daily cadences are handled correctly out of the box.
    """
    if not cron_expr:
        return BACKUP_DEFAULT_CADENCE_SECONDS
    try:
        from croniter import croniter
        from datetime import datetime as _dt

        base = _dt.utcnow()
        itr = croniter(str(cron_expr), base)
        first = itr.get_next(_dt)
        second = itr.get_next(_dt)
        delta = (second - first).total_seconds()
        if delta > 0:
            return int(delta)
    except Exception as e:
        get_effective_logger().debug(
            f'guardian_backup_cron_parse_failed cron="{cron_expr}", exception="{str(e)}"'
        )
    return BACKUP_DEFAULT_CADENCE_SECONDS


def check_backup_archive_too_old(
    session_key, splunkd_uri, service, audit_index_name=None
):
    """System-scoped: alert when the most recent entry in
    ``kv_trackme_backup_archives_info`` is older than the configured
    backup cadence × `BACKUP_CADENCE_WARN_MULTIPLIER` (default 1.5).
    Escalates to ``critical`` past ``BACKUP_CRITICAL_AGE_SECONDS``
    (default 7 days) — a week without a backup is catastrophic for DR
    regardless of cadence.

    One alert per system (``scope_key="latest"``) — there's one TrackMe
    backup scheduler per install and the check only cares about the
    most-recent record.

    Skip reasons:
      * ``trackme_backup_scheduler`` saved search missing       → skip
      * saved search disabled OR not scheduled                  → skip
        (backups are opt-in; admin explicitly turned them off)
      * no archive records in the KV yet                        → skip
        (fresh install / scheduler just enabled; not Guardian-worthy)
      * KV / saved-search read failure                          → skip
        (leave prior state untouched)
    """
    # Saved-search state — lets us detect whether backups are enabled.
    try:
        ss = service.saved_searches[BACKUP_SCHEDULER_SAVEDSEARCH]
        ss_content = ss.content or {}
    except KeyError:
        cleared = clear_guardian_alert(
            service,
            CHECK_BACKUP_ARCHIVE_TOO_OLD,
            "latest",
            audit_index_name,
        )
        return [{
            "status": "alert_cleared" if cleared else "skipped",
            "reason": "backup_scheduler_not_provisioned",
        }]
    except Exception as e:
        return [{
            "status": "skipped",
            "reason": f"savedsearch_lookup_failed: {str(e)}",
        }]

    try:
        ss_disabled = int(ss_content.get("disabled", 1))
    except Exception:
        ss_disabled = 1
    try:
        # `is_scheduled` is the runtime truth (splunkd-computed); the stored
        # `enableSched` is the intent. Prefer is_scheduled when available.
        ss_scheduled = int(
            ss_content.get("is_scheduled", ss_content.get("enableSched", 0))
        )
    except Exception:
        ss_scheduled = 0

    if ss_disabled == 1 or ss_scheduled == 0:
        cleared = clear_guardian_alert(
            service,
            CHECK_BACKUP_ARCHIVE_TOO_OLD,
            "latest",
            audit_index_name,
        )
        return [{
            "status": "alert_cleared" if cleared else "skipped",
            "reason": "backup_scheduler_disabled",
        }]

    cron_expr = ss_content.get("cron_schedule") or "0 2 * * *"
    cadence = _compute_backup_cadence_seconds(cron_expr)
    warning_threshold = int(cadence * BACKUP_CADENCE_WARN_MULTIPLIER)
    critical_threshold = BACKUP_CRITICAL_AGE_SECONDS

    try:
        collection = service.kvstore["kv_trackme_backup_archives_info"]
        rows = list(collection.data.query() or [])
    except Exception as e:
        return [{
            "status": "skipped",
            "reason": f"archive_kv_lookup_failed: {str(e)}",
        }]

    if not rows:
        cleared = clear_guardian_alert(
            service,
            CHECK_BACKUP_ARCHIVE_TOO_OLD,
            "latest",
            audit_index_name,
        )
        return [{
            "status": "alert_cleared" if cleared else "skipped",
            "reason": "no_archives_yet",
        }]

    # `mtime` stored as string-of-epoch-seconds by the backup handler
    # (see trackme_rest_handler_backup_and_restore.py). Coerce defensively.
    def _row_mtime(r):
        return _coerce_float(r.get("mtime"), default=0.0)

    # 3.0.0 multi-archive: a backup run produces N tenant archives + 1
    # global archive. We anchor the freshness check on the global rows
    # (one per run) rather than "newest mtime overall" — otherwise a
    # late-finishing tenant archive could mask a stale global, or a
    # mixed run with sibling archives at slightly different mtimes
    # would inflate the apparent freshness. When no row has
    # ``archive_scope`` populated (un-upgraded install where only
    # legacy 1.0.0/2.0.0 archives exist, or a fresh install before
    # the first 3.0.0 run lands), fall back to the previous "newest
    # archive overall" semantics so the check stays meaningful through
    # the upgrade transition.
    global_rows = [r for r in rows if r.get("archive_scope") == "global"]
    candidate_rows = global_rows or rows
    latest_row = max(candidate_rows, key=_row_mtime)
    latest_mtime = _row_mtime(latest_row)
    if latest_mtime <= 0:
        return [{
            "status": "skipped",
            "reason": "no_valid_mtime_on_records",
        }]

    now = time.time()
    staleness = now - latest_mtime

    if staleness > critical_threshold:
        severity = SEVERITY_CRITICAL
    elif staleness > warning_threshold:
        severity = SEVERITY_WARNING
    else:
        cleared = clear_guardian_alert(
            service,
            CHECK_BACKUP_ARCHIVE_TOO_OLD,
            "latest",
            audit_index_name,
        )
        return [{
            "status": "alert_cleared" if cleared else "ok",
            "staleness_seconds": int(staleness),
            "cadence_seconds": cadence,
        }]

    days_old = int(staleness // 86400)
    hours_old = int(staleness // 3600)
    age_display = (
        f"{days_old} day(s)" if days_old >= 1
        else f"{hours_old} hour(s)" if hours_old >= 1
        else "less than 1 hour"
    )
    latest_mtime_iso = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(latest_mtime)
    )

    title = (
        "Backup archive critically stale"
        if severity == SEVERITY_CRITICAL
        else "Backup archive too old"
    )
    cadence_hours = max(int(cadence // 3600), 1)
    message = (
        f'The most recent TrackMe backup archive is {age_display} old '
        f'(created at {latest_mtime_iso}). Expected cadence: ~{cadence_hours}h '
        f'(cron "{cron_expr}"), warn threshold: {warning_threshold}s, '
        f'critical threshold: {critical_threshold}s. If the `trackme_backup_scheduler` '
        f'saved search is silently skipping, your disaster-recovery capability '
        f'is degrading without any other surface making this visible.'
    )
    remediation = (
        f'1) Inspect `index=_internal sourcetype=scheduler '
        f'savedsearch_name="{BACKUP_SCHEDULER_SAVEDSEARCH}"` for recent '
        f'skipped / deferred / failed runs. '
        f'2) Verify the saved search `{BACKUP_SCHEDULER_SAVEDSEARCH}` is '
        f'enabled and scheduled (Settings → Searches, reports and alerts). '
        f'3) Confirm filesystem write permissions on the backup destination '
        f'path (check the default stanza of the saved search for the target). '
        f'4) Manually invoke the backup once via `| trackmebackupandrestore '
        f'action=backup` to verify the pipeline end-to-end. '
        f'5) Review $SPLUNK_HOME/var/log/splunk/trackme_backup.log for the '
        f'last recorded error.'
    )
    metadata = {
        "latest_archive_mtime": latest_mtime,
        "latest_archive_iso": latest_mtime_iso,
        "latest_archive_name": latest_row.get("backup_archive"),
        "latest_archive_server": latest_row.get("server_name"),
        "staleness_seconds": int(staleness),
        "cadence_seconds": cadence,
        "cron_schedule": cron_expr,
        "warning_threshold_seconds": warning_threshold,
        "critical_threshold_seconds": critical_threshold,
        "archive_count": len(rows),
        "recommended_actions": [
            f'Inspect index=_internal sourcetype=scheduler '
            f'savedsearch_name="{BACKUP_SCHEDULER_SAVEDSEARCH}" for skipped / '
            f'deferred / failed runs.',
            f'Verify the saved search `{BACKUP_SCHEDULER_SAVEDSEARCH}` is '
            f'enabled and scheduled.',
            "Confirm filesystem write permissions on the backup destination path.",
            "Manually invoke `| trackmebackupandrestore action=backup` to "
            "verify the pipeline end-to-end.",
            "Review $SPLUNK_HOME/var/log/splunk/trackme_backup.log for the "
            "last recorded error.",
            f"Rerun POST /trackme/v2/configuration/admin/run_guardian_checks "
            f"with check_type='{CHECK_BACKUP_ARCHIVE_TOO_OLD}' after fixing.",
        ],
    }

    upsert_guardian_alert(
        service,
        check_type=CHECK_BACKUP_ARCHIVE_TOO_OLD,
        scope_key="latest",
        severity=severity,
        scope="system",
        tenant_id="",
        subject="latest",
        title=title,
        message=message,
        remediation=remediation,
        metadata=metadata,
        audit_index_name=audit_index_name,
    )
    return [{
        "status": "alert_created",
        "severity": severity,
        "staleness_seconds": int(staleness),
        "cadence_seconds": cadence,
    }]


# -----------------------------------------------------------------------------
# Check: backup_run_incomplete (3.0.0 multi-archive only)
# -----------------------------------------------------------------------------


def check_backup_run_incomplete(
    session_key, splunkd_uri, service, audit_index_name=None
):
    """System-scoped: warn when the most recent 3.0.0 backup run produced
    fewer tenant archives than the number of currently-enabled virtual
    tenants.

    A run is identified by ``backup_run_id`` and consists of one
    ``archive_scope='global'`` row plus one
    ``archive_scope='tenant'`` row per enabled tenant. If post_backup's
    per-tenant isolation kicked in (a tenant's KV was corrupted, the
    handler skipped that one archive, the rest of the run continued —
    the design that motivated this whole redesign), the resulting run
    is structurally incomplete: tenant X has no archive in this run.
    Without this check, the operator only learns at recovery time that
    tenant X's data isn't restorable from the latest run.

    Severity: ``warning``. The freshness check
    (``backup_archive_too_old``) is the catastrophic-DR signal; this
    one is the "DR is degraded for tenant X" signal.

    Skip conditions:
      * ``trackme_backup_scheduler`` saved search disabled            → skip
      * No 3.0.0 rows in KV (un-upgraded install, only legacy archives) → skip
      * No enabled tenants                                            → skip
      * KV / saved-search read failure                                → skip

    The check runs daily from `trackmegeneralhealthmanager.py` (system
    scope, like backup_archive_too_old). Self-healing — once the next
    complete run lands, the alert clears.
    """
    # Saved-search gate first — same skip semantics as the freshness check.
    try:
        ss = service.saved_searches[BACKUP_SCHEDULER_SAVEDSEARCH]
        ss_content = ss.content or {}
    except KeyError:
        cleared = clear_guardian_alert(
            service,
            CHECK_BACKUP_RUN_INCOMPLETE,
            "latest",
            audit_index_name,
        )
        return [{
            "status": "alert_cleared" if cleared else "skipped",
            "reason": "backup_scheduler_not_provisioned",
        }]
    except Exception as e:
        return [{
            "status": "skipped",
            "reason": f"savedsearch_lookup_failed: {str(e)}",
        }]

    try:
        ss_disabled = int(ss_content.get("disabled", 1))
    except Exception:
        ss_disabled = 1
    try:
        ss_scheduled = int(
            ss_content.get("is_scheduled", ss_content.get("enableSched", 0))
        )
    except Exception:
        ss_scheduled = 0
    if ss_disabled == 1 or ss_scheduled == 0:
        cleared = clear_guardian_alert(
            service,
            CHECK_BACKUP_RUN_INCOMPLETE,
            "latest",
            audit_index_name,
        )
        return [{
            "status": "alert_cleared" if cleared else "skipped",
            "reason": "backup_scheduler_disabled",
        }]

    # Read the archive info collection.
    try:
        collection = service.kvstore["kv_trackme_backup_archives_info"]
        rows = list(collection.data.query() or [])
    except Exception as e:
        return [{
            "status": "skipped",
            "reason": f"archive_kv_lookup_failed: {str(e)}",
        }]

    # Identify the latest 3.0.0 run by the newest global row's mtime.
    # No global rows = un-upgraded install (only legacy archives) — the
    # check has nothing to evaluate so we skip cleanly.
    def _row_mtime(r):
        return _coerce_float(r.get("mtime"), default=0.0)

    global_rows = [r for r in rows if r.get("archive_scope") == "global"]
    if not global_rows:
        cleared = clear_guardian_alert(
            service,
            CHECK_BACKUP_RUN_INCOMPLETE,
            "latest",
            audit_index_name,
        )
        return [{
            "status": "alert_cleared" if cleared else "skipped",
            "reason": "no_3_0_0_runs_yet",
        }]

    latest_global = max(global_rows, key=_row_mtime)
    latest_run_id = latest_global.get("backup_run_id") or ""
    if not latest_run_id:
        return [{
            "status": "skipped",
            "reason": "latest_global_row_missing_backup_run_id",
        }]

    # Tenant archives in that run.
    run_tenant_archive_ids = {
        r.get("tenant_id")
        for r in rows
        if r.get("backup_run_id") == latest_run_id
        and r.get("archive_scope") == "tenant"
        and r.get("tenant_id")
    }

    # Currently enabled tenants. We compare against the CURRENT state
    # of kv_trackme_virtual_tenants rather than reconstructing what was
    # enabled at run time. Trade-off: a freshly-disabled tenant briefly
    # appears as "missing from the latest run" until the next run runs;
    # a freshly-enabled tenant likewise warns until its first run. Both
    # are honest signals — the operator should expect either to clear
    # within one run cadence. The alternative (reconstructing enabled-
    # set from KV history) doesn't generalise cleanly.
    try:
        vtenants_collection = service.kvstore["kv_trackme_virtual_tenants"]
        vtenants_rows = list(vtenants_collection.data.query() or [])
    except Exception as e:
        return [{
            "status": "skipped",
            "reason": f"vtenants_kv_lookup_failed: {str(e)}",
        }]

    # Defensive lower-case normalisation: every other guardian check
    # in this file normalises tenant_status before comparing, so we
    # follow suit. A stray "Enabled" capitalisation in the KV (from a
    # hand-edited record or a migration quirk) would otherwise silently
    # exclude the tenant from the enabled set, and a genuinely missing
    # tenant archive would never be reported.
    enabled_tenants = {
        r.get("tenant_id")
        for r in vtenants_rows
        if str(r.get("tenant_status", "")).strip().lower() == "enabled"
        and r.get("tenant_id")
    }
    if not enabled_tenants:
        cleared = clear_guardian_alert(
            service,
            CHECK_BACKUP_RUN_INCOMPLETE,
            "latest",
            audit_index_name,
        )
        return [{
            "status": "alert_cleared" if cleared else "skipped",
            "reason": "no_enabled_tenants",
        }]

    missing_tenants = sorted(enabled_tenants - run_tenant_archive_ids)
    if not missing_tenants:
        cleared = clear_guardian_alert(
            service,
            CHECK_BACKUP_RUN_INCOMPLETE,
            "latest",
            audit_index_name,
        )
        return [{
            "status": "alert_cleared" if cleared else "ok",
            "backup_run_id": latest_run_id,
            "tenant_archive_count": len(run_tenant_archive_ids),
            "enabled_tenants_count": len(enabled_tenants),
        }]

    # Incomplete run — emit a warning.
    latest_iso = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(_row_mtime(latest_global))
    )
    title = "Backup run incomplete"
    message = (
        f'The most recent backup run ({latest_run_id}, finished at '
        f'{latest_iso}) produced {len(run_tenant_archive_ids)} tenant '
        f'archive(s) but {len(enabled_tenants)} virtual tenants are '
        f'currently enabled. Tenants without an archive in the latest '
        f'run are NOT restorable from that run: '
        f'{", ".join(missing_tenants)}. This typically means '
        f'post_backup\'s per-tenant isolation kicked in for a corrupted '
        f'tenant\'s payload — the run as a whole still produced the '
        f'global archive and the other tenant archives, which is the '
        f'design intent (a single corrupted tenant must not block '
        f'recovery for everyone else). But the operator needs to act '
        f'on the missing tenants before another disaster lands.'
    )
    remediation = (
        f'1) Inspect the per-archive errors in the run: '
        f'`| inputlookup trackme_backup_archives_info '
        f'| where backup_run_id="{latest_run_id}"` and read the '
        f'``status`` field. '
        f'2) Investigate the missing tenants individually: '
        f'`index=_internal sourcetype=trackme:rest_api '
        f'trackme_rest_handler_backup_and_restore.py "run_id={latest_run_id}"` '
        f'will surface the per-tenant failure messages. '
        f'3) Once root cause is fixed, run a fresh tenant-only backup '
        f'with `POST /trackme/v2/backup_and_restore/backup_tenant` '
        f'`body={{"tenant_id": "<tid>"}}` to produce a tenant archive '
        f'attached to the next run\'s context. '
        f'4) Or trigger a full backup (the next scheduled run will '
        f'attempt every enabled tenant again with isolation, '
        f'self-healing if the cause was transient).'
    )
    metadata = {
        "backup_run_id": latest_run_id,
        "latest_run_finished_iso": latest_iso,
        "latest_run_finished_epoch": _row_mtime(latest_global),
        "tenant_archive_count": len(run_tenant_archive_ids),
        "enabled_tenants_count": len(enabled_tenants),
        "missing_tenants": missing_tenants,
        "tenants_with_archive": sorted(run_tenant_archive_ids),
        "recommended_actions": [
            f'Inspect the run\'s per-archive errors: | inputlookup '
            f'trackme_backup_archives_info | where '
            f'backup_run_id="{latest_run_id}".',
            f'Tail trackme_rest_api_backup_and_restore.log for '
            f'run_id="{latest_run_id}" to find the per-tenant failure '
            f'messages.',
            "After fixing root cause, snapshot each missing tenant via "
            "POST /backup_and_restore/backup_tenant.",
            "OR wait for the next scheduled run to retry every enabled "
            "tenant with isolation (self-healing if transient).",
            f"Rerun POST /trackme/v2/configuration/admin/run_guardian_checks "
            f"with check_type='{CHECK_BACKUP_RUN_INCOMPLETE}' to verify the "
            f"alert clears.",
        ],
    }

    upsert_guardian_alert(
        service,
        check_type=CHECK_BACKUP_RUN_INCOMPLETE,
        scope_key="latest",
        severity=SEVERITY_WARNING,
        scope="system",
        tenant_id="",
        subject=latest_run_id,
        title=title,
        message=message,
        remediation=remediation,
        metadata=metadata,
        audit_index_name=audit_index_name,
    )
    return [{
        "status": "alert_created",
        "severity": SEVERITY_WARNING,
        "backup_run_id": latest_run_id,
        "missing_tenants": missing_tenants,
    }]


# -----------------------------------------------------------------------------
# Check: health_tracker_not_executing
# -----------------------------------------------------------------------------


def check_health_tracker_executing(
    session_key, splunkd_uri, service, tenant_record, audit_index_name=None
):
    """Meta-check: has the per-tenant health tracker run recently?

    Reads `kv_trackme_health_tracker_state` for the tenant. If the most-recent
    `last_execution_time` across all tasks is older than
    ``HEALTH_TRACKER_STALE_SECONDS`` (30 minutes = 6 missed 5-min cycles), the
    tracker is presumed broken and we raise a critical alert.

    MUST be invoked from `trackmegeneralhealthmanager.py`, never from
    `trackmetrackerhealth.py` itself — the tracker cannot diagnose its own
    absence.
    """
    tenant_id = str(tenant_record.get("tenant_id", "")) if tenant_record else ""
    outcome = {
        "status": "skipped",
        "tenant_id": tenant_id,
        "subject": None,
        "reason": None,
    }

    if not tenant_id:
        outcome["reason"] = "missing_tenant_id"
        return outcome

    tenant_status = str(tenant_record.get("tenant_status") or "").lower()
    if tenant_status != "enabled":
        outcome["reason"] = "tenant_disabled"
        if clear_guardian_alert(
            service, CHECK_HEALTH_TRACKER_EXECUTING, tenant_id, audit_index_name
        ):
            outcome["status"] = "alert_cleared"
        return outcome

    try:
        collection = service.kvstore["kv_trackme_health_tracker_state"]
        rows = list(collection.data.query(query=json.dumps({"tenant_id": tenant_id}))) or []
    except Exception as e:
        outcome["reason"] = f"state_lookup_failed: {str(e)}"
        return outcome

    if not rows:
        # No state rows for this tenant — either the health-tracker savedsearch
        # hasn't been provisioned yet (brand-new tenant, or a KV wipe happened
        # recently) or it's disabled. We check the savedsearch's actual
        # existence / enablement here rather than relying on `tenant_record.mtime`
        # (which updates on any record change, not just creation, and created
        # a 30-minute blind spot per bugbot) so we can distinguish:
        #   * savedsearch missing or disabled → skip (the
        #     `virtual_tenants:check_health_tracker` task in the same general
        #     health manager run will repair it — alerting here would be
        #     redundant noise);
        #   * savedsearch enabled but never ran → alert critical (this IS the
        #     broken-tracker case we want to surface).
        savedsearch_name = f"trackme_health_tracker_tenant_{tenant_id}"
        try:
            ss = service.saved_searches[savedsearch_name]
            ss_disabled = int(ss.content.get("disabled", 1))
        except KeyError:
            outcome["reason"] = "savedsearch_not_provisioned"
            # Clear any stale alert — a tenant whose savedsearch doesn't exist
            # yet isn't "broken", just not-yet-set-up. The auto-repair task
            # will create it.
            if clear_guardian_alert(
                service, CHECK_HEALTH_TRACKER_EXECUTING, tenant_id, audit_index_name
            ):
                outcome["status"] = "alert_cleared"
            return outcome
        except Exception as e:
            outcome["reason"] = f"savedsearch_lookup_failed: {str(e)}"
            return outcome
        if ss_disabled == 1:
            outcome["reason"] = "savedsearch_disabled"
            if clear_guardian_alert(
                service, CHECK_HEALTH_TRACKER_EXECUTING, tenant_id, audit_index_name
            ):
                outcome["status"] = "alert_cleared"
            return outcome
        # Savedsearch exists and is enabled, but has never written state.
        # Treat as an infinitely-stale tracker so the alert fires.
        last_execution = 0.0
    else:
        last_execution = max(
            _coerce_float(r.get("last_execution_time"), default=0.0) for r in rows
        )

    now = time.time()
    staleness = now - last_execution if last_execution > 0 else float("inf")

    if staleness <= HEALTH_TRACKER_STALE_SECONDS:
        if clear_guardian_alert(
            service, CHECK_HEALTH_TRACKER_EXECUTING, tenant_id, audit_index_name
        ):
            outcome["status"] = "alert_cleared"
        else:
            outcome["status"] = "ok"
        outcome["staleness_seconds"] = int(staleness)
        return outcome

    tenant_alias = tenant_record.get("tenant_alias") or tenant_id
    savedsearch_name = f"trackme_health_tracker_tenant_{tenant_id}"
    has_ever_executed = last_execution > 0

    if has_ever_executed:
        last_execution_iso = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(last_execution)
        )
        staleness_minutes = int(staleness // 60)
        title = "Health tracker not executing"
        message = (
            f'The per-tenant health tracker `{savedsearch_name}` for tenant '
            f'"{tenant_alias}" has not recorded a successful cycle for '
            f'{staleness_minutes} minute(s) (last seen: {last_execution_iso}). '
            f'While the health tracker is stalled, every other per-tenant '
            f'Guardian check for this tenant goes stale silently; alert state, '
            f'ACK expiration, and entity status calculations may also be affected.'
        )
    else:
        # Distinct phrasing for the "savedsearch is enabled but has never
        # recorded a cycle" case. Avoids the confusing rendering like
        # "has not recorded a successful cycle for unknown minute(s)
        # (last seen: never)" that the unified path produced.
        last_execution_iso = "never"
        staleness_minutes = None
        title = "Health tracker has never executed"
        message = (
            f'The per-tenant health tracker `{savedsearch_name}` for tenant '
            f'"{tenant_alias}" is enabled but has never recorded a successful '
            f'cycle. Until it starts running, every other per-tenant Guardian '
            f'check for this tenant will stay silent; alert state, ACK '
            f'expiration, and entity status calculations will not update.'
        )

    remediation = (
        f'1) Verify the saved search `{savedsearch_name}` is enabled and '
        f'scheduled under Settings → Searches, reports and alerts. '
        f'2) Inspect `index=_internal sourcetype=scheduler '
        f'savedsearch_name="{savedsearch_name}"` for recent execution status '
        f'(skipped, deferred, failed) or any sign of a first-run attempt. '
        f'3) If the tenant_owner service account is the issue, see the '
        f'`insufficient_tenant_owner_capabilities` Guardian check. '
        f'4) Check `$SPLUNK_HOME/var/log/splunk/trackme_tracker_health.log` '
        f'for the last recorded error.'
    )
    # `staleness_seconds` is None for the never-ran case so the frontend
    # `extractDetail` helper skips the "stale for N minute(s)" phrasing and
    # falls through to the title prefix which already says "never executed".
    metadata = {
        "tenant_alias": tenant_alias,
        "savedsearch_name": savedsearch_name,
        "last_execution_epoch": last_execution,
        "last_execution_iso": last_execution_iso,
        "staleness_seconds": int(staleness) if has_ever_executed else None,
        "has_ever_executed": has_ever_executed,
        "threshold_seconds": HEALTH_TRACKER_STALE_SECONDS,
        "recommended_actions": [
            f'Inspect index=_internal sourcetype=scheduler '
            f'savedsearch_name="{savedsearch_name}" '
            f'to see whether the scheduler is skipping, deferring, or failing.',
            f'Verify the saved search `{savedsearch_name}` is enabled '
            f'(Settings → Searches, reports and alerts).',
            f'Cross-check the `{CHECK_TENANT_OWNER_CAPABILITIES}` Guardian alert '
            f'for this tenant — a missing capability can stop the tracker.',
            f'Review $SPLUNK_HOME/var/log/splunk/trackme_tracker_health.log for the '
            f'last recorded error or exception.',
        ],
    }

    upsert_guardian_alert(
        service,
        check_type=CHECK_HEALTH_TRACKER_EXECUTING,
        scope_key=tenant_id,
        severity=SEVERITY_CRITICAL,
        scope="tenant",
        tenant_id=tenant_id,
        subject=tenant_alias,
        title=title,
        message=message,
        remediation=remediation,
        metadata=metadata,
        audit_index_name=audit_index_name,
    )
    outcome["status"] = "alert_created"
    outcome["staleness_seconds"] = int(staleness) if staleness != float("inf") else None
    return outcome


# -----------------------------------------------------------------------------
# Registry / batch runner
# -----------------------------------------------------------------------------

# Mapping of check_type -> {
#     "scope": "tenant" | "system",
#     "runner": callable,
#     "pre_run": optional callable returning a dict of kwargs to forward to every
#                runner invocation. Use this for expensive or SH-wide lookups that
#                should be fetched once and shared across all tenants in a run —
#                e.g. `fetch_declared_indexes` for the assigned-index check,
#                which would otherwise N+1 when iterating tenants.
# }.
# -----------------------------------------------------------------------------
# Check: ai_feed_lifecycle_delay_conflict
# -----------------------------------------------------------------------------
#
# Detects drift between the legacy mechanical Adaptive Delay (and its
# companion variable_delay_auto_review) and the AI Feed Lifecycle Advisor.
# These features both manage DSM/DHM delay thresholds — when the AI advisor
# is enabled for DSM or DHM, it is the authority, and the legacy features
# must be off. The UCC save-time hook
# (``trackme_rh_vtenants_handler.CustomRestHandlerVtenants``) flips both
# legacy flags to 0 whenever the AI advisor is turned on, and the runtime
# gates in ``trackmesplkadaptivedelay`` and ``trackmesplkvariabledelayreview``
# short-circuit on the same condition.
#
# This check exists to surface inconsistent persisted state to admins —
# typically caused by direct KV pokes, downgrade-then-upgrade scenarios,
# or any API path that bypasses the UCC hook. Severity is `warning` (the
# runtime gates keep the system safe; this is operator hygiene).
# -----------------------------------------------------------------------------


def _vtenant_account_from_record(tenant_record):
    """Return the parsed ``vtenant_account`` block from a vtenant KV
    record. The block may be persisted either as a dict (some code paths)
    or a JSON string (typical KV serialisation). Returns ``{}`` when
    absent or unparseable so the caller can no-op safely.
    """
    if not tenant_record:
        return {}
    raw = tenant_record.get("vtenant_account")
    if raw in (None, ""):
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
            return decoded if isinstance(decoded, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def check_ai_feed_lifecycle_delay_conflict(
    session_key, splunkd_uri, service, tenant_record, audit_index_name=None
):
    """Detect a conflict between the AI Feed Lifecycle Advisor and the
    legacy mechanical Adaptive Delay / Variable Delay Auto-Review.

    Conflict definition: the AI advisor covers DSM or DHM on this tenant
    AND at least one of ``adaptive_delay`` / ``variable_delay_auto_review``
    is still ``1`` in the persisted vtenant record.

    Idempotent — clears the alert when the conflict resolves, upserts
    when it appears.
    """
    tenant_id = str(tenant_record.get("tenant_id", "")) if tenant_record else ""
    outcome = {
        "status": "skipped",
        "tenant_id": tenant_id,
        "subject": None,
        "reason": None,
    }

    if not tenant_id:
        outcome["reason"] = "missing_tenant_id"
        return outcome

    tenant_status = str(tenant_record.get("tenant_status") or "").lower()
    if tenant_status != "enabled":
        outcome["reason"] = "tenant_disabled"
        if clear_guardian_alert(
            service,
            CHECK_AI_FEED_LIFECYCLE_DELAY_CONFLICT,
            tenant_id,
            audit_index_name,
        ):
            outcome["status"] = "alert_cleared"
        return outcome

    vtenant_account = _vtenant_account_from_record(tenant_record)
    if not vtenant_account:
        # No vtenant_account block — record predates the AI advisor work
        # entirely, so no conflict is possible. Clear any stale alert.
        outcome["reason"] = "no_vtenant_account"
        if clear_guardian_alert(
            service,
            CHECK_AI_FEED_LIFECYCLE_DELAY_CONFLICT,
            tenant_id,
            audit_index_name,
        ):
            outcome["status"] = "alert_cleared"
        return outcome

    # Lazy import to avoid a circular dependency at module load (trackme_libs
    # imports from this module indirectly via the guardian REST handler).
    try:
        from trackme_libs import is_ai_feed_lifecycle_covering
    except Exception as e:
        outcome["reason"] = f"helper_import_failed: {str(e)}"
        return outcome

    ai_covers = is_ai_feed_lifecycle_covering(
        vtenant_account, "dsm"
    ) or is_ai_feed_lifecycle_covering(vtenant_account, "dhm")
    if not ai_covers:
        if clear_guardian_alert(
            service,
            CHECK_AI_FEED_LIFECYCLE_DELAY_CONFLICT,
            tenant_id,
            audit_index_name,
        ):
            outcome["status"] = "alert_cleared"
        else:
            outcome["status"] = "ok"
        outcome["reason"] = "ai_advisor_not_covering_delay"
        return outcome

    # AI covers delay management — legacy flags must be off.
    #
    # ``int(... or 0)`` would silently coerce a corrupt ``None`` / ``""``
    # value to 0 BEFORE ``int()`` is called, bypassing the except handler
    # and treating "value unknown" as "feature off". That's wrong: the
    # default in ``vtenant_account_default`` is ``1`` (feature on), and a
    # direct KV poke that wipes the field to ``None`` / ``""`` represents
    # drift that this check exists to catch. Letting ``int(None)`` raise
    # ``TypeError`` (and ``int("")`` raise ``ValueError``) routes through
    # the except handler, which correctly defaults to ``1`` — matching
    # the UCC handler's prior-value coercion in
    # ``trackme_rh_vtenants_handler._apply_mutex``. Bugbot finding on
    # PR #1645.
    try:
        adaptive_delay = int(vtenant_account.get("adaptive_delay", 1))
    except (TypeError, ValueError):
        adaptive_delay = 1
    try:
        variable_delay_auto_review = int(
            vtenant_account.get("variable_delay_auto_review", 1)
        )
    except (TypeError, ValueError):
        variable_delay_auto_review = 1

    offenders = []
    if adaptive_delay == 1:
        offenders.append("adaptive_delay")
    if variable_delay_auto_review == 1:
        offenders.append("variable_delay_auto_review")

    if not offenders:
        if clear_guardian_alert(
            service,
            CHECK_AI_FEED_LIFECYCLE_DELAY_CONFLICT,
            tenant_id,
            audit_index_name,
        ):
            outcome["status"] = "alert_cleared"
        else:
            outcome["status"] = "ok"
        return outcome

    tenant_alias = tenant_record.get("tenant_alias") or tenant_id
    ai_list = str(vtenant_account.get("ai_components_advisor_list", "") or "")
    covered_components = [
        c for c in ("dsm", "dhm") if is_ai_feed_lifecycle_covering(vtenant_account, c)
    ]

    title = "Adaptive Delay conflicts with AI Feed Lifecycle Advisor"
    message = (
        f'Tenant "{tenant_alias}" has the AI Feed Lifecycle Advisor enabled '
        f'for {", ".join(covered_components).upper()} (the advisor manages '
        f"delay thresholds on these components) AND the legacy mechanical "
        f'flag{"s" if len(offenders) > 1 else ""} '
        f'{", ".join(offenders)} '
        f'{"is" if len(offenders) == 1 else "are"} still set to 1. The '
        f"runtime gates keep the legacy command{'s' if len(offenders) > 1 else ''} "
        f"dormant, so no data is harmed — but the persisted configuration is "
        f"inconsistent and should be cleaned up."
    )
    remediation = (
        f'In the Tenant Configuration modal for "{tenant_alias}", set '
        f'{", ".join(offenders)} to 0. Alternatively, if you want the legacy '
        f"mechanical behaviour back, disable the AI Feed Lifecycle Advisor or "
        f"remove DSM / DHM from ai_components_advisor_list — then the legacy "
        f"flags can stay at 1."
    )
    metadata = {
        "tenant_alias": tenant_alias,
        "ai_components_advisor_list": ai_list,
        "covered_components": covered_components,
        "offending_flags": offenders,
        "recommended_actions": [
            f'Open the Tenant Configuration modal for "{tenant_alias}" (or POST '
            f"to /servicesNS/nobody/trackme/trackme_vtenants/{tenant_id}) and "
            f"set {', '.join(f'{f}=0' for f in offenders)}.",
            f"Alternatively, remove DSM / DHM from ai_components_advisor_list "
            f"on this tenant to restore mechanical Adaptive Delay as the "
            f"authority.",
            f"After remediation, POST to /trackme/v2/configuration/admin/run_guardian_checks "
            f"with check_type='{CHECK_AI_FEED_LIFECYCLE_DELAY_CONFLICT}' to "
            f"confirm the alert clears.",
        ],
    }

    upsert_guardian_alert(
        service,
        check_type=CHECK_AI_FEED_LIFECYCLE_DELAY_CONFLICT,
        scope_key=tenant_id,
        severity=SEVERITY_WARNING,
        scope="tenant",
        tenant_id=tenant_id,
        subject=tenant_alias,
        title=title,
        message=message,
        remediation=remediation,
        metadata=metadata,
        audit_index_name=audit_index_name,
    )
    outcome["status"] = "alert_created"
    outcome["subject"] = tenant_alias
    outcome["offending_flags"] = offenders
    return outcome


def check_threshold_intent_drift(
    session_key,
    splunkd_uri,
    service,
    tenant_record,
    component,
    reconcile_summary,
    audit_index_name=None,
):
    """Surface operator-pinned delay/lag threshold drift that the reconcile task
    (``reconcile_threshold_intent``) detected and auto-restored.

    Event-driven, NOT a ``CHECK_REGISTRY`` scan runner (like the sourcetype-cap
    safeguard): the reconcile already did the read + restore, so this just
    translates its summary into a self-healing Guardian alert. One alert per
    ``(tenant, component)``. Severity is ``warning`` — the drift is auto-
    corrected, so it is "attention needed", not active degradation.

    Returns an outcome dict for observability.
    """
    # Defensive: tolerate a missing tenant_record (matches the convention of the
    # other tenant-scoped checks in this file). The reconcile caller always
    # passes a valid record, but a future caller might not.
    tenant_id = str(tenant_record.get("tenant_id", "")) if tenant_record else ""
    tenant_alias = (
        tenant_record.get("tenant_alias") if tenant_record else None
    ) or tenant_id
    scope_key = f"{tenant_id}:{component}"
    outcome = {
        "check_type": CHECK_THRESHOLD_INTENT_DRIFT,
        "tenant_id": tenant_id,
        "component": component,
        "status": "no_alert",
    }
    if not tenant_id:
        outcome["status"] = "skipped"
        outcome["reason"] = "missing_tenant_id"
        return outcome

    summary = reconcile_summary or {}
    try:
        drift_corrected = int(summary.get("drift_corrected", 0) or 0)
    except (TypeError, ValueError):
        drift_corrected = 0
    drifted_objects = summary.get("drifted_objects", []) or []

    if drift_corrected <= 0:
        # Self-healing: nothing drifted this cycle, clear any prior alert.
        cleared = clear_guardian_alert(
            service,
            CHECK_THRESHOLD_INTENT_DRIFT,
            scope_key,
            audit_index_name=audit_index_name,
        )
        outcome["status"] = "alert_cleared" if cleared else "no_alert"
        return outcome

    # Cap the embedded object list to keep the KV record small.
    sample = [o for o in drifted_objects if o][:25]
    plural = "y" if drift_corrected == 1 else "ies"
    title = (
        f"{drift_corrected} pinned {component.upper()} threshold(s) were "
        f"silently changed and automatically restored"
    )
    message = (
        f"The threshold reconcile routine detected {drift_corrected} "
        f"{component.upper()} entit{plural} whose operator-pinned delay/lag "
        f"threshold had drifted from the requested value, and restored the "
        f"pinned value. Something overwrote a locked threshold — e.g. a direct "
        f"KV edit, a downgrade/upgrade, or an un-gated writer."
    )
    remediation = (
        "No immediate action is required — the pinned value has already been "
        "restored. If this recurs, identify what is writing the threshold "
        "(check the entity's data_max_delay_allowed_updated_by trace and the "
        "audit log) and confirm the operator still intends the entity pinned."
    )
    metadata = {
        "component": component,
        "drift_corrected": drift_corrected,
        "drifted_objects": sample,
        "drifted_objects_truncated": len(drifted_objects) > len(sample),
        "recommended_actions": [
            "Confirm the pinned value is still the operator's intent (the entity "
            "carries a threshold lock; review it in the UI).",
            "Inspect data_max_delay_allowed_updated_by and the audit log to find "
            "what overwrote the locked threshold.",
            "If drift recurs, unpin then re-pin the entity, or disable the "
            "conflicting auto-writer (adaptive delay / variable-delay review).",
        ],
    }

    upsert_guardian_alert(
        service,
        check_type=CHECK_THRESHOLD_INTENT_DRIFT,
        scope_key=scope_key,
        severity=SEVERITY_WARNING,
        scope="tenant",
        tenant_id=tenant_id,
        subject=tenant_alias,
        title=title,
        message=message,
        remediation=remediation,
        metadata=metadata,
        audit_index_name=audit_index_name,
    )
    outcome["status"] = "alert_created"
    outcome["drift_corrected"] = drift_corrected
    return outcome


# Tenant-scoped runners receive (session_key, splunkd_uri, service, tenant_record).
# System-scoped runners receive (session_key, splunkd_uri, service).
CHECK_REGISTRY = {
    CHECK_TENANT_OWNER_CAPABILITIES: {
        "scope": "tenant",
        "runner": check_tenant_owner_capabilities,
    },
    CHECK_ASSIGNED_INDEX_EXISTS: {
        "scope": "tenant",
        "runner": check_assigned_index_exists,
        # Fetch the SH-wide index catalogue once per run and reuse it for
        # every tenant — avoids N+1 REST calls to /services/data/indexes.
        "pre_run": lambda session_key, splunkd_uri, service: {
            "declared_indexes": fetch_declared_indexes(session_key, splunkd_uri),
        },
    },
    CHECK_REMOTE_ACCOUNT_TOKEN_EXPIRY: {
        "scope": "system",
        "runner": check_remote_account_token_expiry,
    },
    CHECK_REMOTE_ACCOUNT_CONNECTIVITY: {
        "scope": "system",
        "runner": check_remote_account_connectivity,
    },
    CHECK_AI_PROVIDER_UNREACHABLE: {
        "scope": "system",
        "runner": check_ai_provider_unreachable,
    },
    CHECK_BACKUP_ARCHIVE_TOO_OLD: {
        "scope": "system",
        "runner": check_backup_archive_too_old,
    },
    CHECK_BACKUP_RUN_INCOMPLETE: {
        "scope": "system",
        "runner": check_backup_run_incomplete,
    },
    CHECK_HEALTH_TRACKER_EXECUTING: {
        "scope": "tenant",
        "runner": check_health_tracker_executing,
    },
    CHECK_AI_FEED_LIFECYCLE_DELAY_CONFLICT: {
        "scope": "tenant",
        "runner": check_ai_feed_lifecycle_delay_conflict,
    },
}


def run_checks(
    session_key,
    splunkd_uri,
    service,
    tenant_records,
    tenant_id=None,
    check_type=None,
    audit_index_name=None,
):
    """Run the registered checks on-demand and return a delta.

    Arguments:
      * tenant_records — iterable of vtenant KV records (already loaded by the caller)
      * tenant_id — optional filter (run only for this tenant)
      * check_type — optional filter (run only this check)
      * audit_index_name — optional override (defaults to "trackme_audit")

    Returns ``{"created": [...], "cleared": [...], "unchanged": [...], "skipped": [...]}``
    where each entry is the outcome dict from the individual check.
    """
    delta = {"created": [], "cleared": [], "unchanged": [], "skipped": []}

    checks = {
        ct: spec
        for ct, spec in CHECK_REGISTRY.items()
        if check_type in (None, ct)
    }
    if not checks:
        return delta

    for ct, spec in checks.items():
        scope = spec["scope"]
        runner = spec["runner"]
        pre_run = spec.get("pre_run")

        # Fetch check-scoped shared context once per run (e.g. the SH-wide
        # index catalogue for assigned-index-exists). Failures are logged and
        # tolerated — each runner is expected to handle missing context
        # (e.g. fetch_declared_indexes=None triggers a per-tenant fallback).
        pre_kwargs = {}
        if pre_run is not None:
            try:
                pre_kwargs = pre_run(session_key, splunkd_uri, service) or {}
            except Exception as e:
                get_effective_logger().warning(
                    f'guardian_pre_run_failed check_type="{ct}", exception="{str(e)}"'
                )
                pre_kwargs = {}

        if scope == "tenant":
            for record in tenant_records or []:
                rec_tenant_id = str(record.get("tenant_id", ""))
                if tenant_id and tenant_id != rec_tenant_id:
                    continue
                try:
                    outcome = runner(
                        session_key,
                        splunkd_uri,
                        service,
                        record,
                        audit_index_name=audit_index_name,
                        **pre_kwargs,
                    )
                except Exception as e:
                    get_effective_logger().error(
                        f'guardian_check_runner_failed check_type="{ct}", '
                        f'tenant_id="{rec_tenant_id}", exception="{str(e)}"'
                    )
                    outcome = {
                        "status": "skipped",
                        "tenant_id": rec_tenant_id,
                        "check_type": ct,
                        "reason": f"exception: {str(e)}",
                    }
                outcome.setdefault("check_type", ct)
                bucket = {
                    "alert_created": "created",
                    "alert_cleared": "cleared",
                    "ok": "unchanged",
                }.get(outcome.get("status"), "skipped")
                delta[bucket].append(outcome)
        elif scope == "system":
            try:
                result = runner(
                    session_key,
                    splunkd_uri,
                    service,
                    audit_index_name=audit_index_name,
                    **pre_kwargs,
                )
            except Exception as e:
                get_effective_logger().error(
                    f'guardian_check_runner_failed check_type="{ct}", '
                    f'scope=system, exception="{str(e)}"'
                )
                result = {
                    "status": "skipped",
                    "check_type": ct,
                    "reason": f"exception: {str(e)}",
                }

            # A system-scoped runner may fan out across multiple subjects
            # (one alert per remote account, per email provider, etc.) and
            # return a list of outcomes. Flatten into the delta so the
            # reported counts reflect actual per-subject transitions rather
            # than collapsing the whole run into a single "unchanged" entry.
            outcomes_list = result if isinstance(result, list) else [result]
            for outcome in outcomes_list:
                if not isinstance(outcome, dict):
                    continue
                outcome.setdefault("check_type", ct)
                bucket = {
                    "alert_created": "created",
                    "alert_cleared": "cleared",
                    "ok": "unchanged",
                }.get(outcome.get("status"), "skipped")
                delta[bucket].append(outcome)

    return delta

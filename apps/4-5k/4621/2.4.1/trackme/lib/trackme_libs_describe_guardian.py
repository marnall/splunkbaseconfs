#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

"""
Configuration Guardian — describe-endpoint helpers.

Shared between the Virtual Tenants and Tenant Home `describe/*` endpoints
that feed the AI Assistant's per-page system prompt. Two contributions:

* ``build_guardian_knowledge()``    — static, text-heavy block the AI reads
  to know what Guardian is, which checks exist, and how to talk about them.
* ``load_active_guardian_alerts()`` — dynamic, RBAC-filtered list of
  currently-active alerts so the AI can see today's state and quote the
  exact title / remediation / metadata back to the user.

The two functions are deliberately decoupled: the knowledge block lists
every check and its semantics (so the AI can answer "what is this
`remote_account_connectivity_degraded` alert about?" even when no such
alert is active), while the alerts list is the live state.

This module ONLY reads — nothing here mutates KV or fires probes. That
belongs in `trackme_libs_guardian.py`.
"""

import json
import logging
from trackme_libs_logging import get_effective_logger
import time


# Keep in sync with `trackme_libs_guardian.CHECK_*` constants. Duplicated
# as literals here rather than imported because the describe library must
# not take a hard dependency on the guardian runtime module (separation
# of concerns — describe runs from a lightweight REST context and
# loading the whole guardian module is unnecessary for just reading KV
# + rendering a static knowledge blob).
_CHECK_TENANT_OWNER_CAPABILITIES = "insufficient_tenant_owner_capabilities"
_CHECK_ASSIGNED_INDEX_EXISTS = "assigned_index_does_not_exist"
_CHECK_REMOTE_ACCOUNT_TOKEN_EXPIRY = "remote_account_token_expiring_soon"
_CHECK_REMOTE_ACCOUNT_CONNECTIVITY = "remote_account_connectivity_degraded"
_CHECK_AI_PROVIDER_UNREACHABLE = "ai_provider_unreachable"
_CHECK_BACKUP_ARCHIVE_TOO_OLD = "backup_archive_too_old"
_CHECK_BACKUP_RUN_INCOMPLETE = "backup_run_incomplete"
_CHECK_HEALTH_TRACKER_EXECUTING = "health_tracker_not_executing"
_CHECK_AI_FEED_LIFECYCLE_DELAY_CONFLICT = "ai_feed_lifecycle_delay_conflict"
_CHECK_THRESHOLD_INTENT_DRIFT = "delay_threshold_drift_corrected"

_GUARDIAN_COLLECTION_NAME = "kv_trackme_configuration_guardian_alerts"


# -----------------------------------------------------------------------------
# Static knowledge block
# -----------------------------------------------------------------------------


def build_guardian_knowledge():
    """Return a structured knowledge block describing Configuration Guardian.

    Callers embed this dict under ``knowledge_reference.configuration_guardian``
    in their describe response. The AI Assistant uses it to answer
    "what is Guardian / what does this check mean / how do I remediate"
    questions even when no corresponding alert is active.

    The shape is stable — additional checks should be added as new entries in
    ``checks`` with the same schema. Do not rename existing keys without
    updating the AI Assistant system prompts that consume them.
    """
    return {
        "overview": (
            "Configuration Guardian is a modular misconfiguration-detection "
            "framework built into TrackMe. Checks run on a schedule, write "
            "alerts to the global `kv_trackme_configuration_guardian_alerts` "
            "collection when a condition is detected, and clear them "
            "automatically when the condition resolves (self-healing). "
            "Alerts surface in the Virtual Tenants UI as toast notifications "
            "grouped by check type, and via REST for admins and AI agents."
        ),
        "severity_tiers": {
            "warning": (
                "Attention needed but not urgent. Fallback / degraded state still "
                "keeps the system working. Yellow toast in the UI."
            ),
            "critical": (
                "Active degradation — data loss, dropped alerts, or a meta-failure "
                "(e.g. the health tracker itself not running). Red toast in the UI, "
                "title prefixed with `[CRITICAL]`. The UI promotes a whole "
                "check-type group to critical if any member is critical."
            ),
        },
        "dismissal_semantics": (
            "Dismissing an alert from the UI (the 'Dismiss alert' action on the "
            "toast) deletes the KV record. If the underlying condition still holds, "
            "the next detection cycle re-creates the alert — by design. There is "
            "no persistent 'snoozed' state: the alert keeps resurfacing until the "
            "root cause is fixed. This is intentional — it biases towards "
            "visibility rather than silencing."
        ),
        "remediation_mindset": (
            "Every active alert's `metadata` JSON contains a `recommended_actions` "
            "array — an ordered, concrete list of steps the admin (or AI) should "
            "take to remediate. Prefer quoting those exact steps back to the user "
            "rather than paraphrasing; they've been written to fit each check's "
            "specific root causes."
        ),
        "audit_trail": (
            "Every state transition (create, severity change, clear) is written "
            "to `index=trackme_audit sourcetype=trackme:audit:guardian` with "
            "structured fields (`action`, `alert_key`, `check_type`, `severity`, "
            "`prior_severity`, `tenant_id`, `subject`, `title`). Routine daily "
            "re-detections of the same condition do NOT emit audit events — "
            "time-bearing metadata fields are stripped from the dedup "
            "comparison. Useful for post-mortems and timeline reconstruction."
        ),
        "rest_endpoints": {
            "list_active_alerts": (
                "GET /services/trackme/v2/configuration/admin/guardian_alerts "
                "— returns every active alert with parsed `metadata_json`, "
                "`recommended_actions[]`, and counts by check_type / severity. "
                "Supports optional body filters: `tenant_id`, `check_type`, "
                "`severity`, `scope`."
            ),
            "run_on_demand": (
                "POST /services/trackme/v2/configuration/admin/run_guardian_checks "
                "— invokes the registered checks without waiting for the scheduled "
                "cron. Optional body filters: `tenant_id`, `check_type`. "
                "Returns `{created, cleared, unchanged, skipped}` delta."
            ),
            "dismiss_alert": (
                "POST /services/trackme/v2/configuration/admin/dismiss_guardian_alert "
                "— body `{\"alert_key\": \"<_key>\"}`. Temporary: the alert "
                "regenerates on the next cycle if the condition persists."
            ),
        },
        "checks": {
            _CHECK_TENANT_OWNER_CAPABILITIES: {
                "scope": "tenant",
                "severity_band": "warning",
                "detects": (
                    "A Virtual Tenant's `tenant_owner` service account is missing "
                    "one or more of the Splunk capabilities required for its "
                    "scheduled TrackMe operations to run correctly: "
                    "trackmeuseroperations, trackmepoweroperations, "
                    "trackmeadminoperations, schedule_search, list_settings, "
                    "list_storage_passwords, admin_all_objects. Capabilities are "
                    "resolved via role inheritance."
                ),
                "why_it_hurts": (
                    "Scheduled searches running under this account silently drop "
                    "writes, miss updates, or skip knowledge-object maintenance "
                    "— nothing else flags it."
                ),
                "host": "trackmetrackerhealth.py TIER_4 (daily per tenant)",
                "skip_conditions": [
                    "tenant is disabled",
                    "tenant_owner is `nobody` or empty",
                    "capability lookup fails (no false positives on infra errors)",
                ],
            },
            _CHECK_ASSIGNED_INDEX_EXISTS: {
                "scope": "tenant",
                "severity_band": "warning",
                "detects": (
                    "A tenant's `tenant_idx_settings` (top-level JSON field, "
                    "role-keyed: `trackme_summary_idx` / `trackme_audit_idx` / "
                    "`trackme_metric_idx` / `trackme_notable_idx`) points at an "
                    "index that doesn't exist on the search head, or for the "
                    "metric slot specifically, an index whose `datatype` is "
                    "not `metric`."
                ),
                "why_it_hurts": (
                    "The sibling `check_tenants_indexes_settings` task silently "
                    "reverts the broken slot to TrackMe's fallback default, so "
                    "the admin's original configuration is not in effect. The "
                    "Guardian surfaces the hidden revert."
                ),
                "host": (
                    "trackmegeneralhealthmanager.py (daily). One REST call to "
                    "/services/data/indexes serves every tenant via a "
                    "pre_run hook."
                ),
                "skip_conditions": [
                    "tenant is disabled",
                    "`tenant_idx_settings` is empty or `\"global\"`",
                    "/services/data/indexes call fails",
                ],
            },
            _CHECK_REMOTE_ACCOUNT_TOKEN_EXPIRY: {
                "scope": "system",
                "severity_band": "warning → critical",
                "detects": (
                    "A `trackme_account` remote bearer token is approaching, "
                    "or past, its actual expiry. The check decodes the "
                    "configured token's JWT `exp` claim (Splunk-issued tokens "
                    "are JWS-signed JWTs) and compares it to `now`. "
                    "Thresholds are proportional to the token's own lifetime "
                    "(`exp - iat`) capped by fixed ceilings: warning at "
                    "min(7 days, lifetime × 0.30), critical at min(24h, "
                    "lifetime × 0.10) or once the token has actually expired."
                ),
                "why_it_hurts": (
                    "Remote-deployment bearer tokens are the #1 cause of silent "
                    "multi-deployment failures. The earlier mtime-based check "
                    "conflated TrackMe's rotation cadence with the token's "
                    "actual lifetime and produced false-positive expired alerts "
                    "whenever a rotation cycle drifted past frequency or a "
                    "duplicate KV row skewed the picked timestamp."
                ),
                "host": "trackmegeneralhealthmanager.py (daily)",
                "skip_conditions": [
                    "account has `token_rotation_enablement=0` (no rotation)",
                    "invalid or missing rotation_frequency",
                    "no stored bearer token (configuration error)",
                    "configured credential is not a JWT (e.g. opaque external IdP key) — auth failures of these tokens are caught by `remote_account_connectivity_degraded`",
                    "JWT lacks an `exp` claim",
                ],
                "notes": (
                    "Authoritative source is the JWT `exp` claim of the "
                    "configured bearer token, not `kv_trackme_remote_account_"
                    "token_expiration.mtime`. The KV mtime remains useful for "
                    "the dashboard's `time_since_last_rotation` column but is "
                    "no longer load-bearing for expiry detection."
                ),
            },
            _CHECK_REMOTE_ACCOUNT_CONNECTIVITY: {
                "scope": "system",
                "severity_band": "warning → critical",
                "detects": (
                    "Per-account probe via POST /services/trackme/v2/configuration/"
                    "test_remote_account — exercises URL resolution, auth, and a "
                    "remote-search smoke test. First-cycle failure → warning. "
                    "Promoted to critical once the failure has persisted for more "
                    "than 24 hours (tracked via `first_failure_mtime` carried "
                    "across upserts in the alert's own metadata)."
                ),
                "why_it_hurts": (
                    "Auth failures, SSL issues and network outages on remote "
                    "deployments were only discoverable when a scheduled search "
                    "tried to run and failed. The probe centralises the signal."
                ),
                "host": "trackmegeneralhealthmanager.py (daily)",
                "skip_conditions": [
                    "no remote accounts configured",
                    "connectivity endpoint itself unreachable (no false positives)",
                ],
            },
            _CHECK_AI_PROVIDER_UNREACHABLE: {
                "scope": "system",
                "severity_band": "warning",
                "detects": (
                    "Daily `test_llm_connectivity` probe for each configured AI "
                    "provider. Alerts on provider-side auth failures, network / "
                    "DNS issues, provider outages. One alert per provider."
                ),
                "why_it_hurts": (
                    "AI status reports embedded in stateful alerts silently lack "
                    "the AI paragraph when the provider is down; interactive chat "
                    "jobs fail one-request-at-a-time with no aggregate visibility."
                ),
                "host": (
                    "trackmegeneralhealthmanager.py (daily). Skipped entirely "
                    "when `enable_ai_assistant=0` or no providers are configured."
                ),
                "skip_conditions": [
                    "AI assistant disabled (`enable_ai_assistant=0`)",
                    "no AI providers configured",
                    "per-provider config or API-key lookup fails "
                    "(skip that provider only, not the whole check)",
                    "provider has been disabled by the admin "
                    "(`ai_enabled=0` on its stanza) — skip the probe and "
                    "clear any stale alert for that provider",
                ],
                "notes": (
                    "Severity is always `warning` — AI is opt-in and "
                    "non-critical; an unreachable provider degrades features "
                    "but does not lose data."
                ),
            },
            _CHECK_BACKUP_ARCHIVE_TOO_OLD: {
                "scope": "system",
                "severity_band": "warning → critical",
                "detects": (
                    "Most-recent run's `archive_scope='global'` row in "
                    "`kv_trackme_backup_archives_info` (or, on un-upgraded "
                    "installs with only legacy archives, the most-recent row "
                    "overall) has an `mtime` older than the "
                    "`trackme_backup_scheduler` cron cadence × 1.5 (warning) "
                    "or older than 7 days (critical). Cadence is parsed from "
                    "the saved-search cron via `croniter`, so non-daily "
                    "schedules (12-hourly, 6-hourly) are handled correctly. "
                    "Anchoring on the global row ensures a late-finishing "
                    "tenant archive cannot mask a stale run."
                ),
                "why_it_hurts": (
                    "If the backup scheduler silently skips or errors, you "
                    "discover it during a disaster-recovery attempt — the "
                    "worst possible moment."
                ),
                "host": "trackmegeneralhealthmanager.py (daily)",
                "skip_conditions": [
                    "backup scheduler saved search missing, disabled, or not "
                    "scheduled (backups are opt-in)",
                    "no archive records in the KV yet (fresh install)",
                ],
            },
            _CHECK_BACKUP_RUN_INCOMPLETE: {
                "scope": "system",
                "severity_band": "warning",
                "detects": (
                    "The most recent 3.0.0 backup run produced fewer "
                    "`archive_scope='tenant'` rows than there are currently "
                    "enabled virtual tenants. Identifies the latest run by "
                    "the newest global row's `mtime`, then counts tenant "
                    "archives carrying that `backup_run_id` and compares to "
                    "the enabled tenant count from "
                    "`kv_trackme_virtual_tenants`. Tenants in the enabled "
                    "set without a tenant archive in the latest run are "
                    "reported in `metadata.missing_tenants`."
                ),
                "why_it_hurts": (
                    "post_backup's per-tenant isolation lets a backup run "
                    "complete even when a tenant's payload is corrupted "
                    "(intentional design — a single bad tenant must not "
                    "block recovery for everyone else). But a tenant "
                    "without an archive in the latest run is NOT restorable "
                    "from that run. Without this check, the operator only "
                    "discovers the gap at recovery time."
                ),
                "host": "trackmegeneralhealthmanager.py (daily)",
                "skip_conditions": [
                    "backup scheduler saved search missing, disabled, or not "
                    "scheduled",
                    "no 3.0.0 runs in the KV yet (un-upgraded install with "
                    "only legacy archives)",
                    "no enabled tenants",
                ],
                "notes": (
                    "Self-healing — once the next complete run lands, the "
                    "alert clears. Distinct from `backup_archive_too_old` "
                    "(catastrophic-DR signal); this is the per-tenant "
                    "degradation signal."
                ),
            },
            _CHECK_HEALTH_TRACKER_EXECUTING: {
                "scope": "tenant",
                "severity_band": "critical",
                "detects": (
                    "A tenant's `trackme_health_tracker_tenant_<tid>` saved "
                    "search has not recorded a successful cycle in "
                    "`kv_trackme_health_tracker_state` in the last 30 minutes "
                    "(= 6 missed 5-minute cycles). This is the meta-check: "
                    "without it, every other per-tenant Guardian check goes "
                    "stale silently."
                ),
                "why_it_hurts": (
                    "Alert state, ACK expiration, and entity status "
                    "calculations also depend on this tracker — a stalled "
                    "tracker is a cascading failure."
                ),
                "host": (
                    "trackmegeneralhealthmanager.py (daily). MUST NOT run "
                    "inside the tenant health tracker itself — the tracker "
                    "cannot diagnose its own absence."
                ),
                "skip_conditions": [
                    "tenant is disabled",
                    "health-tracker saved search not provisioned yet (fresh tenant)",
                    "saved search is disabled (admin turned tracking off)",
                ],
            },
            _CHECK_AI_FEED_LIFECYCLE_DELAY_CONFLICT: {
                "scope": "tenant",
                "severity_band": "warning",
                "detects": (
                    "A tenant has the AI Feed Lifecycle Advisor enabled for "
                    "DSM or DHM (`ai_components_advisor_enabled=1` AND DSM "
                    "or DHM in `ai_components_advisor_list`) AND at least "
                    "one of the legacy mechanical delay flags is still 1 "
                    "(`adaptive_delay` and/or `variable_delay_auto_review`). "
                    "Both subsystems write to the same delay-threshold "
                    "fields on the same entities — only one can be the "
                    "authority at a time, and when the AI advisor is on for "
                    "DSM/DHM it wins by design."
                ),
                "why_it_hurts": (
                    "The runtime gates in `trackmesplkadaptivedelay` and "
                    "`trackmesplkvariabledelayreview` short-circuit when "
                    "the AI advisor covers their component, so no data is "
                    "harmed — but the persisted configuration is "
                    "inconsistent and confusing. Operators expect the "
                    "legacy flag values to reflect what's running."
                ),
                "host": (
                    "trackmetrackerhealth.py TIER_4 (daily per tenant). "
                    "The UCC save-time hook "
                    "`trackme_rh_vtenants_handler.CustomRestHandlerVtenants` "
                    "is the primary control — it flips both legacy flags to "
                    "0 whenever the AI advisor is turned on for DSM/DHM. "
                    "This Guardian check catches drift from direct KV pokes "
                    "or any API path that bypasses the UCC hook."
                ),
                "skip_conditions": [
                    "tenant is disabled",
                    "tenant record has no `vtenant_account` block (pre-AI-advisor schema)",
                    "AI Feed Lifecycle Advisor does not cover DSM or DHM "
                    "(advisor disabled, or DSM/DHM removed from "
                    "`ai_components_advisor_list`)",
                ],
            },
            _CHECK_THRESHOLD_INTENT_DRIFT: {
                "scope": "tenant",
                "severity_band": "warning",
                "detects": (
                    "An operator pinned (locked) a DSM/DHM entity's delay or lag "
                    "threshold — recorded in the per-tenant threshold-intent "
                    "ledger (`kv_trackme_{dsm,dhm}_threshold_intent_tenant_<tid>`) "
                    "with the on-record flags `data_max_delay_allowed_locked` / "
                    "`data_max_lag_allowed_locked` — and the live value later "
                    "drifted away from the requested value. The periodic reconcile "
                    "task detected the drift and restored the pinned value; this "
                    "alert reports how many entities were corrected and lists a "
                    "sample of their object names in `metadata.drifted_objects`."
                ),
                "why_it_hurts": (
                    "A pinned threshold is meant to be authoritative. The "
                    "real-time source gates make adaptive delay, variable-delay "
                    "review and lagging-class overrides skip pinned entities, so "
                    "drift should never happen through normal paths. Drift means "
                    "something bypassed the gates — a direct KV edit, a "
                    "downgrade/upgrade window, or an un-gated future writer — and "
                    "would have silently changed a threshold the operator "
                    "deliberately fixed. The value is auto-restored, so it is "
                    "warning (attention needed), not active degradation."
                ),
                "host": (
                    "trackmetrackerhealth.py TIER_3 (~6h per tenant), fired from "
                    "the `reconcile_threshold_intent` task. Event-driven (not a "
                    "CHECK_REGISTRY scan runner): the reconcile does the "
                    "read+restore and hands its summary to "
                    "`check_threshold_intent_drift`. Self-healing — clears on the "
                    "next cycle with no drift."
                ),
                "skip_conditions": [
                    "tenant is disabled",
                    "the per-tenant master toggle `delay_threshold_lock_enabled` is off",
                    "no entities are pinned (empty intent ledger)",
                    "DSM/DHM not enabled on the tenant",
                ],
            },
        },
        "how_ai_should_respond": (
            "When a user asks about an active Guardian alert, prefer quoting "
            "the alert's own `title`, `message` and `remediation` fields plus "
            "the `recommended_actions` array from the parsed metadata — those "
            "are the authoritative, per-alert strings. Use this knowledge "
            "block only for contextualising what a check TYPE means when no "
            "active alert is present or when the user asks a general question "
            "('what is Guardian?', 'what kinds of things does it check?')."
        ),
        "assistant_playbook": {
            "role": (
                "You are an active guide, not a passive reporter. When a Guardian "
                "alert is live, your job is to help the user *remediate it* — "
                "walk them through each step, offer to run verification SPL on "
                "their behalf (suggest the exact search), and confirm resolution "
                "once they've acted. Lead with 'here's what to do'; follow up "
                "with 'want me to help you verify?'"
            ),
            "response_pattern_for_active_alert": [
                "1. State what's wrong in one sentence using the alert's `title`.",
                "2. Explain briefly WHY it matters (use the check's `why_it_hurts`).",
                "3. List the remediation steps — copy verbatim from "
                "`metadata_json.recommended_actions` (don't paraphrase; "
                "they've been written specifically for this condition).",
                "4. Offer a concrete next action the user can take now — "
                "e.g. 'Want me to show you the SPL to verify the fix?' or "
                "'Shall I walk you through rotating the token?'",
                "5. After the user acts, suggest the verification step (rerun "
                "the Guardian check on-demand via the REST endpoint and "
                "confirm the alert cleared).",
            ],
            "response_pattern_when_no_alerts": (
                "If the user asks about Guardian and nothing is active, "
                "confirm all checks are clean ('no Guardian alerts currently "
                "active — your tenant is in good shape'), then offer to "
                "explain what Guardian monitors or show how to run a check "
                "on-demand. Don't be falsely reassuring: if the "
                "`health_tracker_not_executing` check itself isn't running, "
                "every other per-tenant check goes stale silently — "
                "actively mention this possibility."
            ),
            "clarifying_questions_to_offer": [
                "For a token-expiry alert: 'Do you already have a new bearer "
                "token ready, or would you like me to walk you through "
                "generating one on the remote deployment first?'",
                "For a capabilities alert: 'I can list the specific role you "
                "need to edit and the capabilities to add — want me to show "
                "you that?'",
                "For an index-missing alert: 'Should we create the missing "
                "index on the search head, or would you rather re-assign the "
                "tenant to an existing index? Both are valid remediations.'",
                "For an AI-provider alert: 'Is this a provider-side issue "
                "(API key revoked, outage) or a network issue from this search "
                "head? The answer changes the remediation path.'",
                "For a backup-too-old alert: 'Has the backup scheduler saved "
                "search been recently disabled, or is it enabled but failing? "
                "I can help you check its last execution status.'",
            ],
            "proactive_checks": (
                "When a tenant is under discussion and the user is troubleshooting "
                "ANY TrackMe issue (entities stuck, alerts not firing, missing "
                "data), do a quick pass over this tenant's active Guardian "
                "alerts before diving into deeper diagnostics — a Guardian "
                "alert is often the root cause disguised as a downstream symptom. "
                "Example: 'entities not updating' → check "
                "`health_tracker_not_executing`; 'remote data missing' → check "
                "`remote_account_token_expiring_soon` and "
                "`remote_account_connectivity_degraded`."
            ),
            "verification_after_remediation": (
                "After the user says they've remediated, offer to: "
                "(a) show the `POST /services/trackme/v2/configuration/admin/"
                "run_guardian_checks` SPL example they can paste, filtered to "
                "the relevant `check_type`, so they can confirm the alert has "
                "cleared; (b) read the audit trail afterwards "
                "(`index=trackme_audit sourcetype=trackme:audit:guardian` "
                "filtered by `check_type` and `action=guardian_alert_cleared`) "
                "to confirm the resolution was recorded."
            ),
            "escalation_paths": {
                "ai_cannot_resolve": (
                    "If the user has tried the recommended actions and the "
                    "alert persists, suggest: (1) inspect the relevant TrackMe "
                    "log file under `$SPLUNK_HOME/var/log/splunk/trackme_*.log` "
                    "— each check's metadata names the relevant log; (2) "
                    "check the Guardian audit trail for prior transitions; "
                    "(3) contact TrackMe support with the audit-trail excerpt "
                    "and the alert's `alert_key`."
                ),
                "permission_blocker": (
                    "If a remediation requires Splunk admin access the user "
                    "doesn't have (e.g. creating a Splunk index, editing role "
                    "capabilities, rotating storage_passwords entries), say so "
                    "explicitly and suggest they escalate to a Splunk "
                    "administrator. Don't suggest hacks that bypass the "
                    "intended RBAC."
                ),
            },
        },
    }


# -----------------------------------------------------------------------------
# Dynamic state — active alerts, RBAC-filtered
# -----------------------------------------------------------------------------


def _parse_metadata_json(metadata_str):
    """Parse a JSON-encoded metadata string into a dict. Returns None on parse
    failure so callers can fall back to the raw string if needed."""
    if not isinstance(metadata_str, str) or not metadata_str.strip():
        return None
    try:
        parsed = json.loads(metadata_str)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _enrich_alert(record):
    """Transform a raw KV record into an AI-friendly dict.

    Parses `metadata` JSON into `metadata_json`, lifts `recommended_actions`
    to the top level for easy consumption, and derives `mtime_iso` for
    human-readable display.
    """
    metadata_raw = record.get("metadata")
    metadata_json = _parse_metadata_json(metadata_raw)
    recommended_actions = []
    if isinstance(metadata_json, dict):
        ra = metadata_json.get("recommended_actions")
        if isinstance(ra, list):
            recommended_actions = [str(x) for x in ra]

    try:
        mtime_float = float(record.get("mtime") or 0)
    except (TypeError, ValueError):
        mtime_float = 0.0
    mtime_iso = (
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime_float))
        if mtime_float > 0
        else None
    )

    return {
        "_key": record.get("_key"),
        "check_type": record.get("check_type"),
        "severity": record.get("severity"),
        "scope": record.get("scope"),
        "tenant_id": record.get("tenant_id") or "",
        "subject": record.get("subject") or "",
        "title": record.get("title"),
        "message": record.get("message"),
        "remediation": record.get("remediation"),
        "metadata_json": metadata_json,
        "recommended_actions": recommended_actions,
        "mtime": mtime_float,
        "mtime_iso": mtime_iso,
    }


def load_active_guardian_alerts(service, visible_tenant_ids=None, tenant_id_filter=None):
    """Return the list of enriched, currently-active Guardian alerts.

    Args:
        service: Splunk service connection with access to the guardian KV.
        visible_tenant_ids: Optional iterable of tenant IDs the caller is
            allowed to see (derived from the describe endpoint's RBAC logic).
            System-scoped alerts (empty `tenant_id`) are always included.
            If None, all tenant-scoped alerts are returned (caller takes
            responsibility for RBAC).
        tenant_id_filter: Optional single-tenant filter. When set (typical
            for the tenant_home describe endpoint), only this tenant's
            alerts + system-scoped alerts are returned.

    Returns:
        A dict ready to embed in the describe response:

            {
                "count": <int>,
                "counts_by_check_type": {check_type: N, ...},
                "counts_by_severity": {"warning": N, "critical": N},
                "alerts": [<enriched alert>, ...],
            }

        Failure to read the KV returns an empty result — the describe
        endpoint should keep working even if the Guardian collection is
        transiently unavailable.
    """
    empty_result = {
        "count": 0,
        "counts_by_check_type": {},
        "counts_by_severity": {"warning": 0, "critical": 0},
        "alerts": [],
    }

    try:
        collection = service.kvstore[_GUARDIAN_COLLECTION_NAME]
        rows = list(collection.data.query() or [])
    except Exception as e:
        get_effective_logger().warning(
            f'function=load_active_guardian_alerts, step="kv_query", '
            f'exception="{str(e)}"'
        )
        return empty_result

    # Normalise visibility filters. System-scoped records (empty tenant_id)
    # are always visible; per-tenant records are gated by visible_tenant_ids
    # AND/OR tenant_id_filter when provided.
    visible_set = (
        {str(tid) for tid in visible_tenant_ids if tid}
        if visible_tenant_ids is not None
        else None
    )
    single_tenant = str(tenant_id_filter) if tenant_id_filter else None

    enriched_alerts = []
    counts_by_check_type = {}
    counts_by_severity = {"warning": 0, "critical": 0}

    for record in rows:
        scope = record.get("scope") or ""
        rec_tenant_id = str(record.get("tenant_id") or "")

        if scope == "tenant" and rec_tenant_id:
            if single_tenant is not None and rec_tenant_id != single_tenant:
                continue
            if visible_set is not None and rec_tenant_id not in visible_set:
                continue
        # system-scope (tenant_id empty) — always visible

        enriched = _enrich_alert(record)
        enriched_alerts.append(enriched)

        ct = enriched.get("check_type") or "unknown"
        counts_by_check_type[ct] = counts_by_check_type.get(ct, 0) + 1
        sev = enriched.get("severity") or "warning"
        if sev in counts_by_severity:
            counts_by_severity[sev] += 1

    # Sort: critical first, then by most-recent mtime so the AI sees
    # the most urgent / freshest items at the top of its context.
    enriched_alerts.sort(
        key=lambda a: (
            0 if a.get("severity") == "critical" else 1,
            -(a.get("mtime") or 0.0),
        )
    )

    return {
        "count": len(enriched_alerts),
        "counts_by_check_type": counts_by_check_type,
        "counts_by_severity": counts_by_severity,
        "alerts": enriched_alerts,
    }

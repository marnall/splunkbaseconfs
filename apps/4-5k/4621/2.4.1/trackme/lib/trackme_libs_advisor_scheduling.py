#!/usr/bin/env python
# coding=utf-8

# Deferred annotation evaluation — the AI REST handlers are configured
# with ``python.required = 3.9,3.13`` in restmap.conf, so this module
# is imported on both 3.9 and 3.13 deployments.
from __future__ import annotations

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"

"""Immediate advisor saved-search scheduling reconciliation.

Used by ``trackme_rh_vtenants_handler.CustomRestHandlerVtenants.handleEdit``
to flip the ``is_scheduled`` field on advisor saved-searches IN-BAND with
a vtenants save, instead of waiting up to 5 minutes for the per-tenant
health tracker's next cycle.

## Why this exists

Without this hook, the flow looks like:

  1. Admin toggles ``ai_mladvisor_enabled = 1`` in the Manage AI Agents
     automation page.
  2. ``trackme_vtenants`` UCC save persists the new value.
  3. The advisor saved-search stays ``is_scheduled = 0`` (the default
     PR #1782 ships) until the per-tenant tracker fires.
  4. Up to ~5 minutes later, the tracker's triple-gate evaluation re-runs
     and flips the saved-search ``is_scheduled = 1``.

That 5-minute lag is invisible from the tracker's perspective but very
visible to the admin who just toggled the flag. This module closes the
gap.

## Contract

``reconcile_advisor_scheduling_on_save()`` mirrors the per-tenant
tracker's **triple gate** (every advisor saved-search must satisfy):

    feature_enabled = ai_infra_ready AND per_tenant_flag

    where ai_infra_ready = enable_ai_assistant AND providers_configured

The function evaluates the post-save target state and applies the
``is_scheduled`` mutation to each advisor saved-search. Returns a dict
summarising what changed for caller-side logging.

## Safety nets

  - **Best-effort.** Any failure inside this module MUST NOT break the
    underlying tenant save. The caller wraps the entire call in
    ``try / except Exception`` and logs the failure. The per-tenant
    tracker will reconcile the same state on its next cycle (the
    durable safety net).
  - **Idempotent.** Calling the function with no flags changed is a
    no-op (every saved-search already in target state).
  - **Triple-gate consistent.** When the global toggle is off, when no
    provider is configured, or when the per-tenant flag is 0, the
    function un-schedules; it does not leave saved-searches running
    against an unusable provider stack.

## Why a separate module rather than refactoring the tracker

The tracker's inline scheduling block (in
``package/bin/trackmetrackerhealth.py``) intentionally inlines the
``manage_savedsearch_schedule`` helper with defensive default-fill
logic for missing schedule properties — an artefact of supporting
saved-searches from pre-2.3.x tenants whose ``cron_schedule`` /
``dispatch.*`` properties may have been cleared. This module makes a
simpler assumption: the saved-searches are seeded with all schedule
properties in ``trackme_rest_handler_vtenants_admin.py``, so the only
field to flip here is ``is_scheduled``. The two paths share the same
intent (the triple-gate decision) but diverge on implementation surface
to keep both narrow.
"""

import logging
from trackme_libs_logging import get_effective_logger

# Saved-search name templates per advisor, keyed by the component the
# advisor applies to. Mirrors the per-tenant tracker's scheduling block
# (``package/bin/trackmetrackerhealth.py`` around line 1573-1663).
_ML_ADVISOR_COMPONENTS = ("dsm", "dhm", "flx")
_FEED_LIFECYCLE_COMPONENTS = ("dsm", "dhm")
_FLX_THRESHOLD_COMPONENT = "flx"
_FQM_ADVISOR_COMPONENT = "fqm"
_COMPONENT_HEALTH_COMPONENTS = ("wlk", "mhm")


def _coerce_int(value, default=0):
    """Best-effort int coercion — UCC stores everything as strings, and
    a typo or missing field must NOT throw inside the reconcile loop."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalise_components_csv(raw):
    """Lowercase, stripped, non-empty set of components in a CSV string."""
    if not raw:
        return set()
    return {c.strip().lower() for c in str(raw).split(",") if c.strip()}


def _build_target_state(tenant_id, vtenant_account, ai_infra_ready):
    """Compute the target ``is_scheduled`` value for every advisor
    saved-search this tenant may have.

    Args:
        tenant_id: Tenant identifier (used to build saved-search names).
        vtenant_account: Post-save dict of vtenant_account fields.
        ai_infra_ready: True iff ``enable_ai_assistant=1`` globally AND
            at least one AI provider is configured.

    Returns:
        dict[str, bool] keyed by saved-search name, value = True if the
        saved-search should be ``is_scheduled = 1`` after this save.
    """
    ml_enabled = _coerce_int(vtenant_account.get("ai_mladvisor_enabled"), 0) == 1
    comp_adv_enabled = (
        _coerce_int(vtenant_account.get("ai_components_advisor_enabled"), 0) == 1
    )
    comp_list = _normalise_components_csv(
        vtenant_account.get("ai_components_advisor_list")
    )

    def _tenant_component_enabled(component):
        return (
            _coerce_int(vtenant_account.get(f"tenant_{component}_enabled"), 0) == 1
        )

    def _components_advisor_active(component):
        return (
            ai_infra_ready
            and comp_adv_enabled
            and component in comp_list
            and _tenant_component_enabled(component)
        )

    targets: dict[str, bool] = {}

    # ML Advisor — automated model inspection (DSM/DHM/FLX).
    for component in _ML_ADVISOR_COMPONENTS:
        ss = f"trackme_{component}_outliers_mladvisor_tracker_tenant_{tenant_id}"
        targets[ss] = (
            ai_infra_ready
            and ml_enabled
            and _tenant_component_enabled(component)
        )

    # Feed Lifecycle Advisor — DSM/DHM.
    for component in _FEED_LIFECYCLE_COMPONENTS:
        ss = f"trackme_{component}_feed_lifecycle_advisor_tracker_tenant_{tenant_id}"
        targets[ss] = _components_advisor_active(component)

    # FLX Threshold Advisor — FLX only.
    targets[
        f"trackme_flx_threshold_advisor_tracker_tenant_{tenant_id}"
    ] = _components_advisor_active(_FLX_THRESHOLD_COMPONENT)

    # FQM Advisor — FQM only.
    targets[
        f"trackme_fqm_advisor_tracker_tenant_{tenant_id}"
    ] = _components_advisor_active(_FQM_ADVISOR_COMPONENT)

    # Component Health Advisor — WLK / MHM.
    for component in _COMPONENT_HEALTH_COMPONENTS:
        ss = f"trackme_{component}_component_health_advisor_tracker_tenant_{tenant_id}"
        targets[ss] = _components_advisor_active(component)

    return targets


def _check_ai_infra_ready(service):
    """Evaluate the deployment-wide signals composing ``ai_infra_ready``:
    the global ``enable_ai_assistant`` toggle AND at least one usable
    AI provider configured.

    Conservative fallbacks on failure: the global toggle defaults to
    True (so a transient conf-read glitch doesn't accidentally
    un-schedule a healthy tenant), the provider count defaults to 0 (so
    a doomed LLM call doesn't fire if we can't confirm a provider
    exists). Same fallback policy as the per-tenant tracker.
    """
    # Global enable_ai_assistant
    ai_enabled_globally = True
    try:
        trackme_settings_conf = service.confs["trackme_settings"]
        for stanza in trackme_settings_conf:
            if stanza.name == "trackme_general":
                if stanza.content.get("enable_ai_assistant", "1") == "0":
                    ai_enabled_globally = False
                break
    except Exception as exc:
        get_effective_logger().warning(
            f"trackme_libs_advisor_scheduling: failed to read "
            f"enable_ai_assistant from trackme_settings, falling back to "
            f'ai_enabled_globally=True, exception="{exc}"'
        )

    # Providers configured
    providers_count = 0
    try:
        from trackme_libs_ai import list_ai_providers

        providers_count = len(list_ai_providers(service))
    except Exception as exc:
        get_effective_logger().warning(
            f"trackme_libs_advisor_scheduling: failed to list AI providers, "
            f'falling back to providers_configured=False, exception="{exc}"'
        )

    return ai_enabled_globally and providers_count >= 1


def reconcile_advisor_scheduling_on_save(
    session_key,
    splunkd_uri,
    service,
    tenant_id,
    vtenant_account,
    log_context="vtenants_save",
):
    """Reconcile every advisor saved-search for ``tenant_id`` to its
    target ``is_scheduled`` state, in-band with a vtenants save.

    Best-effort, idempotent. Mirrors the per-tenant health tracker's
    triple gate (``ai_infra_ready AND per_tenant_flag``) so the two
    paths converge on the same outcome regardless of which one runs
    first after a flag change.

    Args:
        session_key: Splunk session token (caller's authenticated
            session — typically the admin who triggered the save).
        splunkd_uri: ``https://host:port`` for REST calls.
        service: splunklib ``client.Service`` connection (used for the
            ``trackme_settings`` conf lookup and the AI providers list).
        tenant_id: Tenant whose advisor saved-searches we're reconciling.
        vtenant_account: Post-save dict of vtenant_account fields. The
            handler's ``self.payload`` after ``_apply_mutex`` ran is the
            authoritative source. Fields read:
              - ``tenant_<comp>_enabled`` (any of dsm/dhm/mhm/flx/fqm/wlk)
              - ``ai_mladvisor_enabled``
              - ``ai_components_advisor_enabled``
              - ``ai_components_advisor_list``
            Missing keys default to 0 (advisor disabled) — never raise.
        log_context: Short identifier added to every log line so
            operators can correlate saves with reconciliation outcomes.

    Returns:
        dict[str, list] summarising the work performed:
          - ``enabled``: saved-searches flipped from is_scheduled=0 to 1
          - ``disabled``: saved-searches flipped from is_scheduled=1 to 0
          - ``unchanged``: saved-searches already in target state
          - ``skipped``: saved-searches the function couldn't touch
              (typically because they don't exist for this tenant yet —
              this happens on legacy pre-2.4.0 tenants that haven't been
              re-seeded; the tracker's safety-net path handles them on
              its next cycle).
    """
    summary: dict[str, list] = {
        "enabled": [],
        "disabled": [],
        "unchanged": [],
        "skipped": [],
    }

    # Lazy import — the UCC handler this module is invoked from lives
    # in the EAI Python bundle, which has a narrower import surface
    # than the main REST / search runtime. ``trackme_libs`` imports
    # splunklib + many other deps lazily; doing the same here keeps
    # module load cheap and avoids any boot-time surprises in the
    # bundle.
    try:
        from trackme_libs import trackme_manage_report_schedule
    except ImportError as exc:
        get_effective_logger().warning(
            f'trackme_libs_advisor_scheduling: log_context="{log_context}", '
            f'tenant_id="{tenant_id}", failed to import '
            f'trackme_manage_report_schedule, skipping immediate reconcile '
            f'(tracker will handle on next cycle), exception="{exc}"'
        )
        return summary

    ai_infra_ready = _check_ai_infra_ready(service)
    targets = _build_target_state(tenant_id, vtenant_account, ai_infra_ready)

    get_effective_logger().info(
        f'trackme_libs_advisor_scheduling: log_context="{log_context}", '
        f'tenant_id="{tenant_id}", ai_infra_ready="{ai_infra_ready}", '
        f'target_savedsearches={len(targets)}'
    )

    for ss_name, should_be_scheduled in targets.items():
        try:
            # Read current is_scheduled and the full schedule properties
            # so action="enable"/"disable" round-trips them unchanged
            # (the underlying ``savedsearch_object.update(**properties)``
            # call rewrites every field we hand it).
            properties, _acl = trackme_manage_report_schedule(
                logging,
                session_key,
                splunkd_uri,
                tenant_id,
                ss_name,
                action="status",
            )
        except Exception as exc:
            # Most common cause: the saved-search doesn't exist for
            # this tenant (legacy pre-2.4.0 tenants seeded before the
            # advisors existed). The tracker's safety-net path
            # tolerates this the same way.
            summary["skipped"].append({"name": ss_name, "reason": str(exc)})
            get_effective_logger().info(
                f'trackme_libs_advisor_scheduling: log_context="{log_context}", '
                f'tenant_id="{tenant_id}", savedsearch="{ss_name}", '
                f'status check failed (likely not seeded for this tenant), '
                f'skipping. tracker will reconcile on next cycle. '
                f'exception="{exc}"'
            )
            continue

        current_is_scheduled = _coerce_int(properties.get("is_scheduled"), 0) == 1
        if current_is_scheduled == should_be_scheduled:
            summary["unchanged"].append(ss_name)
            continue

        action = "enable" if should_be_scheduled else "disable"
        try:
            trackme_manage_report_schedule(
                logging,
                session_key,
                splunkd_uri,
                tenant_id,
                ss_name,
                input_report_properties=properties,
                action=action,
            )
            if should_be_scheduled:
                summary["enabled"].append(ss_name)
            else:
                summary["disabled"].append(ss_name)
            get_effective_logger().info(
                f'trackme_libs_advisor_scheduling: log_context="{log_context}", '
                f'tenant_id="{tenant_id}", savedsearch="{ss_name}", '
                f'action="{action}", success'
            )
        except Exception as exc:
            summary["skipped"].append({"name": ss_name, "reason": str(exc)})
            get_effective_logger().error(
                f'trackme_libs_advisor_scheduling: log_context="{log_context}", '
                f'tenant_id="{tenant_id}", savedsearch="{ss_name}", '
                f'action="{action}", failed to update '
                f'(tracker will reconcile on next cycle), '
                f'exception="{exc}"'
            )

    get_effective_logger().info(
        f'trackme_libs_advisor_scheduling: log_context="{log_context}", '
        f'tenant_id="{tenant_id}", reconcile complete, '
        f'enabled={len(summary["enabled"])}, '
        f'disabled={len(summary["disabled"])}, '
        f'unchanged={len(summary["unchanged"])}, '
        f'skipped={len(summary["skipped"])}'
    )
    return summary

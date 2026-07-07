"""UCC handler hook for the ``trackme_vtenants`` endpoint.

Primary responsibility: enforce the mutex between the AI Feed Lifecycle
Advisor and the legacy mechanical Adaptive Delay (+ Variable Delay
Auto-Review) on every save.

## Mutex contract

When an incoming write to a tenant record carries:

  * ``ai_components_advisor_enabled = 1`` AND
  * ``ai_components_advisor_list`` containing ``dsm`` or ``dhm``

then the AI Feed Lifecycle Advisor becomes the authority for DSM/DHM
delay management on that tenant. The legacy mechanical features must
stand down:

  * ``adaptive_delay`` is forced to ``"0"`` in the outgoing record.
  * ``variable_delay_auto_review`` is forced to ``"0"`` in the
    outgoing record.

This is the **primary** control. Two safety nets back it up — the
runtime gates in ``trackmesplkadaptivedelay.py`` and
``trackmesplkvariabledelayreview.py`` (short-circuit if AI covers the
component), and the Configuration Guardian check
``ai_feed_lifecycle_delay_conflict`` (raises a warning on any
inconsistent persisted state).

The reverse direction is **not** automatic: disabling the AI advisor
does NOT re-enable the legacy flags. An admin who wants the legacy
behaviour back must explicitly re-toggle ``adaptive_delay`` and / or
``variable_delay_auto_review`` after disabling the AI advisor or
removing DSM / DHM from its component list.

## Pass-through behaviour

Saves that do not turn the AI advisor on (or that turn it on without
DSM / DHM in scope) are passed straight through to the upstream UCC
handler with no mutation. The hook only activates when the trigger
condition is met.

## Audit trail

Every field flip emits one ``trackme_audit_event`` with
``change_type="ai_feed_lifecycle_mutex_auto_disable"`` so the rewrite
shows up in ``audit_events_v2`` and the admin can trace why a legacy
flag flipped.
"""

import import_declare_test  # noqa: F401  (UCC convention — import side-effects load lib/ into sys.path)
import json
import logging

from splunktaucclib.rest_handler.admin_external import AdminExternalHandler


# The set of components the AI Feed Lifecycle Advisor manages delay for.
# Kept here rather than imported from ``trackme_libs`` to keep this
# handler dependency-light (the handler runs inside the EAI Python
# bundle which has a narrower import scope than the standard search /
# REST processes).
_AI_DELAY_COMPONENTS = ("dsm", "dhm")

# Legacy flags the AI Feed Lifecycle Advisor takes authority over.
_LEGACY_FLAGS_AUTO_DISABLED = ("adaptive_delay", "variable_delay_auto_review")


def _normalise_components_csv(raw):
    """Return the lowercase, stripped, non-empty set of components in a
    CSV string. Empty / None → empty set.
    """
    if not raw:
        return set()
    return {c.strip().lower() for c in str(raw).split(",") if c.strip()}


def _payload_triggers_mutex(payload):
    """Return True if this incoming payload turns the AI Feed Lifecycle
    Advisor on for DSM or DHM.

    The check is intentionally narrow:

      * Both ``ai_components_advisor_enabled`` and
        ``ai_components_advisor_list`` must be present in the incoming
        payload. If either is absent, this is not an "AI tenants modal"
        save — pass through.
      * ``ai_components_advisor_enabled`` must coerce to int 1.
      * The list (as CSV) must contain ``dsm`` or ``dhm``.

    A save that disables the AI advisor (``...enabled=0``) or that
    enables it with no DSM / DHM coverage does NOT trigger the mutex.
    """
    if "ai_components_advisor_enabled" not in payload:
        return False
    if "ai_components_advisor_list" not in payload:
        return False
    try:
        enabled = int(payload.get("ai_components_advisor_enabled", 0) or 0)
    except (TypeError, ValueError):
        return False
    if enabled != 1:
        return False
    covered = _normalise_components_csv(payload.get("ai_components_advisor_list"))
    return any(c in covered for c in _AI_DELAY_COMPONENTS)


def _fetch_prior_record(handler, tenant_id):
    """Best-effort fetch of the current persisted vtenant record so the
    hook can detect which legacy flags actually flipped (and avoid
    emitting redundant audit events when both were already 0).

    Returns a dict of ``content`` values, or an empty dict on any
    error — the mutex still applies even if we can't determine the
    prior state.
    """
    try:
        entities = list(handler.get(tenant_id))
        if entities:
            content = entities[0].content
            # `content` is a dict-like object — copy out the legacy flags
            # we care about plus the AI flags for context in the audit.
            return {
                "adaptive_delay": content.get("adaptive_delay"),
                "variable_delay_auto_review": content.get("variable_delay_auto_review"),
                "ai_components_advisor_enabled": content.get(
                    "ai_components_advisor_enabled"
                ),
                "ai_components_advisor_list": content.get(
                    "ai_components_advisor_list"
                ),
            }
    except Exception as e:
        logging.warning(
            f'trackme_rh_vtenants_handler: failed to fetch prior record for '
            f'tenant_id="{tenant_id}" while computing mutex audit context, '
            f'exception="{str(e)}". Mutex will still apply.'
        )
    return {}


def _emit_audit(session_key, splunkd_uri, tenant_id, field, prior_value, new_value, ai_list):
    """Emit an ``audit_events_v2`` entry recording one legacy-flag flip
    triggered by the AI Feed Lifecycle mutex.

    Best-effort: a misconfigured audit index must not break the
    underlying tenant save. ``trackme_libs`` is imported lazily so the
    handler can fail to import the lib (e.g. EAI bundle skew) without
    breaking the primary mutex behaviour.
    """
    try:
        from trackme_libs import trackme_audit_event  # local import — see docstring

        trackme_audit_event(
            session_key,
            splunkd_uri,
            tenant_id,
            "trackme_rh_vtenants_handler",
            "updated",
            "ai_feed_lifecycle_mutex_auto_disable",
            field,
            "vtenant_account",
            json.dumps(
                {
                    "prior_value": prior_value,
                    "new_value": new_value,
                    "ai_components_advisor_list": ai_list,
                }
            ),
            "success",
            (
                f"Legacy ``{field}`` flag auto-disabled because the AI Feed "
                f"Lifecycle Advisor was enabled for DSM / DHM on this tenant. "
                f"Re-enable manually after disabling the advisor or removing "
                f"DSM / DHM from ai_components_advisor_list."
            ),
        )
    except Exception as e:
        # Defence-in-depth: audit failure must NOT propagate. The
        # primary mutex behaviour (payload mutation + persistence)
        # remains correct even if the audit index is misconfigured.
        logging.warning(
            f'trackme_rh_vtenants_handler: failed to emit audit event for '
            f'mutex flip on tenant_id="{tenant_id}", field="{field}", '
            f'exception="{str(e)}"'
        )


def _apply_mutex(handler_self, action_label):
    """Mutate ``handler_self.payload`` in place to enforce the mutex.

    Computes the prior record for audit context, forces the legacy
    flags to ``"0"`` in the outgoing payload, and emits one audit event
    per actual flip (a flag that was already ``0`` does not emit, to
    avoid log noise on repeat saves).

    Returns a list of ``{field, prior_value, new_value}`` dicts
    describing what was flipped — the caller can stash this in
    ``confInfo`` for the frontend to consume, though UCC's confInfo
    surface does not currently propagate custom metadata to JSON
    responses (UI consumers detect the flip by re-reading the tenant
    record after save).
    """
    if not _payload_triggers_mutex(handler_self.payload):
        return []

    tenant_id = handler_self.callerArgs.id
    session_key = handler_self.getSessionKey()
    splunkd_uri = handler_self.handler._splunkd_uri
    ai_list = handler_self.payload.get("ai_components_advisor_list", "")
    prior = _fetch_prior_record(handler_self.handler, tenant_id)

    actions = []
    for flag in _LEGACY_FLAGS_AUTO_DISABLED:
        prior_value = prior.get(flag)
        # Normalise the prior value to a string for comparison — UCC
        # stores everything as strings in the .conf backend.
        try:
            prior_int = int(prior_value) if prior_value is not None else 1  # default = on
        except (TypeError, ValueError):
            prior_int = 1
        # Force the flag to "0" in the outgoing payload regardless of
        # what the admin submitted. The AI advisor is the authority.
        handler_self.payload[flag] = "0"
        if prior_int != 0:
            actions.append(
                {"field": flag, "prior_value": str(prior_value), "new_value": "0"}
            )
            _emit_audit(
                session_key, splunkd_uri, tenant_id, flag, prior_value, "0", ai_list
            )

    if actions:
        logging.info(
            f'trackme_rh_vtenants_handler: AI Feed Lifecycle mutex '
            f'triggered on {action_label} for tenant_id="{tenant_id}". '
            f'Flipped legacy flags: '
            f'{", ".join(a["field"] for a in actions)} '
            f'(ai_components_advisor_list="{ai_list}")'
        )

    return actions


def _reconcile_advisor_scheduling(handler_self, action_label):
    """Best-effort: trigger immediate reconciliation of the per-tenant
    advisor saved-search schedules right after the parent ``handleEdit``
    persists the new ``vtenant_account``.

    Without this hook, the saved-searches stay at the seed-time default
    of ``is_scheduled=0`` until the per-tenant health tracker's next
    cycle picks up the new flag (up to ~5 min lag). The tracker's
    triple gate (``enable_ai_assistant AND providers_configured AND
    per_tenant_flag``) is mirrored verbatim by the reconciler so the two
    paths converge on the same outcome regardless of which runs first.

    Best-effort by design: any failure in the reconciler logs a warning
    and returns. The save itself has already persisted, and the tracker
    will reconcile on its next cycle as the durable safety net.
    """
    tenant_id = handler_self.callerArgs.id
    session_key = handler_self.getSessionKey()
    try:
        splunkd_uri = handler_self.handler._splunkd_uri
    except Exception:
        # Defensive: if the URI is unavailable for any reason, skip the
        # immediate reconcile (the tracker still handles it).
        logging.warning(
            f'trackme_rh_vtenants_handler: could not resolve splunkd_uri '
            f'for tenant_id="{tenant_id}" on {action_label}; skipping '
            f'immediate advisor reconcile (tracker will handle).'
        )
        return

    try:
        from trackme_libs_advisor_scheduling import (
            reconcile_advisor_scheduling_on_save,
        )
        import splunklib.client as client  # noqa: WPS433 — lazy import

        # Build a splunklib service the reconciler can use for the
        # global enable_ai_assistant lookup and the AI providers list.
        # ``ai_providers`` listing requires app-context "trackme" so the
        # ``trackme_ai_provider.conf`` stanzas are visible.
        from urllib.parse import urlparse

        parsed = urlparse(splunkd_uri)
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=parsed.port,
            token=session_key,
            timeout=120,
        )

        # IMPORTANT: the reconciler's triple gate reads fields from TWO
        # different surfaces, and the post-save view must merge them.
        #
        # 1. The ``ai_*`` flags (``ai_mladvisor_enabled``,
        #    ``ai_components_advisor_enabled``, ``ai_components_advisor_list``,
        #    etc.) ARE declared in ``trackme_vtenants.conf.spec`` and the
        #    UCC handler's parent ``handleEdit`` just persisted them.
        # 2. The ``tenant_<comp>_enabled`` flags (``tenant_dsm_enabled``,
        #    ``tenant_dhm_enabled``, etc.) are NOT in the conf spec.
        #    They live ONLY in the ``kv_trackme_virtual_tenants`` KV
        #    collection — written by the tenant-creation flow in
        #    ``trackme_rest_handler_vtenants_admin.py``, never mirrored
        #    to the .conf surface.
        #
        # An earlier draft fetched ``handler_self.handler.get(tenant_id)``
        # hoping to get the full record — but the UCC conf entity is a
        # strict-allowlist projection, so the component flags stayed
        # missing. That left the asymmetric bug in place: DISABLE works
        # (the advisor flag itself short-circuits the AND at 0, missing
        # component flags don't matter) while ENABLE silently no-ops
        # (advisor flag is 1, AND continues to the missing component
        # flag, evaluates False, silent "unchanged" branch).
        #
        # The fix is to read the same view the UI uses — the trackmeload
        # REST endpoint at ``/services/trackme/v2/vtenants/trackmeload``,
        # which internally calls ``trackmeload()`` for the KV-backed
        # ``tenant_<comp>_enabled`` flags and ``trackme_vtenant_account()``
        # for the .conf-backed ``ai_*`` flags, then merges the result.
        # Single canonical source; same merge logic that drives the UI
        # render of the Manage AI Agents automation page; keeps the
        # save-hook view consistent with what the operator sees and what
        # the tracker would compute on its next cycle.

        try:
            import requests as _requests  # noqa: WPS433 — lazy import
        except ImportError as imp_exc:
            logging.warning(
                f'trackme_rh_vtenants_handler: ``requests`` unavailable, '
                f'skipping immediate advisor reconcile for '
                f'tenant_id="{tenant_id}" on {action_label} (tracker '
                f'will reconcile on next cycle), exception="{imp_exc}"'
            )
            return

        # Resolve splunkd_timeout the same way the existing tracker code
        # does (``trackme_libs.get_splunkd_timeout`` honours the
        # ``[trackme_general] splunkd_timeout`` setting and falls back
        # to a safe default). Lazy import to keep this hook's load
        # surface narrow on the EAI Python bundle.
        splunkd_timeout = 300
        try:
            from trackme_libs import get_splunkd_timeout, trackme_reqinfo_from_service

            splunkd_timeout = get_splunkd_timeout(
                trackme_conf=trackme_reqinfo_from_service(service)
            )
        except Exception:
            # Conservative default — better to time out a slow read
            # eventually than to block the save indefinitely.
            splunkd_timeout = 300

        trackmeload_url = f"{splunkd_uri.rstrip('/')}/services/trackme/v2/vtenants/trackmeload"
        try:
            response = _requests.post(
                trackmeload_url,
                headers={
                    "Authorization": f"Splunk {session_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({"mode": "full"}),
                verify=False,
                timeout=splunkd_timeout,
            )
            response.raise_for_status()
            trackmeload_data = response.json()
        except Exception as fetch_exc:
            logging.warning(
                f'trackme_rh_vtenants_handler: failed to fetch '
                f'trackmeload view for tenant_id="{tenant_id}" on '
                f'{action_label}, skipping immediate advisor reconcile '
                f'(tracker will handle on next cycle), '
                f'exception="{fetch_exc}"'
            )
            return

        # Locate THIS tenant in the trackmeload payload. The endpoint
        # returns ``tenants_json.tenants`` — a list of every tenant the
        # caller is RBAC-allowed to see. The save-hook caller is the
        # admin who just submitted the edit, so we're guaranteed to be
        # in the visibility set.
        target_tenant = None
        for entry in trackmeload_data.get("tenants_json", {}).get("tenants", []):
            if entry.get("tenant_id") == tenant_id:
                target_tenant = entry
                break

        if not target_tenant:
            logging.warning(
                f'trackme_rh_vtenants_handler: trackmeload payload did '
                f'not contain tenant_id="{tenant_id}" on {action_label}, '
                f'skipping immediate advisor reconcile.'
            )
            return

        # Build the merged dict the reconciler expects: top-level
        # ``tenant_<comp>_enabled`` flags (from the trackmeload view of
        # the KV record) overlaid with the nested ``vtenant_account``
        # dict (the .conf-backed ai_* flags). Same shape the tracker's
        # inline scheduling block consumes — the two paths now read
        # from the same canonical source.
        merged_vtenant_account = {
            **(target_tenant.get("vtenant_account") or {}),
            "tenant_dsm_enabled": target_tenant.get("tenant_dsm_enabled"),
            "tenant_dhm_enabled": target_tenant.get("tenant_dhm_enabled"),
            "tenant_mhm_enabled": target_tenant.get("tenant_mhm_enabled"),
            "tenant_flx_enabled": target_tenant.get("tenant_flx_enabled"),
            "tenant_fqm_enabled": target_tenant.get("tenant_fqm_enabled"),
            "tenant_wlk_enabled": target_tenant.get("tenant_wlk_enabled"),
        }

        # Diagnostic INFO line so operators can confirm the merge
        # captured the flags they expect to see flipped. Bounded log
        # surface — only the five flags the reconciler actually
        # consumes.
        logging.info(
            f'trackme_rh_vtenants_handler: tenant_id="{tenant_id}" '
            f'{action_label} merged vtenant view for reconcile: '
            f'ai_mladvisor_enabled="{merged_vtenant_account.get("ai_mladvisor_enabled")}", '
            f'ai_components_advisor_enabled="{merged_vtenant_account.get("ai_components_advisor_enabled")}", '
            f'ai_components_advisor_list="{merged_vtenant_account.get("ai_components_advisor_list")}", '
            f'tenant_dsm_enabled="{merged_vtenant_account.get("tenant_dsm_enabled")}", '
            f'tenant_dhm_enabled="{merged_vtenant_account.get("tenant_dhm_enabled")}", '
            f'tenant_flx_enabled="{merged_vtenant_account.get("tenant_flx_enabled")}", '
            f'tenant_fqm_enabled="{merged_vtenant_account.get("tenant_fqm_enabled")}", '
            f'tenant_wlk_enabled="{merged_vtenant_account.get("tenant_wlk_enabled")}", '
            f'tenant_mhm_enabled="{merged_vtenant_account.get("tenant_mhm_enabled")}"'
        )

        summary = reconcile_advisor_scheduling_on_save(
            session_key=session_key,
            splunkd_uri=splunkd_uri,
            service=service,
            tenant_id=tenant_id,
            vtenant_account=merged_vtenant_account,
            log_context=f"vtenants_{action_label}",
        )
        # Only log a single summary line at INFO when something actually
        # moved — repeated saves that change nothing should stay quiet.
        if summary["enabled"] or summary["disabled"]:
            logging.info(
                f'trackme_rh_vtenants_handler: tenant_id="{tenant_id}" '
                f'{action_label} reconciled advisor scheduling immediately. '
                f'enabled={summary["enabled"]}, disabled={summary["disabled"]}'
            )
    except Exception as exc:
        # Best-effort: never break the save on a reconcile failure. The
        # per-tenant tracker will pick up the change on its next cycle.
        logging.warning(
            f'trackme_rh_vtenants_handler: immediate advisor schedule '
            f'reconcile failed for tenant_id="{tenant_id}" on {action_label} '
            f'(tracker will reconcile on next cycle), '
            f'exception="{exc}"'
        )


class CustomRestHandlerVtenants(AdminExternalHandler):
    """UCC custom handler for the ``trackme_vtenants`` endpoint.

    Two side-effects layered on top of the upstream UCC save:

    1. ``_apply_mutex`` — AI Feed Lifecycle ↔ legacy Adaptive Delay
       mutex (forces ``adaptive_delay = 0`` and
       ``variable_delay_auto_review = 0`` when the AI advisor covers
       DSM / DHM on the tenant).
    2. ``_reconcile_advisor_scheduling`` — immediate per-tenant
       reconciliation of advisor saved-search ``is_scheduled`` so the
       admin doesn't have to wait up to 5 min for the health tracker
       to pick up an advisor toggle. Best-effort; tracker remains the
       durable safety net.
    """

    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleCreate(self, confInfo):
        _apply_mutex(self, action_label="create")
        AdminExternalHandler.handleCreate(self, confInfo)
        _reconcile_advisor_scheduling(self, action_label="create")

    def handleEdit(self, confInfo):
        _apply_mutex(self, action_label="edit")
        AdminExternalHandler.handleEdit(self, confInfo)
        _reconcile_advisor_scheduling(self, action_label="edit")

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleRemove(self, confInfo):
        AdminExternalHandler.handleRemove(self, confInfo)

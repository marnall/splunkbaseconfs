# coding=utf-8
"""
Describe payload for the AI Assistant when mounted inside the FQM tracker
creation wizard.

This is a Phase-5 surface specifically for the wizard-time advisor invocation
flow (``mode=dictionary_generate``). It deliberately differs from the
``tenant_home`` describe in two key ways:

1. **No entity health, no alerting summary, no Guardian alerts.** The user
   has NOT created the tracker yet — there is no entity to inspect, no
   alerts to triage, no health to summarise. Including those payloads
   would distract the LLM from the only goal that matters at this surface:
   recognising that the user wants to generate a starter dictionary and
   proposing a clean ``advisor_invocation`` contract for it.

2. **Tightly scoped knowledge reference.** Only the FQM advisor's catalog
   entry is shipped (with ``dictionary_generate`` mode highlighted), plus
   the action-contract schema. Other advisor entries (ML, FLX Threshold,
   Feed Lifecycle, Component Health) are intentionally omitted — none of
   them apply at wizard time, and including them would tempt the LLM into
   proposing the wrong advisor.

Recent FQM advisor runs (specifically ``mode=dictionary_generate`` runs in
the last hour) are included so the LLM can see whether the user already
launched one in this same wizard session and avoid redundant proposals.

The system prompt that consumes this payload lives in
``trackme_libs_ai.py::FQM_DICTIONARY_WIZARD_SYSTEM_PROMPT_TEMPLATE``.
"""

import logging
from trackme_libs_logging import get_effective_logger
import time

from trackme_libs_describe_ai_advisors import (
    _action_contract_schema,
    _full_advisor_catalog,
    load_recent_ai_advisor_runs,
)


def _wizard_assistant_playbook():
    """Wizard-specific instruction block for the assistant.

    Distinct from the standard ``ai_advisors.assistant_playbook`` — that
    one covers the full advisor catalog (which advisor for which symptom,
    cross-advisor decision rules, never-fabricate-IDs rule for entity
    flows). At wizard time the choice is made for us: the user is in the
    FQM wizard and the only meaningful proposal is
    ``fqm_advisor / dictionary_generate``. The playbook below is the
    wizard-specific decision tree.
    """
    return {
        "context": (
            "You are the AI Assistant mounted inside the FQM (Field Quality "
            "Monitoring) tracker creation wizard. The user has not yet "
            "created the tracker — there is NO entity in the KV store, NO "
            "live monitoring data, NO existing dictionary. The user is "
            "configuring a new tracker and may have already sampled fields "
            "from their data source via the wizard's 'Generate fields "
            "summary' step."
        ),
        "what_to_propose": [
            (
                "When the user asks to GENERATE / CREATE / AUTO-BUILD / "
                "PROPOSE / DRAFT a data dictionary for the tracker they're "
                "configuring, propose the FQM Advisor in "
                "``mode=dictionary_generate``. The wizard frontend will "
                "inject the sampled-fields payload into the launch body — "
                "you do NOT need to ask the user for the field samples, "
                "they are already attached at launch time."
            ),
            (
                "Emit the action-contract as a fenced ``` ```json `` block at "
                "the END of your prose response. Minimal shape: "
                "``{\"advisor_invocation\": {\"advisor\": \"fqm_advisor\", "
                "\"mode\": \"dictionary_generate\", "
                "\"suggested_reason\": \"<why>\", "
                "\"consent_required\": true}}``. The frontend hard-codes "
                "``component`` and ``tenant_id`` at launch — do NOT add "
                "those fields, do NOT add ``object`` / ``object_id`` "
                "(no entity exists yet)."
            ),
        ],
        "what_NOT_to_propose": [
            (
                "DO NOT propose ``inspect`` or ``act`` modes — those operate "
                "on a stored entity, which doesn't exist yet during wizard "
                "creation. The advisor REST handler will reject the call "
                "with a 400 (`Missing required parameters: object / "
                "object_id`)."
            ),
            (
                "DO NOT propose other advisors (ML, Feed Lifecycle, FLX "
                "Threshold, Component Health) — the user is in the FQM "
                "wizard. None of the other advisors apply at this stage."
            ),
            (
                "DO NOT propose anything if the user hasn't generated the "
                "fieldsummary yet (i.e. no sampled fields on screen). "
                "Instead, walk them through the wizard steps: select "
                "tracker type → set search → generate fields summary → "
                "then come back and ask about the dictionary."
            ),
        ],
        "imperative_emission": (
            "If your prose suggests running the advisor — phrasings like "
            "\"I can generate the dictionary\", \"Would you like me to "
            "build a starter dictionary?\", \"Let me run the FQM Advisor "
            "in dictionary-generate mode\" — you MUST end your response "
            "with the fenced ``json`` block carrying the advisor_invocation "
            "contract. Without it, the chat UI has no button for the user "
            "to click and your proposal is non-actionable."
        ),
        "answer_general_questions_freely": (
            "You may also answer general questions about FQM (what it is, "
            "how dictionaries work, what allow_unknown / allow_empty_or_"
            "missing mean, how thresholds relate to dictionaries). Do NOT "
            "emit the action-contract for those — only when the user is "
            "asking you to actually run the advisor."
        ),
    }


def _wizard_knowledge_reference():
    """Tight FQM-only knowledge: catalog entry + action-contract schema.

    The full multi-advisor catalog (``build_ai_advisor_knowledge``) would
    bring in ML, Feed Lifecycle, FLX Threshold, and Component Health
    entries — none of them applicable at wizard time. We hand-pick just
    the FQM entry so the LLM has one option to choose from, not five.
    """
    catalog = _full_advisor_catalog()
    fqm_entry = catalog.get("fqm_advisor")
    return {
        "ai_advisors": {
            "purpose": (
                "AI agents that perform structured, tool-using analysis on "
                "TrackMe entities and configurations. At wizard time only "
                "the FQM advisor's ``dictionary_generate`` mode is "
                "applicable — the others operate on stored entities and "
                "are documented under tenant_home / entity contexts."
            ),
            "fqm_advisor": fqm_entry,
            "action_contract_schema": _action_contract_schema(),
            "assistant_playbook": _wizard_assistant_playbook(),
        },
    }


def build_fqm_dictionary_wizard_description(service, request_info, tenant_id):
    """Build the describe payload for the FQM wizard chat surface.

    Args:
        service: splunklib service handle (system context).
        request_info: REST handler request_info (carries session_key /
            server_rest_uri).
        tenant_id: the tenant the wizard is creating a tracker for. Used
            only to scope the recent-runs lookup; no per-tenant config is
            included in the payload.

    Returns:
        dict with a single top-level key ``fqm_dictionary_wizard_description``
        suitable for embedding in a system prompt template.
    """
    # Resolve the per-tenant summary index for the recent-runs lookup.
    # Best-effort — fall back to the global default on any failure.
    summary_index_for_runs = "trackme_summary"
    try:
        from trackme_libs import trackme_idx_for_tenant  # deferred import
        idx_settings = trackme_idx_for_tenant(
            request_info.session_key,
            request_info.server_rest_uri,
            tenant_id,
        )
        summary_index_for_runs = (idx_settings or {}).get(
            "trackme_summary_idx", "trackme_summary"
        )
    except Exception as e:
        get_effective_logger().warning(
            f'function=build_fqm_dictionary_wizard_description, '
            f'step="resolve_summary_index", tenant_id="{tenant_id}", '
            f'exception="{str(e)}"'
        )

    # Recent FQM advisor runs for this tenant. The LLM uses these to
    # avoid redundant proposals when the user has already launched the
    # advisor in the same wizard session — and to refer back to past
    # runs when the user asks "did I already try this?".
    ai_advisor_recent_runs = load_recent_ai_advisor_runs(
        service,
        summary_index=summary_index_for_runs,
        tenant_id_filter=tenant_id,
    )

    return {
        "fqm_dictionary_wizard_description": {
            "meta": {
                "api_version": "2.0",
                "generated_at": time.time(),
                "context_type": "fqm_dictionary_wizard",
                "tenant_id": tenant_id,
            },
            "wizard_state": {
                "summary": (
                    "User is currently in the FQM tracker creation wizard. "
                    "No tracker entity exists yet in the KV store. The "
                    "wizard frontend handles all per-tenant context (the "
                    "sampled fields, the chosen tracker type, the root "
                    "Splunk search, the breakby fields) and injects them "
                    "into the advisor launch body when the user clicks "
                    "the consent card."
                ),
                "available_advisor_invocations": [
                    "fqm_advisor / dictionary_generate (wizard-time only)"
                ],
                "unavailable_advisor_invocations": [
                    "fqm_advisor / inspect (no entity exists yet)",
                    "fqm_advisor / act (no entity exists yet)",
                    "ml_advisor / *  (FQM-specific surface)",
                    "feed_lifecycle_advisor / *  (FQM-specific surface)",
                    "flx_threshold_advisor / *  (FQM-specific surface)",
                    "component_health_advisor / *  (FQM-specific surface)",
                ],
            },
            "ai_advisor_recent_runs": ai_advisor_recent_runs,
            "knowledge_reference": _wizard_knowledge_reference(),
        }
    }

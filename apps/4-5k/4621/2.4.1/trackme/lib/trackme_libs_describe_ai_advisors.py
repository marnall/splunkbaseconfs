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
AI Advisor — describe-endpoint helpers (AI Assistant ↔ AI Advisor bridge, Phase 1).

Shared between the Virtual Tenants, Tenant Home, and per-entity ``describe/*``
endpoints that feed the AI Assistant's per-page system prompt. Two
contributions, mirroring the Configuration Guardian template (see
``trackme_libs_describe_guardian.py``):

* ``build_ai_advisor_knowledge(component_filter=None)`` — static, text-heavy
  block describing the 5 AI Advisors (ML Advisor + 4 component advisors), the
  modes (inspect / act), tenant-level gates, REST endpoints, the
  ``advisor_invocation`` action-contract schema, and an ``assistant_playbook``
  directing the AI Assistant's conversational style. Optionally filtered to
  the advisors relevant for a single component (DSM/DHM/MHM/FLX/FQM/WLK) so
  per-entity prompts stay tight.

* ``load_recent_ai_advisor_runs(service, summary_index, ...)`` — dynamic,
  RBAC-filtered list of recent advisor runs from
  ``index=<summary_index> sourcetype=trackme:ai_agent:*advisor*``. Same source
  the Audit page reads. Sorted newest-first.

Bridge plan: ``ai-context/integrations/ai-assistant-ai-advisor-bridge-implementation-plan.md``.

This module ONLY reads — nothing here invokes an Advisor or mutates KV. The
chat layer emits the action-contract; the frontend (Phase 2) renders a
consent card; only the user's explicit click invokes an Advisor. Phase 1 is
behaviour-additive only.
"""

import logging
from trackme_libs_logging import get_effective_logger
import sys

from trackme_libs import run_splunk_search


# -----------------------------------------------------------------------------
# Python-runtime compatibility for the Splunk Agent SDK
# -----------------------------------------------------------------------------


# Minimum Python version required by ``splunklib.ai`` and therefore by every
# AI Advisor / AI Concierge agent run. Splunk 10.2 is the first release that
# bundles a Python 3.13 runtime; earlier Splunk versions default to Python 3.9
# and the agent invocation path raises ``ImportError`` at SDK import time.
_MIN_PYTHON_FOR_AI_AGENTS = (3, 13)


def get_ai_runtime_compat():
    """Return a system_compatibility block for the AI Assistant.

    Shipped inside both ``knowledge_reference.ai_advisors`` (via
    :func:`build_ai_advisor_knowledge`) and
    ``knowledge_reference.concierge_advisor`` (via
    :func:`build_concierge_knowledge`), so every describe surface that
    feeds the AI Assistant has the data — including the four
    Concierge-only surfaces (License / Maintenance / Backup & Restore /
    REST API Reference) that do NOT ship the specialist advisor
    knowledge block.

    Consumed by two distinct rules:

    * ``ai_advisors.assistant_playbook.runtime_compatibility_rule`` —
      hard gate on the specialist ``advisor_invocation`` path.  When
      ``ai_agents_available`` is false, the LLM MUST NOT emit any
      ``advisor_invocation`` JSON block.
    * ``concierge_advisor.assistant_playbook.decision_tree[0]`` (step 1,
      specialist routing) — same gate, scoped to the decision-tree step
      that would route to a specialist.  The Concierge's OWN
      ``concierge_invocation`` chat-direct path is runtime-independent
      and is NOT gated by ``ai_agents_available`` (it resolves through
      ``executeConcierge`` → ``splunkdFetch`` to a named REST endpoint,
      with no ``splunklib.ai`` dependency).

    Computed from ``sys.version_info`` so the result reflects the
    interpreter executing this describe call — the same interpreter
    that would attempt to import ``splunklib.ai.*`` if the user
    clicked [Run now] on a specialist consent card.  No round-trip to
    the backend gate endpoint needed.

    Shape is stable; both consumer rules reference
    ``ai_agents_available`` and ``required_splunk_release`` by name.
    """
    major, minor, patch = sys.version_info[:3]
    return {
        "python_version": "{}.{}.{}".format(major, minor, patch),
        "min_version_for_ai_agents": "{}.{}".format(
            _MIN_PYTHON_FOR_AI_AGENTS[0], _MIN_PYTHON_FOR_AI_AGENTS[1]
        ),
        "ai_agents_available": (major, minor) >= _MIN_PYTHON_FOR_AI_AGENTS,
        "required_splunk_release": (
            "Splunk 10.2 or later (which bundles Python 3.13)"
        ),
    }


# -----------------------------------------------------------------------------
# Advisor catalog — keep in sync with ``ai-context/ai-advisors/tenant-config.md``
# -----------------------------------------------------------------------------

# Stable string IDs for each advisor — match the ``advisor`` field as
# extracted from the run-event sourcetype prefix
# (``trackme:ai_agent:<advisor>:<mode>``) so the LLM can cross-reference
# entries in ``ai_advisor_recent_runs`` with this catalog without
# normalisation. The sourcetypes are the audit-truth for "which advisor
# ran" and the REST endpoints under ``/services/trackme/v2/`` use the same
# naming convention (e.g. ``ai_feed_lifecycle_advisor``), so aligning the
# catalog keys with the sourcetype-extracted names keeps a single
# consistent vocabulary across audit / REST / contract enum / catalog.
ADVISOR_ML = "ml_advisor"
ADVISOR_FEED_LIFECYCLE = "feed_lifecycle_advisor"
ADVISOR_FLX_THRESHOLD = "flx_threshold_advisor"
ADVISOR_FQM = "fqm_advisor"
ADVISOR_COMPONENT_HEALTH = "component_health_advisor"

# Per-component relevance — used to filter the static reference for per-entity
# describe endpoints so the system prompt only carries advisors the user can
# actually invoke for the entity in scope. Source of truth is the tenant-config
# doc; if you add a new advisor or change the mapping, update both places.
ADVISORS_BY_COMPONENT = {
    "splk-dsm": [ADVISOR_ML, ADVISOR_FEED_LIFECYCLE],
    "splk-dhm": [ADVISOR_ML, ADVISOR_FEED_LIFECYCLE],
    "splk-mhm": [ADVISOR_COMPONENT_HEALTH],
    "splk-flx": [ADVISOR_ML, ADVISOR_FLX_THRESHOLD],
    "splk-fqm": [ADVISOR_FQM],
    "splk-wlk": [ADVISOR_COMPONENT_HEALTH],
}


# -----------------------------------------------------------------------------
# Static knowledge block
# -----------------------------------------------------------------------------


def _full_advisor_catalog():
    """Return the full per-advisor reference dict.

    Keep this aligned with:
      - ``ai-context/ai-advisors/tenant-config.md`` (configuration & gates)
      - ``ai-context/ml/outlier-detection.md`` (ML Advisor specifics)
      - the actual REST handler files under ``package/bin/trackme_rest_handler_ai_*_advisor.py``
    """
    return {
        ADVISOR_ML: {
            "purpose": (
                "Maintains accuracy of ML outlier detection models. Reviews "
                "models for false positives, behaviour-change drift, "
                "stale boundaries, and applies remediation: period exclusions, "
                "retrains, false-positive scoring, model-rule updates."
            ),
            "components_supported": ["splk-dsm", "splk-dhm", "splk-flx"],
            "scope": "entity",
            "actions_available": [
                "add_period_exclusion",
                "trigger_model_retrain",
                "set_false_positive",
                "update_model_rules",
                "disable_ml_model",
            ],
            "modes": {
                "inspect": "Read-only — reviews, diagnoses, reports recommendations. No writes.",
                "act": "Applies remediation actions per recommendation.",
            },
            "tenant_master_switch": "ai_mladvisor_enabled",
            "default_mode_field": "ai_mladvisor_mode",
            "decommission_guard": "ai_mladvisor_allow_model_disable",
            "rest_endpoints": {
                "launch": "POST /services/trackme/v2/ai_ml_advisor/ml_advisor",
                "status": "GET /services/trackme/v2/ai_ml_advisor/ml_advisor_status?job_id=<id>",
                "cancel": "DELETE /services/trackme/v2/ai_ml_advisor/ml_advisor_cancel?job_id=<id>",
            },
            "audit_sourcetype_pattern": "trackme:ai_agent:ml_advisor:<inspect|act>",
        },
        ADVISOR_FEED_LIFECYCLE: {
            "purpose": (
                "Reviews DSM / DHM feeds for lifecycle issues — prolonged "
                "inactivity, decommissioning candidates, stale entities. "
                "In act mode can adjust monitored_state, priority, or "
                "decommission per the unified components-advisor policy. "
                "In generate_model mode (DSM-only, Phase 3 of issue #1901) "
                "proposes a starter data-sampling custom-model regex from "
                "a sampled-events payload supplied by the Data Sampling "
                "Create Custom Rule wizard."
            ),
            "components_supported": ["splk-dsm", "splk-dhm"],
            "scope": "entity",
            "actions_available": [
                "update_entity_state_priority",
                "set_false_positive",
            ],
            "modes": {
                "inspect": "Reads, diagnoses, recommends. No writes.",
                "act": "Applies recommended state / priority changes.",
                "generate_model": (
                    "Wizard-time, DSM-only. Proposes a starter custom data-"
                    "sampling model regex (name + regex + type + sourcetype "
                    "scope + confidence) from a sampled-events payload "
                    "supplied by the Data Sampling Create Custom Rule "
                    "wizard. No entity in KV at this stage; no MCP tools "
                    "used. Only valid when the chat is mounted inside the "
                    "wizard with sampled events available — propose this "
                    "mode when the user says they want to create / generate "
                    "/ auto-build a custom data-sampling model for the "
                    "sourcetype they're currently configuring. Emit a "
                    "minimal action_contract (``advisor: 'feed_lifecycle_advisor', "
                    "mode: 'generate_model'``); the frontend injects the "
                    "wizard payload at launch — do NOT include sampled "
                    "values in the contract."
                ),
            },
            "tenant_master_switch": "ai_components_advisor_enabled",
            "tenant_eligibility_list": "ai_components_advisor_list",
            "default_mode_field": "ai_components_advisor_mode",
            "decommission_guard": "ai_components_advisor_allow_decommission",
            "rest_endpoints": {
                "launch": "POST /services/trackme/v2/ai_feed_lifecycle/lifecycle_advisor",
                "status": "GET /services/trackme/v2/ai_feed_lifecycle/lifecycle_advisor_status?job_id=<id>",
                "cancel": "DELETE /services/trackme/v2/ai_feed_lifecycle/lifecycle_advisor_cancel?job_id=<id>",
            },
            "audit_sourcetype_pattern": "trackme:ai_agent:feed_lifecycle_advisor:<inspect|act|generate_model>",
        },
        ADVISOR_FLX_THRESHOLD: {
            "purpose": (
                "Reviews FLX entity dynamic thresholds and metric-quality "
                "detection. Tunes static or variable threshold values, "
                "removes obsolete thresholds, recommends new ones based on "
                "observed metric distributions."
            ),
            "components_supported": ["splk-flx"],
            "scope": "entity",
            "actions_available": [
                "update_threshold",
                "create_threshold",
                "remove_threshold",
                "update_entity_state_priority",
            ],
            "modes": {
                "inspect": "Reads, diagnoses, recommends. No writes.",
                "act": "Applies threshold and entity-state updates.",
            },
            "tenant_master_switch": "ai_components_advisor_enabled",
            "tenant_eligibility_list": "ai_components_advisor_list",
            "default_mode_field": "ai_components_advisor_mode",
            "decommission_guard": "ai_components_advisor_allow_decommission",
            "rest_endpoints": {
                "launch": "POST /services/trackme/v2/ai_flx_threshold/threshold_advisor",
                "status": "GET /services/trackme/v2/ai_flx_threshold/threshold_advisor_status?job_id=<id>",
                "cancel": "DELETE /services/trackme/v2/ai_flx_threshold/threshold_advisor_cancel?job_id=<id>",
            },
            "audit_sourcetype_pattern": "trackme:ai_agent:flx_threshold_advisor:<inspect|act>",
        },
        ADVISOR_FQM: {
            "purpose": (
                "Reviews FQM (Fields Quality Monitoring) entities — field "
                "extraction quality, CIM compliance, missing or malformed "
                "fields. Recommends and applies threshold tuning and entity "
                "state corrections."
            ),
            "components_supported": ["splk-fqm"],
            "scope": "entity",
            "actions_available": [
                "update_threshold",
                "update_entity_state_priority",
            ],
            "modes": {
                "inspect": "Reads, diagnoses, recommends. No writes.",
                "act": "Applies threshold and entity-state updates.",
                "dictionary_generate": (
                    "Wizard-time. Proposes a starter data dictionary "
                    "(per-field regex / allow_unknown / allow_empty_or_missing) "
                    "from a sampled-fields payload supplied by the FQM tracker "
                    "creation wizard. No entity in KV at this stage; no MCP "
                    "tools used. Only valid when the chat is mounted inside a "
                    "wizard with sampled-field data available — propose this "
                    "mode when the user says they want to create / generate / "
                    "auto-build the data dictionary for the tracker they're "
                    "currently configuring. Emit a minimal action_contract "
                    "(``advisor: 'fqm_advisor', mode: 'dictionary_generate'``); "
                    "the frontend injects the wizard payload at launch — do NOT "
                    "include sampled values in the contract."
                ),
            },
            "tenant_master_switch": "ai_components_advisor_enabled",
            "tenant_eligibility_list": "ai_components_advisor_list",
            "default_mode_field": "ai_components_advisor_mode",
            "decommission_guard": "ai_components_advisor_allow_decommission",
            "rest_endpoints": {
                "launch": "POST /services/trackme/v2/ai_fqm_advisor/fqm_advisor",
                "status": "GET /services/trackme/v2/ai_fqm_advisor/fqm_advisor_status?job_id=<id>",
                "cancel": "DELETE /services/trackme/v2/ai_fqm_advisor/fqm_advisor_cancel?job_id=<id>",
            },
            "audit_sourcetype_pattern": "trackme:ai_agent:fqm_advisor:<inspect|act|dictionary_generate>",
        },
        ADVISOR_COMPONENT_HEALTH: {
            "purpose": (
                "Reviews WLK (workload / scheduled-search) and MHM "
                "(metric-host) entities for health issues — skip rate, "
                "execution errors, metric lag, missing hosts. Recommends "
                "and applies threshold tuning and entity-state changes."
            ),
            "components_supported": ["splk-wlk", "splk-mhm"],
            "scope": "entity",
            "actions_available": [
                "update_threshold",
                "update_entity_state_priority",
            ],
            "modes": {
                "inspect": "Reads, diagnoses, recommends. No writes.",
                "act": "Applies threshold and entity-state updates.",
            },
            "tenant_master_switch": "ai_components_advisor_enabled",
            "tenant_eligibility_list": "ai_components_advisor_list",
            "default_mode_field": "ai_components_advisor_mode",
            "decommission_guard": "ai_components_advisor_allow_decommission",
            "rest_endpoints": {
                "launch": "POST /services/trackme/v2/ai_component_health/health_advisor",
                "status": "GET /services/trackme/v2/ai_component_health/health_advisor_status?job_id=<id>",
                "cancel": "DELETE /services/trackme/v2/ai_component_health/health_advisor_cancel?job_id=<id>",
            },
            "audit_sourcetype_pattern": "trackme:ai_agent:component_health_advisor:<inspect|act>",
        },
    }


def _action_contract_schema():
    """JSON-shape description of the ``advisor_invocation`` action-contract.

    Embedded in the knowledge block so the AI Assistant knows the EXACT shape
    to emit when it wants to propose an Advisor invocation. Phase 2 of the
    bridge picks this up in the chat UI as a consent card; Phase 1 just logs
    it for observation.

    See the bridge implementation plan for per-field source rules — most
    importantly the rule that ``tenant_id`` and ``object_id`` MUST come from
    the user's chat-session context, not be fabricated by the LLM (same
    lesson as the period-exclusion epoch fiasco fixed in PR #1258).
    """
    return {
        "shape": {
            "advisor_invocation": {
                "advisor": "<one of ml_advisor | feed_lifecycle_advisor | flx_threshold_advisor | fqm_advisor | component_health_advisor>",
                "mode": "<inspect | act | dictionary_generate | generate_model> — wizard-time modes (dictionary_generate for FQM, generate_model for feed_lifecycle_advisor) are valid only when the chat is mounted inside the matching wizard",
                "tenant_id": "<tenant identifier — supplied verbatim from the user's session context>",
                "object_id": "<entity _key — supplied verbatim from the user's session context. NEVER fabricated.>",
                "component": "<the entity's object_category short form (dsm/dhm/mhm/flx/fqm/wlk) — only when component-advisor>",
                "suggested_reason": "<one or two sentences explaining why this invocation is appropriate now>",
                "expected_actions": ["<lifted from this advisor's actions_available; do not invent>"],
                "user_context": "<optional: free-form context from the chat to pass through as additional instructions>",
                "estimated_cost": {
                    "tokens": "<integer, approximate token budget>",
                    "duration_seconds_estimate": "<integer, approximate run duration>",
                },
                "consent_required": True,
            }
        },
        "field_rules": {
            "tenant_id": "MUST come from the user's chat-session context. Never construct or guess.",
            "object_id": "MUST come from the user's chat-session context. Never construct or guess. Even when ai_anonymize_entity_names=1, the frontend supplies the un-hashed object_id; the LLM never sees or constructs it.",
            "advisor": "Must match exactly one of the registered advisors. Server validates.",
            "mode": "Default to 'inspect' unless the user has explicitly authorised remediation. Server validates.",
            "expected_actions": "Lift values verbatim from advisors[<advisor>].actions_available — do not paraphrase or fabricate action names.",
            "consent_required": "Must be `true` in Phase 1 and Phase 2. The server REJECTS `false` until a future autonomous-mode opt-in is introduced.",
        },
        "emission_format": (
            "When you propose an invocation, emit ALSO a single fenced JSON code "
            "block at the END of your response containing only the "
            "`advisor_invocation` object. Native structured-output (when the "
            "provider supports it) is preferred; the fenced block is the "
            "universal fallback. Always emit prose first explaining the "
            "recommendation — the structured block accompanies your "
            "explanation, it does not replace it."
        ),
    }


def build_ai_advisor_knowledge(component_filter=None):
    """Return a structured knowledge block describing the AI Advisor family.

    Callers embed this dict under ``knowledge_reference.ai_advisors`` in their
    describe response. The AI Assistant uses it to:
      1. Answer general questions ("what does the FLX Threshold Advisor do?")
      2. Recognise when a user's intent matches an Advisor capability
      3. Construct a valid ``advisor_invocation`` action-contract to propose

    Args:
        component_filter: Optional ``object_category`` (e.g. ``"splk-flx"``) —
            when set, the returned ``advisors`` map is restricted to those
            registered as relevant for that component (see
            :data:`ADVISORS_BY_COMPONENT`). Used by per-entity describes so
            their system prompts stay tight.

    The shape is stable — additional advisors should be added as new entries
    in ``advisors`` with the same per-advisor schema. Do not rename existing
    keys without updating the AI Assistant system prompts that consume them.
    """
    advisors_full = _full_advisor_catalog()

    if component_filter and component_filter in ADVISORS_BY_COMPONENT:
        relevant = ADVISORS_BY_COMPONENT[component_filter]
        advisors = {key: advisors_full[key] for key in relevant if key in advisors_full}
    else:
        advisors = advisors_full

    return {
        # First key in the block — the assistant_playbook below depends on
        # this being available BEFORE the model decides whether to propose
        # an ``advisor_invocation`` contract.  See ``runtime_compatibility_rule``.
        "system_compatibility": get_ai_runtime_compat(),
        "overview": (
            "The TrackMe AI Advisor family is a set of agentic helpers that "
            "review entities and ML models, diagnose issues, and (in act mode) "
            "apply remediation actions on behalf of an analyst. Each advisor "
            "runs as an autonomous agent (Splunk Agent SDK) with a curated "
            "set of MCP read/write tools. Advisors are launched from dedicated "
            "panels in the TrackMe UI today; this knowledge block lets the AI "
            "Assistant propose them inline in chat (the action-contract bridge)."
        ),
        "modes": {
            "inspect": (
                "Read-only review. The advisor analyses the entity/model and "
                "produces a structured `MLAdvisorResult` (or equivalent) with "
                "recommendations and reasoning. No writes occur. Safe default."
            ),
            "act": (
                "Apply remediation. The advisor executes write actions per its "
                "recommendations. Always interactive (TRACKME_AI_AUTOMATED=0) "
                "when launched from the AI Assistant — analyst oversight stays "
                "in place via the existing decommission guard."
            ),
        },
        "tenant_configuration": {
            "ml_advisor_master_switch": "ai_mladvisor_enabled (vtenant_account)",
            "components_advisor_master_switch": "ai_components_advisor_enabled (vtenant_account)",
            "components_advisor_eligibility_list": (
                "ai_components_advisor_list (vtenant_account) — csv of enabled "
                "components per tenant. Each component advisor checks both that "
                "its component is in this list AND that the component is "
                "enabled on the tenant before reviewing any entity."
            ),
            "automated_priority_filter": (
                "ai_automated_priority_filter (vtenant_account) — "
                "csv of priority levels eligible for ANY automated AI Advisor "
                "action (ML Advisor AND every Components Advisor batch). "
                "Default `critical,high`. Empty CSV = match-all. Interactive "
                "launches via the AI Assistant or REST endpoints ignore the filter."
            ),
            "automated_filter_expression": (
                "ai_automated_filter_expression (vtenant_account) — optional "
                "TrackMe filter DSL expression (same syntax as Virtual Groups / "
                "ML Outliers scope) layered on top of the priority filter. "
                "field=value with wildcards (*, ?), OR / implicit AND, parens, "
                "case-insensitive. Available fields: priority, tags, labels, "
                "object, component, plus any raw entity field (data_index / "
                "data_sourcetype resolve on DSM/DHM entities only — not "
                "surfaced in the UI quick-reference since this filter applies "
                "across every component). Empty = no expression. An "
                "unparseable expression "
                "is fail-closed: every entity is skipped with reason "
                "`filter_expression_invalid` and surfaced in the per-cycle "
                "summary log so the operator can fix the misconfiguration "
                "(LLM tokens are never burned against an invalid filter)."
            ),
            "system_master_switch": (
                "trackme_settings.conf [trackme_general] enable_ai_assistant — "
                "if `0`, every advisor REST endpoint returns 403 with a clear "
                "message. The AI Assistant should NOT propose an invocation in "
                "that state."
            ),
        },
        "advisors": advisors,
        "action_contract": _action_contract_schema(),
        "rest_audit_trail": {
            "summary_index": "trackme_summary (or whatever the tenant's `trackme_summary_idx` overrides)",
            "sourcetype_pattern": "trackme:ai_agent:<advisor>:<inspect|act>",
            "key_fields": [
                "_time", "advisor", "mode", "status", "duration_ms",
                "token_count", "tenant_id", "component", "object", "object_id",
                "user", "automated", "actions_taken_count",
                "recommendations_count", "entity_status", "error", "job_id",
            ],
            "spl_example": (
                "search index=trackme_summary sourcetype=\"trackme:ai_agent:*advisor*\" "
                "tenant_id=<tenant> object_id=<entity_key> | sort -_time | head 5"
            ),
        },
        "assistant_playbook": {
            # First rule the model evaluates — comes BEFORE ``role`` and
            # ``imperative_routing_rule`` because if the runtime can't run
            # an agent, ALL the downstream "route → advisor_invocation"
            # rules are inapplicable.
            #
            # IMPORTANT scope distinction: this rule applies ONLY to the
            # specialist-advisor ``advisor_invocation`` path.  The
            # Concierge generalist uses a separate ``concierge_invocation``
            # JSON block which the AI Assistant frontend resolves via the
            # **chat-direct REST path** (``executeConcierge`` →
            # ``splunkdFetch`` to the named ``endpoint_path``).  That path
            # does NOT touch ``splunklib.ai`` and works on every
            # supported Splunk Python runtime — so the Concierge
            # assistant_playbook deliberately does NOT carry a
            # ``concierge_invocation`` blocking rule.  The Concierge
            # playbook DOES self-gate its decision-tree step 1
            # (specialist routing → ``advisor_invocation``) on the same
            # ``system_compatibility.ai_agents_available`` flag — see
            # ``trackme_libs_describe_concierge`` for that mirror.
            "runtime_compatibility_rule": (
                "BEFORE proposing any ``advisor_invocation`` contract "
                "(specialist advisors: ML / Feed Lifecycle / FLX "
                "Threshold / FQM / Component Health), check "
                "``system_compatibility.ai_agents_available`` in this "
                "knowledge block.  If that flag is **false**, the Splunk "
                "Python runtime on this deployment is older than "
                "``system_compatibility.min_version_for_ai_agents`` and "
                "the Splunk Agent SDK is unavailable — the specialist "
                "agent can NOT be launched even if the user explicitly "
                "asks for it.  In that case you MUST: "
                "(a) NOT emit any ``advisor_invocation`` JSON block — "
                "surfacing a consent card the backend will reject is "
                "worse than not offering one. "
                "(b) Provide your best investigation guidance, threshold "
                "recommendations, root-cause hypotheses, and SPL "
                "snippets directly from the chat context — you remain "
                "useful for diagnosis and recommendations, you just "
                "can't run a specialist agent on this runtime. "
                "(c) If a Concierge-style ``concierge_invocation`` is "
                "appropriate for the user's intent (priority change, "
                "ack, tag edit, threshold update via a direct REST "
                "endpoint), emit that contract normally — chat-direct "
                "Concierge is unaffected by the runtime gate. "
                "(d) Once per conversation (NOT once per turn), tell "
                "the user explicitly that the specialist AI Advisors "
                "require ``system_compatibility.required_splunk_release`` "
                "and that until the deployment is upgraded you can "
                "investigate, recommend, AND propose direct-REST "
                "Concierge actions — but not run a specialist "
                "investigation agent. "
                "When ``ai_agents_available`` is **true**, ignore this "
                "rule and follow the normal routing / emission rules below."
            ),
            "role": (
                "You are an active guide, not a passive reporter. When a user "
                "describes a symptom that one of the advisors can resolve, "
                "your job is to: (1) state what's wrong, (2) explain which "
                "advisor handles this and what it can do, (3) emit an "
                "`advisor_invocation` action-contract with `mode=inspect` by "
                "default so the user can review before committing. The user "
                "always retains explicit consent — Phase 2 will render your "
                "contract as a consent card with `[Run now]` / `[Inspect-only "
                "first]` / `[Cancel]` buttons; today the contract is logged "
                "but not yet rendered."
            ),
            "when_to_propose_an_invocation": {
                # Top-level rule that overrides default Q&A behaviour on
                # advisor-eligible entity surfaces. Production observation
                # (2026-05): smaller models (Haiku, Gemini-Pro) treat
                # open-ended health questions like "why is this red?" as
                # general Q&A and answer in prose with SPL templates,
                # never proposing the relevant specialist advisor — even
                # though that's exactly the intent class the advisor was
                # built for. This rule makes the routing explicit and
                # mandatory: on DSM/DHM/MHM/WLK/FLX/FQM entities, any
                # question about entity health, root cause, or
                # configuration tuning IS an advisor opportunity. The
                # advisor runs investigation queries autonomously and
                # proposes specific remediations — strictly more
                # capable than a prose answer with SPL templates.
                "imperative_routing_rule": (
                    "ROUTE, DO NOT ANSWER. On entity surfaces the "
                    "following user-intent classes MUST be routed to the "
                    "appropriate specialist advisor as an "
                    "``advisor_invocation`` (mode=inspect by default), "
                    "not answered in prose with SPL templates: "
                    "(a) any 'why is this entity in alert state / "
                    "red / orange', "
                    "(b) any 'what's wrong with this entity', "
                    "(c) any 'investigate the root cause', "
                    "(d) any 'how do I fix the delay / latency / "
                    "threshold', "
                    "(e) any 'tune the thresholds / variable delay / "
                    "lag policy', "
                    "(f) any 'this entity has been failing for X days', "
                    "(g) any 'review the configuration'. "
                    "The advisor is strictly more capable than a prose "
                    "answer because it runs investigation queries "
                    "autonomously and proposes specific remediations "
                    "the user can confirm with one click. Generating "
                    "investigation SPL templates and asking 'would you "
                    "like me to investigate?' is a regression — the "
                    "advisor IS the investigation."
                ),
                # Per-advisor trigger phrasings. The LLM uses these as
                # recognition anchors to map user intent → advisor. Lift
                # phrasings should match common production user
                # questions, not ideal-world phrasings. Each list is
                # the union of the top-level imperative_routing_rule
                # categories filtered to the advisor's surface — same
                # phrasing repeated across advisors is intentional (the
                # LLM may match either path; both lead to the right
                # advisor).
                "ml_advisor": [
                    "Why is this entity in red / orange state? (when outliers contribute to the score)",
                    "The ML model is producing false positives / has stale boundaries / hasn't retrained recently",
                    "Behaviour-change drift on this metric — the model isn't catching real anomalies anymore",
                    "Should we add a period exclusion for the maintenance window / outage / known incident?",
                    "Retrain the model / reset model state / tune outlier sensitivity",
                    "Inspect the ML config for this entity",
                ],
                "feed_lifecycle_advisor": [
                    "Why is this DSM/DHM entity in red / orange state?",
                    "What's wrong with this entity? Investigate the root cause",
                    "How do I fix the delay / latency / lag on this entity?",
                    "Tune the thresholds / variable delay / lag policy / monitoring time",
                    "This DSM/DHM entity has been failing / lagging for X days",
                    "Review the variable delay slot configuration / lifecycle config",
                    "Is the monitoring config for this entity correct?",
                    "Decommission candidate / stale entity check",
                ],
                "flx_threshold_advisor": [
                    "Why is this FLX entity in red / orange state?",
                    "Tune the dynamic / variable / static thresholds for this FLX entity",
                    "The metric distribution has shifted — recalibrate the thresholds",
                    "Remove obsolete thresholds / create new thresholds based on observed metrics",
                    "Review the metric coverage on this FLX entity",
                ],
                "fqm_advisor": [
                    "Why is this FQM entity in red / orange state?",
                    "Field extraction quality issues / CIM compliance gaps / missing or malformed fields",
                    "Tune the FQM thresholds / data dictionary / regex patterns",
                    "Review the field coverage on this FQM tracker",
                    "Generate a starter data dictionary from sampled fields (wizard mode only)",
                ],
                "component_health_advisor": [
                    "Why is this WLK/MHM entity in red / orange state?",
                    "What's wrong with this entity? Investigate the root cause",
                    "Tune the WLK skip-rate / error-count / metric-lag thresholds",
                    "This scheduled search is failing / metrics aren't arriving",
                    "Review the workload / metric host configuration",
                ],
            },
            "when_NOT_to_propose_an_invocation": [
                "User is just asking a general question about TrackMe concepts — answer with knowledge alone.",
                "User has not provided enough context to determine the correct advisor — ASK first.",
                "An advisor is gated off (`ai_components_advisor_enabled=0` or `ai_mladvisor_enabled=0`) for the tenant — explain instead and direct them to enable it.",
                "`enable_ai_assistant=0` — the system master switch is off; do not propose anything that calls advisor REST endpoints.",
                "Recent runs already show this advisor inspected/acted on this entity within the last hour — surface that result first instead of proposing another run.",
            ],
            "mode_selection_rules": [
                "Default to `inspect`. Always.",
                "Only emit `mode=act` when the user has EXPLICITLY asked for remediation (e.g. 'fix it', 'apply the recommendation', 'go ahead and update').",
                "Even when the user asks for `act`, your prose should call out the actions that will be taken (lifted from `expected_actions`) so they can read before clicking confirm.",
            ],
            "never_fabricate_invocation_fields": (
                "tenant_id and object_id MUST come from the user's chat-session "
                "context — they are supplied as part of the entity/page "
                "describe. Never invent or guess them. (Lesson from PR #1258: "
                "LLMs fluently fabricate IDs / epochs / hashes in structured "
                "output even when their prose is correct. The bridge "
                "deliberately does not give you the chance.)"
            ),
            "expected_actions_rules": (
                "Lift `expected_actions` verbatim from `advisors[<advisor>]"
                ".actions_available`. Do not paraphrase or invent action names; "
                "the consent card will compare them against the server-side "
                "registered tool list."
            ),
            "cost_disclosure": (
                "Always populate `estimated_cost` so the user sees what they "
                "are about to spend. Token estimate from the provider's "
                "configured `ai_max_tokens`; duration estimate from the "
                "advisor's historical p95 (visible in `ai_advisor_recent_runs`)."
            ),
            "use_recent_runs_first": (
                "Before proposing a new invocation, check `ai_advisor_recent_runs` "
                "for prior runs on the same entity / tenant. If a recent inspect "
                "run already exists with relevant findings, quote that result "
                "before proposing another run — saves cost and avoids loops. "
                "Recent run records include `actions_taken`, "
                "`recommendations_count`, and the agent's reasoning trace via "
                "`job_id` lookup."
            ),
            "response_pattern_when_advisor_can_help": [
                "1. Acknowledge what the user described in one sentence.",
                "2. Diagnose using the entity/page context already in the prompt — what is the entity's current state, what has been tried.",
                "3. Name the advisor that handles this and ONE-line summary of what it can do.",
                "4. End with a clear consent prompt — phrasings like 'Want me to run an inspect-only review?' / 'Shall I run it in act mode?'.",
                "5. **HARD RULE — your response MUST end with a fenced ```json block carrying the `advisor_invocation` contract.** Without the JSON block, the chat UI has nothing to render as a consent button and the user has no way to launch the advisor; your proposal becomes a non-actionable suggestion. This applies whenever your prose names an advisor and suggests running it, regardless of how casually the suggestion is phrased. The closing ``` is the LAST thing in your response — do NOT write any explanation, summary, capability note, or consent-card description AFTER the closing ```. The consent card UI surfaces all of that automatically from the structured contract; trailing prose after the JSON block has historically broken the parser and made the consent card disappear (the user sees the raw JSON in the chat bubble instead).",
            ],
            "emission_is_mandatory_examples": (
                "If you wrote any of these phrases, you MUST emit the JSON block: "
                "'I can run the ML Advisor', 'Would you like me to run an inspect-only review?', "
                "'Let me know if you want me to launch the FLX Threshold Advisor', "
                "'I'll inspect this with the FQM Advisor', "
                "'Shall I run the Component Health Advisor on this entity?'. "
                "There is no soft path — every advisor proposal must come with the contract."
            ),
            "response_pattern_when_advisor_cannot_help": (
                "If the symptom does not match any advisor's capability "
                "(e.g. tenant configuration is locked, advisor is disabled, "
                "the issue is system-level rather than entity-level), say so "
                "explicitly and direct the user to the right surface "
                "(Configuration Guardian for misconfiguration; entity "
                "thresholds page for manual tuning; admin REST API for "
                "operations). Don't propose an invocation just to seem helpful."
            ),
        },
    }


# -----------------------------------------------------------------------------
# Dynamic state — recent advisor runs, RBAC-filtered
# -----------------------------------------------------------------------------


# How many recent runs to surface by default. Kept moderate — the AI Assistant
# only needs enough context to answer "did we already inspect this?" and to
# anchor cost/duration estimates from p95 history.
_DEFAULT_RECENT_RUNS_LIMIT = 20

# Lookback for recent-run queries. Long enough that an Assistant pulled into a
# conversation about an old issue can still cite the prior advisor outcome.
_RECENT_RUNS_EARLIEST = "-30d"


def _build_recent_runs_search(
    summary_index,
    tenant_id_filter=None,
    visible_tenant_ids=None,
    object_id_filter=None,
    limit=_DEFAULT_RECENT_RUNS_LIMIT,
):
    """Compose the SPL the recent-runs loader runs against the summary index.

    Mirrors the base search the AI Audit page uses (see
    ``splunkui/packages/audit-ai-advisor/src/AuditAiAdvisor.tsx``) so the data
    shape stays consistent with the dashboard.
    """
    parts = [
        f'search index={summary_index} sourcetype="trackme:ai_agent:*advisor*"',
    ]

    if object_id_filter:
        # Strict equality on object_id when present — entity-scoped describes.
        # Don't OR with `object` since object names are not stable identifiers.
        parts.append(f'object_id="{object_id_filter}"')

    if tenant_id_filter:
        parts.append(f'tenant_id="{tenant_id_filter}"')
    elif visible_tenant_ids is not None:
        # ``is not None`` semantics — match the Guardian template
        # (``trackme_libs_describe_guardian.py``) and distinguish:
        #
        #   visible_tenant_ids=None      -> system-user bypass; no filter
        #   visible_tenant_ids=set()     -> user with access to ZERO tenants;
        #                                   filter must match nothing
        #   visible_tenant_ids={t1, t2}  -> filter to those tenants
        #
        # A truthiness check here would collapse the empty-set case into the
        # bypass case, leaking ALL tenants' advisor runs to a user with no
        # access. Bugbot caught this on PR #1264.
        ids = sorted({str(t) for t in visible_tenant_ids if t})
        if ids:
            quoted = " OR ".join(f'tenant_id="{tid}"' for tid in ids)
            parts.append(f"({quoted})")
        else:
            # User has zero visible tenants — emit a sentinel filter that
            # cannot match any real tenant_id rather than letting the search
            # return runs from every tenant. (load_recent_ai_advisor_runs
            # also short-circuits this case before dispatch, but we emit
            # the filter here as well for defence-in-depth.)
            parts.append('tenant_id="__no_visible_tenants__"')

    parts.extend([
        # Derive a stable `advisor` field from the sourcetype, same as the
        # AI Audit page's baseAdvisorSearch.
        '| rex field=sourcetype "trackme:ai_agent:(?<advisor_kind_extracted>[^:]+):[^:]+(?::[^:]+)?$"',
        '| eval advisor=coalesce(advisor_kind_extracted, "unknown")',
        '| sort - _time',
        f'| head {int(limit)}',
        # Restrict the columns to the AI Assistant-relevant subset. Keeps the
        # describe payload tight and avoids leaking long fields like the full
        # reasoning trace (lookup-able via job_id if needed).
        '| table _time, advisor, mode, status, tenant_id, component, '
        'object, object_id, user, automated, duration_ms, token_count, '
        'recommendations_count, actions_taken_count, entity_status, '
        'error, job_id',
    ])

    return "\n".join(parts)


def load_recent_ai_advisor_runs(
    service,
    summary_index,
    tenant_id_filter=None,
    visible_tenant_ids=None,
    object_id_filter=None,
    limit=_DEFAULT_RECENT_RUNS_LIMIT,
    earliest=_RECENT_RUNS_EARLIEST,
    latest="now",
):
    """Return the list of recent AI Advisor runs visible to the caller.

    Args:
        service: Splunk service connection (must be able to dispatch searches
            against the tenant's summary index).
        summary_index: Resolved summary index name (see
            ``trackme_idx_for_tenant``). Required — querying without an
            explicit ``index=`` clause would search the user's default
            indexes and silently return zero rows.
        tenant_id_filter: Optional single-tenant filter. Used by tenant_home
            and per-entity describes.
        visible_tenant_ids: Optional iterable of tenant IDs the caller is
            allowed to see (vtenants describe path). Mutually-exclusive with
            ``tenant_id_filter`` — if both are passed, ``tenant_id_filter``
            wins (tighter scope).
        object_id_filter: Optional entity-scoped filter (per-entity describes).
        limit: Maximum number of runs to return. Default 20.
        earliest / latest: Time range for the search. Default `-30d` to `now`.

    Returns:
        A dict ready to embed in the describe response:

            {
                "count": <int>,
                "runs": [<run dict>, ...],
                "stats": {
                    "by_advisor": {advisor: N, ...},
                    "by_status": {status: N, ...},
                    "by_mode": {mode: N, ...},
                },
            }

        Failure to dispatch the search returns an empty result — the
        describe endpoint must keep working even if the summary index is
        transiently unavailable or the user lacks search privileges.
    """
    empty_result = {
        "count": 0,
        "runs": [],
        "stats": {
            "by_advisor": {},
            "by_status": {},
            "by_mode": {},
        },
    }

    if not summary_index:
        return empty_result

    # RBAC short-circuit. ``visible_tenant_ids=None`` means system-user
    # bypass (intentional, no filter applied); ``set()`` means a real user
    # whose RBAC resolved to zero accessible tenants — the search would
    # produce no rows the caller is allowed to see, so skip the dispatch
    # entirely. The SPL builder has a defence-in-depth sentinel for the
    # same case, but short-circuiting here saves a search dispatch and
    # keeps the contract obvious to readers of this function. Same shape
    # the Guardian template uses (load_active_guardian_alerts).
    if (
        tenant_id_filter is None
        and visible_tenant_ids is not None
        and not visible_tenant_ids
    ):
        return empty_result

    spl = _build_recent_runs_search(
        summary_index,
        tenant_id_filter=tenant_id_filter,
        visible_tenant_ids=visible_tenant_ids,
        object_id_filter=object_id_filter,
        limit=limit,
    )

    # output_mode='json' and count=0 are project-wide requirements for every
    # run_splunk_search() call site (see issue #1108 / PR #1107) — the
    # static-analysis test enforces both keys are explicitly present even
    # though run_splunk_search itself force-overrides output_mode internally.
    # count=0 lifts the silent 100-row default; we already cap via | head <limit>.
    #
    # Do NOT pass exec_mode here. run_splunk_search() forwards search_params
    # to service.jobs.export(), and the splunklib export endpoint raises
    # TypeError("Cannot specify an exec_mode to export.") on any exec_mode
    # kwarg. The export stream is already the streaming-equivalent of a
    # oneshot for our purposes.
    search_params = {
        "earliest_time": earliest,
        "latest_time": latest,
        "output_mode": "json",
        "count": 0,
    }

    try:
        reader = run_splunk_search(
            service=service,
            search_query=spl,
            search_params=search_params,
            max_retries=2,
            sleep_time=2,
        )
    except Exception as e:
        get_effective_logger().warning(
            f'function=load_recent_ai_advisor_runs, step="dispatch", '
            f'tenant_id_filter="{tenant_id_filter}", '
            f'object_id_filter="{object_id_filter}", '
            f'exception="{str(e)}"'
        )
        return empty_result

    runs = []
    by_advisor = {}
    by_status = {}
    by_mode = {}

    try:
        for row in reader:
            if not isinstance(row, dict):
                continue
            run = {
                "_time": row.get("_time"),
                "advisor": row.get("advisor") or "unknown",
                "mode": row.get("mode") or "unknown",
                "status": row.get("status") or "unknown",
                "tenant_id": row.get("tenant_id") or "",
                "component": row.get("component") or "",
                "object": row.get("object") or "",
                "object_id": row.get("object_id") or "",
                "user": row.get("user") or "",
                "automated": row.get("automated") or "",
                "duration_ms": _coerce_int(row.get("duration_ms")),
                "token_count": _coerce_int(row.get("token_count")),
                "recommendations_count": _coerce_int(row.get("recommendations_count")),
                "actions_taken_count": _coerce_int(row.get("actions_taken_count")),
                "entity_status": row.get("entity_status") or "",
                "error": row.get("error") or "",
                "job_id": row.get("job_id") or "",
            }
            runs.append(run)

            adv = run["advisor"]
            by_advisor[adv] = by_advisor.get(adv, 0) + 1
            st = run["status"]
            by_status[st] = by_status.get(st, 0) + 1
            md = run["mode"]
            by_mode[md] = by_mode.get(md, 0) + 1
    except Exception as e:
        get_effective_logger().warning(
            f'function=load_recent_ai_advisor_runs, step="iterate", '
            f'exception="{str(e)}"'
        )
        return empty_result

    return {
        "count": len(runs),
        "runs": runs,
        "stats": {
            "by_advisor": by_advisor,
            "by_status": by_status,
            "by_mode": by_mode,
        },
    }


def _coerce_int(value):
    """Best-effort int coercion. Splunk returns strings for numeric fields."""
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

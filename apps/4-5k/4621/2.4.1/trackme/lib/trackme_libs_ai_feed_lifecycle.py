"""
TrackMe AI Agents — Feed Lifecycle Advisor

Provides the Feed Lifecycle Advisor agent and supporting orchestration:
- System prompt for DSM/DHM entity lifecycle analysis (inspect / act)
- Pydantic output schema (lifecycle): LifecycleAdvisorResult
- Pydantic output schema (generate_model wizard): DataSamplingModelGenerateResult
- Wizard payload validator: validate_data_sampling_generate_payload()
- Wizard system prompt: DATA_SAMPLING_MODEL_GENERATE_SYSTEM_PROMPT
  (Phase 3a of issue #1901 — runner integration lands in Phase 3b)
- start_feed_lifecycle_advisor_async()  — REST / interactive invocation
- start_feed_lifecycle_advisor_from_search_context() — streaming command / automated

NOTE: Splunk Agent SDK imports (splunklib.ai.*) are deferred to function scope.
The AI SDK requires Python 3.13+ and raises ImportError on 3.9.
"""

import asyncio
import json
import logging
import os
import time
import threading
import uuid

import splunklib.client as client

# Pydantic primitives come through the project-wide compat shim so the
# advisor modules stay importable on Python 3.9 (Splunk 9.x) — see
# ``trackme_libs_pydantic_compat`` for the full rationale.
from trackme_libs_pydantic_compat import BaseModel, Field

from trackme_libs_ai import get_ai_config, get_ai_api_key
import trackme_libs_ai_agents as _agents_module
from trackme_libs_ai_agents import (
    get_sdk_model,
    _create_agent_job,
    _update_agent_job,
    get_agent_job_status,
    _release_agent_slot,
    _is_tool_result_bug,
    _is_transient_provider_error,
    _transient_retry_backoff_sec,
    _is_structured_output_unsupported,
    _is_agent_structured_output_failure,
    _check_agent_model_capability,
    _build_initial_message_tool_strategy_hint,
    _active_agents_lock,
    _MAX_CONCURRENT_AGENTS_DEFAULT,
    _KV_COLLECTION_AGENT_JOBS,
    AgentAction,
    inline_schema_refs,
    force_tool_strategy_for_provider,
    make_prompt_cache_middleware,
    make_tool_trace_middleware,
    enrich_agent_event_for_audit,
    set_current_advisor_logger,
    format_agent_error_chain,
    build_automated_system_prompt,
)

# Named logger — shares the singleton configured by the parent
# REST handler's setup_logger() call (root logger redirect there means
# `logging.<level>(...)` here would bleed across handlers).
logger = logging.getLogger("trackme.rest.ai.feed_lifecycle")

# ---------------------------------------------------------------------------
# Pydantic Output Schema
# ---------------------------------------------------------------------------


class LifecycleRecommendation(BaseModel):
    """A recommendation for improving entity lifecycle configuration."""
    field: str = Field(
        description=(
            "Configuration field to change, e.g. 'data_max_delay_allowed', "
            "'data_max_lag_allowed', 'monitored_state', 'lock_threshold', "
            "'variable_delay_policy', 'priority', 'impact_score_weights'"
        )
    )
    current_value: str = Field(description="Current value of the field")
    recommended_value: str = Field(description="Recommended new value")
    rationale: str = Field(
        description="Clear explanation of why this change is recommended, citing observed data"
    )


class LifecycleAdvisorResult(BaseModel):
    """Structured output from the Feed Lifecycle Advisor agent."""
    entity_status: str = Field(
        description=(
            "Overall entity lifecycle assessment: "
            "'healthy' (configuration is appropriate for the entity's behaviour), "
            "'needs_tuning' (thresholds or settings need adjustment), "
            "'stale' (no recent data — entity may be inactive), "
            "'decommission_candidate' (entity should be disabled or removed)"
        )
    )
    summary: str = Field(description="2-3 sentence executive summary of the analysis")
    recommendations: list[LifecycleRecommendation] = Field(
        default_factory=list,
        description="Ordered list of recommendations (highest priority first)"
    )
    actions_taken: list[AgentAction] = Field(
        default_factory=list,
        description=(
            "Actions executed via write tools in act mode. Each entry records the "
            "tool name, status, description, and a short result summary. "
            "In act mode this array MUST NOT be empty — populate it from actual tool call results."
        ),
    )
    reasoning_trace: str = Field(
        default="",
        description="Step-by-step reasoning explanation for transparency"
    )

    @classmethod
    def model_json_schema(cls, **kwargs):
        """Return a flat ``$ref``/``$defs``-free JSON Schema — see MLAdvisorResult."""
        return inline_schema_refs(super().model_json_schema(**kwargs))


# ---------------------------------------------------------------------------
# Phase 3 of issue #1901 — wizard-time data sampling model generator
# ---------------------------------------------------------------------------
#
# The Feed Lifecycle Advisor has a third mode (``generate_model``) that runs
# WIZARD-TIME — no entity required, no KV access, no act-mode write tools.
# The agent receives a wizard payload (sourcetype + sampled events) and
# proposes a starter custom data-sampling model regex the operator can
# review and submit via the existing Data Sampling Create Custom Rule UI
# (or programmatically via ``add_data_sampling_model``).
#
# Mirrors the FQM Advisor's ``dictionary_generate`` mode (PR sequence on
# CIM-aware FQM dictionary generation). The wizard payload contract is
# enforced strictly so failure modes surface as 400 errors at launch,
# before paying any LLM tokens.
# ---------------------------------------------------------------------------


# Hard caps on the wizard payload — keep agent input bounded so a
# pathological request can't blow the context window or spike token cost.
_DATA_SAMPLING_WIZARD_PAYLOAD_MAX_SAMPLES = 100
_DATA_SAMPLING_WIZARD_PAYLOAD_MAX_BYTES = 256 * 1024  # 256 KiB

# Accepted values for the OUTPUT field ``proposed_model_type`` (set by the
# agent, not the wizard payload). The Pydantic schema documents these in
# the field description; the constant is referenced here for callers
# (Phase 3b agent runner, Phase 3c frontend) that want to validate the
# agent's structured output against the same allowed-set without
# duplicating the literal strings.
_DATA_SAMPLING_OUTPUT_MODEL_TYPES = frozenset({"inclusive", "exclusive"})


class DataSamplingModelGenerateResult(BaseModel):
    """Structured output from the Feed Lifecycle Advisor agent in
    ``generate_model`` mode.

    Wizard-time only — the agent has just consumed a sampled-events
    payload (no entity / no KV access) and proposes a single starter
    custom regex model. The output schema is intentionally narrow so the
    UI can populate the Create Custom Rule modal's fields directly.
    """

    summary: str = Field(
        description=(
            "2-3 sentence overview of what the agent observed in the "
            "sampled events (event shape, format family detected, any "
            "noteworthy patterns or outliers in the sample). Surfaced "
            "as the headline above the proposed model in the wizard."
        )
    )
    proposed_model_name: str = Field(
        description=(
            "Suggested human-readable model name, kebab-case or "
            "snake_case (e.g. ``netscreen_firewall``). The operator can "
            "edit it before submission. MUST be non-empty."
        )
    )
    proposed_model_regex: str = Field(
        description=(
            "The proposed regular expression to fit sampled events. "
            "Must be a syntactically valid Python ``re`` pattern. "
            "Escape special characters (`\\`, `(`, `)`, `[`, `]`, `.`) "
            "per Python re-module conventions. The wizard will surface "
            "this for operator review before any write."
        )
    )
    proposed_model_type: str = Field(
        description=(
            "Match semantics — one of: ``inclusive`` (events MUST match "
            "to count as well-formed for this sourcetype) or "
            "``exclusive`` (events MUST NOT match — match indicates "
            "malformed / unexpected content). Almost always "
            "``inclusive`` for format-recognition models."
        )
    )
    proposed_sourcetype_scope: str = Field(
        default="*",
        description=(
            "Comma-separated sourcetype scope (no wildcards / no spaces "
            "per the data_sampling endpoint contract). Defaults to "
            "``\"*\"`` (match all sourcetypes); the agent SHOULD narrow "
            "to the sampled sourcetype unless the pattern is genuinely "
            "format-agnostic."
        )
    )
    confidence: str = Field(
        description=(
            "One of: ``high`` (sample size is healthy, the pattern is "
            "clear and stable across the sample), ``medium`` (some "
            "variability — the regex covers the majority but the "
            "operator should review edge cases), ``low`` (sample size "
            "too small, multiple format families present, or "
            "regex required generous tolerances). Operators use this "
            "to triage which proposals to accept verbatim."
        )
    )
    confidence_notes: str = Field(
        default="",
        description=(
            "Optional caveats — sample-size limits, mixed formats "
            "detected, fields where the regex is permissive. Empty "
            "when the proposal is high-confidence and unambiguous."
        )
    )
    reasoning_trace: list[str] = Field(
        default_factory=list,
        description=(
            "Short step-by-step trace explaining how the agent reached "
            "the proposed regex from the sampled events. One step per "
            "observation is plenty — verbose traces just bloat the "
            "wizard's collapsible reasoning panel."
        )
    )

    @classmethod
    def model_json_schema(cls, **kwargs):
        """Return a flat ``$ref``/``$defs``-free JSON Schema.

        The Splunk Agent SDK's structured-output validator does not
        resolve ``$ref`` / ``$defs`` in the output schema — passing a
        Pydantic-default schema with refs causes validation to fail
        even when the agent output is correct. ``inline_schema_refs``
        flattens the schema so the SDK sees the literal field
        definitions inline. The same flat-schema contract applies to
        every advisor output schema in TrackMe (LifecycleAdvisorResult
        and the ML / FQM / FLX / Component Health advisor schemas all
        override ``model_json_schema`` the same way).
        """
        return inline_schema_refs(super().model_json_schema(**kwargs))


def validate_data_sampling_generate_payload(payload):
    """Validate the shape of the wizard payload for ``mode=generate_model``.

    Returns a string error message on failure, or ``None`` when the
    payload is acceptable. Validation is strict — the agent's prompt
    assumes a specific shape, and a malformed payload would either fail
    the Pydantic output schema later (after spending tokens) or, worse,
    produce a plausible-looking but wrong regex.

    Strict rules:
      - Must be a JSON object (dict).
      - ``tenant_id`` must be a non-empty string (used in the audit
        event).
      - ``sourcetype`` must be a non-empty string identifying the
        sourcetype the operator is generating a model for.
      - ``samples`` must be a list with at least one entry and at most
        ``_DATA_SAMPLING_WIZARD_PAYLOAD_MAX_SAMPLES`` entries.
      - Every sample entry must be a non-empty string (raw event).
      - Total serialised size must not exceed
        ``_DATA_SAMPLING_WIZARD_PAYLOAD_MAX_BYTES``.
    """
    if payload is None:
        return "wizard_payload is required when mode=generate_model."
    if not isinstance(payload, dict):
        return "wizard_payload must be a JSON object."

    tenant_id = payload.get("tenant_id")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        return "wizard_payload.tenant_id must be a non-empty string."

    sourcetype = payload.get("sourcetype")
    if not isinstance(sourcetype, str) or not sourcetype.strip():
        return "wizard_payload.sourcetype must be a non-empty string."

    samples = payload.get("samples")
    if not isinstance(samples, list) or not samples:
        return "wizard_payload.samples must be a non-empty list of raw event strings."
    # NOTE: the system prompt instructs the agent to tag
    # ``confidence="low"`` for samples with fewer than 3 events. This
    # validator intentionally does NOT enforce that minimum at the
    # 400-error layer — we fail-fast here only on STRUCTURAL issues
    # (missing keys, wrong types, oversized payload) and let the agent
    # degrade gracefully on sparse inputs. A caller that supplies a
    # single sample gets a valid payload back from the validator and
    # then a ``confidence: "low"`` response from the agent (or a
    # confidence-notes caveat). Phase 3b should preserve this soft/hard
    # split — moving the <3 check into the validator would break the
    # "the agent reasons about sparse data" contract documented in the
    # system prompt.
    if len(samples) > _DATA_SAMPLING_WIZARD_PAYLOAD_MAX_SAMPLES:
        return (
            f"wizard_payload.samples has {len(samples)} entries; max "
            f"{_DATA_SAMPLING_WIZARD_PAYLOAD_MAX_SAMPLES} allowed. "
            "Trim the sample set on the caller side."
        )
    for idx, sample in enumerate(samples):
        if not isinstance(sample, str) or not sample.strip():
            return (
                f"wizard_payload.samples[{idx}] must be a non-empty "
                "string (raw event text)."
            )

    # Total-size guard — JSON-encoded payload size including overhead.
    try:
        size_bytes = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError) as e:
        return f"wizard_payload is not JSON-serialisable: {e}"
    if size_bytes > _DATA_SAMPLING_WIZARD_PAYLOAD_MAX_BYTES:
        return (
            f"wizard_payload size {size_bytes} bytes exceeds the "
            f"{_DATA_SAMPLING_WIZARD_PAYLOAD_MAX_BYTES}-byte cap. "
            "Trim samples or sample fewer events."
        )

    return None


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

FEED_LIFECYCLE_ADVISOR_SYSTEM_PROMPT = """You are TrackMe's Feed Lifecycle Advisor — an AI agent that analyzes
DSM (Data Source Monitoring) and DHM (Data Host Monitoring) entity configurations and recommends
or applies corrective lifecycle changes to eliminate false alerts and reduce manual maintenance.

## YOUR MISSION

Review a DSM or DHM entity's ingestion history, current thresholds, and monitoring configuration.
Determine whether the configuration is appropriate for the entity's actual ingestion behaviour,
and recommend or apply changes that align monitoring settings with reality.

## CONTEXT

TrackMe monitors the health of data feeds. Each DSM entity represents a Splunk index+sourcetype
combination; each DHM entity represents a host. Key monitored metrics:

- **data_max_delay_allowed** (seconds): Maximum acceptable delay between the latest event time
  in the index and the entity's expected latest event. If events arrive later than this, the
  entity goes RED. Default: often 300s (5 min), which is far too tight for many feeds.
- **data_max_lag_allowed** (seconds): Maximum acceptable lag (time since Splunk last saw data).
  If Splunk hasn't received any data within this window, entity goes RED.
- **Threshold lock** (entity field `data_max_delay_allowed_locked`): the SINGLE user-facing control
  for whether TrackMe may auto-adjust this entity's delay/lag thresholds. LOCKED = the operator's
  thresholds are pinned: no adaptive delay, no lagging-class override, and a reconcile routine
  restores them if any background writer changes them. UNLOCKED = thresholds are auto-managed
  (adaptive delay / lagging classes may rewrite them). In the UI a locked entity shows a red 🔒
  badge next to its name. The legacy `allow_adaptive_delay` / `data_override_lagging_class` fields
  are DERIVED from the lock — do NOT reason about them as independent controls and do NOT recommend
  changing them directly. NOTE: the `update_entity_adaptive_delay` tool still takes
  `allow_adaptive_delay` "true"/"false" for back-compat — passing "false" LOCKS the entity, "true"
  UNLOCKS it. Always describe the action to the user as "locking / unlocking the thresholds" to
  match the UI. Pass the string, never the integer.
- **variable_delay_policy** (static/variable): When 'variable', time-slot-based thresholds apply
  (different thresholds for business hours vs. nights vs. weekends).
- **monitored_state** (enabled/disabled): Whether the entity is actively monitored.
- **priority** (critical/high/medium/low/pending): Alert severity weight.
- **impact_score_weights**: JSON dict adjusting the impact of delay/latency score components.

## REASONING FRAMEWORK

Follow this 5-step process for every analysis:

1. **UNDERSTAND THE ENTITY**: Call get_entity_lifecycle_context to get the full configuration
   snapshot — current thresholds, monitoring state, priority, tenant defaults, and entity type.

2. **ANALYSE INGESTION HISTORY**: Call get_entity_delay_latency_history to understand the last
   30 days of delay/latency patterns:
   - What is the typical (p50/p75/p95) delay for this entity?
   - Are there periodic spikes (weekends, nights, month-end)?
   - Has the feed been silent for days or weeks (stale/decommissioned)?
   - Does the feed have a regular cadence (once-per-day, hourly, real-time)?

3. **CHECK ALERT PATTERNS**: Call get_entity_alert_flip_history to understand false positive rate:
   - How many state transitions to RED in the last 30 days?
   - Are the RED states correlated with actual data issues, or are they threshold mismatches?
   - Has the entity been continuously RED despite data still arriving?

4. **COMPARE TO PEERS**: Optionally call get_entity_peer_comparison for same-sourcetype context:
   - What thresholds do similar entities use?
   - Is this entity an outlier in its threshold settings vs. its peers?

5. **DECIDE AND ACT**:
   - If thresholds are too tight for the observed pattern → recommend/set looser values
   - If entity shows 7+ days of no data → recommend disable or investigate
   - If once-per-day pattern detected → recommend data_max_delay_allowed ≥ 86400s
   - If automation keeps overwriting manual tuning → recommend LOCKING the entity's thresholds
     (via update_entity_adaptive_delay with allow_adaptive_delay="false", which now locks them)
   - If regular weekend/night spikes → recommend variable delay schedule
   - If priority mismatches entity criticality → recommend priority change
   - If configuration is appropriate → report 'healthy', no changes needed

## COMMON SCENARIO PATTERNS

### Scenario 1: Thresholds Too Tight (Most Common)
**Signals**: Entity regularly RED, but delay history shows typical delay of 1-8 hours.
Current data_max_delay_allowed is 300-900 seconds (5-15 min). High flip count.
**Action**: Set data_max_delay_allowed to ~110% of p95 observed delay. Add 20% buffer.
Example: p95 = 3600s → recommend data_max_delay_allowed = 4000s.

### Scenario 2: Once-Per-Day Batch Feed
**Signals**: Delay history shows gaps of 18-26 hours between data events. This is a scheduled
daily batch — the feed is not continuous. Common for: Azure Billing, O365, ServiceNow exports,
database exports, EDR daily rollups.
**Action**: Set data_max_delay_allowed ≥ 36h (129600s) to cover the full expected cycle plus buffer.
Optionally LOCK the thresholds (update_entity_adaptive_delay with allow_adaptive_delay="false")
to prevent further auto-adjustment.

### Scenario 3: Threshold Drift (settings overwritten by automation)
**Signals**: The entity is UNLOCKED (no red 🔒), delay history shows the threshold keeps changing,
user complaints about manually-set settings being overwritten by automation.
**Action**: LOCK the entity's thresholds (update_entity_adaptive_delay with
allow_adaptive_delay="false") to stabilize the configuration — this pins the values and stops
adaptive delay / lagging-class rewrites. If thresholds were already manually tuned and still
appropriate, preserve their values and just lock them.

### Scenario 4: Seasonal/Weekend Spikes
**Signals**: Delay history shows a clear pattern — low delay on weekdays, high delay on weekends
or nights. Entity is regularly RED on weekend mornings or Monday mornings.
**Action**: Enable variable delay policy. Set weekend/night slots with higher thresholds.
Use update_entity_variable_delay to create time-slot configuration.

### Scenario 5: Stale / Decommissioned Entity
**Signals**: No data in delay/latency history for 7+ consecutive days.
Entity has been RED continuously. No recent state changes back to GREEN.
**Action**: Recommend disabling monitoring (monitored_state=disabled). Add a comment explaining
the detection. Do NOT disable without noting why in your reasoning.

### Scenario 6: Priority Mismatch
**Signals**: Entity supplies critical data (payment processing, security logs, prod infra)
but is configured as low/medium priority. Or vice versa — entity is marked critical but
rarely has issues and monitors non-critical data.
**Action**: Recommend priority adjustment with justification based on entity name/sourcetype.

**CAUTION — priority changes can collide with lagging classes.** A priority field
update may move the entity INTO (or OUT OF) a lagging class match on the next
decision-maker cycle. If a class then matches, the class's delay/lag thresholds
override the entity-level values you may have just tuned in the same act run.
Before raising priority, call `get_lagging_classes` and check whether any
class with `level="priority"` targets the new priority value. If yes, decide
explicitly which threshold should win (see LAGGING CLASSES below) — either
loosen the class via `update_lagging_class` or flip
`set_entity_lagging_class_override` so the entity-level value takes precedence.

## LAGGING CLASSES — the threshold precedence chain you MUST understand

Lagging classes are tenant-level rule policies. Each class declares a match
pattern (level + match_mode + name) and a set of override thresholds (static
`value_delay` or a variable-delay schedule, optional `value_lag`). Every cycle
the per-tenant decision maker walks the classes against every entity and stamps
the result onto the entity record. The fields you see under
`lagging_class_assignment` on `get_entity_lifecycle_context`:

- `matched` (bool)         — does any class currently match this entity?
- `name` / `level` / `match_mode` / `delay_mode` — the matched class identity
- `key`                    — the matched class's `_key` (use it with
                             `update_lagging_class` / `delete_lagging_class`)
- `entity_override`        — the per-entity opt-out flag ("true"/"false")

### Precedence rule (single source of truth)

  effective_delay_threshold =
      lagging_class_threshold  if (matched AND entity_override == "false")
                                   AND (lagging_class.delay_mode applicable)
      else  entity-level threshold  (data_max_delay_allowed for static policy,
                                     active slot value for variable policy)

The same rule applies to `data_max_lag_allowed` when the matched class also
declares a `value_lag` — when present, the class's lag value wins over the
entity's. When the class has no `value_lag`, lag stays at the entity-level
value.

### The trap (and how to avoid it)

If you `update_entity_thresholds` (or `update_entity_variable_delay`) for an
entity where `lagging_class_assignment.matched=true` AND
`lagging_class_assignment.entity_override="false"`, the write SUCCEEDS at the
API layer and is recorded in the audit log — but the *active* threshold the
decision maker enforces is still the class's. The entity stays RED. Operators
see "the advisor said it fixed this and nothing happened".

You have THREE legitimate responses when this collision exists. Pick ONE per
remediation and explain the choice in `reason`:

1. **Update the class** via `update_lagging_class(lagging_class_key=...,
   value_delay=... | variable_delay_default=... + variable_delay_slots=...,
   value_lag=...)`. Use this when the class threshold is wrong for EVERY
   matched entity — the typical case (peer entities share the same regime).
   ONE write fixes the whole peer set.

2. **Opt the entity out** via `set_entity_lagging_class_override(override=true,
   ...)`. Use this only when the SPECIFIC entity needs to differ from its
   peers. Rare; document the divergence in `reason`. After opt-out, your
   entity-level threshold writes take effect normally.

3. **Live with it.** When the matched class is actually correct for this
   entity, no action is needed on delay/lag — but you may still need to act
   on other anomaly reasons (priority, monitoring state, ML model, etc.).

NEVER do (1) AND (2) on the same entity in the same run — pick the right lever
for the situation and act on it once. Doing both implies confused intent and
the audit log will show it.

### Priority change + lagging class side effect

Lagging classes can match on `level="priority"`. Escalating an entity from
`low` → `critical` may suddenly match a `high|critical` class that wasn't
matching before, instantly putting the entity under that class's thresholds.
The reverse is also true (`critical` → `low` may drop a match). Before changing
priority on an entity, call `get_lagging_classes` and walk the
`level="priority"` ones to determine the post-change match state. If a new
class will match, plan the threshold remediation around what THAT class
enforces (or preemptively loosen it via `update_lagging_class`).

## DATA SAMPLING (DSM-only data-quality anomaly type)

Data Sampling is a DSM-only feature that periodically samples a subset of
events from each entity, fits regex-based format models, and flags anomalies
when the match percentage drops below the configured threshold or a
multiformat (multiple formats simultaneously in the source) is detected.
When a sampling anomaly fires:

- ``anomaly_reasons`` (returned by `get_entity_lifecycle_context`) includes
  ``"data_sampling_anomaly"``.
- The decision maker adds `impact_score_dsm_data_sampling_anomaly` to the
  entity's total score. The default weight is **36** (medium —
  configurable per-tenant). A sampling anomaly alone is not enough to push
  an entity to RED (RED = score ≥ 100), but combined with one or two other
  anomaly reasons it readily can.

### Recognising the anomaly

If `anomaly_reasons` contains `"data_sampling_anomaly"`, your reasoning
chain MUST call `get_entity_data_sampling_state(tenant_id, object_name)`
before recommending or applying any remediation. Without that call you'll
see the anomaly reason but have no idea WHY sampling failed — the actual
root cause (a content-format change, a new event shape, a multiformat
collision) is in the sampling state record.

The tool returns:
- `status_colour` — currently `"red"` when an anomaly is active
- `anomaly_reason` — a short string explaining what failed
- `status_message` — the human-readable status the operator sees in the UI
- `matched_model_summary` — comma-separated names of the OOTB / custom models
  that recently matched the sampled events
- `multiformat_detected` — when ``True``, the entity is producing events in
  more than one format simultaneously (e.g. JSON and KV in the same
  sourcetype) — common when an upstream forwarder is misrouted
- `current_detected_format` / `current_detected_major_format` — the
  predominant format the latest sampling pass recognised
- `previous_detected_format` — what was matching BEFORE the anomaly fired —
  useful for "did the format change" reasoning
- `events_count` — sample size; if this is low (<100) sampling stats are
  noisy and the anomaly may be a flake

### Remediation paths

The right response depends on what the sampling state tells you:

1. **Legitimate format change** (`previous_detected_format` ≠
   `current_detected_format`, but the new format is a recognised major
   format like JSON / XML / CSV): the data source has shifted format. Either
   accept the new normal (no action needed — the next sampling cycle should
   re-learn) OR, if the model is too strict, in act mode call
   `add_data_sampling_model` to extend coverage to the new shape (see
   the DATA SAMPLING WRITE-TOOL DISCIPLINE section for the pre-read +
   reason discipline you MUST follow). In inspect mode, surface the
   recommendation in your structured output and let the operator act.
2. **Multiformat detected** (`multiformat_detected=True`): the entity is
   producing more than one format simultaneously. This is almost always
   an upstream misrouting — investigate forwarder routing, sourcetype
   assignment, or input-stage parsing rules. Do NOT silence the alert by
   tuning thresholds; the alert is correct and the operator needs to know.
3. **Coverage gap** (no recognised major format matched, but the events
   parse cleanly to the human eye): the entity uses a proprietary format
   not covered by OOTB or existing custom models. Recommend an operator add
   a custom model regex via the Data Sampling management UI (or wait for
   Phase 3 generate-model wizard support).
4. **Sparse sampling** (`events_count` low — heuristic baseline ~100,
   adjust based on the tenant's sampling cadence
   (`iteration_interval_seconds`) and entity ingest rate): the anomaly may
   be noise from too few events. Note it in your reasoning but don't
   recommend a permanent change — the next cycle should produce more
   samples. Use your judgement: a high-volume entity that sampled <100
   events in a 1-hour window is unusual and worth flagging; a low-volume
   entity that legitimately produces <100 events per sampling window is
   normal.
5. **False positive** (`current_detected_major_format` matches the
   `matched_model_summary` and `pct_min_inclusive_match` is high): the
   detection is incorrect. Surface this in `reason` so the operator can
   investigate / tune the model thresholds.

### What you MUST NOT do in inspect mode

- Do NOT recommend tuning `data_max_delay_allowed` / `data_max_lag_allowed`
  to "fix" a sampling anomaly. Delay/lag thresholds have nothing to do with
  content format — the agent's audit trail will read as nonsensical to the
  operator and erode trust.
- Do NOT recommend disabling sampling for the entity to "make the alert go
  away". Sampling is a data-quality signal; silencing it loses information
  the operator wants. If the anomaly is genuinely a false positive, recommend
  reviewing the model thresholds instead.

### DATA SAMPLING WRITE-TOOL DISCIPLINE (Phase 2 of issue #1901)

In act mode you have three write tools for the per-tenant custom
data-sampling model collection:

- `add_data_sampling_model(tenant_id, model_name, model_regex, model_type,
  reason, sourcetype_scope="*")` — add a new custom regex format model.
  `model_type` is `"inclusive"` (events MUST match to count as well-formed)
  or `"exclusive"` (events MUST NOT match — match indicates malformed
  content). `sourcetype_scope` defaults to `"*"`; use a comma-separated
  exact-match list (no wildcards, no spaces) for narrower scoping.
- `update_data_sampling_model(tenant_id, model_record, reason)` — modify
  an existing custom model. `model_record` is a full record dict from
  `get_data_sampling_models` (the `custom` list), mutated to carry the
  fields that need changing. The `_key` field on the record identifies
  which model to update.
- `delete_data_sampling_model(tenant_id, model_name, reason)` — remove a
  custom model. The name is the human-readable `model_name` returned by
  `get_data_sampling_models`.

#### Discipline you MUST follow

1. **Pre-read before every write**. ALWAYS call `get_data_sampling_models`
   before any of the three writes:
   - Before `add_*`: confirm the proposed pattern is not already covered
     by an OOTB or existing custom model. Duplicate models clutter the
     audit trail and confuse downstream model-match summaries.
   - Before `update_*`: fetch the current record (you need its `_key`,
     and you must not blank out fields you didn't intend to change).
   - Before `delete_*`: confirm the model is custom (OOTB models can't be
     deleted via this endpoint anyway, but proposing one is a sign your
     reasoning chain is wrong).

2. **One model per call.** Each write tool targets a single model. Bulk
   operations are out of scope — they make audit reasoning harder. If
   you have N changes to make, issue N calls; the operator can track
   each one in the audit log.

3. **`reason` is mandatory.** Every write lands in the
   `trackme_audit` index with `update_comment` set to
   `[AI Feed Lifecycle Advisor] <reason>`. Empty / one-word reasons
   ("API update", "fix") are useless to the operator reading the audit
   trail later. Explain WHAT changed and WHY — e.g. *"Coverage gap
   detected for netscreen:firewall sourcetype — no OOTB model fits the
   `device_id=` keyword the new firmware emits"*.

4. **Never write to silence an alert without root-cause analysis.** A
   `data_sampling_anomaly` reflects a real change in the data shape;
   tuning a model to mask it loses the signal the operator wanted.
   When in doubt, prefer surfacing a recommendation in your structured
   output over taking an act-mode action.

5. **Deletion has downstream consequences.** Removing a custom model can
   re-introduce `data_sampling_anomaly` reports for entities whose data
   only matched that model. Before recommending a deletion, sample a
   few entities via `get_entity_data_sampling_state` and confirm the
   model isn't the sole matcher under `matched_model_summary` for any
   active entity. If it is, propose the deletion AND a replacement plan
   together — don't strand the operator with a regression.

6. **Honour the operator's request for inspect-only behaviour.** If the
   `user_context` says "do not modify models" / "inspect only" /
   similar, respect it. Surface recommendations; do not call the write
   tools. Same lesson as the lagging-class discipline.

### Out of scope for the Feed Lifecycle Advisor (still)

- Phase 3 of issue #1901 will add a wizard-time generate-model mode
  (mirroring FQM's `dictionary_generate`) where you sample events and
  propose a starter regex. Not in scope yet — the three Phase 2 tools
  above let you ADD a model you already know, but they don't help you
  DISCOVER one from raw sampled events. Until Phase 3 lands, the agent
  proposes regexes based on its own reasoning about the data shape
  (visible via `current_detected_format` / `previous_detected_format`),
  which is acceptable but slower.

## MODE BEHAVIOR

- **inspect**: Read-only. Gather data, analyze, report findings with specific recommendations.
  Do NOT call any write tools.
- **act**: You MUST follow this EXACT sequence:
  1. FIRST: Call read tools to analyze (steps 1-5 of the reasoning framework).
     From `get_entity_lifecycle_context`, read `anomaly_reasons` and `is_outlier`.
     These two fields MUST drive every write decision.
     **EXCEPTION**: If the initial message contains a **PRIOR INSPECTION RESULTS**
     block from a recent inspect run, you MAY use it directly. In that case, call
     `get_entity_lifecycle_context` ONCE to confirm the entity state has not changed,
     then skip straight to step 2.
  2. THEN: Call the write tools that DIRECTLY address the `anomaly_reasons`.
     The correct delay tool depends on the entity's `variable_delay_policy`
     (always read this from `get_entity_lifecycle_context` BEFORE writing):

     - `lag_threshold_breached` / `latency_threshold_breached` (any policy):
       → MUST call `update_entity_thresholds` with `data_max_lag_allowed` only.
         The lag threshold is always static; `variable_delay_policy` does
         NOT redefine it. Leave `data_max_delay_allowed` empty in this call.

     - `delay_threshold_breached` AND `variable_delay_policy="static"`:
       → MUST call `update_entity_thresholds` with `data_max_delay_allowed`.

     - `delay_threshold_breached` AND `variable_delay_policy="variable"`:
     - `variable_delay_threshold_breached` (any policy):
       → MUST call `update_entity_variable_delay` to update the slot
         configuration (specifically the active slot for the time window
         where the breach occurred — usually `business_hours`).
         Slot `days`/`hours` are in the Splunk server's local time (UTC on
         Splunk Cloud, the host's system zone on-prem); always read and write
         them in server-local time. The web UI translates hours to/from the
         operator's browser time for display only — never the stored values.
         DO NOT call `update_entity_thresholds(data_max_delay_allowed=...)`
         in this case — the static field is INERT when slot-based
         thresholds are active, the call will be REJECTED by the tool
         guard with a `redirect_tool` hint pointing back to
         `update_entity_variable_delay`. The audit log would otherwise
         record a misleading write to a field that has no effect on the
         entity's active alerting threshold.

     - `delay_threshold_breached` on an UNLOCKED entity (no red 🔒):
       → MUST also call `update_entity_adaptive_delay` (with
         allow_adaptive_delay="false") to LOCK the new thresholds so
         automation cannot overwrite them on the next cycle (regardless
         of which delay-update tool above applied).

     - Combined case: variable-policy entity with BOTH a slot breach AND a
       lag breach → make TWO calls. First `update_entity_variable_delay`
       for the slot, then `update_entity_thresholds` with
       `data_max_lag_allowed` only for the lag.

     Write tools targeting the root `anomaly_reasons` are MANDATORY before
     producing output. ML model actions are SECONDARY and are only
     permitted when `is_outlier=1`.
  3. LAST: Only after the write tools have returned their results, produce your
     structured output with actions_taken populated from the actual tool responses.

  CRITICAL: If you are in act mode and you have not called any write tools yet,
  you are NOT done. Do NOT produce your final structured output until you have
  called the write tools for the identified anomaly_reasons. An empty actions_taken
  array in act mode is a failure. Filling actions_taken with ML-only actions when
  `is_outlier=0` and delay/latency anomalies are present is also a failure.

## AUDIT REASON DISCIPLINE

Every write tool you call takes a `reason: str` parameter. Whatever you pass
lands in the per-entity "Audit changes" panel as `[AI Agent] <reason>` —
teammates reviewing the audit timeline weeks later see only this. Make `reason`
count:

- **Cite the field, the from/to values, and the operational trigger.** Bad:
  `"updated"`. Good: `"Loosened delay_threshold from 600s to 1800s after
  observing p95=1490s sustained for 14 days on this slow-batch feed."`
- **Mirror the user's intent** when supplied via `user_context` — the audit
  should show why the operator asked for the change, not just what the agent
  computed.
- **Never use empty / generic strings** like `""` / `"update"` /
  `"API update"`. They signal the reason wasn't thought through and degrade
  the audit log's value for everyone.

## CONSTRAINTS

- NEVER disable an entity without stating the explicit data evidence (e.g., "no data for 14 days")
- NEVER tighten thresholds — only loosen them or leave them unchanged
- When setting delay/latency thresholds, ALWAYS add a safety buffer above p95
  (at minimum 10-20% above the observed p95)
- When recommending variable delay schedules, specify concrete slot values
- Always explain your reasoning in the reasoning_trace field
- Limit write tool calls to the minimum necessary to fix the identified issues
- NEVER take any ML outlier action (disable, retrain, update model rules, manage detection)
  when `is_outlier` is `0`. A model that is not contributing to the current RED score must
  not be touched — the root cause is elsewhere (delay/latency thresholds) and ML actions
  would only obscure the real fix.
- NEVER disable, retrain, or modify ML outlier models when `outlier_readiness` is `false`.
  A model with readiness=false has insufficient training history and cannot have contributed
  meaningfully to the entity's score — leave it alone and focus solely on delay/latency
  threshold tuning.
"""


# ---------------------------------------------------------------------------
# Phase 3 of issue #1901 — wizard-time system prompt
# ---------------------------------------------------------------------------

DATA_SAMPLING_MODEL_GENERATE_SYSTEM_PROMPT = """You are TrackMe's Feed Lifecycle
Advisor in **generate-model mode** — invoked WIZARD-TIME from the Data Sampling
Create Custom Rule UI to propose a starter regex model from a sampled-events
payload. No entity exists yet, no KV access, no write tools — your single job
is to analyse the supplied sample events and produce a high-quality starter
regex the operator can review and submit.

## YOUR MISSION

The operator is creating a custom Data Sampling model for a specific sourcetype.
They want a regex that will match well-formed events of that sourcetype during
the next sampling cycle. You receive:

- `tenant_id` — the virtual tenant the operator is configuring
- `sourcetype` — the Splunk sourcetype the model will scope to
- `samples` — a list of raw event strings sampled from the live data

Propose ONE custom model regex (inclusive type — match-to-count-as-well-formed)
that recognises the dominant format family in the sample. Return your reasoning
in the structured output schema.

## CONTEXT

Data Sampling is a DSM-only data-quality feature that periodically samples
events from each entity and fits regex-based format models against them.
Custom models extend the OOTB built-in models (JSON, XML, CSV, key=value,
syslog, …) with site-specific patterns — proprietary log formats, vendor-
specific log shapes, internal application formats.

A high-quality model regex:

- **Is specific enough to NOT match unrelated formats** — a regex like `.*` would
  match every event and provide zero signal.
- **Is general enough to match every well-formed event of THIS format** — a
  regex pinned to a single example value (e.g. specific timestamps, specific
  device IDs) will fail the next time the format produces a different value.
- **Anchors on stable structural markers** — keywords, fixed punctuation,
  field-name prefixes, format-family hallmarks like `<n>1 <timestamp>` for
  RFC5424 syslog.

## REASONING FRAMEWORK

1. **CLASSIFY THE SAMPLE**: scan the events and decide whether the dominant
   format family is structured (JSON / XML / CSV / KV-pairs), semi-structured
   (syslog, vendor logs), or unstructured (free-text). Note in
   `summary` what you observed.

2. **DETECT MULTIFORMAT**: if the sample contains more than one obviously
   distinct format family (e.g. some events are JSON, others are KV), say so
   in `confidence_notes` and propose the regex for the DOMINANT family. The
   operator can add a second model for the minority family afterwards. Don't
   try to capture both in one regex — it dilutes specificity.

3. **EXTRACT STRUCTURAL ANCHORS**: identify the tokens that appear in every
   well-formed event of the dominant format and are NOT specific to any one
   value. Good anchors:
   - Format-family hallmarks: `^\\{` for JSON, `^<\\d+>` for RFC5424,
     `^[A-Z]+\\s+\\d+\\s+\\d{2}:\\d{2}:\\d{2}` for BSD syslog.
   - Persistent field-name prefixes: `device_id=`, `level=`, `time=`,
     `event_type=`.
   - Vendor signatures: `NetScreen`, `ASA-\\d-\\d{6}`, `EVT_`.

4. **AVOID VALUE-SPECIFIC PINS**: timestamps, IPs, hostnames, device IDs,
   integer counters vary across events of the SAME format. Match the
   *structural shape* (`\\d+`, `[a-fA-F0-9.:]+`, `\\S+`) not the specific
   value.

5. **PROPOSE THE REGEX**: write the simplest regex that matches every event
   of the dominant family in the sample and would NOT match obviously
   different formats. Escape special characters per Python re-module
   conventions. Test it mentally against every sampled event before
   submitting.

6. **TAG CONFIDENCE**:
   - `high` — the format family is unambiguous, the sample is uniform, the
     regex matches every event cleanly, the anchors are stable across
     vendors / versions.
   - `medium` — the dominant family is clear but the sample has some
     variability (e.g. occasional whitespace differences, optional fields).
     Operator should review.
   - `low` — sample size is small (<10), multiple format families coexist,
     OR the regex required permissive tolerances to cover the sample. The
     operator should sample more events before committing.

## OUTPUT CONTRACT (HARD RULES)

Your structured output MUST satisfy:

- `proposed_model_name` — non-empty kebab-case or snake_case identifier
  derived from the sourcetype + format family (e.g.
  `netscreen_firewall_rfc5424`).
- `proposed_model_regex` — a syntactically VALID Python `re` pattern. Use
  `re` escaping conventions (`\\`, `(`, `)`, `[`, `]`, `.`).
- `proposed_model_type` — almost always `inclusive` (events must match to
  count as well-formed). Use `exclusive` only when the operator is asking
  to flag a MALFORMED pattern (rare in wizard-mode; mention it in
  `confidence_notes` if you go this way).
- `proposed_sourcetype_scope` — defaults to the wizard's `sourcetype`
  value (single sourcetype, no wildcards / no spaces). Use `*` only if
  the regex is genuinely format-agnostic AND should apply to every
  sourcetype this tenant ingests.
- `summary` — 2-3 sentences. What format family did you see? Anything
  unusual?
- `confidence_notes` — caveats. Empty when the proposal is high-confidence
  and unambiguous.
- `reasoning_trace` — short bullets explaining how you got from the sample
  to the regex. One bullet per major observation is plenty.

## CONSTRAINTS

- **You have NO entity context.** Don't reason about historical delay /
  lag / threshold settings — those belong to inspect/act mode. Stay focused
  on the sample.
- **You have NO write tools.** Do not call any tool. Produce structured
  output only.
- **Reject samples with <3 events** by setting `confidence: "low"` and
  saying so in `confidence_notes`. Don't make up a regex you can't verify
  against the sample — surface the uncertainty.
- **NEVER output `.*` or `.+` as the entire regex.** Such a "match anything"
  pattern provides zero signal and is worse than no model at all.
- **NEVER pin to value-specific tokens** (specific timestamps, specific
  IPs, specific device IDs). The model has to keep matching tomorrow's
  events.
"""


# ---------------------------------------------------------------------------
# Prior Inspect Result Lookup
# ---------------------------------------------------------------------------


def _get_recent_inspect_result(service, tenant_id, object_id, max_age_minutes=30):
    """Retrieve the most recent successful Feed Lifecycle Advisor inspect result from the summary index."""
    from trackme_libs_ai import get_recent_agent_inspect_result

    return get_recent_agent_inspect_result(
        service,
        tenant_id,
        object_id,
        sourcetype="trackme:ai_agent:feed_lifecycle_advisor:inspect",
        max_age_minutes=max_age_minutes,
    )


# ---------------------------------------------------------------------------
# Agent Runner
# ---------------------------------------------------------------------------


def _vtenant_allows_decommission(vtenant_account):
    """Return True if the tenant allows automated decommissioning actions.

    Reads the unified ``ai_components_advisor_allow_decommission`` field
    (replaces the per-advisor ``ai_feed_lifecycle_allow_decommission``).
    """
    return vtenant_account.get("ai_components_advisor_allow_decommission", "0") == "1"


async def _run_feed_lifecycle_agent(
    service, model, config, tenant_id, component, object_id, object_name, mode,
    user_context=None, automated=False, vtenant_account=None, job_id=None, server_name=None,
    wizard_payload=None,):
    """
    Run the Feed Lifecycle Advisor agent asynchronously.

    Args:
        service: Splunk service connection
        model: SDK model (OpenAIModel or AnthropicModel)
        config: AI provider configuration dict
        tenant_id: Tenant identifier
        component: Component type (dsm or dhm)
        object_id: Entity _key hash in KV Store. Pass empty string when
            ``mode="generate_model"`` (no entity exists wizard-time).
        object_name: Entity name. Pass empty string when
            ``mode="generate_model"``.
        mode: "inspect" (read-only) / "act" (apply changes) /
            "generate_model" (wizard-time, no entity, no tools —
            Phase 3b of issue #1901).
        user_context: Optional free-text instructions from the user
        wizard_payload: Required when ``mode="generate_model"``,
            ignored otherwise. Already validated by the REST handler
            via ``validate_data_sampling_generate_payload``. Carries
            ``tenant_id`` / ``sourcetype`` / ``samples`` for the
            wizard agent.

    Returns:
        LifecycleAdvisorResult (inspect / act) OR
        DataSamplingModelGenerateResult (generate_model).
    """
    # Pin the shared agent infrastructure's logger to this advisor for
    # the duration of this async context.  Without this, tool_middleware
    # lines from trackme_libs_ai_agents.py route to the default
    # (ml_advisor) log file even when this advisor is the one running.
    set_current_advisor_logger("trackme.rest.ai.feed_lifecycle")

    from splunklib.ai.agent import Agent
    from splunklib.ai.messages import HumanMessage
    from splunklib.ai.hooks import before_model
    from splunklib.ai.limits import AgentLimits
    from splunklib.ai.tool_settings import ToolSettings, LocalToolSettings, ToolAllowlist

    model_name = config.get("ai_model", "unknown")
    provider_type = config.get("ai_provider", "unknown")
    provider_name_log = config.get("provider_name", "unknown")

    if mode == "inspect":
        allowed_tags = ["lifecycle_read", "maintenance_read"]
        agent_token_limit = max(1, int(config.get("ai_agent_token_limit", "150000")))
        agent_step_limit = max(1, int(config.get("ai_agent_step_limit", "20")))
    elif mode == "generate_model":
        # Phase 3b of issue #1901 — wizard-time data-sampling model
        # generation. The agent reasons purely from the wizard payload
        # supplied in the initial message; no MCP tools are invoked.
        # Allowlist is empty so the SDK's tool filter rejects any tool
        # call attempt (prompt also tells the model not to try, but
        # defence in depth — same pattern as FQM ``dictionary_generate``).
        # Token / step limits reuse the inspect tier; the wizard agent
        # has no read-tool round trip eating tokens — everything is in
        # the prompt and the structured output.
        #
        # Defensive guard against bypass of the REST validator: the
        # docstring says wizard_payload is validated by the REST handler,
        # but ``_run_feed_lifecycle_agent`` is reachable from
        # ``start_feed_lifecycle_advisor_async`` (public API). A future
        # caller that forgets to set wizard_payload would otherwise hit
        # ``json.dumps(wizard_payload or {}, ...)`` and produce an empty-
        # payload prompt — the agent would reason over `{}` and return
        # garbage with no error signal. Fail fast here. CodeRabbit
        # finding on PR #1914.
        if wizard_payload is None:
            raise ValueError(
                "wizard_payload is required when mode='generate_model'. "
                "Call validate_data_sampling_generate_payload() at the "
                "REST / public-API boundary before invoking the runner."
            )
        allowed_tags = []
        agent_token_limit = max(1, int(config.get("ai_agent_token_limit", "150000")))
        agent_step_limit = max(1, int(config.get("ai_agent_step_limit", "20")))
    else:  # "act"
        # ``entity_metadata_write`` — shared cross-advisor tag for
        # entity-metadata tools (labels, notes, …) defined in
        # ``trackme_ai_agent_tools``. ``maintenance_*`` — shared per-entity
        # maintenance tools. See the same comment in
        # ``trackme_libs_ai_agents.py``.
        allowed_tags = [
            "lifecycle_read",
            "lifecycle_write",
            "entity_metadata_write",
            "maintenance_read",
            "maintenance_write",
        ]
        agent_token_limit = max(1, int(config.get("ai_agent_act_token_limit", "200000")))
        agent_step_limit = max(1, int(config.get("ai_agent_act_step_limit", "40")))

    if mode == "generate_model":
        # No entity context — log the wizard-payload identifier instead.
        _sourcetype_log = ""
        if isinstance(wizard_payload, dict):
            # ``.get("sourcetype")`` returns None when the key is missing;
            # ``or ""`` coerces that AND any falsy non-string the validator
            # would have rejected. CodeRabbit PR #1914 nit: drop the
            # redundant default arg (the ``or`` already covers None).
            _sourcetype_log = wizard_payload.get("sourcetype") or ""
        logger.info(
            f"Feed Lifecycle Advisor agent starting: mode={mode}, model={model_name}, "
            f"provider={provider_type} ({provider_name_log}), "
            f"token_limit={agent_token_limit}, step_limit={agent_step_limit}, "
            f"sourcetype={_sourcetype_log!r}"
        )
    else:
        logger.info(
            f"Feed Lifecycle Advisor agent starting: mode={mode}, model={model_name}, "
            f"provider={provider_type} ({provider_name_log}), "
            f"token_limit={agent_token_limit}, step_limit={agent_step_limit}, "
            f"entity={object_name} ({object_id})"
        )

    if mode == "generate_model":
        # Wizard-time payload — no entity in KV. The system prompt has the
        # full reasoning framework; we just hand it the JSON sample. Same
        # shape as FQM's ``dictionary_generate`` initial message.
        initial_message = (
            "Generate a starter data-sampling custom-model regex for the "
            "sourcetype the operator is configuring in the wizard.\n\n"
            "**Wizard payload** (raw events sampled from the live source):\n\n"
            f"```json\n{json.dumps(wizard_payload or {}, indent=2)}\n```\n\n"
            "Reason directly from the sampled events above. Produce one "
            "proposed model — name, regex, type, sourcetype scope, "
            "confidence — per the structured output contract in your system "
            "prompt. No tool calls — you don't have any in this mode."
        )
    else:
        initial_message = (
            f"Analyze the lifecycle configuration for this TrackMe entity:\n\n"
            f"- **Tenant ID**: {tenant_id}\n"
            f"- **Component**: {component}\n"
            f"- **Object ID** (_key hash, use for KV lookups): {object_id}\n"
            f"- **Object Name** (entity name, use for history queries): {object_name}\n"
            f"- **Mode**: {mode}\n\n"
        )

    if mode == "inspect":
        initial_message += (
            "Perform a read-only inspection. Analyze the entity's ingestion history, "
            "current thresholds, and monitoring configuration. Report your findings with "
            "specific, actionable recommendations but do NOT apply any changes."
        )
    elif mode == "generate_model":
        # Already populated above — no extra narrative.
        pass
    else:
        initial_message += (
            "**MODE: ACT — You MUST apply changes using write tools.**\n\n"
            "Analyze the entity's ingestion history, current thresholds, and configuration. "
            "Then EXECUTE the appropriate remediation actions by calling the write tools:\n"
            "- Use `update_entity_thresholds` to fix static delay/latency "
            "thresholds — `data_max_lag_allowed` always, `data_max_delay_allowed` "
            "ONLY when `variable_delay_policy=\"static\"` (the call is rejected "
            "by the tool guard when policy is `\"variable\"`)\n"
            "- Use `update_entity_variable_delay` to update slot thresholds — "
            "this is the ONLY tool that affects the active delay threshold "
            "when `variable_delay_policy=\"variable\"`\n"
            "- Use `update_entity_monitoring_state` to disable stale entities\n"
            "- Use `update_entity_adaptive_delay` to LOCK/UNLOCK the entity's thresholds "
            "(allow_adaptive_delay=\"false\" locks, \"true\" unlocks)\n"
            "- Use `update_entity_priority_and_tags` to adjust priority\n"
            "- Use `update_entity_impact_score_weights` to tune impact scores\n"
            "- For `data_sampling_anomaly` on a DSM entity, use "
            "`add_data_sampling_model` / `update_data_sampling_model` / "
            "`delete_data_sampling_model` to mutate the per-tenant custom "
            "sampling model collection. ALWAYS pre-read with "
            "`get_data_sampling_models` first (one tool call) and pass a "
            "multi-word `reason` — see the DATA SAMPLING WRITE-TOOL "
            "DISCIPLINE section for the full discipline\n\n"
            "Do NOT just recommend — you MUST call the write tools to apply changes. "
            "Document every action in the actions_taken array of your response."
        )

        # Inject prior inspect result if available (saves redundant read phase)
        prior_result = _get_recent_inspect_result(service, tenant_id, object_id)
        if prior_result:
            initial_message += (
                f"\n\n**PRIOR INSPECTION RESULTS (completed within the last 30 minutes)**\n"
                f"A recent inspect run already analyzed this entity. Use these findings as "
                f"your starting point: call `get_entity_lifecycle_context` once to confirm "
                f"the entity state is unchanged, then proceed directly to the write tools.\n\n"
                f"```json\n{json.dumps(prior_result, indent=2)}\n```"
            )

    if user_context:
        initial_message += (
            f"\n\n**OPERATOR INSTRUCTIONS** (from the user running this analysis):\n"
            f"{user_context}"
        )

    # For models using SDK ToolStrategy (Ollama, Mistral, etc.), remind the model
    # it must call the `respond` tool to submit structured output.
    initial_message += _build_initial_message_tool_strategy_hint(model, provider_type)

    # Automated decommission guard: inject constraint when automated=True and allow_decommission=0
    if automated and not _vtenant_allows_decommission(vtenant_account or {}):
        initial_message += (
            "\n\n**AUTOMATED MODE CONSTRAINT — DECOMMISSIONING**: You must NOT apply "
            "`monitored_state: disabled` or entity deletion actions in this automated run. "
            "These destructive actions require analyst review and are blocked by tenant policy. "
            "If you believe decommissioning is warranted, include it as a recommendation only — "
            "do not call any write tool to disable or delete the entity."
        )

    # Sanitize SSL_CERT_FILE — may point to non-existent path in Splunk env
    _ssl_cert_file = os.environ.get("SSL_CERT_FILE")
    _ssl_removed = False
    if _ssl_cert_file and not os.path.isfile(_ssl_cert_file):
        del os.environ["SSL_CERT_FILE"]
        _ssl_removed = True

    # Signal automated mode to the MCP tool subprocess so the decommission guard
    # only fires for scheduled (unattended) runs, not interactive user sessions.
    _automated_prev = os.environ.get("TRACKME_AI_AUTOMATED")
    os.environ["TRACKME_AI_AUTOMATED"] = "1" if automated else "0"

    max_attempts = 3
    last_error = None

    # Token/step usage tracking — captured via before_model hook.
    _token_count = [0]
    _steps_taken = [0]

    @before_model
    def _capture_usage(req) -> None:
        # AgentState.token_count / total_steps were removed by upstream
        # PR #770 (commit ``3d68138``). Derive equivalents from
        # ``req.state.messages`` — for steps, the message-list length is
        # what the SDK's old ``total_steps`` tracked; for tokens, the ~4
        # chars/token heuristic matches what the SDK's now-internal
        # ``_get_approximate_token_counter`` returns in the same order of
        # magnitude, without taking a dep on a ``_``-prefixed function.
        # Polymorphic text extraction — HumanMessage / AIMessage / SystemMessage /
        # StructuredOutputMessage carry ``.content``; ToolMessage / SubagentMessage
        # carry ``.result`` (a nested dataclass whose ``__repr__`` includes the
        # text we'd want anyway).  ``getattr`` fallback handles both shapes
        # without needing an isinstance dispatch — important because the SDK
        # adds new message types over time and we'd silently undercount.
        _token_count[0] = sum(
            len(str(getattr(m, "content", None) or getattr(m, "result", None) or ""))
            // 4
            for m in req.state.messages
        )
        _steps_taken[0] = len(req.state.messages)
        # Heartbeat for the watchdog (see ``_make_agent_worker_watchdog``
        # in ``trackme_libs_ai_agents``): refresh ``last_activity`` so
        # the watchdog's inactivity check sees liveness BEFORE entering
        # the LLM call.  Catches the SDK-hang failure mode where the
        # round-trip never returns.
        try:
            _agents_module._refresh_agent_heartbeat(service, job_id)
        except Exception:
            pass

    # Import feed lifecycle tools registry (deferred — requires Python 3.13)
    import trackme_ai_feed_lifecycle_tools  # noqa: F401 — side-effect: registers tools

    # Resolve tenant summary index for per-tool-call event emission.
    try:
        from trackme_libs import trackme_idx_for_tenant  # noqa: WPS433 — deferred import
        _splunkd_uri = f"{service.scheme}://{service.host}:{service.port}"
        _idx_settings = trackme_idx_for_tenant(service.token, _splunkd_uri, tenant_id)
        _summary_index = _idx_settings.get("trackme_summary_idx", "trackme_summary")
    except Exception:
        _summary_index = "trackme_summary"

    _check_agent_model_capability(model, provider_type, model_name)
    # Mode-specific prompt + output-schema selection. ``generate_model`` is
    # wizard-time and uses an entirely different framework (no entity, no
    # tools, just sample-driven regex inference) so it gets its own system
    # prompt + Pydantic schema. ``inspect`` and ``act`` share the
    # entity-analysis prompt and result schema. Mirrors FQM's
    # ``dictionary_generate`` dispatch (Phase 3b of issue #1901).
    if mode == "generate_model":
        _system_prompt = DATA_SAMPLING_MODEL_GENERATE_SYSTEM_PROMPT
        _output_schema = DataSamplingModelGenerateResult
    else:
        _system_prompt = FEED_LIFECYCLE_ADVISOR_SYSTEM_PROMPT
        _output_schema = LifecycleAdvisorResult
    # Append provider-level and tenant-level custom instructions to the
    # resolved system prompt — same concatenation as every other automated
    # advisor (see ``build_automated_system_prompt``).
    _system_prompt = build_automated_system_prompt(
        _system_prompt, config, vtenant_account
    )
    try:
        for attempt in range(1, max_attempts + 1):
            _token_count[0] = 0  # reset on retry
            _steps_taken[0] = 0
            try:
                with force_tool_strategy_for_provider(provider_type):
                    async with Agent(
                        model=model,
                        system_prompt=_system_prompt,
                        service=service,
                        tool_settings=ToolSettings(
                            local=LocalToolSettings(allowlist=ToolAllowlist(tags=allowed_tags)),
                            remote=None,
                        ),
                        output_schema=_output_schema,
                        limits=AgentLimits(
                            max_tokens=agent_token_limit,
                            max_steps=agent_step_limit,
                        ),
                        middleware=[
                            mw for mw in [
                                _capture_usage,
                                make_prompt_cache_middleware(
                                    provider_type, config=config,
                                ),
                                make_tool_trace_middleware(
                                    "Feed Lifecycle Advisor",
                                    job_id=job_id,
                                    service=service,
                                    advisor_kind="feed_lifecycle_advisor",
                                    tenant_id=tenant_id,
                                    component=component,
                                    object_name=object_name,
                                    object_id=object_id,
                                    mode=mode,
                                    automated=automated,
                                    summary_index=_summary_index,
                                    server_name=server_name,
                                ),
                            ] if mw is not None
                        ],
                    ) as agent:
                        logger.info(
                            f"Feed Lifecycle Advisor agent invoke starting: job_id={job_id}, mode={mode}, attempt={attempt}/{max_attempts}"
                        )
                        result = await agent.invoke([HumanMessage(content=initial_message)])
                        output = result.structured_output

                        actions_count = len(output.actions_taken) if isinstance(output, LifecycleAdvisorResult) else 0
                        entity_status = output.entity_status if isinstance(output, LifecycleAdvisorResult) else "unknown"
                        logger.info(
                            f"Feed Lifecycle Advisor agent completed: mode={mode}, model={model_name}, "
                            f"entity_status={entity_status}, actions_taken_count={actions_count}, "
                            f"token_count={_token_count[0]}, steps={_steps_taken[0]}"
                        )

                        if mode == "act" and actions_count == 0:
                            logger.warning(
                                "Feed Lifecycle Advisor act mode produced no actions_taken — "
                                "the model may have skipped write tool execution"
                            )

                        return output, _token_count[0], _steps_taken[0]

            except Exception as e:
                if _is_structured_output_unsupported(e):
                    # Hard API rejection (e.g. Ollama 400 "does not support tools") —
                    # no point retrying, the model cannot participate in the agentic loop.
                    raise RuntimeError(
                        f"Model '{model_name}' (provider: {provider_type}) does not support "
                        f"tool use or structured output, which is required by the Feed Lifecycle "
                        f"Advisor agent. Please configure a model with function-calling support. "
                        f"Commercial API providers (OpenAI, Anthropic, Azure OpenAI) are "
                        f"recommended for reliable agentic workflows."
                    ) from e
                if _is_agent_structured_output_failure(e) and attempt < max_attempts:
                    # Model called tools but didn't call the `respond` tool at the end —
                    # non-deterministic with smaller open-source models. Retry with fresh
                    # agent context; the prompt hint may succeed on the next attempt.
                    logger.warning(
                        f"Feed Lifecycle Advisor agent did not produce structured output "
                        f"(attempt {attempt}/{max_attempts}), retrying with fresh context..."
                    )
                    last_error = e
                    continue
                if _is_agent_structured_output_failure(e):
                    # Exhausted retries — raise a clear error without asserting specific models.
                    raise RuntimeError(
                        f"Model '{model_name}' (provider: {provider_type}) did not produce "
                        f"structured output after {max_attempts} attempts. The model called tools "
                        f"but did not submit a final structured response. Commercial API providers "
                        f"(OpenAI, Anthropic, Azure OpenAI) offer the most consistent results "
                        f"for this agentic pattern."
                    ) from e
                # Transient provider / network error — see ML Advisor
                # for full rationale. Gated to inspect mode because
                # act mode has write tools allowlisted
                # (``lifecycle_write``, ``entity_metadata_write``)
                # that may already have executed before the transient
                # surfaced. See CodeRabbit review on PR #1754.
                if (
                    _is_transient_provider_error(e)
                    and attempt < max_attempts
                    and mode != "act"
                ):
                    delay = _transient_retry_backoff_sec(attempt + 1)
                    logger.warning(
                        f"Feed Lifecycle Advisor agent hit transient provider error "
                        f"(attempt {attempt}/{max_attempts}, sleeping {delay}s before retry): "
                        f"{type(e).__name__}: {str(e)[:300]}"
                    )
                    await asyncio.sleep(delay)
                    last_error = e
                    continue
                if (
                    _is_transient_provider_error(e)
                    and mode == "act"
                ):
                    logger.warning(
                        f"Feed Lifecycle Advisor agent hit transient provider error in act mode "
                        f"(attempt {attempt}/{max_attempts}) — NOT retrying because "
                        f"write tools may have executed; job will surface as error. "
                        f"{type(e).__name__}: {str(e)[:300]}"
                    )
                # Tool_result_bug also gated to non-act modes — see ML
                # Advisor's full rationale. Earlier writes in the same
                # conversation may have completed before the SDK lost
                # the LAST tool_result pairing.
                if (
                    _is_tool_result_bug(e)
                    and attempt < max_attempts
                    and mode != "act"
                ):
                    logger.warning(
                        f"Feed Lifecycle Advisor agent hit SDK tool_result bug "
                        f"(attempt {attempt}/{max_attempts}), retrying..."
                    )
                    last_error = e
                    continue
                if _is_tool_result_bug(e) and mode == "act":
                    logger.warning(
                        f"Feed Lifecycle Advisor agent hit SDK tool_result bug in act mode "
                        f"(attempt {attempt}/{max_attempts}) — NOT retrying because "
                        f"earlier write tools may have already executed; job will "
                        f"surface as error."
                    )
                raise

        if last_error:
            raise last_error

    finally:
        # Restore SSL_CERT_FILE if we removed it
        if _ssl_removed and _ssl_cert_file:
            os.environ["SSL_CERT_FILE"] = _ssl_cert_file
        # Restore TRACKME_AI_AUTOMATED
        if _automated_prev is None:
            os.environ.pop("TRACKME_AI_AUTOMATED", None)
        else:
            os.environ["TRACKME_AI_AUTOMATED"] = _automated_prev


# ---------------------------------------------------------------------------
# Interactive Entry Point (REST handler)
# ---------------------------------------------------------------------------


def start_feed_lifecycle_advisor_async(
    system_service,
    user_service,
    request_info,
    tenant_id,
    component,
    object_id,
    object_name,
    mode="inspect",
    provider_name=None,
    user_context=None,
    launched_by="ui",
    chat_session_id="",
    wizard_payload=None,
):
    """
    Start the Feed Lifecycle Advisor agent asynchronously.

    Creates a job record, spawns a background thread, returns immediately with job_id.

    Args:
        system_service: Splunk service with system auth (for config access)
        user_service: Splunk service with user auth (for RBAC)
        request_info: REST handler request info
        tenant_id: Tenant identifier
        component: "dsm" or "dhm"
        object_id: Entity _key hash in KV Store
        object_name: Entity name
        mode: "inspect" or "act"
        provider_name: AI provider name (None = first configured)
        user_context: Optional free-text instructions from the user
        launched_by: Audit attribution — ``"ui"`` (default), ``"ai_assistant"``
            (chat bridge), or ``"automation"`` (scheduled). Validated by the
            REST handler before reaching here.
        chat_session_id: Chat session that triggered this run (only when
            ``launched_by="ai_assistant"``); free-form audit string.

    Returns:
        dict with {job_id, status} or raises exception
    """
    model, config = get_sdk_model(system_service, provider_name=provider_name)

    with _active_agents_lock:
        if _agents_module._active_agents >= _MAX_CONCURRENT_AGENTS_DEFAULT:
            raise RuntimeError(
                f"AI agent at maximum capacity ({_MAX_CONCURRENT_AGENTS_DEFAULT} concurrent). "
                "Please try again later."
            )
        _agents_module._active_agents += 1

    try:
        job_id = _create_agent_job(system_service)

        # Build service for the agent.
        #
        # IMPORTANT: we authenticate as the *requester* (``session_key``)
        # rather than ``system_authtoken``.  Splunk SDK's
        # ``validate_agent_privileges`` (added in splunk-sdk-python PR
        # #753) rejects an agent whose service resolves to
        # ``splunk-system-user`` — the system token resolves to exactly
        # that user.  The requester is a trackme_admin / trackme_power
        # caller (enforced by the REST handler's capability check), so
        # they already have the per-tenant KV Store ACLs and trackme
        # REST permissions every agent tool needs.
        agent_service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.session_key,
            timeout=600,
        )
    except Exception:
        with _active_agents_lock:
            _agents_module._active_agents = max(0, _agents_module._active_agents - 1)
        raise

    splunkd_uri = f"{system_service.scheme}://{system_service.host}:{system_service.port}"
    session_key = request_info.system_authtoken
    server_name = request_info.server_servername

    # Captured for the audit dashboard: who launched this run, and how long
    # did it take end-to-end?  Pulled out here so they can be closed-over by
    # `_index_agent_event` without changing its signature (the function is
    # called from multiple terminal branches — adding parameters at every
    # call site adds noise without value).
    # Mutable holder so the thread's _worker() can stamp the start time AFTER
    # the worker actually begins running — this excludes thread spawn /
    # scheduling overhead from duration_ms and keeps interactive vs
    # automated runs comparable.  See enrich_agent_event_for_audit.
    _run_start_time = [time.time()]
    _request_user = getattr(request_info, "user", None) or None

    def _index_agent_event(svc, result_dict, agent_mode, status, error_msg=None, token_count=0, steps_taken=0):
        try:
            from trackme_libs import trackme_idx_for_tenant
            try:
                idx_settings = trackme_idx_for_tenant(session_key, splunkd_uri, tenant_id)
                tenant_summary_idx = idx_settings.get("trackme_summary_idx", "trackme_summary")
            except Exception:
                tenant_summary_idx = "trackme_summary"

            sourcetype = f"trackme:ai_agent:feed_lifecycle_advisor:{agent_mode}"
            object_category = f"splk-{component}"
            event = {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "component": component,
                "object_category": object_category,
                "object_id": object_id,
                "object": object_name,
                "mode": agent_mode,
                "status": status,
                "provider_name": provider_name or "default",
                "model": config.get("ai_model", "unknown"),
                "automated": False,
                "token_count": token_count,
                "steps_taken": steps_taken,
                "launched_by": launched_by or "ui",
                "chat_session_id": chat_session_id or "",
            }
            if result_dict:
                event["result"] = result_dict
            if error_msg:
                event["error"] = error_msg[:2000]
            if user_context:
                event["user_context"] = user_context

            # Audit-dashboard top-level fields — see enrich_agent_event_for_audit.
            enrich_agent_event_for_audit(
                event,
                result_dict=result_dict,
                user=_request_user,
                automated=False,
                duration_ms=int((time.time() - _run_start_time[0]) * 1000),
            )

            target = svc.indexes[tenant_summary_idx]
            target.submit(
                event=json.dumps(event),
                source="trackme:ai_agent:feed_lifecycle",
                sourcetype=sourcetype,
                host=server_name,
            )
            logger.info(f"Indexed Feed Lifecycle Advisor event: job={job_id}, mode={agent_mode}, status={status}, token_count={token_count}")
        except Exception as idx_e:
            # Audit event lost permanently (no retry path).  Use ERROR
            # so audit-pipeline failures surface in error monitoring.
            logger.error(f"Failed to index Feed Lifecycle Advisor event (job={job_id}): {idx_e}")

    # Watchdog coordination — see ``_make_agent_worker_watchdog`` in
    # ``trackme_libs_ai_agents``.  Same SDK-hang safety net the ML
    # Advisor uses; every Agent SDK advisor shares the risk.
    _watchdog_stop, _watchdog_fired, _start_watchdog = _agents_module._make_agent_worker_watchdog(
        advisor_label="Feed Lifecycle Advisor",
        service=system_service,
        job_id=job_id,
        mode=mode,
        run_start_time_holder=_run_start_time,
        update_agent_job_fn=lambda status, *, error=None: _update_agent_job(
            system_service, job_id, status, error=error
        ),
        index_agent_event_fn=lambda result_dict, status, *, error_msg=None: _index_agent_event(
            agent_service, result_dict, mode, status, error_msg=error_msg
        ),
        automated=False,
    )

    def _worker():
        try:
            _run_start_time[0] = time.time()  # capture INSIDE worker — see _run_start_time comment above
            _start_watchdog()
            result, token_count, steps_taken = asyncio.run(
                asyncio.wait_for(
                    _run_feed_lifecycle_agent(
                        agent_service, model, config, tenant_id, component,
                        object_id, object_name, mode, user_context=user_context,
                        server_name=server_name, job_id=job_id,
                        wizard_payload=wizard_payload,
                    ),
                    timeout=_agents_module._resolve_hard_timeout_sec(mode),
                )
            )
            if _watchdog_fired.is_set():
                logger.warning(
                    f"Feed Lifecycle Advisor worker returned successfully "
                    f"AFTER watchdog abort (job={job_id}); preserving "
                    f"the watchdog's error state — discarding late "
                    f"result."
                )
                return
            result_dict = result.model_dump() if result else {"summary": "Agent completed without structured output"}
            _update_agent_job(system_service, job_id, "complete", result=result_dict)
            _index_agent_event(agent_service, result_dict, mode, "success",
                               token_count=token_count, steps_taken=steps_taken)

        except Exception as e:
            error_str = format_agent_error_chain(e)

            # Hard timeout fired (see ``_resolve_hard_timeout_sec``).
            # Almost always an SDK hang inside parallel-tool aggregation
            # or structured-output extraction — the watchdog (above)
            # is the production-observed backstop when
            # ``asyncio.wait_for`` fails to surface the hang.
            if isinstance(e, asyncio.TimeoutError):
                if _watchdog_fired.is_set():
                    return  # watchdog already wrote the error
                budget_s = _agents_module._resolve_hard_timeout_sec(mode)
                elapsed_s = int(time.time() - _run_start_time[0])
                timeout_msg = (
                    f"Agent run exceeded {budget_s}s "
                    f"(elapsed: {elapsed_s}s, mode={mode}) — likely "
                    f"SDK hang in tool-aggregation or structured-"
                    f"output extraction"
                )
                logger.error(
                    f"Feed Lifecycle Advisor agent TIMEOUT (job={job_id}, "
                    f"mode={mode}, elapsed={elapsed_s}s): {timeout_msg}"
                )
                _update_agent_job(system_service, job_id, "error", error=timeout_msg)
                _index_agent_event(agent_service, None, mode, "error", error_msg=timeout_msg)
                return  # ``finally`` still runs → _release_agent_slot fires

            is_tool_result_bug = _is_tool_result_bug(e)

            if _watchdog_fired.is_set():
                return  # watchdog already wrote the error
            if is_tool_result_bug:
                # Terminal failure path — retries are exhausted, possibly
                # partial writes have been applied.  Use ERROR.
                logger.error(
                    f"Feed Lifecycle Advisor hit SDK tool_result bug (job={job_id}): "
                    f"partial actions may have been applied."
                )
                partial_result = {
                    "entity_status": "unknown",
                    "summary": (
                        "The AI agent encountered a known SDK error (tool_use/tool_result mismatch) "
                        "during execution. The agent may have completed some actions before the error. "
                        "Please check the entity configuration to verify what changes were applied, "
                        "and re-run the analysis if needed."
                    ),
                    "recommendations": [
                        {
                            "field": "n/a",
                            "current_value": "n/a",
                            "recommended_value": "n/a",
                            "rationale": (
                                "Re-run the Feed Lifecycle Advisor in inspect mode to verify the "
                                "current state and confirm which actions (if any) were applied."
                            ),
                        }
                    ],
                    "actions_taken": [],
                    "reasoning_trace": f"Agent execution interrupted by SDK error: {error_str[:300]}",
                    "_partial_result": True,
                }
                _update_agent_job(system_service, job_id, "complete", result=partial_result)
                _index_agent_event(agent_service, partial_result, mode, "partial_error", error_msg=error_str)
            else:
                logger.error(f"Feed Lifecycle Advisor error (job={job_id}): {e}", exc_info=True)
                _update_agent_job(system_service, job_id, "error", error=error_str)
                _index_agent_event(agent_service, None, mode, "error", error_msg=error_str)

        finally:
            _watchdog_stop.set()
            _release_agent_slot(job_id)

    thread = threading.Thread(target=_worker, daemon=True, name=f"feed_lifecycle_{job_id[:8]}")
    thread.start()

    return {"job_id": job_id, "status": "running"}


# ---------------------------------------------------------------------------
# Automated Entry Point (streaming command)
# ---------------------------------------------------------------------------


def start_feed_lifecycle_advisor_from_search_context(
    service,
    session_key,
    splunkd_uri,
    server_name,
    tenant_id,
    component,
    object_id,
    object_name,
    mode="inspect",
    provider_name=None,
    vtenant_account=None,
):
    """
    Start the Feed Lifecycle Advisor agent from a streaming command context.

    Same as start_feed_lifecycle_advisor_async() but accepts streaming command
    context (service, session_key, splunkd_uri, server_name) instead of request_info.
    Used by the automated feedlifecycle scheduled backend.

    Returns:
        dict with {job_id, status} or raises exception
    """
    model, config = get_sdk_model(service, provider_name=provider_name)

    with _active_agents_lock:
        if _agents_module._active_agents >= _MAX_CONCURRENT_AGENTS_DEFAULT:
            raise RuntimeError(
                f"AI agent at maximum capacity ({_MAX_CONCURRENT_AGENTS_DEFAULT} concurrent). "
                "Please try again later."
            )
        _agents_module._active_agents += 1

    try:
        job_id = _create_agent_job(service)

        agent_service = client.connect(
            owner="nobody",
            app="trackme",
            port=service.port,
            token=session_key,
            timeout=600,
        )
    except Exception:
        with _active_agents_lock:
            _agents_module._active_agents = max(0, _agents_module._active_agents - 1)
        raise

    # End-to-end run timer for the audit dashboard.
    # Mutable holder so the thread's _worker() can stamp the start time AFTER
    # the worker actually begins running — this excludes thread spawn /
    # scheduling overhead from duration_ms and keeps interactive vs
    # automated runs comparable.  See enrich_agent_event_for_audit.
    _run_start_time = [time.time()]

    def _index_agent_event(svc, result_dict, agent_mode, status, error_msg=None, token_count=0, steps_taken=0):
        try:
            from trackme_libs import trackme_idx_for_tenant
            try:
                idx_settings = trackme_idx_for_tenant(session_key, splunkd_uri, tenant_id)
                tenant_summary_idx = idx_settings.get("trackme_summary_idx", "trackme_summary")
            except Exception:
                tenant_summary_idx = "trackme_summary"

            sourcetype = f"trackme:ai_agent:feed_lifecycle_advisor:{agent_mode}"
            object_category = f"splk-{component}"
            event = {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "component": component,
                "object_category": object_category,
                "object_id": object_id,
                "object": object_name,
                "mode": agent_mode,
                "status": status,
                "provider_name": provider_name or "default",
                "model": config.get("ai_model", "unknown"),
                "automated": True,
                # Set on every scheduled-path emission so the
                # ``audit-ai-advisor-scheduled`` dashboard can
                # attribute the run to the in-product automation
                # rather than falling back to the function default
                # of ``"ui"``.
                "launched_by": "automation",
                "token_count": token_count,
                "steps_taken": steps_taken,
            }
            if result_dict:
                event["result"] = result_dict
            if error_msg:
                event["error"] = error_msg[:2000]

            # Audit-dashboard top-level fields.
            enrich_agent_event_for_audit(
                event,
                result_dict=result_dict,
                user=None,
                automated=True,
                duration_ms=int((time.time() - _run_start_time[0]) * 1000),
            )

            target = svc.indexes[tenant_summary_idx]
            target.submit(
                event=json.dumps(event),
                source="trackme:ai_agent:feed_lifecycle:automated",
                sourcetype=sourcetype,
                host=server_name,
            )
            logger.info(f"Indexed automated Feed Lifecycle Advisor event: job={job_id}, mode={agent_mode}, status={status}, token_count={token_count}")
        except Exception as idx_e:
            # Audit event lost permanently (no retry path).  Use ERROR.
            logger.error(f"Failed to index automated Feed Lifecycle Advisor event (job={job_id}): {idx_e}")

    # Watchdog coordination — see ``_make_agent_worker_watchdog`` in
    # ``trackme_libs_ai_agents``.  Automated/scheduled variant of
    # the same SDK-hang safety net used in the interactive UI path.
    _watchdog_stop, _watchdog_fired, _start_watchdog = _agents_module._make_agent_worker_watchdog(
        advisor_label="Feed Lifecycle Advisor",
        service=service,
        job_id=job_id,
        mode=mode,
        run_start_time_holder=_run_start_time,
        update_agent_job_fn=lambda status, *, error=None: _update_agent_job(
            service, job_id, status, error=error
        ),
        index_agent_event_fn=lambda result_dict, status, *, error_msg=None: _index_agent_event(
            agent_service, result_dict, mode, status, error_msg=error_msg
        ),
        automated=True,
    )

    def _worker():
        try:
            _run_start_time[0] = time.time()  # capture INSIDE worker — see _run_start_time comment above
            _start_watchdog()
            result, token_count, steps_taken = asyncio.run(
                asyncio.wait_for(
                    _run_feed_lifecycle_agent(
                        agent_service, model, config, tenant_id, component,
                        object_id, object_name, mode,
                        automated=True, vtenant_account=vtenant_account or {},
                        server_name=server_name, job_id=job_id,
                    ),
                    timeout=_agents_module._resolve_hard_timeout_sec(mode),
                )
            )
            if _watchdog_fired.is_set():
                logger.warning(
                    f"Feed Lifecycle Advisor automated worker returned "
                    f"successfully AFTER watchdog abort (job={job_id}); "
                    f"preserving the watchdog's error state — "
                    f"discarding late result."
                )
                return
            result_dict = result.model_dump() if result else {"summary": "Agent completed without structured output"}
            _update_agent_job(service, job_id, "complete", result=result_dict)
            _index_agent_event(agent_service, result_dict, mode, "success",
                               token_count=token_count, steps_taken=steps_taken)

        except Exception as e:
            error_str = format_agent_error_chain(e)

            # Hard timeout fired (see ``_resolve_hard_timeout_sec``).
            # Almost always an SDK hang inside parallel-tool aggregation
            # or structured-output extraction — the watchdog above is
            # the production-observed backstop when ``asyncio.wait_for``
            # fails to surface the hang.
            if isinstance(e, asyncio.TimeoutError):
                if _watchdog_fired.is_set():
                    return  # watchdog already wrote the error
                budget_s = _agents_module._resolve_hard_timeout_sec(mode)
                elapsed_s = int(time.time() - _run_start_time[0])
                timeout_msg = (
                    f"Agent run exceeded {budget_s}s "
                    f"(elapsed: {elapsed_s}s, mode={mode}) — likely "
                    f"SDK hang in tool-aggregation or structured-"
                    f"output extraction"
                )
                logger.error(
                    f"Feed Lifecycle Advisor agent TIMEOUT (job={job_id}, "
                    f"mode={mode}, elapsed={elapsed_s}s): {timeout_msg}"
                )
                _update_agent_job(service, job_id, "error", error=timeout_msg)
                _index_agent_event(agent_service, None, mode, "error", error_msg=timeout_msg)
                return  # ``finally`` still runs → _release_agent_slot fires

            is_tool_result_bug = _is_tool_result_bug(e)

            if _watchdog_fired.is_set():
                return  # watchdog already wrote the error
            if is_tool_result_bug:
                # Terminal failure in the automated path with possible
                # partial writes.  Use ERROR.
                logger.error(
                    f"Feed Lifecycle Advisor hit SDK tool_result bug (job={job_id}): "
                    f"automated run, partial actions may have been applied."
                )
                partial_result = {
                    "entity_status": "unknown",
                    "summary": "Automated inspection interrupted by SDK error. Partial actions may have been applied.",
                    "recommendations": [],
                    "actions_taken": [],
                    "reasoning_trace": f"Agent interrupted by SDK error: {error_str[:300]}",
                    "_partial_result": True,
                }
                _update_agent_job(service, job_id, "complete", result=partial_result)
                _index_agent_event(agent_service, partial_result, mode, "partial_error", error_msg=error_str)
            else:
                logger.error(f"Feed Lifecycle Advisor automated error (job={job_id}): {e}", exc_info=True)
                _update_agent_job(service, job_id, "error", error=error_str)
                _index_agent_event(agent_service, None, mode, "error", error_msg=error_str)

        finally:
            _watchdog_stop.set()
            _release_agent_slot(job_id)

    thread = threading.Thread(target=_worker, daemon=True, name=f"feed_lifecycle_auto_{job_id[:8]}")
    thread.start()

    return {"job_id": job_id, "status": "running"}

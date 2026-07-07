"""
TrackMe AI Agents — Component Health Advisor

Provides the Component Health Advisor agent and supporting orchestration for
WLK (WorkLoad Knowledge) and MHM (Metric Host Monitoring) entities (FQM has its
own dedicated advisor — see trackme_libs_ai_fqm_advisor.py):

- Component-specific system prompts: WLK, MHM
- Pydantic output schema: ComponentHealthAdvisorResult
- start_component_health_advisor_async()           — REST / interactive invocation
- start_component_health_advisor_from_search_context() — streaming command / automated

NOTE: Splunk Agent SDK imports (splunklib.ai.*) are deferred to function scope.
The AI SDK requires Python 3.13+ and raises ImportError on 3.9.
"""

import asyncio
import json
import logging
import os
import threading
import time

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
logger = logging.getLogger("trackme.rest.ai.component_health")

# ---------------------------------------------------------------------------
# Pydantic Output Schema
# ---------------------------------------------------------------------------


class ComponentHealthRecommendation(BaseModel):
    """A single recommendation produced by the Component Health Advisor."""

    field: str = Field(
        description=(
            "Configuration field or dimension this recommendation addresses. "
            "Examples: 'metric_name threshold', 'monitored_state', 'priority', "
            "'metric_max_lag_allowed', 'skipped_pct_last_24h threshold'"
        )
    )
    current_value: str = Field(description="Current value of the field")
    recommended_value: str = Field(description="Recommended new value")
    rationale: str = Field(
        description=(
            "Clear explanation of why this change is recommended, citing observed data"
        )
    )


class ComponentHealthAdvisorResult(BaseModel):
    """Structured output from the Component Health Advisor agent."""

    entity_status: str = Field(
        description=(
            "Overall entity health assessment: "
            "'healthy' (configuration is appropriate for the entity's behaviour), "
            "'needs_tuning' (thresholds or settings need adjustment), "
            "'stale' (no recent activity — entity may be inactive or orphaned), "
            "'decommission_candidate' (entity should be disabled or removed)"
        )
    )
    summary: str = Field(description="2-3 sentence executive summary of the analysis")
    recommendations: list[ComponentHealthRecommendation] = Field(
        default_factory=list,
        description="Ordered list of recommendations (highest priority first)",
    )
    actions_taken: list[AgentAction] = Field(
        default_factory=list,
        description=(
            "Actions executed via write tools in act mode. Each entry records the "
            "tool name, status, description, and a short result summary. "
            "In act mode this array MUST NOT be empty — populate it from actual tool call results."
        ),
    )
    evidence_log_samples: list[str] = Field(
        default_factory=list,
        description=(
            "Verbatim raw log lines that provide direct evidence for the "
            "diagnosis. Populate this field whenever the advisor's reasoning "
            "depends on specific log content — most commonly when "
            "``get_wlk_execution_errors`` returned scheduler error entries "
            "that the recommendation set hinges on. Each entry SHOULD be a "
            "single-line string, copy-pasted verbatim from the tool's "
            "``errors[].errmsg`` (or ``unique_error_messages[].message``) "
            "field — the same content the operator would see by running "
            "the scheduler-error SPL directly. Include 1-3 representative "
            "lines: usually the highest-occurrence unique error message + "
            "1-2 distinct variants if the entity emits more than one kind "
            "of error. Empty by design when the diagnosis doesn't rest on "
            "log content (e.g. pure threshold-tuning scenarios, "
            "stale-entity / decommission recommendations, MHM entities). "
            "The operator UI renders this as a code-block Evidence "
            "section so the operator can map the advisor's claim back to "
            "the canonical source — no need to re-run the SPL by hand to "
            "trust the diagnosis."
        ),
    )
    reasoning_trace: str = Field(
        default="",
        description="Step-by-step reasoning explanation for transparency",
    )

    @classmethod
    def model_json_schema(cls, **kwargs):
        """Return a flat ``$ref``/``$defs``-free JSON Schema — see MLAdvisorResult."""
        return inline_schema_refs(super().model_json_schema(**kwargs))


# ---------------------------------------------------------------------------
# System Prompts — one per component
# ---------------------------------------------------------------------------

WLK_HEALTH_ADVISOR_SYSTEM_PROMPT = """You are TrackMe's WorkLoad Knowledge (WLK) Health Advisor — an AI agent that analyzes
scheduled search entities monitored by TrackMe's WLK component, identifies configuration issues
that cause false alerts or miss real execution problems, and recommends or applies corrective changes.

## YOUR MISSION

Review a WLK entity's execution history, current thresholds, and monitoring configuration.
Determine whether the configuration accurately reflects the search's real-world behaviour,
and recommend or apply changes that eliminate noise and surface genuine issues.

## CONTEXT

TrackMe WLK monitors Splunk saved searches for execution health. Each WLK entity represents one
scheduled search. Key monitored metrics:

- **skipped_pct_last_4h** / **skipped_pct_last_24h** (percentage): Fraction of scheduled execution
  windows where Splunk skipped the search (e.g. system under load). High skip rate usually indicates
  Splunk scheduler contention or an overly aggressive schedule cadence.
- **count_errors_last_4h** / **count_errors_last_24h** (integer): Number of execution errors reported
  by Splunk for the search. Errors indicate broken SPL, missing lookups, or permissions issues.
  These two fields are AGGREGATED COUNTS only — they tell you that errors are happening, not WHY.
  For root-cause diagnosis you MUST call `get_wlk_execution_errors`, which returns the actual error
  messages from Splunk's `index=_internal sourcetype=scheduler` logs (mirrors the SPL the smart
  status investigation uses). The same chronic error typically repeats every scheduled run, so the
  deduplicated `unique_error_messages` field points straight at the root cause.
- **sec_since_lastexec** (seconds): Seconds elapsed since the search last ran. A very large value
  means the search may be disabled or its schedule has been altered.
- **monitored_state** (enabled/disabled): Whether the entity is actively monitored.
- **priority** (critical/high/medium/low/pending): Alert severity weight.
- **Thresholds**: Dynamic per-entity rules stored in KV Store. WLK supports a `default` threshold
  object that applies tenant-wide when no entity-specific threshold exists. Threshold conditions
  use operator+value pairs (e.g. `skipped_pct_last_24h > 20`).
- **orphan status**: A search reported as orphan no longer exists in Splunk's scheduled search list.
  Orphan entities should be disabled unless the search is expected to be recreated.

## REASONING FRAMEWORK

Follow this 5-step process for every analysis:

1. **UNDERSTAND THE ENTITY**: Call `get_wlk_entity_context` to get the full configuration snapshot —
   current thresholds, monitoring state, priority, orphan flag, last execution time, tenant defaults.

2. **ANALYSE EXECUTION HISTORY**: Call `get_wlk_execution_history` to review the last 30 days of
   execution metrics:
   - What is the typical skip percentage (p50/p75/p95)?
   - Are errors isolated incidents or chronic?
   - When did the search last execute (is it effectively dead)?
   - Are there periodic patterns (e.g. high skip rate every Monday morning)?

3. **DIAGNOSE EXECUTION ERRORS** (conditional): If ANY of the following holds, ALSO call
   `get_wlk_execution_errors` to retrieve the raw scheduler error log entries — `count_errors_last_24h`
   alone is just an aggregate count, not a diagnosis:
   - `count_errors_last_24h > 0` (from `get_wlk_entity_context`)
   - `execution_errors_detected` appears in `anomaly_reasons`
   - `max_errors > 0` in any row from `get_wlk_execution_history`

   The tool returns deduplicated `unique_error_messages` sorted by occurrence count — the top
   entry is almost always the chronic root cause. Read the message verbatim and identify the
   class of failure:
   - "Could not construct lookup '<name>'" → SPL references a lookup that does not exist
     (commonly a typo: `uc003_ations` vs `uc003_actions`). The fix is in the saved search SPL,
     NOT in the threshold.
   - "Unknown sid" / "Search not executed" → transient scheduler / dispatch issue.
   - "permission denied" / "does not have permissions" → RBAC; recommend reviewing the search
     owner's role assignments.
   - Quote the actual error message in your `reasoning_trace` and `recommendations`. Hand-wavy
     advice like "fix the SPL" is a failure — name the specific lookup / command / permission
     that needs correcting.

   **Remote account routing** — the tool automatically dispatches the SPL through
   `splunkremotesearch` when the entity is backed by a non-local account (same as the smart
   status investigation). The result includes `search_dispatch: "local" | "remote"` and the
   `account` name so you can confirm. WLK entities monitoring scheduled searches on a remote
   SH will have their errors retrieved from THAT SH's `_internal` index, not the local one —
   you don't need to do anything special; the tool handles it transparently. If the result
   shows `search_dispatch="remote"` and `errors` is empty, the remote dispatch may have
   failed (network / token / RBAC on the remote account); inspect the `error` field for
   details and consider asking the operator to verify the remote account via the Remote
   Accounts page before recommending further action.

   When `execution_errors_detected` is in anomaly_reasons but the tool returns an empty list,
   the breach is older than the default `-7d` window — widen `earliest` to `-30d` and retry.

4. **ASSESS THRESHOLD FITNESS**: Call `get_wlk_threshold_breach_history` to understand how often
   configured thresholds have triggered:
   - Are thresholds too tight (firing on normal transient skips)?
   - Are thresholds too loose (missing sustained degradation)?
   - Does the entity rely solely on a tenant-wide default — should it have its own thresholds?

   **HARD RULE — TrackMe threshold semantics.** Before proposing ANY change to a threshold's
   `operator` or `condition_true`, apply this formula:

       match = op_func(metric_value, threshold_value)
       Alert fires if: (condition_true AND NOT match) OR (NOT condition_true AND match)

   `condition_true=True` means "this is the HEALTHY condition I expect to hold — alert me when
   it breaks." It does NOT mean "alert when the operator evaluates to true."

   For WLK metrics, the canonical patterns are:

   | Intent | operator | condition_true | Example | Alert fires when |
   |---|---|---|---|---|
   | Expect skip% BELOW X; alert when HIGH | `<` | `True` | 20 | skipped_pct_last_24h >= 20 |
   | Expect zero errors; alert on ANY non-zero | `==` | `True`, value=0 | 0 | count_errors_last_24h != 0 |
   | Expect search to run within X sec; alert when STALE | `<` | `True` | 86400 | sec_since_lastexec >= 86400 |

   Mandatory pre-flip checklist for any `operator` / `condition_true` change:

   1. **Restate** in plain English what healthy condition the current pair encodes.
   2. **Prove** it is logically inverted relative to the metric's semantics.
   3. **Spell out** what the proposed new pair would mean using the same formula.

   A threshold that fires when a metric exceeds its expected range IS working correctly — the
   question is usually whether the threshold *value* needs tuning, not whether the operator
   needs flipping.

5. **COMPARE TO PEERS**: Optionally call `get_wlk_peer_comparison` to benchmark against similar
   searches (same app, similar schedule frequency):
   - Is this entity an outlier in skip rate vs. its peers?
   - What thresholds do well-calibrated peer entities use?

6. **DECIDE AND ACT**:
   - Thresholds too tight for observed skip pattern → loosen with entity-specific thresholds
   - Chronic errors over 7+ days with a clear unique_error_messages root cause → cite the
     specific SPL/lookup/permission issue, recommend the saved-search fix, escalate priority
   - Orphan search (search no longer exists in Splunk) → recommend disabling entity
   - Search with no executions for 14+ days → recommend disabling or investigating
   - Entity relying on tenant default with very different behaviour → add entity-specific thresholds
   - Priority mismatches the search criticality → recommend priority adjustment

## COMMON SCENARIO PATTERNS

### Scenario 1: Threshold Too Tight for Normal Scheduler Behaviour
**Signals**: `skipped_pct_last_24h` threshold fires repeatedly, but p75 of observed skip rate
is below the current threshold. Spikes are transient (a few hours per week).
**Action**: Set entity-specific threshold at ~p95 of observed skip rate plus a 20% buffer.
Example: p95 skip rate = 15% → set threshold at 18-20%.

### Scenario 2: Chronic Execution Errors
**Signals**: `count_errors_last_24h` has been non-zero for 7+ consecutive days. The search is
consistently erroring. No recent clean executions. `execution_errors_detected` is in the
entity's `anomaly_reasons`.
**Action**: This is NOT a threshold-tuning scenario — the threshold is doing its job by
flagging real errors. The fix lives in the saved search SPL.

1. Call `get_wlk_execution_errors` to retrieve the actual error log entries. The
   `unique_error_messages` field gives you the chronic root cause directly (highest
   occurrence count = the repeating failure mode).
2. Quote the specific error message in your `summary` and `reasoning_trace`. Hand-wavy
   phrases like "search definition may need fixing" or "lookup name typo in SPL" are
   FAILURES — you must name the specific lookup / command / permission / macro that's
   broken, and ideally suggest the corrected form when obvious (e.g. a typo:
   `Could not construct lookup 'uc003_ations'` → recommend correcting to the
   intended lookup name in the SPL's `lookup` clause).
3. **Populate `evidence_log_samples`** with 1-3 verbatim raw log lines from the tool's
   `errors[].errmsg` field (or the deduplicated `unique_error_messages[].message`
   field — both contain the canonical text). Pick the highest-occurrence unique
   error message first; if the entity emits more than one kind of error, include
   1-2 distinct variants. The operator UI renders this as an Evidence code block
   so the operator can map your claim back to the canonical source — the
   "show me the actual logs" affordance every triage workflow needs.
   Empty `evidence_log_samples` for execution-error scenarios is a FAILURE — you
   diagnosed from log content, so quote it.
4. Recommend setting `count_errors_last_24h > 0` threshold to catch every error if not
   already present (this catches future regressions even after the current root cause
   is fixed).
5. Escalate priority if not already high — chronic SPL failures on a security /
   compliance / production saved search warrant analyst attention.

In act mode you can apply the priority change (`update_wlk_entity_state_priority`) and
the threshold setting (`add_wlk_threshold` / `update_wlk_threshold`) automatically.
You CANNOT fix the saved search SPL itself — that requires an analyst to edit the
search in Splunk. Make the SPL recommendation clear and actionable in `recommendations`.

### Scenario 3: Orphan Search
**Signals**: `is_orphan = 1` or `orphan_status` indicates the search no longer exists.
The entity is monitoring a search that has been deleted or renamed.
**Action**: Recommend disabling monitoring (`monitored_state = disabled`). Only apply this
in act mode if the entity has been orphaned for 7+ days to avoid false positives from
temporary search recreation.

### Scenario 4: Effectively Dead Search
**Signals**: `sec_since_lastexec` is very large (>7 days). The search exists but has not run.
Could indicate the search is manually disabled in Splunk, or the schedule has been changed to
a very infrequent cadence.
**Action**: Report as stale. Recommend disabling monitoring or adjusting the monitoring window.
In act mode, disable only if last execution was >14 days ago.

### Scenario 5: Monitoring Window Mismatch
**Signals**: The search runs once per day but thresholds evaluate `last_4h` window.
The 4-hour window will almost always show 0 executions, causing spurious alerts.
**Action**: Recommend using `last_24h` metrics for threshold rules to match the search cadence.

### Scenario 6: Priority Mismatch
**Signals**: Entity monitors a critical production search (e.g. stateful alert, threat detection)
but is configured as low or medium priority, or vice versa.
**Action**: Recommend priority adjustment with justification based on search name and app context.

## MODE BEHAVIOR

- **inspect**: Read-only. Gather data, analyze, report findings with specific recommendations.
  Do NOT call any write tools.
- **act**: You MUST follow this EXACT sequence:
  1. FIRST: Call read tools to analyze (steps 1-5 of the reasoning framework).
     From `get_wlk_entity_context`, read `anomaly_reason` and current metrics.
     These fields MUST drive every write decision.
     **EXCEPTION**: If the initial message contains a **PRIOR INSPECTION RESULTS** block
     from a recent inspect run, you MAY use it directly. In that case, call
     `get_wlk_entity_context` ONCE to confirm the entity state has not changed,
     then skip straight to step 2.
  2. THEN: Call the write tools that DIRECTLY address the identified anomaly reasons:
     - Thresholds too tight or missing → `add_wlk_threshold` or `update_wlk_threshold`
     - Redundant or counterproductive thresholds → `delete_wlk_threshold`
     - Priority mismatch → `update_wlk_entity_state_priority`
     Write tools targeting the root anomaly reasons are MANDATORY before producing output.
  3. LAST: Only after write tools have returned their results, produce your structured output
     with actions_taken populated from the actual tool responses.

  CRITICAL: If you are in act mode and you have not called any write tools yet, you are NOT done.
  Do NOT produce your final structured output until write tools have been called.
  An empty actions_taken array in act mode is a failure.

## AUDIT REASON DISCIPLINE

Every write tool you call takes a `reason: str` parameter. Whatever you pass
lands in the per-entity "Audit changes" panel as `[AI Agent] <reason>` —
teammates reviewing the audit timeline weeks later see only this. Make `reason`
count:

- **Cite the field, the from/to values, and the operational trigger.** Bad:
  `"updated"`. Good: `"Loosened skipped_pct threshold from 5% to 15% on
  this scheduled-search entity after observing recurring scheduler-pressure
  spikes during 02:00 UTC backup window."`
- **Mirror the user's intent** when supplied via `user_context` — the audit
  should show why the operator asked for the change, not just what the agent
  computed.
- **Never use empty / generic strings** like `""` / `"update"` /
  `"API update"`. They signal the reason wasn't thought through and degrade
  the audit log's value for everyone.

## CONSTRAINTS

- NEVER disable an entity without stating explicit data evidence (e.g. "orphan for 10 days", "no execution for 16 days")
- NEVER tighten thresholds — only loosen them or leave them unchanged (unless adding a threshold
  that previously did not exist, in which case calibrate conservatively above p95)
- NEVER take action on a search that appears temporarily disabled unless absence extends >14 days
- Always explain your reasoning in the reasoning_trace field
- Limit write tool calls to the minimum necessary to address the identified issues
"""

MHM_HEALTH_ADVISOR_SYSTEM_PROMPT = """You are TrackMe's Metric Host Monitoring (MHM) Health Advisor — an AI agent that analyzes
MHM entities (hosts sending metric data), identifies lag threshold misconfigurations, and
recommends or applies corrective changes to eliminate false alerts.

## YOUR MISSION

Review an MHM entity's metric lag history, current lag threshold, and monitoring configuration.
Determine whether the `metric_max_lag_allowed` setting matches the host's actual metric emission
cadence, and recommend or apply changes that align the threshold with reality.

## CONTEXT

TrackMe MHM monitors hosts that send Splunk metrics. Each MHM entity represents a host. Key
monitored aspects:

- **metric_max_lag_allowed** (seconds): The maximum acceptable time since the host last sent
  metrics in a given category. If Splunk has not received metrics within this window, the entity
  goes RED. This is the PRIMARY tuning lever for MHM — almost all false alerts come from this
  value being set too tight for the host's actual emission frequency.
  Common examples:
    - A host sending metrics every 10 minutes needs metric_max_lag_allowed >= 900s (15 min buffer)
    - A host sending metrics every hour needs metric_max_lag_allowed >= 4500s (1.25 hour buffer)
    - An infrastructure host with 5-minute metric collection needs metric_max_lag_allowed >= 450s
- **metric_details**: JSON array describing per-category metric status. Each entry shows
  the metric category, when it was last seen, and current lag. Review this to identify if
  specific categories have structurally higher lag than others (heterogeneous emission cadences).
- **monitored_state** (enabled/disabled): Whether the entity is actively monitored.
- **priority** (critical/high/medium/low/pending): Alert severity weight.
- **lagging_classes**: Named lag threshold rule sets. Some tenants use lagging classes to apply
  shared thresholds to groups of hosts. Check whether the entity uses a lagging class or has an
  individual `metric_max_lag_allowed` override.

## KEY DIFFERENCE FROM FLX/WLK

MHM has NO per-entity dynamic threshold system. The only threshold-equivalent levers are:
- `metric_max_lag_allowed` (per-entity or per-tenant default)
- Lagging classes (shared named rule sets)

There are no `add_mhm_threshold`, `update_mhm_threshold`, or `delete_mhm_threshold` tools.
The ONLY write tools available are:
- `update_mhm_metric_max_lag` — set a new metric_max_lag_allowed value
- `update_mhm_entity_state_priority` — change monitored_state or priority

Do NOT attempt to call threshold management tools — they do not exist for MHM.

## REASONING FRAMEWORK

Follow this 5-step process for every analysis:

1. **UNDERSTAND THE HOST**: Call `get_mhm_entity_context` to get the full configuration snapshot —
   current `metric_max_lag_allowed`, monitored state, priority, metric_details categories,
   lagging class assignment, tenant defaults.

2. **CHECK METRIC LAG HISTORY**: Call `get_mhm_lag_history` to review the last 30 days of
   lag patterns across all metric categories:
   - What is the typical maximum lag observed (p50/p75/p95)?
   - Are there periodic spikes (maintenance windows, nightly collection gaps)?
   - Has the host stopped sending metrics entirely for extended periods?
   - Do different categories have structurally different lag patterns?

3. **ASSESS LAG THRESHOLD FITNESS**: Call `get_mhm_alert_flip_history` to understand false
   positive rate:
   - How many RED transitions in the last 30 days?
   - Are RED states correlated with actual collection gaps, or are they threshold mismatches?
   - What is the typical gap between metric collection events?

4. **COMPARE TO PEER HOSTS**: Optionally call `get_mhm_peer_comparison` for context:
   - What `metric_max_lag_allowed` do similar hosts (same OS/role/tenant) use?
   - Is this host's emission cadence consistent with its peers?

5. **DECIDE AND ACT**:
   - `metric_max_lag_allowed` too tight for emission cadence → increase to ~1.5x p95 observed lag
   - Host showing 7+ days of no metrics in any category → stale/decommission candidate
   - Specific categories with higher structural lag → document but note no per-category threshold exists
   - Priority does not match host criticality → recommend adjustment
   - Lag threshold appropriate and host healthy → report 'healthy'

## COMMON SCENARIO PATTERNS

### Scenario 1: Emission Cadence Mismatch (Most Common)
**Signals**: Host emits metrics every 10 minutes (600s cadence). `metric_max_lag_allowed` is
300s (5 min). Entity regularly transitions RED for 10-minute periods every hour.
This is a pure threshold misconfiguration — no actual collection problem.
**Action**: Set `metric_max_lag_allowed` to ~900s (1.5x the 600s cadence).
Formula: recommended = ceil(p95_lag * 1.5), minimum = p95_lag + 60.

### Scenario 2: Nightly / Maintenance Collection Gap
**Signals**: Lag history shows regular large gaps (e.g. 2-4 hours) every night between 2:00-6:00.
This is a planned maintenance window or reduced collection period.
`metric_max_lag_allowed` is too tight to cover these gaps.
**Action**: Set `metric_max_lag_allowed` to cover the largest regular gap plus a 20% buffer.
Example: 4-hour gap = 14400s → recommend 18000s (5 hours).

### Scenario 3: Stale Host
**Signals**: `metric_details` shows no metrics received in any category for 7+ consecutive days.
The host may have been decommissioned, renamed, or stopped sending metrics.
**Action**: Recommend disabling monitoring. Only apply in act mode if silent for 14+ days.

### Scenario 4: Category-Level Lag Heterogeneity
**Signals**: `metric_details` shows some categories with lag ~120s (healthy) and others with
structural lag of ~3600s. The current `metric_max_lag_allowed` is set for the fast categories,
causing false RED states from the slow categories.
**Action**: Set `metric_max_lag_allowed` to accommodate the slowest category with a buffer.
Note in reasoning that this means the fast categories will have looser monitoring — this is
the correct trade-off given the single-threshold MHM architecture.

### Scenario 5: Priority Mismatch
**Signals**: Host is a critical production server (database primary, load balancer, security sensor)
but is set to low or medium priority, or vice versa.
**Action**: Recommend priority adjustment with justification based on host name and context.

## MODE BEHAVIOR

- **inspect**: Read-only. Gather data, analyze, report findings with specific recommendations.
  Do NOT call any write tools.
- **act**: You MUST follow this EXACT sequence:
  1. FIRST: Call read tools to analyze (steps 1-5 of the reasoning framework).
     From `get_mhm_entity_context`, read `anomaly_reason` and current lag configuration.
     These fields MUST drive every write decision.
     **EXCEPTION**: If the initial message contains a **PRIOR INSPECTION RESULTS** block
     from a recent inspect run, call `get_mhm_entity_context` ONCE to confirm state is
     unchanged, then proceed to write tools.
  2. THEN: Call write tools that DIRECTLY address the identified issues:
     - Lag threshold too tight → `update_mhm_metric_max_lag`
     - Priority or monitoring state change → `update_mhm_entity_state_priority`
  3. LAST: Produce structured output with actions_taken from actual tool responses.

  CRITICAL: In act mode you MUST call write tools before producing final output.
  An empty actions_taken array in act mode is a failure.
  Remember: there are ONLY two write tools for MHM. Do not attempt to call threshold
  management tools — they do not exist for this component.

## AUDIT REASON DISCIPLINE

Every write tool you call takes a `reason: str` parameter. Whatever you pass
lands in the per-entity "Audit changes" panel as `[AI Agent] <reason>` —
teammates reviewing the audit timeline weeks later see only this. Make `reason`
count:

- **Cite the field, the from/to values, and the operational trigger.** Bad:
  `"updated"`. Good: `"Increased metric_max_lag_allowed from 60s to 180s
  after observing sustained p95=145s caused by collector backpressure on
  PROD-2 — buffer = p95 + 60s per safety rule."`
- **Mirror the user's intent** when supplied via `user_context` — the audit
  should show why the operator asked for the change, not just what the agent
  computed.
- **Never use empty / generic strings** like `""` / `"update"` /
  `"API update"`. They signal the reason wasn't thought through and degrade
  the audit log's value for everyone.

## CONSTRAINTS

- NEVER decrease `metric_max_lag_allowed` — only increase or leave unchanged
- NEVER disable an entity without stating explicit data evidence (e.g. "no metrics for 16 days")
- When increasing `metric_max_lag_allowed`, always apply a buffer above p95 observed lag
  (minimum 1.5x the emission cadence, or p95 + 60s, whichever is larger)
- Always explain your reasoning in the reasoning_trace field
- Limit write tool calls to the minimum necessary
"""

# Dispatch map — keyed by component name
_SYSTEM_PROMPTS = {
    "wlk": WLK_HEALTH_ADVISOR_SYSTEM_PROMPT,
    "mhm": MHM_HEALTH_ADVISOR_SYSTEM_PROMPT,
}

# Human-readable component labels used in log messages
_COMPONENT_LABELS = {
    "wlk": "WLK",
    "mhm": "MHM",
}


def _get_system_prompt(component):
    """
    Return the component-specific system prompt for the Component Health Advisor.

    Args:
        component: One of "wlk", "mhm"

    Returns:
        System prompt string

    Raises:
        ValueError: If component is not supported
    """
    prompt = _SYSTEM_PROMPTS.get(component)
    if prompt is None:
        raise ValueError(
            f"Component Health Advisor does not support component '{component}'. "
            f"Supported components: {sorted(_SYSTEM_PROMPTS.keys())}"
        )
    return prompt


# ---------------------------------------------------------------------------
# Prior Inspect Result Lookup
# ---------------------------------------------------------------------------


def _get_recent_inspect_result(service, tenant_id, component, object_id, max_age_minutes=30):
    """
    Retrieve the most recent successful Component Health Advisor inspect result
    from the summary index.

    Args:
        service: Splunk service connection
        tenant_id: Tenant identifier
        component: Component type ("wlk", "mhm")
        object_id: Entity _key hash
        max_age_minutes: Maximum age in minutes for a result to be considered recent

    Returns:
        dict with prior result, or None if not found
    """
    from trackme_libs_ai import get_recent_agent_inspect_result

    sourcetype = f"trackme:ai_agent:component_health_advisor:{component}:inspect"
    return get_recent_agent_inspect_result(
        service,
        tenant_id,
        object_id,
        sourcetype=sourcetype,
        max_age_minutes=max_age_minutes,
    )


# ---------------------------------------------------------------------------
# Agent Runner
# ---------------------------------------------------------------------------


def _vtenant_allows_decommission(vtenant_account, component):
    """
    Return True if the tenant allows automated decommissioning actions.

    Reads the unified ``ai_components_advisor_allow_decommission`` field
    (replaces the per-component ``ai_wlkadvisor_allow_decommission`` /
    ``ai_mhmadvisor_allow_decommission``).  The ``component`` argument is
    retained for backward compatibility of the call sites but is no
    longer used to pick a component-specific field.

    Args:
        vtenant_account: Tenant configuration dict
        component: Component type ("wlk", "mhm") — kept for call-site
            compatibility; the unified field applies regardless.

    Returns:
        bool
    """
    return vtenant_account.get("ai_components_advisor_allow_decommission", "0") == "1"


async def _run_component_health_agent(
    service, model, config, tenant_id, component, object_id, object_name, mode,
    user_context=None, automated=False, vtenant_account=None, job_id=None, server_name=None,):
    """
    Run the Component Health Advisor agent asynchronously.

    Args:
        service: Splunk service connection
        model: SDK model (OpenAIModel or AnthropicModel)
        config: AI provider configuration dict
        tenant_id: Tenant identifier
        component: Component type — one of "wlk", "mhm"
        object_id: Entity _key hash in KV Store
        object_name: Entity name
        mode: "inspect" (read-only) or "act" (apply changes)
        user_context: Optional free-text instructions from the user
        automated: True when invoked from a scheduled search (vs interactive)
        vtenant_account: Tenant configuration dict (for decommission guard)

    Returns:
        Tuple of (ComponentHealthAdvisorResult, token_count, steps_taken)
    """
    # Pin the shared agent infrastructure's logger to this advisor for
    # the duration of this async context.  Without this, tool_middleware
    # lines from trackme_libs_ai_agents.py route to the default
    # (ml_advisor) log file even when this advisor is the one running.
    set_current_advisor_logger("trackme.rest.ai.component_health")

    from splunklib.ai.agent import Agent
    from splunklib.ai.messages import HumanMessage
    from splunklib.ai.hooks import before_model
    from splunklib.ai.limits import AgentLimits
    from splunklib.ai.tool_settings import ToolSettings, LocalToolSettings, ToolAllowlist

    model_name = config.get("ai_model", "unknown")
    provider_type = config.get("ai_provider", "unknown")
    provider_name_log = config.get("provider_name", "unknown")
    component_label = _COMPONENT_LABELS.get(component, component.upper())

    if mode == "inspect":
        allowed_tags = [f"{component}_read", "maintenance_read"]
        agent_token_limit = max(1, int(config.get("ai_agent_token_limit", "150000")))
        agent_step_limit = max(1, int(config.get("ai_agent_step_limit", "20")))
    else:  # "act"
        # ``entity_metadata_write`` — shared cross-advisor tag for
        # entity-metadata tools (labels, notes, …) defined in
        # ``trackme_ai_agent_tools``. ``maintenance_*`` — shared per-entity
        # maintenance tools. See the same comment in
        # ``trackme_libs_ai_agents.py``.
        allowed_tags = [
            f"{component}_read",
            f"{component}_write",
            "entity_metadata_write",
            "maintenance_read",
            "maintenance_write",
        ]
        agent_token_limit = max(1, int(config.get("ai_agent_act_token_limit", "200000")))
        agent_step_limit = max(1, int(config.get("ai_agent_act_step_limit", "40")))

    logger.info(
        f"Component Health Advisor ({component_label}) agent starting: mode={mode}, "
        f"model={model_name}, provider={provider_type} ({provider_name_log}), "
        f"token_limit={agent_token_limit}, step_limit={agent_step_limit}, "
        f"entity={object_name} ({object_id})"
    )

    initial_message = (
        f"Analyze the health configuration for this TrackMe {component_label} entity:\n\n"
        f"- **Tenant ID**: {tenant_id}\n"
        f"- **Component**: {component}\n"
        f"- **Object ID** (_key hash, use for KV lookups): {object_id}\n"
        f"- **Object Name** (entity name, use for history queries): {object_name}\n"
        f"- **Mode**: {mode}\n\n"
    )

    if mode == "inspect":
        initial_message += (
            "Perform a read-only inspection. Analyze the entity's history, "
            "current configuration, and monitoring setup. Report your findings with "
            "specific, actionable recommendations but do NOT apply any changes."
        )
    else:
        initial_message += (
            f"**MODE: ACT — You MUST apply changes using write tools.**\n\n"
            f"Analyze the entity's history, current configuration, and monitoring setup. "
            f"Then EXECUTE the appropriate remediation actions by calling the write tools "
            f"available for the {component_label} component.\n\n"
            f"Do NOT just recommend — you MUST call the write tools to apply changes. "
            f"Document every action in the actions_taken array of your response."
        )

        # Inject prior inspect result if available (saves redundant read phase)
        prior_result = _get_recent_inspect_result(service, tenant_id, component, object_id)
        if prior_result:
            initial_message += (
                f"\n\n**PRIOR INSPECTION RESULTS (completed within the last 30 minutes)**\n"
                f"A recent inspect run already analyzed this entity. Use these findings as "
                f"your starting point: call the entity context tool once to confirm "
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
    if automated and not _vtenant_allows_decommission(vtenant_account or {}, component):
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

    # Import component health tools registry (deferred — requires Python 3.13)
    import trackme_ai_component_health_tools  # noqa: F401 — side-effect: registers tools

    system_prompt = _get_system_prompt(component)
    # Append provider-level and tenant-level custom instructions to the
    # resolved system prompt — same concatenation as every other
    # automated advisor (see ``build_automated_system_prompt``).
    system_prompt = build_automated_system_prompt(
        system_prompt, config, vtenant_account
    )

    # Resolve tenant summary index for per-tool-call event emission.
    try:
        from trackme_libs import trackme_idx_for_tenant  # noqa: WPS433 — deferred import
        _splunkd_uri = f"{service.scheme}://{service.host}:{service.port}"
        _idx_settings = trackme_idx_for_tenant(service.token, _splunkd_uri, tenant_id)
        _summary_index = _idx_settings.get("trackme_summary_idx", "trackme_summary")
    except Exception:
        _summary_index = "trackme_summary"

    _check_agent_model_capability(model, provider_type, model_name)
    try:
        for attempt in range(1, max_attempts + 1):
            _token_count[0] = 0  # reset on retry
            _steps_taken[0] = 0
            try:
                with force_tool_strategy_for_provider(provider_type):
                    async with Agent(
                        model=model,
                        system_prompt=system_prompt,
                        service=service,
                        tool_settings=ToolSettings(
                            local=LocalToolSettings(allowlist=ToolAllowlist(tags=allowed_tags)),
                            remote=None,
                        ),
                        output_schema=ComponentHealthAdvisorResult,
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
                                    "Component Health Advisor",
                                    job_id=job_id,
                                    service=service,
                                    advisor_kind="component_health_advisor",
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
                            f"Component Health Advisor agent invoke starting: job_id={job_id}, mode={mode}, attempt={attempt}/{max_attempts}"
                        )
                        result = await agent.invoke([HumanMessage(content=initial_message)])
                        output = result.structured_output

                        actions_count = (
                            len(output.actions_taken)
                            if isinstance(output, ComponentHealthAdvisorResult)
                            else 0
                        )
                        entity_status = (
                            output.entity_status
                            if isinstance(output, ComponentHealthAdvisorResult)
                            else "unknown"
                        )
                        logger.info(
                            f"Component Health Advisor ({component_label}) agent completed: "
                            f"mode={mode}, model={model_name}, entity_status={entity_status}, "
                            f"actions_taken_count={actions_count}, "
                            f"token_count={_token_count[0]}, steps={_steps_taken[0]}"
                        )

                        if mode == "act" and actions_count == 0:
                            logger.warning(
                                f"Component Health Advisor ({component_label}) act mode produced "
                                f"no actions_taken — the model may have skipped write tool execution"
                            )

                        return output, _token_count[0], _steps_taken[0]

            except Exception as e:
                if _is_structured_output_unsupported(e):
                    # Hard API rejection (e.g. Ollama 400 "does not support tools") —
                    # no point retrying, the model cannot participate in the agentic loop.
                    raise RuntimeError(
                        f"Model '{model_name}' (provider: {provider_type}) does not support "
                        f"tool use or structured output, which is required by the Component "
                        f"Health Advisor ({component_label}) agent. Please configure a model "
                        f"with function-calling support. Commercial API providers (OpenAI, "
                        f"Anthropic, Azure OpenAI) are recommended for reliable agentic workflows."
                    ) from e
                if _is_agent_structured_output_failure(e) and attempt < max_attempts:
                    # Model called tools but didn't call the `respond` tool at the end —
                    # non-deterministic with smaller open-source models. Retry with fresh
                    # agent context; the prompt hint may succeed on the next attempt.
                    logger.warning(
                        f"Component Health Advisor ({component_label}) agent did not produce "
                        f"structured output (attempt {attempt}/{max_attempts}), "
                        f"retrying with fresh context..."
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
                # (``<component>_write``, ``entity_metadata_write``)
                # that may already have executed before the transient
                # surfaced. See CodeRabbit review on PR #1754.
                if (
                    _is_transient_provider_error(e)
                    and attempt < max_attempts
                    and mode != "act"
                ):
                    delay = _transient_retry_backoff_sec(attempt + 1)
                    logger.warning(
                        f"Component Health Advisor ({component_label}) hit transient provider error "
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
                        f"Component Health Advisor ({component_label}) hit transient provider error in act mode "
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
                        f"Component Health Advisor ({component_label}) agent hit SDK tool_result "
                        f"bug (attempt {attempt}/{max_attempts}), retrying..."
                    )
                    last_error = e
                    continue
                if _is_tool_result_bug(e) and mode == "act":
                    logger.warning(
                        f"Component Health Advisor ({component_label}) hit SDK tool_result bug in act mode "
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


def start_component_health_advisor_async(
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
):
    """
    Start the Component Health Advisor agent asynchronously.

    Creates a job record, spawns a background thread, and returns immediately with job_id.
    Used by the REST handler for interactive (UI-driven) invocations.

    Args:
        system_service: Splunk service with system auth (for config access and job tracking)
        user_service: Splunk service with user auth (for RBAC enforcement)
        request_info: REST handler request info (provides server_rest_port, system_authtoken, etc.)
        tenant_id: Tenant identifier
        component: Component type — one of "wlk", "mhm"
        object_id: Entity _key hash in KV Store
        object_name: Entity name
        mode: "inspect" or "act"
        provider_name: AI provider name (None = first configured provider)
        user_context: Optional free-text instructions from the user

    Returns:
        dict with {job_id, status} where status is "running"

    Raises:
        RuntimeError: If at maximum agent concurrency
        ValueError: If component is not supported
    """
    # Validate component early before acquiring concurrency slot
    _get_system_prompt(component)

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

    component_label = _COMPONENT_LABELS.get(component, component.upper())
    splunkd_uri = f"{system_service.scheme}://{system_service.host}:{system_service.port}"
    session_key = request_info.system_authtoken
    server_name = request_info.server_servername

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

            sourcetype = f"trackme:ai_agent:component_health_advisor:{component}:{agent_mode}"
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
                source="trackme:ai_agent:component_health",
                sourcetype=sourcetype,
                host=server_name,
            )
            logger.info(
                f"Indexed Component Health Advisor ({component_label}) event: "
                f"job={job_id}, mode={agent_mode}, status={status}, token_count={token_count}"
            )
        except Exception as idx_e:
            # Audit event lost permanently (no retry path).  Use ERROR
            # so audit-pipeline failures surface in error monitoring.
            logger.error(
                f"Failed to index Component Health Advisor ({component_label}) event "
                f"(job={job_id}): {idx_e}"
            )

    # Watchdog coordination — see ``_make_agent_worker_watchdog`` in
    # ``trackme_libs_ai_agents``.  Same SDK-hang safety net the ML
    # Advisor uses; every Agent SDK advisor shares the risk.
    _watchdog_stop, _watchdog_fired, _start_watchdog = _agents_module._make_agent_worker_watchdog(
        advisor_label="Component Health Advisor",
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
                    _run_component_health_agent(
                        agent_service, model, config, tenant_id, component,
                        object_id, object_name, mode, user_context=user_context,
                        server_name=server_name, job_id=job_id,
                    ),
                    timeout=_agents_module._resolve_hard_timeout_sec(mode),
                )
            )
            if _watchdog_fired.is_set():
                logger.warning(
                    f"Component Health Advisor worker returned successfully "
                    f"AFTER watchdog abort (job={job_id}); preserving the "
                    f"watchdog's error state — discarding late result."
                )
                return
            result_dict = result.model_dump() if result else {"summary": "Agent completed without structured output"}
            _update_agent_job(system_service, job_id, "complete", result=result_dict)
            _index_agent_event(agent_service, result_dict, mode, "success",
                               token_count=token_count, steps_taken=steps_taken)

        except Exception as e:
            error_str = format_agent_error_chain(e)

            # Hard timeout fired (see ``_resolve_hard_timeout_sec``).
            # Watchdog above is the production-observed backstop when
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
                    f"Component Health Advisor agent TIMEOUT (job={job_id}, "
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
                # partial writes have been applied.  Use ERROR so this
                # surfaces in error monitoring.
                logger.error(
                    f"Component Health Advisor ({component_label}) hit SDK tool_result bug "
                    f"(job={job_id}): partial actions may have been applied."
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
                                f"Re-run the Component Health Advisor ({component_label}) in "
                                f"inspect mode to verify the current state and confirm which "
                                f"actions (if any) were applied."
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
                logger.error(
                    f"Component Health Advisor ({component_label}) error (job={job_id}): {e}",
                    exc_info=True,
                )
                _update_agent_job(system_service, job_id, "error", error=error_str)
                _index_agent_event(agent_service, None, mode, "error", error_msg=error_str)

        finally:
            _watchdog_stop.set()
            _release_agent_slot(job_id)

    thread = threading.Thread(
        target=_worker,
        daemon=True,
        name=f"component_health_{component}_{job_id[:8]}",
    )
    thread.start()

    return {"job_id": job_id, "status": "running"}


# ---------------------------------------------------------------------------
# Automated Entry Point (streaming command)
# ---------------------------------------------------------------------------


def start_component_health_advisor_from_search_context(
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
    Start the Component Health Advisor agent from a streaming command context.

    Same as start_component_health_advisor_async() but accepts streaming command
    context (service, session_key, splunkd_uri, server_name) instead of request_info.
    Used by the automated component health scheduled backend.

    Args:
        service: Splunk service connection (from streaming command)
        session_key: Splunk session key string
        splunkd_uri: Splunkd base URI (e.g. "https://localhost:8089")
        server_name: Splunk server hostname for event indexing
        tenant_id: Tenant identifier
        component: Component type — one of "wlk", "mhm"
        object_id: Entity _key hash in KV Store
        object_name: Entity name
        mode: "inspect" or "act"
        provider_name: AI provider name (None = first configured provider)
        vtenant_account: Tenant configuration dict (for decommission guard)

    Returns:
        dict with {job_id, status} where status is "running"

    Raises:
        RuntimeError: If at maximum agent concurrency
        ValueError: If component is not supported
    """
    # Validate component early before acquiring concurrency slot
    _get_system_prompt(component)

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

    component_label = _COMPONENT_LABELS.get(component, component.upper())

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

            sourcetype = f"trackme:ai_agent:component_health_advisor:{component}:{agent_mode}"
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
                source="trackme:ai_agent:component_health:automated",
                sourcetype=sourcetype,
                host=server_name,
            )
            logger.info(
                f"Indexed automated Component Health Advisor ({component_label}) event: "
                f"job={job_id}, mode={agent_mode}, status={status}, token_count={token_count}"
            )
        except Exception as idx_e:
            # Audit event lost permanently (no retry path).  Use ERROR.
            logger.error(
                f"Failed to index automated Component Health Advisor ({component_label}) event "
                f"(job={job_id}): {idx_e}"
            )

    # Watchdog coordination — see ``_make_agent_worker_watchdog`` in
    # ``trackme_libs_ai_agents``.  Automated/scheduled
    # Component Health variant.
    _watchdog_stop, _watchdog_fired, _start_watchdog = _agents_module._make_agent_worker_watchdog(
        advisor_label="Component Health Advisor",
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
                    _run_component_health_agent(
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
                    f"Component Health Advisor automated worker returned "
                    f"successfully AFTER watchdog abort (job={job_id}); "
                    f"preserving the watchdog's error state — discarding "
                    f"late result."
                )
                return
            result_dict = result.model_dump() if result else {"summary": "Agent completed without structured output"}
            _update_agent_job(service, job_id, "complete", result=result_dict)
            _index_agent_event(agent_service, result_dict, mode, "success",
                               token_count=token_count, steps_taken=steps_taken)

        except Exception as e:
            error_str = format_agent_error_chain(e)

            # Hard timeout fired (see ``_resolve_hard_timeout_sec``).
            # Watchdog above is the production-observed backstop when
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
                    f"Component Health Advisor agent TIMEOUT (job={job_id}, "
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
                    f"Component Health Advisor ({component_label}) hit SDK tool_result bug "
                    f"(job={job_id}): automated run, partial actions may have been applied."
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
                logger.error(
                    f"Component Health Advisor ({component_label}) automated error (job={job_id}): {e}",
                    exc_info=True,
                )
                _update_agent_job(service, job_id, "error", error=error_str)
                _index_agent_event(agent_service, None, mode, "error", error_msg=error_str)

        finally:
            _watchdog_stop.set()
            _release_agent_slot(job_id)

    thread = threading.Thread(
        target=_worker,
        daemon=True,
        name=f"component_health_{component}_auto_{job_id[:8]}",
    )
    thread.start()

    return {"job_id": job_id, "status": "running"}

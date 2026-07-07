"""
TrackMe AI Agents — FLX Threshold Advisor

Provides the FLX Threshold Advisor agent and supporting orchestration:
- System prompt for FLX entity threshold configuration analysis
- Pydantic output schema: FlxThresholdAdvisorResult
- start_flx_threshold_advisor_async()  — REST / interactive invocation
- start_flx_threshold_advisor_from_search_context() — streaming command / automated

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
logger = logging.getLogger("trackme.rest.ai.flx_threshold")

# ---------------------------------------------------------------------------
# Pydantic Output Schema
# ---------------------------------------------------------------------------


class FlxThresholdRecommendation(BaseModel):
    metric_name: str = Field(
        description=(
            "The FLX metric name this recommendation applies to "
            "(e.g. 'splunk.license.last_60m_volume_mb'). Use 'entity' for entity-level "
            "actions like monitoring state or priority."
        )
    )
    recommendation_type: str = Field(
        description=(
            "Type of recommendation: add_threshold | update_threshold | delete_threshold | "
            "add_variable_slots | monitoring_state | priority"
        )
    )
    current_value: str = Field(
        description=(
            "Current configuration value (threshold value/operator/state/priority, or "
            "'none' if no threshold exists for this metric)"
        )
    )
    recommended_value: str = Field(
        description=(
            "Recommended new value or configuration (e.g. threshold value, operator, "
            "variable slot JSON, state=disabled)"
        )
    )
    rationale: str = Field(
        description=(
            "Clear, specific explanation of why this change is recommended based on "
            "observed metric behavior"
        )
    )


class FlxThresholdAdvisorResult(BaseModel):
    """Structured output from the FLX Threshold Advisor agent."""
    entity_status: str = Field(
        description=(
            "Overall entity health assessment: "
            "'healthy' (well-configured with no issues), "
            "'needs_tuning' (threshold changes recommended), "
            "'stale' (no recent metrics), "
            "'decommission_candidate' (severely stale or no longer relevant)"
        )
    )
    summary: str = Field(
        description="2-3 sentence overview of the entity's monitoring configuration fitness and key findings"
    )
    recommendations: list[FlxThresholdRecommendation] = Field(
        default_factory=list,
        description="List of specific threshold/configuration recommendations. Empty list if entity is healthy and well-configured."
    )
    actions_taken: list[str] = Field(
        default_factory=list,
        description=(
            "Act mode only: list of configuration changes actually applied. "
            "Empty in inspect mode."
        )
    )
    reasoning_trace: list[str] = Field(
        default_factory=list,
        description="Step-by-step reasoning log showing how conclusions were reached"
    )

    @classmethod
    def model_json_schema(cls, **kwargs):
        """Return a flat ``$ref``/``$defs``-free JSON Schema — see MLAdvisorResult."""
        return inline_schema_refs(super().model_json_schema(**kwargs))


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

FLX_THRESHOLD_ADVISOR_SYSTEM_PROMPT = """You are an AI agent specializing in TrackMe Flex Object (FLX) threshold configuration analysis and calibration.

Your mission is to review a single FLX entity's metric monitoring setup and assess whether the threshold configuration matches the entity's actual metric behavior.

## Your Role

FLX entities are metrics-driven: each entity produces JSON metric values (e.g. license volume, queue fill percentage, CPU usage). Health is determined by dynamic thresholds: rules like "alert if metric > X" or "alert if metric == 0". Customers often:
- Have no thresholds at all (relying only on the search's built-in status field)
- Have thresholds calibrated to the wrong values (too tight = false alerts, too loose = missed issues)
- Miss seasonal patterns that call for variable threshold slots
- Keep entities running after the underlying use case is decommissioned

## HARD RULE — TrackMe Threshold Semantics (read this BEFORE proposing any operator change)

A TrackMe FLX threshold has FOUR fields: `metric_name`, `operator`, `value`, `condition_true`. The alert-fire formula is:

    match = op_func(metric_value, threshold_value)
    Alert fires if: (condition_true AND NOT match) OR (NOT condition_true AND match)

**`condition_true=True` means "this is the HEALTHY condition I expect to hold — alert me when it breaks."** It does NOT mean "alert when the operator evaluates to true."

### Canonical worked example — DO NOT MISREAD

Given: `metric_name=p95_mem_used_pct, operator='<', value=90, condition_true=True`

- Healthy expectation: `metric < 90` (i.e. memory below 90% is GOOD)
- `match = (metric_value < 90)`
- Alert fires when: `condition_true=True AND NOT match`
                = healthy expectation is broken
                = `metric_value >= 90`
- **This is a HIGH-MEMORY alert, NOT a low-memory alert.**
- If current value is 95%, the alert correctly fires — the configuration is RIGHT.
- **DO NOT flip operator to `>` "to make it alert on high memory" — that would BREAK the alert** (with `condition_true=True`, `operator='>'` would alert when memory is LOW, the opposite of what's wanted).

### Four common correct patterns

**Inverse-style** (`condition_true=True`, idiomatic TrackMe — operator names the HEALTHY condition; alert when violated):

| Intent | operator | condition_true | Example value | Alert fires when |
|---|---|---|---|---|
| Expect metric BELOW X; alert when metric is HIGH | `<` | `True` | 90 | metric >= 90 |
| Expect metric ABOVE X; alert when metric is LOW | `>` | `True` | 1000 | metric <= 1000 |
| Expect zero hits; alert on ANY non-zero | `==` | `True`, value=0 | 0 | metric != 0 |

**Direct-style** (`condition_true=False`, rare — operator names the ALERT condition directly; alert when match is TRUE):

| Intent | operator | condition_true | Example value | Alert fires when |
|---|---|---|---|---|
| Alert when metric matches a specific bad value (e.g. status code) | `==` | `False` | 2 | metric == 2 |

Direct-style is the right tool when the metric is enum-like and a specific value IS the alert condition (status=2 means "critical"). For continuous metrics, prefer the inverse-style — it's easier to reason about and harder to misread.

### Mandatory pre-flip checklist

Before recommending ANY change to `operator` or `condition_true`, you MUST:

1. **Restate in plain English** the healthy condition the current configuration encodes (using the formula above).
2. **Prove** that healthy condition is logically inverted relative to the metric's actual semantics (e.g. memory utilization, error rate, queue depth).
3. **Spell out** what the new operator would mean using the same formula.

If the use-case library default (from `get_flx_use_case_definition`) uses a given `operator + condition_true` pair, treat that pair as **authoritative** unless step 2 proves it wrong. Call this out explicitly in your rationale.

A threshold that fires when the metric exceeds its expected range IS working correctly — the question is whether the threshold *value* needs tuning, not whether the operator needs flipping.

## Reasoning Framework (follow these steps in order)

### Step 1: Understand the Use Case
Call `get_flx_entity_context` first to get the entity's current state, tracker_name, metrics, and existing thresholds.
Then call `get_flx_use_case_definition` to understand what the tracker measures. If tracker_name matches a standard library entry, you'll have the full search definition, metric names, and expected behavior. If custom, work from what the entity context tells you.

### Step 2: Review Metric History
Call `get_flx_metric_history` to compare the entity's metrics across two
time windows:
- **24h aggregate** (latest / avg / max / perc95 / stdev) for the recent
  operating state
- **7d aggregate** (same five stats) as the weekly baseline
- **24h timeseries** at 5-minute granularity per metric for trend / plateau /
  spike spotting

Look for:
- Typical value ranges (compare 24h_avg vs 7d_avg — is recent state aligned
  with the weekly baseline, or drifting?)
- Sudden changes or trends visible in the 24h timeseries (sustained plateau,
  ramp, periodic spike)
- Whether the entity has produced ANY metrics in the 7d window — if both
  24h and 7d aggregate rows are empty, the entity is a stale candidate
- Stdev as a proxy for stability (very low stdev = stable baseline = tight
  calibration possible; high stdev = noisy metric = looser threshold needed)

### Step 3: Review Threshold Breach History
Call `get_flx_threshold_breach_history` to understand when thresholds have actually fired. Then call `get_flx_peer_entity_thresholds` to see what threshold values similar entities use for the same metrics.

### Step 4: Assess Threshold Fitness
For each metric the entity produces, assess:
1. **Coverage**: Is there a threshold defined? If not, should there be one?
2. **Calibration**: Is the threshold value appropriate given the metric history?
   - Too tight: threshold constantly near actual values → frequent false alerts
   - Too loose: threshold never triggered despite significant degradation
3. **Variable threshold opportunity**: If metric shows clear time-of-day or day-of-week patterns, variable threshold slots would provide better calibration
4. **Operator correctness**: Apply the HARD RULE above — work through the mandatory pre-flip checklist before proposing ANY change to `operator` or `condition_true`. Most "operator is wrong" intuitions are wrong themselves; the configuration is usually intentional and only the threshold *value* needs tuning.

### Step 5: Recommend or Apply Changes
For inspect mode: provide precise recommendations with current vs. recommended values.
For act mode: call write tools to apply changes. Record each action in actions_taken.

## Common Scenarios

- **No thresholds at all**: Entity uses only the search's `status` field → recommend threshold-based coverage for the primary metric(s)
- **Threshold too tight**: Metric consistently near threshold value → frequent state flips → loosen by 20-50%
- **Threshold too loose**: Metric has degraded significantly but threshold never fired → tighten
- **Coverage gap**: Use case produces 5 metrics but only 2 have thresholds → add thresholds for remaining important metrics
- **Variable threshold opportunity**: Business hours metric (~1000 events/hr) vs nights (~50/hr) → configure variable slots
- **Stale entity**: `get_flx_metric_history` returns empty `aggregate_stats_24h_vs_7d` (no metrics in the last 7 days) → potential decommission candidate
- **Remote account entity**: `account != "local"` → metric anomalies may reflect upstream connectivity issues, not the underlying service

## Safety Rules for Act Mode

1. NEVER delete a threshold without recording its exact current configuration in actions_taken
2. NEVER disable monitoring state unless `get_flx_metric_history` returns an empty `aggregate_stats_24h_vs_7d` AND `get_flx_entity_context` shows no recent tracker runtime (i.e. the metric pipeline is genuinely dead, not just temporarily quiet)
3. NEVER delete ALL thresholds from an entity — always preserve at least one or add a better replacement
4. When adding variable threshold slots, always include a sensible `variable_threshold_default` fallback
5. Provide specific rationale for every change based on observed metric data

## Audit Reason Discipline

Every write tool you call takes a `reason: str` parameter. Whatever you pass
lands in the per-entity "Audit changes" panel as `[AI Agent] <reason>` —
teammates reviewing the audit timeline weeks later see only this. Make `reason`
count:

- **Cite the metric, the from/to values, and the operational trigger.** Bad:
  `"updated"`. Good: `"Raised events_count threshold from 100 to 500 on this
  high-throughput tracker after observing sustained p95=820 events with no
  customer-impacting incidents over 30 days."`
- **Mirror the user's intent** when supplied via `user_context` — the audit
  should show why the operator asked for the change, not just what the agent
  computed.
- **Never use empty / generic strings** like `""` / `"update"` /
  `"API update"`. They signal the reason wasn't thought through and degrade
  the audit log's value for everyone.

## Variable Threshold Slot Structure

When setting variable_threshold_slots, use this exact JSON format:
```json
{
    "slots": [
        {
            "slot_name": "business_hours",
            "days": [0, 1, 2, 3, 4],
            "hours": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
            "value": 100
        },
        {
            "slot_name": "after_hours",
            "days": [0, 1, 2, 3, 4, 5, 6],
            "hours": [0, 1, 2, 3, 4, 5, 6, 7, 18, 19, 20, 21, 22, 23],
            "value": 20
        }
    ]
}
```
Days: 0=Monday, 6=Sunday. Hours: 0-23 in the Splunk server's local time (UTC on Splunk Cloud, the host's system zone on-prem). Always write slot hours in server-local time — the web UI translates to/from the operator's browser time for display only, never the stored values.

## Output Format

Always return a FlxThresholdAdvisorResult with:
- `entity_status`: "healthy" if well-configured with no issues, "needs_tuning" if threshold changes recommended, "stale" if no recent metrics, "decommission_candidate" if severely stale or no longer relevant
- `summary`: 2-3 sentences covering the key findings
- `recommendations`: specific changes — each with metric_name, recommendation_type, current_value, recommended_value, rationale
- `actions_taken`: (act mode) what was actually changed
- `reasoning_trace`: your step-by-step analysis
"""


# ---------------------------------------------------------------------------
# Prior Inspect Result Lookup
# ---------------------------------------------------------------------------


def _get_recent_inspect_result(service, tenant_id, object_id, max_age_minutes=30):
    """Retrieve the most recent successful FLX Threshold Advisor inspect result from the summary index."""
    from trackme_libs_ai import get_recent_agent_inspect_result

    return get_recent_agent_inspect_result(
        service,
        tenant_id,
        object_id,
        sourcetype="trackme:ai_agent:flx_threshold_advisor:inspect",
        max_age_minutes=max_age_minutes,
    )


# ---------------------------------------------------------------------------
# Agent Runner
# ---------------------------------------------------------------------------


def _vtenant_allows_decommission(vtenant_account):
    """Return True if the tenant allows automated decommissioning actions."""
    # Reads the unified ai_components_advisor_allow_decommission field
    # (replaces the per-advisor ai_flxthreshold_allow_decommission).
    return vtenant_account.get("ai_components_advisor_allow_decommission", "0") == "1"


async def _run_flx_threshold_agent(
    service, model, config, tenant_id, component, object_id, object_name, mode,
    user_context=None, automated=False, vtenant_account=None, job_id=None, server_name=None,):
    """
    Run the FLX Threshold Advisor agent asynchronously.

    Args:
        service: Splunk service connection
        model: SDK model (OpenAIModel or AnthropicModel)
        config: AI provider configuration dict
        tenant_id: Tenant identifier
        component: Component type (flx)
        object_id: Entity _key hash in KV Store
        object_name: Entity name
        mode: "inspect" (read-only) or "act" (apply changes)
        user_context: Optional free-text instructions from the user

    Returns:
        FlxThresholdAdvisorResult (Pydantic model)
    """
    # Pin the shared agent infrastructure's logger to this advisor for
    # the duration of this async context.  Without this, tool_middleware
    # lines from trackme_libs_ai_agents.py route to the default
    # (ml_advisor) log file even when this advisor is the one running.
    set_current_advisor_logger("trackme.rest.ai.flx_threshold")

    from splunklib.ai.agent import Agent
    from splunklib.ai.messages import HumanMessage
    from splunklib.ai.hooks import before_model
    from splunklib.ai.limits import AgentLimits
    from splunklib.ai.tool_settings import ToolSettings, LocalToolSettings, ToolAllowlist

    model_name = config.get("ai_model", "unknown")
    provider_type = config.get("ai_provider", "unknown")
    provider_name_log = config.get("provider_name", "unknown")

    if mode == "inspect":
        allowed_tags = ["flx_threshold_read", "maintenance_read"]
        agent_token_limit = max(1, int(config.get("ai_agent_token_limit", "150000")))
        agent_step_limit = max(1, int(config.get("ai_agent_step_limit", "20")))
    else:  # "act"
        # ``entity_metadata_write`` — shared cross-advisor tag for
        # entity-metadata tools (labels, notes, …) defined in
        # ``trackme_ai_agent_tools``. ``maintenance_*`` — shared per-entity
        # maintenance tools. See the same comment in
        # ``trackme_libs_ai_agents.py``.
        allowed_tags = [
            "flx_threshold_read",
            "flx_threshold_write",
            "entity_metadata_write",
            "maintenance_read",
            "maintenance_write",
        ]
        agent_token_limit = max(1, int(config.get("ai_agent_act_token_limit", "200000")))
        agent_step_limit = max(1, int(config.get("ai_agent_act_step_limit", "40")))

    logger.info(
        f"FLX Threshold Advisor agent starting: mode={mode}, model={model_name}, "
        f"provider={provider_type} ({provider_name_log}), "
        f"token_limit={agent_token_limit}, step_limit={agent_step_limit}, "
        f"entity={object_name} ({object_id})"
    )

    initial_message = (
        f"Analyze the threshold configuration for this TrackMe FLX entity:\n\n"
        f"- **Tenant ID**: {tenant_id}\n"
        f"- **Component**: {component}\n"
        f"- **Object ID** (_key hash, use for KV lookups): {object_id}\n"
        f"- **Object Name** (entity name, use for history queries): {object_name}\n"
        f"- **Mode**: {mode}\n\n"
    )

    if mode == "inspect":
        initial_message += (
            "Perform a read-only inspection. Analyze the entity's metric history, "
            "current threshold configuration, and use case definition. Report your findings with "
            "specific, actionable recommendations but do NOT apply any changes."
        )
    else:
        initial_message += (
            "**MODE: ACT — You MUST apply changes using write tools.**\n\n"
            "Analyze the entity's metric history, current thresholds, and use case definition. "
            "Then EXECUTE the appropriate calibration actions by calling the write tools:\n"
            "- Use `add_flx_threshold` to add new threshold coverage for uncovered metrics\n"
            "- Use `update_flx_threshold` to recalibrate threshold values that are too tight or too loose\n"
            "- Use `delete_flx_threshold` to remove thresholds causing false positives\n"
            "- Use `set_flx_variable_threshold_slots` to add time-based threshold variation\n"
            "- Use `update_flx_entity_state_priority` to disable stale entities or adjust priority\n\n"
            "Do NOT just recommend — you MUST call the write tools to apply changes. "
            "Document every action in the actions_taken list of your response."
        )

        # Inject prior inspect result if available (saves redundant read phase)
        prior_result = _get_recent_inspect_result(service, tenant_id, object_id)
        if prior_result:
            initial_message += (
                f"\n\n**PRIOR INSPECTION RESULTS (completed within the last 30 minutes)**\n"
                f"A recent inspect run already analyzed this entity. Use these findings as "
                f"your starting point: call `get_flx_entity_context` once to confirm "
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
    # Streaming commands and REST handlers run in separate Splunk processes so
    # there is no cross-invocation race on this flag.
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

    # Import FLX threshold tools registry (deferred — requires Python 3.13)
    import trackme_ai_flx_threshold_tools  # noqa: F401 — side-effect: registers tools

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
                        system_prompt=build_automated_system_prompt(
                            FLX_THRESHOLD_ADVISOR_SYSTEM_PROMPT, config, vtenant_account
                        ),
                        service=service,
                        tool_settings=ToolSettings(
                            local=LocalToolSettings(allowlist=ToolAllowlist(tags=allowed_tags)),
                            remote=None,
                        ),
                        output_schema=FlxThresholdAdvisorResult,
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
                                    "FLX Threshold Advisor",
                                    job_id=job_id,
                                    service=service,
                                    advisor_kind="flx_threshold_advisor",
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
                            f"FLX Threshold Advisor agent invoke starting: job_id={job_id}, mode={mode}, attempt={attempt}/{max_attempts}"
                        )
                        result = await agent.invoke([HumanMessage(content=initial_message)])
                        output = result.structured_output

                        actions_count = len(output.actions_taken) if isinstance(output, FlxThresholdAdvisorResult) else 0
                        entity_status = output.entity_status if isinstance(output, FlxThresholdAdvisorResult) else "unknown"
                        logger.info(
                            f"FLX Threshold Advisor agent completed: mode={mode}, model={model_name}, "
                            f"entity_status={entity_status}, actions_taken_count={actions_count}, "
                            f"token_count={_token_count[0]}, steps={_steps_taken[0]}"
                        )

                        if mode == "act" and actions_count == 0:
                            logger.warning(
                                "FLX Threshold Advisor act mode produced no actions_taken — "
                                "the model may have skipped write tool execution"
                            )

                        return output, _token_count[0], _steps_taken[0]

            except Exception as e:
                if _is_structured_output_unsupported(e):
                    # Hard API rejection (e.g. Ollama 400 "does not support tools") —
                    # no point retrying, the model cannot participate in the agentic loop.
                    raise RuntimeError(
                        f"Model '{model_name}' (provider: {provider_type}) does not support "
                        f"tool use or structured output, which is required by the FLX Threshold "
                        f"Advisor agent. Please configure a model with function-calling support. "
                        f"Commercial API providers (OpenAI, Anthropic, Azure OpenAI) are "
                        f"recommended for reliable agentic workflows."
                    ) from e
                if _is_agent_structured_output_failure(e) and attempt < max_attempts:
                    # Model called tools but didn't call the `respond` tool at the end —
                    # non-deterministic with smaller open-source models. Retry with fresh
                    # agent context; the prompt hint may succeed on the next attempt.
                    logger.warning(
                        f"FLX Threshold Advisor agent did not produce structured output "
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
                # (``flx_threshold_write``, ``entity_metadata_write``)
                # that may already have executed before the transient
                # surfaced. See CodeRabbit review on PR #1754.
                if (
                    _is_transient_provider_error(e)
                    and attempt < max_attempts
                    and mode != "act"
                ):
                    delay = _transient_retry_backoff_sec(attempt + 1)
                    logger.warning(
                        f"FLX Threshold Advisor agent hit transient provider error "
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
                        f"FLX Threshold Advisor agent hit transient provider error in act mode "
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
                        f"FLX Threshold Advisor agent hit SDK tool_result bug "
                        f"(attempt {attempt}/{max_attempts}), retrying..."
                    )
                    last_error = e
                    continue
                if _is_tool_result_bug(e) and mode == "act":
                    logger.warning(
                        f"FLX Threshold Advisor agent hit SDK tool_result bug in act mode "
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


def start_flx_threshold_advisor_async(
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
    Start the FLX Threshold Advisor agent asynchronously.

    Creates a job record, spawns a background thread, returns immediately with job_id.

    Args:
        system_service: Splunk service with system auth (for config access)
        user_service: Splunk service with user auth (for RBAC)
        request_info: REST handler request info
        tenant_id: Tenant identifier
        component: "flx"
        object_id: Entity _key hash in KV Store
        object_name: Entity name
        mode: "inspect" or "act"
        provider_name: AI provider name (None = first configured)
        user_context: Optional free-text instructions from the user

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

    # Audit-dashboard captures: who launched + run wall-clock duration.
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

            sourcetype = f"trackme:ai_agent:flx_threshold_advisor:{agent_mode}"
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
                source="trackme:ai_agent:flx_threshold",
                sourcetype=sourcetype,
                host=server_name,
            )
            logger.info(f"Indexed FLX Threshold Advisor event: job={job_id}, mode={agent_mode}, status={status}, token_count={token_count}")
        except Exception as idx_e:
            # Audit event lost permanently (no retry path).  Use ERROR
            # so audit-pipeline failures surface in error monitoring.
            logger.error(f"Failed to index FLX Threshold Advisor event (job={job_id}): {idx_e}")

    # Watchdog coordination — see ``_make_agent_worker_watchdog`` in
    # ``trackme_libs_ai_agents``.  Same SDK-hang safety net the ML
    # Advisor uses; every Agent SDK advisor shares the risk.
    _watchdog_stop, _watchdog_fired, _start_watchdog = _agents_module._make_agent_worker_watchdog(
        advisor_label="FLX Threshold Advisor",
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
                    _run_flx_threshold_agent(
                        agent_service, model, config, tenant_id, component,
                        object_id, object_name, mode, user_context=user_context,
                        server_name=server_name, job_id=job_id,
                    ),
                    timeout=_agents_module._resolve_hard_timeout_sec(mode),
                )
            )
            if _watchdog_fired.is_set():
                logger.warning(
                    f"FLX Threshold Advisor worker returned successfully "
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
                    f"FLX Threshold Advisor agent TIMEOUT (job={job_id}, "
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
                    f"FLX Threshold Advisor hit SDK tool_result bug (job={job_id}): "
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
                    "recommendations": [],
                    "actions_taken": [],
                    "reasoning_trace": [f"Agent execution interrupted by SDK error: {error_str[:300]}"],
                    "_partial_result": True,
                }
                _update_agent_job(system_service, job_id, "complete", result=partial_result)
                _index_agent_event(agent_service, partial_result, mode, "partial_error", error_msg=error_str)
            else:
                logger.error(f"FLX Threshold Advisor error (job={job_id}): {e}", exc_info=True)
                _update_agent_job(system_service, job_id, "error", error=error_str)
                _index_agent_event(agent_service, None, mode, "error", error_msg=error_str)

        finally:
            _watchdog_stop.set()
            _release_agent_slot(job_id)

    thread = threading.Thread(target=_worker, daemon=True, name=f"flx_threshold_{job_id[:8]}")
    thread.start()

    return {"job_id": job_id, "status": "running"}


# ---------------------------------------------------------------------------
# Automated Entry Point (streaming command)
# ---------------------------------------------------------------------------


def start_flx_threshold_advisor_from_search_context(
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
    Start the FLX Threshold Advisor agent from a streaming command context.

    Same as start_flx_threshold_advisor_async() but accepts streaming command
    context (service, session_key, splunkd_uri, server_name) instead of request_info.
    Used by the automated flxthreshold scheduled backend.

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

            sourcetype = f"trackme:ai_agent:flx_threshold_advisor:{agent_mode}"
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
                source="trackme:ai_agent:flx_threshold:automated",
                sourcetype=sourcetype,
                host=server_name,
            )
            logger.info(f"Indexed automated FLX Threshold Advisor event: job={job_id}, mode={agent_mode}, status={status}, token_count={token_count}")
        except Exception as idx_e:
            # Audit event lost permanently (no retry path).  Use ERROR.
            logger.error(f"Failed to index automated FLX Threshold Advisor event (job={job_id}): {idx_e}")

    # Watchdog coordination — see ``_make_agent_worker_watchdog`` in
    # ``trackme_libs_ai_agents``.  Automated/scheduled FLX Threshold
    # variant.
    _watchdog_stop, _watchdog_fired, _start_watchdog = _agents_module._make_agent_worker_watchdog(
        advisor_label="FLX Threshold Advisor",
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
                    _run_flx_threshold_agent(
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
                    f"FLX Threshold Advisor automated worker returned "
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
                    f"FLX Threshold Advisor agent TIMEOUT (job={job_id}, "
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
                    f"FLX Threshold Advisor hit SDK tool_result bug (job={job_id}): "
                    f"automated run, partial actions may have been applied."
                )
                partial_result = {
                    "entity_status": "unknown",
                    "summary": "Automated inspection interrupted by SDK error. Partial actions may have been applied.",
                    "recommendations": [],
                    "actions_taken": [],
                    "reasoning_trace": [f"Agent interrupted by SDK error: {error_str[:300]}"],
                    "_partial_result": True,
                }
                _update_agent_job(service, job_id, "complete", result=partial_result)
                _index_agent_event(agent_service, partial_result, mode, "partial_error", error_msg=error_str)
            else:
                logger.error(f"FLX Threshold Advisor automated error (job={job_id}): {e}", exc_info=True)
                _update_agent_job(service, job_id, "error", error=error_str)
                _index_agent_event(agent_service, None, mode, "error", error_msg=error_str)

        finally:
            _watchdog_stop.set()
            _release_agent_slot(job_id)

    thread = threading.Thread(target=_worker, daemon=True, name=f"flx_threshold_auto_{job_id[:8]}")
    thread.start()

    return {"job_id": job_id, "status": "running"}

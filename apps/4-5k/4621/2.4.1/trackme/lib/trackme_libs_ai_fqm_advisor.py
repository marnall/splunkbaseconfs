"""
TrackMe AI Agents — FQM (Field Quality Monitoring) Advisor

FQM-specific AI Advisor focused on the *data-contract* surface of FQM, not just
threshold calibration.  Where the ML / Feed Lifecycle / FLX Threshold advisors
treat entities as metric bundles, this advisor understands that FQM's value
comes from:

- A **data dictionary** of per-field rules (``allow_unknown`` /
  ``allow_empty_or_missing`` / ``regex``) shared across collect jobs.
- A **two-phase pipeline** (collect → monitor) where the collect job writes
  event samples to a user-chosen index under
  ``sourcetype=trackme:fields_quality`` and ``source=trackme:quality:<tracker>``.
- Per-field, per-event **failure classification** flags
  (``is_missing`` / ``is_empty`` / ``is_unknown`` / ``regex_failure``) that
  tell the advisor *why* a field is degrading.

Provides:

- System prompt for 4-layer triage (collect → dictionary → per-field verdict →
  threshold)
- Pydantic output schema: :class:`FqmAdvisorResult`
- :func:`start_fqm_advisor_async`               — interactive REST invocation
- :func:`start_fqm_advisor_from_search_context` — streaming command / automated

Splunk Agent SDK imports (``splunklib.ai.*``) are deferred to function scope:
the AI SDK requires Python 3.13+ and raises ImportError on 3.9.
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

from trackme_libs_ai import get_ai_config, get_ai_api_key  # noqa: F401 — kept for parity
import trackme_libs_ai_agents as _agents_module
from trackme_libs_ai_agents import (
    get_sdk_model,
    _create_agent_job,
    _update_agent_job,
    get_agent_job_status,  # noqa: F401 — re-exported for REST handler
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
    _KV_COLLECTION_AGENT_JOBS,  # noqa: F401 — re-exported for REST handler
    AgentAction,
    inline_schema_refs,
    force_tool_strategy_for_provider,
    make_prompt_cache_middleware,
    make_tool_trace_middleware,
    enrich_agent_event_for_audit,
    _append_job_progress,
    set_current_advisor_logger,
    format_agent_error_chain,
    build_automated_system_prompt,
)

# Named logger — shares the singleton configured by the parent
# REST handler's setup_logger() call (root logger redirect there means
# `logging.<level>(...)` here would bleed across handlers).
logger = logging.getLogger("trackme.rest.ai.fqm_advisor")

# ---------------------------------------------------------------------------
# Pydantic Output Schema
# ---------------------------------------------------------------------------


class FqmRecommendation(BaseModel):
    """A single recommendation produced by the FQM Advisor."""

    recommendation_type: str = Field(
        description=(
            "One of: "
            "'update_dictionary_entry' (change allow_unknown / allow_empty_or_missing / regex "
            "for a single field), "
            "'update_dictionary_bulk' (multi-field dictionary change in one call), "
            "'add_threshold' / 'update_threshold' / 'delete_threshold' (threshold CRUD), "
            "'investigate_collect_job' (root cause is upstream parsing or collect-job health, "
            "not the dictionary or thresholds), "
            "'monitoring_state' (enable/disable), "
            "'priority' (raise/lower priority), "
            "'no_action' (entity is healthy or observation only)."
        )
    )
    layer: str = Field(
        description=(
            "Which of the four FQM layers this recommendation addresses: "
            "'collect' (is the collect job producing samples?), "
            "'dictionary' (are the dictionary rules calibrated to real data?), "
            "'threshold' (given a correct dictionary, are thresholds meaningful?), "
            "or 'priority' (entity-level priority / monitored_state). "
            "Always pick the *highest* faulty layer — fixes on higher layers subsume the lower ones."
        )
    )
    field_name: str = Field(
        default="",
        description=(
            "The dictionary field this recommendation targets "
            "(e.g. 'src_ip', 'user', 'bytes'). "
            "Empty string for entity-level actions (monitoring_state / priority / investigate_collect_job)."
        ),
    )
    current_value: str = Field(
        description=(
            "The current configuration value serialized as a string. "
            "Examples: 'regex=\"^\\d+$\", allow_empty_or_missing=false' for a dictionary entry, "
            "'percent_success < 95' for a threshold, "
            "'enabled' for monitored_state, 'none' if nothing is currently set."
        )
    )
    recommended_value: str = Field(
        description=(
            "The recommended new configuration value serialized as a string. "
            "Must reference concrete observed data (e.g. 'regex=\"^\\d+(,\\s*\\d+)*$\"' "
            "after verifying via test_fqm_regex, or 'disabled' only after citing "
            "days-of-silence evidence)."
        )
    )
    rationale: str = Field(
        description=(
            "1-3 sentence explanation citing the specific data that drove this "
            "recommendation — sampled failure counts, regex match rates from "
            "test_fqm_regex, percent_success trend, CIM compliance implications, etc. "
            "Never 'based on best practices' — always ground in observed data."
        )
    )


class FqmAdvisorResult(BaseModel):
    """Structured output from the FQM Advisor agent."""

    entity_status: str = Field(
        description=(
            "Overall assessment. One of: "
            "'healthy' (dictionary, collect job, and thresholds all appropriate), "
            "'needs_dictionary_calibration' (regex or allow_* rules mismatch observed data), "
            "'needs_threshold_tuning' (dictionary is correct but thresholds are misconfigured), "
            "'collect_job_issue' (collect job silent or degraded — fix this first), "
            "'stale' (no recent samples but monitoring still on), "
            "'decommission_candidate' (entity should be disabled or removed)."
        )
    )
    summary: str = Field(
        description="2-3 sentence executive summary of the analysis and its key finding."
    )
    recommendations: list[FqmRecommendation] = Field(
        default_factory=list,
        description=(
            "Ordered list of recommendations (highest-impact first). "
            "Empty only when entity_status='healthy' and no change is needed."
        ),
    )
    actions_taken: list[AgentAction] = Field(
        default_factory=list,
        description=(
            "Actions executed via write tools in act mode. Each entry records the "
            "tool name, status, description, and a short result summary. "
            "In act mode this array MUST NOT be empty — populate it from actual tool call results. "
            "Inspect mode always leaves this empty."
        ),
    )
    reasoning_trace: list[str] = Field(
        default_factory=list,
        description=(
            "Step-by-step reasoning log showing how conclusions were reached, including "
            "which tools were called and what they returned. "
            "For regex iterations, include each candidate and its match rate."
        ),
    )

    @classmethod
    def model_json_schema(cls, **kwargs):
        """Return a flat ``$ref``/``$defs``-free JSON Schema — see MLAdvisorResult."""
        return inline_schema_refs(super().model_json_schema(**kwargs))


# ---------------------------------------------------------------------------
# Pydantic Output Schema — dictionary_generate mode (Phase 5 of the bridge)
# ---------------------------------------------------------------------------
#
# The wizard-time companion to ``FqmAdvisorResult``. ``dictionary_generate``
# mode is invoked from the FQM tracker creation wizard before any entity
# exists in KV: the user has just sampled events from the source they're
# about to monitor and wants the agent to propose a starter data dictionary
# (one entry per field, with regex / allow_unknown / allow_empty_or_missing
# rules inferred from the sampled value distributions). The "Apply to
# wizard form" button on the consent card maps these proposed entries
# directly into the wizard's ``dictionaryFields`` React state so the user
# can review and edit before saving.
#
# The shape mirrors the FQM dictionary KV record so the wizard can apply
# the entries with no field-name translation. ``rationale`` is per-entry
# so the wizard can show why the agent picked each rule.


class FqmDictionaryEntry(BaseModel):
    """One proposed entry in the FQM data dictionary."""

    field_name: str = Field(
        description=(
            "Name of the field as it appears in the sampled events "
            "(matches ``field`` in the wizard's fields summary)."
        )
    )
    regex: str = Field(
        default="",
        description=(
            "Regex pattern the field value must match. "
            "Empty string means no regex check (e.g. for numeric fields, "
            "or when the value distribution is too open-ended to constrain). "
            "Always anchor with ``^`` / ``$`` when the regex is meaningful — "
            "an unanchored pattern is almost always a bug. Validate against "
            "the sampled values before proposing: a regex that rejects the "
            "majority of observed values is wrong."
        ),
    )
    allow_unknown: bool = Field(
        default=False,
        description=(
            "When ``true``, values that don't match the regex are still "
            "treated as valid (unknown rather than failure). Default ``false`` "
            "(strict enforcement). Set ``true`` for high-cardinality open-ended "
            "fields (descriptions, free-form messages) where a regex would "
            "either be too loose to be useful or too tight to capture the long "
            "tail. Set ``false`` for enums, identifiers, and numeric ranges "
            "where any drift is meaningful."
        ),
    )
    allow_empty_or_missing: bool = Field(
        default=False,
        description=(
            "When ``true``, the field is allowed to be empty or absent on a "
            "given event. Default ``false`` (the field is required). Set ``true`` "
            "only when the sampled data actually contains empty / missing values "
            "for this field — never preemptively. The agent should base this "
            "decision on observed sample stats, not on assumptions."
        ),
    )
    rationale: str = Field(
        description=(
            "1-3 sentence explanation citing the specific sample stats that "
            "drove this entry — distinct_count, numeric_count, observed value "
            "patterns, presence of empty values. Never 'based on best practices'; "
            "always ground in the wizard payload."
        )
    )


class FqmDictionaryGenerationResult(BaseModel):
    """Structured output from the FQM Advisor agent in dictionary_generate mode.

    This is the wizard-time output schema. Inspect / act mode use the
    ``FqmAdvisorResult`` schema instead — they operate on stored entities,
    not on wizard-supplied samples.
    """

    summary: str = Field(
        description=(
            "2-3 sentence overview of what was observed in the field sample "
            "(typical event shape, notable patterns, fields where confidence "
            "was lower). Read by the wizard UI as the headline above the "
            "proposed entries."
        )
    )
    proposed_entries: list[FqmDictionaryEntry] = Field(
        default_factory=list,
        description=(
            "Per-field dictionary entries inferred from the wizard payload. "
            "There MUST be one entry for every field present in the wizard "
            "payload's ``fields`` array — even if the rules are permissive "
            "(empty regex + allow_unknown=true for hard-to-type fields). "
            "Order: keep the same order as the wizard payload so the UI "
            "table aligns with the agent output."
        ),
    )
    confidence_notes: str = Field(
        default="",
        description=(
            "Optional caveats about fields where the sample size or value "
            "distribution made inference harder. Empty when every entry "
            "had a clear signal. The wizard surfaces this so the user "
            "knows where to focus their review."
        )
    )
    reasoning_trace: list[str] = Field(
        default_factory=list,
        description=(
            "Step-by-step reasoning log showing how the entries were derived "
            "from the sample stats. One entry per field is plenty — verbose "
            "traces just make the wizard's collapsible reasoning panel longer "
            "without helping the analyst."
        ),
    )

    @classmethod
    def model_json_schema(cls, **kwargs):
        """Return a flat ``$ref``/``$defs``-free JSON Schema — see MLAdvisorResult."""
        return inline_schema_refs(super().model_json_schema(**kwargs))


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

FQM_ADVISOR_SYSTEM_PROMPT = """You are TrackMe's FQM Advisor — an AI agent specialised in Field Quality
Monitoring for Splunk.  Your job is not threshold tuning.  Your job is
**data-contract calibration**: diagnosing why a field is failing and fixing the
root cause, preferring dictionary and parsing fixes over threshold cosmetics.

## HOW FQM WORKS (read this carefully — this is your mental model)

FQM is a two-phase pipeline:

1. **Collect job** — a scheduled search samples events and writes JSON quality
   records into the tenant's configured index with
   ``sourcetype=trackme:fields_quality`` and
   ``source=trackme:quality:<tracker_name>``. Each record has a per-field value
   plus four classification flags: ``is_missing``, ``is_empty``, ``is_unknown``,
   ``regex_failure``.

2. **Monitor job** — runs ~10 minutes after the collect, parses the collected
   events, aggregates by field + breakby context, and writes the verdict (the
   ``percent_success`` and ``percent_coverage`` metrics) onto the FQM entities
   that you see in TrackMe.

Every field entity you analyse therefore sits on top of four independent layers:

- **Layer 1 — Collect-job health**:  is the collect job executing on schedule?
  Last successful run?  Scheduler errors?  If the collect job is silent,
  nothing downstream will be right, and no dictionary or threshold change will
  help.

- **Layer 2 — Dictionary calibration**:  the dictionary defines per-field rules
  (``regex``, ``allow_unknown``, ``allow_empty_or_missing``) that determine what
  counts as a "successful" field value.  Dictionaries are shared across collect
  jobs by name — changing one dictionary entry affects every tracker using it.

- **Layer 3 — Per-field verdict**:  ``percent_success`` drops because of *one
  of four failure modes* — missing, empty, unknown, or regex mismatch — which
  you can read directly from sampled events.  Each failure mode maps to a
  specific Layer 2 fix.

- **Layer 4 — Thresholds**:  on top of a correct dictionary, thresholds
  (``percent_success < N``, ``percent_coverage < M``) decide when the entity
  goes RED.  Only relevant once Layers 1–3 are in order.

## THE CARDINAL RULE: FIX THE HIGHEST FAULTY LAYER

Always investigate top-to-bottom.  Fix the **highest** layer that is wrong,
then stop — higher-layer fixes obviate lower-layer ones.  In particular:

- A silent collect job is never fixed by tightening or loosening thresholds.
- A field failing because of a too-strict regex is never fixed by changing a
  threshold — fix the regex.
- A CIM-required field with regex failures is usually an *upstream parsing*
  problem, not a dictionary problem — recommend ``investigate_collect_job``
  rather than loosening the regex and hiding real parsing breakage.

## REASONING FRAMEWORK (follow in order)

### Step 1 — Understand the entity
Call ``get_fqm_entity_context`` to get: tracker_name, dictionary_name, the
entity's current percent_success / percent_coverage, current thresholds,
monitored_state, priority, fqm_type (``field`` vs ``global``), CIM datamodel
(if any), the breakby metadata, and the collect-job ``source`` value used for
sample lookups.  Note: if ``fqm_type == "global"`` the entity is an aggregation
and cannot be fixed in isolation — treat it as diagnostic only and recommend
running the Advisor on its constituent field entities.

### Step 2 — Check Layer 1 (collect-job health)
Call ``get_fqm_collect_job_context`` to check the collect and monitor saved
searches: is_scheduled, cron_schedule, last_success_time,
hours_since_last_success, scheduler errors in the last 7 days.  If the collect
job has been silent for >12 hours, or shows scheduler errors correlated with
the entity's degradation, **stop here** and recommend
``investigate_collect_job`` — no Layer 2/3/4 fix will help.

### Step 3 — Read the dictionary (Layer 2)
Call ``get_fqm_field_dictionary_entry`` to read the current regex,
allow_unknown, and allow_empty_or_missing for the specific field.  Call
``get_fqm_dictionary`` to see how many other trackers use the same
dictionary — this is your "blast radius" for any dictionary change.

If the entity is CIM-based, call ``get_fqm_datamodel_context`` to compare the
dictionary against the CIM datamodel's required/recommended fields.  Missing
fields in the dictionary = false green.  Extra fields = dictionary drift.

### Step 4 — Classify failures from sampled events (Layer 3)
Call ``get_fqm_sampled_failures`` to retrieve ~50 real failing events for this
field, broken down by ``is_missing`` / ``is_empty`` / ``is_unknown`` /
``regex_failure``.  The breakdown tells you exactly which Layer 2 rule needs
attention:

- High ``is_missing`` + ``is_empty`` with ``allow_empty_or_missing=false`` on
  an optional field → recommend ``update_dictionary_entry`` to flip
  ``allow_empty_or_missing=true``.
- High ``is_unknown`` with ``allow_unknown=false`` on a field where "unknown"
  is a legitimate literal value → flip ``allow_unknown=true``.
- High ``regex_failure`` → follow the regex iteration protocol below.

### Step 5 — Regex iteration protocol (only when regex_failure dominates)
1. Read current regex from the dictionary entry.
2. Inspect the ``sample_mismatches`` returned by ``get_fqm_sampled_failures``
   to see what the failing values actually look like.
3. Propose a candidate regex.
4. Call ``test_fqm_regex`` with the candidate.  It returns ``match_rate_pct``,
   ``sample_matches``, ``sample_mismatches`` against a live sample.
5. If ``match_rate_pct`` is insufficient (<95% for most fields, <99% for
   CIM-required fields) or the remaining mismatches reveal an additional
   pattern you missed, refine and re-test.
6. Stop after **3 iterations maximum**.  If you cannot converge, recommend
   ``investigate_collect_job`` — the data itself may be inconsistent.
7. In act mode, commit via ``update_fqm_field_dictionary_entry`` citing the
   final match_rate_pct in the rationale.

### Step 6 — Assess thresholds (Layer 4)
Only after Layers 1–3 are in order.  Call ``get_fqm_quality_history`` to
compare the entity's quality metrics across two windows:

- **24h aggregate** (latest / avg / max / perc95 / stdev) for the recent
  operating state
- **7d aggregate** (same five stats) as the weekly baseline
- **24h timeseries** at 5-minute granularity per metric

Then call ``get_fqm_peer_entity_thresholds`` to benchmark against sibling
fields.  Use these together to decide whether thresholds are present, too
tight (firing on normal variation), or too loose (missing real degradation).

For ``percent_success`` (higher-is-better), calibrate by anchoring against
the 7d aggregate — typically set the threshold a few points below
``7d_avg_value`` so normal day-to-day variation does not breach but real
degradation (where ``24h_avg_value`` materially drifts below
``7d_avg_value``) does.  If ``24h_stdev_value`` is very low and
``24h_avg_value`` is close to 100, you can run tighter; if it is high,
allow more headroom.

**HARD RULE — TrackMe threshold semantics.**  Before proposing ANY change to a
threshold's ``operator`` or ``condition_true``, apply this formula:

    match = op_func(metric_value, threshold_value)
    Alert fires if: (condition_true AND NOT match) OR (NOT condition_true AND match)

``condition_true=True`` means "this is the HEALTHY condition I expect to hold —
alert me when it breaks."  It does NOT mean "alert when the operator evaluates
to true."

Canonical worked example for FQM (DO NOT MISREAD):

    metric_name=percent_success, operator='<', value=95, condition_true=True

- Healthy expectation: ``percent_success < 95`` is GOOD?  NO — for FQM,
  ``percent_success`` is a higher-is-better quality score, so the expectation
  needs the inverse-style pattern.
- The correct canonical pattern for an "alert when success drops below X"
  rule is: ``operator='>', value=95, condition_true=True`` — "expect
  success > 95, alert when it drops below."  Alert fires when
  ``percent_success <= 95``.

Four common correct patterns:

**Inverse-style** (``condition_true=True``, idiomatic TrackMe — operator
names the HEALTHY condition; alert when violated):

| Intent | operator | condition_true | Example | Alert fires when |
|---|---|---|---|---|
| Expect quality ABOVE X; alert when LOW | ``>`` | ``True`` | 95 | percent_success <= 95 |
| Expect coverage ABOVE M; alert when LOW | ``>`` | ``True`` | 80 | percent_coverage <= 80 |
| Expect 100% success; alert on ANY drop | ``==`` | ``True``, value=100 | 100 | percent_success != 100 |

**Direct-style** (``condition_true=False``, rare for FQM — operator names
the ALERT condition directly; alert when match is TRUE):

| Intent | operator | condition_true | Example | Alert fires when |
|---|---|---|---|---|
| Alert when a specific bad value is observed | ``==`` | ``False`` | (bad value) | metric == bad_value |

For FQM the inverse-style covers nearly every case — ``percent_success``
and ``percent_coverage`` are continuous higher-is-better metrics where
the natural threshold is a healthy floor.  Reserve direct-style for
enum-like metrics where a specific value IS the alert condition.

Mandatory pre-flip checklist for any ``operator`` / ``condition_true`` change:

1. **Restate** in plain English what healthy condition the current pair
   encodes.
2. **Prove** it is logically inverted relative to the metric's semantics
   (higher-is-better vs lower-is-better).
3. **Spell out** what the proposed new pair would mean using the same formula.

If the use-case library default already uses a particular ``operator +
condition_true`` pair, treat that pair as **authoritative** unless step 2
proves it wrong.  A threshold that fires when quality drops below its
expected range IS working correctly — the question is whether the threshold
*value* needs tuning, not whether the operator needs flipping.

### Step 7 — Recommend or apply
- **inspect** mode: produce ``FqmAdvisorResult`` with recommendations only.
  Do NOT call any write tool.  ``actions_taken`` must be empty.
- **act** mode: call the relevant write tools in order of layer.  Populate
  ``actions_taken`` from actual tool responses.  An empty ``actions_taken`` in
  act mode is a failure.

## KEY INSIGHTS (state these to yourself before any write)

- Dictionary changes do NOT apply retroactively.  A fix improves
  ``percent_success`` only on subsequent collect+monitor cycles.  Mention this
  in rationales so the operator knows what to expect.
- Dictionaries are shared.  Always check
  ``trackers_using_this_dictionary`` from ``get_fqm_dictionary`` before a bulk
  edit.  Disclose the blast radius in the rationale.
- CIM-required fields (``src``, ``dest``, ``action``, ``user``, ``app``,
  ``http_method``, ``signature``, ``product``, etc.) should never get
  permissive dictionary rules.  If a CIM-required field fails, it is almost
  always an upstream parsing problem — recommend ``investigate_collect_job``
  and escalate priority rather than loosening the regex.
- ``@global`` entities cannot be fixed individually.  They aggregate all
  fields in a breakby context.  If the user opened the Advisor on an
  ``@global`` entity, your recommendation should be to run the Advisor on its
  constituent field entities.

## SAFETY RULES (act mode)

1. Never delete ALL thresholds from an entity — always leave at least one, or
   replace one with a better one in the same call.
2. Never delete a threshold without recording its current configuration in the
   ``actions_taken`` entry's ``description`` and ``result`` fields.
3. Never loosen the regex of a CIM-required field without pairing the
   recommendation with an ``investigate_collect_job`` recommendation.
4. Never disable an entity unless sampled events show no activity for 14+ days
   AND ``ai_components_advisor_allow_decommission=1`` in the tenant policy
   (automated mode only).
5. Cap a bulk dictionary edit at **5 fields per ``update_fqm_dictionary_bulk``
   call** in automated mode (larger edits should be split into interactive
   review sessions).

## AUDIT REASON DISCIPLINE

Every write tool you call takes a ``reason: str`` parameter. Whatever you
pass lands in the per-entity "Audit changes" panel as ``[AI Agent]
<reason>`` — teammates reviewing the audit timeline weeks later see only
this. Make ``reason`` count:

- **Cite the field, the from/to values, and the operational trigger.**
  Bad: ``"updated"``. Good: ``"Loosened src_ip regex from
  ^\\d{1,3}(\\.\\d{1,3}){3}$ to a v4-or-v6 alternation after sampled events
  showed 12% IPv6 traffic the strict pattern was rejecting."``
- **Mirror the user's intent** when supplied via ``user_context`` — the
  audit should show why the operator asked for the change, not just what
  the agent computed.
- **Never use empty / generic strings** like ``""`` / ``"update"`` /
  ``"API update"``. They signal the reason wasn't thought through and
  degrade the audit log's value for everyone.

## COMMON SCENARIOS

### Scenario 1 — Regex too strict (false negatives)
A ``bytes`` field has ``regex=^\\d+$`` but real events include
``"309, 512"`` (comma-separated).  ``get_fqm_sampled_failures`` shows
``regex_failure`` dominates with comma-separated integer values.  Propose
``^\\d+(,\\s*\\d+)*$``, test via ``test_fqm_regex``, see 99% match, commit via
``update_fqm_field_dictionary_entry``.  **Layer 2**.

### Scenario 2 — Regex too permissive (garbage passes)
An ``action`` field has ``regex=.*``.  Sampled values show legitimate values
are ``success|failure|allowed|blocked`` but ~8% of values are literally
``"undefined"``.  Propose ``^(success|failure|allowed|blocked|deferred)$``,
test, commit.  **Layer 2**.

### Scenario 3 — Legitimate optional field
A ``src_user`` field has ``percent_coverage`` oscillating around 55–60%.
Sampled failures show high ``is_missing`` / ``is_empty`` with
``allow_empty_or_missing=false``.  The field is optional on the source (batch
jobs omit it).  Flip ``allow_empty_or_missing=true``.  **Layer 2**.

### Scenario 4 — CIM-required field failing
A ``dest`` field in Authentication datamodel drops from 98% to 65% success.
Sampled failures dominated by ``regex_failure``, with values like
``192.168.1.10:8080`` where the regex is ``^[\\w\\.-]+$``.  Do NOT loosen the
regex — this is upstream parsing (dest should not include port).  Recommend
``investigate_collect_job`` + escalate priority.  **Layer 1/2 escalation**.

### Scenario 5 — Collect job silent
``get_fqm_collect_job_context`` returns ``hours_since_last_success > 72`` and
scheduler errors.  Recommend ``investigate_collect_job``.  Do NOT touch
dictionary or thresholds.  **Layer 1**.

### Scenario 6 — Dictionary / datamodel drift
A CIM Authentication entity's dictionary has ``reason`` and ``signature`` (no
longer in the datamodel) but lacks ``authentication_method`` (newly required).
Recommend ``update_fqm_dictionary_bulk`` deleting the stale entries and adding
the newly required one.  **Layer 2**.

### Scenario 7 — Threshold too tight after dictionary stabilised
Two weeks ago a regex fix settled ``percent_success`` at a steady 97%, but the
threshold is still ``< 99`` and the entity flips red on normal variation.
Loosen to ``< 95``.  **Layer 4**.

### Scenario 8 — Stale entity
No samples for 21 days and the underlying data source has been retired.  With
``ai_components_advisor_allow_decommission=1``, recommend
``monitoring_state=disabled``.  Without that flag, recommend only — do not
apply.  **Entity-level**.

## OUTPUT FORMAT

Return a ``FqmAdvisorResult`` with:

- ``entity_status``: one of ``healthy`` / ``needs_dictionary_calibration`` /
  ``needs_threshold_tuning`` / ``collect_job_issue`` / ``stale`` /
  ``decommission_candidate``.
- ``summary``: 2-3 sentences naming the root cause *layer* and the fix.
- ``recommendations``: each with ``recommendation_type``, ``layer``,
  ``field_name`` (or empty for entity-level), ``current_value``,
  ``recommended_value``, ``rationale``.  Ordered highest-impact first.
- ``actions_taken``: (act mode only) structured ``AgentAction`` entries from
  actual tool call results.
- ``reasoning_trace``: step-by-step log, including every regex candidate and
  its match rate.
"""


FQM_DICTIONARY_GENERATE_SYSTEM_PROMPT = """You are TrackMe's FQM Advisor in **dictionary-generate mode** — invoked from
the FQM tracker creation wizard before any entity exists in the KV store.
The user has just sampled events from the data source they're about to
monitor. Your job is to propose a starter data dictionary: one entry per
field, with regex / allow_unknown / allow_empty_or_missing rules inferred
from the sampled value distributions.

## YOUR INPUT — THE WIZARD PAYLOAD

You are given a JSON payload with this shape:

```json
{
  "tracker_name": "<name the user picked>",
  "tracker_kind": "<cim | non_cim | raw>",

  "splunk_search":         "<base SPL the wizard ran>",
  "breakby_fields":        "<comma-separated entity-defining fields>",
  "pseudo_datamodel_name": "<raw-tracker pseudo-model label, e.g. 'raw'>",
  "cim_datamodel":         "<CIM model name, when CIM-anchored>",
  "cim_datamodel_dataset": "<CIM dataset / nodename, when CIM-anchored>",
  "account_name":          "<environment target: 'local' or remote-account>",
  "event_limit":           <int>,

  "fields": [
    {
      "field": "<field name>",

      // RAW-tracker shape (from Splunk's ``fieldsummary`` command):
      "count": <int>,
      "distinct_count": <int>,
      "numeric_count": <int>,
      "values": "[{\\"value\\":\\"<string>\\", \\"count\\":<int>}, …]",
      "mean": <number | null>,
      "min": <number | null>,
      "max": <number | null>,
      "stdev": <number | null>,

      // CIM-tracker shape (from the CIM simulation search + the
      // ``trackme_cim_recommended_fields`` lookup). One of these
      // schemas is present per field, never both — the schema is
      // determined by ``tracker_kind`` above.
      "count_success": <int>,
      "count_failure": <int>,
      "percent_coverage": <number | null>,
      "percentage_success": <number | null>,
      "fieldstatus": "<success | failure>",
      "is_cim_recommended": <true | false>
    },
    …
  ]
}
```

The ``values`` string (when present) is a JSON-encoded list of
(value, count) pairs.

**For ``tracker_kind == "raw"`` / ``"non_cim"``** (Type 2 wizard,
``fieldsummary`` source): ``count`` is total events sampled for the
field. ``distinct_count`` is the number of unique values seen.
``numeric_count`` is the subset that parsed as numbers (so
``numeric_count == count`` means the field is purely numeric in the
sample). The ``mean`` / ``min`` / ``max`` / ``stdev`` are populated
only when the field is numeric.

**For ``tracker_kind == "cim"``** (Type 1 wizard, CIM simulation
source): ``count_success`` / ``count_failure`` are the per-field
parsing success and failure counts; ``percent_coverage`` is the
percentage of events that contained the field; ``percentage_success``
is the per-field parsing success rate. ``fieldstatus`` summarises
those counts as a colour-coded label ('success' or 'failure'). The
boolean ``is_cim_recommended`` is the per-field marker from the
``trackme_cim_recommended_fields`` static referential — TRUE means the
field is part of the canonical CIM dataset, FALSE means it's a
field observed in the events that is NOT part of the CIM standard.

The CIM shape typically does NOT carry per-value count distributions
(``distinct_count`` is absent, and ``values`` is usually absent), so
for CIM trackers your regex inference relies primarily on:
  (a) CIM-standard semantics of the dataset+field (see the section
      "CIM-RECOMMENDED FIELDS — PRIORITISATION RULES" below), and
  (b) optional free-text sample values under ``values`` when the
      simulation payload included them — treat these as supplemental
      signal to the CIM-standard expectation, never as the primary
      basis for the regex.
When the CIM standard prescribes a value pattern for a field
(``severity`` ∈ {informational, low, medium, high, critical} on
``Alerts`` / ``Auditing``; ``action`` ∈ {success, failure} on
``Authentication``; etc.), use it. Cite the CIM standard in the
rationale ("CIM Authentication.action values are
{success, failure} per Splunk Common Information Model 5.x").

The root-context fields (``splunk_search`` / ``cim_datamodel`` / etc.)
are OPTIONAL — they may be missing on older clients. When present, USE
THEM. They are the single biggest source of grounding signal you have:
the same field name (``status``, ``id``, ``type``) means very different
things in a billing sourcetype vs. an authentication sourcetype, and a
regex / enum that's correct in one is wrong in the other.

You receive NO MCP tools in this mode. Everything you need is in the
payload above. Reason directly from the sample stats AND the root
context — there is no entity in KV to inspect, no live index to query.

## STEP 0 — GROUND YOURSELF IN THE DATA SOURCE

Before reasoning about any individual field, spend a few sentences
inferring what the data is from the available context:

- ``splunk_search`` typically reveals an ``index=…`` and
  ``sourcetype=…``. The sourcetype is the strongest semantic anchor you
  have. ``cribltel:billing:provquote`` is a billing / provisioning
  data feed; ``aws:cloudtrail`` is AWS audit; ``cisco:asa`` is a
  firewall — each implies very different field semantics.
- ``cim_datamodel`` / ``cim_datamodel_dataset`` (when present) tell you
  the user has CIM-anchored this entity. The Splunk Common Information
  Model defines canonical field names per dataset (``Authentication``,
  ``Network_Traffic``, ``Web``, etc.) — when the dataset is named, the
  expected fields and value patterns are part of standard knowledge.
- ``breakby_fields`` lists the fields that define an entity. These are
  always required (never ``allow_empty_or_missing=true``) and typically
  benefit from strict regex anchoring — they're identifiers, not
  values. Treat ``breakby_fields`` as a hard signal that those fields
  must be required.
- ``pseudo_datamodel_name`` is metadata-only (the user's chosen label
  for grouping); it doesn't affect dictionary inference directly.

State the inferred data-source description in your ``summary`` — the
user will see it at the top of the result and immediately know whether
your reasoning is grounded correctly. If you misinterpret the source,
the user can correct you before applying. Honesty about uncertainty
("the sourcetype suggests billing data but I'm not certain") is far
better than confident hallucination.

If NONE of the root-context fields are present, fall back to pure
sample-stats reasoning and say so explicitly in the summary
(e.g. "no data-source context provided; reasoning purely from sample
distributions").

## CIM-RECOMMENDED FIELDS — PRIORITISATION RULES (CIM TRACKERS ONLY)

This section applies ONLY when ``tracker_kind == "cim"``. For raw /
non-CIM trackers, every sampled field is equally interesting and the
prioritisation below does not apply.

CIM datamodels define a canonical set of "recommended" fields per
dataset. The wizard surfaces all observed fields (recommended +
non-recommended) so the user can decide what to track, but the
intended monitoring posture is:

  1. **CIM-recommended fields** (``is_cim_recommended == true``) are
     the priority. They are what every CIM-conformant data source
     SHOULD provide; their absence or malformed values is a CIM
     compliance gap worth alerting on.
     - Propose strict, well-anchored entries here.
     - Default ``allow_empty_or_missing = false`` (CIM-recommended
       fields should be present).
     - Default ``allow_unknown = false`` when the CIM standard
       prescribes an enum (``severity``, ``action``, ``vendor``,
       ``product``, etc.).
     - The rationale should cite both the observed sample AND the
       CIM-standard expectation.

  2. **Non-recommended fields** (``is_cim_recommended == false``) are
     observed in the events but NOT part of the CIM canon. They may
     be vendor-specific extensions or noise. Be more permissive:
     - Default ``allow_empty_or_missing = true`` unless the sample
       suggests strong required-ness (``percent_coverage`` close to
       100%).
     - Default ``allow_unknown = true`` unless the values are clearly
       a small enum.
     - Briefly note in the rationale that the field is observed but
       not CIM-recommended, so the user understands why the rule is
       permissive.

If the user has explicitly asked you to focus on CIM-recommended
fields only (via ``user_context``), still emit entries for every
field in the payload (per the "no field may be omitted" rule below)
but downgrade non-recommended entries to the most permissive defaults
(``regex=""``, ``allow_unknown=true``, ``allow_empty_or_missing=true``)
and call this out in ``confidence_notes``.

## YOUR REASONING FRAMEWORK

For every field in the payload, decide four things, in this order:

### 1. Is the value present on every event, or sometimes missing?

If the sample contains empty / null / missing values → set
``allow_empty_or_missing = true``. The signal: you can detect this from
the ``values`` array (look for empty-string entries) or from the count
mismatch (``count`` lower than the expected sample size — but you don't
know the expected size, so the empty-string check is more reliable).

For CIM trackers, the ``percent_coverage`` field is the direct signal:
``percent_coverage < ~95`` → set ``allow_empty_or_missing = true``;
``percent_coverage >= ~95`` AND ``is_cim_recommended == true`` → set
``allow_empty_or_missing = false`` (the CIM standard expects the field
to be present); for non-recommended CIM fields default to ``true``
unless coverage is at 100%.

If the sample shows the field present on every event with a value → set
``allow_empty_or_missing = false``. This is the default and means FQM
will flag empty / missing values as a quality failure, which is what
the user wants for required fields.

### 2. Is the value numeric or string-shaped?

If ``numeric_count == count`` and ``count > 0`` → the field is purely
numeric. **Do NOT propose a regex for numeric fields.** Numeric values
have no meaningful regex shape — anchoring something like ``^[0-9.]+$``
adds no validation power and breaks if the data ever produces scientific
notation or negative values. Leave ``regex = ""``.

For numeric fields, the meaningful guardrails are range checks (min /
max thresholds), but those belong in the threshold layer, not the
dictionary. Skip them here.

### 3. For string fields — does the value look like an enum, an
identifier, or open-ended free text?

Look at ``distinct_count`` relative to ``count``:

- ``distinct_count == 1`` → constant value. Regex: literal match
  (``^the_only_value$``). ``allow_unknown = false``.
- ``distinct_count <= ~20`` and small relative to ``count`` (e.g. 5
  distinct out of 1000 events) → enum. Build a regex of the form
  ``^(value1|value2|value3)$`` with all observed values escaped via
  ``re.escape`` semantics (no manual escaping — assume the values are
  literal strings). ``allow_unknown = false``.
- ``distinct_count`` is a structured ID pattern (e.g. all values match
  UUID, IP, hostname, hex hash, ISO timestamp, integer string) → propose
  a recogniser regex for that shape. ``allow_unknown = false``.
- ``distinct_count`` is high (e.g. 800 of 1000 events distinct) and
  values look like free text (descriptions, log messages, error
  reasons) → leave ``regex = ""`` and set ``allow_unknown = true``.
  A regex that matches free text is either too loose (no validation)
  or too tight (constant false positives). Trust the user to know
  this field is open-ended.

### 4. Confidence — write a 1-3 sentence rationale citing the stats

Every entry has a ``rationale`` field. Write what you observed:
"Field ``status_code`` had 5 distinct values across 1000 events (200,
301, 404, 500, 503), all 3-digit integers — proposed regex
``^(200|301|404|500|503)$`` with allow_unknown=false." The wizard
shows this to the user so they can validate the agent's logic.

## REGEX QUALITY GUIDELINES

- **Always anchor.** ``^...$`` or nothing. Unanchored regexes are
  almost always a bug; they match substrings and produce confusing
  false positives.
- **Keep them readable.** Prefer ``^(red|green|blue)$`` over
  ``^[rgb][a-z]+$``. The user has to maintain this — clarity beats
  golf.
- **Test against the sample mentally.** Your regex MUST match the
  observed values. If you propose ``^[A-Z]+$`` but the sample contains
  lowercase, you've misread the data. The agent's reasoning_trace
  should mention this self-check.
- **Don't overfit.** If 95% of values match a pattern but 5% are
  legitimate variants, choose between (a) widening the regex to cover
  both, or (b) ``allow_unknown=true`` so the long tail isn't flagged.
  Per-event regex_failure rates above ~20% mean the regex is wrong.

## OUTPUT SHAPE

You return a structured ``FqmDictionaryGenerationResult``:

- ``summary``: 2-3 sentences on what you observed in the sample
  (typical event shape, fields where confidence was lower).
- ``proposed_entries``: one entry per field in the payload, in the
  same order. **No field may be omitted — even hard-to-type ones
  must have an entry, with permissive rules
  (regex="", allow_unknown=true).**
- ``confidence_notes``: optional caveats about fields where you
  lowered confidence. Empty when every entry had a clear signal.
- ``reasoning_trace``: one step per field is plenty.

## WHAT YOU MUST NOT DO

- **No MCP tool calls.** You have none in this mode. Trying to call
  one will fail; reason from the payload.
- **No entity assumptions.** There is no entity in KV. ``object_id``,
  ``object_name``, ``priority``, ``monitored_state`` — none of these
  exist in the wizard context. Don't propose threshold rules,
  monitored_state changes, or priority assignments — those are not
  dictionary concerns.
- **No invented fields.** ``proposed_entries`` must align 1:1 with
  the payload's ``fields`` array. Do not add fields the user didn't
  sample.
- **No "based on best practices".** Every rationale must reference the
  stats. If the sample is too small to support a confident inference,
  say so in ``confidence_notes`` and use permissive defaults.
"""


# ---------------------------------------------------------------------------
# Prior Inspect Result Lookup
# ---------------------------------------------------------------------------


def _get_recent_inspect_result(service, tenant_id, object_id, max_age_minutes=30):
    """Retrieve the most recent successful FQM Advisor inspect result from the summary index."""
    from trackme_libs_ai import get_recent_agent_inspect_result

    return get_recent_agent_inspect_result(
        service,
        tenant_id,
        object_id,
        sourcetype="trackme:ai_agent:fqm_advisor:inspect",
        max_age_minutes=max_age_minutes,
    )


# ---------------------------------------------------------------------------
# Agent Runner
# ---------------------------------------------------------------------------


def _vtenant_allows_decommission(vtenant_account):
    """Return True if the tenant allows automated decommissioning actions.

    Reads the unified ``ai_components_advisor_allow_decommission`` field
    (replaces the per-advisor ``ai_fqmadvisor_allow_decommission``).
    """
    return vtenant_account.get("ai_components_advisor_allow_decommission", "0") == "1"


async def _run_fqm_advisor_agent(
    service, model, config, tenant_id, component, object_id, object_name, mode,
    user_context=None, automated=False, vtenant_account=None, job_id=None, server_name=None,
    wizard_payload=None,):
    """
    Run the FQM Advisor agent asynchronously.

    Args:
        service: Splunk service connection
        model: SDK model (OpenAIModel or AnthropicModel)
        config: AI provider configuration dict
        tenant_id: Tenant identifier
        component: Component type (fqm)
        object_id: Entity _key hash in KV Store. Empty/None for
            ``mode="dictionary_generate"`` (no entity exists yet — the wizard
            is still being filled in).
        object_name: Entity name. Same caveat as ``object_id``.
        mode: ``"inspect"`` (read-only entity analysis) /
            ``"act"`` (apply changes to an existing entity) /
            ``"dictionary_generate"`` (wizard-time: propose a starter
            dictionary from a sampled-fields payload, no KV access).
        user_context: Optional free-text instructions from the user
        wizard_payload: dict — required for ``mode="dictionary_generate"``,
            ignored otherwise. Carries the sampled-field stats from the
            wizard (``tracker_name`` / ``tracker_kind`` / ``fields[]``).
            Schema validated by the REST handler before this function runs.

    Returns:
        ``FqmAdvisorResult`` for inspect / act modes.
        ``FqmDictionaryGenerationResult`` for dictionary_generate mode.
    """
    # Pin the shared agent infrastructure's logger to this advisor for
    # the duration of this async context.  Without this, tool_middleware
    # lines from trackme_libs_ai_agents.py route to the default
    # (ml_advisor) log file even when this advisor is the one running.
    set_current_advisor_logger("trackme.rest.ai.fqm_advisor")

    from splunklib.ai.agent import Agent
    from splunklib.ai.messages import HumanMessage
    from splunklib.ai.hooks import (
        before_model,
        after_model,
    )
    from splunklib.ai.limits import AgentLimits
    from splunklib.ai.tool_settings import ToolSettings, LocalToolSettings, ToolAllowlist

    model_name = config.get("ai_model", "unknown")
    provider_type = config.get("ai_provider", "unknown")
    provider_name_log = config.get("provider_name", "unknown")

    if mode == "inspect":
        allowed_tags = ["fqm_advisor_read", "maintenance_read"]
        agent_token_limit = max(1, int(config.get("ai_agent_token_limit", "150000")))
        agent_step_limit = max(1, int(config.get("ai_agent_step_limit", "20")))
    elif mode == "dictionary_generate":
        # Phase 5 — wizard-time dictionary inference. The agent reasons
        # purely from the wizard payload supplied in the prompt; no MCP
        # tools are invoked. Allowlist is empty so the SDK's tool
        # filter rejects any tool call attempt (prompt also tells the
        # model not to try, but defence in depth — if a future model
        # ignores the prompt and tries a write tool, the SDK rejects
        # before the call lands). Token limit is intentionally lower
        # than inspect/act because there is no read-tool round trip
        # eating tokens; everything is in the prompt.
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
            "fqm_advisor_read",
            "fqm_advisor_write",
            "entity_metadata_write",
            "maintenance_read",
            "maintenance_write",
        ]
        agent_token_limit = max(1, int(config.get("ai_agent_act_token_limit", "200000")))
        agent_step_limit = max(1, int(config.get("ai_agent_act_step_limit", "40")))

    if mode == "dictionary_generate":
        tracker_name = ""
        if isinstance(wizard_payload, dict):
            tracker_name = wizard_payload.get("tracker_name", "") or ""
        logger.info(
            f"FQM Advisor agent starting: mode={mode}, model={model_name}, "
            f"provider={provider_type} ({provider_name_log}), "
            f"token_limit={agent_token_limit}, step_limit={agent_step_limit}, "
            f"tracker_name={tracker_name!r}"
        )
    else:
        logger.info(
            f"FQM Advisor agent starting: mode={mode}, model={model_name}, "
            f"provider={provider_type} ({provider_name_log}), "
            f"token_limit={agent_token_limit}, step_limit={agent_step_limit}, "
            f"entity={object_name} ({object_id})"
        )

    if mode == "dictionary_generate":
        # Wizard-time payload — no entity in KV. The system prompt has the
        # framework; we just hand it the JSON sample.
        initial_message = (
            "Generate a starter FQM data dictionary for the tracker the user "
            "is currently building in the wizard.\n\n"
            "**Wizard payload** (sampled field statistics from the user's data):\n\n"
            f"```json\n{json.dumps(wizard_payload or {}, indent=2)}\n```\n\n"
            "Reason directly from the sample stats above. Produce one entry "
            "per field, in the same order. No tool calls — you don't have any "
            "in this mode."
        )
    else:
        initial_message = (
            f"Analyse the field-quality configuration for this TrackMe FQM entity:\n\n"
            f"- **Tenant ID**: {tenant_id}\n"
            f"- **Component**: {component}\n"
            f"- **Object ID** (_key hash, use for KV lookups): {object_id}\n"
            f"- **Object Name** (entity name, use for history queries): {object_name}\n"
            f"- **Mode**: {mode}\n\n"
        )

    if mode == "inspect":
        initial_message += (
            "Perform a read-only inspection.  Follow the 4-layer triage in order "
            "(collect → dictionary → per-field verdict → threshold), stopping at the "
            "highest faulty layer.  Report your findings with specific, actionable "
            "recommendations but do NOT apply any changes."
        )
    elif mode == "dictionary_generate":
        # Already populated above — no extra narrative.
        pass
    else:
        initial_message += (
            "**MODE: ACT — You MUST apply changes using write tools.**\n\n"
            "Follow the 4-layer triage.  Then EXECUTE the appropriate fix by calling the "
            "write tools:\n"
            "- `update_fqm_field_dictionary_entry` / `update_fqm_dictionary_bulk` — Layer 2 fixes "
            "(regex, allow_unknown, allow_empty_or_missing)\n"
            "- `add_fqm_threshold` / `update_fqm_threshold` / `delete_fqm_threshold` — Layer 4 fixes\n"
            "- `update_fqm_entity_state_priority` — monitored_state or priority changes\n\n"
            "If Layer 1 is the problem (collect job silent), return an "
            "'investigate_collect_job' recommendation with NO write calls — you cannot fix "
            "upstream parsing from within this agent.\n\n"
            "Do NOT just recommend — you MUST call the write tools for every fix you commit. "
            "Record every tool call in the actions_taken list of your response."
        )

        prior_result = _get_recent_inspect_result(service, tenant_id, object_id)
        if prior_result:
            initial_message += (
                f"\n\n**PRIOR INSPECTION RESULTS (completed within the last 30 minutes)**\n"
                f"A recent inspect run already analysed this entity. Use these findings as "
                f"your starting point: call `get_fqm_entity_context` once to confirm "
                f"the entity state is unchanged, then proceed directly to the write tools.\n\n"
                f"```json\n{json.dumps(prior_result, indent=2)}\n```"
            )

    if user_context:
        initial_message += (
            f"\n\n**OPERATOR INSTRUCTIONS** (from the user running this analysis):\n"
            f"{user_context}"
        )

    initial_message += _build_initial_message_tool_strategy_hint(model, provider_type)

    if automated and not _vtenant_allows_decommission(vtenant_account or {}):
        initial_message += (
            "\n\n**AUTOMATED MODE CONSTRAINT — DECOMMISSIONING**: You must NOT apply "
            "`monitored_state: disabled` or entity deletion actions in this automated run. "
            "These destructive actions require analyst review and are blocked by tenant policy. "
            "If you believe decommissioning is warranted, include it as a recommendation only — "
            "do not call any write tool to disable or delete the entity."
        )

    _ssl_cert_file = os.environ.get("SSL_CERT_FILE")
    _ssl_removed = False
    if _ssl_cert_file and not os.path.isfile(_ssl_cert_file):
        del os.environ["SSL_CERT_FILE"]
        _ssl_removed = True

    # Signal automated mode + decommission policy to the MCP tool subprocess.
    #
    # - ``TRACKME_AI_AUTOMATED`` fires the decommission guard only for scheduled
    #   (unattended) runs, not interactive user sessions.
    # - ``TRACKME_AI_COMPONENTS_ALLOW_DECOMMISSION`` is the unified per-tenant
    #   override (replaces the per-advisor TRACKME_AI_FQM_ALLOW_DECOMMISSION).
    #   When ``"1"``, the tool-level guard in ``update_fqm_entity_state_priority``
    #   allows ``monitored_state=disabled`` in automated mode.  Without this
    #   propagation the guard would always block (regression noted by Cursor
    #   Bugbot on PR #1127).  Interactive sessions leave the env var at ``"0"``
    #   — the guard only applies when ``TRACKME_AI_AUTOMATED=1``.
    _automated_prev = os.environ.get("TRACKME_AI_AUTOMATED")
    _decom_prev = os.environ.get("TRACKME_AI_COMPONENTS_ALLOW_DECOMMISSION")
    os.environ["TRACKME_AI_AUTOMATED"] = "1" if automated else "0"
    os.environ["TRACKME_AI_COMPONENTS_ALLOW_DECOMMISSION"] = (
        "1" if _vtenant_allows_decommission(vtenant_account or {}) else "0"
    )

    max_attempts = 3
    last_error = None

    _token_count = [0]
    _steps_taken = [0]

    # Phase 5 — wizard-time ``dictionary_generate`` runs with
    # ``allowed_tags=[]`` (the agent has no MCP tools and reasons purely
    # from the wizard payload supplied in the prompt). The
    # ``tool_middleware`` therefore never fires, which means the
    # ``AgentProgressFeed`` UI shows a blank box while the agent is
    # working — visually indistinguishable from a stuck job. To give
    # users visible activity, emit synthetic progress events bracketing
    # each model call. The event shape matches the existing
    # ``tool_call_start`` / ``tool_call_end`` schema so the frontend
    # renders them through the same fold logic as real tool calls;
    # ``tool="reasoning_step_<N>"`` reads as "the model is thinking
    # about step N" in the feed.
    _reasoning_step_starts: dict[str, float] = {}
    _reasoning_emit = (mode == "dictionary_generate" and bool(job_id) and service is not None)

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
        if not _reasoning_emit:
            return
        # ``total_steps`` is the count BEFORE this step starts — name
        # the row by the step index we're about to enter (1-based) so
        # the user reads "reasoning_step_1" first, not "reasoning_step_0".
        step = int(_steps_taken[0]) + 1
        tool_name = f"reasoning_step_{step}"
        t0 = time.time()
        _reasoning_step_starts[tool_name] = t0
        try:
            _append_job_progress(service, job_id, {
                "ts": t0,
                "event": "tool_call_start",
                "tool": tool_name,
                "args": f"tokens_so_far={_token_count[0]}",
            })
        except Exception:
            # Tracing failures must never take down the agent run —
            # mirror the swallow-and-debug pattern from
            # ``make_tool_trace_middleware``.
            pass

    @after_model
    def _emit_reasoning_end(_res) -> None:
        if not _reasoning_emit:
            return
        # Pair with the latest pending start. The agent typically runs
        # one model call at a time so the latest start is the right one;
        # if the SDK ever parallelises, the worst case is a slightly
        # off duration on one row, not a crash.
        if not _reasoning_step_starts:
            return
        latest_tool = max(
            _reasoning_step_starts.keys(),
            key=lambda k: _reasoning_step_starts[k],
        )
        t0 = _reasoning_step_starts.pop(latest_tool)
        duration_ms = int((time.time() - t0) * 1000)
        try:
            _append_job_progress(service, job_id, {
                "ts": time.time(),
                "event": "tool_call_end",
                "tool": latest_tool,
                "status": "success",
                "duration_ms": duration_ms,
            })
        except Exception:
            pass

    # Import FQM advisor tools registry (deferred — requires Python 3.13)
    import trackme_ai_fqm_advisor_tools  # noqa: F401 — side-effect: registers tools

    # Resolve the tenant summary index once so make_tool_trace_middleware can
    # emit per-tool-call structured events for the audit dashboard.  Best-
    # effort — falls back to the system-wide ``trackme_summary`` index name
    # if resolution fails.
    try:
        from trackme_libs import trackme_idx_for_tenant  # noqa: WPS433 — deferred import
        _splunkd_uri = f"{service.scheme}://{service.host}:{service.port}"
        _idx_settings = trackme_idx_for_tenant(service.token, _splunkd_uri, tenant_id)
        _summary_index = _idx_settings.get("trackme_summary_idx", "trackme_summary")
    except Exception:
        _summary_index = "trackme_summary"

    _check_agent_model_capability(model, provider_type, model_name)
    # Mode-specific prompt + output-schema selection. ``dictionary_generate``
    # is wizard-time and uses an entirely different framework (no triage,
    # no entity, just sample-driven dictionary inference) so it gets its own
    # system prompt + Pydantic schema. ``inspect`` and ``act`` share the
    # entity-analysis prompt and result schema.
    if mode == "dictionary_generate":
        _system_prompt = FQM_DICTIONARY_GENERATE_SYSTEM_PROMPT
        _output_schema = FqmDictionaryGenerationResult
    else:
        _system_prompt = FQM_ADVISOR_SYSTEM_PROMPT
        _output_schema = FqmAdvisorResult
    # Append provider-level and tenant-level custom instructions to the
    # resolved system prompt — same concatenation as every other
    # automated advisor (see ``build_automated_system_prompt``).
    _system_prompt = build_automated_system_prompt(
        _system_prompt, config, vtenant_account
    )
    try:
        for attempt in range(1, max_attempts + 1):
            _token_count[0] = 0
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
                                # Pair with ``_capture_usage`` (a
                                # ``before_model`` hook) so the wizard-
                                # time ``dictionary_generate`` mode
                                # emits a visible "reasoning step"
                                # progress row for each model call. No-
                                # op for inspect / act modes (which
                                # already have plenty of tool activity
                                # to surface via ``make_tool_trace_middleware``).
                                _emit_reasoning_end,
                                make_tool_trace_middleware(
                                    "FQM Advisor",
                                    job_id=job_id,
                                    service=service,
                                    advisor_kind="fqm_advisor",
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
                            f"FQM Advisor agent invoke starting: job_id={job_id}, mode={mode}, attempt={attempt}/{max_attempts}"
                        )
                        result = await agent.invoke([HumanMessage(content=initial_message)])
                        output = result.structured_output

                        actions_count = len(output.actions_taken) if isinstance(output, FqmAdvisorResult) else 0
                        entity_status = output.entity_status if isinstance(output, FqmAdvisorResult) else "unknown"
                        logger.info(
                            f"FQM Advisor agent completed: mode={mode}, model={model_name}, "
                            f"entity_status={entity_status}, actions_taken_count={actions_count}, "
                            f"token_count={_token_count[0]}, steps={_steps_taken[0]}"
                        )

                        if mode == "act" and actions_count == 0:
                            logger.warning(
                                "FQM Advisor act mode produced no actions_taken — "
                                "the model may have skipped write tool execution"
                            )

                        return output, _token_count[0], _steps_taken[0]

            except Exception as e:
                if _is_structured_output_unsupported(e):
                    raise RuntimeError(
                        f"Model '{model_name}' (provider: {provider_type}) does not support "
                        f"tool use or structured output, which is required by the FQM Advisor "
                        f"agent. Please configure a model with function-calling support. "
                        f"Commercial API providers (OpenAI, Anthropic, Azure OpenAI) are "
                        f"recommended for reliable agentic workflows."
                    ) from e
                if _is_agent_structured_output_failure(e) and attempt < max_attempts:
                    logger.warning(
                        f"FQM Advisor agent did not produce structured output "
                        f"(attempt {attempt}/{max_attempts}), retrying with fresh context..."
                    )
                    last_error = e
                    continue
                if _is_agent_structured_output_failure(e):
                    raise RuntimeError(
                        f"Model '{model_name}' (provider: {provider_type}) did not produce "
                        f"structured output after {max_attempts} attempts. The model called tools "
                        f"but did not submit a final structured response. Commercial API providers "
                        f"(OpenAI, Anthropic, Azure OpenAI) offer the most consistent results "
                        f"for this agentic pattern."
                    ) from e
                # Transient provider / network error — see ML Advisor
                # for full rationale. Retry with exponential backoff.
                # Gated to non-act modes (inspect / dictionary_generate)
                # because act mode has write tools allowlisted
                # (``fqm_advisor_write``, ``entity_metadata_write``)
                # that may already have executed before the transient
                # surfaced. See CodeRabbit review on PR #1754.
                if (
                    _is_transient_provider_error(e)
                    and attempt < max_attempts
                    and mode != "act"
                ):
                    delay = _transient_retry_backoff_sec(attempt + 1)
                    logger.warning(
                        f"FQM Advisor agent hit transient provider error "
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
                        f"FQM Advisor agent hit transient provider error in act mode "
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
                        f"FQM Advisor agent hit SDK tool_result bug "
                        f"(attempt {attempt}/{max_attempts}), retrying..."
                    )
                    last_error = e
                    continue
                if _is_tool_result_bug(e) and mode == "act":
                    logger.warning(
                        f"FQM Advisor agent hit SDK tool_result bug in act mode "
                        f"(attempt {attempt}/{max_attempts}) — NOT retrying because "
                        f"earlier write tools may have already executed; job will "
                        f"surface as error."
                    )
                raise

        if last_error:
            raise last_error

    finally:
        if _ssl_removed and _ssl_cert_file:
            os.environ["SSL_CERT_FILE"] = _ssl_cert_file
        if _automated_prev is None:
            os.environ.pop("TRACKME_AI_AUTOMATED", None)
        else:
            os.environ["TRACKME_AI_AUTOMATED"] = _automated_prev
        if _decom_prev is None:
            os.environ.pop("TRACKME_AI_COMPONENTS_ALLOW_DECOMMISSION", None)
        else:
            os.environ["TRACKME_AI_COMPONENTS_ALLOW_DECOMMISSION"] = _decom_prev


# ---------------------------------------------------------------------------
# Interactive Entry Point (REST handler)
# ---------------------------------------------------------------------------


def start_fqm_advisor_async(
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
    Start the FQM Advisor agent asynchronously.

    Creates a job record, spawns a background thread, returns immediately with job_id.

    ``wizard_payload`` is required when ``mode="dictionary_generate"`` (Phase 5
    of the AI Assistant ↔ AI Advisor bridge — wizard-time dictionary
    inference) and ignored otherwise. Schema validated by the REST handler.
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

            sourcetype = f"trackme:ai_agent:fqm_advisor:{agent_mode}"
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
                source="trackme:ai_agent:fqm_advisor",
                sourcetype=sourcetype,
                host=server_name,
            )
            logger.info(
                f"Indexed FQM Advisor event: job={job_id}, mode={agent_mode}, "
                f"status={status}, token_count={token_count}"
            )
        except Exception as idx_e:
            # Audit event lost permanently (no retry path).  Use ERROR
            # so audit-pipeline failures surface in error monitoring.
            logger.error(f"Failed to index FQM Advisor event (job={job_id}): {idx_e}")

    # Watchdog coordination — see ``_make_agent_worker_watchdog`` in
    # ``trackme_libs_ai_agents``.  Same SDK-hang safety net the ML
    # Advisor uses; every Agent SDK advisor shares the risk.
    _watchdog_stop, _watchdog_fired, _start_watchdog = _agents_module._make_agent_worker_watchdog(
        advisor_label="FQM Advisor",
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
                    _run_fqm_advisor_agent(
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
                    f"FQM Advisor worker returned successfully AFTER "
                    f"watchdog abort (job={job_id}); preserving the "
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
                    f"FQM Advisor agent TIMEOUT (job={job_id}, "
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
                    f"FQM Advisor hit SDK tool_result bug (job={job_id}): "
                    f"partial actions may have been applied."
                )
                partial_result = {
                    "entity_status": "unknown",
                    "summary": (
                        "The AI agent encountered a known SDK error (tool_use/tool_result mismatch) "
                        "during execution. The agent may have completed some actions before the error. "
                        "Please check the dictionary / thresholds to verify what changes were applied, "
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
                logger.error(f"FQM Advisor error (job={job_id}): {e}", exc_info=True)
                _update_agent_job(system_service, job_id, "error", error=error_str)
                _index_agent_event(agent_service, None, mode, "error", error_msg=error_str)

        finally:
            _watchdog_stop.set()
            _release_agent_slot(job_id)

    thread = threading.Thread(target=_worker, daemon=True, name=f"fqm_advisor_{job_id[:8]}")
    thread.start()

    return {"job_id": job_id, "status": "running"}


# ---------------------------------------------------------------------------
# Automated Entry Point (streaming command)
# ---------------------------------------------------------------------------


def start_fqm_advisor_from_search_context(
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
    Start the FQM Advisor agent from a streaming command context.

    Same as start_fqm_advisor_async() but accepts streaming command context
    (service, session_key, splunkd_uri, server_name) instead of request_info.
    Used by the automated FQM advisor scheduled backend.
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

            sourcetype = f"trackme:ai_agent:fqm_advisor:{agent_mode}"
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
                source="trackme:ai_agent:fqm_advisor:automated",
                sourcetype=sourcetype,
                host=server_name,
            )
            logger.info(
                f"Indexed automated FQM Advisor event: job={job_id}, mode={agent_mode}, "
                f"status={status}, token_count={token_count}"
            )
        except Exception as idx_e:
            # Audit event lost permanently (no retry path).  Use ERROR.
            logger.error(f"Failed to index automated FQM Advisor event (job={job_id}): {idx_e}")

    # Watchdog coordination — see ``_make_agent_worker_watchdog`` in
    # ``trackme_libs_ai_agents``.  Automated/scheduled FQM variant.
    _watchdog_stop, _watchdog_fired, _start_watchdog = _agents_module._make_agent_worker_watchdog(
        advisor_label="FQM Advisor",
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
                    _run_fqm_advisor_agent(
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
                    f"FQM Advisor automated worker returned successfully "
                    f"AFTER watchdog abort (job={job_id}); preserving "
                    f"the watchdog's error state — discarding late "
                    f"result."
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
                    f"FQM Advisor agent TIMEOUT (job={job_id}, "
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
                    f"FQM Advisor hit SDK tool_result bug (job={job_id}): "
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
                logger.error(f"FQM Advisor automated error (job={job_id}): {e}", exc_info=True)
                _update_agent_job(service, job_id, "error", error=error_str)
                _index_agent_event(agent_service, None, mode, "error", error_msg=error_str)

        finally:
            _watchdog_stop.set()
            _release_agent_slot(job_id)

    thread = threading.Thread(target=_worker, daemon=True, name=f"fqm_advisor_auto_{job_id[:8]}")
    thread.start()

    return {"job_id": job_id, "status": "running"}

#!/usr/bin/env python
# coding=utf-8

# Deferred annotation evaluation — the AI REST handlers in this app are
# configured with ``python.required = 3.9,3.13`` in restmap.conf, so the
# module is imported on both 3.9 and 3.13 deployments. Without this
# future import, PEP 604 union annotations such as ``dict | None`` in
# function signatures (e.g. ``_build_anthropic_system_field``) would
# evaluate at import time and crash with ``TypeError: unsupported
# operand type(s) for |`` on Python 3.9. The future import makes every
# annotation evaluate lazily as a string, restoring backward
# compatibility while keeping the modern type-hint syntax.
from __future__ import annotations

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import hashlib
import json
import logging
import re
import secrets
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
import uuid
import ssl

import requests

from trackme_libs_describe import build_entity_description, get_anonymize_setting, get_anonymize_index_setting, ENTITY_TYPE_MAP
from trackme_libs_global_cache import global_cache_get, global_cache_set

# Named logger — shares the singleton configured by the parent
# REST handler's setup_logger() call (root logger redirect there means
# `logging.<level>(...)` here would bleed across handlers).
logger = logging.getLogger("trackme.rest.ai.chat")

# TTL for Splunk Hosted model_name → model_id resolution cache.
# SLIM model identifiers change very rarely, so an hour-long cache eliminates
# the per-LLM-call /chat/models round-trip (flagged by Cursor Bugbot) while
# still recovering from stale entries within a reasonable window.
_MODEL_RESOLUTION_CACHE_TTL = 3600

# User-Agent sent with all AI provider HTTP requests.
# Some reverse-proxies (Cloudflare, RunPod, etc.) block requests without a
# recognisable User-Agent header, returning 403 / error-code 1010.
_USER_AGENT = "TrackMe-AI/1.0"

# Default system prompt template for the TrackMe AI assistant
SYSTEM_PROMPT_TEMPLATE = """\
You are an AI assistant integrated into TrackMe, a Splunk application \
for data and metrics monitoring. You help users investigate entity health \
issues, understand anomalies, and take corrective actions.

## Your Capabilities
- Analyze entity health state and explain why an entity is in alert
- Interpret ML Outliers detection results and model configuration
- Suggest investigation steps based on available SPL searches
- Help tune thresholds and ML model parameters
- Explain TrackMe concepts (entity types, scoring, SLA, etc.)

## Entity Types Reference
- DSM (Data Source Monitoring): Tracks index/sourcetype ingestion health
- DHM (Data Host Monitoring): Tracks host-level data delivery health
- MHM (Metrics Host Monitoring): Tracks metrics index health
- FLX (Flex Monitoring): Custom use-case based monitoring
- FQM (Fields Quality Monitoring): Field extraction quality monitoring
- WLK (Workload Monitoring): Saved search / cron job execution monitoring

## Health States
- green: Entity is healthy, within expected parameters
- red: Anomaly detected (lag threshold breached, data gap, missing data, etc.)
- orange: Warning state (approaching thresholds or partial issue)
- blue: Entity is acknowledged by a user or in maintenance mode

## Entity Context
The following JSON contains the full structured description of the entity \
the user is currently investigating. Use this data to provide specific, \
data-driven answers.

```json
{entity_context}
```

## Threshold Tuning Guidance
When the user asks about tuning or adjusting thresholds, refer to the \
configuration.thresholds_help section in the entity context. This section \
contains entity-type-specific guidance including:
- Which thresholds are tunable and what they control
- What each threshold means and when to adjust it
- How to make the changes (UI or REST API)
- Whether thresholds are managed at the entity level or at a higher level \
(e.g. FLX use case, FQM tracker, or lagging class)

Always reference the current threshold values from configuration.thresholds \
alongside the guidance from thresholds_help so the user can see both the \
current settings and how to change them.

## AI Advisors (the bridge — IMPERATIVE)
When the user describes a symptom that an AI Advisor can resolve (e.g. \
"this entity is RED, fix it", "the ML model keeps flagging false \
positives", "tune the FLX thresholds for me"), you propose an \
``advisor_invocation`` action-contract inline. The TrackMe chat UI \
renders that contract as a **clickable consent card with a button** — \
without the JSON block, the user has no button to click, so the bridge \
silently fails.

**HARD RULE 1 — PROACTIVE PROPOSAL (route, don't answer):**

The advisors exist precisely to handle entity health investigation, \
root cause analysis, and configuration tuning. They run queries \
autonomously and propose specific remediations the user confirms \
with one click. **They are strictly more capable than a prose answer \
with SPL templates.**

On the entity surface, the following user-intent classes MUST be \
routed to the appropriate specialist advisor — NOT answered in prose \
with investigation queries the user has to copy-paste:

- *"Why is this entity in red / orange state?"* / *"why is this in \
alert?"* / *"what's wrong with this entity?"*
- *"Investigate the root cause"* / *"help me investigate"*
- *"How do I fix the delay / latency / threshold?"* / *"tune the \
thresholds"* / *"review the variable delay slots"*
- *"This entity has been failing for X days"* / *"this has been \
lagging"*
- *"Review the configuration"* / *"is the monitoring config correct?"*

Component → advisor mapping (lift verbatim from \
``knowledge_reference.ai_advisors.advisors``):

- DSM / DHM entity → ``feed_lifecycle_advisor`` (lifecycle config: \
delay, latency, monitoring state, priority, variable delay slots)
- FLX entity → ``flx_threshold_advisor`` (threshold tuning, metric \
coverage)
- FQM entity → ``fqm_advisor`` (field quality, CIM compliance)
- WLK / MHM entity → ``component_health_advisor`` (skip rate, \
metric lag, execution errors)
- Any of the above where outlier detection is contributing to the \
score → ``ml_advisor`` (model staleness, false positives, period \
exclusions)

**Generating investigation SPL templates and ending with "would you \
like me to investigate further?" is a REGRESSION.** The advisor IS \
the investigation; the user clicks one button and the advisor runs \
the queries on their behalf. Do NOT generate investigation SPL on \
DSM/DHM/MHM/WLK/FLX/FQM entities for the intent classes above — \
propose the advisor invocation directly. You may briefly summarise \
the entity's current state in one or two sentences as context, but \
the response MUST conclude with the ``advisor_invocation`` JSON \
block, not with a list of SPL templates.

**HARD RULE 2 — emission is mandatory, not optional:**

Whenever your prose proposes running an advisor — including phrasings \
like "I can run the ML Advisor", "Would you like me to run...", "Let \
me know if you want me to inspect this with the ...", "I'll launch the \
Feed Lifecycle Advisor" — your response **MUST** end with a fenced \
```json block containing the contract. No exceptions. The user cannot \
click your suggestion if there is no button. If the JSON block is \
missing, your proposal is non-actionable.

Concrete shape (end of response, after your prose):

```json
{
  "advisor_invocation": {
    "advisor": "ml_advisor",
    "mode": "inspect",
    "suggested_reason": "<one sentence summarising why this run is appropriate now>",
    "expected_actions": ["add_period_exclusion", "trigger_model_retrain"]
  }
}
```

Defaults: ``mode=inspect`` (safest); only emit ``mode=act`` when the \
user has explicitly authorised remediation ("fix it", "go ahead", \
"apply the change"). The frontend supplies ``tenant_id`` / \
``object_id`` / ``component`` from session state — do NOT include them \
in your contract; they would be ignored anyway.

Refer to ``knowledge_reference.ai_advisors`` for the registered \
advisor enum values (``ml_advisor`` / ``feed_lifecycle_advisor`` / \
``flx_threshold_advisor`` / ``fqm_advisor`` / ``component_health_advisor``), \
each advisor's ``actions_available`` (lift verbatim into \
``expected_actions``), modes, and the assistant playbook for \
when-to-propose vs when-NOT-to-propose.

Before proposing a new invocation, check ``ai_advisor_recent_runs`` \
for prior runs on this entity — if a recent inspect run already \
exists, quote that result first; you may still emit a fresh contract \
if a re-run is appropriate, but don't propose blindly.

## Guidelines
- Be concise and actionable in your responses
- Reference specific data from the entity context (timestamps, metric values, thresholds)
- When suggesting SPL searches for investigation, use the ones provided in the investigation.searches, investigation.anomaly_investigation_searches, and investigation.context_searches sections
- The anomaly_investigation_searches section contains SPL searches tailored to specific anomaly types (future data, latency, delay, host count changes, outliers, WLK issues). Recommend the searches that match the entity's current anomaly_reasons from the health section.
- For outlier-related issues, explain the model configuration and detection results. Use the render_search and train_search fields from outliers.models to suggest visualization or re-training commands to the user.
- If the user asks to modify settings, clearly explain what the change will do before they confirm
- Format SPL searches in code blocks for easy copy-paste
- When proposing an AI Advisor invocation, emit the ``advisor_invocation`` JSON in a single fenced ```json block at the END of your response, after your prose explanation. Default to ``mode=inspect``; only emit ``mode=act`` when the user has explicitly authorised remediation.
"""

VTENANTS_SYSTEM_PROMPT_TEMPLATE = """\
You are an AI assistant integrated into TrackMe, a Splunk application \
for data and metrics monitoring. You are operating in the Virtual Tenants \
management context, helping users understand and manage their tenant \
infrastructure.

## Your Capabilities
- Analyze the overall health of the tenant infrastructure
- Compare tenant configurations and identify inconsistencies
- Explain what each monitoring component does and when to use it
- Provide guidance on creating new tenants or adding components
- Explain RBAC configuration and permission model
- Interpret scheduler and operational status
- Suggest optimizations based on entity counts and alert distributions
- Help plan tenant management operations (enable, disable, component changes)
- Explain Virtual Groups and help users understand cross-tenant aggregation views

## Tenant Component Types
- DSM (Data Source Monitoring): Tracks index/sourcetype ingestion health
- DHM (Data Host Monitoring): Tracks host-level data delivery health
- MHM (Metrics Host Monitoring): Tracks metrics index health
- FLX (Flex Monitoring): Custom use-case based monitoring via magic searches
- FQM (Fields Quality Monitoring): Field extraction quality monitoring
- WLK (Workload Monitoring): Saved search / cron job execution monitoring

## Tenant States
- enabled: Tenant is active, all enabled component trackers are running
- disabled: Tenant is suspended, trackers are paused but data is preserved

## Configuration Flags
- sampling: Data sampling for DSM entities (reduces search load)
- adaptive_delay: Automatically adjusts delay thresholds based on data patterns
- mloutliers: Machine learning outlier detection for entity metrics
- cmdb_lookup: CMDB integration for entity enrichment

## Virtual Tenants Context
The following JSON contains the full structured description of all Virtual \
Tenants accessible to the current user, including tenant configuration, \
entity counts, alert counts, RBAC, and a knowledge reference section. \
Use this data to provide specific, data-driven answers.

```json
{vtenants_context}
```

## Guidelines
- Be concise and actionable in your responses
- Reference specific data from the context (tenant names, entity counts, alert counts, configurations)
- When the user asks about creating a tenant, refer to the knowledge_reference.tenant_creation_workflow section
- For RBAC questions, refer to the knowledge_reference.rbac_model section
- When comparing tenants, present data in a structured table or list format
- For alert-related questions, aggregate and summarize across tenants
- If the user asks about operations, reference the knowledge_reference.management_operations section
- Explain component types using the knowledge_reference.component_types section
- When suggesting configuration changes, explain what each flag does using knowledge_reference.configuration_flags
- For Virtual Group questions, refer to the knowledge_reference.virtual_groups section and the virtual_groups data in the context
- When explaining a group's entity_filter, use the DSL syntax described in knowledge_reference.virtual_groups.entity_filter_dsl
- A group's entity_filter field contains the free-form filter expression; priority_filter contains the priority levels selected (empty = all priorities)
- When the user asks about an AI Advisor (ML, Feed Lifecycle, FLX Threshold, FQM, Component Health), or describes a symptom on a specific entity that an Advisor can resolve, refer to knowledge_reference.ai_advisors (full reference) and ai_advisor_recent_runs (live state). Follow knowledge_reference.ai_advisors.assistant_playbook for when to propose, when NOT to propose, mode-selection rules, and the never-fabricate-IDs rule.
- **IMPERATIVE emission**: If your prose suggests running an advisor — phrasings like "I can run the X Advisor", "Would you like me to run...", "I'll launch the X Advisor", "Let me know if you want me to inspect..." — you MUST end your response with a fenced ```json block carrying the `advisor_invocation` contract. The chat UI renders this as a clickable consent card. Without the JSON block, the user has no button to click and the proposal is non-actionable. The shape is `{"advisor_invocation": {"advisor": "<enum>", "mode": "inspect", "suggested_reason": "...", "expected_actions": [...]}}`. Default to mode=inspect; only act when the user has explicitly authorised remediation.
"""

TENANT_HOME_SYSTEM_PROMPT_TEMPLATE = """\
You are an AI assistant integrated into TrackMe, a Splunk application \
for data and metrics monitoring. You are operating in the Tenant Home \
context for a specific tenant, helping users understand and manage \
their monitoring environment, configure features, set up alerting, \
and troubleshoot issues.

## Your Capabilities
- Provide an overview of the tenant's health across all enabled components
- Explain what each monitoring component does and its current status
- Guide users through configuration and feature enablement
- Explain alerting concepts and help configure stateful alerting
- Guide threshold tuning and impact score adjustments
- Explain data sampling, outlier detection, elastic sources, and hybrid trackers
- Help with blocklist management, logical groups, and policy configuration
- Explain the RBAC permission model
- Describe maintenance mode, bank holidays, and operational workflows
- Provide component-specific guidance (DSM, DHM, MHM, FLX, FQM, WLK)

## Tenant Component Types
- DSM (Data Source Monitoring): Tracks index/sourcetype ingestion health
- DHM (Data Host Monitoring): Tracks host-level data delivery health
- MHM (Metrics Host Monitoring): Tracks metrics index health
- FLX (Flex Monitoring): Custom use-case based monitoring via magic searches
- FQM (Fields Quality Monitoring): Field extraction quality monitoring
- WLK (Workload Monitoring): Saved search / cron job execution monitoring

## Health States
- green: Entity is healthy, within expected parameters
- red: Anomaly detected (lag threshold breached, data gap, missing data, etc.)
- orange: Warning state (approaching thresholds or partial issue)
- blue: Entity is acknowledged by a user or in maintenance mode

## Tenant Home Context
The following JSON contains the full structured description of the current \
tenant, including identity, enabled components, entity counts, alert counts, \
feature configuration, health distribution, and a comprehensive knowledge \
reference section. Use this data to provide specific, data-driven answers.

```json
{tenant_home_context}
```

## Guidelines
- Be concise and actionable in your responses
- Reference specific data from the context (entity counts, alert counts, \
health distributions, feature states)
- When the user asks about features, refer to the knowledge_reference sections
- For alerting questions, refer to knowledge_reference.alerting_concepts
- For component-specific questions, refer to knowledge_reference.component_types
- When explaining how to do something, refer to knowledge_reference.common_workflows
- For RBAC questions, refer to knowledge_reference.rbac_model
- For threshold tuning, refer to knowledge_reference.threshold_tuning
- When suggesting configuration changes, explain what each change does
- Present data in structured table or list format when comparing across components
- If the user asks about a specific component, focus on that component's data
- When the user describes a symptom an AI Advisor can resolve (RED entity, ML model false positives, threshold tuning needed, FQM coverage drift, etc.), refer to knowledge_reference.ai_advisors (full reference) and ai_advisor_recent_runs (this tenant's live state). Follow knowledge_reference.ai_advisors.assistant_playbook for when to propose, when NOT to propose, mode-selection rules, and the never-fabricate-IDs rule.
- **IMPERATIVE emission**: If your prose suggests running an advisor — phrasings like "I can run the X Advisor", "Would you like me to run...", "I'll launch the X Advisor", "Let me know if you want me to inspect..." — you MUST end your response with a fenced ```json block carrying the `advisor_invocation` contract. The chat UI renders this as a clickable consent card. Without the JSON block, the user has no button to click and the proposal is non-actionable. The shape is `{"advisor_invocation": {"advisor": "<enum>", "mode": "inspect", "suggested_reason": "...", "expected_actions": [...]}}`. Default to mode=inspect; only act when the user has explicitly authorised remediation.
"""

FQM_DICTIONARY_WIZARD_SYSTEM_PROMPT_TEMPLATE = """\
You are an AI assistant integrated into TrackMe, a Splunk application \
for data and metrics monitoring. You are operating in the FQM (Field \
Quality Monitoring) tracker creation wizard context — the user is \
configuring a NEW tracker that does not yet exist in the KV store.

## Your Single Most Important Capability — Wizard-Time Dictionary Generation

Your primary value at this surface is recognising when the user wants \
the AI Advisor to **generate a starter data dictionary** from the \
fields they have already sampled in the wizard. When that happens, \
you propose ``fqm_advisor`` in ``mode=dictionary_generate``.

The wizard frontend has already collected:
- The Splunk search the user is monitoring (sourcetype, index, …)
- The breakby fields (entity definition)
- The sampled fields with their value distributions (count, distinct_count, \
sample values, mean/min/max/stdev for numerics)
- Tracker name, kind (raw / cim / non_cim), account target, event limit

All of this is automatically attached to the advisor launch body when \
the user clicks the consent card you produce. **You do not see the \
fieldsummary in your chat context, and you do not need to** — the \
wizard injects it at launch time.

## What You DO Propose

When the user asks anything along these lines:
- "Can you generate the data dictionary for this tracker?"
- "Auto-build the dictionary based on the sampled fields"
- "Help me create a starter dictionary"
- "Propose the regex / allow_unknown / allow_empty rules"

Respond with a short prose explanation of what you'll do, then end your \
response with a fenced ``` ```json `` block carrying the action-contract:

```json
{"advisor_invocation": {"advisor": "fqm_advisor", "mode": "dictionary_generate", "suggested_reason": "<one short sentence>", "consent_required": true}}
```

The frontend hard-codes ``component`` and ``tenant_id`` on launch, and \
does NOT include ``object`` / ``object_id`` (no entity exists yet). \
Don't add those fields to your contract — they'd be ignored at best, \
or cause a 400 at worst.

## What You DO NOT Propose

- DO NOT propose ``inspect`` or ``act`` modes. They operate on stored \
entities, which don't exist during wizard creation. The advisor REST \
handler returns 400 for those modes when called from the wizard.
- DO NOT propose other advisors (ML, Feed Lifecycle, FLX Threshold, \
Component Health). The user is in the FQM wizard; the other advisors \
target different surfaces.
- DO NOT propose anything if the user has not yet generated the \
fieldsummary. Walk them through the wizard steps instead: select \
tracker type → set search & metadata → run "Generate fields summary" → \
then come back here and ask about the dictionary.

## Other Things You Can Help With

You can still answer general questions about:
- What FQM is and how it differs from DSM / DHM / MHM / FLX / WLK
- What dictionaries are, what ``allow_unknown`` / \
``allow_empty_or_missing`` / ``regex`` mean, and when each should be set
- How thresholds relate to dictionaries (success rate per field, success \
rate overall)
- How CIM trackers differ from raw trackers (when a CIM data model is \
involved vs. a free-form pseudo-datamodel name)
- Wizard navigation — which step does what, what to fill in

For these general questions, do NOT emit the action-contract. The \
contract is only for the moment the user actually wants to run the \
advisor.

## IMPERATIVE Emission Rule

If your prose suggests running the advisor — ANY phrasing like "I can \
generate the dictionary", "Would you like me to build a starter \
dictionary?", "Let me run the FQM Advisor", "I'll propose a starter \
dictionary now" — you MUST end your response with the fenced \
``` ```json `` block carrying the contract. Without it, the chat UI has \
no button for the user to click and your offer is non-actionable. The \
user has to retry the conversation, which is exactly the friction we \
designed this surface to remove.

## Wizard Context

The following JSON contains the structured description of the current \
wizard surface — the FQM advisor catalog with ``dictionary_generate`` \
mode highlighted, recent FQM advisor runs for this tenant (so you know \
if the user already launched one in this session), and the wizard \
scope. Use it for grounding.

```json
{fqm_dictionary_wizard_context}
```

## Style Guidelines
- Short, friendly, action-oriented. The user is mid-task in a wizard \
and wants progress, not lectures.
- Reference the wizard's own labels when discussing fields ("Fields \
summary", "Dictionary configuration", "Default thresholds").
- When proposing the advisor, your ``suggested_reason`` should be one \
short clear sentence — it shows up on the consent card the user sees.
"""

REST_API_REFERENCE_SYSTEM_PROMPT_TEMPLATE = """\
You are an AI assistant integrated into TrackMe, a Splunk application \
for data and metrics monitoring. You are operating in the REST API \
Reference context, helping users understand and use the TrackMe REST API.

## Your Capabilities
- Explain available REST API resource groups and their endpoints
- Show example API calls using curl or SPL | trackme command syntax
- Explain authentication methods and patterns
- Describe request/response formats and common error codes
- Guide users through API usage for specific operations
- Explain the self-documenting describe=true pattern

## REST API Reference Context
The following JSON contains the full structured description of the \
TrackMe REST API, including resource groups, authentication patterns, \
command syntax, and common usage patterns.

```json
{rest_api_reference_context}
```

## Guidelines
- Be concise and actionable in your responses
- When showing API calls, provide both curl and SPL | trackme syntax
- Always show the full URL path including the /services/trackme/v2/ prefix
- Explain HTTP methods (GET/POST/DELETE) and when each is used
- Include request body examples in JSON format
- Mention the describe=true self-documentation pattern for discovery
- When the user describes an action they want performed (creating, updating, deleting, scheduling, registering, calling an endpoint, etc.) refer to ``knowledge_reference.concierge_advisor`` (full reference, including a compact projection of the live API catalog under ``endpoints_catalog``). Follow ``knowledge_reference.concierge_advisor.assistant_playbook`` for when to propose, when NOT to propose, the surface-appropriate identifier-sourcing rules, and the never-fabricate-IDs rule.
- **IMPERATIVE emission**: If your prose suggests performing an action via the Concierge — phrasings like "I can register the license key", "Would you like me to schedule...", "I'll create the maintenance window..." — you MUST end your response with a fenced ```json block carrying the ``concierge_invocation`` contract. The chat UI renders this as a clickable consent card; without the JSON block the user has no button to click and the proposal is non-actionable. The exact shape and surface-conditional rules (what fields are session-injected vs literal vs caller-provided) are documented in ``knowledge_reference.concierge_advisor.action_contract``. Default to read-mode endpoints when probing state; only emit write/delete/destructive actions when the user has explicitly authorised mutation.
"""

BACKUP_RESTORE_SYSTEM_PROMPT_TEMPLATE = """\
You are an AI assistant integrated into TrackMe, a Splunk application \
for data and metrics monitoring. You are operating in the Backup & \
Restore context, helping users manage their TrackMe backup and \
restore operations.

## Your Capabilities
- Explain the current backup state at run granularity (3.0.0
  multi-archive format from release 2.3.22 onward) and at archive
  granularity (per-tenant + global)
- Guide users through backup creation, restoration, and selective
  recovery (single-tenant, whole-run, or legacy flat)
- Explain what each archive contains (per-tenant KV + KOs +
  vtenant_account; or non-tenant global collections)
- Provide best practices for the multi-archive era — particularly
  around per-tenant recovery, dry-run previews, and the
  missing-tenant safety guard
- Explain automated backup scheduling, retention by run, and the
  Guardian checks that surface freshness + completeness regressions

## Backup & Restore Context
The following JSON contains the full structured description of the \
TrackMe backup and restore state. `backup_summary.runs` carries the \
run-level grouping; `backup_summary.recent_backups` lists individual \
archives sorted by mtime. The `knowledge_reference` section explains \
the multi-archive run model, the three restore modes \
(single_archive / whole_run / legacy_flat), the missing-tenant \
safety guard, the SHC delegation contract, and the two Guardian \
checks (`backup_archive_too_old` and `backup_run_incomplete`).

```json
{backup_restore_context}
```

## Guidelines

- Be concise and actionable in your responses
- Reference specific backup data from the context (run_id, archive
  filenames, timestamps, status, server_name)
- When the user asks about backup operations, refer to
  `knowledge_reference` (especially `restore_modes`,
  `multi_archive_run`, and `endpoint_reference`) for the canonical
  semantics
- **When the user reports corruption affecting a single tenant,
  recommend restoring ONLY that tenant's archive** (POST /restore
  with `archive_name=trackme-backup-<RUN_ID>-tenant-<tid>.tar.zst`).
  Do not propose a whole-run restore unless data is lost across
  multiple tenants OR the global collections are corrupted — that
  would unnecessarily perturb tenants whose data is fine
- **When the user reports corruption affecting ONE specific KV
  collection or knowledge object** (e.g. "I just need
  `kv_trackme_dsm_priority_tenant_X` back"), recommend the selective
  restore path: `archives_scope` body parameter narrows per archive,
  so they can restore only that collection without touching siblings
  or the global archive. See
  `knowledge_reference.selective_restore` for the body shape and
  examples. The frontend exposes per-archive multiselects on the
  dry-run preview screen — guide them through the UI flow if they
  prefer clicking over crafting JSON
- **Before any restore, always run dry_run=true first** and surface
  the preview's `total_records_to_restore`, the per-collection list,
  and any `kvstore_collections_warnings` / `failures` to the user.
  Require their explicit confirmation before recommending
  `dry_run=false`. Restores overwrite live state; they must be
  consciously authorised
- When the user asks about an archive missing from a recent run,
  reach for the `backup_run_incomplete` Guardian alert if present —
  `metadata.missing_tenants` lists exactly which tenants are gaps,
  and `metadata.recommended_actions` is the canonical playbook to
  remediate
- For DR-freshness questions, reach for the `backup_archive_too_old`
  alert; its severity ladder (warning at cadence × 1.5, critical at
  7 days) and skip conditions (scheduler disabled / no archives yet)
  are spelled out in `knowledge_reference.guardian_integration`
- Pre-2.3.22 archives (legacy 1.0.0/2.0.0 flat format) remain
  restorable indefinitely via the legacy code path. If the user
  has an old archive and asks how to restore it, point them at
  `restore_modes.legacy_flat` — they just pass the legacy filename
  via the `backup_archive` parameter, no additional flags needed
- The Search Head Cluster delegation is invisible to the user —
  every operation works regardless of which peer they call. If they
  ask about cross-peer behaviour, reach for
  `knowledge_reference.shc_behaviour`
- When the user describes a backup/restore action they want performed (trigger a backup now, configure scheduled backups, restore from archive X, etc.), refer to ``knowledge_reference.concierge_advisor`` (full reference including a compact projection of the live API catalog under ``endpoints_catalog``). Follow ``knowledge_reference.concierge_advisor.assistant_playbook`` for when to propose, when NOT to propose, the surface-appropriate identifier-sourcing rules, and the never-fabricate-IDs rule.
- **IMPERATIVE emission**: If your prose suggests performing an action via the Concierge — phrasings like "I can trigger the backup now", "Would you like me to schedule...", "I'll restore archive X..." — you MUST end your response with a fenced ```json block carrying the ``concierge_invocation`` contract. The chat UI renders this as a clickable consent card; without the JSON block the user has no button to click and the proposal is non-actionable. The exact shape and surface-conditional rules are documented in ``knowledge_reference.concierge_advisor.action_contract``. Default to read-mode endpoints when probing state; only emit write/delete/destructive actions (restore, archive deletion) when the user has explicitly authorised mutation.
"""

MAINTENANCE_MODE_SYSTEM_PROMPT_TEMPLATE = """\
You are an AI assistant integrated into TrackMe, a Splunk application \
for data and metrics monitoring. You are operating in the Maintenance \
Mode context, helping users manage global maintenance windows.

## Your Capabilities
- Explain the current maintenance mode status
- Guide users through enabling/disabling maintenance mode
- Explain scheduling of maintenance windows
- Describe the impact of maintenance mode on alerting
- Explain the difference between global maintenance and per-entity KDB records

## Maintenance Mode Context
The following JSON contains the full structured description of the \
TrackMe maintenance mode state, including current status, scheduled \
windows, and a comprehensive knowledge reference.

```json
{maintenance_mode_context}
```

## Guidelines
- Be concise and actionable in your responses
- Reference specific maintenance data from the context
- Clearly explain the impact on alerting when maintenance is active
- Distinguish between global maintenance mode and per-entity KDB maintenance
- When discussing scheduling, explain the start/end time format
- When the user describes a maintenance-mode action they want performed (enable global maintenance now, schedule a window for tenant X 22:00–23:00, disable the active window, etc.), refer to ``knowledge_reference.concierge_advisor`` (full reference including a compact projection of the live API catalog under ``endpoints_catalog``). Follow ``knowledge_reference.concierge_advisor.assistant_playbook`` for when to propose, when NOT to propose, the surface-appropriate identifier-sourcing rules, and the never-fabricate-IDs rule.
- **IMPERATIVE emission**: If your prose suggests performing an action via the Concierge — phrasings like "I can enable maintenance mode for the next 2 hours", "Would you like me to schedule...", "I'll disable the active window..." — you MUST end your response with a fenced ```json block carrying the ``concierge_invocation`` contract. The chat UI renders this as a clickable consent card; without the JSON block the user has no button to click and the proposal is non-actionable. The exact shape and surface-conditional rules are documented in ``knowledge_reference.concierge_advisor.action_contract``. Default to read-mode endpoints when probing state; only emit write/destructive actions when the user has explicitly authorised mutation.
"""

MAINTENANCE_KDB_SYSTEM_PROMPT_TEMPLATE = """\
You are an AI assistant integrated into TrackMe, a Splunk application \
for data and metrics monitoring. You are operating in the Maintenance \
Knowledge Database context, helping users manage per-entity maintenance \
records.

## Your Capabilities
- Explain the current KDB records and their status
- Guide users through creating, updating, and deleting KDB records
- Explain how KDB records affect entity monitoring state
- Describe the relationship between KDB records and entity health states
- Help plan recurring maintenance schedules

## Maintenance KDB Context
The following JSON contains the full structured description of the \
TrackMe maintenance knowledge database, including record counts, \
recent records, and a comprehensive knowledge reference.

```json
{maintenance_kdb_context}
```

## Guidelines
- Be concise and actionable in your responses
- Reference specific KDB data from the context (record counts, entities)
- Explain that KDB records put entities into "blue" (maintenance) state
- Clarify the difference between global maintenance mode and per-entity KDB
- Guide users on time-based scheduling (start/end times)
- When the user describes a KDB action they want performed (create a record for entity X tomorrow 22:00–23:00, delete an expired record, set up recurring weekly maintenance for a host, etc.), refer to ``knowledge_reference.concierge_advisor`` (full reference including a compact projection of the live API catalog under ``endpoints_catalog``). Follow ``knowledge_reference.concierge_advisor.assistant_playbook`` for when to propose, when NOT to propose, the surface-appropriate identifier-sourcing rules, and the never-fabricate-IDs rule.
- **IMPERATIVE emission**: If your prose suggests performing an action via the Concierge — phrasings like "I can schedule the maintenance window for entity X", "Would you like me to delete the expired records...", "I'll create the recurring window..." — you MUST end your response with a fenced ```json block carrying the ``concierge_invocation`` contract. The chat UI renders this as a clickable consent card; without the JSON block the user has no button to click and the proposal is non-actionable. The exact shape and surface-conditional rules are documented in ``knowledge_reference.concierge_advisor.action_contract``. Default to read-mode endpoints when probing state; only emit write/delete/destructive actions when the user has explicitly authorised mutation.
"""

BANK_HOLIDAYS_SYSTEM_PROMPT_TEMPLATE = """\
You are an AI assistant integrated into TrackMe, a Splunk application \
for data and metrics monitoring. You are operating in the Bank Holidays \
context, helping users manage holiday calendars and their impact on \
monitoring.

## Your Capabilities
- Explain the current holiday calendar configuration
- Guide users through adding and managing holiday periods
- Explain how bank holidays affect monitoring and SLA calculations
- Describe country-based holiday organization
- Help plan holiday schedules for different regions

## Bank Holidays Context
The following JSON contains the full structured description of the \
TrackMe bank holidays configuration, including active holidays, \
country coverage, and a comprehensive knowledge reference.

```json
{bank_holidays_context}
```

## Guidelines
- Be concise and actionable in your responses
- Reference specific holiday data from the context (countries, dates, periods)
- Explain how holidays interact with SLA calculations
- Guide users on setting up recurring holiday calendars
- Mention the impact on monitoring thresholds during holiday periods
- When the user describes a bank-holiday action they want performed (add UK bank holidays for 2026, import a country's calendar, enable a recurring date, delete an obsolete entry, etc.), refer to ``knowledge_reference.concierge_advisor`` (full reference including a compact projection of the live API catalog under ``endpoints_catalog``). Follow ``knowledge_reference.concierge_advisor.assistant_playbook`` for when to propose, when NOT to propose, the surface-appropriate identifier-sourcing rules, and the never-fabricate-IDs rule.
- **IMPERATIVE emission**: If your prose suggests performing an action via the Concierge — phrasings like "I can add the UK bank holidays for 2026", "Would you like me to import...", "I'll delete the obsolete entries..." — you MUST end your response with a fenced ```json block carrying the ``concierge_invocation`` contract. The chat UI renders this as a clickable consent card; without the JSON block the user has no button to click and the proposal is non-actionable. The exact shape and surface-conditional rules are documented in ``knowledge_reference.concierge_advisor.action_contract``. Default to read-mode endpoints when probing state; only emit write/delete/destructive actions when the user has explicitly authorised mutation.
"""

LICENSE_SYSTEM_PROMPT_TEMPLATE = """\
You are an AI assistant integrated into TrackMe, a Splunk application \
for data and metrics monitoring. You are operating in the License \
Management context, helping users understand and manage their TrackMe \
license.

## Your Capabilities
- Explain the current license status and edition
- Describe features available per edition (Foundation/Enterprise/Unlimited)
- Guide users through license registration and renewal
- Explain read-only mode when license expires
- Describe developer mode and trial options

## License Management Context
The following JSON contains the full structured description of the \
TrackMe license status, including edition, validity, expiration, \
and a comprehensive knowledge reference.

```json
{license_context}
```

## Guidelines
- Be concise and actionable in your responses
- Reference specific license data from the context (edition, expiration, validity)
- When the user asks about features, explain what their current edition includes
- For renewal questions, refer to the knowledge_reference.renewal_workflow section
- Clearly explain the implications of license expiration (read-only mode)
- When the user describes a license action they want performed (register a license key, enable developer mode, start a trial, upload an offline license file, reset the license, etc.), refer to ``knowledge_reference.concierge_advisor`` (full reference including a compact projection of the live API catalog under ``endpoints_catalog``). Follow ``knowledge_reference.concierge_advisor.assistant_playbook`` for when to propose, when NOT to propose, the surface-appropriate identifier-sourcing rules, and the never-fabricate-IDs rule.
- **IMPERATIVE emission**: If your prose suggests performing an action via the Concierge — phrasings like "I can register the license key", "Would you like me to enable developer mode...", "I'll start a trial for you..." — you MUST end your response with a fenced ```json block carrying the ``concierge_invocation`` contract. The chat UI renders this as a clickable consent card; without the JSON block the user has no button to click and the proposal is non-actionable. The exact shape and surface-conditional rules are documented in ``knowledge_reference.concierge_advisor.action_contract``. Default to read-mode endpoints when probing state; only emit write/destructive actions (register, reset) when the user has explicitly authorised mutation.
"""

# Credential realm for AI provider API keys stored via UCC
AI_CREDENTIAL_REALM = "__REST_CREDENTIAL__#trackme#configs/conf-trackme_ai_provider"

# Conf file name for AI provider configuration
AI_CONF_FILE = "trackme_ai_provider"

# Concurrency limit for background LLM threads.
# Uses a simple counter + lock instead of threading.Semaphore so that the
# configured limit can change at runtime without corrupting in-flight permits.
_MAX_CONCURRENT_CHATS_DEFAULT = 10
_active_chats = 0
_active_chats_lock = threading.Lock()

# Jobs that have released their concurrency slot. Ensures we decrement at most
# once per job, whether the worker's finally or the stale-job cleanup releases.
# dict: job_id -> timestamp; pruned when size exceeds _RELEASED_SLOTS_PRUNE_AT.
_released_slots = {}
_released_slots_lock = threading.Lock()
_RELEASED_SLOTS_PRUNE_AT = 5000


class AIProviderError(Exception):
    """Raised when the AI provider returns an error or is unreachable."""

    pass


class AINotConfiguredError(Exception):
    """Raised when AI is not configured or not enabled for the tenant."""

    pass


class AIBusyError(Exception):
    """Raised when the maximum concurrent AI chat limit is reached."""

    pass


def _release_concurrency_slot(job_id):
    """
    Release a concurrency slot for a job. Idempotent — safe to call from both
    the worker's finally block and when force-marking a stale job. The first
    caller releases the slot; subsequent calls for the same job_id are no-ops.
    """
    global _active_chats  # noqa: PLW0603
    now = time.time()
    with _released_slots_lock:
        if job_id in _released_slots:
            return
        _released_slots[job_id] = now
        if len(_released_slots) > _RELEASED_SLOTS_PRUNE_AT:
            cutoff = now - _JOB_TTL_SECONDS
            to_remove = [jid for jid, ts in _released_slots.items() if ts < cutoff]
            for jid in to_remove:
                del _released_slots[jid]
    with _active_chats_lock:
        _active_chats = max(0, _active_chats - 1)


def get_ai_config(service, provider_name=None, include_disabled=False):
    """
    Retrieve AI provider configuration from the trackme_ai_provider.conf file.

    When provider_name is given, returns that specific stanza.
    When provider_name is None, returns the first configured provider found.

    Providers with `ai_enabled=0` are skipped by default so callers that
    pick a provider at runtime (AI Assistant chat, stateful-alert AI status
    report) cannot accidentally resolve a disabled provider. Pass
    `include_disabled=True` from admin flows (e.g. `POST /trackme/v2/ai/admin/test`)
    where the admin explicitly wants to inspect a disabled stanza.

    Args:
        service: Splunk service connection
        provider_name: Optional stanza name to look up
        include_disabled: When False (default), stanzas with `ai_enabled=0`
                          are skipped. When True, they are returned.

    Returns:
        dict with AI config including the provider_name key, or None if not configured
    """
    try:
        confs = service.confs[AI_CONF_FILE]

        for stanza in confs:
            # Skip the default stanza
            if stanza.name == "default":
                continue

            if provider_name and stanza.name != provider_name:
                continue

            # Missing field → treat as enabled (backward compat for pre-2320 records)
            ai_enabled = stanza.content.get("ai_enabled", "1")
            if not include_disabled and ai_enabled == "0":
                continue

            config = {
                "provider_name": stanza.name,
                "ai_enabled": ai_enabled,
                "ai_provider": stanza.content.get("ai_provider", ""),
                "ai_base_url": stanza.content.get("ai_base_url", ""),
                "ai_model": stanza.content.get("ai_model", ""),
                "ai_max_tokens": stanza.content.get("ai_max_tokens", "4096"),
                "ai_temperature": stanza.content.get("ai_temperature", "0.3"),
                "ai_request_timeout": stanza.content.get("ai_request_timeout", "600"),
                "ai_context_window": stanza.content.get("ai_context_window", "8192"),
                "ai_custom_prompt": stanza.content.get("ai_custom_prompt", ""),
                "ai_azure_api_version": stanza.content.get("ai_azure_api_version", "2024-10-21"),
                # Agent orchestration limits
                "ai_agent_token_limit": stanza.content.get("ai_agent_token_limit", "150000"),
                "ai_agent_step_limit": stanza.content.get("ai_agent_step_limit", "20"),
                "ai_agent_act_token_limit": stanza.content.get("ai_agent_act_token_limit", "200000"),
                "ai_agent_act_step_limit": stanza.content.get("ai_agent_act_step_limit", "40"),
                # Prompt caching (Anthropic only — opt-out kill switch).
                # Defaults to "1" (enabled) so existing provider records
                # benefit on the next advisor run without touching their
                # config. ``make_prompt_cache_middleware`` reads this and
                # returns None when set to "0", at which point the
                # middleware list filter drops the cache injection.
                "ai_prompt_caching_enabled": stanza.content.get(
                    "ai_prompt_caching_enabled", "1"
                ),
            }

            # Validate that essential fields are populated
            # splunk_hosted auto-discovers its base URL from SCS tenant info
            if config["ai_provider"] and config["ai_model"]:
                if config["ai_provider"] == "splunk_hosted" or config["ai_base_url"]:
                    return config

        return None

    except Exception as e:
        logger.error(
            f'function=get_ai_config, provider_name="{provider_name}", '
            f'exception="{str(e)}"'
        )
        return None


def list_ai_providers(service, include_disabled=False):
    """
    Return a list of all configured AI providers.

    Each provider must have ai_provider, ai_base_url, and ai_model populated
    to be considered valid (same validation as get_ai_config). Providers with
    `ai_enabled=0` are filtered out by default — this function feeds the AI
    Assistant provider selector and the stateful-alert AI status report,
    neither of which should surface disabled providers.

    Pass `include_disabled=True` from flows that need to see every stanza
    (e.g. the Configuration Guardian needs disabled stanzas too so it can
    clear any stale `ai_provider_unreachable` alert when an admin disables a
    previously-failing provider).

    Args:
        service: Splunk service connection
        include_disabled: When False (default), stanzas with `ai_enabled=0`
                          are skipped. When True, they are returned.

    Returns:
        list of dicts with keys: name, ai_provider, ai_model, ai_enabled.
        Empty list if no providers are configured.
    """
    providers = []
    try:
        confs = service.confs[AI_CONF_FILE]
        for stanza in confs:
            if stanza.name == "default":
                continue
            # Missing field → treat as enabled (backward compat for pre-2320 records)
            ai_enabled = stanza.content.get("ai_enabled", "1")
            if not include_disabled and ai_enabled == "0":
                continue
            ai_provider = stanza.content.get("ai_provider", "")
            ai_base_url = stanza.content.get("ai_base_url", "")
            ai_model = stanza.content.get("ai_model", "")
            # Only include fully configured providers (same check as get_ai_config)
            # splunk_hosted auto-discovers its base URL from SCS tenant info
            if ai_provider and ai_model and (ai_provider == "splunk_hosted" or ai_base_url):
                providers.append(
                    {
                        "name": stanza.name,
                        "ai_provider": ai_provider,
                        "ai_model": ai_model,
                        "ai_enabled": ai_enabled,
                    }
                )
    except Exception as e:
        logger.error(f'function=list_ai_providers, exception="{str(e)}"')
    return providers


def get_ai_api_key(service, provider_name):
    """
    Retrieve the AI provider API key from Splunk's encrypted credential store.

    Uses the UCC credential storage pattern where credentials are stored
    with realm __REST_CREDENTIAL__#trackme#configs/conf-trackme_ai_provider.

    Args:
        service: Splunk service connection
        provider_name: The stanza name of the AI provider configuration

    Returns:
        str: The API key, or None if not found
    """
    credential_name = f"{AI_CREDENTIAL_REALM}:{provider_name}``"

    try:
        api_key_raw = ""
        for credential in service.storage_passwords:
            if (
                credential.content.get("realm") == AI_CREDENTIAL_REALM
                and credential.name.startswith(credential_name)
            ):
                api_key_raw += str(credential.content.clear_password)

        if api_key_raw:
            # UCC stores as JSON: {"ai_api_key": "..."}
            try:
                parsed = json.loads(api_key_raw)
                if isinstance(parsed, dict) and "ai_api_key" in parsed:
                    return parsed["ai_api_key"]
            except (json.JSONDecodeError, ValueError):
                pass
            # Fallback: try regex extraction
            match = re.search(r'"ai_api_key":\s*"(.*?)"', api_key_raw)
            if match:
                return match.group(1)

        return None

    except Exception as e:
        logger.error(
            f'function=get_ai_api_key, provider_name="{provider_name}", '
            f'exception="{str(e)}"'
        )
        return None


# ============================================================================
# Splunk Hosted LLM (SLIM API) helpers
# ============================================================================


def _get_scs_tenant_info(service):
    """
    Retrieve SCS tenant info from the Splunk instance.

    Calls /services/server/scs/tenantinfo to get the tenant ID and hostname
    needed to construct SLIM API URLs.

    Args:
        service: Splunk service connection (system-level)

    Returns:
        tuple: (tenant, tenant_hostname)

    Raises:
        AIProviderError: If tenant info cannot be retrieved
    """
    try:
        response = service.get(
            "/services/server/scs/tenantinfo", output_mode="json"
        )
        body = response["body"].read()
        json_res = json.loads(body)
        entry = json_res.get("entry", [])
        if not entry:
            raise AIProviderError(
                "SCS tenant info returned no entries. "
                "Ensure this is a Splunk Cloud instance with the SLIM API enabled."
            )
        content = entry[0].get("content", {})
        tenant = content.get("tenant")
        tenant_hostname = content.get("tenantHostname")
        if not tenant or not tenant_hostname:
            raise AIProviderError(
                "SCS tenant info is incomplete (missing tenant or tenantHostname). "
                "Ensure this Splunk Cloud instance has the SLIM API enabled."
            )
        return tenant, tenant_hostname
    except AIProviderError:
        raise
    except Exception as e:
        raise AIProviderError(
            f"Failed to retrieve SCS tenant info: {str(e)}. "
            "The splunk_hosted provider requires a Splunk Cloud instance "
            "with the SLIM API enabled."
        )


def _get_scs_token(service):
    """
    Retrieve a short-lived SCS token for SLIM API authentication.

    Calls /services/authorization/scs_tokens to get a Bearer token
    scoped to the SLIM API.

    Args:
        service: Splunk service connection (system-level)

    Returns:
        str: The SCS token

    Raises:
        AIProviderError: If token cannot be retrieved
    """
    try:
        response = service.get(
            "/services/authorization/scs_tokens",
            output_mode="json",
            principalId="slim",
            scope="tenant",
        )
        body = response["body"].read()
        json_res = json.loads(body)
        entry = json_res.get("entry", [])
        if not entry:
            raise AIProviderError(
                "SCS token endpoint returned no entries. "
                "Ensure this is a Splunk Cloud instance with the SLIM API enabled."
            )
        token = entry[0].get("content", {}).get("scs_token")
        if not token:
            raise AIProviderError("SCS token is empty")
        return token
    except AIProviderError:
        raise
    except Exception as e:
        raise AIProviderError(
            f"Failed to retrieve SCS token: {str(e)}. "
            "Ensure this Splunk Cloud instance has the SLIM API enabled "
            "and the user has appropriate permissions."
        )


def _generate_slim_request_id():
    """
    Generate a unique request ID for SLIM API calls.

    The Splunk SLIM API rejects requests missing the ``request_id`` header
    with ``HTTP 400: {"error_message":"Request ID not present in header"}``.
    This helper mirrors the Splunk AI/ML Toolkit behaviour exactly — the
    toolkit uses ``secrets.token_hex(32)`` (64 hex characters) in
    ``Splunk_ML_Toolkit/bin/util/ai_commander_util.py`` — to minimise the
    risk of any server-side length/format validation that we cannot observe
    from the outside.

    Returns:
        str: A 64-character hexadecimal request identifier
    """
    return secrets.token_hex(32)


def _get_slim_base_url(service):
    """
    Construct the SLIM API base URL from SCS tenant info.

    Args:
        service: Splunk service connection (system-level)

    Returns:
        str: The SLIM API base URL, e.g. https://hostname/tenant/slim-api/v1alpha1
    """
    tenant, tenant_hostname = _get_scs_tenant_info(service)
    return f"https://{tenant_hostname}/{tenant}/slim-api/v1alpha1"


def _fetch_slim_models(base_url, scs_token):
    """
    Fetch available chat models from the SLIM API.

    Shared helper used by both :func:`get_splunk_hosted_models` (public,
    for the REST discovery endpoint) and :func:`_resolve_splunk_hosted_model`
    (internal, for model-name resolution).

    Args:
        base_url: The SLIM API base URL, e.g.
            ``https://hostname/tenant/slim-api/v1alpha1``
        scs_token: The SCS bearer token

    Returns:
        list: List of dicts with ``model_name`` and ``model_id``

    Raises:
        AIProviderError: If the request fails or returns a non-2xx status
    """
    url = f"{base_url}/chat/models"
    # NOTE: urllib normalises header names to title case in do_open(), which
    # breaks SLIM's case-sensitive "request_id" header.  Use requests (same
    # library the Splunk AI/ML Toolkit uses) to preserve the exact header
    # name on the wire.
    headers = {
        "Authorization": f"Bearer {scs_token}",
        "Content-Type": "application/json",
        "User-Agent": _USER_AGENT,
        "request_id": _generate_slim_request_id(),
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code >= 400:
            raise AIProviderError(
                f"Failed to retrieve SLIM API models (HTTP {resp.status_code}): {resp.text}"
            )
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "models" in data:
            return data["models"]
        return data
    except AIProviderError:
        raise
    except requests.RequestException as e:
        raise AIProviderError(
            f"Failed to retrieve SLIM API models: {str(e)}"
        )
    except Exception as e:
        raise AIProviderError(
            f"Failed to retrieve SLIM API models: {str(e)}"
        )


def get_splunk_hosted_models(service):
    """
    Discover available chat models from the Splunk SLIM API.

    Public entry point used by the ``GET /trackme/v2/ai/admin/models``
    REST endpoint.  Resolves credentials from the Splunk service
    connection, then delegates to :func:`_fetch_slim_models`.

    Args:
        service: Splunk service connection (system-level)

    Returns:
        list: List of dicts with model_name and model_id

    Raises:
        AIProviderError: If models cannot be retrieved
    """
    base_url = _get_slim_base_url(service)
    scs_token = _get_scs_token(service)
    return _fetch_slim_models(base_url, scs_token)


def _model_resolution_cache_name(base_url, model):
    """
    Deterministic cache key for a (base_url, model) pair.

    Uses SHA-256 over a sentinel-separated string so the key is stable,
    safe for KV Store (hex-only), and distinct per SLIM tenant + configured
    model value.
    """
    digest = hashlib.sha256(f"{base_url}|{model}".encode("utf-8")).hexdigest()
    return f"ai_model_resolution:{digest}"


def _resolve_splunk_hosted_model(model, base_url, scs_token, system_service=None):
    """
    Resolve a Splunk Hosted LLM model value to the actual model_id.

    The SLIM API ``/chat/completions`` endpoint requires a ``model_id``
    (the internal identifier), not the human-friendly ``model_name``
    (e.g. ``gpt-oss-20b``).  Customers may configure either value in the
    ``ai_model`` field.

    This function reuses the already-fetched ``base_url`` and ``scs_token``
    from the caller to avoid duplicate HTTP round-trips.

    Privilege model / caching
    -------------------------
    The resolution cache is backed by the ``kv_trackme_global_cache``
    collection, which (per ``package/metadata/default.meta``) grants
    **write** access only to ``admin`` and ``trackme_admin``.  Normal
    ``trackme_user`` callers of the AI Assistant therefore cannot write
    to the cache directly — this is why the caching parameter is named
    ``system_service`` and MUST be a system-level connection (built from
    ``request_info.system_authtoken`` in REST handlers, for example).

    Call paths that do not have a system-level service available (e.g.,
    alert actions running under the dispatching user's session key) can
    simply pass ``system_service=None`` — caching will be disabled for
    that call and behaviour will be identical to the pre-cache code.
    There is no attempt to privilege-escalate implicitly; that is a
    deliberate design choice to keep the trust boundary clear.

    Resolution logic (fail-safe — never breaks an already-working config):

    1. If ``system_service`` is provided, look up ``(base_url, model)`` in
       the global KV Store cache.  On hit with a valid non-empty string
       payload, return the cached value immediately — no HTTP round-trip.
    2. On ANY cache failure (key-derivation error, KV Store error, missing
       key, expired TTL, malformed payload, non-string resolved value,
       empty resolved value, permission denied because the caller passed
       a non-system service by mistake) — fall through to live resolution.
       The cache is purely additive; a broken cache never blocks a
       working SLIM resolution.
    3. Query ``/chat/models`` to get the list of available models with
       both ``model_name`` (display name) and ``model_id`` (internal id).
    4. If ``model`` already matches a known ``model_id``, return it
       immediately — no resolution needed (existing configs keep working).
    5. If ``model`` matches a ``model_name`` (and is NOT a ``model_id``),
       return the corresponding ``model_id``.
    6. If ``model`` matches neither, return it unchanged and let the
       SLIM API reject it with a clear error.
    7. If the lookup fails entirely (network error, SLIM API unavailable,
       any unexpected exception anywhere in the function), return
       ``model`` unchanged — this preserves the pre-cache behaviour so
       there is **zero regression risk**.

    Successful resolutions (any non-error path) are written back to the
    cache with a TTL of :data:`_MODEL_RESOLUTION_CACHE_TTL` seconds.
    Cache read/write failures are logged at DEBUG level and never break
    resolution — the outer try/except guarantees that any unhandled
    exception anywhere in this function, including in cache plumbing,
    falls back to returning ``model`` unchanged.

    Args:
        model: The configured ai_model value (could be model_name or model_id)
        base_url: The SLIM API base URL (already resolved from SCS tenant info)
        scs_token: The SCS bearer token (already fetched)
        system_service: Optional SYSTEM-LEVEL Splunk service connection
            (i.e., built from ``request_info.system_authtoken`` or
            equivalent).  When provided, enables KV Store caching to
            eliminate per-LLM-call SLIM round-trips.  When ``None``, the
            function behaves exactly as before (no caching).  A
            user-level service passed here would trigger a permission
            error on cache writes, which is caught and ignored — but
            this is wasteful, so do not do it.

    Returns:
        str: The resolved model_id to use in the chat/completions payload
    """
    try:
        # --- Cache lookup (best-effort, must NEVER skip live resolution
        #     except on a clean hit with a validated non-empty string) ---
        cache_name = None
        if system_service is not None:
            try:
                cache_name = _model_resolution_cache_name(base_url, model)
                cached = global_cache_get(
                    system_service, cache_name, ttl=_MODEL_RESOLUTION_CACHE_TTL
                )
                if (
                    cached
                    and isinstance(cached, dict)
                    and isinstance(cached.get("resolved"), str)
                    and cached["resolved"]
                ):
                    return cached["resolved"]
            except Exception as e:
                # Any cache-read error — key derivation, KV Store,
                # permission, JSON parse, anything — falls through to
                # live resolution.
                cache_name = None  # disable cache write for this call
                logger.debug(
                    f'function=_resolve_splunk_hosted_model, '
                    f'action="cache read failed, falling back to live resolution", '
                    f'exception="{str(e)}"'
                )

        # --- Live resolution via SLIM /chat/models ---
        models = _fetch_slim_models(base_url, scs_token)
        if not models or not isinstance(models, list):
            return model

        # Build name→id and id sets from the API response
        name_to_id = {}
        known_ids = set()
        for entry in models:
            if isinstance(entry, dict):
                m_name = entry.get("model_name", "")
                m_id = entry.get("model_id", "")
                if m_name and m_id:
                    name_to_id[m_name] = m_id
                    known_ids.add(m_id)

        # Priority 1: if the value is already a valid model_id, use it as-is.
        # This guarantees existing working configs are never altered.
        if model in known_ids:
            resolved = model
        # Priority 2: if the value matches a model_name, resolve to model_id.
        elif model in name_to_id:
            resolved = name_to_id[model]
            logger.info(
                f'function=_resolve_splunk_hosted_model, '
                f'action="resolved model_name to model_id", '
                f'model_name="{model}", model_id="{resolved}"'
            )
        else:
            # Not found as either model_id or model_name — return unchanged
            # and let the SLIM API return its own error for clarity.
            resolved = model

        # --- Cache write (best-effort; must never break resolution) ---
        if (
            system_service is not None
            and cache_name is not None
            and isinstance(resolved, str)
            and resolved
        ):
            try:
                global_cache_set(
                    system_service,
                    cache_name,
                    {"resolved": resolved, "input": model},
                )
            except Exception as e:
                logger.debug(
                    f'function=_resolve_splunk_hosted_model, '
                    f'action="cache write failed", '
                    f'exception="{str(e)}"'
                )

        return resolved

    except Exception as e:
        # Outer fail-safe: catches any unexpected exception — in cache
        # plumbing, in _fetch_slim_models, or anywhere above — and returns
        # the configured value unchanged.  This preserves the pre-cache
        # behaviour exactly, so there is zero regression risk if any
        # layer of the cache integration misbehaves.
        # Do NOT write to the cache on this path — we want to retry live
        # resolution on the next call.
        logger.warning(
            f'function=_resolve_splunk_hosted_model, '
            f'action="model lookup failed, using configured value as-is", '
            f'model="{model}", exception="{str(e)}"'
        )
        return model


def call_llm(config, api_key, messages, timeout=90, service=None):
    """
    Call an LLM API. Routes to the appropriate provider-specific implementation
    based on the ai_provider config value.

    Args:
        config: AI provider config dict (must contain ai_provider, ai_base_url, ai_model)
        api_key: The API key for authentication
        messages: List of message dicts [{"role": "...", "content": "..."}]
        timeout: Request timeout in seconds
        service: Splunk service connection (required for splunk_hosted provider)

    Returns:
        dict: {"content": "...", "usage": {...}}

    Raises:
        AIProviderError: If the API call fails
    """
    provider = config.get("ai_provider", "openai")

    if provider == "anthropic":
        return _call_anthropic(config, api_key, messages, timeout)
    elif provider == "splunk_hosted":
        if service is None:
            raise AIProviderError(
                "splunk_hosted provider requires a Splunk service connection"
            )
        return _call_splunk_hosted(config, messages, timeout, service)
    else:
        return _call_openai_compatible(config, api_key, messages, timeout)


def _call_openai_compatible(config, api_key, messages, timeout=90):
    """
    Call an OpenAI-compatible LLM API (OpenAI, Azure, Ollama, custom).

    Args:
        config: AI provider config dict (must contain ai_base_url, ai_model)
        api_key: The API key for authentication
        messages: List of message dicts [{"role": "...", "content": "..."}]
        timeout: Request timeout in seconds

    Returns:
        dict: {"content": "...", "usage": {...}}

    Raises:
        AIProviderError: If the API call fails
    """
    provider = config.get("ai_provider", "openai")
    base_url = config.get("ai_base_url", "").rstrip("/")
    model = config.get("ai_model", "")
    max_tokens = max(1, int(config.get("ai_max_tokens", "4096")))
    temperature = float(config.get("ai_temperature", "0.3"))

    if not base_url or not model:
        raise AIProviderError("AI provider base_url and model must be configured")

    # Providers that require an API key (everything except ollama)
    if not api_key and provider != "ollama":
        raise AIProviderError(
            f"API key is required for provider '{provider}'. "
            "Please configure the API key in the AI Provider settings."
        )

    # Build the request — Azure requires api-version query param
    if provider == "azure":
        api_version = config.get("ai_azure_api_version", "2024-10-21")
        url = f"{base_url}/chat/completions?api-version={api_version}"
    else:
        url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": _USER_AGENT,
    }

    # Add authorization — Azure uses api-key header, others use Bearer
    if api_key:
        if provider == "azure":
            headers["api-key"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    # Allow self-signed certs for local Ollama instances
    ctx = _build_ssl_context(base_url)

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))

    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        raise AIProviderError(
            f"LLM API returned HTTP {e.code}: {error_body}"
        )
    except urllib.error.URLError as e:
        raise AIProviderError(
            f"Failed to connect to LLM provider at {base_url}: {str(e.reason)}"
        )
    except TimeoutError:
        raise AIProviderError(
            f"LLM request timed out after {timeout}s"
        )

    # Extract response
    try:
        choices = response_data.get("choices", [])
        if not choices:
            raise AIProviderError("LLM returned empty choices")

        content = choices[0].get("message", {}).get("content", "")
        usage = response_data.get("usage", {})

        return {
            "content": content,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        }

    except (KeyError, IndexError) as e:
        raise AIProviderError(
            f"Unexpected LLM response format: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Anthropic ``temperature`` deprecation handling (Opus 4 generation onwards).
#
# Anthropic deprecated the ``temperature`` request parameter for the Opus 4
# generation. Sending ``temperature`` to ``claude-opus-4-7`` (and likely any
# subsequent Opus N>=4 release) produces:
#
#     HTTP 400 {"type":"error","error":{
#       "type":"invalid_request_error",
#       "message":"`temperature` is deprecated for this model."
#     }}
#
# Sonnet, Haiku and pre-4 Opus still accept ``temperature``, so we cannot
# simply stop sending it everywhere. Two-layer defence:
#
#   1. ``_anthropic_supports_temperature(model)`` — proactive skip for known
#      Opus 4+ models. Conservative regex so anything that doesn't match
#      ``claude-opus-N`` keeps sending temperature unchanged.
#   2. ``_is_temperature_deprecation_error(body)`` — backstop: if Anthropic
#      returns the deprecation error at runtime, the call site retries the
#      same request once with ``temperature`` stripped. This self-heals for
#      any future model that adopts the same deprecation pattern without
#      requiring a regex update.
# ---------------------------------------------------------------------------

_ANTHROPIC_OPUS_VERSIONED = re.compile(r"^claude-opus-(\d+)", re.IGNORECASE)


def _anthropic_supports_temperature(model):
    """
    Return True if Anthropic's API accepts ``temperature`` for *model*.

    Currently returns False only for ``claude-opus-N*`` with N >= 4
    (Opus 4 generation deprecated the parameter). Everything else —
    including Sonnet, Haiku, and pre-4 Opus — still accepts it.
    """
    if not model:
        return True
    match = _ANTHROPIC_OPUS_VERSIONED.match(str(model).strip())
    if not match:
        return True
    try:
        major = int(match.group(1))
    except (TypeError, ValueError):
        return True
    return major < 4


def _is_temperature_deprecation_error(error_body):
    """
    Detect Anthropic's ``temperature is deprecated`` HTTP 400 in a response
    body so the call site can retry without ``temperature``.
    """
    if not error_body:
        return False
    body_lower = str(error_body).lower()
    return "temperature" in body_lower and "deprecated" in body_lower


def _is_prompt_caching_error(error_body):
    """
    Detect HTTP 400 ``invalid_request_error`` bodies that point at the
    ``cache_control`` marker so the call site can retry once with the
    raw string ``system`` field (caching off for this request).

    Anthropic's docs are explicit that *too-small* prompts do NOT
    produce a 400 — caching is silently skipped. But cache_control
    rejections CAN still happen for unrelated validation reasons:
      - Exceeding the per-request limit of cache_control blocks
        (e.g. ``A maximum of 4 blocks with cache_control may be provided``).
      - Incorrect placement of cache_control in nested locations the
        API doesn't allow.
      - Invalid TTL ordering.

    Surfacing the chat request as a hard failure when any such future
    validation error fires would break the AI Assistant entirely. The
    retry below mirrors the existing ``_is_temperature_deprecation_error``
    pattern: detect, log, retry once without the marker, succeed.
    """
    if not error_body:
        return False
    body_lower = str(error_body).lower()
    return "cache_control" in body_lower or "prompt caching" in body_lower


# ---------------------------------------------------------------------------
# Anthropic prompt caching (AI Assistant chat path)
#
# The AI Advisors path (splunklib.ai.Agent) wires prompt caching via the
# ``make_prompt_cache_middleware`` ``before_model`` hook (mutating
# ``ModelRequest.system_message`` into a content-block list with
# ``cache_control``). The AI Assistant chat path doesn't go through the
# Agent SDK — it makes raw ``urllib.request`` POSTs to ``/v1/messages``
# via ``_call_anthropic`` / ``_call_anthropic_streaming``. Same caching
# benefits available, different injection point: convert the
# ``payload["system"]`` value from a plain string to a single-element
# content-block list with the ephemeral marker.
#
# Anthropic minimum cache size: 1024 tokens (~4096 chars). Below that
# the API rejects the cache_control marker. We honour that locally to
# avoid an avoidable 400 round-trip.
#
# Provider-level opt-out: ``ai_provider.ai_prompt_caching_enabled = 0``
# returns the plain string unchanged (no marker, no cache cost). Same
# kill switch the advisor middleware honours, so the toggle in
# ``Manage AI Providers > <Anthropic> > Prompt caching`` silences BOTH
# layers consistently.
# ---------------------------------------------------------------------------

_ANTHROPIC_PROMPT_CACHE_MIN_CHARS = 4096


def _build_anthropic_system_field(
    config: dict | None,
    system_prompt: str | None,
) -> str | list[dict] | None:
    """Return the value to use for the Anthropic ``payload["system"]``
    field, with ``cache_control: {"type": "ephemeral"}`` attached when
    prompt caching is enabled AND the prompt is long enough to be
    cached by Anthropic (~1024 tokens minimum).

    Args:
        config: AI provider config dict (must carry
            ``ai_prompt_caching_enabled``, defaults to enabled when
            absent for backward-compat). ``None`` is accepted
            defensively — defaults to enabled.
        system_prompt: The system prompt string. ``None``/empty → return
            ``None`` (caller skips the ``system`` field entirely).

    Returns:
        - ``None`` when there is no system prompt.
        - The raw string when caching is disabled or the prompt is
          below the Anthropic minimum (still safe to send as-is).
        - A single-element ``[{"type": "text", "text": ...,
          "cache_control": {"type": "ephemeral"}}]`` list when caching
          is enabled and the prompt meets the size threshold.
    """
    if not system_prompt:
        return None

    raw_flag = config.get("ai_prompt_caching_enabled", "1") if config else "1"
    enabled = True
    if raw_flag not in (None, ""):
        try:
            enabled = int(raw_flag) != 0
        except (TypeError, ValueError):
            # Garbage in the field → treat as enabled rather than
            # opt-out, so a typo can't silently disable the feature.
            enabled = True

    if not enabled or len(system_prompt) < _ANTHROPIC_PROMPT_CACHE_MIN_CHARS:
        return system_prompt

    return [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def _call_anthropic(config, api_key, messages, timeout=90):
    """
    Call the Anthropic Messages API (Claude models).

    The Anthropic API differs from OpenAI in several ways:
    - Endpoint: /messages (not /chat/completions)
    - Auth: x-api-key header (not Authorization: Bearer)
    - System prompt: separate top-level "system" field (not in messages)
    - Response: content[0].text (array of content blocks, not choices)
    - Token usage: input_tokens/output_tokens (not prompt_tokens/completion_tokens)
    - Required header: anthropic-version

    Args:
        config: AI provider config dict (must contain ai_base_url, ai_model)
        api_key: The API key for authentication
        messages: List of message dicts [{"role": "...", "content": "..."}]
        timeout: Request timeout in seconds

    Returns:
        dict: {"content": "...", "usage": {...}}

    Raises:
        AIProviderError: If the API call fails
    """
    base_url = config.get("ai_base_url", "").rstrip("/")
    model = config.get("ai_model", "")
    max_tokens = max(1, int(config.get("ai_max_tokens", "4096")))
    temperature = float(config.get("ai_temperature", "0.3"))

    if not base_url or not model:
        raise AIProviderError("AI provider base_url and model must be configured")

    if not api_key:
        raise AIProviderError("Anthropic API key is required")

    # Extract system prompt from messages (Anthropic uses a separate field)
    system_prompt = None
    non_system_messages = []
    for msg in messages:
        if msg.get("role") == "system":
            # Concatenate multiple system messages if present
            if system_prompt is None:
                system_prompt = msg["content"]
            else:
                system_prompt += "\n\n" + msg["content"]
        else:
            non_system_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

    # Build the request — Anthropic uses /messages endpoint
    url = f"{base_url}/messages"
    payload = {
        "model": model,
        "messages": non_system_messages,
        "max_tokens": max_tokens,
    }
    # Skip ``temperature`` for models that have deprecated it (Opus 4+).
    # See module-level comment block on Anthropic temperature handling.
    if _anthropic_supports_temperature(model):
        payload["temperature"] = temperature

    # Add system prompt as top-level field if present. Wrapped in
    # cache_control content-block form when prompt caching is enabled
    # AND the prompt meets Anthropic's ~1024-token minimum — see
    # ``_build_anthropic_system_field``.
    system_field = _build_anthropic_system_field(config, system_prompt)
    if system_field is not None:
        payload["system"] = system_field

    headers = {
        "Content-Type": "application/json",
        "User-Agent": _USER_AGENT,
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    ctx = ssl.create_default_context()

    def _post(payload_dict):
        body = json.dumps(payload_dict).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        response_data = _post(payload)

    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        # Backstop: Anthropic deprecated ``temperature`` on the Opus 4
        # generation and may extend that to other models in the future.
        # If the regex check above didn't catch this model, retry once
        # with ``temperature`` stripped so the caller still gets a
        # working response instead of an opaque HTTP 400.
        if (
            e.code == 400
            and "temperature" in payload
            and _is_temperature_deprecation_error(error_body)
        ):
            logger.warning(
                f"Anthropic rejected model={model!r} with temperature; "
                f"retrying once without temperature. "
                f"Consider extending _anthropic_supports_temperature() "
                f"to cover this model."
            )
            retry_payload = {k: v for k, v in payload.items() if k != "temperature"}
            # The retry is structurally INSIDE the outer ``except`` block,
            # so the outer ``except urllib.error.URLError`` /
            # ``except TimeoutError`` clauses below do NOT catch failures
            # raised by ``_post(retry_payload)`` — they only catch errors
            # from the original ``_post(payload)`` call inside the outer
            # ``try``. Without an explicit catch here, a URLError or
            # TimeoutError on the retry would escape as a raw exception,
            # bypassing the ``AIProviderError`` contract that
            # ``call_llm`` callers rely on. (Bugbot caught this on
            # PR #1508 cycle 1.) Catch all three exception types
            # locally so every failure path returns a wrapped error.
            try:
                response_data = _post(retry_payload)
            except urllib.error.HTTPError as retry_e:
                retry_body = ""
                try:
                    retry_body = retry_e.read().decode("utf-8")
                except Exception:
                    pass
                raise AIProviderError(
                    f"Anthropic API returned HTTP {retry_e.code} "
                    f"(retry without temperature): {retry_body}"
                )
            except urllib.error.URLError as retry_e:
                raise AIProviderError(
                    f"Failed to connect to Anthropic API at {base_url} "
                    f"(retry without temperature): {str(retry_e.reason)}"
                )
            except TimeoutError:
                raise AIProviderError(
                    f"Anthropic API request timed out after {timeout}s "
                    f"(retry without temperature)"
                )
        # Backstop: Anthropic returns HTTP 400 with an
        # ``invalid_request_error`` mentioning ``cache_control`` when
        # the prompt-caching marker is rejected for validation reasons
        # beyond the silently-handled "too small" case (e.g. > 4
        # cache_control blocks, unsupported nesting, TTL ordering).
        # Without a retry, those would break the AI Assistant entirely
        # the first time Anthropic tightens the validation. Mirror the
        # temperature pattern: detect, log, retry once with the raw
        # string ``system`` field.
        elif (
            e.code == 400
            and isinstance(payload.get("system"), list)
            and _is_prompt_caching_error(error_body)
        ):
            logger.warning(
                f"Anthropic rejected model={model!r} with cache_control "
                f"system field; retrying once without prompt caching for "
                f"this request. error_body={error_body!r}"
            )
            retry_payload = dict(payload)
            retry_payload["system"] = system_prompt  # plain string
            try:
                response_data = _post(retry_payload)
            except urllib.error.HTTPError as retry_e:
                retry_body = ""
                try:
                    retry_body = retry_e.read().decode("utf-8")
                except Exception:
                    pass
                raise AIProviderError(
                    f"Anthropic API returned HTTP {retry_e.code} "
                    f"(retry without cache_control): {retry_body}"
                )
            except urllib.error.URLError as retry_e:
                raise AIProviderError(
                    f"Failed to connect to Anthropic API at {base_url} "
                    f"(retry without cache_control): {str(retry_e.reason)}"
                )
            except TimeoutError:
                raise AIProviderError(
                    f"Anthropic API request timed out after {timeout}s "
                    f"(retry without cache_control)"
                )
        else:
            raise AIProviderError(
                f"Anthropic API returned HTTP {e.code}: {error_body}"
            )
    except urllib.error.URLError as e:
        raise AIProviderError(
            f"Failed to connect to Anthropic API at {base_url}: {str(e.reason)}"
        )
    except TimeoutError:
        raise AIProviderError(
            f"Anthropic API request timed out after {timeout}s"
        )

    # Extract response — Anthropic returns content as array of blocks
    try:
        content_blocks = response_data.get("content", [])
        if not content_blocks:
            raise AIProviderError("Anthropic returned empty content")

        # Extract text from content blocks (may contain multiple text blocks)
        text_parts = []
        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        content = "\n".join(text_parts) if text_parts else ""

        if not content:
            raise AIProviderError("Anthropic returned no text content blocks")

        # Map Anthropic usage fields to our standard format. Cache
        # telemetry (cache_creation_input_tokens / cache_read_input_tokens)
        # is the operator's evidence that prompt caching is actually
        # firing — surface it both in the return value and as an INFO
        # log so it shows up in splunkd.log without needing the
        # Anthropic console.
        usage = response_data.get("usage", {})
        cache_write = usage.get("cache_creation_input_tokens", 0) or 0
        cache_read = usage.get("cache_read_input_tokens", 0) or 0
        if cache_write or cache_read:
            logger.info(
                f'function=_call_anthropic, action="prompt_cache_usage", '
                f'cache_creation_input_tokens={cache_write}, '
                f'cache_read_input_tokens={cache_read}, '
                f'input_tokens={usage.get("input_tokens", 0)}, '
                f'output_tokens={usage.get("output_tokens", 0)}'
            )

        return {
            "content": content,
            "usage": {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                # Anthropic-specific cache telemetry (0 for non-cached calls)
                "cache_creation_input_tokens": cache_write,
                "cache_read_input_tokens": cache_read,
            },
        }

    except (KeyError, IndexError) as e:
        raise AIProviderError(
            f"Unexpected Anthropic response format: {str(e)}"
        )


def _call_splunk_hosted(config, messages, timeout, service):
    """
    Call the Splunk SLIM API (non-streaming) for chat completions.

    Retrieves SCS token and tenant info dynamically, constructs the SLIM API
    URL, and makes an OpenAI-compatible request with model_id instead of model.

    The configured ``ai_model`` value may be either a ``model_name`` (display
    name like ``gpt-oss-20b``) or the actual ``model_id``.  The function
    auto-resolves via ``_resolve_splunk_hosted_model()`` so both work.

    Args:
        config: AI provider config dict (must contain ai_model)
        messages: List of message dicts [{"role": "...", "content": "..."}]
        timeout: Request timeout in seconds
        service: Splunk service connection for SCS token retrieval

    Returns:
        dict: {"content": "...", "usage": {...}}

    Raises:
        AIProviderError: If the API call fails
    """
    model = config.get("ai_model", "")
    max_tokens = max(1, int(config.get("ai_max_tokens", "4096")))
    temperature = float(config.get("ai_temperature", "0.3"))

    if not model:
        raise AIProviderError("AI model must be configured for splunk_hosted provider")

    # Get dynamic credentials and URL
    base_url = _get_slim_base_url(service)
    scs_token = _get_scs_token(service)

    # Resolve model_name → model_id if needed (reuses base_url/scs_token,
    # fail-safe).  The ``service`` handed to us here must already be
    # system-level (admin) because SCS token retrieval reads from
    # ``storage_passwords``, which requires ``list_storage_passwords``.  We
    # therefore forward it as ``system_service`` to engage the KV Store
    # resolution cache — eliminating the per-LLM-call /chat/models
    # round-trip flagged by Cursor Bugbot.  If the caller ever passes a
    # non-privileged service, the cache layer fails silently and
    # resolution still succeeds via the live SLIM call.
    model = _resolve_splunk_hosted_model(
        model, base_url, scs_token, system_service=service
    )

    url = f"{base_url}/chat/completions"
    payload = {
        "model_id": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
        # NOTE: the Splunk AI/ML Toolkit always includes an "extra_headers"
        # field in the SLIM request body (see Splunk_ML_Toolkit
        # bin/ai_commander/llm_base.py and bin/rest_handlers/aicommander_metadata.py).
        # The {"additionalProp1": "string"} value is the Swagger/OpenAPI
        # default example, which indicates the SLIM API schema defines this
        # field. Mirroring the toolkit ensures we don't get rejected by
        # schema validation.
        "extra_headers": {"additionalProp1": "string"},
    }

    # NOTE: urllib normalises header names to title case in do_open(), which
    # breaks SLIM's case-sensitive "request_id" header. Use requests (same
    # library the Splunk AI/ML Toolkit uses) to preserve the exact header
    # name on the wire.
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {scs_token}",
        "User-Agent": _USER_AGENT,
        "request_id": _generate_slim_request_id(),
    }

    try:
        resp = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=timeout,
        )
        if resp.status_code >= 400:
            raise AIProviderError(
                f"SLIM API returned HTTP {resp.status_code}: {resp.text}"
            )
        response_data = resp.json()
    except AIProviderError:
        raise
    except requests.Timeout:
        raise AIProviderError(f"SLIM API request timed out after {timeout}s")
    except requests.ConnectionError as e:
        raise AIProviderError(
            f"Failed to connect to SLIM API at {base_url}: {str(e)}"
        )
    except requests.RequestException as e:
        raise AIProviderError(
            f"Failed to connect to SLIM API at {base_url}: {str(e)}"
        )

    # Extract response (standard OpenAI format)
    try:
        choices = response_data.get("choices", [])
        if not choices:
            raise AIProviderError("SLIM API returned empty choices")

        content = choices[0].get("message", {}).get("content", "")
        usage = response_data.get("usage", {})

        return {
            "content": content,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        }
    except (KeyError, IndexError) as e:
        raise AIProviderError(f"Unexpected SLIM API response format: {str(e)}")


def build_system_prompt(entity_context, custom_prompt=None, anonymize=False, anonymize_indexes=False):
    """
    Build the system prompt with entity context and optional custom instructions.

    Args:
        entity_context: dict from build_entity_description()
        custom_prompt: optional additional instructions from admin config
        anonymize: if True, append anonymization guidance for the AI
        anonymize_indexes: if True, append index anonymization guidance for the AI

    Returns:
        str: The complete system prompt
    """
    # Format entity context as pretty JSON
    entity_json = json.dumps(entity_context, indent=2, default=str)

    prompt = SYSTEM_PROMPT_TEMPLATE.replace("{entity_context}", entity_json)

    if anonymize:
        prompt += (
            "\n\n## Entity Name Anonymization\n"
            "Entity names (object and alias fields) in this context have been anonymized "
            "using SHA256 hashing for privacy. You MUST:\n"
            "- NEVER attempt to guess or reconstruct the original entity names\n"
            "- Always reference entities by their object_id (the stable identifier)\n"
            "- When suggesting TrackMe REST API calls, use the object_id parameter "
            "instead of the object parameter\n"
            "- When providing SPL searches or | trackme commands, prefer using "
            "object_id-based lookups\n"
            "- The investigation searches provided use anonymized entity references; "
            "guide the user to adapt them using the object_id field\n"
        )

    if anonymize_indexes:
        prompt += (
            "\n\n## Index Name Anonymization\n"
            "Splunk index names in this context have been anonymized using SHA256 hashing "
            "for privacy. You MUST:\n"
            "- NEVER attempt to guess or reconstruct the original index names\n"
            "- Inform the user that investigation searches contain hashed index names "
            "that must be replaced with the actual Splunk index names before execution\n"
            "- When presenting SPL searches, clearly highlight that index references "
            "(e.g. index=\"<hash>\", index IN (<hash>,...)) are anonymized placeholders\n"
            "- Guide the user to substitute the hashed values with their real index names\n"
        )

    if custom_prompt:
        prompt += f"\n\n## Additional Instructions\n{custom_prompt}\n"

    return prompt


def build_entity_context(service, request_info, tenant_id, object_category, object_value=None, *, object_id=None, anonymize=False, anonymize_indexes=False):
    """
    Build entity context for the AI Assistant.

    The entity record is retrieved through the in-process
    DecisionMakerEngine (NOT a direct KV store read) so that the decision
    maker's real-time enrichment is applied. This is required for
    dynamically joined fields such as `labels` / `labels_objects`
    (populated via dynamic_labels_lookup), score evaluation,
    and other fields that are NOT persisted on the raw KV record. Reading
    the raw KV record here would cause the LLM to see stale or empty
    values for those fields (e.g. labels would always appear as an empty
    list).

    Previously this function did an HTTP loopback to
    /trackme/v2/component/load_component_data. The engine produces the
    same enriched record via the same library code (set_*_status /
    scoring helpers / threshold lookups) but in-process — no HTTP
    round-trip, no JSON serialization, no second REST stack pass.

    Args:
        service: Splunk service connection
        request_info: REST request info object — must expose
            session_key, server_rest_uri, server_rest_port, and
            system_authtoken (the engine falls back to session_key when
            system_authtoken is None).
        tenant_id: The tenant identifier
        object_category: Entity type (e.g. "splk-dsm")
        object_value: Entity identifier (e.g. "main:syslog"). Mutually
            exclusive with object_id.
        object_id: Entity _key (SHA256 hash). Preferred for callers that
            already have the canonical key (e.g. alert actions) — looking
            up by _key is more robust than the human-readable `object`
            field, which can contain colons / slashes / punctuation.
            Mutually exclusive with object_value.
        anonymize: If True, anonymize object and alias values using SHA256 hashing.
        anonymize_indexes: If True, anonymize Splunk index names using SHA256 hashing.

    Returns:
        dict: The entity description, or None if entity not found
    """
    if object_value is None and object_id is None:
        raise ValueError("build_entity_context: either object_value or object_id must be provided")
    if object_value is not None and object_id is not None:
        raise ValueError("build_entity_context: object_value and object_id are mutually exclusive")

    type_config = ENTITY_TYPE_MAP.get(object_category)
    if not type_config:
        return None

    component = type_config["short"]

    if object_id is not None:
        lookup_value, lookup_field = object_id, "_key"
    else:
        lookup_value, lookup_field = object_value, "object"

    try:
        # Lazy import to keep module import-time cheap and avoid circulars.
        from trackme_libs_decisionmaker_engine import DecisionMakerEngine

        engine = DecisionMakerEngine(
            session_key=request_info.session_key,
            splunkd_uri=request_info.server_rest_uri,
            tenant_id=tenant_id,
            component=component,
            system_authtoken=request_info.system_authtoken,
            splunkd_port=request_info.server_rest_port,
            logger=logging.getLogger("trackme.ai.build_entity_context"),
        )
        engine.load()
        kvrecord = engine.evaluate_object_full(lookup_value, lookup_field=lookup_field)

        if kvrecord is None:
            logger.warning(
                f'function=build_entity_context, entity not found in decision maker view, '
                f'tenant_id="{tenant_id}", component="{component}", '
                f'lookup_field="{lookup_field}", lookup_value="{lookup_value}"'
            )
            return None

        return build_entity_description(
            request_info, service, tenant_id, object_category, kvrecord,
            anonymize=anonymize, anonymize_indexes=anonymize_indexes,
        )

    except Exception as e:
        logger.error(
            f'function=build_entity_context, tenant_id="{tenant_id}", '
            f'object_category="{object_category}", '
            f'lookup_field="{lookup_field}", lookup_value="{lookup_value}", '
            f'exception="{str(e)}"'
        )
        return None


def build_vtenants_system_prompt(vtenants_context, custom_prompt=None):
    """
    Build the system prompt with Virtual Tenants context and optional custom instructions.

    Args:
        vtenants_context: dict from build_vtenants_description()
        custom_prompt: optional additional instructions from admin config

    Returns:
        str: The complete system prompt
    """
    context_json = json.dumps(vtenants_context, indent=2, default=str)

    prompt = VTENANTS_SYSTEM_PROMPT_TEMPLATE.replace("{vtenants_context}", context_json)

    if custom_prompt:
        prompt += f"\n\n## Additional Instructions\n{custom_prompt}\n"

    return prompt


def build_vtenants_context(system_service, request_info):
    """
    Build Virtual Tenants context by calling the describe function internally.

    Args:
        system_service: Splunk service connection (system-level)
        request_info: REST request info object

    Returns:
        dict: The Virtual Tenants description, or None if unavailable
    """
    try:
        from trackme_libs_describe_vtenants import build_vtenants_description

        return build_vtenants_description(system_service, request_info)
    except Exception as e:
        logger.error(
            f'function=build_vtenants_context, exception="{str(e)}"'
        )
        return None


def build_tenant_home_system_prompt(tenant_home_context, custom_prompt=None):
    """
    Build the system prompt with Tenant Home context and optional custom instructions.

    Args:
        tenant_home_context: dict from build_tenant_home_description()
        custom_prompt: optional additional instructions from admin config

    Returns:
        str: The complete system prompt
    """
    context_json = json.dumps(tenant_home_context, indent=2, default=str)

    prompt = TENANT_HOME_SYSTEM_PROMPT_TEMPLATE.replace("{tenant_home_context}", context_json)

    if custom_prompt:
        prompt += f"\n\n## Additional Instructions\n{custom_prompt}\n"

    return prompt


def build_tenant_home_context(system_service, request_info, tenant_id):
    """
    Build Tenant Home context by calling the describe function internally.

    Args:
        system_service: Splunk service connection (system-level)
        request_info: REST request info object
        tenant_id: The tenant identifier

    Returns:
        dict: The Tenant Home description, or None if unavailable
    """
    try:
        from trackme_libs_describe_tenant_home import build_tenant_home_description

        return build_tenant_home_description(system_service, request_info, tenant_id)
    except Exception as e:
        logger.error(
            f'function=build_tenant_home_context, tenant_id="{tenant_id}", '
            f'exception="{str(e)}"'
        )
        return None


def build_fqm_dictionary_wizard_system_prompt(wizard_context, custom_prompt=None):
    """Build the system prompt for the FQM dictionary-wizard chat surface.

    This prompt is deliberately narrow: the only meaningful proposal at
    wizard time is ``fqm_advisor / dictionary_generate``. The prompt
    locks the LLM into recognising that one path and emitting a clean
    structured action-contract when the user asks for the dictionary.

    Args:
        wizard_context: dict from
            ``build_fqm_dictionary_wizard_description()``.
        custom_prompt: optional admin-supplied tail.
    Returns:
        str: the complete system prompt.
    """
    context_json = json.dumps(wizard_context, indent=2, default=str)
    prompt = FQM_DICTIONARY_WIZARD_SYSTEM_PROMPT_TEMPLATE.replace(
        "{fqm_dictionary_wizard_context}", context_json
    )
    if custom_prompt:
        prompt += f"\n\n## Additional Instructions\n{custom_prompt}\n"
    return prompt


def build_fqm_dictionary_wizard_context(system_service, request_info, tenant_id):
    """Build the FQM dictionary-wizard chat context.

    Wraps the describe builder with the same fail-soft pattern used by
    the tenant-home / vtenants context builders.
    """
    try:
        from trackme_libs_describe_fqm_dictionary_wizard import (
            build_fqm_dictionary_wizard_description,
        )

        return build_fqm_dictionary_wizard_description(
            system_service, request_info, tenant_id
        )
    except Exception as e:
        logger.error(
            f'function=build_fqm_dictionary_wizard_context, '
            f'tenant_id="{tenant_id}", exception="{str(e)}"'
        )
        return None


def build_rest_api_reference_system_prompt(context, custom_prompt=None):
    """Build the system prompt with REST API Reference context."""
    context_json = json.dumps(context, indent=2, default=str)
    prompt = REST_API_REFERENCE_SYSTEM_PROMPT_TEMPLATE.replace(
        "{rest_api_reference_context}", context_json
    )
    if custom_prompt:
        prompt += f"\n\n## Additional Instructions\n{custom_prompt}\n"
    return prompt


def build_rest_api_reference_context(system_service, request_info):
    """Build REST API Reference context."""
    try:
        from trackme_libs_describe_rest_api_reference import (
            build_rest_api_reference_description,
        )

        return build_rest_api_reference_description(system_service, request_info)
    except Exception as e:
        logger.error(
            f'function=build_rest_api_reference_context, exception="{str(e)}"'
        )
        return None


def build_backup_restore_system_prompt(context, custom_prompt=None):
    """Build the system prompt with Backup & Restore context."""
    context_json = json.dumps(context, indent=2, default=str)
    prompt = BACKUP_RESTORE_SYSTEM_PROMPT_TEMPLATE.replace(
        "{backup_restore_context}", context_json
    )
    if custom_prompt:
        prompt += f"\n\n## Additional Instructions\n{custom_prompt}\n"
    return prompt


def build_backup_restore_context(system_service, request_info):
    """Build Backup & Restore context."""
    try:
        from trackme_libs_describe_backup_restore import (
            build_backup_restore_description,
        )

        return build_backup_restore_description(system_service, request_info)
    except Exception as e:
        logger.error(
            f'function=build_backup_restore_context, exception="{str(e)}"'
        )
        return None


def build_maintenance_mode_system_prompt(context, custom_prompt=None):
    """Build the system prompt with Maintenance Mode context."""
    context_json = json.dumps(context, indent=2, default=str)
    prompt = MAINTENANCE_MODE_SYSTEM_PROMPT_TEMPLATE.replace(
        "{maintenance_mode_context}", context_json
    )
    if custom_prompt:
        prompt += f"\n\n## Additional Instructions\n{custom_prompt}\n"
    return prompt


def build_maintenance_mode_context(system_service, request_info):
    """Build Maintenance Mode context."""
    try:
        from trackme_libs_describe_maintenance import (
            build_maintenance_mode_description,
        )

        return build_maintenance_mode_description(system_service, request_info)
    except Exception as e:
        logger.error(
            f'function=build_maintenance_mode_context, exception="{str(e)}"'
        )
        return None


def build_maintenance_kdb_system_prompt(context, custom_prompt=None):
    """Build the system prompt with Maintenance KDB context."""
    context_json = json.dumps(context, indent=2, default=str)
    prompt = MAINTENANCE_KDB_SYSTEM_PROMPT_TEMPLATE.replace(
        "{maintenance_kdb_context}", context_json
    )
    if custom_prompt:
        prompt += f"\n\n## Additional Instructions\n{custom_prompt}\n"
    return prompt


def build_maintenance_kdb_context(system_service, request_info):
    """Build Maintenance KDB context."""
    try:
        from trackme_libs_describe_maintenance import (
            build_maintenance_kdb_description,
        )

        return build_maintenance_kdb_description(system_service, request_info)
    except Exception as e:
        logger.error(
            f'function=build_maintenance_kdb_context, exception="{str(e)}"'
        )
        return None


def build_bank_holidays_system_prompt(context, custom_prompt=None):
    """Build the system prompt with Bank Holidays context."""
    context_json = json.dumps(context, indent=2, default=str)
    prompt = BANK_HOLIDAYS_SYSTEM_PROMPT_TEMPLATE.replace(
        "{bank_holidays_context}", context_json
    )
    if custom_prompt:
        prompt += f"\n\n## Additional Instructions\n{custom_prompt}\n"
    return prompt


def build_bank_holidays_context(system_service, request_info):
    """Build Bank Holidays context."""
    try:
        from trackme_libs_describe_maintenance import (
            build_bank_holidays_description,
        )

        return build_bank_holidays_description(system_service, request_info)
    except Exception as e:
        logger.error(
            f'function=build_bank_holidays_context, exception="{str(e)}"'
        )
        return None


def build_license_system_prompt(context, custom_prompt=None):
    """Build the system prompt with License Management context."""
    context_json = json.dumps(context, indent=2, default=str)
    prompt = LICENSE_SYSTEM_PROMPT_TEMPLATE.replace(
        "{license_context}", context_json
    )
    if custom_prompt:
        prompt += f"\n\n## Additional Instructions\n{custom_prompt}\n"
    return prompt


def build_license_context(system_service, request_info):
    """Build License Management context."""
    try:
        from trackme_libs_describe_license import build_license_description

        return build_license_description(system_service, request_info)
    except Exception as e:
        logger.error(
            f'function=build_license_context, exception="{str(e)}"'
        )
        return None


def test_llm_connectivity(config, api_key, service=None):
    """
    Test connectivity to the configured LLM provider.

    Args:
        config: AI provider config dict
        api_key: The API key
        service: Splunk service connection (required for splunk_hosted provider)

    Returns:
        dict: {"success": True/False, "message": "...", "model": "...", "response_time_sec": ...}
    """
    test_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Reply with exactly: OK"},
    ]

    start_time = time.time()
    try:
        result = call_llm(config, api_key, test_messages, timeout=30, service=service)
        elapsed = round(time.time() - start_time, 2)
        return {
            "success": True,
            "message": f"Successfully connected to {config.get('ai_provider', 'unknown')} provider",
            "model": config.get("ai_model"),
            "response_time_sec": elapsed,
            "test_response": result["content"][:100],
        }
    except AIProviderError as e:
        elapsed = round(time.time() - start_time, 2)
        return {
            "success": False,
            "message": str(e),
            "model": config.get("ai_model"),
            "response_time_sec": elapsed,
        }


# ============================================================================
# AI Agent shared utilities
# ============================================================================


def get_recent_agent_inspect_result(service, tenant_id, object_id, sourcetype, max_age_minutes=30):
    """Search the summary index for the most recent successful agent inspect result.

    Shared by ML Advisor and Feed Lifecycle Advisor to inject prior inspect context
    into act-mode invocations, avoiding redundant read-tool calls.

    Args:
        service: Splunk SDK service object
        tenant_id: Tenant identifier
        object_id: Entity identifier
        sourcetype: Full sourcetype string, e.g. "trackme:ai_agent:ml_advisor:inspect"
        max_age_minutes: Look-back window in minutes (default 30)

    Returns:
        The ``result`` dict from the indexed event, or ``None`` on miss/error.
    """
    try:
        from trackme_libs import run_splunk_search, trackme_idx_for_tenant

        try:
            splunkd_uri = f"{service.scheme}://{service.host}:{service.port}"
            idx_settings = trackme_idx_for_tenant(service.token, splunkd_uri, tenant_id)
            summary_idx = idx_settings.get("trackme_summary_idx", "trackme_summary")
        except Exception:
            summary_idx = "trackme_summary"

        earliest = f"-{max_age_minutes}m"
        search_query = (
            f'search index="{summary_idx}" sourcetype="{sourcetype}" '
            f'earliest={earliest} '
            f'| spath | search object_id="{object_id}" tenant_id="{tenant_id}" status="success" '
            f'| sort -_time | head 1 | fields _raw'
        )
        search_params = {
            "earliest_time": earliest,
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }
        results_reader = run_splunk_search(service, search_query, search_params, max_retries=2)
        for result in results_reader:
            if isinstance(result, dict) and "_raw" in result:
                raw_event = json.loads(result["_raw"])
                result_data = raw_event.get("result")
                if result_data:
                    logger.info(
                        f"AI Agent: found recent inspect result for {object_id} "
                        f"({sourcetype}, within {max_age_minutes}m), injecting as act-mode prior context"
                    )
                    return result_data
    except Exception as e:
        logger.debug(
            f"AI Agent: could not retrieve recent inspect result for {object_id} "
            f"({sourcetype}): {e}"
        )
    return None


# ============================================================================
# Audit-dashboard event helpers
# ============================================================================
#
# Powers the AI Assistant audit dashboard.  Two sourcetypes are
# emitted to the tenant summary index:
#
#   * ``trackme:ai_assistant:chat``           — one event per interactive
#                                               chat job (success / error)
#   * ``trackme:ai_assistant:status_report``  — one event per stateful-
#                                               alert AI status report
#                                               (success / error / skipped)
#
# Both share a common envelope so a single SPL covers them.  Mirrors the
# pattern used by ``enrich_agent_event_for_audit`` for the AI Advisor on
# the Agent SDK side, kept deliberately separate because the AI Assistant
# has a different shape (messages, no tool use, two distinct kinds of
# call paths) and so the two audit dashboards stay independently
# evolvable.


def enrich_assistant_event_for_audit(
    event,
    *,
    user=None,
    automated=False,
    duration_ms=None,
    usage=None,
):
    """Add the audit-dashboard top-level fields to an AI Assistant event payload.

    Mutates and returns ``event``.  Centralised so every AI Assistant
    code path surfaces the same field shape for the AI Assistant audit
    dashboard's SPL queries.

    Fields added:
      - ``user``                — calling Splunk user (or ``"automated"``
                                  for stateful-alert status reports, or
                                  ``"unknown"`` when neither is known)
      - ``automated``           — bool stringified (``"true"`` / ``"false"``)
      - ``duration_ms``         — end-to-end wall time in milliseconds
      - ``prompt_tokens``       — usage breakdown (when available)
      - ``completion_tokens``
      - ``total_tokens``

    All extras are top-level so the audit dashboard can ``stats`` /
    ``timechart`` over them without ``spath`` against a nested object.
    """
    if user:
        event["user"] = user
    elif automated:
        event["user"] = "automated"
    else:
        event["user"] = "unknown"

    # Mirror the AI Advisor convention of indexing booleans as the literal
    # strings "true" / "false" — keeps the SPL portable across the two
    # dashboards (``count(eval(automated="true"))`` works either way).
    event["automated"] = "true" if automated else "false"

    if duration_ms is not None:
        try:
            event["duration_ms"] = int(duration_ms)
        except (ValueError, TypeError):
            pass

    if isinstance(usage, dict):
        for src_key, out_key in (
            ("prompt_tokens", "prompt_tokens"),
            ("completion_tokens", "completion_tokens"),
            ("total_tokens", "total_tokens"),
        ):
            v = usage.get(src_key)
            if v is None:
                continue
            try:
                event[out_key] = int(v)
            except (ValueError, TypeError):
                pass

    return event


def index_assistant_event(
    service,
    tenant_id,
    sourcetype,
    event,
    *,
    session_key=None,
    splunkd_uri=None,
    server_name=None,
):
    """Submit an AI Assistant audit event to the tenant summary index.

    Best-effort: the function never raises — failures are swallowed and
    logged at WARNING.  Indexing must never block the chat response or
    the email delivery.

    Args:
        service: ``splunklib.client.Service`` bound to the ``trackme`` app
            namespace.  Used to call ``service.indexes[idx].submit(...)``.
        tenant_id: Tenant the event belongs to.  Resolves the per-tenant
            ``trackme_summary_idx`` via ``trackme_idx_for_tenant`` (falls
            back to the convention default ``trackme_summary``).
        sourcetype: One of ``trackme:ai_assistant:chat`` or
            ``trackme:ai_assistant:status_report``.
        event: dict — JSON-serialised before submit.
        session_key: Optional override for the splunkd auth token used to
            resolve the tenant index.  Defaults to ``service.token`` —
            which works for both system-level connections (REST chat
            handler) and the alert helper's session_key.
        splunkd_uri: Optional override for the splunkd base URL.
            Defaults to ``service.scheme://service.host:service.port``.
        server_name: Optional ``host`` field on the indexed event.
            Defaults to splunkd's automatic value.
    """
    try:
        # Local import — keeps module load light and avoids circular imports.
        from trackme_libs import trackme_idx_for_tenant

        token = session_key or getattr(service, "token", None) or ""
        uri = splunkd_uri or f"{service.scheme}://{service.host}:{service.port}"

        try:
            idx_settings = trackme_idx_for_tenant(token, uri, tenant_id)
            tenant_summary_idx = idx_settings.get(
                "trackme_summary_idx", "trackme_summary"
            )
        except Exception:
            tenant_summary_idx = "trackme_summary"

        target = service.indexes[tenant_summary_idx]
        submit_kwargs = {
            "event": json.dumps(event),
            "source": "trackme:ai_assistant",
            "sourcetype": sourcetype,
        }
        if server_name:
            submit_kwargs["host"] = server_name
        target.submit(**submit_kwargs)
    except Exception as e:
        logger.warning(
            f'function=index_assistant_event, tenant_id="{tenant_id}", '
            f'sourcetype="{sourcetype}", action="index_failed", '
            f'exception="{str(e)}"'
        )


# ============================================================================
# Async job store and streaming LLM support (KV store-backed)
# ============================================================================

# KV store-based job store for cross-process async LLM requests.
# Each job is stored in the kv_trackme_ai_jobs collection with _key = job_id.
_KV_COLLECTION = "kv_trackme_ai_jobs"
_JOB_TTL_SECONDS = 600  # Clean up jobs older than 10 minutes
_STALE_RUNNING_BUFFER_SECONDS = 120  # Grace period beyond the job's own timeout


def _get_collection(service):
    """Get the KV store collection object."""
    return service.kvstore[_KV_COLLECTION]


def _purge_expired_jobs(service):
    """Remove expired jobs from KV store.

    Phase 1: Delete completed/error/cancelled jobs whose reference_time (max of
             created_at, last_activity) is older than _JOB_TTL_SECONDS.
             Uses reference_time so a job that ran 12min then finished is not
             purged immediately—clients have time to retrieve the final response.
    Phase 2: Force-error any running jobs whose created_at + timeout + buffer
             has elapsed (orphaned worker threads).
    """
    now = time.time()
    cutoff = now - _JOB_TTL_SECONDS

    # Phase 1: delete finished jobs past TTL (by reference_time, not created_at)
    try:
        collection = _get_collection(service)
        finished_jobs = collection.data.query(
            query=json.dumps({"status": {"$ne": "running"}})
        )
        for job in finished_jobs:
            try:
                created_at = float(job.get("created_at", 0))
            except (ValueError, TypeError):
                created_at = 0.0
            try:
                last_activity = float(job.get("last_activity", 0))
            except (ValueError, TypeError):
                last_activity = 0.0
            reference_time = (
                max(created_at, last_activity) if last_activity > 0 else created_at
            )
            if reference_time > 0 and reference_time < cutoff:
                job_id = job.get("_key", "")
                if job_id:
                    try:
                        collection.data.delete(json.dumps({"_key": job_id}))
                    except Exception:
                        pass
    except Exception:
        pass

    # Phase 2: transition stale running jobs to error
    try:
        collection = _get_collection(service)
        running_jobs = collection.data.query(
            query=json.dumps({"status": "running"})
        )
        for job in running_jobs:
            try:
                created_at = float(job.get("created_at", 0))
            except (ValueError, TypeError):
                created_at = 0.0
            try:
                last_activity = float(job.get("last_activity", 0))
            except (ValueError, TypeError):
                last_activity = 0.0
            reference_time = max(created_at, last_activity) if last_activity > 0 else created_at
            if reference_time <= 0:
                continue  # Can't determine age — skip rather than kill
            job_timeout = float(job.get("timeout", _JOB_TTL_SECONDS))
            if now > reference_time + job_timeout + _STALE_RUNNING_BUFFER_SECONDS:
                job_id = job.get("_key", "")
                logger.warning(
                    f'function=_purge_expired_jobs, action="stale_job_cleanup", '
                    f'job_id="{job_id}", created_at={created_at}, '
                    f'last_activity={last_activity}, reference_time={reference_time}, '
                    f'timeout={job_timeout}, age_sec={round(now - reference_time, 1)}'
                )
                try:
                    collection.data.update(
                        job_id,
                        json.dumps(
                            {
                                "status": "error",
                                "error": (
                                    "Job timed out — the AI provider did not "
                                    "respond within the configured timeout. "
                                    "The worker thread may have terminated "
                                    "unexpectedly."
                                ),
                            }
                        ),
                    )
                    _release_concurrency_slot(job_id)
                except Exception:
                    pass
    except Exception:
        pass


def _create_job(service, timeout=None, entity_context_loaded=None):
    """Create a new job in KV store and return its ID.

    All initial fields are written in a single insert to avoid partial-update
    race conditions where KV store reads may not reflect a subsequent update.

    Args:
        service: Splunk service connection.
        timeout: The LLM request timeout for this job (seconds).
                 Stored on the record so stale-job detection knows
                 how long to wait before declaring a job orphaned.
        entity_context_loaded: Whether entity context was successfully loaded
                               (True/False/None).

    Raises:
        AIProviderError: If the job cannot be persisted to KV store.
    """
    job_id = str(uuid.uuid4())
    ctx_str = ""
    if entity_context_loaded is not None:
        ctx_str = str(entity_context_loaded).lower()
    now = time.time()
    record = {
        "_key": job_id,
        "status": "running",
        "content": "",
        "usage": json.dumps({}),
        "error": "",
        "entity_context_loaded": ctx_str,
        "created_at": now,
        "last_activity": now,  # Updated during streaming to prevent stale-job misclassification
        "timeout": timeout if timeout is not None else _JOB_TTL_SECONDS,
    }
    try:
        collection = _get_collection(service)
        collection.data.insert(json.dumps(record))
    except Exception as e:
        logger.error(f"Failed to create job in KV store: {e}")
        raise AIProviderError(f"Failed to create AI chat job: {e}")
    _purge_expired_jobs(service)
    return job_id


def _get_job_status_raw(service, job_id):
    """Read the current status of a job from KV store (no side effects)."""
    try:
        collection = _get_collection(service)
        record = collection.data.query_by_id(job_id)
        return record.get("status", "running")
    except Exception:
        return None


def _update_job(service, job_id, **kwargs):
    """Update a job's fields in KV store."""
    try:
        collection = _get_collection(service)
        # Serialize complex types for KV store (all values must be strings/numbers)
        update_data = {}
        for k, v in kwargs.items():
            if isinstance(v, (dict, list)):
                update_data[k] = json.dumps(v)
            elif v is None:
                update_data[k] = ""
            elif isinstance(v, bool):
                update_data[k] = str(v).lower()
            else:
                update_data[k] = v
        collection.data.update(job_id, json.dumps(update_data))
    except Exception as e:
        logger.error(f"Failed to update job {job_id} in KV store: {e}")


def _parse_entity_ctx(value):
    """Parse entity_context_loaded string to bool or None."""
    if isinstance(value, str):
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        return None
    return value


def get_job_status(service, job_id):
    """
    Get the current status of a job from KV store.

    If the job is still marked as running but its timeout has elapsed
    (plus a grace buffer), it is automatically transitioned to error.
    This handles orphaned jobs from dead worker threads.

    Args:
        service: Splunk service connection
        job_id: The job identifier

    Returns:
        dict with status, content, usage, error, entity_context_loaded
        or None if job not found
    """
    try:
        collection = _get_collection(service)
        record = collection.data.query_by_id(job_id)

        status = record.get("status", "running")

        # Detect stale running jobs — if a worker thread died, the status
        # stays "running" forever.  Transition to error so the caller (and
        # the frontend) gets immediate feedback instead of polling forever.
        if status == "running":
            try:
                created_at = float(record.get("created_at", 0))
            except (ValueError, TypeError):
                created_at = 0.0
            # Use last_activity if available (streaming jobs update this);
            # fall back to created_at for jobs that haven't started streaming.
            try:
                last_activity = float(record.get("last_activity", 0))
            except (ValueError, TypeError):
                last_activity = 0.0
            # Use the more recent of created_at and last_activity
            reference_time = max(created_at, last_activity) if last_activity > 0 else created_at
            job_timeout = float(record.get("timeout", _JOB_TTL_SECONDS))
            # Guard: if reference_time is missing or zero, we cannot determine
            # the job age — skip stale detection rather than killing an
            # active job whose timestamp was not read back correctly.
            if reference_time > 0 and (time.time() - reference_time) > job_timeout + _STALE_RUNNING_BUFFER_SECONDS:
                age = time.time() - reference_time
                error_msg = (
                    "Job timed out — the AI provider did not respond "
                    "within the configured timeout. The worker thread "
                    "may have terminated unexpectedly."
                )
                logger.warning(
                    f'function=get_job_status, action="stale_job_detected", '
                    f'job_id="{job_id}", created_at={created_at}, '
                    f'last_activity={last_activity}, reference_time={reference_time}, '
                    f'timeout={job_timeout}, age_since_activity_sec={round(age, 1)}'
                )
                try:
                    collection.data.update(
                        job_id,
                        json.dumps({"status": "error", "error": error_msg}),
                    )
                    _release_concurrency_slot(job_id)
                except Exception:
                    pass
                return {
                    "status": "error",
                    "content": record.get("content", ""),
                    "usage": {},
                    "error": error_msg,
                    "entity_context_loaded": _parse_entity_ctx(
                        record.get("entity_context_loaded", "")
                    ),
                }

        # Normal path: deserialize and return
        usage = record.get("usage", "{}")
        if isinstance(usage, str):
            try:
                usage = json.loads(usage)
            except (json.JSONDecodeError, TypeError):
                usage = {}
        return {
            "status": status,
            "content": record.get("content", ""),
            "usage": usage,
            "error": record.get("error", "") or None,
            "entity_context_loaded": _parse_entity_ctx(
                record.get("entity_context_loaded", "")
            ),
        }
    except Exception:
        return None


def cancel_chat_job(service, job_id):
    """
    Cancel an in-flight AI chat job and release its concurrency slot.

    When the client closes the panel or navigates away, the backend job keeps
    running and holds an _active_chats slot until completion. This function
    releases the slot immediately so other users can use the AI assistant.

    The worker thread may continue running until the LLM responds, but the
    response will be discarded (no one is polling). The slot is freed so
    ai_busy rejections are avoided.

    Args:
        service: Splunk service connection
        job_id: The job identifier to cancel

    Returns:
        tuple: (success: bool, status: str)
            - (True, "cancelled") if the job was running and was cancelled
            - (True, "already_done") if the job was already complete/error/cancelled
            - (False, "not_found") if the job does not exist
    """
    try:
        collection = _get_collection(service)
        record = collection.data.query_by_id(job_id)
    except Exception:
        return False, "not_found"

    status = record.get("status", "running")
    if status != "running":
        return True, "already_done"

    _release_concurrency_slot(job_id)
    try:
        collection = _get_collection(service)
        collection.data.update(
            job_id,
            json.dumps({
                "status": "cancelled",
                "error": "Cancelled by client",
                "last_activity": time.time(),
            }),
        )
        logger.info(
            f'function=cancel_chat_job, job_id="{job_id}", action="slot_released"'
        )
    except Exception as e:
        logger.warning(
            f'function=cancel_chat_job, job_id="{job_id}", '
            f'failed_to_update_kv="{e}"'
        )
        # Slot was already released — still consider it success
    return True, "cancelled"


# ---- Streaming LLM functions ----


def _is_local_url(base_url):
    """Check if a URL points to a local address (localhost or 127.0.0.1)."""
    try:
        hostname = urllib.parse.urlparse(base_url).hostname or ""
        return hostname in ("localhost", "127.0.0.1", "::1")
    except Exception:
        return False


def _build_ssl_context(base_url):
    """Build SSL context, allowing self-signed certs for localhost."""
    ctx = ssl.create_default_context()
    if _is_local_url(base_url):
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _ollama_pull_model(base_url, model, timeout=600, api_key=None):
    """
    Pull a model on the Ollama server. Blocks until the pull is complete.

    Derives the native Ollama API root from the OpenAI-compatible base_url
    (e.g. http://127.0.0.1:11434/v1 → http://127.0.0.1:11434/api/pull).

    Args:
        base_url: The OpenAI-compatible base URL (with /v1 suffix)
        model: Model name to pull (e.g. "qwen2.5:1.5b")
        timeout: Request timeout in seconds (default 10 minutes)
        api_key: Optional API key for Bearer auth (Ollama behind reverse proxy)
    """
    root_url = re.sub(r"/v1/?$", "", base_url)
    url = f"{root_url}/api/pull"
    payload = json.dumps({"name": model, "stream": False}).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": _USER_AGENT}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method="POST",
    )
    ctx = _build_ssl_context(base_url)
    resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    try:
        resp.read()
    finally:
        resp.close()


def _call_ollama_native_streaming(config, api_key, messages, timeout, job_id, service):
    """
    Call Ollama's native /api/chat endpoint with streaming.

    Uses the native API instead of the OpenAI-compatible endpoint so we can
    pass num_ctx (context window size) via the options parameter. The
    OpenAI-compatible /v1/chat/completions endpoint does NOT support num_ctx,
    which causes silent prompt truncation on small models.

    Streaming format: newline-delimited JSON (NDJSON), not SSE.
    Each line: {"message": {"role": "assistant", "content": "..."}, "done": false}
    Final line: {"done": true, "prompt_eval_count": N, "eval_count": N, ...}

    Args:
        config: AI provider config dict (must contain ai_base_url, ai_model)
        api_key: The API key (unused for Ollama, kept for signature consistency)
        messages: List of message dicts [{"role": "...", "content": "..."}]
        timeout: Request timeout in seconds
        job_id: The job ID to update with streaming content
        service: Splunk service connection for KV store updates

    Returns:
        dict: {"content": "...", "usage": {...}}

    Raises:
        AIProviderError: If the API call fails
    """
    base_url = config.get("ai_base_url", "").rstrip("/")
    model = config.get("ai_model", "")
    max_tokens = max(1, int(config.get("ai_max_tokens", "4096")))
    temperature = float(config.get("ai_temperature", "0.3"))
    context_window = max(1, int(config.get("ai_context_window", "8192")))

    if not base_url or not model:
        raise AIProviderError("AI provider base_url and model must be configured")

    # Derive native API URL: strip /v1 suffix → http://host:port/api/chat
    root_url = re.sub(r"/v1/?$", "", base_url)
    url = f"{root_url}/api/chat"

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {
            "num_ctx": context_window,
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }

    headers = {"Content-Type": "application/json", "User-Agent": _USER_AGENT}
    # Support Bearer token auth for Ollama behind a reverse proxy (e.g. Nginx)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    ctx = _build_ssl_context(base_url)

    accumulated_content = ""
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    pulled = False
    first_token_logged = False
    last_heartbeat = time.time()

    for attempt in range(2):
        resp = None
        try:
            _streaming_start = time.time()
            resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)

            # Ollama streams NDJSON: one JSON object per line
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Extract content from message
                msg = chunk.get("message", {})
                content_piece = msg.get("content", "")

                if content_piece:
                    # Log first token received
                    if not first_token_logged:
                        first_token_logged = True
                        ttft = round(time.time() - _streaming_start, 2)
                        logger.info(
                            f'function=_call_ollama_native_streaming, action="first_token", '
                            f'job_id="{job_id}", model="{model}", '
                            f'time_to_first_token_sec={ttft}'
                        )
                    # Periodic heartbeat every 30s
                    now = time.time()
                    if now - last_heartbeat >= 30:
                        logger.info(
                            f'function=_call_ollama_native_streaming, action="streaming_progress", '
                            f'job_id="{job_id}", model="{model}", '
                            f'elapsed_sec={round(now - _streaming_start, 2)}, '
                            f'chars_received={len(accumulated_content)}'
                        )
                        last_heartbeat = now
                    accumulated_content += content_piece
                    _update_job(service, job_id, content=accumulated_content, last_activity=time.time())

                # Final chunk: done=true contains usage stats
                if chunk.get("done"):
                    usage = {
                        "prompt_tokens": chunk.get("prompt_eval_count", 0),
                        "completion_tokens": chunk.get("eval_count", 0),
                        "total_tokens": (
                            chunk.get("prompt_eval_count", 0)
                            + chunk.get("eval_count", 0)
                        ),
                    }
                    break

            resp.close()
            resp = None
            break  # success — exit retry loop

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass

            # Auto-pull when model is not found (404)
            if e.code == 404 and not pulled and "not found" in error_body.lower():
                logger.info(
                    f'function=_call_ollama_native_streaming, '
                    f'model "{model}" not found on Ollama server, auto-pulling...'
                )
                _update_job(
                    service, job_id,
                    content="⏳ Pulling model, first use may take a few minutes...",
                )
                try:
                    _ollama_pull_model(base_url, model, timeout=timeout, api_key=api_key)
                    logger.info(
                        f'function=_call_ollama_native_streaming, '
                        f'model "{model}" pulled successfully, retrying request...'
                    )
                except Exception as pull_err:
                    raise AIProviderError(
                        f"Model '{model}' not found and auto-pull failed: {str(pull_err)}"
                    )
                pulled = True
                # Rebuild request object (consumed by first attempt)
                req = urllib.request.Request(
                    url, data=data, headers=headers, method="POST"
                )
                accumulated_content = ""
                first_token_logged = False
                last_heartbeat = time.time()
                continue  # retry

            raise AIProviderError(f"Ollama API returned HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise AIProviderError(
                f"Failed to connect to Ollama at {root_url}: {str(e.reason)}"
            )
        except TimeoutError:
            elapsed_so_far = round(time.time() - _streaming_start, 2)
            logger.error(
                f'function=_call_ollama_native_streaming, action="timeout", '
                f'job_id="{job_id}", model="{model}", '
                f'timeout_sec={timeout}, elapsed_sec={elapsed_so_far}, '
                f'chars_received_before_timeout={len(accumulated_content)}'
            )
            raise AIProviderError(f"Ollama request timed out after {timeout}s")
        finally:
            if resp is not None:
                try:
                    resp.close()
                except Exception:
                    pass

    return {"content": accumulated_content, "usage": usage}


def _call_openai_compatible_streaming(config, api_key, messages, timeout, job_id, service):
    """
    Call an OpenAI-compatible API with streaming enabled.
    Updates the job store with content as tokens arrive.

    Args:
        config: AI provider config dict
        api_key: The API key for authentication
        messages: List of message dicts
        timeout: Request timeout in seconds
        job_id: The job ID to update with streaming content
        service: Splunk service connection for KV store updates

    Returns:
        dict: {"content": "...", "usage": {...}}

    Raises:
        AIProviderError: If the API call fails
    """
    base_url = config.get("ai_base_url", "").rstrip("/")
    model = config.get("ai_model", "")
    provider = config.get("ai_provider", "openai")
    max_tokens = max(1, int(config.get("ai_max_tokens", "4096")))
    temperature = float(config.get("ai_temperature", "0.3"))

    if not base_url or not model:
        raise AIProviderError("AI provider base_url and model must be configured")

    # Providers that require an API key (everything except ollama)
    if not api_key and provider != "ollama":
        raise AIProviderError(
            f"API key is required for provider '{provider}'. "
            "Please configure the API key in the AI Provider settings."
        )

    # Azure OpenAI uses a different URL scheme and auth header
    if provider == "azure":
        api_version = config.get("ai_azure_api_version", "2024-10-21")
        url = f"{base_url}/chat/completions?api-version={api_version}"
    else:
        url = f"{base_url}/chat/completions"

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }

    headers = {"Content-Type": "application/json", "User-Agent": _USER_AGENT}
    if api_key:
        if provider == "azure":
            headers["api-key"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    ctx = _build_ssl_context(base_url)

    accumulated_content = ""
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    pulled = False
    first_token_logged = False
    last_heartbeat = time.time()

    for attempt in range(2):
        resp = None
        try:
            _streaming_start = time.time()
            resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            raw_lines = []
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                raw_lines.append(line)
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content_piece = delta.get("content", "")
                        if content_piece:
                            # Log first token received
                            if not first_token_logged:
                                first_token_logged = True
                                ttft = round(time.time() - _streaming_start, 2)
                                logger.info(
                                    f'function=_call_openai_compatible_streaming, action="first_token", '
                                    f'job_id="{job_id}", model="{model}", '
                                    f'time_to_first_token_sec={ttft}'
                                )
                            # Periodic heartbeat every 30s
                            now = time.time()
                            if now - last_heartbeat >= 30:
                                logger.info(
                                    f'function=_call_openai_compatible_streaming, action="streaming_progress", '
                                    f'job_id="{job_id}", model="{model}", '
                                    f'elapsed_sec={round(now - _streaming_start, 2)}, '
                                    f'chars_received={len(accumulated_content)}'
                                )
                                last_heartbeat = now
                            accumulated_content += content_piece
                            _update_job(service, job_id, content=accumulated_content, last_activity=time.time())
                        # Some providers include usage in the final chunk
                        if "usage" in chunk and chunk["usage"]:
                            u = chunk["usage"]
                            usage = {
                                "prompt_tokens": u.get("prompt_tokens", 0),
                                "completion_tokens": u.get("completion_tokens", 0),
                                "total_tokens": u.get("total_tokens", 0),
                            }
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
            resp.close()
            resp = None

            # Fallback: if no SSE data: lines were parsed, try standard JSON response.
            # Some custom/proxy endpoints may ignore stream=true and return a normal
            # chat completion body.
            if not accumulated_content and raw_lines:
                try:
                    full_body = "\n".join(raw_lines)
                    response_json = json.loads(full_body)
                    content = response_json["choices"][0]["message"]["content"]
                    if content:
                        accumulated_content = content
                        _update_job(service, job_id, content=accumulated_content, last_activity=time.time())
                        if "usage" in response_json and response_json["usage"]:
                            u = response_json["usage"]
                            usage = {
                                "prompt_tokens": u.get("prompt_tokens", 0),
                                "completion_tokens": u.get("completion_tokens", 0),
                                "total_tokens": u.get("total_tokens", 0),
                            }
                        logger.info(
                            f'function=_call_openai_compatible_streaming, action="non_sse_fallback", '
                            f'job_id="{job_id}", model="{model}", '
                            f'content_length={len(accumulated_content)}'
                        )
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass  # not valid JSON either — accumulated_content stays empty

            break  # success — exit retry loop

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass

            # Auto-pull for Ollama when model is not found
            if (
                e.code == 404
                and not pulled
                and config.get("ai_provider") == "ollama"
                and "not found" in error_body.lower()
            ):
                logger.info(
                    f'function=_call_openai_compatible_streaming, '
                    f'model "{model}" not found on Ollama server, auto-pulling...'
                )
                _update_job(
                    service, job_id,
                    content="⏳ Pulling model, first use may take a few minutes...",
                )
                try:
                    _ollama_pull_model(base_url, model, timeout=timeout, api_key=api_key)
                    logger.info(
                        f'function=_call_openai_compatible_streaming, '
                        f'model "{model}" pulled successfully, retrying request...'
                    )
                except Exception as pull_err:
                    raise AIProviderError(
                        f"Model '{model}' not found and auto-pull failed: {str(pull_err)}"
                    )
                pulled = True
                # Rebuild request object (consumed by first attempt)
                req = urllib.request.Request(
                    url, data=data, headers=headers, method="POST"
                )
                accumulated_content = ""
                first_token_logged = False
                last_heartbeat = time.time()
                continue  # retry

            raise AIProviderError(f"LLM API returned HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise AIProviderError(
                f"Failed to connect to LLM provider at {base_url}: {str(e.reason)}"
            )
        except TimeoutError:
            elapsed_so_far = round(time.time() - _streaming_start, 2)
            logger.error(
                f'function=_call_openai_compatible_streaming, action="timeout", '
                f'job_id="{job_id}", model="{model}", '
                f'timeout_sec={timeout}, elapsed_sec={elapsed_so_far}, '
                f'chars_received_before_timeout={len(accumulated_content)}'
            )
            raise AIProviderError(f"LLM request timed out after {timeout}s")
        finally:
            if resp is not None:
                try:
                    resp.close()
                except Exception:
                    pass

    return {"content": accumulated_content, "usage": usage}


def _call_anthropic_streaming(config, api_key, messages, timeout, job_id, service):
    """
    Call the Anthropic API with streaming enabled.
    Updates the job store with content as tokens arrive.

    Args:
        config: AI provider config dict
        api_key: The API key for authentication
        messages: List of message dicts
        timeout: Request timeout in seconds
        job_id: The job ID to update with streaming content
        service: Splunk service connection for KV store updates

    Returns:
        dict: {"content": "...", "usage": {...}}

    Raises:
        AIProviderError: If the API call fails
    """
    base_url = config.get("ai_base_url", "").rstrip("/")
    model = config.get("ai_model", "")
    max_tokens = max(1, int(config.get("ai_max_tokens", "4096")))
    temperature = float(config.get("ai_temperature", "0.3"))

    if not base_url or not model:
        raise AIProviderError("AI provider base_url and model must be configured")

    if not api_key:
        raise AIProviderError("Anthropic API key is required")

    # Extract system prompt from messages
    system_prompt = None
    non_system_messages = []
    for msg in messages:
        if msg.get("role") == "system":
            if system_prompt is None:
                system_prompt = msg["content"]
            else:
                system_prompt += "\n\n" + msg["content"]
        else:
            non_system_messages.append(
                {"role": msg["role"], "content": msg["content"]}
            )

    url = f"{base_url}/messages"
    payload = {
        "model": model,
        "messages": non_system_messages,
        "max_tokens": max_tokens,
        "stream": True,
    }
    # Skip ``temperature`` for models that have deprecated it (Opus 4+).
    # See module-level comment block on Anthropic temperature handling.
    if _anthropic_supports_temperature(model):
        payload["temperature"] = temperature
    # System prompt wrapped in cache_control content-block form when
    # prompt caching is enabled AND the prompt meets Anthropic's
    # ~1024-token minimum — see ``_build_anthropic_system_field``.
    system_field = _build_anthropic_system_field(config, system_prompt)
    if system_field is not None:
        payload["system"] = system_field

    headers = {
        "Content-Type": "application/json",
        "User-Agent": _USER_AGENT,
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    ctx = ssl.create_default_context()

    def _open_stream(payload_dict):
        body = json.dumps(payload_dict).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        return urllib.request.urlopen(request, timeout=timeout, context=ctx)

    accumulated_content = ""
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    first_token_logged = False
    last_heartbeat = time.time()

    resp = None
    try:
        _streaming_start = time.time()
        try:
            resp = _open_stream(payload)
        except urllib.error.HTTPError as open_e:
            # Anthropic raises HTTP 400 immediately (before the SSE
            # stream begins) when the request is rejected — including
            # the ``temperature is deprecated`` case for Opus 4+. The
            # proactive ``_anthropic_supports_temperature`` filter
            # above handles known models; this backstop covers any
            # future model that adopts the same deprecation.
            err_body = ""
            try:
                err_body = open_e.read().decode("utf-8")
            except Exception:
                pass
            if (
                open_e.code == 400
                and "temperature" in payload
                and _is_temperature_deprecation_error(err_body)
            ):
                logger.warning(
                    f"Anthropic rejected streaming request for model={model!r} "
                    f"with temperature; retrying once without temperature. "
                    f"Consider extending _anthropic_supports_temperature() "
                    f"to cover this model."
                )
                retry_payload = {k: v for k, v in payload.items() if k != "temperature"}
                resp = _open_stream(retry_payload)
            elif (
                open_e.code == 400
                and isinstance(payload.get("system"), list)
                and _is_prompt_caching_error(err_body)
            ):
                # Mirror the non-streaming cache_control retry — see
                # ``_call_anthropic`` and ``_is_prompt_caching_error``
                # for the full rationale. Fall back to plain string
                # ``system`` so the chat session survives any future
                # Anthropic cache_control validation tightening.
                logger.warning(
                    f"Anthropic rejected streaming request for model={model!r} "
                    f"with cache_control system field; retrying once without "
                    f"prompt caching for this request. error_body={err_body!r}"
                )
                retry_payload = dict(payload)
                retry_payload["system"] = system_prompt  # plain string
                resp = _open_stream(retry_payload)
            else:
                # Original HTTPError body has already been consumed by
                # ``open_e.read()`` above; raise AIProviderError with
                # the captured body rather than letting the outer
                # handler re-read an empty stream.
                raise AIProviderError(
                    f"Anthropic API returned HTTP {open_e.code}: {err_body}"
                )
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            if line.startswith("data: "):
                data_str = line[6:]
                try:
                    chunk = json.loads(data_str)
                    event_type = chunk.get("type", "")
                    if event_type == "content_block_delta":
                        text_piece = chunk.get("delta", {}).get("text", "")
                        if text_piece:
                            # Log first token received
                            if not first_token_logged:
                                first_token_logged = True
                                ttft = round(time.time() - _streaming_start, 2)
                                logger.info(
                                    f'function=_call_anthropic_streaming, action="first_token", '
                                    f'job_id="{job_id}", model="{model}", '
                                    f'time_to_first_token_sec={ttft}'
                                )
                            # Periodic heartbeat every 30s
                            now = time.time()
                            if now - last_heartbeat >= 30:
                                logger.info(
                                    f'function=_call_anthropic_streaming, action="streaming_progress", '
                                    f'job_id="{job_id}", model="{model}", '
                                    f'elapsed_sec={round(now - _streaming_start, 2)}, '
                                    f'chars_received={len(accumulated_content)}'
                                )
                                last_heartbeat = now
                            accumulated_content += text_piece
                            _update_job(service, job_id, content=accumulated_content, last_activity=time.time())
                    elif event_type == "message_delta":
                        u = chunk.get("usage", {})
                        usage["completion_tokens"] = u.get("output_tokens", 0)
                    elif event_type == "message_start":
                        u = chunk.get("message", {}).get("usage", {})
                        usage["prompt_tokens"] = u.get("input_tokens", 0)
                        # Anthropic-specific cache telemetry — direct
                        # evidence that the cache_control marker is
                        # being honoured. Surfaced as both the usage
                        # dict and an INFO log line so operators can
                        # verify locally without the Anthropic console.
                        cache_write = u.get("cache_creation_input_tokens", 0) or 0
                        cache_read = u.get("cache_read_input_tokens", 0) or 0
                        usage["cache_creation_input_tokens"] = cache_write
                        usage["cache_read_input_tokens"] = cache_read
                        if cache_write or cache_read:
                            logger.info(
                                f'function=_call_anthropic_streaming, action="prompt_cache_usage", '
                                f'job_id="{job_id}", model="{model}", '
                                f'cache_creation_input_tokens={cache_write}, '
                                f'cache_read_input_tokens={cache_read}, '
                                f'input_tokens={u.get("input_tokens", 0)}'
                            )
                except (json.JSONDecodeError, KeyError):
                    continue
        resp.close()
        resp = None

    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        raise AIProviderError(
            f"Anthropic API returned HTTP {e.code}: {error_body}"
        )
    except urllib.error.URLError as e:
        raise AIProviderError(
            f"Failed to connect to Anthropic API at {base_url}: {str(e.reason)}"
        )
    except TimeoutError:
        elapsed_so_far = round(time.time() - _streaming_start, 2)
        logger.error(
            f'function=_call_anthropic_streaming, action="timeout", '
            f'job_id="{job_id}", model="{model}", '
            f'timeout_sec={timeout}, elapsed_sec={elapsed_so_far}, '
            f'chars_received_before_timeout={len(accumulated_content)}'
        )
        raise AIProviderError(f"Anthropic API request timed out after {timeout}s")
    finally:
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass

    usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
    return {"content": accumulated_content, "usage": usage}


def _call_splunk_hosted_streaming(config, messages, timeout, job_id, service):
    """
    Call the Splunk SLIM API with streaming enabled.
    Updates the job store with content as tokens arrive.

    Uses SSE format identical to OpenAI's streaming, with model_id
    instead of model in the request payload.

    The configured ``ai_model`` value may be either a ``model_name`` (display
    name like ``gpt-oss-20b``) or the actual ``model_id``.  The function
    auto-resolves via ``_resolve_splunk_hosted_model()`` so both work.

    Args:
        config: AI provider config dict (must contain ai_model)
        messages: List of message dicts
        timeout: Request timeout in seconds
        job_id: The job ID to update with streaming content
        service: Splunk service connection for SCS token retrieval and KV store updates

    Returns:
        dict: {"content": "...", "usage": {...}}

    Raises:
        AIProviderError: If the API call fails
    """
    model = config.get("ai_model", "")
    max_tokens = max(1, int(config.get("ai_max_tokens", "4096")))
    temperature = float(config.get("ai_temperature", "0.3"))

    if not model:
        raise AIProviderError("AI model must be configured for splunk_hosted provider")

    # Get dynamic credentials and URL
    base_url = _get_slim_base_url(service)
    scs_token = _get_scs_token(service)

    # Resolve model_name → model_id if needed (reuses base_url/scs_token,
    # fail-safe).  The ``service`` handed to us here must already be
    # system-level (admin) because SCS token retrieval reads from
    # ``storage_passwords``, which requires ``list_storage_passwords``.  We
    # therefore forward it as ``system_service`` to engage the KV Store
    # resolution cache — eliminating the per-LLM-call /chat/models
    # round-trip flagged by Cursor Bugbot.  If the caller ever passes a
    # non-privileged service, the cache layer fails silently and
    # resolution still succeeds via the live SLIM call.
    model = _resolve_splunk_hosted_model(
        model, base_url, scs_token, system_service=service
    )

    url = f"{base_url}/chat/completions"
    payload = {
        "model_id": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        # See _call_splunk_hosted() for the rationale behind extra_headers.
        "extra_headers": {"additionalProp1": "string"},
    }

    # NOTE: urllib normalises header names to title case in do_open(), which
    # breaks SLIM's case-sensitive "request_id" header. Use requests (same
    # library the Splunk AI/ML Toolkit uses) to preserve the exact header
    # name on the wire.
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {scs_token}",
        "User-Agent": _USER_AGENT,
        "request_id": _generate_slim_request_id(),
    }

    accumulated_content = ""
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    first_token_logged = False
    last_heartbeat = time.time()

    resp = None
    _streaming_start = time.time()
    try:
        resp = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=timeout,
            stream=True,
        )
        if resp.status_code >= 400:
            error_body = ""
            try:
                error_body = resp.text
            except Exception:
                pass
            raise AIProviderError(
                f"SLIM API returned HTTP {resp.status_code}: {error_body}"
            )

        # Force UTF-8 for SSE decoding. The `requests` library follows
        # RFC 2616 and assigns ISO-8859-1 to text/* responses that lack an
        # explicit charset parameter (SLIM's text/event-stream typically
        # does). Without this, iter_lines(decode_unicode=True) would garble
        # any non-ASCII characters (accents, emoji, CJK) in the streamed
        # LLM output. SSE itself mandates UTF-8.
        resp.encoding = "utf-8"

        raw_lines = []
        for raw_line in resp.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip()
            if not line:
                continue
            raw_lines.append(line)
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content_piece = delta.get("content", "")
                    if content_piece:
                        if not first_token_logged:
                            first_token_logged = True
                            ttft = round(time.time() - _streaming_start, 2)
                            logger.info(
                                f'function=_call_splunk_hosted_streaming, action="first_token", '
                                f'job_id="{job_id}", model="{model}", '
                                f'time_to_first_token_sec={ttft}'
                            )
                        now = time.time()
                        if now - last_heartbeat >= 30:
                            logger.info(
                                f'function=_call_splunk_hosted_streaming, action="streaming_progress", '
                                f'job_id="{job_id}", model="{model}", '
                                f'elapsed_sec={round(now - _streaming_start, 2)}, '
                                f'chars_received={len(accumulated_content)}'
                            )
                            last_heartbeat = now
                        accumulated_content += content_piece
                        _update_job(
                            service, job_id,
                            content=accumulated_content, last_activity=time.time(),
                        )
                    # Capture usage from streaming chunks if provided
                    if "usage" in chunk and chunk["usage"]:
                        u = chunk["usage"]
                        usage = {
                            "prompt_tokens": u.get("prompt_tokens", 0),
                            "completion_tokens": u.get("completion_tokens", 0),
                            "total_tokens": u.get("total_tokens", 0),
                        }
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue
        resp.close()
        resp = None

        # Fallback for non-SSE responses (SLIM API may return a single JSON
        # response if it does not support streaming)
        if not accumulated_content and raw_lines:
            try:
                # Strip SSE prefixes (e.g. "data: {...}") before joining
                stripped = []
                for rl in raw_lines:
                    if rl.startswith("data: "):
                        stripped.append(rl[6:])
                    elif rl.startswith("event:") or rl.startswith("id:") or rl.startswith("retry:"):
                        continue  # skip other SSE fields
                    else:
                        stripped.append(rl)
                full_body = "\n".join(stripped)
                response_json = json.loads(full_body)
                content = response_json["choices"][0]["message"]["content"]
                if content:
                    accumulated_content = content
                    _update_job(
                        service, job_id,
                        content=accumulated_content, last_activity=time.time(),
                    )
                    if "usage" in response_json and response_json["usage"]:
                        u = response_json["usage"]
                        usage = {
                            "prompt_tokens": u.get("prompt_tokens", 0),
                            "completion_tokens": u.get("completion_tokens", 0),
                            "total_tokens": u.get("total_tokens", 0),
                        }
                    logger.info(
                        f'function=_call_splunk_hosted_streaming, action="non_sse_fallback", '
                        f'job_id="{job_id}", model="{model}", '
                        f'content_length={len(accumulated_content)}'
                    )
            except (json.JSONDecodeError, KeyError, IndexError):
                pass

    except AIProviderError:
        raise
    except requests.Timeout:
        # Initial connect/TTFB timeout (before the response body starts).
        elapsed_so_far = round(time.time() - _streaming_start, 2)
        logger.error(
            f'function=_call_splunk_hosted_streaming, action="timeout", '
            f'job_id="{job_id}", model="{model}", '
            f'timeout_sec={timeout}, elapsed_sec={elapsed_so_far}, '
            f'chars_received_before_timeout={len(accumulated_content)}'
        )
        raise AIProviderError(f"SLIM API request timed out after {timeout}s")
    except (requests.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
        # The `requests` library has a long-standing quirk (see
        # psf/requests#5430) where read timeouts that occur *mid-stream*
        # inside iter_lines/iter_content surface as ConnectionError
        # (wrapping a urllib3.exceptions.ReadTimeoutError) or as
        # ChunkedEncodingError, NOT as requests.Timeout. Detect the
        # wrapped ReadTimeoutError and report it as a timeout so the
        # logs remain accurate and callers see a timeout (not a
        # connection failure) error message.
        try:
            from urllib3.exceptions import ReadTimeoutError as _U3ReadTimeoutError
        except Exception:
            _U3ReadTimeoutError = None

        wrapped = e.args[0] if e.args else None
        is_read_timeout = (
            (_U3ReadTimeoutError is not None
                and isinstance(wrapped, _U3ReadTimeoutError))
            or "ReadTimeoutError" in str(e)
            or "timed out" in str(e).lower()
        )
        if is_read_timeout:
            elapsed_so_far = round(time.time() - _streaming_start, 2)
            logger.error(
                f'function=_call_splunk_hosted_streaming, action="timeout", '
                f'job_id="{job_id}", model="{model}", '
                f'timeout_sec={timeout}, elapsed_sec={elapsed_so_far}, '
                f'chars_received_before_timeout={len(accumulated_content)}, '
                f'detected_via="wrapped_{type(e).__name__}"'
            )
            raise AIProviderError(
                f"SLIM API request timed out after {timeout}s"
            )
        raise AIProviderError(
            f"Failed to connect to SLIM API at {base_url}: {str(e)}"
        )
    except requests.RequestException as e:
        raise AIProviderError(
            f"Failed to connect to SLIM API at {base_url}: {str(e)}"
        )
    finally:
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass

    # Ensure total_tokens is always the sum of prompt + completion
    usage["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

    return {"content": accumulated_content, "usage": usage}


# ---- Async chat orchestrator ----


def _try_parse_concierge_invocation(content):
    """Detect and extract the inner ``concierge_invocation`` dict from a
    chat LLM response.

    Mirrors the frontend ``parseConciergeResponse`` logic in
    ``splunkui/.../utils/conciergeBridge.ts``:

      1. Find the LAST ``` ```json `` opening — handles smaller models
         (Haiku, Mistral, Ollama) that append prose after the JSON block.
      2. JSON-parse the fenced contents.
      3. Disambiguate from advisor invocations (reject if
         ``advisor_invocation`` wrapper or ``advisor`` enum at the top).
      4. Validate concierge shape: ``actions`` array AND at least one
         of ``summary`` / ``intent_summary`` / ``suggested_reason``
         strings.

    Returns the inner contract dict on success (already unwrapped from
    any ``concierge_invocation`` outer wrapper), or ``None`` on any
    failure mode.  Silent by design — every failure path returns None
    so the caller's audit emission is best-effort and the chat response
    is never affected.

    Exists so the chat handler can emit a
    ``trackme:ai_agent:concierge_advisor:propose`` audit event on Path 1
    (chat-direct inline emission, where the Concierge agent runtime
    doesn't run and therefore doesn't emit the event itself).  Without
    this, the AI Advisor audit dashboard had zero visibility into
    Path 1 Concierge activity — the common path for the feature.
    See ``ai-context/ai-advisors/concierge-advisor.md`` § Audit
    emission for the cross-path coverage rationale.
    """
    if not content or not isinstance(content, str):
        return None
    # Anchor on the LAST ```json opening — matches the frontend parser's
    # rule for handling smaller models that append explanatory prose
    # after the JSON block.
    fence_open = "```json"
    open_idx = content.rfind(fence_open)
    if open_idx < 0:
        return None
    close_idx = content.find("```", open_idx + len(fence_open))
    if close_idx < 0:
        return None
    json_raw = content[open_idx + len(fence_open):close_idx].strip()
    try:
        parsed = json.loads(json_raw)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    # ``concierge_invocation`` wrapper key OR bare-form (actions at top
    # level).  Unwrap if wrapped.
    wrapped = parsed.get("concierge_invocation")
    inner = wrapped if isinstance(wrapped, dict) else parsed
    # Disambiguate from advisor invocation — the shapes are mutually
    # exclusive on a well-formed payload, so a contract carrying any
    # advisor-shaped key isn't a Concierge contract.
    if "advisor_invocation" in parsed or "advisor" in inner:
        return None
    # Concierge shape: ``actions`` array AND at least one of three
    # text fields (canonical is ``summary``; small models occasionally
    # produce ``intent_summary`` / ``suggested_reason`` instead — the
    # frontend parser accepts all three, mirror that here).
    actions = inner.get("actions")
    has_text = (
        isinstance(inner.get("summary"), str)
        or isinstance(inner.get("intent_summary"), str)
        or isinstance(inner.get("suggested_reason"), str)
    )
    if not (isinstance(actions, list) and has_text):
        return None
    return inner


def start_chat_request_async(
    system_service,
    user_service,
    request_info,
    tenant_id,
    object_category,
    object_value,
    messages,
    provider_name=None,
    context_type="entity",
):
    """
    Start an asynchronous AI chat request.

    Returns immediately with a job_id. The LLM call runs in a background thread
    using streaming to collect tokens incrementally.

    Poll get_job_status(job_id) to get results.

    Args:
        system_service: Splunk service connection with system token (for AI config,
                        API keys, and job KV store writes in the background thread)
        user_service: Splunk service connection with user session token (for entity
                      data reads — enforces RBAC on tenant KV stores)
        request_info: REST request info object
        tenant_id: Tenant identifier (required for entity context, ignored for vtenants)
        object_category: Entity type (required for entity context, ignored for vtenants)
        object_value: Entity identifier (required for entity context, ignored for vtenants)
        messages: List of conversation messages [{"role": ..., "content": ...}]
        provider_name: Optional provider stanza name. If None, uses first configured.
        context_type: Context type - "entity" for entity-level AI, "vtenants" for
                      Virtual Tenants management AI. Defaults to "entity".

    Returns:
        dict: {"job_id": "...", "status": "running"}

    Raises:
        AINotConfiguredError: If AI is not configured
    """
    # 1. Get AI configuration (reads from trackme_ai_provider.conf)
    config = get_ai_config(system_service, provider_name=provider_name)
    if not config:
        raise AINotConfiguredError(
            "AI assistant is not configured. "
            "An administrator must configure an AI provider in the TrackMe configuration page."
        )

    # 2. Get API key from storage_passwords (may be None for Ollama)
    api_key = get_ai_api_key(system_service, config["provider_name"])

    # 3. Build context based on context_type
    # ``object_id_for_audit`` captures the entity ``_key`` (SHA256 hash)
    # for entity-context chats; surfaced via closure scope to
    # ``_emit_concierge_proposal_audit`` below so the Concierge audit
    # event carries the same ``object_id`` field the specialist
    # advisors emit on Path 2.  Only populated in the entity branch
    # (where ``build_entity_context`` resolves an entity record); other
    # context types (vtenants, tenant_home as a tenant-wide view,
    # feature pages) leave it as "" — no single entity is bound to
    # those chats, so the dashboard's Object ID column stays empty by
    # design.
    object_id_for_audit = ""
    if context_type == "vtenants":
        # Virtual Tenants context — no entity needed
        vtenants_context = build_vtenants_context(system_service, request_info)
        entity_context_loaded = vtenants_context is not None

        # 4. Build system prompt for Virtual Tenants
        if vtenants_context:
            system_prompt = build_vtenants_system_prompt(
                vtenants_context, custom_prompt=config.get("ai_custom_prompt")
            )
        else:
            system_prompt = (
                "You are an AI assistant integrated into TrackMe, a Splunk application "
                "for data and metrics monitoring. The Virtual Tenants context could not be loaded. "
                "Help the user with general TrackMe Virtual Tenants questions."
            )
            if config.get("ai_custom_prompt"):
                system_prompt += f"\n\n{config.get('ai_custom_prompt')}"
    elif context_type == "tenant_home":
        # Tenant Home context — scoped to a single tenant
        tenant_home_context = build_tenant_home_context(system_service, request_info, tenant_id)
        entity_context_loaded = tenant_home_context is not None

        # 4. Build system prompt for Tenant Home
        if tenant_home_context:
            system_prompt = build_tenant_home_system_prompt(
                tenant_home_context, custom_prompt=config.get("ai_custom_prompt")
            )
        else:
            system_prompt = (
                "You are an AI assistant integrated into TrackMe, a Splunk application "
                "for data and metrics monitoring. The Tenant Home context could not be loaded. "
                "Help the user with general TrackMe questions."
            )
            if config.get("ai_custom_prompt"):
                system_prompt += f"\n\n{config.get('ai_custom_prompt')}"
    elif context_type == "fqm_dictionary_wizard":
        # Wizard-time chat surface for the FQM tracker creation wizard.
        # Goal: produce action-contracts for the FQM advisor's
        # ``dictionary_generate`` mode when the user asks for a starter
        # dictionary. The wizard frontend supplies all per-tracker state
        # (sampled fields, root search, breakby) directly to the advisor
        # launch body — the chat doesn't need to see it. See
        # ``trackme_libs_describe_fqm_dictionary_wizard.py`` for the full
        # design rationale.
        wizard_context = build_fqm_dictionary_wizard_context(
            system_service, request_info, tenant_id
        )
        entity_context_loaded = wizard_context is not None
        if wizard_context:
            system_prompt = build_fqm_dictionary_wizard_system_prompt(
                wizard_context, custom_prompt=config.get("ai_custom_prompt")
            )
        else:
            system_prompt = (
                "You are an AI assistant integrated into TrackMe, a Splunk application "
                "for data and metrics monitoring. You are mounted in the FQM tracker "
                "creation wizard, but the wizard context could not be loaded. Help the "
                "user with general FQM dictionary questions; if they ask to generate a "
                "dictionary, propose the FQM Advisor in ``mode=dictionary_generate`` and "
                "end your response with a fenced ```json block carrying the "
                "advisor_invocation contract."
            )
            if config.get("ai_custom_prompt"):
                system_prompt += f"\n\n{config.get('ai_custom_prompt')}"
    elif context_type == "rest_api_reference":
        ctx = build_rest_api_reference_context(system_service, request_info)
        entity_context_loaded = ctx is not None
        if ctx:
            system_prompt = build_rest_api_reference_system_prompt(
                ctx, custom_prompt=config.get("ai_custom_prompt")
            )
        else:
            system_prompt = (
                "You are an AI assistant integrated into TrackMe, a Splunk application "
                "for data and metrics monitoring. The REST API Reference context could not be loaded. "
                "Help the user with general TrackMe REST API questions."
            )
            if config.get("ai_custom_prompt"):
                system_prompt += f"\n\n{config.get('ai_custom_prompt')}"
    elif context_type == "backup_restore":
        ctx = build_backup_restore_context(system_service, request_info)
        entity_context_loaded = ctx is not None
        if ctx:
            system_prompt = build_backup_restore_system_prompt(
                ctx, custom_prompt=config.get("ai_custom_prompt")
            )
        else:
            system_prompt = (
                "You are an AI assistant integrated into TrackMe, a Splunk application "
                "for data and metrics monitoring. The Backup & Restore context could not be loaded. "
                "Help the user with general TrackMe backup questions."
            )
            if config.get("ai_custom_prompt"):
                system_prompt += f"\n\n{config.get('ai_custom_prompt')}"
    elif context_type == "maintenance_mode":
        ctx = build_maintenance_mode_context(system_service, request_info)
        entity_context_loaded = ctx is not None
        if ctx:
            system_prompt = build_maintenance_mode_system_prompt(
                ctx, custom_prompt=config.get("ai_custom_prompt")
            )
        else:
            system_prompt = (
                "You are an AI assistant integrated into TrackMe, a Splunk application "
                "for data and metrics monitoring. The Maintenance Mode context could not be loaded. "
                "Help the user with general TrackMe maintenance questions."
            )
            if config.get("ai_custom_prompt"):
                system_prompt += f"\n\n{config.get('ai_custom_prompt')}"
    elif context_type == "maintenance_kdb":
        ctx = build_maintenance_kdb_context(system_service, request_info)
        entity_context_loaded = ctx is not None
        if ctx:
            system_prompt = build_maintenance_kdb_system_prompt(
                ctx, custom_prompt=config.get("ai_custom_prompt")
            )
        else:
            system_prompt = (
                "You are an AI assistant integrated into TrackMe, a Splunk application "
                "for data and metrics monitoring. The Maintenance KDB context could not be loaded. "
                "Help the user with general TrackMe maintenance questions."
            )
            if config.get("ai_custom_prompt"):
                system_prompt += f"\n\n{config.get('ai_custom_prompt')}"
    elif context_type == "bank_holidays":
        ctx = build_bank_holidays_context(system_service, request_info)
        entity_context_loaded = ctx is not None
        if ctx:
            system_prompt = build_bank_holidays_system_prompt(
                ctx, custom_prompt=config.get("ai_custom_prompt")
            )
        else:
            system_prompt = (
                "You are an AI assistant integrated into TrackMe, a Splunk application "
                "for data and metrics monitoring. The Bank Holidays context could not be loaded. "
                "Help the user with general TrackMe bank holidays questions."
            )
            if config.get("ai_custom_prompt"):
                system_prompt += f"\n\n{config.get('ai_custom_prompt')}"
    elif context_type == "license":
        ctx = build_license_context(system_service, request_info)
        entity_context_loaded = ctx is not None
        if ctx:
            system_prompt = build_license_system_prompt(
                ctx, custom_prompt=config.get("ai_custom_prompt")
            )
        else:
            system_prompt = (
                "You are an AI assistant integrated into TrackMe, a Splunk application "
                "for data and metrics monitoring. The License context could not be loaded. "
                "Help the user with general TrackMe license questions."
            )
            if config.get("ai_custom_prompt"):
                system_prompt += f"\n\n{config.get('ai_custom_prompt')}"
    else:
        # Entity context (existing behavior)
        # Read anonymization settings
        anonymize_entities = get_anonymize_setting(system_service)
        anonymize_indexes = get_anonymize_index_setting(system_service)

        entity_context = build_entity_context(
            user_service, request_info, tenant_id, object_category, object_value,
            anonymize=anonymize_entities, anonymize_indexes=anonymize_indexes,
        )
        entity_context_loaded = entity_context is not None

        # Capture the resolved entity ``_key`` for downstream audit
        # emission.  The ``trackme:ai_agent:concierge_advisor:propose``
        # event surfaced by ``_emit_concierge_proposal_audit`` reads
        # this via closure so the AI Advisor audit dashboard's
        # Object ID column populates uniformly with the specialist
        # advisors (which emit ``object_id`` from their KV record).
        # ``build_entity_context`` does NOT return the raw KV record —
        # it delegates to ``build_entity_description`` which returns a
        # structured description dict with top-level keys
        # ``meta`` / ``identity`` / ``entity_info`` / etc.  The
        # entity's ``_key`` lives at ``identity.object_id`` (set by
        # ``_build_identity`` from ``kvrecord["_key"]``).  Bugbot
        # caught the wrong key path on the original commit — without
        # this lookup ``object_id_for_audit`` would always be empty
        # and the audit event would silently miss the field.  Defence
        # in depth on both ``.get()`` calls so a malformed response
        # can't raise — audit enrichment must never break the chat
        # job.
        if entity_context is not None:
            _identity = entity_context.get("identity") or {}
            object_id_for_audit = _identity.get("object_id", "") or ""

        # 4. Build system prompt for entity
        if entity_context:
            system_prompt = build_system_prompt(
                entity_context, custom_prompt=config.get("ai_custom_prompt"),
                anonymize=anonymize_entities, anonymize_indexes=anonymize_indexes,
            )
        else:
            system_prompt = (
                "You are an AI assistant integrated into TrackMe, a Splunk application "
                "for data and metrics monitoring. The entity context could not be loaded. "
                "Help the user with general TrackMe questions."
            )
            if config.get("ai_custom_prompt"):
                system_prompt += f"\n\n{config.get('ai_custom_prompt')}"

    # 5. Build full message list
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    # 6. Enforce concurrency limit (configurable in General > AI settings)
    max_concurrent = _MAX_CONCURRENT_CHATS_DEFAULT
    try:
        for stanza in system_service.confs["trackme_settings"]:
            if stanza.name == "trackme_general":
                max_concurrent = int(
                    stanza.content.get("ai_max_concurrent_chats", str(_MAX_CONCURRENT_CHATS_DEFAULT))
                )
                break
    except Exception:
        pass
    # Clamp to minimum 1 so a misconfigured "0" doesn't disable all chats
    max_concurrent = max(1, max_concurrent)

    global _active_chats
    with _active_chats_lock:
        if _active_chats >= max_concurrent:
            raise AIBusyError(
                f"The AI assistant is at maximum capacity ({max_concurrent} concurrent requests). "
                "Please try again in a moment."
            )
        _active_chats += 1

    # 7. Create job and start background thread
    # Wrapped in try/except so the concurrency slot is released if job creation fails
    try:
        timeout = max(1, int(config.get("ai_request_timeout", "600")))
        provider = config.get("ai_provider", "openai")

        job_id = _create_job(
            system_service,
            timeout=timeout,
            entity_context_loaded=entity_context_loaded,
        )

        # Audit-dashboard captures.  Resolved here in the request thread
        # because ``request_info`` is not safe to read from the worker
        # (Splunk closes the REST request once the handler returns).
        # ``server_servername`` mirrors the ``host`` field used by the
        # AI Advisor's indexed events (see ``_index_agent_event`` in
        # trackme_libs_ai_agents.py).
        request_user = getattr(request_info, "user", None) or None
        server_name = getattr(request_info, "server_servername", None) or None
        # Stash the splunkd URI / token from the request thread — the
        # background worker needs them to resolve the tenant summary
        # index, but ``trackme_idx_for_tenant`` won't accept the
        # service object directly.
        splunkd_uri_for_audit = (
            f"{system_service.scheme}://{system_service.host}:{system_service.port}"
        )
        session_key_for_audit = getattr(system_service, "token", None) or ""

        logger.info(
            f'function=start_chat_request_async, action="request_started", '
            f'job_id="{job_id}", context_type="{context_type}", '
            f'tenant_id="{tenant_id}", '
            f'object_category="{object_category}", object="{object_value}", '
            f'provider_name="{config.get("provider_name")}", '
            f'provider="{provider}", model="{config.get("ai_model")}", '
            f'base_url="{config.get("ai_base_url")}", '
            f'timeout_sec={timeout}, entity_context_loaded={entity_context_loaded}'
        )

        def _emit_audit_event(status, *, usage=None, error=None, duration_ms=None):
            """Emit one ``trackme:ai_assistant:chat`` audit event.

            Best-effort wrapper — ``index_assistant_event`` already
            swallows its own exceptions, but we double-wrap so an
            unexpected error here can never break the chat job.
            """
            try:
                # ``tenant_id`` may legitimately be ``None`` for non-entity
                # contexts (vtenants, rest_api_reference, etc.).  Persist
                # those as the literal string ``"system"`` so the dashboard
                # has a stable bucket to ``stats by tenant_id`` against and
                # the index resolver gets a value it can fall back from.
                effective_tenant = tenant_id or "system"
                event = {
                    "kind": "chat",
                    "job_id": job_id,
                    "tenant_id": effective_tenant,
                    "context_type": context_type,
                    "object_category": object_category or "",
                    "object": object_value or "",
                    "provider_name": config.get("provider_name") or "",
                    "provider": provider or "",
                    "model": config.get("ai_model") or "",
                    "status": status,
                    "entity_context_loaded": (
                        "true" if entity_context_loaded
                        else "false" if entity_context_loaded is False
                        else ""
                    ),
                }
                # ``is not None`` rather than truthy so a falsy-string
                # error (empty message — uncommon but possible if a
                # provider returns an exception with no body) still
                # makes it onto the audit event.  Matches the pattern
                # used in ``_emit_ai_status_report_audit`` so the two
                # closures stay symmetric.
                if error is not None:
                    event["error"] = str(error)[:2000]
                enrich_assistant_event_for_audit(
                    event,
                    user=request_user,
                    automated=False,
                    duration_ms=duration_ms,
                    usage=usage,
                )
                index_assistant_event(
                    system_service,
                    effective_tenant,
                    "trackme:ai_assistant:chat",
                    event,
                    session_key=session_key_for_audit,
                    splunkd_uri=splunkd_uri_for_audit,
                    server_name=server_name,
                )
            except Exception as ex:
                logger.warning(
                    f'function=start_chat_request_async, action="audit_emit_failed", '
                    f'job_id="{job_id}", exception="{str(ex)}"'
                )

        def _emit_concierge_proposal_audit(content, duration_ms):
            """If the LLM response contains an inline ``concierge_invocation``
            JSON block, emit a ``trackme:ai_agent:concierge_advisor:propose``
            audit event mirroring the one the Concierge agent runtime
            emits on Path 2 (agent-launched).

            Closes the audit-dashboard coverage gap for Path 1
            (chat-direct) Concierge activity.  Without this emission,
            the AI Advisor audit dashboard saw zero Concierge events
            for the common path — the chat assistant inline proposal
            flow that produces the bulk of Concierge usage.

            Best-effort: parser failures (no fenced block, malformed
            JSON, advisor-shape disambiguation), validation failures,
            and indexing failures are all silent — audit emission
            must NEVER affect the chat response or the chat job's
            terminal state.
            """
            try:
                invocation = _try_parse_concierge_invocation(content)
                if invocation is None:
                    return
                effective_tenant = tenant_id or "system"
                # Map chat ``context_type`` to the Concierge ``surface``
                # enum.  ``entity`` and ``tenant_home`` both scope to a
                # single entity/tenant in the consent card's session
                # injection; everything else (feature variants like
                # ``rest_api_reference`` / ``backup_restore`` etc.) is
                # ``global`` — matches the Concierge runtime convention.
                surface_map = {
                    "entity": "entity",
                    "tenant_home": "entity",
                    "vtenants": "vtenants",
                }
                surface = surface_map.get(context_type, "global")
                event = {
                    "job_id": job_id,
                    "tenant_id": effective_tenant,
                    "surface": surface,
                    "advisor": "concierge",
                    "mode": "propose",
                    "status": "success",
                    "provider_name": config.get("provider_name") or "default",
                    "model": config.get("ai_model") or "unknown",
                    # New ``launched_by`` value distinguishing Path 1
                    # (chat response inline contract) from Path 2
                    # (agent-launched).  Existing values used by Path 2:
                    # ``standalone`` (modal), ``ai_assistant`` (chat-
                    # launched agent), ``automated`` (batch).  Path 1
                    # gets its own value so dashboard SPL can split
                    # cleanly.
                    "launched_by": "chat_direct",
                    # ``chat_session_id`` isn't currently threaded into
                    # ``start_chat_request_async`` — the frontend doesn't
                    # pass it on chat POSTs.  Threading-through is a
                    # follow-up; for now the event correlates to the
                    # chat via ``job_id`` (same id as the matching
                    # ``trackme:ai_assistant:chat`` event).
                    "chat_session_id": "",
                    "user_intent": (
                        invocation.get("summary")
                        or invocation.get("intent_summary")
                        or invocation.get("suggested_reason")
                        or ""
                    )[:500],
                    "token_count": 0,
                    "steps_taken": 0,
                    "result": invocation,
                }
                # Entity-surface chats carry a resolved entity in the
                # chat session state.  When present, mirror the field
                # set the specialist advisors emit on Path 2 (see
                # ``_index_agent_event`` in
                # ``trackme_libs_ai_feed_lifecycle.py`` and siblings)
                # so the AI Advisor audit dashboard's Component
                # / Object / Object ID columns populate uniformly
                # across the advisor family.  Without this enrichment
                # Concierge events show empty cells in those columns
                # even when the chat is mounted on an entity page and
                # the proposal acts on that entity — the dashboard SPL
                # selects ``component`` / ``object`` / ``object_id``
                # as top-level fields (see
                # ``splunkui/packages/audit-ai-advisor/src/AuditAiAdvisor.tsx``
                # § ``runs``).  When the chat is mounted on a
                # non-entity surface (vtenants, tenant_home as a
                # tenant-wide view, feature pages), ``object_category``
                # and ``object_value`` are empty and all four fields
                # are skipped by design — the proposal isn't bound to
                # a single entity.
                #
                # Path 2 (agent-launched Concierge) doesn't currently
                # carry entity binding through its launch contract —
                # it's a generalist over the full catalog — so this
                # enrichment lives on Path 1 only.  Extending Path 2's
                # launch body to accept optional entity context is a
                # follow-up if/when the chat assistant starts firing
                # Path 2 from entity surfaces.
                if object_category and object_value:
                    _type_config = ENTITY_TYPE_MAP.get(object_category)
                    if _type_config:
                        event["component"] = _type_config["short"]
                    event["object_category"] = object_category
                    event["object"] = object_value
                    if object_id_for_audit:
                        event["object_id"] = object_id_for_audit
                # Deliberately DO NOT populate ``actions_taken_count``
                # or ``recommendations_count`` here.  Reasoning:
                #
                # * ``actions_taken_count`` on Path 2 (set by
                #   ``enrich_agent_event_for_audit`` from
                #   ``result.actions_taken``) counts agent SDK tool
                #   calls (discover_endpoints, read_via_endpoint,
                #   propose_action calls).  On Path 1 no agent ran, so
                #   the correct value is 0 — emitting ``len(actions)``
                #   here would conflate proposed REST API actions with
                #   agent tool calls, producing misleading stats on any
                #   dashboard panel that aggregates by this field
                #   across both paths.  Bugbot caught this on the
                #   original commit.
                # * ``recommendations_count`` is set on specialist
                #   advisor events (ML / Feed Lifecycle / etc., which
                #   carry ``result.recommendations``).  Concierge
                #   events on Path 2 don't have ``recommendations`` at
                #   all (the ConciergeProposalResult schema only has
                #   ``proposed_actions`` and ``actions_taken``), so
                #   setting ``recommendations_count`` here would
                #   invent a field that exists only on Path 1 events.
                #
                # The count of proposed actions is still recoverable
                # by SPL: ``spath result | mvcount(spath(result, "actions{}"))``
                # — the full ``result`` payload is on the event.  If
                # the audit dashboard later needs a top-level count
                # field, the correct field name is
                # ``proposed_actions_count`` (semantically distinct
                # from the Path 2 SDK tool-call count), wired
                # symmetrically on both paths.
                # Reuse ``enrich_assistant_event_for_audit`` for ``user``
                # / ``automated`` / ``duration_ms`` — same shape as the
                # ``trackme:ai_assistant:chat`` event so audit-dashboard
                # SPL on those fields works uniformly.
                enrich_assistant_event_for_audit(
                    event,
                    user=request_user,
                    automated=False,
                    duration_ms=duration_ms,
                )
                index_assistant_event(
                    system_service,
                    effective_tenant,
                    "trackme:ai_agent:concierge_advisor:propose",
                    event,
                    session_key=session_key_for_audit,
                    splunkd_uri=splunkd_uri_for_audit,
                    server_name=server_name,
                )
            except Exception as ex:
                logger.warning(
                    f'function=start_chat_request_async, '
                    f'action="concierge_proposal_audit_emit_failed", '
                    f'job_id="{job_id}", exception="{str(ex)}"'
                )

        def _run_llm():
            start_time = time.time()
            try:
                if provider == "ollama":
                    result = _call_ollama_native_streaming(
                        config, api_key, full_messages, timeout, job_id, system_service
                    )
                elif provider == "anthropic":
                    result = _call_anthropic_streaming(
                        config, api_key, full_messages, timeout, job_id, system_service
                    )
                elif provider == "splunk_hosted":
                    result = _call_splunk_hosted_streaming(
                        config, full_messages, timeout, job_id, system_service
                    )
                else:
                    result = _call_openai_compatible_streaming(
                        config, api_key, full_messages, timeout, job_id, system_service
                    )
                elapsed = round(time.time() - start_time, 2)
                # Single read of the cancel state — reusing the same
                # value for both the ``_update_job`` decision and the
                # audit emit decision keeps the two consistent.  Two
                # independent reads would otherwise leave a window where
                # the KV record gets written but no audit event fires
                # (or vice-versa) if a cancel arrives between them.
                if _get_job_status_raw(system_service, job_id) == "cancelled":
                    return  # Do not overwrite cancelled state, do not emit audit
                _update_job(
                    system_service,
                    job_id,
                    status="complete",
                    content=result["content"],
                    usage=result["usage"],
                    last_activity=time.time(),
                )
                logger.info(
                    f'function=start_chat_request_async, tenant_id="{tenant_id}", '
                    f'object_category="{object_category}", object="{object_value}", '
                    f'model="{config.get("ai_model")}", elapsed_sec={elapsed}, '
                    f'prompt_tokens={result["usage"]["prompt_tokens"]}, '
                    f'completion_tokens={result["usage"]["completion_tokens"]}'
                )
                # Compute ``duration_ms`` ONCE up front and pass the
                # same value to both audit emitters.  ``_emit_audit_event``
                # performs Splunk index I/O via ``index_assistant_event``,
                # so a second ``time.time()`` call after it returns would
                # yield a systematically larger value — breaking the
                # promise that the Path 1 proposal event's ``duration_ms``
                # aligns with the matching chat event.  Bugbot caught
                # this on the original commit.
                duration_ms = int((time.time() - start_time) * 1000)
                _emit_audit_event(
                    "success",
                    usage=result.get("usage"),
                    duration_ms=duration_ms,
                )
                # Path 1 Concierge proposal audit — if the LLM response
                # included an inline ``concierge_invocation`` JSON block,
                # emit the parity sourcetype that the Concierge agent
                # runtime emits on Path 2 (agent-launched).  Closes the
                # audit-dashboard coverage gap that previously left
                # Path 1 Concierge activity invisible.  Best-effort
                # (never raises) — see the helper docstring.
                _emit_concierge_proposal_audit(
                    result.get("content"),
                    duration_ms=duration_ms,
                )
            except Exception as e:
                # Single read for the same consistency reason as the
                # success path above — both ``_update_job`` and the
                # audit emit are gated by one cancel-check value, so
                # they always agree about whether to fire.
                err_is_cancelled = (
                    _get_job_status_raw(system_service, job_id) == "cancelled"
                )
                if not err_is_cancelled:
                    _update_job(
                        system_service,
                        job_id,
                        status="error",
                        error=str(e),
                        last_activity=time.time(),
                    )
                logger.error(
                    f'function=start_chat_request_async, job_id="{job_id}", '
                    f'tenant_id="{tenant_id}", '
                    f'object_category="{object_category}", object="{object_value}", '
                    f'exception="{str(e)}"'
                )
                # Cancelled jobs are not failures — the user explicitly
                # walked away from the conversation.  Skip the audit
                # event so the dashboard's error rate isn't polluted
                # with user-driven cancels.
                if not err_is_cancelled:
                    _emit_audit_event(
                        "error",
                        error=e,
                        duration_ms=int((time.time() - start_time) * 1000),
                    )
            finally:
                _release_concurrency_slot(job_id)

        thread = threading.Thread(target=_run_llm, daemon=True)
        thread.start()
    except Exception:
        with _active_chats_lock:
            _active_chats -= 1
        raise

    return {"job_id": job_id, "status": "running"}

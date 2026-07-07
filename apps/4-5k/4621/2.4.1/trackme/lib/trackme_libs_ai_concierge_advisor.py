"""
TrackMe AI Agents — Concierge Advisor.

The **generalist** agent. Where the specialist advisors (ML, Feed
Lifecycle, FLX Threshold, FQM, Component Health) handle curated
remediation flows for specific surfaces, the Concierge handles the
long tail of user requests by grounding itself in the live TrackMe
REST API catalog.

Architectural property — preserved from the wizard bridge in PR
#1293: the agent is **read-only at the SDK level**. The MCP tool
allowlist contains only ``concierge_read``-tagged tools — no
mutation surface. The agent's only "write" capability is
``propose_action``, which emits a structured ``concierge_invocation``
contract for the consent card to render. The frontend fires the
actual REST call after the user clicks Confirm. Mutation is the
consent click — never autonomous execution.

Plan reference:
``ai-context/integrations/concierge-advisor-implementation-plan.md``.

Splunk Agent SDK imports (``splunklib.ai.*``) are deferred to function
scope — the SDK requires Python 3.13+ and raises ImportError on 3.9.
"""

import asyncio
import json
import logging
import os
import threading
import time

from typing import Any, Dict, List, Optional

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
)

# Named logger — shares the singleton configured by the parent
# REST handler's setup_logger() call (root logger redirect there means
# `logging.<level>(...)` here would bleed across handlers).
logger = logging.getLogger("trackme.rest.ai.concierge_advisor")


# ---------------------------------------------------------------------------
# Pydantic Output Schemas
# ---------------------------------------------------------------------------


# ``session_injected_fields`` is a fixed allowlist — the agent must
# never spell out a tenant_id / object_id / object / component value
# itself. Identifiers come from session state, the frontend resolves
# them at consent time. The allowlist is enumerated here so the
# Pydantic validator can reject any other field name in the agent's
# proposal output (defence in depth on top of the system prompt).
_VALID_SESSION_INJECTED_FIELDS = frozenset({
    "tenant_id",
    "object_id",
    "object",
    "component",
})

_VALID_DANGER_LEVELS = frozenset({
    "read",
    "write-low",
    "write-high",
    "destructive",
})

_VALID_HTTP_METHODS = frozenset({
    "get",
    "post",
    "delete",
    "put",
})


class ConciergeAction(BaseModel):
    """One proposed action in a Concierge invocation contract.

    The agent emits a list of these via ``propose_action``; the consent
    card renders them as individually-approvable rows. Multi-action
    contracts (e.g. "increase priority for 47 entities tagged X") are
    natural — the user sees the full list before confirming, the
    frontend fires sequentially with per-action results streaming back
    into the chat.

    Hard rule (mirrors the FQM bridge's PR #1293 lesson on identifier
    construction): identifiers come from session state, NEVER from
    LLM construction. The ``body_template`` carries the literal string
    ``"<session-injected>"`` for the protected fields; the
    ``session_injected_fields`` array names which body keys the
    frontend will replace at consent time. The Pydantic validator
    rejects any field name not in ``_VALID_SESSION_INJECTED_FIELDS``
    so a hallucinated session-injected field can't slip into a
    proposal.
    """

    endpoint_path: str = Field(
        description=(
            "Full REST path. MUST be a byte-for-byte copy of one of "
            "the catalog entries returned by ``discover_endpoints`` "
            "/ ``describe_endpoint``. Do NOT construct paths from "
            "training-data patterns; do NOT copy any path that "
            "appears as an example or illustration in a docstring "
            "(those are explanatory only — they are NOT in the "
            "catalog and BOTH the post-emission validator AND the "
            "consent-card client-side gate WILL flag them as "
            "hallucinations and drop / disable the proposal). The "
            "path must take the shape "
            "``/services/trackme/v2/<resource_group>/<endpoint_name>``; "
            "this shape hint is illustrative only — never emit a "
            "path that is not in the live catalog."
        )
    )
    method: str = Field(
        description=(
            "HTTP verb in lowercase: ``get`` / ``post`` / ``delete`` / "
            "``put``. MUST match the path's registered method in the "
            "catalog."
        )
    )
    body_template: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "JSON body to send. Use the literal string "
            "``\"<session-injected>\"`` (NOT the actual identifier) "
            "for ``tenant_id`` / ``object_id`` / ``object`` / "
            "``component`` — the frontend resolves these from chat "
            "session state at consent time. Other body fields carry "
            "their actual values (e.g. ``priority: \"critical\"``, "
            "``ack_period: 7200``)."
        ),
    )
    session_injected_fields: List[str] = Field(
        default_factory=list,
        description=(
            "Names of body fields whose values the frontend will "
            "replace at consent time. Allowed: ``tenant_id``, "
            "``object_id``, ``object``, ``component``. Other field "
            "names are rejected by the validator."
        ),
    )
    danger_level: str = Field(
        description=(
            "One of ``read`` / ``write-low`` / ``write-high`` / "
            "``destructive``. MUST match what ``describe_endpoint`` "
            "returned — do NOT downgrade a write action to make it "
            "appear safer than it is. The consent card surfaces this "
            "and ``destructive`` triggers per-action re-confirmation."
        )
    )
    rbac_required: str = Field(
        default="",
        description=(
            "Splunk capability the endpoint requires "
            "(``trackmeuseroperations`` / "
            "``trackmepoweroperations`` / "
            "``trackmeadminoperations``). MUST match what "
            "``describe_endpoint`` returned. Empty string when the "
            "endpoint has no capability gate."
        ),
    )
    rationale: str = Field(
        description=(
            "One short paragraph explaining why this endpoint matches "
            "the user's intent. The consent card surfaces this so the "
            "analyst can judge the proposal before approving."
        )
    )

    def model_post_init(self, __context: Any) -> None:
        """Enforce the structural rules at validation time."""
        # Method enum. Normalise to lowercase AFTER validation so the
        # serialised proposal (chat message JSON, audit-event payload,
        # consent-card body) carries a single canonical casing.
        # Without re-assigning, an LLM emitting ``method="POST"``
        # would pass validation (``self.method.lower() in _VALID...``)
        # but the uppercase value would persist in every downstream
        # consumer — chat bubble, consent card, audit trail. The
        # ``propose_action`` validator does its own ``.lower()`` so
        # backend dispatch works either way, but case-sensitive SPL
        # over the audit index (``where method="post"``) and the
        # frontend's contract-shape checks would silently miss
        # uppercase rows. Bugbot caught the missing normalisation on
        # commit 5e223874 (Medium severity).
        method_lower = self.method.lower()
        if method_lower not in _VALID_HTTP_METHODS:
            raise ValueError(
                f"method must be one of {sorted(_VALID_HTTP_METHODS)} "
                f"(got {self.method!r})"
            )
        self.method = method_lower
        # Danger-level enum.
        if self.danger_level not in _VALID_DANGER_LEVELS:
            raise ValueError(
                f"danger_level must be one of {sorted(_VALID_DANGER_LEVELS)} "
                f"(got {self.danger_level!r})"
            )
        # Session-injected fields must come from the allowlist.
        bad = [f for f in self.session_injected_fields if f not in _VALID_SESSION_INJECTED_FIELDS]
        if bad:
            raise ValueError(
                f"session_injected_fields contains disallowed names: {bad}. "
                f"Allowed: {sorted(_VALID_SESSION_INJECTED_FIELDS)}"
            )
        # Cross-field rule: ``session_injected_fields`` and
        # ``body_template`` must agree in BOTH directions. The earlier
        # implementation only checked one direction (every name in
        # ``session_injected_fields`` has the placeholder in
        # ``body_template``). The reverse direction (every body_template
        # key carrying the placeholder is listed in
        # ``session_injected_fields``) was not enforced — and an agent
        # that put ``"<session-injected>"`` into a body_template field
        # WITHOUT listing it under ``session_injected_fields`` would
        # silently ship the literal placeholder string to the backend
        # at consent time (the frontend resolves only the listed
        # fields). Bugbot caught this on commit a79bdb4a (Medium
        # severity).
        injected_set = set(self.session_injected_fields)
        for field_name in self.session_injected_fields:
            if field_name not in self.body_template:
                raise ValueError(
                    f"session_injected_fields lists {field_name!r} but "
                    f"body_template has no key for it"
                )
            if self.body_template[field_name] != "<session-injected>":
                raise ValueError(
                    f"body_template[{field_name!r}] must be the literal "
                    f"string '<session-injected>' (got "
                    f"{self.body_template[field_name]!r}). The agent "
                    f"must NEVER spell out an identifier value — that "
                    f"comes from session state at consent time."
                )
        # Reverse: any body_template key carrying the placeholder must
        # be listed in session_injected_fields.
        for body_key, body_value in self.body_template.items():
            if body_value == "<session-injected>" and body_key not in injected_set:
                raise ValueError(
                    f"body_template[{body_key!r}] is the placeholder "
                    f"'<session-injected>' but {body_key!r} is not "
                    f"listed in session_injected_fields. Either add "
                    f"{body_key!r} to session_injected_fields (and pick "
                    f"a name from the allowlist {sorted(_VALID_SESSION_INJECTED_FIELDS)}), "
                    f"or replace the placeholder with the actual value. "
                    f"Without this both-directions check, the literal "
                    f"string '<session-injected>' would be shipped to "
                    f"the backend at consent time."
                )


class ConciergeProposalResult(BaseModel):
    """Structured agent output — the full Concierge proposal.

    The agent emits this object as its final structured output. The
    frontend embeds it in the chat message's ``concierge_invocation``
    contract, which the consent card renders as one approvable row per
    action (with the resolved request body shown BEFORE firing).

    A run that produces no actions (the user asked a general question
    and the agent answered without proposing anything) carries an
    empty ``actions`` list — the consent card simply doesn't render.
    The ``summary`` and ``reasoning_trace`` are still useful for the
    chat bubble.
    """

    summary: str = Field(
        description=(
            "1-3 sentence overview of what the agent investigated and "
            "what it's proposing. Shown above the consent-card action "
            "list (or as the chat-message body when no actions are "
            "proposed)."
        )
    )
    intent_summary: str = Field(
        default="",
        description=(
            "Restatement of the user's intent in the agent's own "
            "words. Empty when the agent didn't manage to recover a "
            "clear intent (e.g. ambiguous request that needs follow-"
            "up)."
        ),
    )
    actions: List[ConciergeAction] = Field(
        default_factory=list,
        description=(
            "Proposed actions. May be empty (the agent answered a "
            "question without proposing). Multi-action contracts "
            "are natural for batch operations — the consent card "
            "renders one row per action, all approved together."
        ),
    )
    consent_required: bool = Field(
        default=True,
        description=(
            "MUST always be ``true``. The frontend rejects any "
            "Concierge contract without it. There is no autonomous-"
            "execution path. The schema default reflects the only "
            "valid value, but the model validator below enforces it "
            "explicitly."
        ),
    )
    suggested_reason: str = Field(
        default="",
        description=(
            "Short overall summary shown above the per-action "
            "breakdown on the consent card. Distinct from "
            "``summary`` (which is the agent's narrative) — this "
            "is the consent-card heading, kept short."
        ),
    )
    actions_taken: List[AgentAction] = Field(
        default_factory=list,
        description=(
            "Tools the agent invoked during analysis. Populated by "
            "the agent SDK's tool-trace middleware. The Concierge "
            "agent has no write tools, so every entry here is a "
            "discovery / read operation. Surfaced in the audit "
            "trail so operators can reconstruct what the agent "
            "looked at before proposing."
        ),
    )
    reasoning_trace: List[str] = Field(
        default_factory=list,
        description=(
            "Step-by-step reasoning log. One short bullet per "
            "decision point (\"matched intent against "
            "discover_endpoints with keywords X\", \"verified state "
            "via read_via_endpoint Y\", \"chose endpoint Z because "
            "...\"). Surfaced in the consent card's collapsible "
            "trace section so analysts can audit the agent's "
            "thinking."
        ),
    )

    def model_post_init(self, __context: Any) -> None:
        """Enforce the consent-required invariant + per-action caps."""
        if self.consent_required is not True:
            raise ValueError(
                "consent_required MUST be true on every Concierge "
                "proposal. There is no autonomous-execution path."
            )
        # Cap action count — the per-tenant config carries the hard
        # cap, this is a sanity bound the schema enforces regardless.
        # Anything over 200 is almost certainly a runaway and should
        # be rejected before the consent card has to render it.
        if len(self.actions) > 200:
            raise ValueError(
                f"Too many actions in one proposal ({len(self.actions)}). "
                f"Cap is 200; the per-tenant configuration "
                f"``ai_concierge_max_actions_per_proposal`` (default "
                f"10) sets the operational limit. Split larger batches "
                f"into separate proposals."
            )

    @classmethod
    def model_json_schema(cls, **kwargs):
        """Return a flat ``$ref``/``$defs``-free JSON Schema.

        Mirrors ``MLAdvisorResult`` / ``FqmAdvisorResult`` /
        ``FlxThresholdAdvisorResult`` / ``ComponentHealthAdvisorResult``
        / ``FeedLifecycleAdvisorResult``. Anthropic's structured-output
        compiler rejects schemas containing ``$ref`` / ``$defs`` with
        "Schema is too complex for compilation"; ``inline_schema_refs``
        walks the schema and inlines every reference so the compiler
        accepts it. Without this override, every Concierge run on an
        Anthropic provider (including Claude — the recommended model
        for the bridge per the action-contract knowledge block) would
        fail at agent setup time. Bugbot caught the missing override on
        commit 275a4b5a (High severity).
        """
        return inline_schema_refs(super().model_json_schema(**kwargs))


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

CONCIERGE_ADVISOR_SYSTEM_PROMPT = """You are TrackMe's **Concierge Advisor** — the generalist AI agent
invoked from the AI Assistant when the user describes an action that
doesn't match one of the specialist advisors (ML, Feed Lifecycle, FLX
Threshold, FQM, Component Health).

Your job: translate user intent into concrete, structured action
proposals against the TrackMe REST API. The catalog has ~423
endpoints, but DON'T search them all at once — use the resource-
groups map to scope first.

## STRUCTURAL SAFETY PROPERTY

You are **read-only at the SDK level**. Your MCP tool allowlist
contains zero write tools. Your only "write" capability is
``propose_action``, which emits a structured contract for the consent
card to render. The user clicks Confirm; the frontend fires the
actual REST call. Mutation is the consent click — never your direct
action.

This means:
  - You CANNOT directly call any endpoint that mutates state.
  - You CAN call read-tagged endpoints via ``read_via_endpoint`` to
    verify current state before proposing a write.
  - You MUST emit ``propose_action`` for any action you want the user
    to actually run.
  - The user always sees the resolved request body BEFORE it fires.

## DISCOVERY CHECKLIST — FOLLOW IN ORDER

The catalog has ~423 endpoints across ~30 resource groups. Searching
the whole catalog with a flat keyword query produces false positives
(common production failure mode: ``"disable monitoring"`` matches
half a dozen unrelated endpoints, the agent picks the wrong one or
hallucinates a plausible-looking name). The fix is **scope first**.

For ANY user-action request, follow these steps in order:

**Step 1 — Restate the intent in one line.** Before any tool call,
echo back what you understood. If ambiguous, ASK the user before
discovering. *"Did you mean increase priority to critical, or high?
Current is medium."*

**Step 2 — Pick a resource group.** The full curated list of
resource groups is **embedded in your initial message** under the
``## RESOURCE GROUPS — AVAILABLE TO YOU`` section. Read that list
before doing anything else; it is your authoritative scope. You can
also call ``list_resource_groups()`` for the same data programmatically
if you need it during reasoning, but you should NOT need a tool call
just to see the group names — they're already in front of you.

Map the user's intent to ONE group from the embedded list. Common
patterns:

  - "disable monitoring on a DSM entity" → ``splk_dsm``
  - "change priority to critical" → ``splk_dsm`` (entity-level
    priority lives under the data-source group, not a separate
    "priority" group; the priority POLICIES are in
    ``splk_priority_policies``)
  - "create a backup" → ``backup_and_restore``
  - "list maintenance windows" → ``maintenance`` or ``maintenance_kdb``
  - "set up a tag policy" → ``splk_tag_policies``

If the intent doesn't map cleanly to one group **from the embedded
list**, ASK the user to clarify rather than guess. Do NOT invent a
group name that isn't in the embedded list — the catalog ONLY
contains those groups, and ``list_endpoints_in_group`` will reject
unknown values.

**Step 3 — List endpoints in that group.** Call
``list_endpoints_in_group(resource_group=<chosen>)``. The response
gives you the full manifest (~15 endpoints typical) with each
endpoint's ``path``, ``method``, ``danger_level``, ``description``,
AND ``body_parameters`` (the authoritative body-key map). This is
your shortlist — pick from it.

  Alternative: ``discover_endpoints(intent_keywords=...,
  resource_group=<chosen>)`` ranks the same shortlist by lexical
  match against your intent. Useful when the manifest is long and
  the description-driven pick isn't obvious.

**Step 4 — Verify state for write actions.** If your pick is a
write endpoint, FIRST exercise a read endpoint via
``read_via_endpoint`` to confirm:

  - Does the target exist?
  - What's its current state?
  - Is the action a no-op (priority already critical, monitoring
    already disabled)?

If the action would be a no-op, tell the user — don't propose.

**Step 5 — Construct the action contract.** Build
``propose_action`` with:

  - ``endpoint_path`` — **COPY VERBATIM** from
    ``list_endpoints_in_group``'s ``path`` field (or
    ``describe_endpoint`` if you fetched the full block). Never
    construct, shorten, or "simplify" the path. The catalog publishes
    the full Splunk-style path (e.g.
    ``/services/trackme/v2/splk_dsm/write/ds_monitoring``); the
    ``/write/`` segment is **load-bearing** — dropping it produces a
    404. Post-emission validation rejects any ``endpoint_path`` not
    present in the live catalog.
  - ``method`` — must match the catalog's registered method.
  - ``body_template`` — JSON body. **EVERY KEY MUST COME FROM** the
    catalog's ``body_parameters``. Do **not** invent keys based on
    intuition — e.g. there is no ``monitored_state`` field on
    ``ds_monitoring``; the real schema is ``object_list`` /
    ``keys_list`` / ``action: "enable" | "disable"``. Post-emission
    validation rejects any body key not in ``body_parameters``.
  - Use the literal string ``<session-injected>`` for identifier
    values (``tenant_id`` / ``object_id`` / ``object`` /
    ``component``). Spelled-out values are rejected by the
    Pydantic validator.
  - **PREFER ``object_list`` over ``keys_list``** when both are
    accepted by the endpoint. ``object_list`` resolves from the
    always-known ``object`` name (every chat surface supplies it).
    ``keys_list`` resolves from ``object_id`` which is the entity's
    SHA256 KV ``_key`` — but the entity-variant chat panel does not
    populate ``object_id`` (it only knows the human-readable name),
    so a ``keys_list: <session-injected>`` placeholder will fail to
    resolve and the Confirm loop will refuse the action. (Body
    fields are JSON-serialised, not URL paths, so colons in
    ``object`` values are safe — there is no URL-encoding hazard.)
    Use ``keys_list`` only when (a) the endpoint accepts ONLY
    ``keys_list`` (rare) or (b) you have explicit instructions from
    the user with a confirmed ``object_id`` value — in which case
    you must propose without session injection and let the user
    review the spelled-out id.
  - ``session_injected_fields`` — names body keys the frontend
    resolves at consent time. Allowed: ``tenant_id``, ``object_id``,
    ``object``, ``component``. **Caveat:** the entity-variant
    chat panel only populates ``tenant_id`` / ``object`` /
    ``component``; ``object_id`` is intentionally unset and any
    placeholder relying on it will fail to resolve.
  - **``update_comment`` — ALWAYS include for write endpoints that
    accept it** (most do — check ``body_parameters``). One concise
    sentence in operator voice that explains WHY the change is
    being made, citing the user's stated intent and any specific
    fields / values involved. This text lands in the per-entity
    "Audit changes" panel — when a teammate looks at the audit
    timeline three weeks later, this is the only context they
    see. ``"API update"`` is the handler's default fallback and
    means "the agent didn't bother" — never accept it. Examples:
    ``"update_comment": "Disable monitoring — user reports this
    feed is intentionally noisy and out of scope for alerting"``;
    ``"update_comment": "Tighten lag threshold from 600s to 180s
    per analyst request after observing latency drop on
    PROD-2"``. Mirror the prose ``rationale`` from this proposal
    (audit-ready short form), don't duplicate the full
    multi-sentence consent-card text.

    **Do NOT prefix ``update_comment`` with ``[AI Agent]``** — the
    consent card stamps the prefix automatically at confirm time
    (mirrors the server-side stamping the five specialised
    advisors do inside their Python tools, where every write
    body's ``update_comment`` becomes ``f"[AI Agent] {reason}"``).
    Write the reason content only; the prefix lands on every
    Concierge write through the same audit convention without
    you having to repeat it. If you do include the prefix it
    won't double-stamp (the helper is idempotent), but writing
    just the reason keeps the proposal cleaner.
  - ``danger_level`` — must match the catalog's classification (no
    downgrades; ``destructive`` stays destructive even if you think
    it "really" is just write-low).
  - ``rbac_required`` — must match the catalog's required capability.
  - ``rationale`` — one short paragraph the user reads on the
    consent card before approving.

**Step 6 — Be honest about uncertainty.** If after Step 3 you don't
have a clean shortlist match, say so in prose:

  *"The closest match in the splk_dsm group is `ds_update_lag_policy`,
  but you said 'tighten the SLA threshold' which more naturally maps
  to the splk_sla_policies group's `update_sla_class`. Want me to
  pursue that one instead?"*

Better to bounce back than emit a confident-but-wrong proposal that
the catalog gate will reject.

## SPECIALIST OVER GENERALIST

If the user's intent matches a SPECIALIST advisor (ML model issues,
FLX threshold tuning, FQM dictionary calibration, Feed Lifecycle for
DSM/DHM, Component Health for WLK/MHM), propose the SPECIALIST's
action-contract (``advisor_invocation``) — NOT a Concierge
invocation. Specialists carry curated remediation logic and audit
categorisation that a generic REST call cannot replicate. Concierge
is for the long tail — everything outside the specialists' surfaces.

## HARD RULES

- **Copy ``endpoint_path`` verbatim from ``describe_endpoint``.** Never
  construct or shorten it. Common production failure mode: agent emits
  ``/services/trackme/v2/splk_dsm/ds_update_dsm`` (a fabricated path)
  when the real endpoint is
  ``/services/trackme/v2/splk_dsm/write/ds_monitoring``. The
  ``/write/`` segment is load-bearing; dropping it produces a 404.
  Post-emission validation rejects any path not in the live catalog.

- **Body keys come from ``describe_endpoint``'s ``body_parameters``,
  never from intuition.** The catalog publishes a per-endpoint map of
  accepted body keys; copy keys verbatim from that map. Common
  production failure mode: agent emits ``monitored_state: "disabled"``
  on an endpoint whose actual schema is
  ``action: "enable" | "disable"``. Post-emission validation rejects
  any body key not in the catalog's ``body_parameters``.

- **Identifiers come from session state, NEVER from your own
  construction.** Use the literal string ``"<session-injected>"`` in
  the ``body_template`` for ``tenant_id`` / ``object_id`` / ``object``
  / ``component``. The frontend resolves them at consent time. The
  Pydantic validator REJECTS any other value for those fields — so
  even if you confidently spell out an ID in prose, the structured
  output will fail and the user will see an error.

- **Prefer ``object_list`` (with ``object``) over ``keys_list``
  (with ``object_id``)** when both are accepted by the endpoint.
  The entity-variant chat panel populates ``object`` but NOT
  ``object_id``, so ``keys_list: <session-injected>`` cannot be
  resolved and the Confirm loop will refuse the action. The colons
  in ``object`` names are safe — body fields are JSON-serialised,
  not URL paths, so there is no URL-encoding hazard. Reach for
  ``keys_list`` only when the endpoint accepts ONLY ``keys_list``
  (rare).

- **Every action requires explicit user consent.**
  ``consent_required: true`` on every proposal. The frontend rejects
  contracts without it. There is no auto-fire mode.

- **Read first, propose second.** Always exercise read endpoints to
  confirm state before proposing a write. Proposing a write without
  having verified current state is a smell — at best the agent
  proposes a no-op, at worst it proposes the wrong action because
  it misread the intent.

- **Specialist over generalist.** When intents match both a
  specialist (ML / FLX Threshold / FQM / Feed Lifecycle / Component
  Health) AND a discovered REST endpoint, propose the specialist's
  contract. Specialists are tuned for their surfaces; Concierge is
  the catch-all.

- **Cap multi-action proposals at 50.** For larger batches, ask the
  user to confirm a sample first, then propose subsequent batches in
  follow-up turns. The per-tenant
  ``ai_concierge_max_actions_per_proposal`` (default 10) is the
  operational cap; the schema-level cap (200) is a runaway guard.

- **Destructive-tagged actions need extra confirmation.** The consent
  card adds a "type X to confirm" textbox per destructive action;
  don't try to bypass that UX.

## YOUR OUTPUT — TWO CHANNELS, ONE SOURCE OF TRUTH

You produce two outputs per run, and only ONE of them carries actions
to the consent card.

### Channel 1 — ``propose_action`` tool calls (AUTHORITATIVE)

Actions reach the consent card ONLY through ``propose_action``. The
server records the validated set from your last successful
``propose_action`` call and uses that — and ONLY that — as the action
list rendered to the user. You can call ``propose_action`` multiple
times to refine; the LAST call replaces previous ones. When the
return shape is ``status: "valid"``, your proposal is locked in.

**HARD RULE**: if you do not call ``propose_action`` successfully, NO
ACTIONS reach the user, regardless of what you put in your structured
output. The server WIPES the structured-output ``actions`` field
before serialising the response — there is NO fallback, NO recovery
path. Hallucinating an ``endpoint_path`` in the structured output is
a wasted generation: it gets discarded and the user sees a "no
proposal could be validated" message in the chat.

**The ONLY way to propose an action is**: discover endpoints with
``list_endpoints_in_group`` (using a group from the embedded list),
copy a real ``path`` verbatim, then call ``propose_action`` with that
exact path. The catalog is the only source of truth; never construct
a path from intuition.

### Channel 2 — ``ConciergeProposalResult`` structured output (NARRATIVE)

You return a structured ``ConciergeProposalResult`` with:

- ``summary``: 1-3 sentence overview of what you investigated and
  what you're proposing. Shown in the chat bubble.
- ``intent_summary``: Restatement of the user's intent. Shown as the
  consent card title.
- ``actions``: **IGNORED BY THE SERVER**. Leave it empty (``[]``).
  The consent card renders only what ``propose_action`` recorded.
  Filling this field is wasted output tokens — the server overwrites
  it with the recorder's contents before serialising the response.
- ``consent_required``: MUST be ``true``.
- ``suggested_reason``: Short consent-card heading.
- ``actions_taken``: Auto-populated by the SDK with the tools you
  invoked.
- ``reasoning_trace``: Step-by-step bullets explaining how you
  arrived at the proposal. Surfaced in the consent card's
  collapsible trace section.

### Why two channels?

The Splunk Agent SDK emits tool calls and structured output along two
INDEPENDENT generation paths. In testing we saw the LLM call
``propose_action`` with a clean catalog-validated path (e.g.
``/services/trackme/v2/splk_dsm/write/ds_monitoring``) and then emit
a DIFFERENT path in its structured output (e.g. the fabricated
``/services/trackme/v2/splk_dsm/ds_update_dsm``). The user saw the
fabricated path with a "not in catalog" red banner, even though the
agent's tool call was correct.

Approach 1 makes the divergence physically impossible: only the
recorded ``propose_action`` set reaches the consent card. The
structured-output ``actions`` field is trapped output that nobody
reads. Don't waste tokens on it.

### When you have nothing to propose

If you investigated and decided NOT to propose any actions (the user
asked a question you answered in prose, OR the request is out of
scope), simply do NOT call ``propose_action``. Return a structured
output with a clear ``summary`` explaining the situation. The consent
card won't render and the user reads your narrative.

Don't fabricate a proposal just because you're asked.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Per-tenant ``ai_concierge_enabled`` and ``ai_concierge_allow_destructive``
# helpers were removed in the gate-removal refactor. TrackMe RBAC at the
# REST boundary is the authoritative gate — a user's effective roles
# determine which catalog endpoints they can fire — and the consent card's
# per-action typed-confirmation flow is the UX-belt-and-suspenders for
# destructive actions. Two redundant per-tenant gates added nothing beyond
# what RBAC + the typed-confirmation already enforce, and the enablement
# gate broke the Virtual Tenants chat surface (no single ``tenant_id`` in
# scope to gate against → fail-closed swallowed every cross-tenant
# proposal). The operational caps below stay because they're not safety
# gates — they shape per-tenant agent behaviour (cost, rate).


def _vtenant_concierge_max_actions(
    vtenant_account: Optional[Dict[str, Any]],
    default: int = 10,
) -> int:
    """Per-tenant cap on actions per proposal.

    Defaults to 10. The schema-level cap (200) catches runaway
    proposals; this is the lower per-tenant operational limit. The
    REST handler reads this and surfaces it to the agent at launch
    time so the agent prompt can adjust ("don't propose more than N
    actions in one go").
    """
    if not vtenant_account:
        return default
    raw = vtenant_account.get("ai_concierge_max_actions_per_proposal", default)
    try:
        value = int(raw)
        return max(1, min(value, 200))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Resource-groups grounding for the initial message
# ---------------------------------------------------------------------------
#
# The Concierge agent has tools to discover the catalog
# (``list_resource_groups`` / ``discover_endpoints`` /
# ``list_endpoints_in_group`` / ``describe_endpoint``), but observed
# behaviour shows the LLM frequently SKIPS the discovery step and
# hallucinates plausible-looking paths from its training data
# (``ds_update_dsm`` / ``ds_update_entity`` / etc.) — paths that don't
# exist in the live API. Approach 1 + the catalog gate prevent the
# hallucinated path from reaching the user as a fireable action, but
# the user-visible UX is still "agent failed: invented path".
#
# Embedding the curated resource-groups map (35 entries, ~3.5K tokens)
# directly in the initial message is cheap relative to the agent's
# 200K token budget and gives the LLM the canonical group taxonomy as
# ground truth from token zero. The agent still calls
# ``list_endpoints_in_group`` to drill into a chosen group — but it
# can't fabricate a group name that doesn't exist, because the
# authoritative list is right in front of it.


def _format_resource_groups_for_initial_message() -> str:
    """Format the curated resource-groups map as a markdown section.

    Pulls the same hand-curated map the REST API Reference's AI
    Assistant context uses (single source of truth in
    ``trackme_libs_describe_rest_api_reference.get_resource_groups_map``).
    Output is one line per group: ``- **<key>** [/<sub_groups>...]:
    <description>``. Sub-groups are listed inline so the LLM sees the
    full set of valid umbrella keys it can pass to
    ``list_endpoints_in_group`` (the tool accepts both umbrella keys
    like ``splk_dsm`` AND specific sub-groups like ``splk_dsm/write``).

    Returns the formatted markdown section, or an empty string if the
    map cannot be loaded for any reason — a missing groundings
    section is strictly better than a runtime exception in the agent
    runner.
    """
    # The whole load + format path is wrapped in a single try/except.
    # The docstring promises "graceful return empty string on any
    # failure" — but the previous shape only protected the import +
    # ``get_resource_groups_map()`` call, leaving the formatting loop
    # exposed. If the curated map's structure ever drifts (a
    # non-string in ``sub_groups``, a non-dict entry where we
    # presumed dict-shape, a UTF-8 issue inside ``join``), an
    # unhandled exception would propagate up and FAIL THE ENTIRE
    # AGENT RUN — which contradicts the safety guarantee the
    # grounding section claims to provide. Bugbot caught this on
    # PR #1336 (Medium severity). The whole-function try/except is
    # the simplest fix that genuinely honours the docstring.
    try:
        from trackme_libs_describe_rest_api_reference import (
            get_resource_groups_map,
        )
        groups = get_resource_groups_map()

        if not isinstance(groups, dict) or not groups:
            return ""

        lines: List[str] = []
        for key in sorted(groups.keys()):
            entry = groups.get(key) or {}
            if not isinstance(entry, dict):
                continue
            description = (entry.get("description") or "").strip()
            sub_groups = entry.get("sub_groups") or []
            if isinstance(sub_groups, list) and sub_groups:
                # Surface the sub-group keys inline so the LLM knows the
                # specific umbrella values that ``list_endpoints_in_group``
                # accepts (e.g. ``splk_dsm/write`` for write-tagged
                # endpoints under DSM). Filter to strings + sort for
                # stable output and to defend against schema drift.
                sub_str = ", ".join(
                    sorted(
                        s for s in sub_groups
                        if isinstance(s, str) and s != key
                    )
                )
                if sub_str:
                    lines.append(
                        f"- **{key}** (also: {sub_str}): {description}"
                    )
                    continue
            lines.append(f"- **{key}**: {description}")

        if not lines:
            return ""

        return (
            "\n## RESOURCE GROUPS — AVAILABLE TO YOU\n\n"
            "The TrackMe REST API is organised into the following resource "
            "groups. **This is your authoritative scope** — every endpoint "
            "you propose MUST belong to one of these groups. Pick the group "
            "that matches the user's intent FIRST, then call "
            "``list_endpoints_in_group(resource_group=<key>)`` to see the "
            "exact endpoints available within it.\n\n"
            + "\n".join(lines)
            + "\n\n**Do NOT invent group names or paths.** The list above "
            "is the complete set of resource groups; if the user's intent "
            "doesn't map cleanly to one, ask them to clarify rather than "
            "guess.\n"
        )

    except Exception as exc:
        logger.warning(
            f"_format_resource_groups_for_initial_message: failed to "
            f"build grounding section ({type(exc).__name__}: {exc}); "
            f"skipping. The agent's ``list_resource_groups`` tool "
            f"remains the runtime fallback."
        )
        return ""


def _append_recorder_empty_note_to_trace(
    result: "ConciergeProposalResult",
    *,
    reason: str,
) -> None:
    """Append a user-facing explanation to ``result.reasoning_trace``.

    Called when ``result.actions`` is wiped because the propose_action
    recorder is empty (or rebuild failed). The chat panel renders
    ``reasoning_trace`` as a collapsible "agent thinking" block, so the
    user sees WHY the proposal was discarded rather than a silent empty
    card. Without this, an agent run that fails to call
    ``propose_action`` looks like it just succeeded with no actions —
    which is indistinguishable from a legitimate question-answering
    response.

    Mutates the result in place via direct attribute assignment.
    ``reasoning_trace`` is a ``List[str]`` field on a Pydantic model;
    Pydantic v2's default behaviour assigns lists without revalidating,
    so a direct write is equivalent to the ``model_copy`` roundtrip
    and avoids constructing an entire new instance just to read back
    the same list. Bugbot flagged the pointless roundtrip on PR #1336
    (Low severity).
    """
    note = (
        f"⚠️ No consent card rendered: {reason}"
    )
    existing_trace = list(result.reasoning_trace or [])
    existing_trace.append(note)
    result.reasoning_trace = existing_trace  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Post-emission validation
# ---------------------------------------------------------------------------


def _validate_post_emission(
    result: "ConciergeProposalResult",
    *,
    system_service: Any,
    job_id: str,
) -> "ConciergeProposalResult":
    """Final cross-check of the agent's structured output against the catalog.

    The Splunk Agent SDK's structured-output emission is independent of
    the agent's tool calls — even when ``propose_action`` returned
    ``valid``, the LLM can still emit a different
    ``ConciergeProposalResult`` with hallucinated ``endpoint_path`` /
    invented ``body_template`` keys. This guard is the very last check
    before the proposal reaches the chat bubble.

    For each action:
      1. Look up ``endpoint_path`` in the live catalog. If absent →
         drop the action and accumulate a warning.
      2. Cross-check every body_template key against the catalog
         entry's ``body_parameters`` (sourced from
         ``raw_describe.options[0]``). Unknown keys → drop the
         action.
      3. Cross-check ``method`` and ``danger_level`` for consistency
         with the catalog. Mismatches → drop.

    Warnings land in ``result.reasoning_trace`` so the user sees why
    actions were filtered. If every action gets dropped, the
    ``actions`` list ends up empty and the consent card simply doesn't
    render — the chat bubble still shows the agent's narrative
    (``summary``) plus the warnings.

    Catalog fetch failures are fail-open: if we cannot load the catalog
    we log a warning and return ``result`` unchanged. The frontend
    catalog gate (PR #4) catches the same hallucinations on the second
    pass.

    Returns a (possibly mutated) ``ConciergeProposalResult``.
    """
    if result is None or not getattr(result, "actions", None):
        return result

    # Build a path-indexed lookup over the live catalog. The row →
    # entry projection runs through the shared
    # ``project_catalog_row_to_entry`` helper in
    # ``trackme_libs_autodocs_catalog`` — same single source of truth
    # the Concierge tools module uses (``_fetch_full_catalog``). A
    # future schema tweak (new field on ``raw_describe.options``,
    # different normalisation, new inferred attribute) lands in one
    # place; this validator and the tools-side fetch cannot drift.
    # Bugbot caught the original duplication on PR #1321.
    try:
        # Use the version-keyed filesystem cache — post-emission
        # validation runs on every Concierge proposal and rebuilding the
        # catalog (~19s) on each call would dwarf the agent's own
        # latency. Cache hit: sub-second; auto-invalidates on app
        # upgrade because the cache key embeds ``version.json``.
        from trackme_libs_autodocs_catalog_builder import (
            build_catalog_as_list_cached as _build_catalog_list,
        )
        from trackme_libs_autodocs_catalog import (
            CatalogEntry,
            project_catalog_row_to_entry,
        )
        splunkd_uri = (
            f"{system_service.scheme}://"
            f"{system_service.host}:{system_service.port}"
        )
        session_key = system_service.token
        raw_entries = list(_build_catalog_list(splunkd_uri, session_key, target="endpoints"))
    except Exception as exc:
        logger.warning(
            f"Concierge Advisor: post-emission catalog fetch failed "
            f"for job_id={job_id}: {exc}. Skipping validation."
        )
        return result

    by_path: Dict[str, "CatalogEntry"] = {}
    for row in raw_entries:
        entry = project_catalog_row_to_entry(row)
        if entry is None:
            continue
        by_path[entry.path] = entry
        by_path[entry.path.lstrip("/")] = entry

    kept: List[ConciergeAction] = []
    warnings: List[str] = []
    for idx, action in enumerate(result.actions):
        endpoint_path = action.endpoint_path or ""
        catalog_entry = by_path.get(endpoint_path) or by_path.get(endpoint_path.lstrip("/"))
        if catalog_entry is None:
            warnings.append(
                f"action[{idx}] dropped: endpoint_path "
                f"{endpoint_path!r} is not present in the live API "
                f"catalog (likely a hallucination). Try rephrasing or "
                f"asking for a specific endpoint by name."
            )
            continue
        if action.method != catalog_entry.method:
            warnings.append(
                f"action[{idx}] dropped: method {action.method!r} does "
                f"not match catalog method {catalog_entry.method!r} for "
                f"path {endpoint_path!r}."
            )
            continue
        if action.danger_level != catalog_entry.danger_level:
            warnings.append(
                f"action[{idx}] dropped: danger_level "
                f"{action.danger_level!r} does not match catalog "
                f"danger_level {catalog_entry.danger_level!r} for path "
                f"{endpoint_path!r}."
            )
            continue
        # Body-key validation.
        accepted_keys = catalog_entry.body_parameters or frozenset(
            tuple(catalog_entry.required_params) + tuple(catalog_entry.optional_params)
        )
        if accepted_keys:
            bad_keys = sorted(
                k for k in action.body_template.keys() if k not in accepted_keys
            )
            if bad_keys:
                warnings.append(
                    f"action[{idx}] dropped: body_template carries "
                    f"unknown key(s) {bad_keys!r} not accepted by "
                    f"endpoint {endpoint_path!r}. Accepted keys per "
                    f"the catalog: {sorted(accepted_keys)!r}."
                )
                continue
        kept.append(action)

    if warnings:
        # Mutate the result via Pydantic's model_copy + update so the
        # Pydantic invariants stay intact. ``reasoning_trace`` accumulates
        # the warnings so they surface in the chat (the consent card
        # renders ``reasoning_trace`` as a collapsible list).
        existing_trace = list(result.reasoning_trace or [])
        existing_trace.extend(warnings)
        try:
            result = result.model_copy(update={
                "actions": kept,
                "reasoning_trace": existing_trace,
            })
        except Exception:
            # Fall back to a direct field write if model_copy isn't
            # available on the result type for some reason.
            result.actions = kept  # type: ignore[assignment]
            result.reasoning_trace = existing_trace  # type: ignore[assignment]
        logger.warning(
            f"Concierge Advisor: post-emission validation dropped "
            f"{len(warnings)} action(s) for job_id={job_id}: "
            f"{warnings!r}"
        )
    return result


# ---------------------------------------------------------------------------
# Agent orchestration
# ---------------------------------------------------------------------------


async def _run_concierge_advisor_agent(
    model,
    config,
    service,
    job_id,
    tenant_id,
    surface,
    user_intent,
    user_context=None,
    vtenant_account=None,
    automated=False,
    server_name=None,
):
    """Run the Concierge agent and return a ``ConciergeProposalResult``.

    Mirrors the FQM advisor's ``_run_fqm_advisor_agent`` shape but
    with Concierge-specific tool tags / system prompt / output schema.
    The agent has zero write tools — its only "mutation" surface is
    ``propose_action``, which emits a structured contract that the
    consent card renders. Mutation flows through the consent click,
    not the agent.

    Args:
        model: Resolved Splunk Agent SDK model (provider-bound).
        config: AI provider configuration dict (token limit, custom
            prompt, etc.).
        service: splunklib service handle for the agent's tool
            subprocess. Should be authenticated as the requesting
            user (``session_key``), NOT ``system_authtoken`` — the
            SDK rejects ``splunk-system-user`` as the agent caller.
        job_id: ``_key`` of the agent job record in
            ``kv_trackme_ai_agent_jobs``. Used for progress tracing
            + structured output persistence.
        tenant_id: Tenant the user is operating in.
        surface: One of ``entity`` / ``tenant_home`` / ``vtenants`` /
            ``global``. Filters the agent's discovery scope so it
            doesn't surface off-context endpoints.
        user_intent: Free-text user intent from the chat.
        user_context: Optional analyst-supplied additional
            instructions.
        vtenant_account: Tenant configuration dict (carries
            ``ai_concierge_*`` flags).
        automated: When ``True``, the agent runs in unattended
            mode (no UI). The Concierge agent doesn't currently have
            an automated entry path — flag is plumbed through for
            symmetry with the FQM advisor and as a future hook.
        server_name: Search-head identifier for audit-event
            ``host`` field. Best-effort.

    Returns:
        ``ConciergeProposalResult`` with the agent's proposal.
    """
    # Pin the shared agent infrastructure's logger to this advisor for
    # the duration of this async context.  Without this, tool_middleware
    # lines from trackme_libs_ai_agents.py route to the default
    # (ml_advisor) log file even when this advisor is the one running.
    set_current_advisor_logger("trackme.rest.ai.concierge_advisor")

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

    # Concierge agent has its own per-provider token / step limits —
    # higher than the specialists because catalog-grounding burns
    # tokens. Defaults match the plan doc.
    agent_token_limit = max(1, int(config.get("ai_concierge_token_limit", "200000")))
    agent_step_limit = max(1, int(config.get("ai_concierge_step_limit", "30")))

    # Tool allowlist: ONLY read-tagged tools (``concierge_read`` +
    # ``maintenance_read``). No write tools at the SDK level. This is the
    # structural safety property — the agent literally cannot mutate state
    # because it has no mutation tools. Mutation (including putting an entity
    # into maintenance) is proposed and only happens on the consent-card click.
    allowed_tags = ["concierge_read", "maintenance_read"]

    logger.info(
        f"Concierge Advisor agent starting: tenant_id={tenant_id!r}, "
        f"surface={surface!r}, model={model_name}, "
        f"provider={provider_type} ({provider_name_log}), "
        f"token_limit={agent_token_limit}, step_limit={agent_step_limit}, "
        f"intent={user_intent[:120]!r}"
    )

    # Build the initial message — surface the user's intent + the
    # operational cap the tenant has configured. The agent reads the
    # cap from this preamble; we don't rely on it inferring it from
    # environment. The destructive-action gate was removed in the
    # gate-removal refactor — RBAC + per-action typed-confirmation
    # are the authoritative safety layers.
    max_actions = _vtenant_concierge_max_actions(vtenant_account)

    initial_message = (
        f"## CHAT CONTEXT\n\n"
        f"- **Tenant**: {tenant_id}\n"
        f"- **Surface**: {surface}\n"
        f"- **Max actions per proposal (tenant cap)**: {max_actions}\n\n"
        f"## USER INTENT\n\n"
        f"{user_intent}\n"
    )

    if user_context:
        initial_message += (
            f"\n## OPERATOR INSTRUCTIONS (additional)\n\n"
            f"{user_context}\n"
        )

    # Embed the curated resource-groups map directly in the initial
    # message — the LLM sees it as ground truth from token zero, can't
    # fabricate group names, and is forced to start scoping from a
    # known taxonomy. Cheap (~3.5K tokens) relative to the 200K agent
    # budget. Empty string when the map isn't loadable; the agent's
    # ``list_resource_groups`` tool remains the live fallback.
    initial_message += _format_resource_groups_for_initial_message()

    initial_message += _build_initial_message_tool_strategy_hint(model, provider_type)

    # Reset tool-subprocess env vars (defensive — the FQM agent does
    # the same). We don't currently propagate any Concierge-specific
    # env, but the slot is here for future use (e.g. a destructive-
    # action allow-flag).
    _ssl_cert_file = os.environ.get("SSL_CERT_FILE")
    _ssl_removed = False
    if _ssl_cert_file and not os.path.isfile(_ssl_cert_file):
        del os.environ["SSL_CERT_FILE"]
        _ssl_removed = True

    _automated_prev = os.environ.get("TRACKME_AI_AUTOMATED")
    os.environ["TRACKME_AI_AUTOMATED"] = "1" if automated else "0"

    max_attempts = 3
    last_error = None

    _token_count = [0]
    _steps_taken = [0]
    _reasoning_step_starts: Dict[str, float] = {}

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
        # Emit a synthetic "reasoning_step_<N>" progress event so
        # the chat panel's progress feed has something to render —
        # same trick we used for the FQM dictionary_generate flow
        # (PR #1293) since the Concierge agent's discovery /
        # describe / read tool calls already produce real progress
        # events, but the synthesis step (last model call before
        # final output) is silent without this hook. Net result:
        # the user sees consistent progress activity throughout
        # the agent's run.
        if not job_id or service is None:
            return
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
            pass

    @after_model
    def _emit_reasoning_end(_res) -> None:
        if not job_id or service is None:
            return
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

    # Import the Concierge tools registry — side-effect: registers
    # the four ``concierge_read``-tagged tools with the SDK.
    import trackme_ai_concierge_tools  # noqa: F401

    # Approach 1 recorder — the per-run list ``propose_action`` populates
    # on validation success. The composer below reads from this list AFTER
    # ``agent.invoke()`` returns and overwrites ``output.actions`` so the
    # consent card sees only validated, recorded proposals (not the
    # LLM's free-form structured-output actions, which can hallucinate).
    # See module docstring on ``trackme_ai_concierge_tools`` for the full
    # rationale.
    _recorded_actions: List[Dict[str, Any]] = []
    _recorder_token = trackme_ai_concierge_tools.install_proposed_actions_recorder(
        _recorded_actions
    )

    # Resolve the tenant summary index for tool-call audit events.
    try:
        from trackme_libs import trackme_idx_for_tenant  # noqa: WPS433
        _splunkd_uri = f"{service.scheme}://{service.host}:{service.port}"
        _idx_settings = trackme_idx_for_tenant(service.token, _splunkd_uri, tenant_id)
        _summary_index = _idx_settings.get("trackme_summary_idx", "trackme_summary")
    except Exception:
        _summary_index = "trackme_summary"

    _check_agent_model_capability(model, provider_type, model_name)

    try:
        for attempt in range(1, max_attempts + 1):
            _token_count[0] = 0
            _steps_taken[0] = 0
            # Clear the recorder at the start of each attempt — same
            # rationale as ``_token_count`` / ``_steps_taken`` reset
            # above. If attempt N's LLM successfully called
            # ``propose_action`` (recorder populated) but the agent
            # then raised an SDK error before reaching structured-
            # output emission (e.g. ``_is_agent_structured_output_failure``),
            # the recorder retains attempt-N's stale validated set.
            # Without this clear, attempt N+1 — which may legitimately
            # decide NOT to call ``propose_action`` (different LLM
            # decision tree on the retry) — would still surface attempt
            # N's actions to the composer. The composer would then
            # overwrite ``result.actions`` with stale data from a
            # discarded run.
            #
            # ``recorder.clear()`` mutates in-place, so the install_*
            # call's recorder reference (held inside the ContextVar)
            # stays valid — both ``propose_action`` and the post-run
            # composer (which reads via ``list(_recorded_actions)``)
            # see the same list object across attempts. Bugbot caught
            # this on PR #1329 (Medium severity).
            _recorded_actions.clear()
            try:
                with force_tool_strategy_for_provider(provider_type):
                    async with Agent(
                        model=model,
                        system_prompt=CONCIERGE_ADVISOR_SYSTEM_PROMPT,
                        service=service,
                        tool_settings=ToolSettings(
                            local=LocalToolSettings(allowlist=ToolAllowlist(tags=allowed_tags)),
                            remote=None,
                        ),
                        output_schema=ConciergeProposalResult,
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
                                _emit_reasoning_end,
                                make_tool_trace_middleware(
                                    "Concierge Advisor",
                                    job_id=job_id,
                                    service=service,
                                    advisor_kind="concierge",
                                    tenant_id=tenant_id,
                                    component="",  # generalist — no fixed component
                                    object_name="",
                                    object_id="",
                                    mode="propose",
                                    automated=automated,
                                    summary_index=_summary_index,
                                    server_name=server_name,
                                ),
                            ] if mw is not None
                        ],
                    ) as agent:
                        logger.info(
                            f"Concierge Advisor agent invoke starting: "
                            f"job_id={job_id}, attempt={attempt}/{max_attempts}"
                        )
                        result = await agent.invoke([HumanMessage(content=initial_message)])
                        # ``result.structured_output`` is the canonical
                        # SDK accessor for the Pydantic-parsed response —
                        # matches FQM / ML / Component Health / FLX
                        # Threshold / Feed Lifecycle. ``result.output`` is
                        # not part of the SDK's stable surface and would
                        # raise AttributeError at runtime, breaking every
                        # Concierge run. Bugbot caught the wrong
                        # accessor on commit 411e633b (High severity).
                        output = result.structured_output
                        if not isinstance(output, ConciergeProposalResult):
                            raise RuntimeError(
                                f"agent returned unexpected output type "
                                f"{type(output).__name__}, expected "
                                f"ConciergeProposalResult"
                            )
                        logger.info(
                            f"Concierge Advisor agent completed: "
                            f"surface={surface}, "
                            f"actions_count={len(output.actions) if output.actions else 0}, "
                            f"token_count={_token_count[0]}, "
                            f"steps={_steps_taken[0]}"
                        )
                        # Return real usage counters so the worker can
                        # surface them in the audit event — matches FQM's
                        # ``return output, _token_count[0], _steps_taken[0]``
                        # tuple contract. Without this the audit dashboard
                        # reports zero token / step usage for every run,
                        # which makes per-run cost analysis impossible.
                        # Bugbot caught the discarded counters on commit
                        # 411e633b (Medium severity).
                        #
                        # Approach 1 — also return the recorded action set
                        # ``propose_action`` populated. The caller
                        # (``_worker``) uses this as the authoritative
                        # source of ``output.actions``, ignoring whatever
                        # the LLM put in its structured output. ``list()``
                        # snapshots the recorder so subsequent retry
                        # iterations (which reuse the same list) don't
                        # mutate the value the caller sees.
                        return (
                            output,
                            _token_count[0],
                            _steps_taken[0],
                            list(_recorded_actions),
                        )

            except Exception as exc:
                last_error = exc
                # Transient provider / network error — see ML Advisor
                # for full rationale. Retry with exponential backoff.
                # Checked BEFORE the SDK-bug case because a 5s backoff
                # is the right behaviour for a network blip, whereas a
                # tool_result_bug should retry immediately.
                #
                # Concierge is exempt from the act-mode write-tool
                # safety gating that the 5 component advisors apply:
                # its tool allowlist is ``["concierge_read"]`` (see
                # ``allowed_tags`` above). The agent's only "write"
                # behaviour is emitting a structured ``propose_action``
                # contract — a pure JSON output, not a tool call — so
                # a retry never duplicates side effects.
                if attempt < max_attempts and _is_transient_provider_error(exc):
                    delay = _transient_retry_backoff_sec(attempt + 1)
                    logger.warning(
                        f"Concierge Advisor agent attempt "
                        f"{attempt}/{max_attempts} hit transient provider error "
                        f"({type(exc).__name__}: {str(exc)[:200]}), "
                        f"sleeping {delay}s before retry"
                    )
                    await asyncio.sleep(delay)
                    continue
                # Replay the FQM advisor's known-bug retry loop — the
                # SDK has occasional ``tool_use``/``tool_result`` race
                # conditions that succeed on retry. Same heuristic
                # applies here: retry only on the recognised SDK bug
                # signatures, fail fast on anything else.
                if attempt < max_attempts and (
                    _is_tool_result_bug(exc)
                    or _is_agent_structured_output_failure(exc)
                ):
                    logger.warning(
                        f"Concierge Advisor agent attempt "
                        f"{attempt}/{max_attempts} hit known SDK bug "
                        f"({type(exc).__name__}: {str(exc)[:200]}), "
                        f"retrying"
                    )
                    continue
                if _is_structured_output_unsupported(exc):
                    raise RuntimeError(
                        "The selected AI provider does not support "
                        "structured output, which the Concierge Advisor "
                        "requires. Pick a provider with structured-"
                        "output support (Anthropic Claude, OpenAI "
                        "GPT-4o, or equivalent)."
                    ) from exc
                # Unrecognised — re-raise.
                raise

        # Out of retries — propagate the last seen error.
        raise RuntimeError(
            f"Concierge Advisor agent exhausted {max_attempts} attempts: "
            f"{type(last_error).__name__}: {str(last_error)[:200]}"
        ) from last_error

    finally:
        # Restore env. Mirrors the FQM advisor's defensive cleanup so
        # subsequent runs in the same process don't pick up
        # leftover state.
        if _automated_prev is None:
            os.environ.pop("TRACKME_AI_AUTOMATED", None)
        else:
            os.environ["TRACKME_AI_AUTOMATED"] = _automated_prev
        if _ssl_removed and _ssl_cert_file:
            os.environ["SSL_CERT_FILE"] = _ssl_cert_file
        # Tear down the propose_action recorder (Approach 1). Idempotent
        # — the helper swallows token-mismatch errors. We do this even
        # on retries / failures so the next run in the same worker
        # process gets a fresh recorder.
        try:
            trackme_ai_concierge_tools.uninstall_proposed_actions_recorder(
                _recorder_token
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Public entry — async REST handler
# ---------------------------------------------------------------------------


def start_concierge_advisor_async(
    system_service,
    user_service,
    request_info,
    tenant_id,
    surface,
    user_intent,
    provider_name=None,
    user_context=None,
    launched_by="ui",
    chat_session_id="",
    vtenant_account=None,
):
    """Start the Concierge agent asynchronously.

    Creates a job record, spawns a background thread, returns the
    ``job_id`` immediately. The REST handler polls
    ``get_agent_job_status`` for the result.

    Mirrors ``start_fqm_advisor_async`` so the surrounding
    infrastructure (slot tracking, audit events, retry loop, agent
    service authentication) is shared.

    Args:
        system_service: System-context splunklib service (token =
            ``system_authtoken``). Used for KV reads.
        user_service: User-context splunklib service. Used for
            access-controlled reads.
        request_info: REST handler request_info.
        tenant_id: The tenant the user is operating in.
        surface: One of ``entity`` / ``tenant_home`` / ``vtenants`` /
            ``global``.
        user_intent: Free-text user request from the chat.
        provider_name: AI provider stanza name. Optional — defaults
            to the first configured provider.
        user_context: Optional analyst-supplied additional
            instructions.
        launched_by: ``"ui"`` (advisor modal) or ``"ai_assistant"``
            (chat-driven launch). Threaded to audit events so
            operators can see whether a run came from the chat
            bridge or a direct UI invocation.
        chat_session_id: When ``launched_by="ai_assistant"``, the
            chat session that proposed the launch. Empty otherwise.
        vtenant_account: Tenant configuration. Carries the
            ``ai_concierge_*`` flags.

    Returns:
        Dict with the structured ``{job_id, status: "running"}``
        response the REST handler returns to the caller.
    """
    model, config = get_sdk_model(system_service, provider_name=provider_name)

    with _active_agents_lock:
        if _agents_module._active_agents >= _MAX_CONCURRENT_AGENTS_DEFAULT:
            raise RuntimeError(
                f"AI agent at maximum capacity "
                f"({_MAX_CONCURRENT_AGENTS_DEFAULT} concurrent). "
                "Please try again later."
            )
        _agents_module._active_agents += 1

    try:
        job_id = _create_agent_job(system_service)

        # Build service for the agent.
        # See FQM advisor for the rationale: agent service
        # authenticates as the *requester* (``session_key``), NOT
        # ``system_authtoken`` — Splunk SDK's
        # ``validate_agent_privileges`` rejects ``splunk-system-user``
        # as the agent caller.
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
    _run_start_time = [time.time()]
    _request_user = getattr(request_info, "user", None) or None

    def _index_agent_event(svc, result_dict, status, error_msg=None,
                           token_count=0, steps_taken=0):
        """Index a structured audit event for this agent run.

        Sourcetype is ``trackme:ai_agent:concierge_advisor:propose`` for
        successful runs (the agent emitted a proposal — even if
        ``actions`` is empty). Failures index with the same sourcetype
        but ``status=error`` and the error message embedded.
        """
        try:
            from trackme_libs import trackme_idx_for_tenant
            try:
                idx_settings = trackme_idx_for_tenant(
                    session_key, splunkd_uri, tenant_id
                )
                tenant_summary_idx = idx_settings.get(
                    "trackme_summary_idx", "trackme_summary"
                )
            except Exception:
                tenant_summary_idx = "trackme_summary"

            sourcetype = "trackme:ai_agent:concierge_advisor:propose"
            duration_ms = int((time.time() - _run_start_time[0]) * 1000)
            event = {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "surface": surface,
                "advisor": "concierge",
                "mode": "propose",
                "status": status,
                # ``provider_name`` and ``model`` mirror the FQM /
                # ML / Component Health / FLX Threshold / Feed
                # Lifecycle conventions so per-provider and
                # per-model SPL aggregations work uniformly across
                # the agent family. Both ``provider_name`` (function
                # parameter) and ``config`` (loaded by
                # ``get_sdk_model``) live in the
                # ``start_concierge_advisor_async`` closure scope and
                # are accessible here. Bugbot caught the missing
                # fields on commit d99f6584 (Medium severity).
                "provider_name": provider_name or "default",
                "model": config.get("ai_model", "unknown"),
                "launched_by": launched_by,
                "chat_session_id": chat_session_id,
                "user_intent": (user_intent or "")[:500],
                "token_count": token_count,
                "steps_taken": steps_taken,
            }
            # Embed the full proposal payload so SPL queries against
            # ``index=trackme_summary sourcetype=trackme:ai_agent:concierge_advisor:propose``
            # can ``spath result.actions{}.endpoint_name`` /
            # ``spath result.summary`` etc. without needing a parallel
            # KV store of past runs. Mirrors the FQM / ML / Component
            # Health / FLX Threshold / Feed Lifecycle convention.
            # Bugbot caught the missing field on commit d4bf06e5
            # (Medium severity). Guard on truthiness — error / timeout
            # paths pass an empty dict and we don't want a JSON ``{}``
            # cluttering the event.
            if result_dict:
                event["result"] = result_dict
            if error_msg:
                event["error"] = str(error_msg)[:500]
            # ``enrich_agent_event_for_audit`` populates ``user`` (or
            # ``"automated"`` / ``"unknown"`` fallbacks), ``duration_ms``,
            # and the result-derived top-level mirrors
            # (``recommendations_count`` / ``actions_taken_count`` /
            # ``entity_status``). All parameters after ``event`` are
            # keyword-only — bugbot caught the wrong call signature on
            # commit a79bdb4a (High severity).
            enrich_agent_event_for_audit(
                event,
                result_dict=result_dict,
                user=_request_user,
                automated=False,
                duration_ms=duration_ms,
            )
            payload = {
                "event": json.dumps(event, default=str),
                "source": "trackme:ai_agent:concierge",
                "sourcetype": sourcetype,
            }
            if server_name:
                payload["host"] = server_name
            target_index = svc.indexes[tenant_summary_idx]
            target_index.submit(**payload)
        except Exception as exc:
            # Audit event lost permanently (no retry path).  Use ERROR
            # so audit-pipeline failures surface in error monitoring.
            logger.error(
                f"Concierge Advisor: failed to index audit event "
                f"for job_id={job_id}: {exc}"
            )

    # Watchdog coordination — see ``_make_agent_worker_watchdog`` in
    # ``trackme_libs_ai_agents``.  Concierge has no ``mode`` (it's
    # an interactive chat advisor) but does writes via
    # ``propose_action``, so the act-mode budget (15 min) is the
    # right wall-clock cap.  Index-event closure omits ``mode`` since
    # concierge's ``_index_agent_event`` doesn't take it.
    _watchdog_stop, _watchdog_fired, _start_watchdog = _agents_module._make_agent_worker_watchdog(
        advisor_label="Concierge Advisor",
        service=system_service,
        job_id=job_id,
        mode="act",
        run_start_time_holder=_run_start_time,
        update_agent_job_fn=lambda status, *, error=None: _update_agent_job(
            system_service, job_id, status, error=error
        ),
        index_agent_event_fn=lambda result_dict, status, *, error_msg=None: _index_agent_event(
            system_service, result_dict or {}, status=status, error_msg=error_msg
        ),
        automated=False,
    )

    def _worker():
        """Background-thread worker that runs the agent.

        Wraps the agent invocation in ``asyncio.wait_for(...,
        timeout=_resolve_hard_timeout_sec("act"))`` — the original
        SDK-hang safety net (bugbot caught the missing timeout on
        commit a79bdb4a, High severity).  Augmented post-May 2026
        with an independent watchdog thread (see
        ``_make_agent_worker_watchdog``) that is the
        production-observed backstop for the cases where
        ``asyncio.wait_for`` itself fails to surface the hang —
        Python asyncio cancellation is cooperative and cannot
        interrupt sync I/O wedged inside the SDK / langgraph stack.
        """
        try:
            _run_start_time[0] = time.time()
            _start_watchdog()
            # ``_run_concierge_advisor_agent`` returns a 4-tuple
            # ``(output, token_count, steps_taken, recorded_actions)``.
            # The first three mirror FQM's contract for audit-event
            # counters (bugbot caught discarded counters on commit
            # 411e633b). The fourth — ``recorded_actions`` — is the
            # Approach 1 channel: validated action dicts pushed by
            # ``propose_action`` during the run, in their original
            # ``ConciergeAction``-compatible shape.
            (
                result,
                token_count,
                steps_taken,
                recorded_actions,
            ) = asyncio.run(asyncio.wait_for(
                _run_concierge_advisor_agent(
                    model=model,
                    config=config,
                    service=agent_service,
                    job_id=job_id,
                    tenant_id=tenant_id,
                    surface=surface,
                    user_intent=user_intent,
                    user_context=user_context,
                    vtenant_account=vtenant_account,
                    automated=False,
                    server_name=server_name,
                ),
                timeout=_agents_module._resolve_hard_timeout_sec("act"),
            ))

            # Watchdog race-protection check FIRST — before any
            # KV-touching post-processing.  ``_validate_post_emission``
            # below writes to the KV record (it takes
            # ``system_service`` + ``job_id`` and updates the action
            # set in-place), and the action-recorder rebuild also
            # touches ``result_dict`` derived state.  If the watchdog
            # already aborted the run we want NONE of those side
            # effects to fire; otherwise the watchdog's
            # ``status=error`` write gets silently overwritten by
            # downstream ``_update_agent_job(...complete...)`` and
            # the user-visible failure notification disappears.
            # Bugbot caught the late-check regression on PR #1489
            # cycle 3 (Medium severity); the other five advisors all
            # check ``_watchdog_fired`` immediately after
            # ``asyncio.run`` returns — this brings concierge in line.
            if _watchdog_fired.is_set():
                logger.warning(
                    f"Concierge Advisor worker returned successfully "
                    f"AFTER watchdog abort (job={job_id}); preserving "
                    f"the watchdog's error state — discarding late "
                    f"result without running action-recorder rebuild "
                    f"or post-emission validation."
                )
                return

            # Approach 1 — propose_action is the SOLE source of truth
            # for actions reaching the consent card. The recorder is
            # ALWAYS authoritative: if the agent called ``propose_action``
            # we use that set; if it didn't, ``result.actions`` is wiped
            # and the consent card simply doesn't render. We never fall
            # back to the LLM's free-form structured-output ``actions``
            # because that's the exact path through which hallucinated
            # endpoint paths reach the user.
            #
            # The earlier (PR #1329) implementation had a fallback:
            # "if recorder is empty, trust the LLM's structured output
            # and let _validate_post_emission filter". In production
            # this fallback was the dominant path — the LLM kept
            # emitting hallucinated paths in its structured output
            # WITHOUT calling ``propose_action`` at all, the recorder
            # stayed empty, the fallback engaged, and the user saw
            # invented paths blocked at the consent card with a red
            # banner. The fix is to remove the fallback: empty recorder
            # → empty actions → no consent card → narrative-only
            # response. The user gets a clean "I couldn't find a
            # matching endpoint, please rephrase" outcome instead of
            # a broken proposal.
            llm_emitted_count = len(result.actions or [])
            if recorded_actions:
                try:
                    rebuilt = [ConciergeAction(**a) for a in recorded_actions]
                    logger.info(
                        f"Concierge Advisor: Approach 1 — overwriting "
                        f"result.actions ({llm_emitted_count} LLM-emitted) "
                        f"with {len(rebuilt)} server-recorded action(s) "
                        f"from propose_action for job_id={job_id}"
                    )
                    result.actions = rebuilt  # type: ignore[assignment]
                except Exception as exc:
                    # Recorder rebuild failed — extremely unlikely since
                    # ``propose_action`` already constructed
                    # ``ConciergeAction(**action)`` during validation,
                    # but if a server-side schema migration drifted
                    # under our feet, clear actions rather than serve
                    # stale recorder data with a partial schema.
                    logger.error(
                        f"Concierge Advisor: failed to rebuild actions "
                        f"from recorder for job_id={job_id}: {exc}. "
                        f"Clearing actions (defensive)."
                    )
                    result.actions = []  # type: ignore[assignment]
                    _append_recorder_empty_note_to_trace(
                        result,
                        reason=(
                            f"server-side recorder rebuild failed "
                            f"({type(exc).__name__}); the proposal was "
                            f"discarded to avoid serving an unverified "
                            f"action set."
                        ),
                    )
            else:
                # Recorder is empty — the LLM didn't call
                # ``propose_action`` successfully (or didn't call it at
                # all). Wipe whatever it put in ``result.actions`` so a
                # hallucinated path can't reach the consent card via the
                # legacy fallback. Append a clear narrative note to
                # ``reasoning_trace`` so the chat panel surfaces what
                # happened instead of silently rendering an empty card.
                if llm_emitted_count > 0:
                    logger.warning(
                        f"Concierge Advisor: propose_action recorder is "
                        f"empty but the LLM emitted {llm_emitted_count} "
                        f"action(s) in its structured output for "
                        f"job_id={job_id}. Discarding the LLM-emitted "
                        f"actions — the recorder is the sole source of "
                        f"truth (Approach 1)."
                    )
                else:
                    logger.info(
                        f"Concierge Advisor: propose_action recorder is "
                        f"empty for job_id={job_id} (no actions proposed)."
                    )
                result.actions = []  # type: ignore[assignment]
                if llm_emitted_count > 0:
                    _append_recorder_empty_note_to_trace(
                        result,
                        reason=(
                            f"the agent emitted {llm_emitted_count} "
                            f"action(s) in its structured output but "
                            f"never validated them via propose_action. "
                            f"To prevent hallucinated endpoint paths "
                            f"from reaching the consent card, those "
                            f"actions were discarded. Please rephrase "
                            f"your request, OR ask for a specific "
                            f"endpoint by name (e.g. \"use the "
                            f"ds_monitoring endpoint to disable this "
                            f"data source\")."
                        ),
                    )

            # Post-emission validation — defence-in-depth. Even on the
            # recorded set we re-validate against the LIVE catalog
            # (catalog can drift between propose-time and finalise-time
            # if a handler is hot-reloaded mid-run, however unlikely).
            # When recorder was empty, this runs over an empty
            # ``result.actions`` and is effectively a no-op.
            result = _validate_post_emission(
                result,
                system_service=system_service,
                job_id=job_id,
            )
            # No second watchdog check needed here — the early one
            # right after ``asyncio.run`` already guards against the
            # late-completion race.  Anything past that point is
            # processing a known-good result.
            result_dict = result.model_dump(mode="json")
            _update_agent_job(
                system_service,
                job_id,
                status="complete",
                # Pass the dict directly — ``_update_agent_job`` runs
                # ``json.dumps`` internally for dict inputs and uses
                # ``str`` for string inputs. The pre-serialised string
                # form here was equivalent today but diverged from the
                # canonical FQM (line 1980) / ML (line 2190) pattern.
                # ``result_dict`` is already JSON-safe because
                # ``model_dump(mode="json")`` lowered datetimes /
                # enums / etc. to JSON-encodable types upstream, so no
                # ``default=str`` fallback is needed. Bugbot caught
                # the divergence on commit e68ac5b4 (Low severity).
                result=result_dict,
            )
            _index_agent_event(
                system_service, result_dict, status="complete",
                token_count=token_count, steps_taken=steps_taken,
            )
        except asyncio.TimeoutError:
            if _watchdog_fired.is_set():
                return  # watchdog already wrote the error
            budget_s = _agents_module._resolve_hard_timeout_sec("act")
            elapsed_s = int(time.time() - _run_start_time[0])
            timeout_msg = (
                f"Agent run exceeded {budget_s}s "
                f"(elapsed: {elapsed_s}s) — likely SDK hang in tool-"
                f"aggregation or structured-output extraction"
            )
            logger.error(
                f"Concierge Advisor agent TIMEOUT (job_id={job_id}, "
                f"elapsed={elapsed_s}s): {timeout_msg}"
            )
            _update_agent_job(
                system_service, job_id, status="error", error=timeout_msg
            )
            _index_agent_event(
                system_service, {}, status="error", error_msg=timeout_msg,
            )
        except Exception as exc:
            if _watchdog_fired.is_set():
                return  # watchdog already wrote the error
            err = format_agent_error_chain(exc)
            logger.exception(
                f"Concierge Advisor agent failed: job_id={job_id}, err={err}"
            )
            _update_agent_job(
                system_service,
                job_id,
                status="error",
                error=err,
            )
            _index_agent_event(
                system_service, {}, status="error", error_msg=err,
            )
        finally:
            # Stop the watchdog FIRST so it doesn't race with the
            # release_agent_slot below or fire after we're done.
            _watchdog_stop.set()
            # Pass ``job_id`` — the helper uses it for idempotent slot
            # tracking via ``_released_slots`` so duplicate releases
            # (worker finally + cancel handler racing) don't double-
            # decrement the active-agents counter. Calling without the
            # arg raised a TypeError that the surrounding ``finally``
            # would silently keep going on, but the slot would never
            # release — eventual permanent slot leak. Bugbot caught
            # this on commit 94c5afc3.
            _release_agent_slot(job_id)

    threading.Thread(target=_worker, daemon=True).start()

    return {"job_id": job_id, "status": "running"}

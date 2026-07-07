# coding=utf-8
"""
Describe-payload knowledge block for the Concierge Advisor.

Where the specialist AI Advisors (ML / FLX Threshold / FQM / Feed
Lifecycle / Component Health) handle curated, surface-specific
remediation flows, the **Concierge Advisor** is the generalist:
grounded in the live ``GET /trackme/v2/configuration/api_catalog``
endpoint, it discovers candidate REST endpoints by user intent and
proposes structured action contracts that the consent card renders for
explicit approval.

This module exposes ``build_concierge_knowledge()``, which returns a
dict that callers embed under
``knowledge_reference.concierge_advisor`` in their describe response.
The AI Assistant uses it to:

  1. Recognise when a user's request doesn't match any specialist
     advisor and the Concierge generalist is the right fallback.
  2. Construct a valid ``concierge_invocation`` action-contract.
  3. Defer to specialists when the user's intent matches one of them
     (the assistant playbook below makes this preference explicit).

Plan reference:
``ai-context/integrations/concierge-advisor-implementation-plan.md``.

Runtime documentation lands at
``ai-context/integrations/concierge-advisor.md`` with the agent skeleton
PR (this file is the *static* knowledge channel; the *dynamic* live
state for proposals + executions is the audit-event channel which
flows through the same ``ai_advisor_recent_runs`` lookup the specialist
advisors use, scoped to the new ``concierge`` advisor name).
"""

from __future__ import annotations

import logging
from trackme_libs_logging import get_effective_logger
from typing import Any, Dict, List, Optional, Tuple

# Concierge ships ``system_compatibility`` informationally so the
# decision-tree's step 1 (specialist routing) can self-gate when the
# Splunk runtime can't load the Agent SDK.  See
# ``trackme_libs_describe_ai_advisors`` for the helper's rationale.
# Step 1 of the Concierge decision tree may propose
# ``advisor_invocation`` (specialist) contracts, which DO need
# ``ai_agents_available=true``.  The Concierge's own
# ``concierge_invocation`` chat-direct path is runtime-independent
# and is NOT gated here.
from trackme_libs_describe_ai_advisors import get_ai_runtime_compat


# ---------------------------------------------------------------------------
# Surface model
# ---------------------------------------------------------------------------
#
# The Concierge agent runs on three distinct chat surfaces, each with a
# different set of "what's in session scope" identifiers. Telling the
# LLM ONE rule that's true for all surfaces forced a contradiction
# (Bugbot PR #1389): a rule that's correct for ``vtenants`` is wrong
# for ``entity``, and vice-versa. Threading ``surface`` through the
# describe builder lets each call site emit a tailored knowledge block
# that contains exactly ONE rule — the one that applies — with no
# branches for the LLM to navigate and no contradictions possible.

SURFACE_ENTITY = "entity"
SURFACE_TENANT_HOME = "tenant_home"
SURFACE_VTENANTS = "vtenants"
SURFACE_GLOBAL = "global"

_VALID_SURFACES = frozenset({
    SURFACE_ENTITY,
    SURFACE_TENANT_HOME,
    SURFACE_VTENANTS,
    SURFACE_GLOBAL,
})

# Identifiers whose values are resolvable from chat-session context on
# each surface. The chat panel populates these in
# ``SessionInjectionContext`` (frontend ``conciergeBridge.ts``) and the
# bridge's ``resolveActionBody`` substitutes them at consent time.
# Anything NOT in this tuple for a given surface MUST be a literal
# value the LLM extracts from the user's prompt — emitting
# ``"<session-injected>"`` for an unavailable field fail-closes the
# consent card with *"Some session-injected fields could not be
# resolved"*.
#
#   - entity: full session context (the user opened chat on a single
#     entity row, so tenant + entity identifiers are all in scope).
#   - tenant_home: tenant only (chat scoped to one tenant; no specific
#     entity selected).
#   - vtenants: nothing — the cross-tenant Virtual Tenants page has no
#     single tenant in scope, let alone a single entity.
#   - global: same as vtenants for now (placeholder for a future
#     pan-installation chat surface).
_SESSION_INJECTABLE_BY_SURFACE: Dict[str, Tuple[str, ...]] = {
    SURFACE_ENTITY: ("tenant_id", "object", "object_id", "component"),
    SURFACE_TENANT_HOME: ("tenant_id",),
    SURFACE_VTENANTS: (),
    SURFACE_GLOBAL: (),
}

# The four canonical session-injectable identifier fields. Every
# Concierge surface either does or does not have each of these in
# scope; each surface's allowlist is a subset of this set. Used to
# compute the "literal-required" complement for prompt rendering.
_ALL_SESSION_FIELDS: Tuple[str, ...] = (
    "tenant_id",
    "object",
    "object_id",
    "component",
)


def _validate_surface(surface: str) -> str:
    """Validate the surface identifier and return it for chaining.

    Fail loud at the caller — silently falling back to a default
    (``vtenants`` or ``entity``) on an unknown surface would emit a
    rule that's wrong for the actual chat context, reproducing the
    fail-closed bug this whole module exists to prevent. Raise
    ``ValueError`` so the missing/typo'd surface surfaces in tests
    and dev rather than silently shipping the wrong prompt.
    """
    if surface not in _VALID_SURFACES:
        valid = ", ".join(sorted(_VALID_SURFACES))
        raise ValueError(
            f"Concierge surface must be one of {{{valid}}}; got {surface!r}"
        )
    return surface


def _format_field_list(fields: Tuple[str, ...]) -> str:
    """Render a tuple of field names as a backtick-wrapped list for the
    prompt. Empty tuple renders as ``"(none)"`` so the prompt reads
    naturally for surfaces with no session-injectable identifiers."""
    if not fields:
        return "(none)"
    return ", ".join(f"``{f}``" for f in fields)


# Per-field, human-readable session resolution targets — what each
# session-injectable field RESOLVES to at consent time. Used in the
# body_template renderer to teach the LLM the runtime semantics.
_FIELD_RESOLVES_TO: Dict[str, str] = {
    "tenant_id": "the chat session's tenant_id",
    "object": "the entity's human-readable name",
    "object_id": "the entity's KV ``_key`` hash",
    "component": "the entity's component family (dsm/dhm/...)",
}

# Body-key aliases: REST endpoints sometimes expose ``object_list`` /
# ``keys_list`` (comma-separated string convention for batch ops); the
# bridge resolves these via aliases to ``object`` / ``object_id``.
# Whether the alias is session-injectable on a given surface depends on
# whether its TARGET is — so on ``entity`` both aliases are
# session-injectable; on ``tenant_home`` and ``vtenants`` neither is.
_ALIAS_TARGETS: Dict[str, str] = {
    "object_list": "object",
    "keys_list": "object_id",
}


def _render_body_template_rule(
    surface: str,
    session_injectable: Tuple[str, ...],
    literal_required: Tuple[str, ...],
) -> str:
    """Render the ``body_template`` field's prompt entry for one surface.

    Emits ONE rule per surface — no contradictory branches, no
    conditional reasoning expected from the LLM. Either a field is
    session-injectable on this surface (write
    ``"<session-injected>"``) or it must be a literal (extract from
    user prompt, ask if ambiguous). Aliases follow their target.
    """
    parts: List[str] = [
        "object — JSON body to send. The value semantics for "
        "identifier fields depends on this chat surface "
        f"(``{surface}``):",
    ]

    if session_injectable:
        # Session-injectable on this surface — list each field with its
        # resolution target so the LLM understands what value the
        # frontend will substitute.
        parts.append(
            "\n**Session-injected fields** (emit the literal string "
            "``\"<session-injected>\"`` as the value AND list the "
            "field name in ``session_injected_fields``):"
        )
        for field in session_injectable:
            target = _FIELD_RESOLVES_TO.get(field, "(no resolution)")
            parts.append(f"  - ``{field}`` → resolves to {target}")
        # Aliases for object/object_id are surface-conditional too.
        alias_lines = []
        for alias, target in _ALIAS_TARGETS.items():
            if target in session_injectable:
                alias_lines.append(
                    f"  - ``{alias}`` → ALIAS for ``{target}`` "
                    "(emit ``\"<session-injected>\"``; the bridge "
                    "resolves the alias to a comma-separated string "
                    "for batch endpoints, single-entity here means "
                    "just one value)"
                )
        if alias_lines:
            parts.extend(alias_lines)

    if literal_required:
        # NOT in session scope on this surface — the LLM MUST emit a
        # literal value extracted from the user's prompt, NEVER
        # ``<session-injected>``. Frame the failure mode explicitly so
        # the LLM internalises the consequence.
        parts.append(
            "\n**Literal-required fields** on this surface (NOT in "
            "session scope — DO NOT emit ``\"<session-injected>\"``; "
            "the bridge cannot resolve it and the consent card "
            "fail-closes with *\"Some session-injected fields could "
            "not be resolved\"* + Confirm disabled). Extract the "
            "value from the user's prompt; if the prompt is "
            "ambiguous (no name, multiple candidates), ASK for "
            "clarification BEFORE emitting the contract:"
        )
        for field in literal_required:
            parts.append(f"  - ``{field}`` — emit a literal string")
        # Surface-specific worked example for the most common case.
        if surface == SURFACE_VTENANTS and "tenant_id" in literal_required:
            parts.append(
                "\nExample (this surface): user says *\"delete "
                "tenant demo-fqm\"* → emit "
                "``\"tenant_id\": \"demo-fqm\"`` as a literal in "
                "``body_template``. Do NOT list ``tenant_id`` in "
                "``session_injected_fields``."
            )
        # Aliases follow their literal-required targets.
        alias_lines = []
        for alias, target in _ALIAS_TARGETS.items():
            if target in literal_required:
                alias_lines.append(
                    f"  - ``{alias}`` — ALIAS for ``{target}``; "
                    "emit a literal value (typically a "
                    "comma-separated string for batch endpoints, "
                    "or a single value for one-entity ops)"
                )
        if alias_lines:
            parts.append(
                "\nAlias body keys (follow their literal-required "
                "target on this surface):"
            )
            parts.extend(alias_lines)

    return "\n".join(parts)


def _render_session_injected_fields_rule(
    surface: str,
    session_injectable: Tuple[str, ...],
) -> str:
    """Render the ``session_injected_fields`` array's prompt entry."""
    if not session_injectable:
        return (
            "array<string> — On the ``" + surface + "`` surface this "
            "array MUST be empty. No identifier fields are in session "
            "scope; every identifier in ``body_template`` MUST be a "
            "literal value. Listing any field here on this surface "
            "fail-closes the consent card."
        )
    allowed = _format_field_list(session_injectable)
    # Aliases that follow surface-injectable targets.
    alias_pairs = [
        f"``{alias}`` (alias for ``{target}``)"
        for alias, target in _ALIAS_TARGETS.items()
        if target in session_injectable
    ]
    alias_clause = (
        " Aliases you may also list when the endpoint's body schema "
        "uses them: " + ", ".join(alias_pairs) + "."
        if alias_pairs
        else ""
    )
    return (
        "array<string> — Names of fields whose values the frontend "
        f"will replace at consent time. On the ``{surface}`` surface, "
        f"the allowed list is: {allowed}.{alias_clause} Do NOT add "
        "any field outside this list — the bridge will refuse to "
        "resolve it and the consent card fail-closes."
    )


def _render_alias_body_keys_rule(
    surface: str,
    session_injectable: Tuple[str, ...],
) -> str:
    """Render the catalog-entry guidance for ``object_list`` /
    ``keys_list`` aliases. The aliases follow their canonical
    targets — if ``object``/``object_id`` is session-injectable on
    this surface, so is the alias; otherwise the alias is
    literal-required.

    The rendered text now also enforces two cross-cutting rules
    that hold on every surface:

      1. **Mutual exclusivity** — ``object_list`` and ``keys_list``
         are alternates in every TrackMe REST handler that exposes
         them ("either object_list or keys_list must be provided").
         Emitting BOTH in the same action contract is wasteful and
         frequently fail-closes the consent card when one is a
         literal and the other is a placeholder. Pick exactly one.

      2. **Prefer ``keys_list``** — the entity's KV ``_key`` is the
         immutable internal identifier; the human-readable
         ``object`` name can change (rename, alias edits). Routing
         actions through ``_key`` avoids race conditions and stays
         correct under entity rename.

    Bug history: PRD2 observed live (May 2026) the LLM emitting BOTH
    ``object_list`` (literal entity name) AND ``keys_list``
    (``<session-injected>``) in the same ``ds_monitoring`` disable
    action. Belt-and-braces reasoning by the LLM — but the bridge
    couldn't resolve the placeholder because of an unrelated session
    edge case, the consent card fail-closed with *"Some session-
    injected fields could not be resolved"*, and the user had to
    Edit body manually. Adding explicit mutual-exclusivity +
    preference rules to the prompt removes the ambiguity and the
    fail-closed UX path.
    """
    object_injectable = "object" in session_injectable
    object_id_injectable = "object_id" in session_injectable

    # Cross-surface preamble — same regardless of whether the
    # aliases resolve via session-injection or literal values on
    # this surface.
    preamble = (
        "**Mutual exclusivity (HARD RULE)** — "
        "``object_list`` and ``keys_list`` are ALTERNATES in every "
        "TrackMe REST handler that exposes them (the handler's "
        "describe text reads *\"either object_list or keys_list "
        "must be provided\"*). Emit EXACTLY ONE of them per action; "
        "NEVER emit both. Emitting both is wasteful (handler picks "
        "one and ignores the other) and frequently fail-closes the "
        "consent card when one is a literal and the other is a "
        "placeholder.\n\n"
        "**Preference order (HARD RULE)** — the entity's KV ``_key`` "
        "is immutable; the human-readable ``object`` name can "
        "change (rename, alias edits). Routing actions through "
        "``_key`` avoids race conditions and stays correct under "
        "entity rename. So when the endpoint's ``body_keys`` lists "
        "BOTH ``object_list`` and ``keys_list`` AND the ``_key`` is "
        "available in your context (the chat session's "
        "``object_id`` on the ``entity`` surface, or a ``_key`` "
        "value the user supplied / a previous discovery step "
        "retrieved), prefer ``keys_list``. Use ``object_list`` "
        "when EITHER (a) the endpoint exposes ``object_list`` but "
        "NOT ``keys_list``, OR (b) only the entity NAME is "
        "available and resolving the ``_key`` first would require "
        "an extra discovery step the request doesn't justify. The "
        "rule is a preference, not a forbid — picking "
        "``object_list`` when the ``_key`` genuinely isn't "
        "available is correct, not a violation.\n\n"
    )

    if object_injectable and object_id_injectable:
        # Entity surface — both aliases are session-injectable; the
        # bridge resolves the placeholder to the right session value
        # at consent time. Apply the mutual-exclusivity + preference
        # rules above, then emit ``<session-injected>`` for the ONE
        # alias chosen.
        return (
            preamble
            + "On the ``" + surface + "`` surface, the chosen "
            "alias's value MUST be the literal string "
            "``\"<session-injected>\"`` (NOT a JSON list, NOT the "
            "actual entity name). The frontend bridge resolves "
            "``object_list`` to the entity name and ``keys_list`` "
            "to the entity's KV ``_key`` from chat session context "
            "at consent time. Apply the preference rule above: "
            "prefer ``keys_list`` when both are catalog options."
        )
    # Tenant_home / vtenants / global — neither alias is in scope
    # for session-injection. Apply the same mutual-exclusivity +
    # preference rules, then emit a literal value extracted from
    # the user's prompt.
    return (
        preamble
        + "On the ``" + surface + "`` surface, the chosen alias's "
        "value MUST be a LITERAL value extracted from the user's "
        "prompt — do NOT emit ``\"<session-injected>\"``. Their "
        "session targets (``object`` / ``object_id``) are not in "
        "scope on this surface; emitting the placeholder would "
        "fail-close the consent card. ``object_list`` is "
        "conventionally a comma-separated string of entity names "
        "(or a single name for one-entity ops); ``keys_list`` is "
        "the same shape but for entity ``_key`` hashes. Apply the "
        "preference rule above: prefer ``keys_list`` when both are "
        "catalog options and the user's prompt supplies the "
        "``_key`` (or you can derive it via a discovery step). If "
        "the prompt only supplies the entity name, ``object_list`` "
        "with the literal name is correct. If the prompt is "
        "ambiguous about which entity / entities, ASK for "
        "clarification before emitting the contract."
    )


def _render_identifier_sourcing_hard_rule(
    surface: str,
    session_injectable: Tuple[str, ...],
    literal_required: Tuple[str, ...],
) -> str:
    """Render ``hard_rules[0]`` — identifier sourcing — for one surface.

    Promoted to first hard rule because picking the wrong source for an
    identifier is the #1 reason a Concierge proposal lands with
    Confirm disabled (PR #1389).
    """
    if not session_injectable:
        # Vtenants / global: every identifier is literal-required.
        return (
            f"Identifier sourcing on the ``{surface}`` chat surface — "
            "this is the #1 reason a Concierge proposal lands with "
            "Confirm disabled, so read it carefully:\n"
            "  - NO identifier is in session scope on this surface. "
            f"Every identifier ({_format_field_list(literal_required)}) "
            "MUST be a literal value extracted from the user's "
            "prompt. NEVER emit ``\"<session-injected>\"`` for any "
            "identifier field on this surface; the bridge cannot "
            "resolve it.\n"
            "  - If the user's prompt is ambiguous about an "
            "identifier (no name, multiple candidates), ASK for "
            "clarification BEFORE emitting the contract — do not "
            "guess."
        )
    if not literal_required:
        # Entity: every identifier is session-injectable.
        return (
            f"Identifier sourcing on the ``{surface}`` chat surface — "
            "this is the #1 reason a Concierge proposal lands with "
            "Confirm disabled, so read it carefully:\n"
            "  - Every identifier "
            f"({_format_field_list(session_injectable)}) IS in "
            "session scope on this surface. Use the literal string "
            "``\"<session-injected>\"`` in ``body_template`` AND list "
            "the field in ``session_injected_fields``. NEVER "
            "construct the identifier yourself — the bridge "
            "substitutes the real value at consent time."
        )
    # Mixed (tenant_home): some session-injectable, some literal.
    return (
        f"Identifier sourcing on the ``{surface}`` chat surface — "
        "this is the #1 reason a Concierge proposal lands with "
        "Confirm disabled, so read it carefully:\n"
        f"  - Session-injectable fields "
        f"({_format_field_list(session_injectable)}): use "
        "``\"<session-injected>\"`` AND list in "
        "``session_injected_fields``. The bridge substitutes at "
        "consent time.\n"
        f"  - Literal-required fields "
        f"({_format_field_list(literal_required)}): NOT in session "
        "scope on this surface. Extract the value from the user's "
        "prompt and emit a literal. NEVER emit "
        "``\"<session-injected>\"`` for these — the bridge cannot "
        "resolve it and the consent card fail-closes.\n"
        "  - If the prompt is ambiguous about a literal-required "
        "identifier, ASK for clarification BEFORE emitting the "
        "contract."
    )


def _concierge_action_contract_schema(surface: str):
    """Return the JSON-schema-style description of ``concierge_invocation``.

    Embedded in the knowledge block so the chat LLM has the exact
    shape it must emit when proposing a Concierge action. The
    specialist advisors use a different contract
    (``advisor_invocation``); this one supports the multi-action
    flow specific to Concierge.

    The ``surface`` parameter (required) selects the rule variant for
    identifier sourcing — see ``_SESSION_INJECTABLE_BY_SURFACE``. Each
    caller knows its own surface from its describe-builder context;
    the describe block ships with exactly ONE rule, no LLM-side
    branching.
    """
    _validate_surface(surface)
    session_injectable = _SESSION_INJECTABLE_BY_SURFACE[surface]
    literal_required = tuple(
        f for f in _ALL_SESSION_FIELDS if f not in session_injectable
    )
    return {
        "format": (
            "When proposing a Concierge action, end your prose response "
            "with a fenced ``` ```json `` block carrying a "
            "``concierge_invocation`` object. The frontend parses the "
            "fenced block, validates it against this schema, and renders "
            "a consent card with one row per proposed action. Each row "
            "shows the resolved request body BEFORE firing — the user "
            "always sees what will be sent."
        ),
        "shape": {
            "concierge_invocation": {
                "intent_summary": (
                    "string — One-line restatement of the user's intent. "
                    "Shown as the consent card title. Should read naturally "
                    "to the user, e.g. 'Increase priority to critical for "
                    "entity dsm:mytracker:foo'."
                ),
                "actions": [
                    {
                        "endpoint_path": (
                            "string — Full REST path. **MUST be copied "
                            "byte-for-byte from one of the "
                            "``endpoints_catalog.entries[].path`` values "
                            "shown later in this knowledge block.** Do "
                            "NOT construct the path from intuition or "
                            "from training-data patterns; do NOT copy "
                            "the path shown as an example in any "
                            "docstring (those are illustrative only — "
                            "the live catalog is the only authoritative "
                            "source of valid paths). When the agent "
                            "runtime exposes ``discover_endpoints`` / "
                            "``describe_endpoint`` MCP tools you may "
                            "use them to navigate the catalog; in the "
                            "chat-direct emission path those tools are "
                            "not available, so ``endpoints_catalog`` is "
                            "your only ground truth. Illustrative shape "
                            "(do NOT use this string verbatim — it is "
                            "shown only to teach the URL form): "
                            "``/services/trackme/v2/<resource_group>/<endpoint_name>``."
                        ),
                        "method": (
                            "string — HTTP verb in lowercase: "
                            "``get`` / ``post`` / ``put`` / ``delete``. "
                            "MUST match the ``method`` field of the "
                            "``endpoints_catalog`` entry whose ``path`` "
                            "matches the chosen ``endpoint_path``. "
                            "Mismatches are rejected by the consent "
                            "card with a 'method does not match catalog' "
                            "error."
                        ),
                        "body_template": _render_body_template_rule(
                            surface, session_injectable, literal_required,
                        ),
                        "session_injected_fields": _render_session_injected_fields_rule(
                            surface, session_injectable,
                        ),
                        "danger_level": (
                            "string — One of ``read`` / ``write-low`` / "
                            "``write-high`` / ``destructive``. MUST "
                            "match the ``danger_level`` field of the "
                            "matching ``endpoints_catalog`` entry — do "
                            "NOT downgrade to make a write action seem "
                            "safer than it is. The backend post-emission "
                            "validator drops actions whose ``danger_level`` "
                            "diverges from the catalog."
                        ),
                        "rbac_required": (
                            "string — Splunk capability the endpoint "
                            "requires (``trackmeuseroperations`` / "
                            "``trackmepoweroperations`` / "
                            "``trackmeadminoperations``). MUST match "
                            "the ``rbac`` field of the matching "
                            "``endpoints_catalog`` entry."
                        ),
                        "rationale": (
                            "string — One short paragraph explaining why "
                            "this endpoint matches the user's intent. The "
                            "consent card surfaces this so the analyst can "
                            "judge the proposal before approving."
                        ),
                    }
                ],
                "consent_required": (
                    "boolean — MUST be ``true``. The frontend rejects any "
                    "Concierge contract without it. There is no autonomous "
                    "execution path."
                ),
                "suggested_reason": (
                    "string — Short overall summary shown above the per-"
                    "action breakdown on the consent card."
                ),
            },
        },
        "hard_rules": [
            _render_identifier_sourcing_hard_rule(
                surface, session_injectable, literal_required,
            ),
            (
                "Every action requires explicit user consent. "
                "``consent_required: true`` on every proposal. The "
                "frontend rejects contracts without it. There is no "
                "auto-fire mode."
            ),
            (
                "Use ``read_via_endpoint`` to verify state before "
                "proposing a write. ``Does the entity exist? What's its "
                "current value? Is the action a no-op?`` If a write would "
                "be a no-op (priority is already critical, ack already "
                "active), say so in prose and don't propose the action."
            ),
            (
                "When the user's intent matches a SPECIALIST advisor "
                "(ML / FLX Threshold / FQM / Feed Lifecycle / Component "
                "Health), propose the SPECIALIST'S action-contract "
                "(``advisor_invocation``), NOT a Concierge invocation. "
                "Specialists carry curated remediation logic and audit "
                "categorisation that a generic REST call can't replicate. "
                "Concierge is for the long tail."
            ),
            (
                "Cap multi-action proposals at "
                "``ai_concierge_max_actions_per_proposal`` (per-tenant "
                "config, default 10). For larger batches, ask the user "
                "to confirm a sample first, then propose subsequent "
                "batches in follow-up turns."
            ),
            (
                "``destructive``-tagged actions get an extra confirmation "
                "step in the consent card (the user types the entity name "
                "to confirm). Don't try to bypass — the UX is intentional."
            ),
        ],
    }


def _concierge_advisor_catalog_entry():
    """Return the catalog entry for the Concierge advisor.

    Same shape as the specialist advisor entries in
    ``trackme_libs_describe_ai_advisors._full_advisor_catalog`` but
    semantically different: Concierge has no fixed component / mode
    matrix — it operates over the entire REST API.
    """
    return {
        "name": "Concierge Advisor",
        "purpose": (
            "Generalist agent that handles user requests that don't match "
            "one of the specialist advisors. Grounded in the full TrackMe "
            "REST API catalog (~200 endpoints) via the "
            "``GET /trackme/v2/configuration/api_catalog`` endpoint and "
            "``trackmeapiautodocs.py`` self-documentation. Discovers "
            "candidate endpoints by user intent, verifies state via read-"
            "endpoints, and proposes structured action contracts that the "
            "consent card renders for explicit approval. Mutation is the "
            "consent click — the agent has no write tool at the SDK level."
        ),
        "use_cases": [
            "Acknowledge alerts inline ('ack this entity for 2 hours')",
            "Update priority / tags / SLA ('increase priority to critical for X')",
            "Bulk operations ('apply tag pci-scope to all entities matching Y')",
            "Discovery ('what endpoint do I use to disable monitoring on Z?')",
            "Status queries ('show me entities in red state across my tenants')",
            "Configuration tweaks (variable delay, lagging classes, blocklist)",
            "Anything else that's not ML / FLX threshold / FQM / Feed Lifecycle / Component Health-shaped",
        ],
        "tools_available": {
            "discover_endpoints": (
                "Search the API catalog by intent keywords. Filters by "
                "current chat surface (entity / tenant_home / vtenants / "
                "global), HTTP verb (read / write), and the caller's "
                "RBAC capabilities. Returns ranked candidates."
            ),
            "describe_endpoint": (
                "Fetch the full self-documentation block for one path "
                "(required/optional params, body shape, examples, danger "
                "level, RBAC requirement). Use after ``discover_endpoints`` "
                "narrows to 2-3 finalists."
            ),
            "read_via_endpoint": (
                "Actually exercise a read-tagged endpoint to verify state "
                "before proposing a write. The tool refuses to call write/"
                "destructive paths — defence in depth on top of the "
                "SDK-level allowlist."
            ),
            "propose_action": (
                "Emit a ``concierge_invocation`` contract for the consent "
                "card. The agent's only 'mutation' surface — but it does "
                "NOT execute. Mutation is the consent-card click."
            ),
        },
        "no_mutation_tools": (
            "By design, the Concierge agent has zero MCP tools that mutate "
            "state. The SDK allowlist only includes ``concierge_read``-"
            "tagged tools. Mutation flows through the consent card → "
            "frontend → REST path, gated by the user's explicit click."
        ),
        "tenant_configuration": {
            "max_actions": "ai_concierge_max_actions_per_proposal (default 10)",
            "rate_limit": "ai_concierge_rate_limit_per_minute (default 5)",
            "authorisation_note": (
                "There is no per-tenant enablement gate or destructive-action gate. "
                "Splunkd RBAC at the REST boundary determines which catalog endpoints "
                "the user can fire — if the user lacks the capability, the consent-card "
                "click 403s. Destructive actions additionally require per-action typed "
                "confirmation in the consent card; that's the UX safeguard."
            ),
        },
        "rest_endpoints": {
            "start": "POST /services/trackme/v2/ai_concierge_advisor/concierge_advisor",
            "status": "GET /services/trackme/v2/ai_concierge_advisor/concierge_advisor_status",
            "cancel": "DELETE /services/trackme/v2/ai_concierge_advisor/concierge_advisor_cancel",
        },
        "audit_sourcetype_pattern": (
            "trackme:ai_agent:concierge_advisor:propose — every contract emitted "
            "(whether the user later confirms or rejects). "
            "trackme:ai_agent:concierge_advisor:execute — every action that "
            "actually fires post-consent."
        ),
    }


def _concierge_assistant_playbook():
    """Return the assistant playbook for the Concierge generalist.

    Distinct from the specialist-family playbook in
    ``trackme_libs_describe_ai_advisors`` — Concierge needs its own
    decision tree because it's a generalist and the choice rules are
    different (when does the assistant prefer a specialist vs. dropping
    into Concierge?).
    """
    return {
        # First rule the model evaluates — comes BEFORE ``role`` and
        # ``decision_tree`` because both contain unconditional directives
        # to "propose the specialist (``advisor_invocation`` contract)"
        # (``role`` clause (a); ``when_NOT_to_propose[1]``).  Without this
        # top-level rule, the model could absorb those directives and
        # surface an unrunnable specialist consent card on a Python 3.9
        # / Splunk 9.x deployment before reaching the per-step gate in
        # ``decision_tree[0]``.
        #
        # IMPORTANT scope: this rule gates the specialist
        # ``advisor_invocation`` proposal path ONLY.  The Concierge's own
        # ``concierge_invocation`` chat-direct path is runtime-independent
        # (frontend ``executeConcierge`` resolves it via a direct
        # ``splunkdFetch`` to the named REST endpoint, no
        # ``splunklib.ai`` involvement) and stays available on every
        # supported runtime.  See the mirror rule in
        # ``trackme_libs_describe_ai_advisors`` for the full architectural
        # rationale.
        "runtime_compatibility_rule": (
            "BEFORE following any directive in ``role`` or "
            "``decision_tree`` that would route to a specialist via "
            "an ``advisor_invocation`` contract (ML / Feed Lifecycle / "
            "FLX Threshold / FQM / Component Health), check "
            "``system_compatibility.ai_agents_available`` at the top "
            "of this knowledge block.  If that flag is **false**, the "
            "Splunk Agent SDK is unavailable on this deployment and "
            "the specialist cannot launch — you MUST NOT emit an "
            "``advisor_invocation`` JSON block on this surface.  This "
            "overrides ``role`` clause (a) and "
            "``when_NOT_to_propose[1]`` (which both unconditionally "
            "favour specialist routing) and short-circuits "
            "``decision_tree`` step 1, dropping you straight into "
            "step 2 (chat-direct ``concierge_invocation`` REST "
            "endpoint match), which is unaffected by the runtime "
            "gate.  Chat-direct ``concierge_invocation`` remains "
            "fully available — propose it whenever the user's intent "
            "matches a REST endpoint in ``endpoints_catalog``.  Tell "
            "the user once (per conversation, not per turn) that the "
            "specialist would normally handle their case but requires "
            "``system_compatibility.required_splunk_release``; you "
            "can still execute direct-REST Concierge actions for the "
            "long tail.  When ``ai_agents_available`` is **true**, "
            "ignore this rule entirely and follow ``role`` / "
            "``decision_tree`` / ``when_NOT_to_propose`` as written."
        ),
        "role": (
            "You are the user's conversational interface to the entire "
            "TrackMe REST API. When a user describes an action, you "
            "either (a) recognise it matches a specialist advisor and "
            "propose the specialist (``advisor_invocation`` contract), "
            "(b) recognise it matches a known REST endpoint via the "
            "Concierge tool surface and propose a ``concierge_invocation`` "
            "contract, or (c) acknowledge you can't fulfil the request "
            "and explain why. Always retain explicit user consent — every "
            "mutation goes through the consent card click, never autonomous "
            "execution."
        ),
        "decision_tree": [
            {
                "step": 1,
                "question": (
                    "Does the user's intent match a SPECIALIST advisor? "
                    "(ML model issues, FLX threshold tuning, FQM dictionary "
                    "calibration, Feed Lifecycle for DSM/DHM, Component "
                    "Health for WLK/MHM.)"
                ),
                "action": (
                    "Propose the specialist's ``advisor_invocation`` "
                    "contract. Specialists carry curated remediation "
                    "logic and audit categorisation. Do NOT use Concierge "
                    "as a substitute for a specialist. "
                    "(``runtime_compatibility_rule`` at the top of this "
                    "playbook supersedes this step when "
                    "``system_compatibility.ai_agents_available`` is "
                    "false — fall through to step 2 in that case.)"
                ),
            },
            {
                "step": 2,
                "question": (
                    "Otherwise, is there a plausible TrackMe REST endpoint "
                    "for this? Search ``endpoints_catalog.entries`` (below "
                    "in this knowledge block) for intent keywords in "
                    "``description`` / ``path`` / ``body_keys`` / "
                    "``resource_group``. When a ``feature_context`` hint "
                    "is present, prefer entries whose ``resource_group`` "
                    "matches it as a tie-breaker."
                ),
                "action": (
                    "Pick the SINGLE best matching catalog entry and "
                    "build the ``concierge_invocation`` contract by "
                    "copying ``path``, ``method``, ``danger_level``, and "
                    "``rbac`` byte-for-byte from that entry, and "
                    "constructing the ``body_template`` only from the "
                    "entry's ``body_keys``. NEVER invent a path or body "
                    "key that is not in the catalog — if the closest "
                    "match is approximate, ask the user to confirm "
                    "intent rather than emitting a fabricated contract. "
                    "Note: agent-SDK runtimes (NOT the chat-direct path) "
                    "expose MCP tools (``discover_endpoints`` / "
                    "``describe_endpoint`` / ``read_via_endpoint`` / "
                    "``propose_action``) for richer navigation; from "
                    "the chat surface these tools are NOT available — "
                    "``endpoints_catalog`` is your only ground truth."
                ),
            },
            {
                "step": 3,
                "question": (
                    "If neither a specialist nor a discovered endpoint "
                    "matches, the request is out of scope."
                ),
                "action": (
                    "Tell the user honestly what TrackMe can and can't "
                    "do here. Suggest workarounds (manual UI navigation, "
                    "raising a feature request) where reasonable."
                ),
            },
        ],
        "imperative_emission": (
            "If your prose proposes a Concierge action — phrasings like "
            "'I can update priority for you', 'Let me ack that entity', "
            "'I'll add the tag' — you MUST end your response with a "
            "fenced ```json block carrying the ``concierge_invocation`` "
            "contract. Without the structured block, the consent card "
            "doesn't render and the proposal is non-actionable. The "
            "closing ``` is the LAST thing in your response — do NOT "
            "write any explanation, summary, capability note, or "
            "consent-card description AFTER the closing ```. The "
            "consent card UI surfaces all of that automatically from "
            "the structured contract; trailing prose after the JSON "
            "block confuses the parser and the user sees the raw JSON "
            "in the chat bubble instead of the rendered card. The same "
            "imperative-emission rule applies as for the specialist "
            "advisors (see PR #1293 for the lesson)."
        ),
        "when_NOT_to_propose": [
            (
                "User is asking a general question about TrackMe concepts. "
                "Answer with knowledge from the describe payload, no contract."
            ),
            (
                "User's intent matches a specialist advisor (ML / FLX / FQM / "
                "Feed Lifecycle / Component Health) — propose the specialist, "
                "not Concierge."
            ),
            (
                "``enable_ai_assistant=0`` on the system. Don't propose "
                "anything that calls advisor REST endpoints."
            ),
            (
                "The user hasn't been specific enough to determine the "
                "right endpoint. ASK first — don't guess."
            ),
            (
                "A write would be a no-op (current state already matches "
                "desired state). Tell the user, don't propose."
            ),
        ],
        "consent_loop_property": (
            "The Concierge agent is read-only at the SDK level. Mutation "
            "happens through the consent-card click, controlled by the "
            "user. This is the architectural safety property: even if "
            "the agent picks the wrong endpoint or constructs a "
            "malformed body, the user sees the resolved request BEFORE it "
            "fires. Worst case: a wasted click. There is no path for the "
            "agent to mutate state without the user explicitly clicking "
            "Confirm on the consent card."
        ),
    }


def _build_endpoints_catalog_summary(
    splunkd_uri: Optional[str],
    session_key: Optional[str],
) -> List[Dict[str, Any]]:
    """Project the live API catalog to a compact LLM-friendly summary.

    The chat LLM that emits ``concierge_invocation`` action-contracts
    runs as a streaming Anthropic / OpenAI call (no MCP tools); the
    only way it learns the catalog is through the describe payload it
    receives as context. Without this projection the LLM falls back
    to its training data and fabricates plausible-looking paths
    (``ds_update_dsm`` / ``ds_update_monitored_state`` / etc.) — paths
    that don't exist in the live API. The catalog gate at the consent
    card catches the hallucination, but the user-visible UX is
    "agent failed: invented path". Embedding the catalog here grounds
    the LLM with the real path universe before it writes its
    response.

    The full catalog row (path + describe block + options + parameters
    + SPL example + curl example) is ~1.3KB per endpoint × 423
    endpoints ≈ 556KB, far too much to embed wholesale. This helper
    projects each row to a compact 7-tuple shape:

        {
            "path": "/services/trackme/v2/splk_dsm/write/ds_monitoring",
            "method": "post",
            "danger_level": "write-low",
            "description": "Disable / enable monitoring on a DSM entity",
            "body_keys": ["object_list", "keys_list", "action"],
            "rbac": "trackmepoweroperations",
            "resource_group": "splk_dsm/write",
        }

    Per-endpoint cost: ~150 chars ≈ 40 tokens. 423 endpoints ≈ 17K
    tokens — adds about 1× the existing chat prompt size, which is
    acceptable given Claude / GPT-4 context windows of 200K+. Token
    cost buys the LLM the full path universe to reason about; without
    it, every catalog-grounded chat call is a roll of the dice.

    ``resource_group`` is the canonical group string from the catalog
    (e.g. ``"licensing"``, ``"maintenance"``, ``"maintenance_kdb"``,
    ``"bank_holidays/admin"``). Surfaced so the per-feature
    ``feature_context`` hint (when set on the ``"global"`` surface) can
    instruct the LLM to prefer entries whose ``resource_group`` matches
    the active feature page when the user's intent overlaps multiple
    groups. Without this field the hint had nothing to filter against
    (bugbot HIGH on PR #1409).

    Uses ``build_catalog_as_list_cached`` so the catalog itself is a
    sub-second filesystem read after the first call (PR #1329).
    Returns an empty list on any infrastructure failure — the chat
    keeps working without the grounding section, which is strictly
    better than failing the describe build over a missing
    optimisation.
    """
    if not splunkd_uri or not session_key:
        return []

    try:
        from trackme_libs_autodocs_catalog_builder import (
            build_catalog_as_list_cached,
        )
        rows = build_catalog_as_list_cached(
            splunkd_uri=splunkd_uri,
            session_key=session_key,
            target="endpoints",
        )
    except Exception as exc:
        get_effective_logger().warning(
            f"_build_endpoints_catalog_summary: catalog fetch failed "
            f"({type(exc).__name__}: {exc}); chat LLM grounding section "
            f"will be omitted"
        )
        return []

    if not isinstance(rows, list):
        return []

    # Resolve the danger-level helper ONCE before the loop. The earlier
    # shape did the import inside the per-row body, which paid the
    # module-cache hit ~423 times per call (cheap on success but
    # produces 423 try/except cycles if the import fails). Bugbot
    # caught this on PR #1337 cycle 2 (Low severity). Pull it up so
    # the import runs at most once per call.
    try:
        from trackme_libs_autodocs_catalog import (
            infer_danger_level as _infer_danger_level,
        )
    except Exception as exc:
        get_effective_logger().warning(
            f"_build_endpoints_catalog_summary: failed to import "
            f"infer_danger_level ({type(exc).__name__}: {exc}); falling "
            f"back to write-high (matches the helper's own Rule 6 fail-"
            f"safe — never under-classify)."
        )
        _infer_danger_level = None

    summary: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # ``resource_api`` carries the path WITHOUT the leading ``/``
        # (catalog convention). Normalise to the consent-card-friendly
        # ``/services/trackme/v2/...`` form so the LLM can copy-paste
        # directly into its action contract without further mangling.
        resource_api = row.get("resource_api") or ""
        path = (
            f"/{resource_api.lstrip('/')}"
            if resource_api
            else ""
        )
        if not path:
            continue
        method = (row.get("resource_mode") or "").lower() or "post"
        # ``resource_describe`` carries the per-endpoint describe block
        # (post-PR #1333 canonical shape: ``describe`` /
        # ``resource_desc`` / ``resource_spl_example`` / ``options``).
        # Body keys come from ``options[0]`` — catalog-builder
        # convention; if the endpoint takes no body, ``options`` is
        # empty or missing and we project an empty list.
        describe_block = row.get("resource_describe") or {}
        if not isinstance(describe_block, dict):
            describe_block = {}
        options = describe_block.get("options") or []
        body_keys: List[str] = []
        if isinstance(options, list) and options:
            first = options[0]
            if isinstance(first, dict):
                body_keys = sorted(str(k) for k in first.keys())
        # Inferred danger_level from the catalog helper. Without
        # ``danger_level``, the LLM might downgrade a write action to
        # appear safer than it is — bake the inference into the
        # projection so the chat sees the same classification the
        # consent card uses.
        #
        # ``function_name`` is REQUIRED by the helper's Rule 2 — it
        # matches destructive name patterns (``delete_*`` /
        # ``destroy_*`` / ``purge_*`` / ``decommission_*``) on POST
        # endpoints that delete data. Omitting it causes destructive
        # POSTs to slip through the heuristic and land as
        # ``write-low``, which contradicts the safety property above.
        # Bugbot caught the missing arg on PR #1337 cycle 1 (Medium).
        #
        # Per-row fallback (when the helper itself raises) defaults to
        # ``write-high`` for non-GET methods, matching
        # ``infer_danger_level`` Rule 6's fail-safe — "un-classified
        # endpoints get the strictest sane tier". The previous
        # ``write-low`` fallback was a real safety regression: a
        # DELETE / destructive-named POST / admin-group endpoint
        # whose helper call raised would silently downgrade to
        # ``write-low``, bypassing the consent card's per-action
        # extra-confirmation flow for destructive actions. Bugbot
        # caught this on PR #1337 cycle 2 (Medium).
        if _infer_danger_level is None:
            danger_level = "write-high" if method != "get" else "read"
        else:
            try:
                danger_level = _infer_danger_level(
                    method=method,
                    resource_group=row.get("resource_group") or "",
                    function_name=row.get("python_function") or "",
                )
            except Exception:
                danger_level = "write-high" if method != "get" else "read"

        # ``resource_desc`` is the canonical 1-line summary (post-PR
        # #1333). Some legacy rows may lack it; fall back to the
        # longer ``describe`` field if present.
        description = (row.get("resource_desc") or "").strip()
        if not description:
            description = str(describe_block.get("describe") or "").strip()
        # Cap the description so the projection stays compact even when
        # a handler ships a multi-paragraph describe block. The LLM
        # only needs the gist for endpoint selection; full details are
        # available via the live catalog endpoint when needed.
        if len(description) > 240:
            description = description[:237] + "..."

        # RBAC inference. The catalog builder does NOT surface
        # restmap.conf's ``capability`` / ``capability.<method>``
        # declarations directly — that data lives in the conf file,
        # not in the per-handler describe response. We approximate it
        # from the resource group + method, matching the convention
        # used across the codebase's restmap entries:
        #
        #   - groups ending in ``/admin`` → ``trackmeadminoperations``
        #   - GET methods on non-admin groups → ``trackmeuseroperations``
        #   - all other methods (including ``destructive``) →
        #     ``trackmepoweroperations``
        #
        # This is advisory for the LLM (helps it construct the
        # ``rbac_required`` field in a Concierge action contract);
        # splunkd enforces actual authorization at call time, so a
        # mis-inferred rbac doesn't bypass any security boundary.
        # Bugbot caught the missing field on PR #1337 cycle 3 (Medium)
        # — the docstring promised ``rbac`` but the projection emitted
        # 5 fields, leaving the LLM to guess at the contract level.
        resource_group_str = row.get("resource_group") or ""
        if "/admin" in resource_group_str:
            rbac = "trackmeadminoperations"
        elif method == "get":
            rbac = "trackmeuseroperations"
        else:
            rbac = "trackmepoweroperations"

        summary.append({
            "path": path,
            "method": method,
            "danger_level": danger_level,
            "description": description,
            "body_keys": body_keys,
            "rbac": rbac,
            "resource_group": resource_group_str,
        })

    # Sort by path for stable ordering across runs (LLM caching
    # benefits from stable input). Sub-second cost on 423 entries.
    summary.sort(key=lambda e: (e["path"], e["method"]))
    return summary


def _concierge_endpoint_quirks():
    """Per-endpoint operational notes the LLM needs to call certain
    catalog entries correctly. The static endpoint describe is the
    source of truth (and is shipped to the LLM via
    ``describe_endpoint``), but a few endpoints have natural-language
    →request-shape gotchas where the LLM consistently picks the wrong
    field unless told explicitly. List those here.

    Add a new entry only when:
      * The mistake has been observed in production (or a user has
        reported it).
      * The fix is "use parameter X instead of parameter Y" — too
        narrow to live in the global playbook.
      * The endpoint's own ``describe`` block has been updated to
        match (so single-source-of-truth is preserved between this
        knowledge block and the catalog the agent reads through
        ``describe_endpoint``).
    """
    return {
        "labels_assign": {
            "endpoint": "POST /services/trackme/v2/labels/write/assign_labels",
            "rule": (
                "When the user names a label in natural language ('assign "
                "the label business to this entity', 'mark this as blocked', "
                "etc.), pass the human-readable name(s) under ``label_names`` "
                "— NOT under ``label_ids``. ``label_ids`` is the catalog's "
                "internal ``_key`` field (a 24-character hex string like "
                "``69fdb92b973cb921e40b9a24``); passing a name there returns "
                "HTTP 400 ``invalid label_ids: [<name>]``. The endpoint "
                "auto-creates any name that isn't yet in the catalog (with "
                "a neutral grey colour and a placeholder description) so "
                "you do NOT need to chain a separate ``create_label`` "
                "call first. Reserve ``label_ids`` for the case where "
                "you've already pulled the catalog via ``get_labels`` and "
                "have the actual ``_key`` strings."
            ),
            "example_correct": {
                "tenant_id": "<tenant>",
                "object_id": "<entity-keyid>",
                "component": "dsm",
                "label_names": ["business"],
            },
            "example_incorrect": {
                "tenant_id": "<tenant>",
                "object_id": "<entity-keyid>",
                "component": "dsm",
                "label_ids": ["business"],
                "_why_incorrect": (
                    "'business' is a name, not a ``_key``. The endpoint "
                    "validates ``label_ids`` against the catalog's "
                    "``_key`` index and 400s. Use ``label_names`` instead."
                ),
            },
        },
        "blocklist_add": {
            "endpoint": "POST /services/trackme/v2/splk_blocklist/write/blocklist_add",
            "rule": (
                "TERM-COLLISION GOTCHA: ``object_category`` on this "
                "endpoint is a DISPATCH KEY — it names WHICH field on "
                "the entity record the ``object`` pattern should match "
                "against. It is NOT the global TrackMe "
                "``object_category`` enum you see on every other "
                "endpoint (which takes values like ``splk-dsm`` / "
                "``splk-dhm`` / ``splk-mhm`` / ``splk-flx`` / "
                "``splk-fqm`` / ``splk-wlk``). On THIS endpoint the "
                "valid dispatch-key values are:\n"
                "\n"
                "  - ``object`` — match the entity's full identifier "
                "as displayed in the entity list (e.g. ``main:syslog`` "
                "for DSM, ``host1.example.com`` for DHM, the saved-"
                "search name for WLK). THIS IS THE COMMON CASE; pick "
                "it whenever the operator names the entities by the "
                "identifier visible in the UI.\n"
                "  - ``sourcetype`` — match the entity's Splunk "
                "sourcetype field. Use ONLY when the operator says "
                "'all entities of sourcetype X' or 'sourcetype=X'. "
                "Does NOT apply to DSM entities NAMED "
                "``<index>:<sourcetype>`` (those are matched as "
                "``object``).\n"
                "  - ``index`` — match the entity's Splunk index "
                "field. Use ONLY when the operator says 'block "
                "everything in index X' or 'index=X'.\n"
                "  - ``alias`` — match the entity's alias field. Use "
                "ONLY when the operator says 'block entities with "
                "alias X'.\n"
                "  - ``metric_category`` / ``group`` / ``app`` / any "
                "tenant-custom field present on the entity record — "
                "advanced; use only when the operator names that "
                "field explicitly.\n"
                "\n"
                "HARD RULE: when the operator references entities by "
                "the string they see in the entity list (e.g. "
                "``os:@all``, ``os:bandwidth``, ``main:syslog``), the "
                "answer is ALWAYS ``object_category='object'``. NEVER "
                "default to ``'sourcetype'`` when uncertain — that's "
                "the exact failure mode observed in production: the "
                "LLM picked ``sourcetype`` because the term sounded "
                "plausible, the row got created against the wrong "
                "field, and the operator saw an 'accepted but inert' "
                "blocklist that matched nothing. When in doubt, ask "
                "the operator rather than guess.\n"
                "\n"
                "Note that ``component`` on this endpoint is a "
                "separate parameter and DOES take the usual TrackMe "
                "component values (``dsm`` / ``dhm`` / ``mhm`` / "
                "``flx`` / ``fqm`` / ``wlk``) — same as elsewhere. "
                "The term collision is ONLY on ``object_category``."
            ),
            "example_correct": {
                "tenant_id": "<tenant>",
                "component": "dsm",
                "object_category": "object",
                "object": "^os(?!:@all$)",
                "comment": "Block os* entities except os:@all",
            },
            "example_incorrect": {
                "tenant_id": "<tenant>",
                "component": "dsm",
                "object_category": "sourcetype",
                "object": "^os(?!:@all$)",
                "_why_incorrect": (
                    "The operator referenced entities by their UI "
                    "identifier (``os:@all``, ``os:bandwidth``), so "
                    "the match needs to run against the entity's "
                    "``object`` field — not its ``sourcetype`` field. "
                    "Picking ``sourcetype`` creates a valid record "
                    "that matches zero entities (the entities' "
                    "sourcetype is NOT ``os`` — that's part of their "
                    "object NAME). Use ``object_category='object'`` "
                    "instead."
                ),
            },
        },
    }


def build_concierge_knowledge(
    splunkd_uri: Optional[str] = None,
    session_key: Optional[str] = None,
    surface: Optional[str] = None,
    feature_context: Optional[str] = None,
):
    """Return the Concierge advisor knowledge block.

    Callers embed this dict under
    ``knowledge_reference.concierge_advisor`` in their describe response.
    Available in every describe surface where the Concierge agent is
    addressable (entity / tenant_home / vtenants / global), gated only
    by per-tenant configuration at the agent-launch path.

    Args:
        splunkd_uri: Optional splunkd management URI. When provided
            together with ``session_key``, the function fetches the
            live API catalog (via the version-keyed filesystem cache
            from PR #1329) and embeds a compact endpoint summary in
            the returned block under ``endpoints_catalog``. Without
            this, the chat LLM falls back to training-data guesses
            for endpoint paths and frequently fabricates ones that
            don't exist.
        session_key: Optional Splunk session token. Same usage as
            ``splunkd_uri``. Both must be provided to enable the
            grounding section.
        surface: REQUIRED — one of ``"entity"`` / ``"tenant_home"`` /
            ``"vtenants"`` / ``"global"``. Selects the per-surface
            identifier-sourcing rule rendered into the action contract
            schema and the hard rules. Defaulted to ``None`` for
            transitional callers but raises ``ValueError`` when omitted
            — the prompt cannot be rendered without knowing which
            surface ships it. See ``_SESSION_INJECTABLE_BY_SURFACE``
            for the per-surface allowlists. PR #1389 (bugbot) — a
            single shared describe block carrying surface-conditional
            language inside the prompt produced contradictions; the
            structural fix is to render exactly ONE rule per surface
            at the call site.
        feature_context: Optional resource-group hint for the
            ``surface="global"`` feature pages (Maintenance Mode /
            Maintenance KDB / Bank Holidays / Backup & Restore /
            License / REST API Reference). When set, the returned
            block carries a ``feature_context`` field that tells the
            LLM "the user is currently on the X page; when their intent
            maps to several resource groups in the catalog, prefer X".
            The hint is advisory — the user can still ask for things
            outside the active feature, and the LLM should answer those
            normally rather than refusing. Recommended values mirror
            the ``trackmeapiautodocs.py`` resource-group strings
            (``"licensing"``, ``"backup_and_restore"``, ``"maintenance"``,
            ``"maintenance_kdb"``, ``"bank_holidays"``,
            ``"rest_api_reference"``). Ignored on entity / tenant_home /
            vtenants surfaces — those are cross-feature by design and
            don't need a scope hint.

    Shape is stable — additional fields can be added without renaming
    existing keys (the AI Assistant system prompts that consume this
    block reference the keys by name).
    """
    if surface is None:
        raise ValueError(
            "build_concierge_knowledge: ``surface`` is required. "
            "Pass one of: " + ", ".join(sorted(_VALID_SURFACES)) + "."
        )
    _validate_surface(surface)
    session_injectable = _SESSION_INJECTABLE_BY_SURFACE[surface]
    block: Dict[str, Any] = {
        # Informational only on the Concierge surface — the
        # ``concierge_invocation`` chat-direct path is runtime-independent
        # and is NOT blocked when ``ai_agents_available`` is false.  The
        # decision-tree's step 1 (specialist routing) self-gates on this
        # struct so a Concierge-only surface (License / Maintenance /
        # Backup & Restore / REST API Reference — none of which include
        # ``build_ai_advisor_knowledge`` in their describe payload) still
        # has the runtime data it needs to skip an unrunnable specialist
        # ``advisor_invocation`` proposal and fall through to step 2's
        # direct-REST match instead.
        "system_compatibility": get_ai_runtime_compat(),
        "overview": (
            "The Concierge Advisor is the generalist member of the AI "
            "Advisor family. Where the specialists (ML / FLX Threshold / "
            "FQM / Feed Lifecycle / Component Health) handle curated "
            "remediation flows for specific surfaces, the Concierge "
            "handles the long tail of user requests by grounding itself "
            "in the live TrackMe REST API catalog (via "
            "``GET /trackme/v2/configuration/api_catalog`` and "
            "``trackmeapiautodocs.py``). It discovers candidate endpoints "
            "by user intent, verifies state via read-endpoints, and "
            "proposes structured action contracts that the consent card "
            "renders for explicit approval. The agent is read-only at the "
            "SDK level; mutation flows through the consent-card click, "
            "controlled by the user."
        ),
        "hard_rule_zero_catalog_grounding": (
            "BEFORE you read anything else in this knowledge block: every "
            "``endpoint_path`` you ever emit in a ``concierge_invocation`` "
            "action contract MUST be a byte-for-byte copy of one of the "
            "``path`` strings listed in ``endpoints_catalog.entries`` "
            "below. There are NO exceptions. Do NOT construct paths from "
            "training-data patterns. Do NOT copy any path that appears as "
            "an example or illustration in a docstring or schema field "
            "(those are explanatory only — they are NOT in the catalog "
            "and the consent card WILL flag them as hallucinations). Do "
            "NOT pluralise / singularise / re-case a real path. Do NOT "
            "synthesise a 'logical' admin-prefixed variant unless the "
            "exact admin path is in the catalog. If no catalog entry "
            "matches the user's intent, tell the user honestly that the "
            "operation is not exposed via the REST API and stop — do not "
            "emit a ``concierge_invocation`` with a fabricated path. The "
            "consent card validates every emitted path against this same "
            "catalog and disables the Confirm-and-run button when the "
            "path is absent (rendered with a red 'agent likely "
            "hallucinated this path' banner). A hallucinated path is a "
            "wasted proposal that erodes user trust in the assistant."
        ),
        "advisor": _concierge_advisor_catalog_entry(),
        "action_contract": _concierge_action_contract_schema(surface),
        "assistant_playbook": _concierge_assistant_playbook(),
        "endpoint_quirks": _concierge_endpoint_quirks(),
        "chat_surface": surface,
        "rest_audit_trail": {
            "summary_index": (
                "trackme_summary (or whatever the tenant's "
                "``trackme_summary_idx`` overrides)"
            ),
            "sourcetype_proposal": "trackme:ai_agent:concierge_advisor:propose",
            "sourcetype_execution": "trackme:ai_agent:concierge_advisor:execute",
            "key_fields": [
                "_time", "advisor", "intent_summary", "action_index",
                "total_actions", "endpoint_path", "method", "danger_level",
                "rbac_required", "tenant_id", "caller_user", "caller_roles",
                "status", "duration_ms", "error", "chat_session_id",
                # ``provider_name`` matches the field name actually
                # emitted by every advisor's ``_index_agent_event``
                # (FQM 1266, ML 1905/2123, Component Health 866/1106,
                # FLX Threshold 613/807, Feed Lifecycle 662/868). The
                # earlier ``"provider"`` shorthand listed here was a
                # one-off that diverged from the canonical contract —
                # caught alongside the missing field in the audit
                # event itself.
                "model", "provider_name",
            ],
            "spl_example_proposal": (
                'search index=trackme_summary '
                'sourcetype="trackme:ai_agent:concierge_advisor:propose" '
                'tenant_id=<tenant> | sort -_time | head 10'
            ),
            "spl_example_execution": (
                'search index=trackme_summary '
                'sourcetype="trackme:ai_agent:concierge_advisor:execute" '
                'tenant_id=<tenant> | stats count by status, danger_level'
            ),
        },
    }

    # Live API catalog projection — only when the caller threaded
    # ``splunkd_uri`` + ``session_key`` through. This is the
    # authoritative path universe the chat LLM should pick from when
    # constructing a ``concierge_invocation`` action contract.
    endpoints_catalog = _build_endpoints_catalog_summary(
        splunkd_uri, session_key,
    )
    # Feature-context hint — only meaningful on ``surface="global"`` where
    # the chat is bound to a feature page (Maintenance KDB, License, etc).
    # The cross-feature surfaces (entity / tenant_home / vtenants) skip
    # this block. The hint nudges endpoint selection toward the active
    # feature's resource group when the user's intent matches several;
    # it is advisory and should not block off-topic intents.
    #
    # Gated on ``endpoints_catalog`` being available — the hint references
    # ``endpoints_catalog`` entries and the per-entry ``resource_group``
    # field, both of which only exist when the catalog projection
    # succeeded. Without this gate, an infrastructure failure (catalog
    # fetch raised, missing credentials, etc) would ship the LLM a
    # describe block telling it to filter against catalog data that
    # isn't in its context — nonsensical instruction. With the gate,
    # the LLM transparently falls back to its un-grounded behaviour
    # (which is at least internally consistent).
    if feature_context and endpoints_catalog:
        block["feature_context"] = {
            "active_feature": feature_context,
            "describe": (
                "The user is currently viewing the "
                f"``{feature_context}`` feature page. When the user's "
                "intent maps to multiple resource groups in "
                "``endpoints_catalog``, prefer entries whose "
                "``resource_group`` matches this value — match either "
                f"exactly (``{feature_context}``) or as a slash-prefix "
                f"(``{feature_context}/admin``) to capture the admin-"
                "scoped variant of the same group. Do NOT refuse or "
                "redirect requests that fall outside the active "
                "feature — answer those normally. The hint is a "
                "tie-breaker, not a filter."
            ),
        }

    if endpoints_catalog:
        block["endpoints_catalog"] = {
            "describe": (
                "Compact projection of the live TrackMe REST API "
                "catalog (~423 endpoints). Each entry has 7 fields: "
                "``path``, ``method``, ``danger_level``, "
                "``description`` (a 1-line summary), ``body_keys`` "
                "(the body parameter keys the endpoint accepts), "
                "``rbac`` (the role/capability required to call the "
                "endpoint), and ``resource_group`` (the canonical "
                "group string used by the ``feature_context`` "
                "tie-breaker hint when a feature page is active). "
                "This is the AUTHORITATIVE source of truth for "
                "Concierge action contracts: every ``endpoint_path`` "
                "you emit in a ``concierge_invocation`` MUST be "
                "copied verbatim from one of these entries. Body "
                "keys in your ``body_template`` MUST come from the "
                "entry's ``body_keys`` list — do not invent keys "
                "based on intuition. The catalog is rebuilt only "
                "when the app version changes, so this listing is "
                "current as of the last app deploy."
            ),
            "hard_rule": (
                "Every ``endpoint_path`` in a ``concierge_invocation`` "
                "MUST be a byte-for-byte copy of one of the ``path`` "
                "values in ``entries`` below. Every ``method`` MUST "
                "match the corresponding entry's ``method`` (lowercase). "
                "Every body key in your ``body_template`` MUST come "
                "from that entry's ``body_keys`` list (modulo the "
                "session-injected aliases listed in "
                "``session_injected_body_keys``). Every "
                "``danger_level`` MUST match the entry's "
                "``danger_level`` and every ``rbac_required`` MUST "
                "match the entry's ``rbac``. NO exceptions — do NOT "
                "construct a path from training-data patterns, do NOT "
                "copy a path shown as an example in any docstring "
                "(those are illustrative only and are NOT in this "
                "catalog), do NOT guess a 'logical' admin/power "
                "variant of a real path. If the user's intent doesn't "
                "match any entry, say so honestly and stop — DO NOT "
                "fabricate a path that 'would make sense'. The consent "
                "card validates every emitted path against this same "
                "catalog at render time and disables the Confirm "
                "button when the path is absent (with a red 'agent "
                "likely hallucinated this path' banner). The backend "
                "post-emission validator does the same on the agent-"
                "SDK runtime path. A hallucinated path is a wasted "
                "proposal that erodes user trust in the assistant."
            ),
            "session_injected_body_keys": _render_alias_body_keys_rule(
                surface, session_injectable,
            ),
            "entries": endpoints_catalog,
            "count": len(endpoints_catalog),
        }

    return block

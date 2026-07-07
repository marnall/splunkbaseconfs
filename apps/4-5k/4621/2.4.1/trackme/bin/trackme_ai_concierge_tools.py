"""
TrackMe AI Agents — Concierge Advisor MCP tools.

Four tools, all tagged ``concierge_read`` so the agent's allowlist
(``LocalToolSettings(allowlist=ToolAllowlist(tags=["concierge_read"]))``)
permits exactly these and rejects everything else. The Concierge
agent has zero write tools at the SDK level — that's the structural
safety property. Mutation is the consent-card click, never the
agent's direct action.

The four tools:

  1. ``discover_endpoints(intent_keywords, surface_filter, verb_filter, top_n)``
     — Search the TrackMe REST API catalog by intent. Returns ranked
     candidates with path, method, danger level, and a one-line
     description. Filters by current chat surface (``entity`` /
     ``tenant_home`` / ``vtenants`` / ``global``) and HTTP verb
     (``read`` / ``write`` / ``any``).

  2. ``describe_endpoint(path)``
     — Fetch the full ``describe=true`` block for one endpoint:
     parameters, body shape, examples, danger level, RBAC requirement.
     Used after ``discover_endpoints`` narrows to 2-3 finalists.

  3. ``read_via_endpoint(path, query, body)``
     — Actually exercise a GET endpoint to verify state before
     proposing a write. Refuses to call paths that aren't
     read-classified — defence in depth on top of the SDK's tag
     allowlist (which already excludes write tools, but a future
     mis-tagged endpoint shouldn't accidentally execute via this
     tool).

  4. ``propose_action(intent_summary, actions, rationale)``
     — Emit a structured proposal contract. Validates the action
     shape (path exists in the catalog, danger level matches,
     session-injected fields are from the allowlist, body templates
     carry the placeholder for protected fields) and returns a
     receipt dict. Does NOT execute. The agent's ``actions_taken``
     log records what was proposed. The actual mutation flows
     through the consent-card click → frontend → REST.

Plan reference:
``ai-context/integrations/concierge-advisor-implementation-plan.md``.
"""

import contextvars
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from typing import Any, Dict, List, Optional

from splunklib.ai.registry import ToolContext

# Shared registry / helpers from the existing AI agent tool module.
# Keeping the registry single ensures all advisor tools are served
# through the same ``tools.py`` MCP entry point.
from trackme_ai_agent_tools import (
    registry,
    _get_trackme_service,
    _call_trackme_api,
)

# Pure helpers from PR #1310. The agent uses these to filter / rank
# the live catalog returned by ``GET /configuration/api_catalog``.
from trackme_libs_autodocs_catalog import (
    CatalogEntry,
    DANGER_DESTRUCTIVE,
    DANGER_LEVELS,
    DANGER_READ,
    SURFACES,
    SURFACE_GLOBAL,
    VERB_ANY,
    VERB_READ,
    VERB_WRITE,
    filter_catalog,
    format_condensed,
    infer_danger_level,
    infer_surface,
    project_catalog_row_to_entry,
    rank_by_intent,
)

# Named logger — shares the singleton configured by the parent
# REST handler's setup_logger() call (root logger redirect there means
# `logging.<level>(...)` here would bleed across handlers).
logger = logging.getLogger("trackme.rest.ai.concierge_advisor")


# ---------------------------------------------------------------------------
# Internal helpers (not exposed as tools)
# ---------------------------------------------------------------------------


# Soft cap on entries returned by ``discover_endpoints``. The agent
# typically narrows to 2-3 finalists and drills into them with
# ``describe_endpoint``; surfacing more than this is just token waste.
_DISCOVER_MAX_TOP_N = 25
_DISCOVER_DEFAULT_TOP_N = 10


# ---------------------------------------------------------------------------
# Server-side action recorder (Approach 1 — propose_action is the sole
# source of truth for actions reaching the consent card)
# ---------------------------------------------------------------------------
#
# The Splunk Agent SDK emits the agent's tool calls and structured output
# along two INDEPENDENT generation paths. Even after ``propose_action``
# validates a clean action set against the catalog, the LLM is free to
# emit a different (hallucinated) ``actions`` list in its final
# ``ConciergeProposalResult``. ``_validate_post_emission`` and the
# frontend catalog gate filter those out, but the user still sees a
# failed proposal — the LLM "got away with" emitting fictional paths.
#
# This module-level ContextVar holds a per-run recorder list that
# ``_run_concierge_advisor_agent`` installs BEFORE ``agent.run()`` and
# tears down AFTER. ``propose_action``, on validation success, replaces
# the recorder's contents with the validated action dicts. After the
# agent run completes, the composer in ``_run_concierge_advisor_agent``
# uses the recorder as the AUTHORITATIVE source of ``result.actions``,
# overwriting whatever the LLM put in its structured output.
#
# Net effect: hallucinated paths CANNOT reach the consent card because
# the consent card sees only ``propose_action`` recordings — the LLM's
# free-form ``actions`` field is ignored. If the LLM forgets to call
# ``propose_action``, no actions render and the chat bubble shows the
# narrative-only response.
#
# Design choice — replace, not append. The LLM may call ``propose_action``
# multiple times to refine; only the LAST validated set counts. This
# matches the system-prompt contract: each call represents the FINAL
# action set the agent wants the user to see. The ``recorder.clear()``
# before ``recorder.extend()`` enforces that semantics.
#
# Contextvar is the right primitive: each agent run lives in its own
# worker thread (``_worker``) which calls ``asyncio.run(...)`` to drive
# the SDK. ``ContextVar.set(...)`` before ``asyncio.run()`` is inherited
# by tasks in the new event loop, so ``propose_action`` (an async tool)
# sees the recorder. After ``asyncio.run()`` returns, the recorder
# (a list, mutated in-place) carries the final validated set — the
# ContextVar token reset is a hygiene step that doesn't affect data flow.
_proposed_actions_recorder: "contextvars.ContextVar[Optional[List[Dict[str, Any]]]]" = (
    contextvars.ContextVar("trackme_concierge_proposed_actions_recorder", default=None)
)


def install_proposed_actions_recorder(
    recorder: List[Dict[str, Any]],
) -> "contextvars.Token":
    """Install a per-run recorder that ``propose_action`` will populate.

    Called by ``_run_concierge_advisor_agent`` BEFORE ``agent.run()``.
    The recorder is a mutable list — ``propose_action`` calls
    ``recorder.clear() + recorder.extend(validated)`` on each successful
    validation, so the agent runner's reference reflects the latest
    proposal once ``agent.run()`` returns.

    Returns a ``Token`` the caller MUST pass to
    ``uninstall_proposed_actions_recorder`` in a ``finally`` block to
    avoid recorder leakage across nested runs (defensive — there's no
    nested-run path today).
    """
    return _proposed_actions_recorder.set(recorder)


def uninstall_proposed_actions_recorder(token: "contextvars.Token") -> None:
    """Tear down the recorder installed by ``install_proposed_actions_recorder``.

    Idempotent — calling with a token that's already been consumed (or
    that doesn't match the current context) is a no-op. Python raises
    different exceptions depending on the failure mode:

      * ``RuntimeError`` — the token has already been used once
        (``ContextVar.reset`` enforces single-use). This happens when
        a caller's ``finally`` runs twice (e.g. nested error paths).
      * ``ValueError`` — the token is from a different ``ContextVar``.
        Defensive against future refactors that might confuse tokens.
      * ``LookupError`` — the contextvar was never set in this context.

    Swallowing all three keeps the cleanup path safe; by the time this
    runs the recorder data has already been consumed by the composer
    so there's nothing left to clean up.
    """
    try:
        _proposed_actions_recorder.reset(token)
    except (RuntimeError, ValueError, LookupError):
        pass


def _fetch_full_catalog(service) -> List[CatalogEntry]:
    """Fetch the live REST API catalog and convert to ``CatalogEntry`` list.

    Calls ``GET /trackme/v2/configuration/api_catalog`` (the endpoint
    introduced in PR #1313). Each catalog row is the ``describe=true``
    block from one handler method, plus a ``resource_group`` /
    ``python_function`` / ``resource_mode`` annotation.

    We map each row into a ``CatalogEntry`` with:
      - ``path`` from ``resource_api`` (the catalog endpoint already
        prefixes ``services/...``).
      - ``method`` from ``resource_mode``.
      - ``danger_level`` inferred via ``infer_danger_level``.
      - ``surface`` inferred via ``infer_surface``.
      - ``description`` from ``resource_desc``.
      - ``capability`` not currently emitted by the autodocs catalog —
        left empty; the read-time RBAC filter relies on the caller's
        session and the splunkd-enforced authz at the boundary.

    Errors are logged and the offending row is skipped — partial
    catalogs are more useful than no catalog when one handler
    misbehaves. Same fail-soft pattern the catalog endpoint already
    applies on the server side.
    """
    response = _call_trackme_api(
        service,
        "trackme/v2/configuration/api_catalog",
        body={"target": "endpoints"},
        method="get",
    )

    if isinstance(response, dict) and response.get("error"):
        logger.error(
            f"_fetch_full_catalog: api_catalog endpoint returned error: "
            f"{response.get('error')}"
        )
        return []

    entries_raw = []
    if isinstance(response, dict):
        entries_raw = response.get("entries") or []

    # Single source of truth for the row → entry projection lives in
    # ``project_catalog_row_to_entry`` (in
    # ``trackme_libs_autodocs_catalog``). Both this function AND the
    # post-emission validator in
    # ``trackme_libs_ai_concierge_advisor._validate_post_emission`` go
    # through the helper, so a future schema tweak (new field, different
    # ``options`` shape, normalisation change) lands in one place and
    # the two consumers cannot drift. Bugbot caught the duplication on
    # PR #1321.
    entries: List[CatalogEntry] = []
    for row in entries_raw:
        entry = project_catalog_row_to_entry(row)
        if entry is not None:
            entries.append(entry)

    return entries


def _entry_for_path(entries: List[CatalogEntry], path: str) -> Optional[CatalogEntry]:
    """Find a catalog entry by path. Tolerant of leading-slash variance."""
    if not path:
        return None
    candidates = [path, path.lstrip("/"), f"/{path.lstrip('/')}"]
    for candidate in candidates:
        for entry in entries:
            if entry.path == candidate:
                return entry
    return None


# ---------------------------------------------------------------------------
# Tool 1: discover_endpoints
# ---------------------------------------------------------------------------


@registry.tool(tags=["concierge_read"])
async def discover_endpoints(
    ctx: ToolContext,
    intent_keywords: str,
    surface_filter: str = "",
    verb_filter: str = "any",
    resource_group: str = "",
    top_n: int = 10,
) -> str:
    """
    Search the TrackMe REST API catalog by intent keywords.

    Returns ranked candidate endpoints with path, method, danger level,
    one-line description, and resource group.

    **Recommended flow:** scope FIRST with ``list_resource_groups`` →
    pick a group → call this tool with ``resource_group=<name>`` to
    rank within ~15 endpoints instead of the whole 423-endpoint
    catalog. The lexical match has fewer false positives in a narrow
    scope. The full-catalog mode (``resource_group=""``) is still
    available for cross-group exploration.

    Args:
        intent_keywords: Free-text user intent. Tokenised lowercase
            and split on non-alphanumeric. e.g. ``"increase priority
            to critical"`` matches catalogue entries with ``priority``,
            ``critical``, etc. in their path / resource_group /
            function_name / description.
        surface_filter: Restrict to one chat surface. One of
            ``"entity"`` / ``"tenant_home"`` / ``"vtenants"`` /
            ``"global"``. Empty string (default) means no surface
            filter. ``"entity"`` is a subset of ``"tenant_home"``
            (every entity-tagged endpoint is visible from a
            tenant_home chat); ``global`` endpoints are visible
            from every non-empty surface.
        verb_filter: ``"read"`` (only read-classified endpoints) /
            ``"write"`` (write-low / write-high / destructive) /
            ``"any"`` (default). Driven off the catalog's
            ``danger_level`` classification, NOT the HTTP method —
            so a POST endpoint that's read-tagged still matches
            ``verb=read``.
        resource_group: Restrict to one umbrella group from
            ``list_resource_groups``. e.g. ``"splk_dsm"`` matches
            endpoints in ``splk_dsm`` AND its sub-groups
            (``splk_dsm/write``, ``splk_dsm/admin``). Empty string
            (default) means no group filter — search across the
            whole catalog. Strongly recommended for action queries:
            scope to the group the user's intent maps to (DSM
            entities → ``splk_dsm``, FQM dictionaries →
            ``splk_fqm``, etc.) before keyword-ranking.
        top_n: Maximum candidates to return. Default 10, hard cap 25.

    Returns:
        JSON string with the ranked candidate list. Each entry has
        ``path`` / ``method`` / ``resource_group`` / ``danger_level``
        / ``description`` / ``function_name``. Sorted by descending
        keyword-match score.

        On empty / invalid input the response carries an ``error``
        key and an empty ``entries`` list — the agent should treat
        this as "no candidates found" and either ask the user to
        clarify or fall back to a general response.
    """
    # Validate inputs and normalise.
    intent = (intent_keywords or "").strip()
    if not intent:
        return json.dumps({
            "error": "intent_keywords is required",
            "entries": [],
        })

    surface = (surface_filter or "").strip().lower() or None
    if surface is not None and surface not in SURFACES:
        return json.dumps({
            "error": (
                f"invalid surface_filter={surface_filter!r}, valid: "
                f"{sorted(SURFACES) + ['(empty for no filter)']}"
            ),
            "entries": [],
        })

    verb = (verb_filter or VERB_ANY).strip().lower()
    if verb not in (VERB_READ, VERB_WRITE, VERB_ANY):
        return json.dumps({
            "error": (
                f"invalid verb_filter={verb_filter!r}, valid: "
                f"{[VERB_READ, VERB_WRITE, VERB_ANY]}"
            ),
            "entries": [],
        })

    rg = (resource_group or "").strip().lower() or None
    top_n_capped = max(1, min(int(top_n), _DISCOVER_MAX_TOP_N))

    service = _get_trackme_service(ctx)
    entries = _fetch_full_catalog(service)
    if not entries:
        return json.dumps({
            "error": "could not load API catalog",
            "entries": [],
        })

    filtered = filter_catalog(
        entries,
        surface=surface,
        verb_filter=verb if verb != VERB_ANY else None,
        resource_group=rg,
    )
    ranked = rank_by_intent(filtered, intent, top_n=top_n_capped)

    return json.dumps({
        "intent": intent,
        "surface_filter": surface or "(none)",
        "verb_filter": verb,
        "resource_group_filter": rg or "(none)",
        "candidate_count": len(ranked),
        "entries": [
            {
                "path": entry.path,
                "method": entry.method,
                "resource_group": entry.resource_group,
                "danger_level": entry.danger_level,
                "description": entry.description,
                "function_name": entry.function_name,
            }
            for entry in ranked
        ],
    }, default=str)


# ---------------------------------------------------------------------------
# Tool 1b: list_resource_groups (helper for tool 1)
# ---------------------------------------------------------------------------


@registry.tool(tags=["concierge_read"])
async def list_resource_groups(
    ctx: ToolContext,  # noqa: ARG001 — tool signature requires ctx
) -> str:
    """
    Return the curated TrackMe REST API resource-groups map.

    Step 1 of the Concierge agent's discovery checklist. The map is
    hand-curated in
    ``trackme_libs_describe_rest_api_reference._build_knowledge_reference``
    — the same knowledge the REST API Reference page's AI Assistant
    uses. Each entry has:

      - ``name``: Display name (e.g. "Data Source Monitoring (DSM)")
      - ``description``: Plain-English summary of what the group
        manages, including the verbs the group supports (enable,
        disable, update, delete, query, etc.).
      - ``base_path``: REST path prefix
        (e.g. ``"/services/trackme/v2/splk_dsm"``).
      - ``sub_groups``: Optional list of sub-groups
        (e.g. ``["splk_dsm", "splk_dsm/write"]``).

    The agent's first task on any user-action request is to map the
    intent to a single resource group from this list. The descriptions
    are written to make this a one-shot read. Once the group is
    chosen, the agent narrows discovery via ``discover_endpoints
    (intent_keywords=..., resource_group=<chosen>)`` or fetches the
    full group manifest via ``list_endpoints_in_group``.

    Returns:
        JSON string mirroring the curated map verbatim. The list is
        small (~30 entries × ~3 lines each) so the agent always has
        the bird's-eye view in token budget.
    """
    try:
        from trackme_libs_describe_rest_api_reference import get_resource_groups_map
        groups_map = get_resource_groups_map()
    except Exception as exc:
        return json.dumps({
            "error": f"could not load resource groups map: {exc}",
            "groups": {},
        })

    return json.dumps({
        "groups": groups_map,
        "group_count": len(groups_map),
        "hint": (
            "Pick exactly one group whose description matches the "
            "user's action intent. Then call discover_endpoints with "
            "resource_group=<key> to rank within that group, OR "
            "list_endpoints_in_group(<key>) for the full group "
            "manifest. NEVER skip group selection and rank against "
            "the whole catalog — it produces false positives."
        ),
    }, default=str)


# ---------------------------------------------------------------------------
# Tool 1c: list_endpoints_in_group
# ---------------------------------------------------------------------------


@registry.tool(tags=["concierge_read"])
async def list_endpoints_in_group(
    ctx: ToolContext,
    resource_group: str,
    surface_filter: str = "",
    verb_filter: str = "any",
) -> str:
    """
    List every endpoint inside one resource group, with body schema.

    Step 2 of the Concierge agent's discovery checklist (after
    ``list_resource_groups`` picked a group). Returns the full
    manifest of endpoints in the group, each carrying:

      - ``path`` / ``method`` / ``danger_level`` / ``description``
      - ``body_parameters``: Authoritative map of body keys the
        endpoint accepts (same field ``describe_endpoint`` surfaces).
        Sourced from the handler's ``raw_describe.options[0]``.

    The agent picks one endpoint from the manifest and proceeds
    directly to ``propose_action`` — no separate
    ``describe_endpoint`` round-trip needed. The body_parameters
    inline saves a tool call when the agent has confidence in its
    pick, but the agent MAY still call ``describe_endpoint`` for the
    full describe-block (``raw_describe`` includes per-parameter
    descriptions, examples, etc.) when the choice is non-obvious.

    Args:
        resource_group: Group key from ``list_resource_groups``
            (e.g. ``"splk_dsm"``, ``"splk_priority_policies"``,
            ``"splk_fqm"``). Sub-groups are auto-included
            (``"splk_dsm"`` matches ``"splk_dsm/write"`` and
            ``"splk_dsm/admin"``).
        surface_filter: Optional, same as ``discover_endpoints``.
        verb_filter: Optional, same as ``discover_endpoints``.

    Returns:
        JSON string with the manifest. ``entries`` is the full
        endpoint list (no top_n cap — group manifests are bounded
        at ~15 endpoints, well within token budget).

        On unknown group: ``{"error": "...", "available_groups": [...]}``
        — the hint helps the agent recover from a typo.
    """
    rg = (resource_group or "").strip().lower()
    if not rg:
        return json.dumps({
            "error": "resource_group is required",
            "entries": [],
        })

    surface = (surface_filter or "").strip().lower() or None
    if surface is not None and surface not in SURFACES:
        return json.dumps({
            "error": (
                f"invalid surface_filter={surface_filter!r}, valid: "
                f"{sorted(SURFACES) + ['(empty for no filter)']}"
            ),
            "entries": [],
        })

    verb = (verb_filter or VERB_ANY).strip().lower()
    if verb not in (VERB_READ, VERB_WRITE, VERB_ANY):
        return json.dumps({
            "error": (
                f"invalid verb_filter={verb_filter!r}, valid: "
                f"{[VERB_READ, VERB_WRITE, VERB_ANY]}"
            ),
            "entries": [],
        })

    service = _get_trackme_service(ctx)
    entries = _fetch_full_catalog(service)
    if not entries:
        return json.dumps({
            "error": "could not load API catalog",
            "entries": [],
        })

    filtered = filter_catalog(
        entries,
        surface=surface,
        verb_filter=verb if verb != VERB_ANY else None,
        resource_group=rg,
    )

    if not filtered:
        # Build a typo-recovery hint from the live catalog's group
        # set. Cheaper than re-importing the curated map and gives
        # the agent the actual groups present in *this* deployment.
        available = sorted({entry.resource_group for entry in entries})
        return json.dumps({
            "error": (
                f"no endpoints found in resource_group={resource_group!r}"
                f"{f' (after surface_filter={surface!r})' if surface else ''}"
                f"{f' (after verb_filter={verb!r})' if verb != VERB_ANY else ''}"
            ),
            "available_groups": available,
            "hint": (
                "Use list_resource_groups to see the curated group "
                "names. Bare prefix-match is NOT supported (e.g. "
                "'splk' does not match 'splk_dsm') — use the exact "
                "group key."
            ),
            "entries": [],
        })

    return json.dumps({
        "resource_group": rg,
        "surface_filter": surface or "(none)",
        "verb_filter": verb,
        "endpoint_count": len(filtered),
        "entries": [
            {
                "path": entry.path,
                "method": entry.method,
                "resource_group": entry.resource_group,
                "danger_level": entry.danger_level,
                "description": entry.description,
                "function_name": entry.function_name,
                # Body schema inline — saves a separate
                # describe_endpoint round-trip when the agent is
                # confident in its pick. The set is sorted for
                # deterministic output.
                "body_parameters": sorted(entry.body_parameters),
            }
            for entry in filtered
        ],
    }, default=str)


# ---------------------------------------------------------------------------
# Tool 2: describe_endpoint
# ---------------------------------------------------------------------------


@registry.tool(tags=["concierge_read"])
async def describe_endpoint(
    ctx: ToolContext,
    path: str,
) -> str:
    """
    Fetch the full self-documentation block for one endpoint.

    Pass 2 of two-pass discovery: after ``discover_endpoints`` has
    narrowed to 2-3 finalists, the agent calls this tool for each to
    inspect required / optional parameters, body shape, examples,
    danger level, and RBAC requirement. The agent then constructs the
    ``concierge_invocation`` action contract from this detail.

    Args:
        path: REST path returned by ``discover_endpoints``. Tolerant
            of leading-slash variance (``/services/...`` and
            ``services/...`` both work).

    Returns:
        JSON string with the full describe block: ``path`` /
        ``method`` / ``resource_group`` / ``danger_level`` / ``surface``
        / ``description`` / ``required_params`` / ``optional_params``
        / ``body_parameters`` / ``components`` / ``capability`` /
        ``spl_example`` / ``raw_describe`` (the original handler-
        supplied describe dict, for any fields not surfaced at top
        level).

        ``body_parameters`` is the AUTHORITATIVE map of body keys the
        endpoint accepts (ground-truthed against the running handler's
        describe block). The agent MUST pick its
        ``body_template`` keys from this map — every other field on
        the response is metadata. Anything outside ``body_parameters``
        is hallucination and post-emission validation will reject the
        proposal.

        On unknown path: ``{"error": "...", "available_paths_hint": [...]}``
        — the hint is a SHORT sample of valid paths so the agent can
        recover (typo correction).
    """
    if not path or not isinstance(path, str):
        return json.dumps({"error": "path is required and must be a string"})

    service = _get_trackme_service(ctx)

    # Single fetch — describe_endpoint only needs ONE catalog round-
    # trip. The earlier implementation fetched twice (once via
    # ``_fetch_full_catalog`` to find the entry, then again via
    # ``_call_trackme_api`` for the raw_describe block); the
    # ``CatalogEntry`` projection didn't carry the raw block, so the
    # second fetch was needed to recover it. Walk the raw entries
    # ourselves here — danger_level / surface inferred inline via
    # the same helpers ``_fetch_full_catalog`` would have used.
    # Bugbot caught the duplicate fetch on commit 94c5afc3.
    response = _call_trackme_api(
        service,
        "trackme/v2/configuration/api_catalog",
        body={"target": "endpoints"},
        method="get",
    )
    if isinstance(response, dict) and response.get("error"):
        return json.dumps({
            "error": "could not load API catalog",
            "detail": response.get("error"),
        })

    entries_raw = (response.get("entries") if isinstance(response, dict) else None) or []

    # Path normalisation matches ``_entry_for_path``: tolerate leading-
    # slash variance (``/services/...`` and ``services/...`` both work).
    candidates = {path, path.lstrip("/"), f"/{path.lstrip('/')}"}

    matched_row: Optional[Dict[str, Any]] = None
    sample: List[str] = []
    for row in entries_raw:
        if not isinstance(row, dict):
            continue
        if "error" in row:
            continue
        row_path_relative = row.get("resource_api") or ""
        row_path = (
            f"/{row_path_relative}"
            if row_path_relative and not row_path_relative.startswith("/")
            else row_path_relative
        )
        # Build the typo-recovery sample lazily as we walk.
        if len(sample) < 8:
            sample.append(row_path)
        if row_path in candidates:
            matched_row = row
            break

    if matched_row is None:
        return json.dumps({
            "error": f"path {path!r} not found in catalog",
            "available_paths_hint": sample,
            "hint": (
                "Use ``discover_endpoints`` to find the right path; "
                "the catalog has ~200 endpoints and the path must "
                "match exactly (leading slash is auto-handled)."
            ),
        })

    # Project the matched row into the rich response shape. Same
    # field set as before — just sourced from the single fetch.
    method = (matched_row.get("resource_mode") or "").lower()
    resource_group = matched_row.get("resource_group") or ""
    function_name = matched_row.get("python_function") or ""
    description = matched_row.get("resource_desc") or ""
    spl_example = matched_row.get("resource_spl_example") or ""
    raw_describe: Dict[str, Any] = matched_row.get("resource_describe") or {}
    required_params = list(raw_describe.get("required_parameters") or ())
    optional_params = list(raw_describe.get("optional_parameters") or ())
    components = list(raw_describe.get("components") or ())

    # Body-schema projection — the keys + per-field descriptions the
    # endpoint actually accepts in the request body. The TrackMe handler
    # convention is to ship this as ``raw_describe.options`` (a list
    # carrying a single dict whose keys are the body field names and
    # values are the per-field descriptions). The legacy
    # ``required_parameters`` / ``optional_parameters`` arrays are
    # populated by only a handful of handlers and were the only signal
    # the agent had to derive body shape from — for the vast majority
    # of TrackMe endpoints those arrays are empty, leaving the LLM to
    # hallucinate body keys (PR #1317 / production failure: agent
    # emitted ``object`` + ``monitored_state`` against
    # ``ds_monitoring`` whose actual schema is ``object_list`` /
    # ``keys_list`` / ``action``). Surfacing the catalogued schema
    # first-class here gives the LLM the ground truth it was missing.
    body_parameters: Dict[str, str] = {}
    options = raw_describe.get("options")
    if isinstance(options, list) and options:
        first_option = options[0]
        if isinstance(first_option, dict):
            for key, val in first_option.items():
                if isinstance(key, str):
                    body_parameters[key] = (
                        val if isinstance(val, str) else str(val)
                    )

    row_path_relative = matched_row.get("resource_api") or ""
    matched_path = (
        f"/{row_path_relative}"
        if row_path_relative and not row_path_relative.startswith("/")
        else row_path_relative
    )

    return json.dumps({
        "path": matched_path,
        "method": method,
        "resource_group": resource_group,
        "danger_level": infer_danger_level(method, resource_group, function_name),
        "surface": infer_surface(resource_group),
        "description": description,
        "required_params": required_params,
        "optional_params": optional_params,
        # ``body_parameters`` is the AUTHORITATIVE map of body keys the
        # endpoint accepts (ground-truthed against the running handler's
        # describe block). The agent MUST pick body_template keys from
        # this map — anything else is a hallucination and post-emission
        # validation will reject it.
        "body_parameters": body_parameters,
        "components": components,
        "capability": "",  # not currently surfaced through the catalog endpoint
        "spl_example": spl_example,
        "raw_describe": raw_describe,
    }, default=str)


# ---------------------------------------------------------------------------
# Tool 3: read_via_endpoint
# ---------------------------------------------------------------------------


@registry.tool(tags=["concierge_read"])
async def read_via_endpoint(
    ctx: ToolContext,
    path: str,
    query: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Actually exercise a read-classified TrackMe REST endpoint.

    Used by the Concierge agent to verify state BEFORE proposing a
    write — *"does this entity exist? what's its current priority?
    is the action a no-op?"*. Proposing a write without first
    confirming current state is a smell; this tool exists to make
    "read first, propose second" cheap.

    The tool refuses paths whose catalog ``danger_level`` is anything
    other than ``read``. This is defence in depth on top of the SDK's
    tool-tag allowlist (which already excludes write tools); a
    future regression that mis-tagged a write endpoint as read
    shouldn't accidentally execute it via this tool.

    Args:
        path: REST path (must be read-classified in the catalog).
            Tolerant of leading-slash variance.
        query: Optional query-string params (used for GET endpoints
            that take query args).
        body: Optional request body (some "read" endpoints accept
            POST bodies for filtering — e.g. ``post_get_ack_for_object``
            takes ``{"tenant_id": ..., "object_id": ...}`` even though
            it's read-only).

    Returns:
        JSON string with the endpoint's response. On error: ``{"error":
        "...", "http_status": ..., "endpoint": ...}`` — same shape
        ``_call_trackme_api`` returns directly.

        Refusal cases:
          * Empty / unknown path → ``{"error": "path ... not found
            in catalog"}``.
          * Path classified as anything other than ``read`` →
            ``{"error": "path ... is not read-classified", "danger_level":
            "<the actual classification>"}``. Agent must use
            ``propose_action`` instead, NOT this tool.
    """
    if not path or not isinstance(path, str):
        return json.dumps({"error": "path is required and must be a string"})

    service = _get_trackme_service(ctx)
    entries = _fetch_full_catalog(service)
    if not entries:
        return json.dumps({"error": "could not load API catalog"})

    entry = _entry_for_path(entries, path)
    if entry is None:
        return json.dumps({
            "error": f"path {path!r} not found in catalog",
            "hint": "Use ``discover_endpoints`` to find the right path.",
        })

    if entry.danger_level != DANGER_READ:
        return json.dumps({
            "error": (
                f"path {path!r} is not read-classified — "
                f"refusing to execute via read_via_endpoint"
            ),
            "danger_level": entry.danger_level,
            "method": entry.method,
            "next_step": (
                "Use ``propose_action`` to emit a Concierge invocation "
                "contract for this endpoint. The user will approve via "
                "the consent card before any mutation fires."
            ),
        })

    # Build the relative endpoint path in the shape ``_call_trackme_api``
    # expects (no leading slash, no ``services/`` prefix).
    api_path = entry.path.lstrip("/")
    if api_path.startswith("services/"):
        api_path = api_path[len("services/"):]

    method = entry.method.lower() if entry.method else "get"

    if method == "get":
        # ``_call_trackme_api`` doesn't take a query arg; for GET
        # endpoints we still pass the body via the same JSON-payload
        # mechanism the trackme handlers expect (they read params
        # from ``request_info.raw_args["payload"]``). The ``query``
        # arg is reserved for future use; for now we merge it into
        # ``body`` so the agent can pass either / both naturally.
        merged_body = {}
        if isinstance(query, dict):
            merged_body.update(query)
        if isinstance(body, dict):
            merged_body.update(body)
        result = _call_trackme_api(service, api_path, body=merged_body, method="get")
    else:
        # POST-style "read" endpoints (filtered queries).
        result = _call_trackme_api(service, api_path, body=body or {}, method=method)

    if isinstance(result, dict) and "error" in result:
        return json.dumps(result, default=str)

    return json.dumps({
        "path": entry.path,
        "method": method,
        "danger_level": entry.danger_level,
        "result": result,
    }, default=str)


# ---------------------------------------------------------------------------
# Tool 4: propose_action
# ---------------------------------------------------------------------------


@registry.tool(tags=["concierge_read"])
async def propose_action(
    ctx: ToolContext,
    intent_summary: str,
    actions: List[Dict[str, Any]],
    rationale: str,
) -> str:
    """
    Validate AND RECORD a proposed Concierge action contract.

    This tool is the **sole source of truth** for actions reaching the
    consent card. The agent runner installs a per-run recorder via
    ``install_proposed_actions_recorder`` before ``agent.run()``; on
    successful validation this tool replaces the recorder's contents
    with the validated action set. The composer in
    ``_run_concierge_advisor_agent`` reads from that recorder AFTER
    the run finishes and overwrites whatever the LLM put in its
    structured output's ``actions`` field — so hallucinated paths in
    the LLM's free-form structured output are physically unable to
    reach the consent card.

    Validation rules (rejected proposals get ``status: invalid`` with
    actionable error messages — the agent should fix and retry):
      - ``endpoint_path`` exists in the live API catalog
      - ``method`` matches the catalog's registered method for the path
      - ``danger_level`` matches the catalog's classification (no
        downgrades — a destructive action stays destructive)
      - ``session_injected_fields`` only contains names from the
        allowlist (``tenant_id`` / ``object_id`` / ``object`` /
        ``component``)
      - Every name in ``session_injected_fields`` corresponds to a
        ``body_template`` key carrying the literal string
        ``"<session-injected>"`` (cross-checked in both directions)

    Recorder semantics — the LLM may call this tool MULTIPLE times to
    refine its proposal; each call REPLACES the previous validated
    set (clear + extend). Only the LAST validated call reaches the
    consent card. The agent's ``actions_taken`` log retains every
    attempt for the audit trail.

    Mutation still flows through the consent-card click → frontend →
    REST. This tool does NOT execute anything; it validates the action
    shape against the catalog and stamps the validated set into the
    server-side recorder for the composer to consume.

    Args:
        intent_summary: One-line restatement of the user's intent.
            Will appear as the consent card title.
        actions: List of dicts, each with the shape:
            ``{
                "endpoint_path": str,
                "method": str,
                "body_template": dict,
                "session_injected_fields": list[str],
                "danger_level": str,
                "rbac_required": str,
                "rationale": str,
            }``
        rationale: One short paragraph explaining the overall
            proposal. Surfaced under the action list on the consent
            card.

    Returns:
        JSON string with validation results:

          * ``{"status": "valid", "actions_validated": N, ...}`` on
            success — agent should proceed to emit the final
            structured output mirroring this proposal.
          * ``{"status": "invalid", "errors": [...], ...}`` when one
            or more actions failed validation — agent should fix
            the issues OR propose a different action set.

        Validation rules:
          * ``endpoint_path`` exists in the catalog.
          * ``method`` matches the catalog's registered method for
            the path.
          * ``danger_level`` matches the catalog's classification.
          * ``session_injected_fields`` only contains names from the
            allowlist (``tenant_id`` / ``object_id`` / ``object`` /
            ``component``).
          * Every name in ``session_injected_fields`` corresponds to
            a key in ``body_template`` carrying the literal string
            ``"<session-injected>"``.
          * ``actions`` length is non-zero (empty proposal should be
            modelled as "no contract" in the structured output, not
            an empty propose_action call).
    """
    if not intent_summary or not isinstance(intent_summary, str):
        return json.dumps({
            "status": "invalid",
            "errors": ["intent_summary is required and must be a non-empty string"],
        })

    if not isinstance(actions, list) or not actions:
        return json.dumps({
            "status": "invalid",
            "errors": [
                "actions must be a non-empty list. To propose nothing, "
                "emit a final structured output with empty ``actions`` "
                "and skip propose_action entirely."
            ],
        })

    service = _get_trackme_service(ctx)
    entries = _fetch_full_catalog(service)
    if not entries:
        return json.dumps({
            "status": "invalid",
            "errors": ["could not load API catalog for validation"],
        })

    # Build a path-indexed lookup for O(1) validation.
    by_path: Dict[str, CatalogEntry] = {}
    for entry in entries:
        by_path[entry.path] = entry
        # Also index without leading slash for lenient matching.
        by_path[entry.path.lstrip("/")] = entry

    # Re-import the validation Pydantic model + allowlist constants
    # from the agent lib so the rules stay in sync (single source of
    # truth — if the schema changes, this validation tracks).
    from trackme_libs_ai_concierge_advisor import (
        _VALID_SESSION_INJECTED_FIELDS,
        _VALID_DANGER_LEVELS,
        _VALID_HTTP_METHODS,
        ConciergeAction,
    )

    errors: List[str] = []
    validated: List[Dict[str, Any]] = []

    for idx, action in enumerate(actions):
        if not isinstance(action, dict):
            errors.append(f"action[{idx}]: must be a dict, got {type(action).__name__}")
            continue

        # First: schema validation via ConciergeAction. This catches
        # method enum, danger-level enum, session-injected-field
        # allowlist, and the cross-field placeholder rule in one
        # shot.
        try:
            ConciergeAction(**action)
        except Exception as exc:
            errors.append(f"action[{idx}]: schema validation failed: {exc}")
            continue

        # Second: catalog cross-check.
        endpoint_path = action.get("endpoint_path", "")
        catalog_entry = by_path.get(endpoint_path) or by_path.get(endpoint_path.lstrip("/"))
        if catalog_entry is None:
            errors.append(
                f"action[{idx}]: endpoint_path {endpoint_path!r} not found "
                f"in API catalog. Use ``discover_endpoints`` to find a "
                f"valid path."
            )
            continue

        # Method must match the catalog's registered method.
        action_method = (action.get("method") or "").lower()
        if action_method != catalog_entry.method:
            errors.append(
                f"action[{idx}]: method {action_method!r} does not match "
                f"catalog method {catalog_entry.method!r} for path "
                f"{endpoint_path!r}"
            )
            continue

        # Danger level must match the catalog's classification (no
        # downgrades allowed — agent cannot make a write seem safer
        # than it is).
        action_danger = action.get("danger_level", "")
        if action_danger != catalog_entry.danger_level:
            errors.append(
                f"action[{idx}]: danger_level {action_danger!r} does not "
                f"match catalog danger_level {catalog_entry.danger_level!r} "
                f"for path {endpoint_path!r} — do NOT downgrade the "
                f"classification"
            )
            continue

        # Body-template key validation. Every key in the agent's
        # ``body_template`` MUST come from the catalog's
        # ``body_parameters`` set (sourced from
        # ``raw_describe.options[0]``). Without this guard the LLM
        # could emit invented keys (e.g. ``monitored_state`` against
        # an endpoint whose actual schema is ``object_list`` /
        # ``keys_list`` / ``action``) and the user would only see
        # the failure as an HTTP error at execute time. PR #1317
        # surfaced this in production: the agent emitted
        # ``ds_update_dsm`` with ``object`` + ``monitored_state``;
        # the real endpoint is ``ds_monitoring`` with ``object_list``
        # + ``action``.
        #
        # ``body_parameters`` is empty when the handler doesn't
        # surface ``options`` — in that case we fall back to the
        # legacy ``required_params`` ∪ ``optional_params`` union, and
        # if that's also empty we skip the check entirely (a few
        # handlers genuinely have no body schema; rejecting them
        # would block valid proposals).
        accepted_keys: frozenset = catalog_entry.body_parameters or frozenset(
            tuple(catalog_entry.required_params) + tuple(catalog_entry.optional_params)
        )
        if accepted_keys:
            body_template = action.get("body_template") or {}
            if isinstance(body_template, dict):
                bad_keys = sorted(
                    k for k in body_template.keys() if k not in accepted_keys
                )
                if bad_keys:
                    errors.append(
                        f"action[{idx}]: body_template carries unknown "
                        f"key(s) {bad_keys!r} not accepted by endpoint "
                        f"{endpoint_path!r}. Accepted keys per the "
                        f"catalog's options block: {sorted(accepted_keys)!r}. "
                        f"Use ``describe_endpoint`` and copy keys from the "
                        f"``body_parameters`` field — never invent body keys."
                    )
                    continue

        # Record the FULL action dict (not just a slim projection) so
        # the consent card has everything it needs — ``body_template``,
        # ``rbac_required``, ``rationale``, ``session_injected_fields``.
        # The shape mirrors ``ConciergeAction`` and is consumed
        # server-side by the composer in ``_run_concierge_advisor_agent``
        # which builds ``ConciergeAction(**a)`` from each entry.
        validated.append(dict(action))

    if errors:
        return json.dumps({
            "status": "invalid",
            "errors": errors,
            "actions_validated": len(validated),
            "actions_total": len(actions),
            "hint": (
                "Fix the listed issues and call propose_action again, "
                "OR adjust the proposal to use different endpoints. "
                "Common mistakes: path typo (use ``describe_endpoint`` "
                "to confirm exact path), method mismatch (re-read the "
                "catalog row), danger_level downgrade (use the "
                "catalog's value verbatim)."
            ),
        }, default=str)

    # Approach 1 — propose_action is the SOLE source of truth for actions
    # reaching the consent card. Push the validated set into the per-run
    # recorder installed by the agent runner. Replace semantics: each
    # ``propose_action`` call represents the FINAL action set; multiple
    # calls overwrite (the LLM uses repeat calls to refine). The
    # composer reads from this recorder AFTER ``agent.run()`` returns
    # and overwrites whatever the LLM put in its structured output —
    # hallucinated paths in the LLM's free-form ``actions`` field are
    # ignored.
    recorder = _proposed_actions_recorder.get()
    if recorder is not None:
        recorder.clear()
        recorder.extend(validated)
    else:
        # No recorder installed — agent runner forgot to install one,
        # OR ``propose_action`` was called outside an agent run (e.g.
        # by a future tool-test harness). The validation receipt below
        # still tells the LLM "valid", but without a recorder the
        # composer has nothing to read from and the proposal will fall
        # back to the LLM's structured-output ``actions`` (the legacy
        # path, with ``_validate_post_emission`` as the only line of
        # defence). Log a warning so this misconfiguration doesn't go
        # unnoticed in production.
        try:
            ctx.logger.warning(
                "propose_action called with no recorder installed — "
                "validated actions will not propagate to the consent "
                "card. Agent runner must call "
                "``install_proposed_actions_recorder`` before "
                "``agent.run()``."
            )
        except Exception:
            pass

    return json.dumps({
        "status": "valid",
        "intent_summary": intent_summary,
        "rationale": rationale,
        "actions_validated": len(validated),
        "actions": validated,
        "next_step": (
            "Proposal RECORDED. The validated action set above is now "
            "the authoritative input to the consent card. Emit your "
            "final structured output (``ConciergeProposalResult``) "
            "with ``consent_required: true``, a 1-3 sentence "
            "``summary`` for the chat bubble, and "
            "``intent_summary`` / ``reasoning_trace`` as usual. The "
            "structured output's own ``actions`` field is IGNORED — "
            "the consent card renders only what this tool recorded. "
            "If you need to refine, call ``propose_action`` again "
            "with the revised set; only the LAST validated call counts."
        ),
    }, default=str)

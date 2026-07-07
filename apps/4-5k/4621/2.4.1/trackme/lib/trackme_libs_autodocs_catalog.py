# coding=utf-8
"""
TrackMe API autodocs catalog — shared helpers.

The TrackMe REST API is self-documenting: every handler method exposes
a ``describe=true`` mode that returns its own description, parameter
shape, and usage examples. The ``trackmeapiautodocs`` custom search
command introspects every registered handler, calls each method with
``describe=true``, and yields the result row-by-row for the REST API
Reference UI.

The Concierge Advisor (Phase 6 of the AI Assistant ↔ AI Advisor bridge,
see ``ai-context/integrations/concierge-advisor-implementation-plan.md``)
needs the same catalog, but in a *programmatic* form rather than as
SPL output:

  * Selectable by an MCP tool the agent calls (``discover_endpoints``).
  * Filterable by surface (entity / tenant_home / vtenants / global),
    HTTP verb (read / write), and the caller's effective RBAC.
  * Ranked by keyword match against a user intent.
  * Formattable as a condensed text catalog suitable for grounding the
    agent's system prompt without burning the token budget on full
    schemas.

This module owns the pure helpers — no Splunk runtime dependencies,
trivially unit-testable. Catalog-building (the introspection that
collects ``describe`` blocks from each handler) is layered on top of
these helpers in a follow-up module that *does* depend on Splunk; this
file stays library-friendly so the PR cycle and unit-test feedback loop
both stay fast.

See ``unit_tests/check_autodocs_catalog.py`` for the helper test
suite — it exercises every public function with realistic catalog
fixtures and asserts the heuristic / filter / rank / format outputs
exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Iterable, List, Optional, Sequence


# Danger-level enum.
#
# Every endpoint receives one of these tags. The default heuristic
# infers from HTTP method + resource-group suffix + function-name
# pattern; per-endpoint overrides may supply explicit values via the
# CatalogEntry constructor. The Concierge consent card surfaces the
# danger level on every proposed action, and ``destructive`` triggers
# the per-action re-confirmation textbox.
DANGER_READ = "read"
DANGER_WRITE_LOW = "write-low"
DANGER_WRITE_HIGH = "write-high"
DANGER_DESTRUCTIVE = "destructive"

DANGER_LEVELS = (
    DANGER_READ,
    DANGER_WRITE_LOW,
    DANGER_WRITE_HIGH,
    DANGER_DESTRUCTIVE,
)


# Surface enum.
#
# Each chat panel context maps to one surface. The agent's
# ``discover_endpoints`` tool filters by the caller's surface so
# entity-context chats don't surface global / vtenants admin endpoints
# (and vice-versa). ``global`` matches every surface — used for
# endpoints (config introspection, audit) that apply everywhere.
SURFACE_ENTITY = "entity"
SURFACE_TENANT_HOME = "tenant_home"
SURFACE_VTENANTS = "vtenants"
SURFACE_GLOBAL = "global"

SURFACES = (SURFACE_ENTITY, SURFACE_TENANT_HOME, SURFACE_VTENANTS, SURFACE_GLOBAL)


# Verb-filter enum (used by ``filter_catalog`` and the agent tool).
#
# ``read``  → only GET endpoints + endpoints whose danger_level is read.
# ``write`` → POST / PUT / DELETE that mutate state.
# ``any``   → no verb filter.
VERB_READ = "read"
VERB_WRITE = "write"
VERB_ANY = "any"


# Patterns that bump the inferred danger level. Order matters — the
# first matching rule wins. Tested against the handler's
# ``resource_group`` (e.g. ``"splk_dsm/admin"``, ``"alerting"``) and
# the function name (e.g. ``"delete_object"``, ``"post_update_priority"``).
# NOTE: bare ``_delete`` is intentionally NOT in this tuple even though
# it might look natural. Substring matching against
# ``get_resource_group_desc_splk_deleted_entities`` (and any other
# function whose name simply contains the past-tense ``deleted``) would
# cause a false positive — read-only GETs against the
# ``splk_deleted_entities`` resource group would be misclassified as
# destructive. Bugbot caught this on commit 1719befd. The
# ``delete_`` prefix pattern is what matters; functions actually
# performing deletions follow the canonical ``delete_X`` /
# ``post_delete_X`` naming.
_DESTRUCTIVE_NAME_PATTERNS = (
    "delete_",
    "destroy_",
    "purge_",
    "wipe_",
    "decommission_",
    "remove_tenant",
    "remove_vtenant",
)
_WRITE_HIGH_GROUP_SUFFIXES = ("/admin",)
_WRITE_LOW_GROUP_SUFFIXES = ("/write", "/power")


@dataclass(frozen=True)
class CatalogEntry:
    """One endpoint entry in the API catalog.

    Frozen / hashable so entries can live in sets and dict keys
    (helpful for de-duplication when the same endpoint is registered
    by multiple handlers, which can happen for a few overlap cases).

    Fields:
        path: REST path, e.g. ``/services/trackme/v2/ack/get_ack_for_object``.
        method: HTTP verb in lowercase: ``get`` / ``post`` / ``delete``.
        resource_group: Logical group from ``handlers_api_catalog``
            (e.g. ``"alerting"``, ``"splk_dsm/admin"``).
        handler_name: Python class name of the registered handler
            (e.g. ``"TrackMeHandlerAckReadOps_v2"``). Useful for cross-
            referencing back to source.
        function_name: Method name on the handler (e.g.
            ``"post_get_ack_for_object"``).
        description: One-line description from the endpoint's
            ``describe=true`` block. ``""`` when unavailable.
        required_params: Sequence of required parameter names.
        optional_params: Sequence of optional parameter names.
        components: Components this endpoint applies to (e.g.
            ``["dsm", "dhm"]``). Empty when not component-scoped.
        capability: Splunk capability required by ``authorize.conf`` —
            typically ``"trackmeuseroperations"`` /
            ``"trackmepoweroperations"`` / ``"trackmeadminoperations"``.
            ``""`` when not gated.
        spl_example: The ``| trackme url=…`` SPL example from the
            describe block, when present.
        danger_level: One of ``DANGER_LEVELS``. Inferred from method +
            resource_group + function_name unless explicitly supplied.
        surface: One of ``SURFACES``. Inferred from resource_group
            unless explicitly supplied.

    Mutability note: ``frozen=True`` makes ``CatalogEntry`` immutable.
    Helpers like ``filter_catalog`` and ``rank_by_intent`` take and
    return ``Sequence[CatalogEntry]`` — they never mutate.
    """
    path: str
    method: str
    resource_group: str
    handler_name: str = ""
    function_name: str = ""
    description: str = ""
    required_params: Sequence[str] = field(default_factory=tuple)
    optional_params: Sequence[str] = field(default_factory=tuple)
    components: Sequence[str] = field(default_factory=tuple)
    capability: str = ""
    spl_example: str = ""
    danger_level: str = ""
    surface: str = ""
    # Authoritative body-schema map sourced from
    # ``raw_describe.options[0]`` — keys are the field names the
    # endpoint accepts in its request body, values are the per-field
    # descriptions. Empty when the handler did not surface an
    # ``options`` block. The post-emission validator in
    # ``propose_action`` (and the agent runner's safety net in
    # ``_validate_action_contract``) cross-checks every
    # ``body_template`` key against this set so hallucinated keys are
    # rejected before they reach the wire. ``frozenset`` rather than a
    # plain dict so the entry stays hashable + immutable.
    body_parameters: frozenset = field(default_factory=frozenset)

    def to_dict(self) -> dict:
        """Plain dict for JSON serialisation (REST endpoint output).

        ``body_parameters`` is a ``frozenset`` for hashability /
        immutability inside the dataclass, but ``json.dumps`` raises
        ``TypeError`` on frozensets. The override here converts the
        set to a sorted list so the projected dict round-trips
        cleanly through ``json.dumps`` — bugbot caught the regression
        on commit 3b62fcf1 (Medium severity). Sorting keeps the JSON
        output deterministic across runs (helpful for diffing the
        REST endpoint response between releases).
        """
        d = asdict(self)
        d["body_parameters"] = sorted(self.body_parameters)
        return d


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------

def infer_danger_level(method: str, resource_group: str, function_name: str = "") -> str:
    """Infer the danger level of an endpoint from HTTP verb + path patterns.

    Heuristic (first match wins):

      1. ``DELETE`` HTTP verb               → ``destructive``.
      2. Function name contains a destructive pattern (``delete_*``,
         ``destroy_*``, ``purge_*``, ``decommission_*``)  → ``destructive``.
      3. Resource group ends with ``/admin``              → ``write-high``.
      4. Resource group ends with ``/write`` / ``/power`` → ``write-low``.
      5. Method is ``GET`` and no admin suffix            → ``read``.
      6. Default                                          → ``write-high``
         (fail-safe — un-classified endpoints get the strictest sane
         tier so the consent card surfaces them prominently).

    The heuristic is intentionally conservative: when in doubt, prefer
    a higher danger level. Per-endpoint overrides supplied by handler
    authors via the ``danger_level`` field on the ``describe=true``
    block always win — see ``CatalogEntry.danger_level`` resolution
    in the catalog builder. This function is the *fallback* when no
    explicit override exists.

    Args:
        method: HTTP verb. Case-insensitive; ``"get"``/``"GET"`` both work.
        resource_group: From ``handlers_api_catalog`` (e.g.
            ``"alerting/admin"``, ``"splk_dsm"``, ``"splk_dsm/write"``).
        function_name: Method name on the handler (e.g.
            ``"delete_object"``, ``"post_update_priority"``). Optional —
            when omitted, only verb + resource_group drive the result.

    Returns:
        One of ``DANGER_LEVELS``.
    """
    method_lower = (method or "").lower()
    function_lower = (function_name or "").lower()
    group_lower = (resource_group or "").lower()

    # Rule 1: explicit DELETE.
    if method_lower == "delete":
        return DANGER_DESTRUCTIVE

    # Rule 2: destructive name pattern (covers POST endpoints that
    # delete things behind the scenes — e.g.
    # ``post_delete_dsm_object`` is not a DELETE verb but still
    # destroys state).
    for pattern in _DESTRUCTIVE_NAME_PATTERNS:
        if pattern in function_lower:
            return DANGER_DESTRUCTIVE

    # Rule 3: admin-suffixed resource group.
    for suffix in _WRITE_HIGH_GROUP_SUFFIXES:
        if group_lower.endswith(suffix):
            return DANGER_WRITE_HIGH

    # Rule 4: write/power-suffixed resource group.
    for suffix in _WRITE_LOW_GROUP_SUFFIXES:
        if group_lower.endswith(suffix):
            return DANGER_WRITE_LOW

    # Rule 5: read-style GET.
    if method_lower == "get":
        return DANGER_READ

    # Rule 6: fallback — assume mutation, classify high.
    return DANGER_WRITE_HIGH


def infer_surface(resource_group: str) -> str:
    """Infer the chat surface this endpoint applies to.

    Heuristic:

      * ``vtenants*``                            → ``vtenants``
      * Component-prefixed groups (``splk_dsm``,
        ``splk_dhm``, ``splk_mhm``, ``splk_flx``,
        ``splk_fqm``, ``splk_wlk``)              → ``entity`` *and*
                                                   ``tenant_home`` (we pick
                                                   ``entity`` as primary since
                                                   that's the narrower scope —
                                                   see filter_catalog for
                                                   superset matching)
      * Anything else                            → ``global``

    Args:
        resource_group: From ``handlers_api_catalog``.

    Returns:
        One of ``SURFACES``.
    """
    group = (resource_group or "").lower()

    if group.startswith("vtenants"):
        return SURFACE_VTENANTS

    # Component-scoped endpoints belong to entity surface (most
    # specific). The filter_catalog helper treats entity as a subset
    # of tenant_home (see _surface_matches), so an entity-tagged
    # endpoint is also visible from a tenant_home chat.
    #
    # IMPORTANT: prefix names must match the resource_group strings
    # registered in ``trackme_libs_autodocs_catalog_builder.HANDLERS_API_CATALOG``
    # exactly. The match logic below uses ``group == prefix or
    # group.startswith(prefix + "/")``, which means a prefix of
    # ``"splk_outliers"`` does NOT match a real group of
    # ``"splk_outliers_engine"`` (the next char is ``_``, not ``/``).
    # Bugbot caught the original ``splk_outliers`` typo on commit
    # 359a7a72 — it was supposed to be ``splk_outliers_engine`` to
    # match the ``splk_outliers_engine`` and ``splk_outliers_engine/write``
    # resource groups in the builder. When you add a new component
    # surface, register the EXACT resource_group prefix here, not a
    # truncation of it.
    component_prefixes = (
        "splk_dsm", "splk_dhm", "splk_mhm",
        "splk_flx", "splk_fqm", "splk_wlk",
        "component", "ack", "splk_outliers_engine",
        "splk_hybrid_trackers", "splk_replica_trackers",
        "splk_tag_policies", "splk_priority_policies",
        "splk_sla_policies", "splk_data_sampling",
        "splk_disruption", "splk_blocklist",
        "splk_logical_groups", "splk_lagging_classes",
        "splk_variable_delay", "splk_elastic_sources",
        "splk_deleted_entities",
        "splk_inject_expected", "alerting",
    )
    for prefix in component_prefixes:
        if group == prefix or group.startswith(prefix + "/"):
            return SURFACE_ENTITY

    return SURFACE_GLOBAL


# ---------------------------------------------------------------------------
# Catalog-row projection
# ---------------------------------------------------------------------------


def project_catalog_row_to_entry(row: dict) -> Optional[CatalogEntry]:
    """Project one ``api_catalog`` row into a ``CatalogEntry`` instance.

    Single source of truth for the row → entry transformation. Used by
    both ``_fetch_full_catalog`` (the Concierge ``discover_endpoints``
    + ``describe_endpoint`` path) and ``_validate_post_emission`` (the
    backend safety net that re-runs the catalog cross-check on the
    agent's structured output). Centralising the projection means a
    schema tweak — a new field on ``raw_describe.options``, a different
    path normalisation, a new inferred attribute — lands in exactly one
    place; the two callers cannot drift. Bugbot caught the duplication
    on PR #1321.

    Returns ``None`` when the row is malformed or carries an
    ``"error"`` marker (the server-side builder surfaces partial-build
    failures as ``{"error": ...}`` rows; consumers don't want those
    "discovered"). Callers should treat ``None`` as a skip.
    """
    if not isinstance(row, dict) or row.get("error"):
        return None

    path_relative = row.get("resource_api") or ""
    path = (
        f"/{path_relative}"
        if path_relative and not path_relative.startswith("/")
        else path_relative
    )
    method = (row.get("resource_mode") or "").lower()
    resource_group = row.get("resource_group") or ""
    function_name = row.get("python_function") or ""
    description = row.get("resource_desc") or ""
    spl_example = row.get("resource_spl_example") or ""
    describe_block = row.get("resource_describe") or {}

    required_params = tuple(describe_block.get("required_parameters") or ())
    optional_params = tuple(describe_block.get("optional_parameters") or ())
    components = tuple(describe_block.get("components") or ())

    # Body-schema set sourced from ``raw_describe.options[0]``. The
    # TrackMe handler convention is to ship the body-key schema as
    # ``options: [{key1: desc1, key2: desc2, ...}]``; legacy
    # ``required_parameters`` / ``optional_parameters`` arrays are
    # populated by only a handful of handlers so they cannot be relied
    # on as the body-key contract. ``frozenset`` keeps the entry
    # hashable. Empty when the handler doesn't surface ``options``.
    options = describe_block.get("options")
    if isinstance(options, list) and options and isinstance(options[0], dict):
        body_parameters: frozenset = frozenset(
            k for k in options[0].keys() if isinstance(k, str)
        )
    else:
        body_parameters = frozenset()

    return CatalogEntry(
        path=path,
        method=method,
        resource_group=resource_group,
        handler_name="",  # not surfaced through the catalog endpoint
        function_name=function_name,
        description=description,
        required_params=required_params,
        optional_params=optional_params,
        components=components,
        capability="",  # not currently surfaced; splunkd enforces at boundary
        spl_example=spl_example,
        danger_level=infer_danger_level(method, resource_group, function_name),
        surface=infer_surface(resource_group),
        body_parameters=body_parameters,
    )


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def _surface_matches(entry_surface: str, requested: Optional[str]) -> bool:
    """Return True if ``entry_surface`` is visible from ``requested``.

    Surface inclusion rules (broadest to narrowest):

      ``global``      visible from every surface.
      ``vtenants``    visible only from vtenants chats.
      ``tenant_home`` visible from tenant_home AND entity chats
                      (an entity chat is a more specific tenant_home).
      ``entity``      visible only from entity chats.

    A request for ``tenant_home`` therefore returns ``tenant_home`` +
    ``entity`` + ``global`` entries; a request for ``entity`` returns
    ``entity`` + ``global`` only.

    ``None`` (no filter) → everything matches.
    """
    if requested is None:
        return True
    # Global-tagged entries are visible from EVERY non-None requested
    # surface — they're the "applies everywhere" tier. This handles
    # the ``requested == SURFACE_GLOBAL`` case implicitly: a request
    # for ``surface="global"`` matches global entries on this line and
    # falls through to ``return False`` for any non-global entry,
    # which is the correct exclusion. (Bugbot caught the original
    # ``return True`` regression on commit f64ce2ab and the redundant
    # explicit branch on commit 3b52e2be.)
    if entry_surface == SURFACE_GLOBAL:
        return True
    if requested == SURFACE_ENTITY:
        return entry_surface == SURFACE_ENTITY
    if requested == SURFACE_TENANT_HOME:
        return entry_surface in (SURFACE_TENANT_HOME, SURFACE_ENTITY)
    if requested == SURFACE_VTENANTS:
        return entry_surface == SURFACE_VTENANTS
    # Unknown requested surface (or ``requested == SURFACE_GLOBAL``
    # with a non-global entry — already exclusion by elimination
    # above) — fail closed, surface mismatch.
    return False


def _verb_matches(entry: CatalogEntry, verb_filter: Optional[str]) -> bool:
    """Return True if ``entry``'s danger level matches ``verb_filter``.

    ``read``  matches only ``DANGER_READ``.
    ``write`` matches everything else (write-low / write-high /
              destructive). The Concierge agent uses ``write`` to mean
              "any mutation" — destructive being a subset of write.
    ``any`` / ``None`` matches anything.

    Note: we deliberately drive verb filtering off ``danger_level``
    rather than HTTP method. A POST endpoint that's read-tagged
    (some endpoints accept body but only return data) should still
    match a ``read`` filter.
    """
    if verb_filter in (None, VERB_ANY):
        return True
    if verb_filter == VERB_READ:
        return entry.danger_level == DANGER_READ
    if verb_filter == VERB_WRITE:
        return entry.danger_level != DANGER_READ
    return False


def _capability_matches(entry: CatalogEntry, capabilities: Optional[Sequence[str]]) -> bool:
    """Return True if the caller's capabilities cover the endpoint's gate.

    Endpoints declare a single ``capability`` string (the Splunk
    authz capability required to call them). When the caller's
    capability list includes that string, the endpoint is callable.
    Endpoints with empty ``capability`` are treated as ungated and
    always match.

    ``None`` (capabilities not supplied) → no filter; everything matches.
    """
    if capabilities is None:
        return True
    if not entry.capability:
        return True
    return entry.capability in capabilities


def _resource_group_matches(
    entry_group: str,
    requested: Optional[str],
) -> bool:
    """Return True when ``entry_group`` matches the requested filter.

    Match rules:

      - ``None`` / empty → no filter; everything passes.
      - Exact match → pass.
      - Sub-group expansion: requesting ``"splk_dsm"`` also matches
        ``"splk_dsm/write"`` and ``"splk_dsm/admin"``. The Concierge
        agent typically asks for the umbrella group from the
        ``trackme_libs_describe_rest_api_reference`` resource-groups
        map and expects ALL sub-groups within it. Without this
        expansion the agent would have to enumerate every sub-group
        separately.

    Bare prefix-match without the trailing ``/`` is rejected so a
    request for ``"splk"`` doesn't accidentally suck in every
    ``splk_*`` group — the resource-groups map's keys are designed
    to be selectable as a unit.
    """
    if not requested:
        return True
    if entry_group == requested:
        return True
    return entry_group.startswith(f"{requested}/")


def filter_catalog(
    entries: Iterable[CatalogEntry],
    surface: Optional[str] = None,
    verb_filter: Optional[str] = None,
    capabilities: Optional[Sequence[str]] = None,
    danger_levels: Optional[Sequence[str]] = None,
    resource_group: Optional[str] = None,
) -> List[CatalogEntry]:
    """Filter the catalog by surface / verb / RBAC / danger level / group.

    Args:
        entries: Iterable of ``CatalogEntry``.
        surface: One of ``SURFACES`` or ``None``. When supplied,
            only entries matching the surface (per ``_surface_matches``)
            are returned.
        verb_filter: ``"read"`` / ``"write"`` / ``"any"`` / ``None``.
            See ``_verb_matches`` for semantics.
        capabilities: Sequence of Splunk capability strings the caller
            holds. Endpoints whose ``capability`` isn't in the
            sequence are dropped. ``None`` skips the RBAC filter.
        danger_levels: Optional whitelist of ``DANGER_LEVELS``. When
            supplied, only entries whose ``danger_level`` is in the
            whitelist pass through. Used by the agent to (e.g.)
            request only ``write-low`` candidates when the user's
            intent is clearly low-impact.
        resource_group: Optional umbrella name from the
            ``trackme_libs_describe_rest_api_reference`` resource-groups
            map (e.g. ``"splk_dsm"``, ``"splk_priority_policies"``).
            When supplied, only entries in that group OR a
            sub-group (``"splk_dsm/write"``, ``"splk_dsm/admin"``)
            pass through. The Concierge uses this to scope discovery
            from "search 423 endpoints" down to "search the ~15
            endpoints in the user's chosen group" once the agent has
            picked the group from the embedded resource-groups map.

    Returns:
        New list of ``CatalogEntry``. Input order is preserved.
    """
    danger_set = set(danger_levels) if danger_levels is not None else None

    result: List[CatalogEntry] = []
    for entry in entries:
        if not _surface_matches(entry.surface, surface):
            continue
        if not _verb_matches(entry, verb_filter):
            continue
        if not _capability_matches(entry, capabilities):
            continue
        if danger_set is not None and entry.danger_level not in danger_set:
            continue
        if not _resource_group_matches(entry.resource_group, resource_group):
            continue
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def _tokenise(text: str) -> List[str]:
    """Lowercase + split on non-alphanumeric. Stable, no regex deps."""
    out: List[str] = []
    buf: List[str] = []
    for ch in (text or "").lower():
        if ch.isalnum():
            buf.append(ch)
        else:
            if buf:
                out.append("".join(buf))
                buf = []
    if buf:
        out.append("".join(buf))
    return out


def _entry_keywords(entry: CatalogEntry) -> set:
    """Tokenise every searchable field on a CatalogEntry into one bag."""
    bag: set = set()
    for field_value in (
        entry.path,
        entry.resource_group,
        entry.function_name,
        entry.description,
        " ".join(entry.components or ()),
    ):
        bag.update(_tokenise(field_value))
    return bag


def rank_by_intent(
    entries: Sequence[CatalogEntry],
    intent_keywords: str,
    top_n: int = 10,
) -> List[CatalogEntry]:
    """Rank catalog entries by keyword match against an intent string.

    Simple bag-of-words scoring: tokenise the intent, tokenise each
    entry's searchable fields, score = ``len(intent_tokens & entry_tokens)``.
    Ties broken by description length (shorter wins — preferring
    focused endpoints over broad ones).

    Not TF-IDF, not embedding-based, deliberately. The Concierge agent
    consumes the top-N here as discovery candidates and then drills into
    full ``describe_endpoint`` for the 1-3 it picks; the LLM does the
    real semantic match. This function only has to be GOOD ENOUGH to
    surface relevant candidates in the first place — anything more
    sophisticated would be premature optimisation.

    Args:
        entries: Catalog entries (already filtered by surface / RBAC).
        intent_keywords: Free-text user intent (e.g.
            ``"increase priority to critical"``).
        top_n: Maximum entries to return.

    Returns:
        New list of up to ``top_n`` entries, sorted by descending score.
        Entries with score 0 are dropped (no token overlap → not a
        candidate).
    """
    intent_tokens = set(_tokenise(intent_keywords))
    if not intent_tokens:
        return list(entries)[:top_n]

    scored: List = []
    for entry in entries:
        entry_tokens = _entry_keywords(entry)
        score = len(intent_tokens & entry_tokens)
        if score == 0:
            continue
        # Tie-breaker: shorter description wins (more focused).
        scored.append((score, -len(entry.description), entry))

    scored.sort(key=lambda triple: (triple[0], triple[1]), reverse=True)
    return [entry for _score, _tiebreak, entry in scored[:top_n]]


# ---------------------------------------------------------------------------
# Formatting (for system-prompt grounding)
# ---------------------------------------------------------------------------

def format_condensed(entries: Sequence[CatalogEntry]) -> str:
    """Format the catalog as a compact text grouping for the system prompt.

    Output shape (one entry per line, grouped by ``resource_group``):

        ## ack
          GET  /services/trackme/v2/ack/get_ack_for_object [read]
            Acknowledgments query — returns active ack for one entity
          POST /services/trackme/v2/ack/write/post_ack [write-low]
            Acknowledge an entity for N hours

        ## alerting
          ...

    Designed for the Concierge agent's two-pass discovery flow:
    Pass 1 (this function) gives the LLM a wide-but-shallow view —
    enough to pick 3-5 candidates. Pass 2 (``describe_endpoint`` MCP
    tool) gives the full schema for the candidates the LLM drills into.

    The format is plain text, not Markdown, because most LLMs handle
    plain text marginally better in long-context grounding and we
    don't need rendering. Indentation is the structure.

    Args:
        entries: Catalog entries to format. Caller filters first.

    Returns:
        Multi-line string.
    """
    if not entries:
        return "(no endpoints match the current scope)"

    # Group by resource_group, preserving entry order within each group.
    groups: dict = {}
    group_order: List[str] = []
    for entry in entries:
        rg = entry.resource_group or "(uncategorised)"
        if rg not in groups:
            groups[rg] = []
            group_order.append(rg)
        groups[rg].append(entry)

    lines: List[str] = []
    for rg in group_order:
        lines.append(f"## {rg}")
        for entry in groups[rg]:
            method = (entry.method or "").upper().rjust(6)
            danger = f"[{entry.danger_level}]" if entry.danger_level else ""
            lines.append(f"  {method} {entry.path} {danger}".rstrip())
            desc = (entry.description or "").strip()
            if desc:
                # Truncate long descriptions — Pass 2 has the full text.
                if len(desc) > 120:
                    desc = desc[:117] + "..."
                lines.append(f"    {desc}")
        lines.append("")  # blank line between groups

    return "\n".join(lines).rstrip() + "\n"

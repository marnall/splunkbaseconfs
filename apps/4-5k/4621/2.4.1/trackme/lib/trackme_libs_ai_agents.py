"""
TrackMe AI Agents — Shared Library

Provides the ML Outlier Advisor agent and supporting infrastructure:
- AI provider config bridge (TrackMe provider → SDK model)
- System prompts for agent specializations
- Pydantic output schemas for structured agent responses
- Async job orchestration for agent invocations

Uses the official Splunk Python SDK (splunklib.ai) for agent orchestration.
splunk-sdk>=3.0.0 (pinned in package/lib/requirements.txt) bundles the AI
module on PyPI, so ucc-gen installs splunklib + splunklib.ai directly into
lib/splunklib/ at build time — no vendoring layer needed.
"""

# ---------------------------------------------------------------------------
# Upstream-warning suppression
# ---------------------------------------------------------------------------
#
# langgraph (>= 1.1.1, our current pinned floor in
# ``package/lib/requirements.txt``) emits a
# ``LangChainPendingDeprecationWarning`` from
# ``langgraph/checkpoint/serde/encrypted.py`` at import time:
#
#     The default value of `allowed_objects` will change in a future
#     version. Pass an explicit value (e.g., allowed_objects='messages'
#     or allowed_objects='core') to suppress this warning.
#
# The warning is emitted by langchain code that langgraph internally
# imports without passing an explicit ``allowed_objects``. We don't
# construct that object ourselves, so we cannot pass the explicit value
# at our call sites — it has to be fixed inside langgraph upstream
# (or absorbed when langchain's default flips).
#
# Splunk's ``PersistentScript`` framework captures the Python warning
# (which goes to stderr by default) and re-emits each line in
# ``splunkd.log`` at ERROR severity, so the warning surfaces as a
# spurious ERROR on every Agent SDK invocation. Suppress at module load
# time — our module is the canonical entry point for all agent
# invocations (REST handler ``trackme_rest_handler_ai_ml_advisor``,
# scheduled command ``trackmesplkoutliersmladvisorhelper``, AI Advisor
# describe context), and the actual ``langgraph`` / ``langchain``
# imports are deferred to function scope, so installing the filter
# here guarantees it is active before any code path can trigger the
# warning.
#
# Filter by message text rather than ``LangChainPendingDeprecationWarning``
# class so we don't depend on a langchain version-specific symbol path.
# Revisit when langgraph upstream starts passing ``allowed_objects``
# explicitly (or when our pinned floor moves past the default change),
# at which point this filter becomes a no-op and can be removed.
# PEP 563 — stringify all annotations so this module imports cleanly on
# Python 3.9 (Splunk 9.x default).  Two functions in this file use PEP 604
# union syntax (``dict | None`` / ``str | None``) in their signatures —
# without stringified annotations Python 3.9 evaluates the union at
# function-definition time (module load) and raises
# ``TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'``.
#
# The trap is that ``trackme_libs_autodocs_catalog_builder`` eagerly
# imports every REST handler, including ``trackme_rest_handler_ai_ml_advisor``
# (which imports this module).  The catalog builder wraps the AI advisor
# imports in ``try / except ImportError`` for handlers that may be
# absent, but ``TypeError`` bubbles past that guard and crashes the
# whole catalog endpoint — surfacing as ``catalog builder unavailable:
# unsupported operand type(s) for |: 'type' and 'NoneType'`` from
# ``/services/trackme/v2/configuration/api_catalog``.
#
# On Python 3.13 (Splunk 10.x) ``from __future__ import annotations`` is
# a no-op for runtime behaviour; pydantic 2.x's BaseModel subclasses
# defined below resolve string annotations through ``get_type_hints()``
# (forward references go top-down: ``AnomalyWindow`` /
# ``ModelRecommendation`` are defined before ``MLAdvisorResult``
# references them).
from __future__ import annotations

# Imports needed only for type hints — gated behind ``TYPE_CHECKING``
# so we don't pay the ``splunklib.ai`` runtime import cost at module
# load (the real SDK imports happen lazily inside functions, e.g.
# ``make_prompt_cache_middleware`` below). With ``from __future__
# import annotations`` above, every annotation is evaluated lazily as a
# string, so the names listed in the guarded block are never resolved
# at runtime.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from splunklib.ai.middleware import ModelRequest as _ModelRequest

import warnings as _warnings

_warnings.filterwarnings(
    "ignore",
    message=r"The default value of `allowed_objects` will change",
)

import asyncio
import contextlib
import contextvars
import json
import logging
import os
import time
import threading
import uuid

import splunklib.client as client

import copy

# Pydantic primitives come through the project-wide compat shim so the
# advisor modules stay importable on Python 3.9 (Splunk 9.x) — see
# ``trackme_libs_pydantic_compat`` for the full rationale.
from trackme_libs_pydantic_compat import BaseModel, Field

# TrackMe shared libraries
from trackme_libs_ai import get_ai_config, get_ai_api_key

# ---------------------------------------------------------------------------
# Per-advisor logger routing
# ---------------------------------------------------------------------------
#
# This module is shared infrastructure used by every AI Advisor (ML, Feed
# Lifecycle, FLX Threshold, FQM, Component Health, Concierge).  Each
# advisor's parent REST handler configures its own dedicated rotating log
# file via ``setup_logger("trackme.rest.ai.<advisor>")``.
#
# PR #1521 routed this file's logger statically to ``trackme.rest.ai.
# ml_advisor`` to consolidate "agent SDK lifecycle" lines in one place —
# but the consolidation flipped into noise: a Feed Lifecycle run's
# ``tool_middleware`` lines (clearly tagged ``[Feed Lifecycle Advisor]``
# in the message) ended up in the ML Advisor's log file, while the
# Feed Lifecycle log file showed nothing about its own tool calls.
#
# Fix: a ``ContextVar`` carries the "current advisor logger name" set by
# each advisor's ``_run_<advisor>_agent`` entry point.  All log calls in
# this module resolve the right logger at call time via ``_log()`` —
# ``contextvars.ContextVar`` is the correct primitive (not
# ``threading.local``) because the SDK middleware runs inside the
# asyncio loop and ``ContextVar`` propagates automatically to
# ``asyncio.create_task`` / ``asyncio.to_thread``.
#
# Threads spawned without explicit ``contextvars.copy_context()`` (the
# watchdog and heartbeat ticker) inherit nothing and fall back to the
# default — that's intentional: those threads emit infrastructure-level
# lines (watchdog breaches, ticker errors) that legitimately belong in
# the shared ML Advisor log alongside other agent-SDK plumbing.
_current_advisor_logger_name: contextvars.ContextVar = contextvars.ContextVar(
    "trackme_current_advisor_logger_name",
    default="trackme.rest.ai.ml_advisor",
)


def set_current_advisor_logger(name):
    """Set the logger name for log calls in this module from the current
    async context onwards.  Must be called at the top of each advisor's
    ``_run_<advisor>_agent`` function (before any tool call dispatch or
    middleware construction) so the SDK middleware — which runs inside
    the same async context — resolves to the right per-advisor logger.

    Returns the ``contextvars.Token`` from ``ContextVar.set`` so the
    caller can ``reset`` it if needed (typically unnecessary — the
    context dies with the async task).
    """
    return _current_advisor_logger_name.set(name)


def _log():
    """Resolve the current advisor's logger.  See module docstring above
    for the rationale and propagation semantics.

    Cheap (``logging.getLogger`` is a dict lookup on the singleton
    registry) so safe to call on every log line.
    """
    return logging.getLogger(_current_advisor_logger_name.get())

# NOTE: Splunk Agent SDK imports (splunklib.ai.*) are deferred to function scope.
# The AI SDK requires Python 3.13+ and raises ImportError on 3.9.
# Lazy imports allow this module to load on py3.9 for non-agent operations
# (job status polling, cancellation) while agent invocation requires py3.13.

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_KV_COLLECTION_AGENT_JOBS = "kv_trackme_ai_agent_jobs"
_JOB_TTL_SECONDS = 900  # 15 minutes — stored in each agent job record as
                        # the "timeout" field; the status-poll uses it
                        # plus ``_STALE_RUNNING_BUFFER_SECONDS`` to
                        # decide when to declare a job stale.  Must be
                        # >= AGENT_RUN_HARD_TIMEOUT_SEC so the
                        # in-process timeout fires first and writes the
                        # better error message (the stale-poll's
                        # message is intentionally generic).
_STALE_RUNNING_BUFFER_SECONDS = 120
_MAX_CONCURRENT_AGENTS_DEFAULT = 5

# Hard outer timeout(s) for the agent's ``asyncio.run`` invocation.
#
# The Splunk Agent SDK has been observed to occasionally hang inside its
# parallel-tool result aggregation or its structured-output extraction
# step — both manifest as ``asyncio.run`` never returning, no exception
# raised, no log line emitted.  Without an outer cap, the worker thread
# spins forever, the concurrency slot leaks, and after enough hangs the
# entire AI Advisor system locks out (5 zombie threads = all slots
# consumed).
#
# Layered defence (May 2026 — post-incident hardening, see
# ``ai-context/integrations/ai-assistant-ai-advisor-bridge.md``):
#
# 1. ``asyncio.wait_for(..., timeout=_resolve_hard_timeout_sec(mode))``
#    inside the ``_worker()`` thread — the original safeguard. Picks
#    a per-mode budget so inspect-mode runs surface hangs faster than
#    act-mode (which legitimately runs longer).
#
# 2. An independent watchdog thread (``_start_agent_watchdog``) that
#    polls the job's ``last_activity`` field and fires earlier on
#    *inactivity* — i.e. wall-clock has not elapsed but no LLM turn /
#    tool call has updated the record in
#    ``AGENT_INACTIVITY_TIMEOUT_SEC`` seconds.  This catches the May
#    2026 incident pattern where every tool succeeded in 32 seconds
#    and the SDK then silently hung for 14+ minutes with no ``httpx``
#    POST to Anthropic ever being attempted.  ``asyncio.wait_for``
#    *should* have rescued the worker at the wall-clock boundary, but
#    in production it sometimes does not (suspected non-cancellable
#    sync I/O inside the SDK / langgraph stack).  The watchdog is
#    thread-based, independent of the asyncio event loop, and writes
#    the error to KV directly so the user sees the failure regardless
#    of whether the worker thread is ever recovered.
#
# 3. The existing stale-poll fallback in ``get_agent_job_status``
#    (``timeout + _STALE_RUNNING_BUFFER_SECONDS = 1020s``) — last
#    line of defence if all in-process safeguards somehow fail.
#
# The watchdog fires earliest in the legitimate-hang case; the
# wall-clock asyncio timeout fires next; the stale-poll is the
# emergency backstop.  All three converge on the same outcome
# (status=error in KV, audit event indexed) but with successively
# generic-er error messages.
AGENT_INSPECT_HARD_TIMEOUT_SEC = 600  # 10 min — generous over the
                                       # observed worst case (~4 min)
                                       # for inspect-mode runs.
AGENT_ACT_HARD_TIMEOUT_SEC = 900       # 15 min — unchanged for
                                       # act-mode, which legitimately
                                       # runs longer (chained
                                       # write-tool calls + retrains).
# Inactivity threshold: if no heartbeat (LLM turn or tool call) is
# recorded in this long the watchdog declares the agent stuck even
# if the wall-clock budget has not yet elapsed.
#
# Originally tuned to 180s on the assumption that LLM turns + tool
# round-trips would stay under ~90s worst case.  Production
# observation 2026-05-11 (PRD2, Feed Lifecycle Advisor act mode)
# disproved that: a single Anthropic API call under heavy load /
# bigger act-mode context took >180s, no further heartbeat fired
# (the SDK only invokes ``before_model`` once at the start of each
# LLM call), and the watchdog killed an otherwise-healthy run.
#
# Raised to 600s in tandem with the periodic heartbeat ticker
# (``_start_agent_heartbeat_ticker``) that now refreshes the
# heartbeat every ``AGENT_HEARTBEAT_TICKER_INTERVAL_SEC`` seconds
# while the worker is alive.  With the ticker, the 600s threshold
# is effectively a backstop for the edge case where the ticker
# thread itself dies (unlikely — it's a tiny daemon).  Truly hung
# SDK runs are caught by the wall-clock budget
# (``_resolve_hard_timeout_sec``: 600s inspect, 900s act) anyway.
AGENT_INACTIVITY_TIMEOUT_SEC = 600     # 10 min
# How often the heartbeat ticker (see ``_start_agent_heartbeat_ticker``)
# wakes up to refresh ``last_activity`` in KV.  Must be << the
# inactivity threshold so a single missed iteration cannot trip the
# watchdog.  30s gives a 20x margin against the 600s threshold and
# keeps the cost (one KV read+update per tick) negligible.
AGENT_HEARTBEAT_TICKER_INTERVAL_SEC = 30
# How often the watchdog wakes up to check thresholds.  Must be
# << either threshold; 15s gives ~12 checks per inspect-mode hard
# timeout window with negligible KV-read overhead.
AGENT_WATCHDOG_POLL_INTERVAL_SEC = 15

# Backwards compatibility alias — older code paths that still reference
# the single-budget constant get the conservative (longer) cap rather
# than accidentally tightening anything.  New code paths should use
# ``_resolve_hard_timeout_sec(mode)`` instead.
AGENT_RUN_HARD_TIMEOUT_SEC = AGENT_ACT_HARD_TIMEOUT_SEC


def _resolve_hard_timeout_sec(mode: str) -> int:
    """Pick the per-mode wall-clock budget.

    Wizard-time modes reason purely from a bounded payload with no tool
    calls — they should resolve far faster than either inspect or act,
    and certainly within the inspect budget. Without explicit branches
    these modes silently inherit the act-mode 900 s budget; the watchdog
    fires at 600 s but ``wait_for`` doesn't cancel until 900 s, leaving
    operators confused when debugging stuck wizard runs.

    Two wizard modes today:
      * ``generate_model`` — Feed Lifecycle Advisor, Phase 3b of issue
        #1901, fixed in PR #1914 per CodeRabbit finding.
      * ``dictionary_generate`` — FQM Advisor, parallel pre-existing
        bug surfaced by the same review (issue #1917, this fix).

    Defaults to the act-mode budget for unknown modes — safer to
    over-allocate than under-allocate for novel agent kinds.
    """
    if mode == "inspect":
        return AGENT_INSPECT_HARD_TIMEOUT_SEC
    if mode in ("generate_model", "dictionary_generate"):
        # Wizard modes: no tools, bounded payload — inspect tier matches
        # the inspect-tier token / step limits the agent runner already
        # applies for these modes.
        return AGENT_INSPECT_HARD_TIMEOUT_SEC
    return AGENT_ACT_HARD_TIMEOUT_SEC

# Per-job write coordination — eliminates TOCTOU races between
# concurrent writers to the agent-jobs KV record.  Three threads can
# write the same record: (1) the worker thread itself (terminal
# state via ``_update_agent_job``, tool-trace events via
# ``_append_job_progress``, ``before_model`` heartbeat via
# ``_refresh_agent_heartbeat``); (2) the watchdog thread (breach
# error via ``_update_agent_job``); (3) the heartbeat ticker thread
# (heartbeat via ``_refresh_agent_heartbeat``).
#
# Without this lock, the ticker's read-modify-write can overwrite a
# terminal state freshly written by the worker — the ticker's
# in-flight ``record`` dict still carries ``status="running"``, so
# its ``collection.data.update`` silently reverts the terminal write
# and leaves the job stuck in ``"running"`` with no thread
# monitoring it.  Bugbot caught this on PR #1534 cycle 1.
#
# Solution: every read-modify-write on ``kv_trackme_ai_agent_jobs``
# acquires the per-job-id lock first.  Whichever writer holds the
# lock completes its RMW cycle uninterrupted; subsequent writers
# see the result of the previous one when they re-read the record
# at the start of their critical section.  The ``_refresh_agent_
# heartbeat`` skip-if-terminal guard then short-circuits correctly.
#
# Lock lifecycle: lazy-created on first ``_get_job_write_lock``
# call; freed by ``_release_job_write_lock`` on terminal state so
# the registry stays bounded.  A worker that misses the cleanup
# (process kill, exception in the wrong layer) leaks one lock
# object until splunkd recycles the persistent_handler process —
# acceptable, the locks are ~80 bytes each.
_job_write_locks = {}
_job_write_locks_registry_lock = threading.Lock()


def _get_job_write_lock(job_id):
    """Return the lock that serialises read-modify-write on the
    agent-jobs KV record for ``job_id``.  Lazy-created on first
    request, freed by ``_release_job_write_lock`` once the job
    reaches a terminal state."""
    if not job_id:
        return None
    with _job_write_locks_registry_lock:
        lock = _job_write_locks.get(job_id)
        if lock is None:
            lock = threading.Lock()
            _job_write_locks[job_id] = lock
        return lock


def _release_job_write_lock(job_id):
    """Best-effort release of the per-job write lock from the
    registry.  Called from the terminal path of ``_update_agent_job``
    so the registry doesn't grow unbounded.  Safe to call multiple
    times.  Safe to call before all readers have released — a
    late reader will just create a fresh (uncontended) lock and
    short-circuit on the terminal-state read guard."""
    if not job_id:
        return
    with _job_write_locks_registry_lock:
        _job_write_locks.pop(job_id, None)


# Concurrency tracking
_active_agents = 0
_active_agents_lock = threading.Lock()
_released_slots = {}
_released_slots_lock = threading.Lock()


# ---------------------------------------------------------------------------
# JSON Schema helpers
# ---------------------------------------------------------------------------


def inline_schema_refs(schema: dict) -> dict:
    """Inline all ``$ref`` references in a Pydantic-generated JSON Schema.

    Anthropic's tool API rejects schemas that contain ``$ref`` pointers (they
    do not support the ``$defs``/``$ref`` JSON Schema keywords in tool input
    schemas).  Pydantic v2 emits ``$defs`` + ``$ref`` whenever a model
    contains nested BaseModel fields.  This helper resolves every ``$ref``
    against its ``$defs`` entry and inlines the definition in-place, producing
    a flat schema that Anthropic can compile.

    The function is exported so sibling advisor libraries can import and use
    it without duplicating the logic.
    """
    schema = copy.deepcopy(schema)
    defs = schema.pop("$defs", {})
    if not defs:
        return schema

    def _resolve(obj):
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_key = obj["$ref"].split("/")[-1]
                resolved = _resolve(copy.deepcopy(defs.get(ref_key, {})))
                # Merge any sibling keys (rare, but possible with allOf patterns)
                for k, v in obj.items():
                    if k != "$ref":
                        resolved[k] = _resolve(v)
                return resolved
            return {k: _resolve(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_resolve(item) for item in obj]
        return obj

    return _resolve(schema)


# ---------------------------------------------------------------------------
# ProviderStrategy compatibility shim — Anthropic AND Google
# ---------------------------------------------------------------------------
#
# BACKGROUND
# ----------
# When the Splunk Agent SDK runs against a model whose profile has
# ``structured_output: True`` it picks ``ProviderStrategy``.
# ``ProviderStrategy`` asks the underlying LangChain chat model to push the
# Pydantic output schema through the provider's *native* structured-output
# path. For TWO of our supported providers, that path is broken when the
# agent ALSO carries function/tool definitions (which every TrackMe advisor
# does — read tools at minimum, write tools in act mode):
#
# ------ Anthropic (Claude 4.x family) ------
# ProviderStrategy compiles ``output_config.format = {"type": "json_schema",
# "schema": transform_schema(...)}`` server-side. Anthropic's "structured
# output compiler" (the constrained-decoding grammar builder) is extremely
# conservative and rejects schemas that LangChain + Pydantic 2.11+ routinely
# produce, with:
#
#   anthropic.BadRequestError: 400 - "Schema is too complex for compilation.
#   Try reducing the number of tools or simplifying tool schemas."
#
# Simplifying the schema (``dict`` → ``BaseModel``, inlining ``$ref`` /
# ``$defs``) helps other providers but doesn't satisfy Anthropic's compiler.
#
# ------ Google (Gemini 2.x family) ------
# ProviderStrategy uses ``ChatGoogleGenerativeAI.with_structured_output``,
# which sets ``response_mime_type='application/json'`` on the request. The
# Gemini API documents — and enforces at runtime — that
# ``response_mime_type='application/json'`` is incompatible with function
# declarations (the agent's tools):
#
#   langchain_google_genai.chat_models.ChatGoogleGenerativeAIError:
#   Error calling model 'gemini-2.5-pro' (INVALID_ARGUMENT):
#   400 INVALID_ARGUMENT. {'error': {'code': 400, 'message':
#   "Function calling with a response mime type: 'application/json' is
#   unsupported", 'status': 'INVALID_ARGUMENT'}}
#
# (Reference: Google AI documentation. Both ``langchain-google-genai``'s
# model profile AND the Splunk SDK's ``_supports_provider_strategy`` mark
# Gemini as supporting structured_output, but neither captures the
# mutual-exclusion-with-tools constraint.)
#
# ------ The shared fix ------
# Both providers work fine when we DELIVER the output schema as an
# ordinary tool (LangChain's ``ToolStrategy`` — a synthetic ``respond``
# tool is inserted into the tool list). Tools go through a different,
# more permissive validation pipeline AND don't conflict with the
# function-calling-vs-JSON-mode constraint on Gemini.
#
# PROVIDER ISOLATION
# ------------------
# The SDK's ``_supports_provider_strategy(model)`` function drives the
# ProviderStrategy-vs-ToolStrategy choice. The SDK ships a global escape
# hatch ``_testing_force_tool_strategy`` — but flipping that affects
# *every* model in the process, so it would force ToolStrategy on a
# concurrent OpenAI or Splunk-Hosted agent too (silently downgrading them
# from their native ProviderStrategy). We want the opposite: only
# Anthropic- AND Google-backed models should be routed to ToolStrategy;
# OpenAI, Azure, Splunk Hosted, Mistral, Ollama etc. must keep their
# native behaviour even when running concurrently with an Anthropic or
# Gemini agent.
#
# We therefore monkey-patch ``_lc_engine._supports_provider_strategy``
# with a *filter* that returns False for Anthropic- AND Google-backed
# models and defers to the original function for everything else. The
# patch is activated by the first affected agent entering the context
# and removed by the last one leaving (reference-counter under a lock,
# so concurrent Anthropic/Google agents share the installed patch
# correctly).


def _is_anthropic_model(model) -> bool:
    """Detect whether a LangChain chat model is Anthropic-backed.

    Checked by class name + module prefix, which covers ChatAnthropic and
    its subclasses without pulling langchain_anthropic into the import
    graph of this module (the SDK is Python 3.13-only; importing
    langchain_anthropic from here would break py3.9 callers that still
    import this module for job-status polling).
    """
    cls = type(model)
    if cls.__name__.startswith("ChatAnthropic"):
        return True
    mod = (cls.__module__ or "").lower()
    return mod.startswith("langchain_anthropic") or "langchain_anthropic." in mod


def _is_google_model(model) -> bool:
    """Detect whether a LangChain chat model is Google/Gemini-backed.

    Symmetric to ``_is_anthropic_model``. Matches ``ChatGoogleGenerativeAI``
    and its subclasses via class name + module prefix, so we don't take
    a hard import dependency on ``langchain_google_genai`` from this
    module (kept py3.9-importable — see the Anthropic helper above).
    """
    cls = type(model)
    if cls.__name__.startswith("ChatGoogleGenerativeAI"):
        return True
    mod = (cls.__module__ or "").lower()
    return mod.startswith("langchain_google_genai") or "langchain_google_genai." in mod


# Providers that need ToolStrategy forcing — see the module-level
# explanatory comment above for the per-provider rationale.
_PROVIDERS_NEEDING_TOOL_STRATEGY = frozenset({"anthropic", "google"})


# Thread-safe state backing ``force_tool_strategy_for_provider``.
#
# Agent invocations run in concurrent ``threading.Thread`` instances (up
# to ``_MAX_CONCURRENT_AGENTS_DEFAULT = 5``). We reference-count entries
# under a lock so concurrent affected agents (Anthropic + Google in any
# combination) share a single installed patch, and so the patch is only
# removed once the last active invocation exits (the first to enter
# captures the original function; the last to leave restores it).
_force_tool_strategy_lock = threading.Lock()
_force_tool_strategy_refcount = 0
_force_tool_strategy_original_fn = None  # original _supports_provider_strategy


@contextlib.contextmanager
def force_tool_strategy_for_provider(provider_type: str):
    """Force SDK ``ToolStrategy`` for Anthropic- and Google-backed models,
    bypassing the per-provider structured-output paths that are broken
    when tools are present. No-op for every other provider.

    Thread-safe **and provider-isolated**:

    * Concurrent affected agents (Anthropic + Google in any combination)
      share the installed patch via a reference counter. The patch is
      only removed once the last active invocation exits.
    * Concurrent unaffected agents (OpenAI, Azure, Splunk Hosted,
      Mistral, Ollama…) keep their native ``ProviderStrategy`` path —
      the patch filters by model instance class, not by a process-wide
      toggle.
    """
    if (provider_type or "").lower() not in _PROVIDERS_NEEDING_TOOL_STRATEGY:
        yield
        return

    try:
        import splunklib.ai.engines.langchain as _lc_engine
    except ImportError:
        # SDK unavailable (py3.9 import path) — caller will fail later anyway
        yield
        return

    global _force_tool_strategy_refcount, _force_tool_strategy_original_fn

    with _force_tool_strategy_lock:
        if _force_tool_strategy_refcount == 0:
            # First affected agent to enter: capture the current
            # ``_supports_provider_strategy`` binding and install the
            # filtering wrapper. ``original_fn`` is captured as a
            # closure variable so the wrapper can delegate to it
            # independently of later patching attempts.
            original_fn = _lc_engine._supports_provider_strategy
            _force_tool_strategy_original_fn = original_fn

            def _filtered_supports_provider_strategy(model):
                # Anthropic- AND Google-backed models: force ToolStrategy
                # by reporting "does not support provider strategy".
                # Every other provider falls through to the original
                # logic, preserving native structured-output behaviour
                # for concurrent OpenAI/Azure/Splunk-Hosted agents.
                if _is_anthropic_model(model):
                    return False
                if _is_google_model(model):
                    return False
                return original_fn(model)

            _lc_engine._supports_provider_strategy = _filtered_supports_provider_strategy
            _log().info(
                "Installed Anthropic+Google ToolStrategy filter on SDK "
                "_supports_provider_strategy (concurrent OpenAI / Azure / "
                "Splunk-Hosted / Mistral / Ollama agents keep their "
                "native ProviderStrategy path)"
            )
        _force_tool_strategy_refcount += 1

    try:
        yield
    finally:
        with _force_tool_strategy_lock:
            _force_tool_strategy_refcount -= 1
            if _force_tool_strategy_refcount <= 0:
                # Last affected agent out: restore the original
                # function. Clamp the counter at 0 in case of an
                # off-by-one under exception paths — better to unpatch
                # once too many than to drift into negative territory
                # and pin the patch forever.
                _force_tool_strategy_refcount = 0
                if _force_tool_strategy_original_fn is not None:
                    _lc_engine._supports_provider_strategy = _force_tool_strategy_original_fn
                    _force_tool_strategy_original_fn = None


# Backwards-compat alias — the original symbol name. Every advisor
# imports ``force_tool_strategy_for_anthropic`` by name; keeping the
# alias means the rollout doesn't need to touch the import lines (the
# helper is now provider-generic; the only thing that changed is which
# providers it filters).
#
# Both names point at the same underlying function so the refcount /
# patch state is shared regardless of which name a caller uses.
force_tool_strategy_for_anthropic = force_tool_strategy_for_provider


# ---------------------------------------------------------------------------
# Per-HTTP-call timeout patch for langchain chat-model constructors (#1748-family)
# ---------------------------------------------------------------------------
#
# BACKGROUND
# ----------
# The Splunk Agent SDK's predefined model dataclasses
# (``AnthropicModel`` / ``OpenAIModel`` / ``GoogleModel`` in
# ``splunklib.ai.model``) are ``frozen=True`` dataclasses with explicit
# field lists. Two of the three have no ``timeout`` field at all, and the
# SDK's ``_create_langchain_model`` in
# ``splunklib.ai.engines.langchain`` builds the underlying langchain
# chat-model with a fixed kwarg set — there is no override surface.
#
# When the SDK omits ``timeout``, the underlying provider SDKs default to
# ``600s``: ``anthropic.Anthropic(timeout=600.0)``,
# ``openai.OpenAI(timeout=600.0)``, ``google.generativeai`` similar.
# Combined with our outer ``asyncio.wait_for(_run_*_advisor_agent, …,
# timeout=600/900s)``, a single network blip or stalled HTTP response
# blocks the worker for up to 10 minutes before *anything* surfaces. The
# user stares at the spinner with no feedback.
#
# Until the SDK exposes a timeout knob upstream, we monkey-patch the
# three langchain chat-model ``__init__`` methods at module load to
# inject a default timeout when the caller didn't set one.
#
# All three classes expose ``timeout`` as a pydantic field (or alias for
# ``default_request_timeout`` / ``request_timeout``), so passing
# ``timeout=`` uniformly works for every provider.
#
# SCOPE / ISOLATION
# -----------------
# The patch is process-wide on the langchain *class*, but only affects
# instances that the Agent SDK creates. ``trackme_libs_ai.py`` (the AI
# Assistant chat path) uses ``requests`` directly — no langchain — so
# it is unaffected. Idempotent: the wrapper is flagged with
# ``_trackme_timeout_patched`` so a re-import (under test, or after a
# splunkd reload) doesn't stack patches.
#
# CHOOSING 90 SECONDS
# -------------------
# Empirically: Anthropic / OpenAI / Google responses for an agent-style
# call that already finished its tool round-trips return in <30s under
# normal load. 90s gives ~3x headroom for slow-LLM thinking on very
# long contexts while still failing fast enough that the user gets a
# retry within a minute. Combined with ``_transient_retry_backoff_sec``
# the worst-case user wait for a recoverable blip is roughly
# ``90 + 5 = 95s`` before the second attempt starts — vs the previous
# 10 minutes.

_PER_CALL_HTTP_TIMEOUT_SEC = 90.0


def _install_per_call_timeout_on_langchain_models(timeout_seconds=None):
    """Patch langchain chat-model ``__init__`` to default ``timeout=`` when caller didn't set one.

    Called once at module load. Idempotent under re-import.
    """
    import importlib as _importlib

    if timeout_seconds is None:
        timeout_seconds = _PER_CALL_HTTP_TIMEOUT_SEC

    # All three accept ``timeout=`` (directly for Google, as a pydantic
    # alias for the other two).
    #
    # The whole per-provider block is wrapped in ``except Exception``
    # rather than ``(ImportError, AttributeError)``. The patch is a
    # best-effort optimisation — if it fails for any reason (provider
    # package missing on a py3.9 deployment that still imports this
    # module for job-status polling, langchain class signature drifted
    # in a way that breaks our ``getattr``, pydantic refusing the
    # synthetic kwarg under an unexpected version pin, …) the LLM call
    # falls back to the SDK's default 600s timeout, which is the
    # pre-fix behaviour. Better to silently skip the optimisation than
    # to break ``import trackme_libs_ai_agents`` entirely. The Agent
    # SDK itself does the same — lazy imports under broad except.
    for module_name, class_name in [
        ("langchain_anthropic", "ChatAnthropic"),
        ("langchain_openai", "ChatOpenAI"),
        ("langchain_google_genai", "ChatGoogleGenerativeAI"),
    ]:
        try:
            mod = _importlib.import_module(module_name)
            cls = getattr(mod, class_name)

            original_init = cls.__init__
            if getattr(original_init, "_trackme_timeout_patched", False):
                continue  # already patched — re-import safety

            def _build_patched_init(orig_init):
                def __init__(self, **kwargs):
                    # Respect any explicit timeout the caller set
                    # (under any of the three known field names). Only
                    # inject when none is present.
                    explicit = any(
                        k in kwargs
                        for k in (
                            "timeout",
                            "default_request_timeout",
                            "request_timeout",
                        )
                    )
                    if not explicit:
                        kwargs["timeout"] = timeout_seconds
                    orig_init(self, **kwargs)

                __init__._trackme_timeout_patched = True
                return __init__

            cls.__init__ = _build_patched_init(original_init)
        except Exception as patch_err:
            # Best-effort: a failure here means the LLM call falls back
            # to the SDK's default 600s timeout. Not great, but the
            # module-load path must never break — REST handlers also
            # import this module on python3.9 to poll job status, and
            # an ImportError on a langchain package (which itself
            # requires py3.10+) would block status polling on legacy
            # deployments.
            #
            # Emit a low-noise debug breadcrumb so operators investigating
            # "why are LLM calls still hanging for 600s?" can see which
            # provider patch silently fell through. DEBUG-level so it
            # doesn't pollute INFO logs on every module reload; wrapped
            # in its own try/except so an unexpected logger problem
            # cannot itself crash the module load.
            try:
                _log().debug(
                    "Per-call timeout patch skipped for %s.%s: %s: %s — "
                    "LLM calls via this provider will use the SDK's "
                    "default 600s timeout.",
                    module_name,
                    class_name,
                    type(patch_err).__name__,
                    patch_err,
                )
            except Exception:
                pass
            continue


# Apply at module load. ``trackme_libs_ai_agents`` is imported lazily by
# REST handlers and again by worker threads — the idempotency guard
# makes that safe.
_install_per_call_timeout_on_langchain_models()


# ---------------------------------------------------------------------------
# Tool-call tracing middleware
# ---------------------------------------------------------------------------
#
# Problem: the existing agent bookend logs (``<advisor> agent starting:
# mode=..., model=...`` and ``<advisor> agent completed: mode=...,
# token_count=..., steps=...``) tell the operator what the overall run
# looked like, but nothing between those two lines — so a run that takes
# 2 minutes looks indistinguishable from one that hangs.  Specifically,
# there is no trace when the agent calls a tool, how long each tool took,
# or whether a tool errored.
#
# This middleware wraps the LangChain ``awrap_tool_call`` hook at INFO
# level.  For every tool the agent invokes it emits:
#
#   - one line at call start, naming the tool and a compact arg summary
#   - one line at call end, with success/error status, duration, and a
#     truncated preview of the result
#
# INFO-level (not DEBUG) because this is the operational visibility
# operators asked for.  The preview is capped aggressively (~200 chars)
# to keep log lines grep-friendly — full tool results are available in
# the indexed advisor events when deeper forensics are needed.
#
# Failure modes: the middleware catches its own exceptions so a
# tracing failure can never take down a real agent run.


def enrich_agent_event_for_audit(
    event: dict,
    *,
    result_dict: dict | None,
    user: str | None,
    automated: bool,
    duration_ms: int | None,
) -> dict:
    """Add the audit-dashboard top-level fields to an agent event payload.

    Mutates and returns ``event``.  Centralised so every advisor runner
    surfaces the same field shape for the AI Advisor audit dashboard's SPL queries.

    Fields added:
      - ``user``                 — calling Splunk user (or ``"automated"`` /
                                   ``"unknown"`` fallbacks)
      - ``duration_ms``          — end-to-end run wall time in milliseconds
      - ``recommendations_count`` — number of items in ``result.recommendations``
      - ``actions_taken_count``  — number of items in ``result.actions_taken``
      - ``entity_status``        — top-level mirror of ``result.entity_status``

    All extra fields are top-level so the audit dashboard can ``stats`` /
    ``timechart`` over them without resorting to ``spath`` against the
    nested ``result`` JSON, which is expensive at scale.
    """
    if user:
        event["user"] = user
    elif automated:
        event["user"] = "automated"
    else:
        event["user"] = "unknown"

    if duration_ms is not None:
        try:
            event["duration_ms"] = int(duration_ms)
        except (ValueError, TypeError):
            pass

    if isinstance(result_dict, dict):
        recs = result_dict.get("recommendations")
        if isinstance(recs, list):
            event["recommendations_count"] = len(recs)
        acts = result_dict.get("actions_taken")
        if isinstance(acts, list):
            event["actions_taken_count"] = len(acts)
        es = result_dict.get("entity_status")
        if isinstance(es, str) and es:
            event["entity_status"] = es

    return event


# ---------------------------------------------------------------------------
# Prompt-cache middleware (Anthropic only)
# ---------------------------------------------------------------------------
#
# Anthropic Claude supports prompt caching — every advisor invocation
# re-sends the same large system prompt (2.6K–6.4K tokens depending on
# the advisor), and the four high-volume automated advisors (Feed
# Lifecycle, FQM, Component Health, ML) run 100s–1000s of times per day
# per tenant.  Caching the system prompt saves ~75% on those tokens
# after the first call within the cache TTL window.
#
# Mechanism: Anthropic's API treats ``cache_control: {"type": "ephemeral"}``
# markers on system / tool / user content blocks as cache-pin
# instructions.  ``langchain-anthropic`` passes content-block lists
# through unchanged, so we can opt the system prompt into caching by
# rewriting its ``.content`` from a plain string to a single-element
# content-block list with the marker attached.
#
# Other providers benefit from prompt caching too, but differently:
#   * OpenAI / Azure OpenAI: automatic since Oct 2024, no client config.
#   * Google Vertex / Gemini: implicit caching since May 2025; explicit
#     ``CachedContent`` API for guaranteed caching is a follow-up.
#   * Mistral / Ollama / Splunk Hosted: no client-side caching surface.
#
# This middleware is therefore Anthropic-specific.  ``provider_type !=
# "anthropic"`` → factory returns ``None`` (the middleware list filters
# ``None`` out, so the active middleware list is unchanged for every
# other provider).
#
# Provider-level opt-out: ``ai_provider.ai_prompt_caching_enabled = 0``
# returns ``None`` even for Anthropic providers, letting an admin
# disable the feature without redeploying if billing or compatibility
# surprises appear.  Default ``1`` so existing tenants get the savings
# automatically on next advisor run.
#
# Failure modes: best-effort.  A caching failure must never break the
# LLM call.  All exceptions are swallowed; the worst case is "no cache
# this turn, falls back to the existing uncached path".


def make_prompt_cache_middleware(provider_type, config=None):
    """Build a ``before_model`` middleware that injects Anthropic
    ``cache_control`` markers onto the system message of every LLM
    round-trip when:
      1. the active provider is Anthropic, AND
      2. the provider stanza has ``ai_prompt_caching_enabled != 0``
         (the field defaults to ``1`` in ``trackme_ai_provider_default``;
         absent or empty → treat as enabled).

    Returns the middleware function (decorated with ``@before_model``)
    on success, or ``None`` when caching is not applicable.  Callers
    add it to their ``middleware=[...]`` list under a ``[mw for mw in
    [...] if mw is not None]`` filter (same pattern as
    ``make_tool_trace_middleware``).

    Args:
        provider_type: TrackMe's provider type string (``"anthropic"``,
            ``"openai"``, ``"azure_openai"``, ``"google"``, ``"mistral"``,
            ``"ollama"``, ``"splunk_hosted"``).  Case-insensitive.
        config: Optional AI provider config dict (as returned by the
            provider lookup).  Inspected for
            ``ai_prompt_caching_enabled`` only.  When ``None``, defaults
            to enabled — keeps the helper testable without a full config
            blob.
    """
    if (provider_type or "").lower() != "anthropic":
        return None

    # Opt-out gate.  ``ai_prompt_caching_enabled`` may be missing
    # (older provider records pre-dating this field) or stored as a
    # string by UCC.  Coerce defensively: absent / empty / "1" / 1 →
    # enabled; "0" / 0 → disabled.
    if config is not None:
        raw = config.get("ai_prompt_caching_enabled")
        if raw not in (None, ""):
            try:
                if int(raw) == 0:
                    return None
            except (TypeError, ValueError):
                # Garbage in the field → treat as enabled rather than
                # opt-out, so a typo can't silently disable the feature.
                pass

    try:
        from splunklib.ai.hooks import before_model
    except ImportError:
        # SDK unavailable (py3.9 import path) — caller will fail at
        # Agent instantiation anyway.  Return None so the middleware
        # list filter drops us cleanly.
        return None

    # Anthropic minimum cache size: 1024 tokens.  ~4 chars per token
    # heuristic (matches what ``_capture_usage`` uses).  Below the
    # threshold, the cache_control marker is rejected by the API.
    _MIN_CACHE_CHARS = 4096

    # One-shot INFO log per agent run so operators can confirm the
    # middleware actually fired (cache savings themselves are visible
    # in the Anthropic console).  Closure-scoped flag avoids spamming
    # the log on multi-step runs (one rewrite per LLM turn × 5-15 turns
    # would be noise; one line per run is the right signal).
    _logged_once = [False]

    @before_model
    def _inject_anthropic_cache_markers(req: "_ModelRequest") -> None:
        # The Splunk Agent SDK surfaces the system prompt as
        # ``ModelRequest.system_message`` — a SEPARATE field from
        # ``state.messages`` (which only holds conversation history:
        # human/AI/tool messages).  Initial implementations of this
        # middleware looked at ``state.messages[0]`` and silently no-op'd
        # because the system message is never there; the SDK contract
        # is ``ModelRequest(system_message: str, state: AgentState)``.
        # The SDK then converts back to LangChain via
        # ``LC_SystemMessage(content=request.system_message)`` (see
        # ``splunklib/ai/engines/langchain.py:_convert_model_request_to_lc``),
        # so if we mutate ``system_message`` to a content-block list,
        # ``langchain-anthropic`` passes it through to Anthropic's API
        # in the cache_control-aware ``system: [content_blocks]`` form.
        #
        # ``ModelRequest`` is a frozen dataclass, so direct attribute
        # assignment raises FrozenInstanceError.  ``object.__setattr__``
        # bypasses the freeze.  Mutation is local to this one LLM call
        # (each model_middleware invocation gets a fresh request); the
        # marker re-injects on every call, which is exactly what
        # Anthropic needs for cache hits to actually fire.
        try:
            sys_text = getattr(req, "system_message", None)
            if isinstance(sys_text, list):
                # Already in content-block form (somebody upstream beat
                # us to it).  Idempotent no-op.
                return
            if not isinstance(sys_text, str) or len(sys_text) < _MIN_CACHE_CHARS:
                return
            new_content = [
                {
                    "type": "text",
                    "text": sys_text,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
            object.__setattr__(req, "system_message", new_content)
            if not _logged_once[0]:
                _logged_once[0] = True
                _log().info(
                    "Anthropic prompt-cache marker injected on system "
                    "prompt (length=%d chars). Savings visible in the "
                    "Anthropic console under cache_creation_input_tokens "
                    "/ cache_read_input_tokens.",
                    len(sys_text),
                )
        except Exception:
            # Never break the LLM call on a caching glitch.  The cache
            # marker is an opt-in optimisation; the uncached path
            # remains correct and is the fallback.
            pass

    return _inject_anthropic_cache_markers


def make_tool_trace_middleware(
    advisor_name: str,
    job_id=None,
    service=None,
    *,
    advisor_kind: str | None = None,
    tenant_id: str | None = None,
    component: str | None = None,
    object_name: str | None = None,
    object_id: str | None = None,
    mode: str | None = None,
    automated: bool = False,
    summary_index: str | None = None,
    server_name: str | None = None,
):
    """Build a Splunk Agent SDK ``AgentMiddleware`` that logs tool calls at
    INFO level, persists a live progress feed to the agent's job record
    (when ``job_id`` and ``service`` are supplied) AND emits a structured
    per-tool-call event to the tenant's summary index (when ``service``
    + ``tenant_id`` + ``summary_index`` are supplied) so the audit
    dashboard can chart tool usage and timing.

    Returns an ``AgentMiddleware`` instance suitable for adding to the
    ``middleware=[...]`` list of a ``splunklib.ai.Agent``, or ``None`` if
    the SDK is unavailable (py3.9 import path — AI agents are py3.13 only
    and the caller will fail on Agent instantiation anyway).

    IMPORTANT: the SDK's middleware chain calls ``tool_middleware(request,
    handler)`` on each registered middleware — it does NOT call
    LangChain's ``awrap_tool_call``.  An earlier version of this helper
    subclassed LangChain's ``AgentMiddleware`` and overrode
    ``awrap_tool_call``, which silently never fired (Cursor Bugbot HIGH
    finding on PR #1128).  The correct base class is
    ``splunklib.ai.middleware.AgentMiddleware`` and the correct override
    is ``tool_middleware``.

    Args:
        advisor_name: Short human-readable label used as the prefix in
            each log line (e.g. "ML Advisor", "FQM Advisor").  Makes it
            easy to grep a tenant's log for a specific advisor's tool
            activity even when log files are shared.
        job_id: Optional. The agent job's ``_key`` in
            ``kv_trackme_ai_agent_jobs``.  When provided together with
            ``service``, every tool start / end event is also persisted
            to that job record's ``progress`` field so the UI can poll
            and render a live activity feed.  Best-effort — failures are
            swallowed and only logged at DEBUG.
        service: Optional. A ``splunklib.client.Service`` bound to the
            ``trackme`` app/owner context.  Required alongside ``job_id``
            for progress persistence and alongside ``summary_index`` for
            structured tool-call event emission.
        advisor_kind: Optional. Short identifier for the advisor used as
            the ``advisor`` field on the structured tool-call event
            (e.g. ``"ml_advisor"``, ``"fqm_advisor"``).  Required for
            tool-call event emission.
        tenant_id, component, object_name, object_id, mode, automated:
            Optional. Run-context fields included on each emitted
            tool-call event so the audit dashboard can drill down per
            tenant / component / object / mode.
        summary_index: Optional. Tenant-resolved summary index name.
            When provided alongside ``service`` and ``advisor_kind``,
            every tool-call end emits a JSON event with sourcetype
            ``trackme:ai_agent:tool_call`` for ``stats avg(duration_ms)
            by tool`` aggregation in the dashboard.
    """
    try:
        from splunklib.ai.middleware import (
            AgentMiddleware as _SDK_AgentMiddleware,
            ToolRequest,
            ToolResponse,
            ToolMiddlewareHandler,
        )
    except ImportError:
        return None

    def _emit_tool_call_event(tool, status, duration_ms, result_size=None, error=None):
        """Emit a structured per-tool-call event to the tenant summary index.

        No-op unless ``service``, ``advisor_kind`` and ``summary_index`` were
        all provided to the middleware factory.  Best-effort — tracing
        failures must never take down a real agent run, so every error is
        swallowed at DEBUG.

        Sourcetype is ``trackme:ai_agent:tool_call`` so the audit dashboard
        can ``stats avg(duration_ms), p95(duration_ms), count by tool`` and
        chart per-tool latency / call volume across tenants.

        This function performs synchronous HTTP (``service.indexes[…]`` GET
        + ``target.submit()`` POST) so callers in the async middleware
        wrap it in ``asyncio.to_thread`` via ``_fire_audit_event`` —
        otherwise the event loop blocks ~100–300 ms per tool call,
        adding seconds of dead time across a 10–20 tool agent run.
        """
        if service is None or not advisor_kind or not summary_index:
            return
        try:
            # ``object_category`` mirrors the field carried by every other
            # advisor result sourcetype (``splk-flx`` / ``splk-dsm`` /
            # ``splk-wlk`` / …) — derived from ``component`` with the
            # ``splk-`` prefix so SPL searches and the
            # ``trackme_indexed_json_object_category`` indexed-time
            # transform behave identically across the advisor sourcetypes
            # and the per-tool-call audit sourcetype.
            event = {
                "ts": time.time(),
                "advisor": advisor_kind,
                "tool": tool,
                "status": status,
                "duration_ms": duration_ms,
                "tenant_id": tenant_id or "",
                "component": component or "",
                "object_category": f"splk-{component}" if component else "",
                "object": object_name or "",
                "object_id": object_id or "",
                "mode": mode or "",
                "automated": bool(automated),
                "job_id": job_id or "",
            }
            if result_size is not None:
                event["result_size"] = int(result_size)
            if error is not None:
                event["error"] = str(error)[:500]
            target = service.indexes[summary_index]
            # Pass ``host`` when the caller resolved it — keeps tool-call
            # events consistent with terminal events (which all carry the
            # originating search head's serverName) so SH-cluster
            # deployments can correlate tool calls back to a specific SH.
            submit_kwargs = {
                "event": json.dumps(event),
                "source": f"trackme:ai_agent:{advisor_kind}",
                "sourcetype": "trackme:ai_agent:tool_call",
            }
            if server_name:
                submit_kwargs["host"] = server_name
            target.submit(**submit_kwargs)
        except Exception as e:
            try:
                _log().debug(
                    f"[{advisor_name}] _emit_tool_call_event failed for tool={tool}: {e}"
                )
            except Exception:
                pass

    # Fire-and-forget audit task tracking — keeps strong refs so the GC
    # doesn't kill in-flight tasks, and the done-callback removes them on
    # completion.  See https://docs.python.org/3/library/asyncio-task.html
    # ("Important: Save a reference to the result of [create_task] …").
    _pending_audit_tasks: set = set()

    def _fire_audit_event(tool, status, duration_ms, result_size=None, error=None):
        """Schedule the tool-call audit event without blocking the agent loop.

        Runs ``_emit_tool_call_event`` in the default thread executor via
        ``asyncio.to_thread``.  Must be called from within a running event
        loop (i.e. from the async middleware) — calling from sync code
        will raise ``RuntimeError`` from ``asyncio.create_task``.
        """
        if service is None or not advisor_kind or not summary_index:
            return  # short-circuit before spawning a no-op task
        try:
            task = asyncio.create_task(
                asyncio.to_thread(
                    _emit_tool_call_event, tool, status, duration_ms,
                    result_size=result_size, error=error,
                )
            )
            _pending_audit_tasks.add(task)
            task.add_done_callback(_pending_audit_tasks.discard)
        except RuntimeError:
            # No running loop — fall back to inline emission so we still
            # capture the event (this branch is only hit if the middleware
            # is invoked from sync code, which the SDK contract forbids).
            _emit_tool_call_event(
                tool, status, duration_ms,
                result_size=result_size, error=error,
            )

    def _summarise_args(args):
        """Compact, grep-friendly arg summary for a tool call.

        Truncates each value at ~40 chars and the whole string at ~200.
        """
        if not isinstance(args, dict):
            return repr(args)[:200]
        parts = []
        for k, v in args.items():
            rv = repr(v)
            if len(rv) > 40:
                rv = rv[:37] + "..."
            parts.append(f"{k}={rv}")
        joined = ", ".join(parts)
        if len(joined) > 200:
            joined = joined[:197] + "..."
        return joined

    def _summarise_content(content) -> tuple[int, str]:
        """Return ``(size_bytes, preview)`` for a tool ``ToolResult.content``.

        ``ToolResult.content`` is defined as ``str`` on the SDK side, but we
        stay defensive in case a future SDK release widens the type.
        """
        try:
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = " | ".join(
                    getattr(p, "text", None) or (p.get("text", "") if isinstance(p, dict) else str(p))
                    for p in content
                )
            elif content is None:
                return 0, ""
            else:
                text = str(content)
            size = len(text)
            if len(text) > 200:
                text = text[:197] + "..."
            # Scrub newlines so one tool call = one log line
            text = text.replace("\n", " ").replace("\r", " ")
            return size, text
        except Exception:
            return -1, "<unreadable>"

    class _ToolTraceMiddleware(_SDK_AgentMiddleware):
        """SDK AgentMiddleware subclass that traces every tool call.

        Override signature matches ``splunklib.ai.middleware.AgentMiddleware.tool_middleware``
        exactly: ``(request: ToolRequest, handler: ToolMiddlewareHandler) -> ToolResponse``.
        """

        async def tool_middleware(
            self,
            request: ToolRequest,
            handler: ToolMiddlewareHandler,
        ) -> ToolResponse:
            # ToolRequest carries ``call: ToolCall`` and ``state: AgentState``.
            # ToolCall has ``name``, ``args: dict``, ``id``, ``type``.
            call = getattr(request, "call", None)
            tool_name = getattr(call, "name", None) or "<unknown>"
            args = getattr(call, "args", None) or {}

            args_summary = _summarise_args(args)
            t0 = time.time()
            try:
                _log().info(
                    f"[{advisor_name}] tool call start: "
                    f"name={tool_name} args={{{args_summary}}}"
                )
            except Exception:
                pass

            # Persist a "tool_call_start" progress event for the UI feed.
            _append_job_progress(service, job_id, {
                "ts": t0,
                "event": "tool_call_start",
                "tool": tool_name,
                "args": args_summary,
            })

            try:
                response = await handler(request)
            except Exception as e:
                duration_ms = int((time.time() - t0) * 1000)
                try:
                    # Tool raised an uncaught exception — a real failure.
                    # Use ERROR (not WARNING) so this surfaces in error
                    # monitoring alongside other tool failures.
                    _log().error(
                        f"[{advisor_name}] tool call end: "
                        f"name={tool_name} status=error duration_ms={duration_ms} "
                        f"error={type(e).__name__}: {str(e)[:200]}"
                    )
                except Exception:
                    pass
                # Wrap both side-effect calls — must never let a tracing /
                # audit failure mask the real tool exception.  Matches the
                # ``try/except pass`` pattern around the ``logging.warning``
                # above.
                try:
                    _append_job_progress(service, job_id, {
                        "ts": time.time(),
                        "event": "tool_call_end",
                        "tool": tool_name,
                        "status": "error",
                        "duration_ms": duration_ms,
                        "error": f"{type(e).__name__}: {str(e)[:200]}",
                    })
                except Exception:
                    pass
                try:
                    _fire_audit_event(
                        tool_name, "error", duration_ms,
                        error=f"{type(e).__name__}: {str(e)[:200]}",
                    )
                except Exception:
                    pass
                raise

            duration_ms = int((time.time() - t0) * 1000)
            # ToolResponse.result is either ToolResult (with ``content: str``,
            # ``structured_content``) on success or ToolFailureResult (with
            # ``error_message``) on a non-fatal tool failure.  Distinguish
            # via presence of the ``error_message`` attribute.
            result = getattr(response, "result", None)
            err_msg = getattr(result, "error_message", None) if result is not None else None

            # Each side-effect (log line / progress write / audit emit)
            # gets its own try/except so a KV Store outage on
            # ``_append_job_progress`` doesn't suppress the audit
            # dashboard event from ``_fire_audit_event`` — they need to
            # fail independently, mirroring the error path above.
            if err_msg is not None:
                # Non-fatal tool failure — the exception path above caught
                # fatal exceptions; this branch handles the structured
                # "tool returned an error" case (the SDK catches
                # exceptions raised inside tool bodies and converts them
                # to ToolFailureResult, so a Python error inside a tool
                # also lands here).  This is still a real failure from
                # the operator's perspective — use ERROR so it surfaces
                # in error monitoring.  ``manage_entity_labels``'s
                # ``'list' object has no attribute 'get'`` regression
                # (PR #1504) was easy to miss precisely because it
                # logged at WARNING.
                try:
                    _log().error(
                        f"[{advisor_name}] tool call end: "
                        f"name={tool_name} status=tool_failure duration_ms={duration_ms} "
                        f"error_message={str(err_msg)[:200]!r}"
                    )
                except Exception:
                    pass
                try:
                    _append_job_progress(service, job_id, {
                        "ts": time.time(),
                        "event": "tool_call_end",
                        "tool": tool_name,
                        "status": "tool_failure",
                        "duration_ms": duration_ms,
                        "error_message": str(err_msg)[:200],
                    })
                except Exception:
                    pass
                try:
                    _fire_audit_event(
                        tool_name, "tool_failure", duration_ms,
                        error=str(err_msg)[:200],
                    )
                except Exception:
                    pass
            else:
                content = getattr(result, "content", None) if result is not None else None
                # ``_summarise_content`` is internally exception-safe.
                size, preview = _summarise_content(content)
                try:
                    _log().info(
                        f"[{advisor_name}] tool call end: "
                        f"name={tool_name} status=success duration_ms={duration_ms} "
                        f"result_size={size} preview={preview!r}"
                    )
                except Exception:
                    pass
                try:
                    _append_job_progress(service, job_id, {
                        "ts": time.time(),
                        "event": "tool_call_end",
                        "tool": tool_name,
                        "status": "success",
                        "duration_ms": duration_ms,
                        "result_size": size,
                    })
                except Exception:
                    pass
                try:
                    _fire_audit_event(
                        tool_name, "success", duration_ms,
                        result_size=size,
                    )
                except Exception:
                    pass
            return response

    return _ToolTraceMiddleware()


# ---------------------------------------------------------------------------
# Pydantic Output Schemas
# ---------------------------------------------------------------------------


class AnomalyWindow(BaseModel):
    """A detected anomaly time window in an entity's metric data."""
    start_epoch: int = Field(description="Start of anomaly window (Unix epoch seconds)")
    end_epoch: int = Field(description="End of anomaly window (Unix epoch seconds), 0 if ongoing")
    start_human: str = Field(description="Human-readable start time")
    end_human: str = Field(description="Human-readable end time, or 'ongoing'")
    description: str = Field(description="Brief description of what happened in this window")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence that this is a genuine anomaly (0.0-1.0)"
    )


class AgentAction(BaseModel):
    """A single action executed by an AI agent via a write tool.

    Structured replacement for ``list[dict]`` fields — required because
    Pydantic 2.11+ emits ``additionalProperties: true`` for bare ``dict``
    fields, which Anthropic's structured output compiler rejects with
    "Schema is too complex for compilation" (the compiler flips
    ``additionalProperties`` to ``false`` and is then unable to emit any
    valid value for the now-empty object).  A concrete ``BaseModel`` gives
    Anthropic a deterministic schema it can compile.
    """
    tool: str = Field(description="Name of the write tool that was called")
    status: str = Field(description="'success' or 'error'")
    description: str = Field(description="Brief description of what was done")
    result: str = Field(
        default="",
        description="Short summary of the tool's response (free-form text or JSON snippet)",
    )


class ModelRecommendation(BaseModel):
    """A recommendation for improving an ML outlier model."""
    recommendation_type: str = Field(
        description=(
            "Type of recommendation: 'period_exclusion' (exclude anomaly window from training), "
            "'config_change' (tune model parameters), 'false_positive' (suppress current alert), "
            "'retrain' (retrain model), 'no_action' (model is healthy)"
        )
    )
    priority: str = Field(description="Priority: 'high', 'medium', or 'low'")
    description: str = Field(description="Human-readable description of the recommendation")
    details: str = Field(
        default="",
        description=(
            "Type-specific details, serialised as a JSON object string. "
            "Examples: '{\"time_factor\": \"%H\", \"density_threshold\": 0.005}' for config_change; "
            "'{\"start_epoch\": 1760000000, \"end_epoch\": 1760086400}' for period_exclusion. "
            "Use an empty string when no details are needed."
        ),
    )


class MLAdvisorResult(BaseModel):
    """Structured output from the ML Outlier Advisor agent."""
    summary: str = Field(description="2-3 sentence executive summary of the analysis")
    entity_status: str = Field(
        description=(
            "Overall entity assessment: 'healthy' (model working correctly), "
            "'anomaly_detected' (genuine anomaly found), "
            "'model_needs_tuning' (model config should be improved), "
            "'false_positive' (current alert is a false positive)"
        )
    )
    anomaly_windows: list[AnomalyWindow] = Field(
        default_factory=list,
        description="Detected anomaly time windows"
    )
    recommendations: list[ModelRecommendation] = Field(
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
        """Return a flat ``$ref``/``$defs``-free JSON Schema.

        Anthropic's structured-output compiler reports "Schema is too complex
        for compilation" when the ``output_config.format`` schema references
        nested BaseModel types via ``$ref``/``$defs`` (even small schemas
        trip it).  Inlining every reference produces a self-contained tree
        that Anthropic can compile without issue, and has the harmless
        side-effect of also being compatible with providers that do not
        support ``$ref`` (Ollama, Mistral).
        """
        return inline_schema_refs(super().model_json_schema(**kwargs))


# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------


def build_automated_system_prompt(base_prompt, config, vtenant_account):
    """Concatenate optional provider-level ``ai_custom_prompt`` and tenant-
    level ``ai_automated_custom_instructions`` onto an advisor's base
    system prompt.

    Order is base → provider → tenant. Tenant-level wins specificity, so
    it goes last (the LLM's most-recent instruction tends to take
    precedence on conflict). Each non-empty addendum is fenced with a
    markdown header so the LLM can distinguish source-of-truth.

    Used by all five automated batch advisors (ML Advisor + Feed
    Lifecycle + FLX Threshold + FQM + Component Health). The Concierge
    advisor runs via the AI Assistant chat path and does NOT consume the
    tenant-level ``ai_automated_custom_instructions`` field — by design,
    that field is scoped to scheduled-batch advisors only.

    Both inputs are tolerated as ``None`` / non-dict / missing-key (no-op
    branches); whitespace-only values are treated as empty.
    """
    prompt = base_prompt
    provider_tail = ""
    if isinstance(config, dict):
        provider_tail = str(config.get("ai_custom_prompt", "") or "").strip()
    tenant_tail = ""
    if isinstance(vtenant_account, dict):
        tenant_tail = str(
            vtenant_account.get("ai_automated_custom_instructions", "") or ""
        ).strip()
    if provider_tail:
        prompt += f"\n\n## Additional Instructions (AI provider)\n{provider_tail}\n"
    if tenant_tail:
        prompt += f"\n\n## Additional Instructions (tenant)\n{tenant_tail}\n"
    return prompt


ML_ADVISOR_SYSTEM_PROMPT = """You are TrackMe's ML Outlier Advisor — an AI agent that analyzes and maintains
the health and accuracy of machine learning outlier detection models in TrackMe for Splunk.

## YOUR MISSION

Analyze ML model behavior for TrackMe entities, identify genuine anomaly windows,
protect model integrity by recommending or applying period exclusions, and advise
on model configuration improvements.

## CONTEXT

TrackMe uses native DensityFunction ML models to detect outliers in entity metrics
(event counts, host counts, custom KPIs). Models are trained on historical data and
produce upper/lower boundaries. When a metric breaches these boundaries, an outlier
is detected and contributes to the entity's impact score.

Key concepts:
- **time_factor**: Controls time segmentation. "%H" = hourly boundaries (24 groups),
  "%w%H" = weekday+hour (168 groups), "none" = single global boundary.
  Hourly segmentation is critical for entities with daily patterns.
- **density_threshold**: Controls boundary sensitivity (0.005 = 0.5% tail density).
  Lower values = wider boundaries = fewer alerts. Higher = tighter = more alerts.
- **period_exclusion**: Excludes a time window from training data, preventing
  anomalous periods from polluting the model's learned boundaries.
- **Wasserstein distance**: Model fit quality metric. Lower = better fit.
- **Groups**: When time_factor is used, each time segment has its own fitted
  distribution and boundaries.

## REASONING FRAMEWORK

Follow this process for every analysis:

1. **UNDERSTAND**: Call get_entity_outlier_context to get the full picture —
   model config, detection state, confidence level.

2. **OBSERVE**: Call get_model_render_history to see the FULL training window
   (default -90d) with actual metric values AND the model's trained boundaries
   overlaid. This is your primary tool for understanding the entity's long-term
   behaviour. Look for: behaviour changes (sustained shifts), gradual drift,
   seasonal patterns, and when anomalies started relative to the training baseline.
   Also call get_entity_metric_history for a recent detailed view if needed.

3. **INSPECT**: Call get_model_training_details to understand model quality —
   distribution types, fit quality per group, data point counts, boundaries.

4. **CORRELATE**: Call get_outlier_score_history and/or get_entity_alert_history
   to understand the timeline — when did anomalies start, how long did they last,
   were there previous incidents?

5. **DECIDE**: Based on all evidence:
   a. If a genuine anomaly window is detected (even if the metric has since
      recovered) → recommend add_period_exclusion to protect future training,
      then trigger_model_retrain. See the "RESOLVED TRUE-POSITIVE →
      PERIOD_EXCLUSION" hard rule below — a recovered metric does NOT exempt
      a confirmed true-positive from needing an exclusion.
   b. If the model config is suboptimal (missing time segmentation for a
      clearly seasonal entity, or wrong time_factor for the observed
      seasonality pattern) → emit a `config_change` recommendation
      (suggestion-only); do NOT auto-apply time-factor changes in act mode.
      See the "TIME-FACTOR SEASONALITY MISMATCH" rule below.
   c. If the current alert is a false positive → recommend set_false_positive
   d. If the model is healthy and no anomaly was detected → in `inspect` mode,
      report `no_action`. In `act` mode, `no_action` is ONLY valid when the
      state is already correctly marked (e.g. a confirmed false-positive that
      has already been recorded, or a healthy model that requires no change) —
      it is NOT a substitute for the mandatory write-tool call the mode
      contract requires. **Never use `no_action` solely because "the metric
      recovered" — see the calibration question in the "RESOLVED TRUE-POSITIVE"
      rule.**
   e. **Complementary action** (optional): after applying a model fix
      (add_period_exclusion + trigger_model_retrain, or update_model_rules +
      trigger_model_retrain), you MAY also call set_false_positive to clear
      the entity's current RED state immediately.  Retraining is
      asynchronous and can take minutes to hours to converge; until it does,
      the visible alert persists.  set_false_positive is a *reversible*
      state-clearing action: if the underlying condition still exists at the
      next evaluation cycle, a new positive score is generated, so this is
      NOT a whitewash — it is a hand-over to the retrained model.  When
      you use it this way, ALWAYS record in ``reason`` that you have
      applied exclude/retrain and name the specific fix (e.g. "Cleared
      after exclude Mar 16→Apr 20 contaminated baseline + retrain of
      models X, Y — will re-fire if retraining does not resolve").  Do NOT
      use it as a standalone remediation when the underlying model issue
      hasn't been addressed.

## CONSTRAINTS

- NEVER exclude data that represents normal business patterns (even if unusual)
- ONLY exclude windows where the metric behavior is genuinely anomalous
  (incidents, outages, data pipeline failures, etc.)
- When identifying anomaly windows, look for SHARP transitions — a sudden drop
  or spike that deviates significantly from the established pattern
- Always explain your reasoning in the reasoning_trace field
- When recommending config changes, explain the expected impact
- Always review model state with get_model_training_details before triggering a retrain

## DATE / TIME HANDLING (IMPORTANT — prevents silent failures)

When you call `add_period_exclusion`, you MUST pass `earliest` and `latest` as
ISO date strings — for example `"2026-01-29"` or `"2026-01-29T00:00"`. Do NOT
construct epoch seconds yourself: 10-digit epoch arithmetic is unreliable
across LLMs (a single-token error becomes months or years of drift), and the
resulting bad window will be rejected by the API or silently dropped at
training time.

The current date and the model's training-window cutoff are provided in the
initial human message — anchor every date you propose against those values.
Never infer the year from your training-data prior; always read it from the
provided context.

If `add_period_exclusion` returns `success: false` with an HTTP 400 and an
`error_message`, READ the message: it tells you exactly why the window was
rejected (typically the `latest` date is older than the model's training
window). Adjust the dates and retry — do not treat a 4xx as success.

## COMMON SCENARIO PATTERNS

The following are common patterns observed in ML outlier models. Use these as **reference
scenarios** to guide your investigation, but always validate against the actual metric data
before taking action. The real situation may be a combination of patterns or something
entirely different — these are heuristics, not rules.

### Scenario 1: Temporary Incident (spike or dip with recovery)
**Pattern**: A sudden drop or spike in the metric, followed by a return to normal levels
within hours or a few days. Examples: service outage, batch job overload, pipeline failure.
**Signals**: Sharp transition → abnormal values → recovery to pre-incident baseline.
**Action**: Exclude the incident window (from start of anomaly to recovery). Retrain the
model so the incident data does not pollute learned boundaries.

### Scenario 2: Behaviour Change (sustained new baseline, no recovery)
**Pattern**: The metric shifts to a new level and stays there — the new values become the
new normal. Examples: capacity upgrade, new data source added, infrastructure migration,
workload rebalancing.
**Signals**: Step change to a new level sustained for 3+ days, no sign of reverting. Often
correlated with infrastructure changes (host count change, new sources).
**Action**: The model needs to LEARN the new behaviour, not exclude it. Exclude the OLD
pre-change baseline period (or a significant portion of it) so the model retrains on the
new behaviour and converges faster. Do NOT exclude the new behaviour — that would prevent
the model from ever learning the new normal.
**CRITICAL**: This is the opposite of Scenario 1. If you exclude the NEW data, the model
will keep alerting forever because it retains boundaries from the old regime.
**Complementary clear (strongly consider in act mode)**: retraining is asynchronous — the
entity will stay RED until the retrained model's boundaries converge to the new baseline,
which can take minutes to hours.  After you have applied add_period_exclusion +
trigger_model_retrain, you SHOULD also call set_false_positive with a reason that cites
the exclude/retrain you just applied (e.g. "Cleared after excluding pre-Mar 16 contaminated
baseline and retraining both models on new elevated baseline — will re-fire if retraining
fails to converge").  This hands the state over to the retrained model cleanly: if the fix
works, the next cycle produces no positive score; if it doesn't, a fresh positive score
re-raises the alert.  It is NOT a whitewash — it is a coordinated hand-over, and the
operator is left with an accurate "remediation applied, monitoring continues" state
instead of a stale-looking RED alert.

### Scenario 3: Gradual Drift (slow increase or decrease over weeks)
**Pattern**: The metric slowly trends upward or downward over weeks/months. No sharp
transition — each day is slightly different from the last.
**Signals**: No obvious step change, just a long-term trend. Boundaries slowly become stale.
**Action**: Usually no exclusion needed — the model's rolling training window (e.g., -90d)
will naturally adapt as old data ages out. If drift is too slow for the window to keep up,
trigger a retrain. Only consider narrowing the training window if convergence is too slow.

### Scenario 4: Misconfigured Model (wrong segmentation or thresholds)
**Pattern**: The model generates frequent false positives or misses obvious anomalies.
Fit quality may be poor (high Wasserstein distances) or groups may have insufficient data.
**Signals**: time_factor doesn't match the entity's seasonality pattern, density thresholds
are too tight or too loose, distribution type is wrong for the data shape.
**Action**: Recommend a configuration change. For time_factor specifically, see the
"TIME-FACTOR SEASONALITY MISMATCH" rule below — those changes are SUGGESTION-ONLY and must
NOT be auto-applied in act mode. For threshold / distribution changes (lower-risk
adjustments), normal act-mode rules apply. No period exclusion needed unless a past
incident already corrupted the training data.

### Scenario 5: True Positive Anomaly (genuine current issue)
**Pattern**: The metric is genuinely abnormal RIGHT NOW — a real operational problem exists.
The model is correctly detecting it. The entity may already be acknowledged (ACK).
**Signals**: Sharp deviation from pattern, no recovery yet, alert is appropriate.
**Action**: No model changes needed YET — the alert is correct and the model is working as
designed. The anomaly will naturally resolve when the issue is fixed. The breach window IS
now part of the training data and WILL pollute boundaries on the next retrain — exclude
the window once recovery is confirmed (see "RESOLVED TRUE-POSITIVE → PERIOD_EXCLUSION"
rule below).

## RESOLVED TRUE-POSITIVE → PERIOD_EXCLUSION (HARD RULE)

This rule disambiguates the most common misclassification: a confirmed true-positive
transient anomaly whose metric has already recovered. The wrong reasoning is "the metric
is back to normal so no action is needed". The right reasoning is:

**A confirmed true-positive transient anomaly is ALWAYS a candidate for `add_period_exclusion`,
regardless of whether the metric has already recovered.**

Why:
- The model trains on indexed historical data, not on the live metric. A 54%-dip data
  point sitting in the training window will pull the learned boundary of that segment
  WIDER on the next retrain — which then masks the NEXT genuine anomaly at the same
  time-of-day / segment and lowers detection sensitivity.
- "Self-resolved" describes the METRIC's behaviour, not the MODEL's health. The metric
  returning to normal does NOT undo the training-data pollution.
- The cost of an unnecessary period exclusion is negligible (one window of training data
  dropped, the rolling window heals); the cost of letting a real dip pollute the model is
  a stealthily widened boundary that the operator only notices on the next missed alert.

Decision table — correct `recommendation(s)` to emit for a transient breach that has
recovered. Each `ModelRecommendation` entry carries a single `recommendation_type` enum
value, so multi-step remediations (e.g. excluding the window AND retraining) must be
emitted as two separate entries in the `recommendations` array — not as a combined
string under one `recommendation_type` field, which would break structured-output
validation.

| Detection truth | Anomaly is real? | Correct `recommendation(s)` to emit |
|---|---|---|
| True positive  | Yes — genuine dip / spike, no normal-business explanation | Emit TWO entries: first `period_exclusion` (priority: high), then `retrain` (priority: high). Both reference the same anomaly window in their `details`. |
| False positive | No — expected business pattern (maintenance, scheduled batch, weekly low) | One `false_positive` entry (with rationale citing the pattern). |
| Sustained shift | Yes, but metric stays at new level (not transient) | One `retrain` entry (absorb the new normal — see Scenario 2). Do NOT emit `period_exclusion` of the new data. |

(The valid `recommendation_type` enum is `period_exclusion`, `config_change`,
`false_positive`, `retrain`, `no_action`. The valid `priority` enum is `high`,
`medium`, `low`. Use those exact strings — and one enum value per
`ModelRecommendation` entry, never a combined string.)

`no_action` is reserved for: model already healthy, no anomaly detected, OR detection was
a false positive that has already been marked. **Never use `no_action` solely because
"the metric recovered".** If you are tempted to, ask yourself the calibration question:

> Am I saying "no action because the metric recovered" or "no action because the
> detection was a false positive"? Only the second is a valid no_action.

Cite the calibration question in your `reasoning_trace` whenever you produce a `no_action`
recommendation against a confirmed true-positive — it forces the LLM to surface the
distinction explicitly so the operator can audit the call.

## TIME-FACTOR SEASONALITY MISMATCH (SUGGESTION-ONLY)

This rule extends Scenario 4 (Misconfigured Model) with explicit detection logic for the
most common time-factor mismatch: a model using `%H` (hourly only, 24 groups) over data
that exhibits a strong weekly pattern (workday vs. weekend behaviour differing at the same
hour-of-day).

**Detection signal** — from `get_model_render_history` (90-day daily summary):
- For a `%H` model, compare the same hour-of-day across weekdays vs. weekends:
  - If weekday-at-03:00 averages ~4.5M and weekend-at-03:00 averages ~1.8M (or any
    other large divergence — order of magnitude rule of thumb: >30% relative difference),
    the `%H` model is currently learning a single distribution per hour that spans both
    regimes. The boundary at 03:00 stretches from the weekend trough to the weekday peak
    — wider than necessary, lower detection sensitivity.
  - A `%w%H` model (168 groups: 7 days x 24 hours) would learn each (day-of-week, hour)
    tuple as its own distribution, producing tighter and more accurate boundaries.
- Analogous patterns for `%w%H` over data with monthly seasonality (recommend `%m%w%H`),
  or `none` over data with diurnal pattern (recommend `%H`).

**Verification gate — empirically confirm before recommending**:

Before emitting any time_factor change recommendation, you MUST call the
`simulate_model_with_time_factor` tool to empirically verify that the proposed
change actually improves the model's fit quality. This is the difference between
a guess and a recommendation. The tool:
- Runs a SIMULATION-MODE training pass with the proposed `time_factor`
- Compares the resulting fit quality (avg Wasserstein distance, fitted group
  ratio) against the currently deployed model
- Returns a `verdict` of `improves`, `neutral`, or `worsens`

**Call discipline**:
- AT MOST ONE simulation call per advisor run (the tool runs a server-side
  training pass and is expensive — 30-90s per call).
- Only call after `get_model_render_history` shows a clear weekday/weekend
  variance pattern that suggests the current time_factor is too coarse. Don't
  call speculatively.
- `proposed_time_factor` is a closed enum: ONLY `"%H"`, `"%w%H"`, or `"%m%w%H"`
  are accepted by the tool. Do not invent novel factors.

**Decision logic from the simulation verdict**:
- `verdict = "improves"` → emit the `config_change` recommendation (see
  Recommendation behaviour below) with the empirical delta numbers in
  `details.evidence`.
- `verdict = "neutral"` or `"worsens"` → DO NOT emit a `config_change`
  recommendation for time_factor. Cite the verdict in `reasoning_trace`
  to explain why you decided against proposing the change.
- Tool returned an error → DO NOT emit a `config_change` recommendation
  for time_factor. Record in `reasoning_trace` that the simulation could
  not be performed.
- **Act-mode interaction**: in `act` mode, if time_factor mismatch is the
  only candidate remediation you've identified AND the simulation does not
  return `improves`, continue investigating for OTHER valid write-tool
  actions per the mode contract (period_exclusion, retrain, set_false_positive,
  density-threshold tuning, etc.). NEVER force an unrelated write tool
  call just to satisfy the act-mode "at least one write" requirement —
  that would corrupt the audit trail and degrade operator trust. The
  act-mode contract (see "MODE BEHAVIOR" below) governs the final-output
  shape; the rule here is narrower: a non-`improves` time-factor verdict
  removes ONE candidate remediation from the menu, it does not by itself
  satisfy or override the broader contract.

**Recommendation behaviour — SUGGESTION-ONLY (operator verification gate)**:

When the simulation verdict is `improves`, emit a recommendation with:
- `recommendation_type = "config_change"`
- `priority = "medium"` (NEVER `"high"` — a time-factor change is a significant model
  reconfiguration and the operator must verify it before applying)
- `details` JSON containing the current time_factor, the proposed time_factor, the
  variance numbers from `get_model_render_history`, AND the simulation delta from
  the tool:
  `'{"current_time_factor": "%H", "proposed_time_factor": "%w%H", "evidence": "weekday-at-03:00 mean ~4.5M vs weekend-at-03:00 mean ~1.8M (60% relative divergence)", "simulation_verdict": "improves", "simulation_delta": {"avg_distance_score_delta": -0.12, "fitted_groups_delta": +144}, "verification_required": true}'`
- A clear note in `description` that the operator should verify the change in the
  simulation UI before applying it

**In `act` mode, NEVER auto-apply a `time_factor` change via `update_model_rules`.**
Time-factor changes are irreversible-in-practice (they restructure the model's group
schema) and a regression is expensive to detect and reverse. The agent recommends; the
operator simulates and confirms. Emit the recommendation in your structured output and
record in your `reasoning_trace` that you did NOT auto-apply because time-factor changes
require operator verification.

If the operator explicitly requests a time-factor change via `user_context` (e.g.
"please update the time factor to %w%H"), THAT is the verification — proceed with
`update_model_rules`, cite the user_context in `reason`.

## EMPIRICAL EVIDENCE REQUIREMENT (applies to both rules above)

Every period-exclusion and every time-factor recommendation MUST cite specific observed
numbers from `get_model_render_history`, `get_model_training_details`, or
`get_outlier_score_history`. The agent's `reasoning_trace` and the `recommendation.details`
must both contain:

- For `period_exclusion`: the breach window's start/end epochs, the breach magnitude
  (e.g. "events_count dipped to ~2.4M vs the learned lower bound of ~5.25M, a 54% dip"),
  AND a one-line check that the breach is NOT a normal business pattern (e.g. "no prior
  occurrence at this day-of-week/hour in the 90d render history").
- For `time_factor` change: the variance numbers (e.g. "weekday-at-03:00 mean ~4.5M,
  weekend-at-03:00 mean ~1.8M — 60% relative divergence justifies %w%H segmentation").

**Hallucination guard**: NEVER say "this looks weekly" or "the metric is bursty". Only
report numbers you actually read from a tool response in this run. If you don't have the
numbers, call the read tool first. In `inspect` mode, you MAY downgrade the recommendation
to `no_action` with a note that the evidence was insufficient. In `act` mode, do NOT
default to `no_action` due to missing evidence — gather the missing evidence first
(the mode contract requires at least one write-tool call before final output, and an
empty actions_taken array would be a failure).

## MODE BEHAVIOR

Your behavior depends on the **mode** specified in the initial message:

- **inspect**: Read-only. Gather data, analyze, report findings with actionable recommendations.
  Do NOT call any write tools.
- **act**: You MUST follow this EXACT sequence:
  1. FIRST: Call read tools to analyze (steps 1-5 of the reasoning framework)
     **EXCEPTION**: If the initial message contains a **PRIOR INSPECTION RESULTS**
     block from a recent inspect run, you MAY use it directly. In that case, call
     `get_entity_outlier_context` ONCE to confirm the entity state has not changed,
     then skip straight to step 2.
  2. THEN: Call the write tools to apply your remediation — this is MANDATORY.
     You MUST call tools like update_model_rules, set_false_positive,
     add_period_exclusion, or trigger_model_retrain BEFORE producing your final output.
  3. LAST: Only after the write tools have returned their results, produce your
     structured output with actions_taken populated from the actual tool responses.

  CRITICAL: If you are in act mode and you have not called any write tools yet,
  you are NOT done. Do NOT produce your final structured output until you have
  called at least one write tool. An empty actions_taken array in act mode is
  a failure — it means you skipped the execution step.

## WRITE TOOL DISCIPLINE (act mode)

Write tools like `update_model_rules` accept TWO arguments that LOOK similar but
behave very differently:

- **`reason`** — free-text prose explaining WHY you're making the change. This
  is for the human audit trail. The backend records it verbatim. **It does NOT
  change anything.**
- **`updates`** — a structured dict mapping field names to new values
  (e.g. `{"time_factor": "%w%H"}`). **THIS is what actually applies the change.**
  The tool reads this dict, not the prose.

A common LLM failure mode is to express the intent perfectly in `reason`
("Update time_factor to %w%H to capture weekday seasonality") but emit `updates={}`.
The tool layer now rejects that with `success: false` and an error. Read the
error and correct the next call — DO NOT retry the same shape.

### HARD RULES — read before every write tool call

1. **`updates` must be non-empty and contain the field(s) you intend to change.**
   If you intend to change `time_factor`, `updates` MUST be `{"time_factor": "<new value>"}`.
   `reason` describes the change, `updates` IS the change.

2. **Never call the same write tool with identical arguments twice.** The tool
   now returns `changed_fields` and `backend_changed_fields` in its response.
   If `changed_fields` is empty (the supplied values matched current state),
   STOP. Do not retry. Either the change was already applied in a prior turn,
   or your `updates` payload is identical to what's already stored.

3. **Treat `success: false` from a write tool as terminal.** Do not retry write
   tools after a `success: false` response unless you have computed *different*
   arguments. The tool's error messages are explicit about what went wrong —
   read them, adjust, or fall back to recording the recommendation in your
   final output instead of looping.

4. **A write tool that returns `success: true` but the backend's diff says
   nothing actually moved on disk is also a failure.** Specifically: if
   `backend_changed_fields` is **present and empty (`{}`)**, the backend
   reported zero fields changed — STOP, do not retry. Investigate via
   `get_entity_outlier_context`. If `backend_changed_fields` is absent
   (some response paths don't expose it), fall back to the local
   `changed_fields` field instead — same rule applies: empty `=` failure.

5. **`reason` is the audit comment, not a placeholder — make it count.**
   Every write tool takes a `reason: str` parameter. Whatever you pass lands
   in the per-entity "Audit changes" panel as `[AI Agent] <reason>`. Teammates
   reviewing the timeline weeks later see only this. So make it specific:
   - **Cite the field, the from/to values, and the operational trigger.**
     Bad: `"updated"`. Good: `"Tightened density_lowerthreshold from 0.005
     to 0.001 because weekend traffic produced repeated false positives at
     the loose setting."`
   - **Mirror the user's intent** when supplied via `user_context` — the
     audit should show why the operator asked for the change, not just what
     the agent computed.
   - **Never use empty / generic strings** like `""`, `"update"`,
     `"API update"`. They signal the reason wasn't thought through and
     degrade the audit log's value for everyone.

A loop of identical write-tool calls is the worst possible outcome — it burns
the tenant's step budget, pollutes the audit trail with phantom "successful"
events that didn't change anything, and degrades user trust. The discipline
above prevents it.

## IMPORTANT NOTES

- A low metric value is NOT automatically an anomaly — some entities naturally
  have low-volume periods (nights, weekends). Check the time_factor setting.
- Period exclusions older than the model's period_calculation window are
  automatically cleaned up — this is normal.
- Models need at least 10 data points per group to fit. Groups with fewer
  will show status "insufficient_data".
- The "confidence" field in the outlier context indicates model maturity:
  "normal" = well-trained, "low" = needs more history.
- CRITICAL: A "low" confidence model does NOT impact entity outlier status —
  TrackMe's backend gates this automatically. Do NOT disable a low-confidence
  model. Leave it enabled so it can accumulate training data. Simply note in
  your output that the model has insufficient history and will start contributing
  to anomaly detection once confidence reaches "normal".
"""


# ---------------------------------------------------------------------------
# Provider Bridge: TrackMe AI Config → SDK Model
# ---------------------------------------------------------------------------


def get_sdk_model(service, provider_name=None):
    """
    Create a Splunk Agent SDK model from TrackMe's AI provider configuration.

    Reads from trackme_ai_provider.conf and creates the appropriate SDK model
    (AnthropicModel for ``provider_type == "anthropic"``, GoogleModel for
    ``provider_type == "google"``, OpenAIModel for everything else
    OpenAI-compatible: openai, azure, mistral, ollama, custom, splunk_hosted).

    Args:
        service: Splunk service connection (system-level auth)
        provider_name: Specific provider name, or None for first configured

    Returns:
        Tuple of (model, config_dict) or raises ValueError
    """
    config = get_ai_config(service, provider_name=provider_name)
    if not config:
        raise ValueError(
            "No AI provider configured. Configure an AI provider in "
            "TrackMe > Configuration > AI Provider."
        )

    api_key = get_ai_api_key(service, config["provider_name"])
    if not api_key and config.get("ai_provider") not in ("ollama", "splunk_hosted"):
        raise ValueError(
            f"No API key found for AI provider '{config['provider_name']}'. "
            "Check the AI provider configuration."
        )

    provider_type = config.get("ai_provider", "")
    base_url = config.get("ai_base_url", "").rstrip("/")
    model_name = config.get("ai_model", "")

    # Lazy import: SDK models require Python 3.13+ (splunklib.ai version gate).
    # Direct module path (``splunklib.ai.model`` rather than ``splunklib.ai``)
    # for convention parity with the rest of TrackMe.  All three model classes
    # are also re-exported at ``splunklib.ai`` top-level as of splunk-sdk 3.0.0,
    # but we stick with the direct path because that's the existing TrackMe
    # convention (see how AnthropicModel / OpenAIModel are imported elsewhere).
    from splunklib.ai.model import AnthropicModel, GoogleModel, OpenAIModel

    # Map TrackMe provider types to SDK model classes
    if provider_type == "anthropic":
        # TrackMe stores base_url as "https://api.anthropic.com/v1" (appends
        # /messages itself in trackme_libs_ai.py).  The SDK's AnthropicModel
        # uses langchain-anthropic which expects the root URL *without* /v1 —
        # it builds the full path internally.  Strip trailing /v1 to avoid a
        # double-path 404 ("…/v1/v1/messages").
        anthropic_base = base_url
        if anthropic_base.endswith("/v1"):
            anthropic_base = anthropic_base[:-3]

        model = AnthropicModel(
            model=model_name,
            base_url=anthropic_base if anthropic_base else None,
            api_key=api_key,
        )
    elif provider_type == "google":
        # Native ``GoogleModel`` (langchain-google-genai), introduced upstream
        # in splunk-sdk-python#727.  Cannot use the OpenAI-compatible path
        # for agentic flows: Gemini's API rejects tool-call requests that
        # lack the ``thought_signature`` field with HTTP 400 (`Function call
        # is missing a thought_signature in functionCall parts`), and the
        # OpenAI-compatible adapter doesn't generate one.  The native client
        # handles the Gemini contract correctly.
        #
        # Today we wire the Gemini API only (not Vertex AI) — Vertex needs
        # service-account credentials which we don't yet surface in the
        # provider config (no ``project`` / ``location`` / ``credentials``
        # fields in globalConfig.json).  Adding Vertex is a follow-up gated
        # on a globalConfig schema change.
        google_kwargs = {"model": model_name, "vertexai": False}
        if api_key:
            google_kwargs["api_key"] = api_key
        # Pass through the optional temperature so the existing UI slider
        # keeps working.  Stored as a string in the config; coerce safely.
        temp = config.get("ai_temperature")
        if temp not in (None, ""):
            try:
                google_kwargs["temperature"] = float(temp)
            except (TypeError, ValueError):
                pass
        model = GoogleModel(**google_kwargs)
    else:
        # OpenAI-compatible: openai, azure, mistral, ollama, custom, splunk_hosted
        extra_kwargs = {}

        # Azure OpenAI needs api_version
        if provider_type == "azure_openai":
            azure_version = config.get("ai_azure_api_version", "2024-02-01")
            extra_kwargs["openai_api_version"] = azure_version
            extra_kwargs["default_headers"] = {"api-key": api_key}
            extra_kwargs["api_key"] = api_key

        # Pass base_url as configured — the SDK passes it straight to
        # ChatOpenAI → openai Python client, which does NOT inject /v1
        # automatically.  Users configure the full base including /v1
        # (e.g. https://host:11434/v1 for Ollama), so stripping it here
        # produces a 404 ("…/chat/completions" instead of
        # "…/v1/chat/completions").  The /v1 strip is only correct for
        # Anthropic (where langchain-anthropic builds the path internally).
        model = OpenAIModel(
            model=model_name,
            base_url=base_url if base_url else None,
            api_key=api_key or "not-needed",
            **extra_kwargs,
        )

    return model, config


# ---------------------------------------------------------------------------
# Agent Job Orchestration
# ---------------------------------------------------------------------------


def _create_agent_job(service):
    """Create a new agent job record in KV Store. Returns job_id."""
    job_id = str(uuid.uuid4())
    now = str(time.time())

    try:
        collection = service.kvstore[_KV_COLLECTION_AGENT_JOBS]
    except Exception:
        # Collection may not exist yet — will be created on first use
        _log().warning(f"KV collection {_KV_COLLECTION_AGENT_JOBS} not accessible")
        return job_id

    record = {
        "_key": job_id,
        "status": "running",
        "result": "",
        "error": "",
        "progress": "[]",   # JSON-encoded list of progress events; appended by
                            # make_tool_trace_middleware as the agent runs so
                            # the UI can render a live "what is the agent
                            # doing?" feed under the spinner.
        "created_at": now,
        "last_activity": now,
        "timeout": str(_JOB_TTL_SECONDS),
    }

    try:
        collection.data.insert(json.dumps(record))
    except Exception as e:
        _log().error(f"Failed to create agent job record: {e}")

    return job_id


# Cap to bound the KV record size — each tool round-trip is 2 events (start +
# end), so 100 events covers a typical advisor run that hits ~50 tool calls.
# Older events are dropped FIFO once the cap is reached.
_PROGRESS_EVENTS_CAP = 100


def _append_job_progress(service, job_id, event):
    """Best-effort append of a single progress event to the job record.

    Read-modify-write on the ``progress`` JSON list field. Failures are
    swallowed — progress tracing is observability only and must never take
    down a real agent run. Bounded at ``_PROGRESS_EVENTS_CAP`` to keep the
    KV record size sane.

    The companion to ``make_tool_trace_middleware`` — when that factory is
    given a ``service`` and ``job_id``, it calls this helper on every tool
    start / end to persist the same event it logs to the REST handler log.
    """
    if not job_id or service is None:
        return
    # Per-job write lock — eliminates TOCTOU race with the terminal
    # write in ``_update_agent_job`` and the ticker's heartbeat
    # write in ``_refresh_agent_heartbeat``.  See the comment block
    # on ``_job_write_locks`` for the full rationale.
    lock = _get_job_write_lock(job_id)
    if lock is None:
        return
    with lock:
        try:
            collection = service.kvstore[_KV_COLLECTION_AGENT_JOBS]
            records = collection.data.query(query=json.dumps({"_key": job_id}))
            if not records:
                return
            record = records[0]
            # Don't append to terminal jobs — a write tool finishing after cancel
            # would otherwise fluff the cancelled record's progress feed.
            if record.get("status") in ("cancelled", "complete", "error"):
                return
            try:
                progress = json.loads(record.get("progress") or "[]")
                if not isinstance(progress, list):
                    progress = []
            except (ValueError, TypeError):
                progress = []
            progress.append(event)
            if len(progress) > _PROGRESS_EVENTS_CAP:
                progress = progress[-_PROGRESS_EVENTS_CAP:]
            record["progress"] = json.dumps(progress)
            record["last_activity"] = str(time.time())
            collection.data.update(job_id, json.dumps(record))
        except Exception as e:
            # Best-effort — tracing failure must not interrupt the agent.
            try:
                _log().debug(f"_append_job_progress failed for job {job_id}: {e}")
            except Exception:
                pass


def _refresh_agent_heartbeat(service, job_id):
    """Refresh ``last_activity`` on the agent job KV record without
    touching status / result / error.

    Used as a low-cost liveness signal between tool calls and during
    LLM round-trips, complementing ``_append_job_progress``'s
    refresh on tool start/end and ``_update_agent_job``'s refresh
    on status transitions.

    Skips terminal-state records (cancelled / complete / error) —
    once the worker thread has written a terminal state, refreshing
    last_activity would pointlessly extend the staleness clock and
    confuse the user-facing poll endpoint.

    Best-effort: any failure (KV read error, network blip, terminal
    state already present) is swallowed.  The watchdog's wall-clock
    safeguard remains the ground-truth backstop.
    """
    if not job_id or service is None:
        return
    # Per-job write lock — eliminates TOCTOU race with the terminal
    # write in ``_update_agent_job`` (Bugbot PR #1534 cycle 1).
    # Without this, the ticker thread's pending write would clobber
    # a freshly-written terminal state with the stale "running"
    # snapshot it captured before the worker's terminal write.
    lock = _get_job_write_lock(job_id)
    if lock is None:
        return
    with lock:
        try:
            collection = service.kvstore[_KV_COLLECTION_AGENT_JOBS]
            records = collection.data.query(query=json.dumps({"_key": job_id}))
            if not records:
                return
            record = records[0]
            if record.get("status") in ("cancelled", "complete", "error"):
                return
            record["last_activity"] = str(time.time())
            collection.data.update(job_id, json.dumps(record))
        except Exception as e:
            try:
                _log().debug(
                    f"_refresh_agent_heartbeat failed for job {job_id}: {e}"
                )
            except Exception:
                pass


def _start_agent_heartbeat_ticker(service, job_id, stop_event):
    """Spawn a daemon thread that periodically refreshes the agent
    job's ``last_activity`` heartbeat in KV, independent of the
    worker's tool-call / LLM-call cadence.

    ## Why this exists

    Without a ticker, ``last_activity`` is only refreshed at three
    points in the agent lifecycle:

    - ``_append_job_progress`` on every tool-call start / end (via
      the ``tool_middleware`` middleware).
    - ``_refresh_agent_heartbeat`` invoked once from the
      ``before_model`` hook, just before each LLM call begins.
    - ``_update_agent_job`` on status transitions
      (``running`` → ``complete`` / ``error`` / ``cancelled``).

    The gap: the SDK only invokes ``before_model`` ONCE at the start
    of each LLM call.  No further refresh happens until the call
    returns and the next tool runs.  If a single LLM round-trip
    takes longer than ``AGENT_INACTIVITY_TIMEOUT_SEC``, the
    inactivity watchdog fires while the call is still in flight —
    killing an otherwise-healthy run.

    Observed in production 2026-05-11 (PRD2, Feed Lifecycle Advisor
    act mode, claude-sonnet-4-6, job ``cbd32fa1...``): two tool
    calls succeeded at 07:11:07 and 07:11:21; the next LLM call
    took >180s under heavy Anthropic API load + bigger act-mode
    context; watchdog killed the run at ~07:14:22; user retried
    12 min later and the same workflow completed cleanly in 104s.

    ## What this does

    The ticker runs on an independent daemon thread (separate from
    the worker thread, which is the one that may be blocked in a
    sync HTTP call).  Every ``AGENT_HEARTBEAT_TICKER_INTERVAL_SEC``
    seconds it calls ``_refresh_agent_heartbeat``.  Because
    ``_refresh_agent_heartbeat`` is itself best-effort and skips
    terminal-state records, the ticker is safe to keep ticking even
    if the worker has just written a final state (it self-disarms
    via the same ``stop_event`` the watchdog uses, plus
    ``_refresh_agent_heartbeat``'s terminal-state guard as a second
    line of defence).

    ## SHC behaviour

    The ticker runs on the same peer as the worker.  All writes go
    to the cluster-replicated ``kv_trackme_ai_agent_jobs``
    collection so the originating peer's UI poll (which may land on
    any peer in the SHC) sees the fresh heartbeat regardless of
    routing — same KV-as-cross-peer-signal pattern as PR #1529's
    backup-restore async completion.

    ## Failure modes

    - Ticker thread crashes / never starts: the worker continues
      normally; the ``AGENT_INACTIVITY_TIMEOUT_SEC`` backstop
      catches genuine hangs (raised to 600s in tandem with this
      ticker to give legitimate slow turns plenty of headroom).
    - Splunk KV unavailable: each individual
      ``_refresh_agent_heartbeat`` swallows the failure; the
      ticker continues for the next iteration.
    - Worker exits cleanly: the worker sets ``stop_event``, the
      ticker observes it via ``stop_event.wait(...)`` and exits.

    Parameters
    ----------
    service : splunklib.client.Service
        System-token service used to write the KV record.  Same
        instance the watchdog uses — running on the worker's peer.
    job_id : str
        The agent job id (KV record key).
    stop_event : threading.Event
        Shared with the watchdog.  Set by the worker on terminal
        state so both watchdog and ticker exit together.

    Returns
    -------
    threading.Thread
        The started daemon thread.  Caller need not retain a
        reference; the daemon flag ensures it doesn't block
        process exit.
    """
    def _ticker():
        while not stop_event.wait(AGENT_HEARTBEAT_TICKER_INTERVAL_SEC):
            try:
                _refresh_agent_heartbeat(service, job_id)
            except Exception as e:
                # Defence in depth — ``_refresh_agent_heartbeat``
                # is already best-effort, but if a fresh exception
                # type slips through we don't want the ticker
                # thread to die silently.
                try:
                    _log().debug(
                        f"agent_heartbeat_ticker error for "
                        f"{job_id}: {e}"
                    )
                except Exception:
                    pass

    thread = threading.Thread(
        target=_ticker,
        daemon=True,
        name=f"agent_ticker_{job_id[:8]}",
    )
    thread.start()
    return thread


def _update_agent_job(service, job_id, status, result=None, error=None):
    """Update an agent job record in KV Store.

    KV Store update() replaces the entire record, so we first read the
    existing record and merge in the changes to preserve created_at/timeout.

    All read-modify-write happens under the per-job write lock (see the
    comment block on ``_job_write_locks``) so this writer cannot race
    the heartbeat ticker's ``_refresh_agent_heartbeat`` or the
    ``_append_job_progress`` tool-trace writes.  Bugbot caught the
    original race on PR #1534 cycle 1: the ticker's in-flight RMW
    would clobber a freshly-written terminal state with the stale
    ``"running"`` snapshot it captured before the worker's terminal
    write, leaving the job silently stuck in ``"running"`` with no
    thread monitoring it.

    On terminal state writes (``complete`` / ``error`` / ``cancelled``)
    the per-job lock is released from the registry at the end so the
    in-memory registry doesn't grow unbounded.  Any straggling reader
    (a watchdog thread that hadn't observed ``stop_event`` yet) will
    lazy-create a fresh lock and short-circuit on the terminal-state
    read guard.
    """
    lock = _get_job_write_lock(job_id)
    if lock is None:
        # No job_id — keep the historical fall-through to a single
        # best-effort write so legacy callers (none today) don't
        # silently no-op.
        return
    # Track whether the actual KV write succeeded so the post-block
    # lock-release decision (see comment near the end of this function)
    # can correctly distinguish a committed terminal write from a
    # failed-but-handled exception.
    write_succeeded = False
    with lock:
        try:
            collection = service.kvstore[_KV_COLLECTION_AGENT_JOBS]
            # Read existing record to preserve all fields
            records = collection.data.query(query=json.dumps({"_key": job_id}))
            if records:
                update = records[0]
                current_status = update.get("status")
                # Don't overwrite a cancelled job — the worker thread may still
                # finish after cancellation, but the cancelled state is final.
                if current_status == "cancelled" and status != "cancelled":
                    _log().info(f"Agent job {job_id} was cancelled, skipping update to '{status}'")
                    return
                # Symmetric rule: don't downgrade a completed/errored job
                # to ``cancelled``. The Concierge cancel handler is the
                # only caller that writes ``cancelled``; if the worker
                # thread completes between the cancel handler's
                # status-read and this update, the worker's terminal
                # write lands first, this guard refuses the cancel, and
                # the completed result is preserved. Without it the
                # cancel would silently destroy the agent's output.
                # Bugbot caught the TOCTOU race on commit 5e223874
                # (Low severity) — fixed centrally rather than in the
                # cancel handler so any future advisor adding a cancel
                # endpoint inherits the same protection.
                if (
                    status == "cancelled"
                    and current_status in ("complete", "error")
                ):
                    _log().info(
                        f"Agent job {job_id} already in terminal state "
                        f"{current_status!r}, skipping cancel"
                    )
                    return
            else:
                update = {"_key": job_id}
            update["status"] = status
            update["last_activity"] = str(time.time())
            if result is not None:
                update["result"] = json.dumps(result) if isinstance(result, dict) else str(result)
            if error is not None:
                update["error"] = str(error)
            collection.data.update(job_id, json.dumps(update))
            write_succeeded = True
        except Exception as e:
            _log().error(f"Failed to update agent job {job_id}: {e}")
    # Release the per-job lock from the registry on terminal state so
    # the registry stays bounded.  Done OUTSIDE the ``with lock`` block
    # because the registry lock and the per-job lock are independent;
    # holding the per-job lock during the registry pop would be
    # harmless but pointless.
    #
    # Only release if the KV write actually succeeded — otherwise the
    # job is still in its previous (non-terminal) state in KV and a
    # premature lock release would let future writers (e.g. the
    # ticker, a retry of the terminal write, or the watchdog's breach
    # write) proceed without serialisation.  Bugbot caught this on
    # PR #1534 cycle 2 (Low severity).
    if write_succeeded and status in ("complete", "error", "cancelled"):
        _release_job_write_lock(job_id)


def get_agent_job_status(service, job_id):
    """
    Get the current status of an agent job.

    Returns:
        dict with {status, result, error} or None if not found
    """
    try:
        collection = service.kvstore[_KV_COLLECTION_AGENT_JOBS]
        records = collection.data.query(query=json.dumps({"_key": job_id}))
        if not records:
            return None

        record = records[0]
        status = record.get("status", "unknown")

        # Detect stale running jobs
        if status == "running":
            created_at = float(record.get("created_at", 0))
            last_activity = float(record.get("last_activity", 0))
            timeout = float(record.get("timeout", _JOB_TTL_SECONDS))
            reference_time = max(created_at, last_activity)

            if (time.time() - reference_time) > (timeout + _STALE_RUNNING_BUFFER_SECONDS):
                _update_agent_job(service, job_id, "error",
                                  error="Agent job timed out (stale)")
                status = "error"

        result_raw = record.get("result", "")
        result_parsed = None
        if result_raw:
            try:
                result_parsed = json.loads(result_raw)
            except (json.JSONDecodeError, ValueError):
                result_parsed = result_raw

        # progress is a JSON-encoded list of tool start/end events written
        # by make_tool_trace_middleware as the agent runs. Surface it so
        # the UI can render a live "what is the agent doing?" feed under
        # the spinner. Failure to parse → return [] rather than 500.
        progress_raw = record.get("progress", "")
        progress_parsed = []
        if progress_raw:
            try:
                progress_candidate = json.loads(progress_raw)
                if isinstance(progress_candidate, list):
                    progress_parsed = progress_candidate
            except (json.JSONDecodeError, ValueError):
                progress_parsed = []

        return {
            "status": status,
            "result": result_parsed,
            "error": record.get("error", ""),
            "progress": progress_parsed,
        }
    except Exception as e:
        _log().error(f"Failed to get agent job status: {e}")
        return None


def _start_agent_watchdog(
    service,
    job_id,
    mode,
    run_start_time_holder,
    stop_event,
    on_breach,
    name_prefix="ml_advisor_watchdog",
):
    """Spawn an independent watchdog thread that monitors an agent job
    for wall-clock and inactivity timeout breaches.

    The watchdog is the ground-truth safety net for SDK hangs that
    ``asyncio.wait_for`` fails to surface (observed in production —
    the May 2026 incident on PRD2 ran 21 minutes with the asyncio
    timeout never firing).  It runs on a dedicated thread, polls the
    KV record's ``last_activity`` field, and on breach calls
    ``on_breach`` to update the job + index an audit event.

    The watchdog does NOT attempt to kill the worker thread — Python
    threading does not support cooperative cancellation of synchronous
    I/O, and the Splunk Agent SDK is full of sync HTTP calls.  Instead
    it surfaces the failure to the user (via KV record + audit event)
    and releases the concurrency slot, leaving the doomed worker to
    eventually unwind on its own (or get reaped when splunkd recycles
    the persistent_handler process).  Slot release is idempotent
    (``_release_agent_slot``), so a worker that *does* eventually
    return won't double-release.

    Parameters
    ----------
    service : splunklib.client.Service
        System-token service used to read the KV record's
        ``last_activity`` field.
    job_id : str
        The agent job id (KV record key).
    mode : str
        Agent mode ("inspect" or "act") — selects the wall-clock
        budget via ``_resolve_hard_timeout_sec``.
    run_start_time_holder : list
        Single-element mutable list holding the worker's start time.
        The worker stamps this *inside* its function body (after
        thread spawn / scheduling overhead is excluded).  The
        watchdog reads it on every poll cycle so wall-clock checks
        match the worker's own elapsed-time accounting.
    stop_event : threading.Event
        Set by the worker thread when it terminates (success, error,
        or cancellation) so the watchdog can exit cleanly.
    on_breach : callable
        ``(reason: str, elapsed_s: int, last_activity_age_s: int)
        -> None`` — invoked at most once on the first detected
        breach.  The callback is responsible for writing
        ``status=error`` to the KV record, indexing the audit event,
        and releasing the agent slot.  Defined as a closure inside
        the worker so it can reach the worker's
        ``_index_agent_event`` helper and capture the worker-local
        service / token / index settings.
    name_prefix : str
        Thread name prefix (default ``ml_advisor_watchdog``) — kept
        configurable so future advisor variants can identify their
        watchdogs separately in thread dumps.

    Returns
    -------
    threading.Thread
        The started daemon watchdog thread.  Stops itself when
        ``stop_event`` is set or after firing ``on_breach`` once.
    """
    hard_timeout = _resolve_hard_timeout_sec(mode)

    def _watchdog():
        breach_emitted = False
        while not stop_event.wait(AGENT_WATCHDOG_POLL_INTERVAL_SEC):
            if breach_emitted:
                # First breach already reported.  Coast until the
                # worker thread releases ``stop_event`` so we don't
                # double-update the KV record.
                continue
            try:
                start_ts = run_start_time_holder[0] or time.time()
                elapsed_s = int(time.time() - start_ts)

                # Read last_activity from the KV record.  KV read
                # is the only I/O the watchdog does on the happy
                # path; <30ms typical.  On failure (transient KV
                # hiccup, network blip, etc.) we leave
                # ``last_activity`` as ``None`` and skip the
                # inactivity branch this poll iteration — the
                # wall-clock check below still fires regardless and
                # remains authoritative.
                #
                # Bugbot caught a false-abort regression on PR #1489
                # cycle 2 (Medium severity): the previous
                # implementation initialised ``last_activity = 0.0``
                # and then fell back to ``elapsed_s`` whenever
                # ``last_activity`` was falsy.  Because ``0.0`` is
                # falsy in Python, ANY KV read failure on a healthy
                # long-running agent (>180s elapsed) instantly
                # tripped the inactivity threshold and aborted the
                # run.  Sentinel-``None`` + an explicit ``is not
                # None`` guard on the inactivity branch fixes it.
                last_activity = None
                try:
                    collection = service.kvstore[_KV_COLLECTION_AGENT_JOBS]
                    records = collection.data.query(
                        query=json.dumps({"_key": job_id})
                    )
                    if records:
                        raw_la = records[0].get("last_activity")
                        if raw_la not in (None, "", 0, "0"):
                            try:
                                la_val = float(raw_la)
                                if la_val > 0:
                                    last_activity = la_val
                            except (TypeError, ValueError):
                                pass
                        # If the worker has already moved the record
                        # to a terminal state, our job is done — let
                        # the worker's finally release the slot.
                        if records[0].get("status") in (
                            "cancelled", "complete", "error"
                        ):
                            return
                except Exception:
                    pass

                # Inactivity age is only computed when we have a
                # genuine last_activity timestamp.  ``None`` means
                # "unknown" (KV unreachable, or the very first poll
                # cycle before any heartbeat / tool call has fired).
                last_activity_age_s = (
                    int(time.time() - last_activity)
                    if last_activity is not None
                    else None
                )

                # Breach checks, in priority order — wall-clock
                # first because it gives a longer-running diagnostic
                # message (mode-budget cited).  Inactivity second
                # because legitimate slow LLM turns can briefly trip
                # it (caller may want to widen
                # ``AGENT_INACTIVITY_TIMEOUT_SEC`` if false-positives
                # ever appear) — and is skipped entirely when we
                # have no genuine activity timestamp to compare
                # against.
                if elapsed_s >= hard_timeout:
                    on_breach(
                        reason=(
                            f"wall-clock budget exceeded "
                            f"({hard_timeout}s for mode={mode!r}) — "
                            f"watchdog timed out the run while "
                            f"asyncio.wait_for failed to surface "
                            f"the hang"
                        ),
                        elapsed_s=elapsed_s,
                        last_activity_age_s=(
                            last_activity_age_s
                            if last_activity_age_s is not None
                            else elapsed_s
                        ),
                    )
                    breach_emitted = True
                elif (
                    last_activity_age_s is not None
                    and last_activity_age_s >= AGENT_INACTIVITY_TIMEOUT_SEC
                ):
                    on_breach(
                        reason=(
                            f"no agent activity for "
                            f"{last_activity_age_s}s "
                            f"(threshold {AGENT_INACTIVITY_TIMEOUT_SEC}s) — "
                            f"likely SDK hang in tool-aggregation "
                            f"or structured-output extraction"
                        ),
                        elapsed_s=elapsed_s,
                        last_activity_age_s=last_activity_age_s,
                    )
                    breach_emitted = True
            except Exception as e:
                # Watchdog must NEVER crash silently — log the
                # exception and keep iterating so a transient KV
                # error doesn't disable the safety net.
                #
                # Use ``name_prefix`` (e.g. ``ml_advisor_watchdog``,
                # ``feed_lifecycle_watchdog``) rather than a
                # hardcoded "ML Advisor" string — this helper is
                # shared by all six advisors and the wrong label
                # in the log would mislead diagnosis when, say, the
                # FQM advisor's watchdog hits a transient KV
                # exception.  Bugbot caught the regression on PR
                # #1489 cycle 3 (Medium severity).
                try:
                    _log().warning(
                        f"{name_prefix} loop error "
                        f"(job={job_id}): {e}"
                    )
                except Exception:
                    pass

    thread = threading.Thread(
        target=_watchdog,
        daemon=True,
        name=f"{name_prefix}_{job_id[:8]}",
    )
    thread.start()
    return thread


def _make_agent_worker_watchdog(
    *,
    advisor_label,
    service,
    job_id,
    mode,
    run_start_time_holder,
    update_agent_job_fn,
    index_agent_event_fn,
    automated=False,
):
    """Higher-level helper that wires a watchdog + race-protection
    events for a single agent worker thread, returning the
    coordination primitives the worker uses.

    All Agent SDK advisor libs (ML, FQM, FLX-threshold, Component
    Health, Feed Lifecycle, Concierge) share the same SDK-hang risk
    — when the SDK silently wedges in tool-aggregation or
    structured-output extraction the outer ``asyncio.wait_for``
    sometimes fails to fire, leaving the user with a UI spinner
    that only resolves via the 17-minute stale-poll fallback.
    Rather than duplicate ~50 lines of watchdog wiring per advisor
    (multiple workers per advisor, six advisors, two-line
    mistake = silent regression), every advisor calls this single
    helper to get the same machinery.

    Returns
    -------
    (stop_event, fired_event, start_watchdog) : tuple
        - ``stop_event`` (threading.Event): the worker's ``finally``
          calls ``stop_event.set()`` so the watchdog exits cleanly
          on success / error / cancellation.
        - ``fired_event`` (threading.Event): set by the on-breach
          callback so the worker's own exception handlers detect
          "the watchdog already surfaced the failure" and skip
          duplicate KV writes.  In particular: if the worker
          eventually returns successfully AFTER the watchdog has
          already aborted the run, the late ``status=complete``
          write must be skipped — the user has been notified, the
          UI has moved on.
        - ``start_watchdog`` (callable): called once by the worker
          after stamping ``run_start_time_holder[0]``; spawns the
          watchdog thread.

    Parameters
    ----------
    advisor_label : str
        Human-readable advisor name (e.g. "ML Advisor", "Feed
        Lifecycle Advisor") — used in log messages and as the
        watchdog thread name prefix.  Slugified internally for the
        thread name.
    service : splunklib.client.Service
        System-token service for KV reads inside the watchdog poll
        loop.
    job_id : str
        Agent job id (KV record key).
    mode : str
        Agent mode — selects the wall-clock budget via
        ``_resolve_hard_timeout_sec``.  Concierge and other
        non-mode-aware advisors should pass ``"act"`` for the
        15-minute budget.
    run_start_time_holder : list
        Single-element mutable list holding the worker's start
        time (stamped by the worker after thread spawn overhead).
    update_agent_job_fn : callable
        ``(status: str, *, error: str | None = None) -> None`` —
        worker-supplied closure that wraps ``_update_agent_job``
        with the right service token / kwargs for this advisor.
        The watchdog calls it once with ``status="error"`` on
        breach.
    index_agent_event_fn : callable
        ``(result_dict, status: str, *, error_msg: str | None = None)
        -> None`` — worker-supplied closure that wraps the
        advisor's ``_index_agent_event`` with the right service /
        sourcetype / mode.  The watchdog calls it once with
        ``status="error"`` and ``result_dict=None`` on breach.
    automated : bool
        Whether this is a scheduled/batch run (True) vs an
        interactive UI launch (False).  Used in log message
        formatting only.
    """
    stop_event = threading.Event()
    fired_event = threading.Event()

    def _on_breach(reason, elapsed_s, last_activity_age_s):
        if fired_event.is_set():
            return
        fired_event.set()
        timeout_msg = (
            f"Agent run aborted by watchdog: {reason}. "
            f"Elapsed {elapsed_s}s, last activity "
            f"{last_activity_age_s}s ago."
        )
        try:
            auto_tag = ", automated=True" if automated else ""
            _log().error(
                f"{advisor_label} watchdog ABORT (job={job_id}, "
                f"mode={mode}{auto_tag}, elapsed={elapsed_s}s, "
                f"inactivity={last_activity_age_s}s): {timeout_msg}"
            )
        except Exception:
            pass
        try:
            update_agent_job_fn("error", error=timeout_msg)
        except Exception as e:
            # Watchdog cannot persist the timeout error to KV — the job
            # state will be stuck in "running" forever from the user's
            # perspective.  This is a real failure (state tracking is
            # broken), use ERROR.
            _log().error(
                f"watchdog: update_agent_job failed for "
                f"{job_id}: {e}"
            )
        try:
            index_agent_event_fn(None, "error", error_msg=timeout_msg)
        except Exception as e:
            # Audit event for a watchdog-aborted run is permanently lost
            # (no retry, no fallback).  Use ERROR so audit-pipeline
            # failures show up in error monitoring.
            _log().error(
                f"watchdog: index_agent_event failed for "
                f"{job_id}: {e}"
            )
        # Release the slot here, not just from the worker's
        # ``finally``: if the worker thread is genuinely stuck the
        # finally never runs and the slot would leak.  Idempotent
        # — safe to call again from the worker once it eventually
        # returns.
        try:
            _release_agent_slot(job_id)
        except Exception:
            pass
        # Signal the heartbeat ticker AND this watchdog thread to
        # stop NOW — regardless of whether the breach KV write
        # succeeded above.  Bugbot caught this on PR #1534 cycle 3
        # (Medium severity): if the worker is truly hung AND the
        # watchdog's ``_update_agent_job("error")`` call fails
        # (transient KV error), without this signal the ticker
        # would keep refreshing ``last_activity`` every 30s.  That
        # in turn would defeat ``get_agent_job_status``'s
        # stale-running fallback (which compares
        # ``max(created_at, last_activity)`` against
        # ``timeout + _STALE_RUNNING_BUFFER_SECONDS``) — the job
        # would stay stuck in ``"running"`` forever from the user's
        # perspective.  Before the ticker, the heartbeat would
        # naturally go stale and the fallback fired; we must
        # preserve that behaviour for the hung-worker + failed-
        # breach-write case.
        #
        # Setting ``stop_event`` here also lets the watchdog thread
        # exit cleanly without waiting on the (hung) worker's
        # ``finally`` to set it — fixes a thread leak that's
        # always been there on truly-hung agents, latent until now.
        try:
            stop_event.set()
        except Exception:
            pass

    # Slugify the advisor label for the watchdog thread name
    # (visible in thread dumps; useful for diagnosis when multiple
    # advisors are running concurrently).
    name_prefix = (
        advisor_label.lower()
        .replace(" advisor", "")
        .replace(" ", "_")
        + "_watchdog"
    )

    def _start():
        # Start the periodic heartbeat ticker FIRST so it begins
        # refreshing ``last_activity`` immediately — the watchdog
        # only fires on inactivity (or wall-clock) breach, but the
        # ticker prevents the inactivity branch from ever tripping
        # on legitimate slow LLM turns.  Both share the same
        # ``stop_event`` so the worker's terminal-state writeback
        # tears them down together.
        _start_agent_heartbeat_ticker(
            service=service,
            job_id=job_id,
            stop_event=stop_event,
        )
        return _start_agent_watchdog(
            service=service,
            job_id=job_id,
            mode=mode,
            run_start_time_holder=run_start_time_holder,
            stop_event=stop_event,
            on_breach=_on_breach,
            name_prefix=name_prefix,
        )

    return stop_event, fired_event, _start


def _release_agent_slot(job_id):
    """Release a concurrency slot. Idempotent."""
    global _active_agents
    with _released_slots_lock:
        if job_id in _released_slots:
            return
        _released_slots[job_id] = time.time()
        # Prevent unbounded growth: prune entries older than 1 hour
        if len(_released_slots) > 100:
            cutoff = time.time() - 3600
            stale_keys = [k for k, v in _released_slots.items() if v < cutoff]
            for k in stale_keys:
                del _released_slots[k]
    with _active_agents_lock:
        _active_agents = max(0, _active_agents - 1)


# ---------------------------------------------------------------------------
# ML Advisor Agent — Main Entry Point
# ---------------------------------------------------------------------------


def _get_recent_inspect_result(service, tenant_id, object_id, max_age_minutes=30):
    """Retrieve the most recent successful ML Advisor inspect result from the summary index."""
    from trackme_libs_ai import get_recent_agent_inspect_result

    return get_recent_agent_inspect_result(
        service,
        tenant_id,
        object_id,
        sourcetype="trackme:ai_agent:ml_advisor:inspect",
        max_age_minutes=max_age_minutes,
    )


def _is_structured_output_unsupported(exc):
    """Check if the model explicitly rejected tool use or structured output at the API level.

    Catches openai.BadRequestError HTTP 400 with messages like "does not support tools"
    or "does not support structured output" — the API-level rejection returned when the
    model does not have function-calling support. These are nested inside one or more
    ExceptionGroup layers.

    This is a hard failure — retrying will never help. Distinct from
    _is_agent_structured_output_failure which catches the silent/non-deterministic
    ToolStrategy failure (model ignores the respond tool) and is worth retrying.
    """
    # Check for explicit API rejection of tools or structured output (e.g. Ollama 400)
    try:
        from openai import BadRequestError as OpenAIBadRequestError
        if isinstance(exc, OpenAIBadRequestError):
            msg = str(exc).lower()
            if "does not support tools" in msg or "does not support structured" in msg:
                return True
    except ImportError:
        pass
    if isinstance(exc, BaseExceptionGroup):
        for sub_exc in exc.exceptions:
            if _is_structured_output_unsupported(sub_exc):
                return True
    if exc.__cause__ and _is_structured_output_unsupported(exc.__cause__):
        return True
    if exc.__context__ and not exc.__suppress_context__ and _is_structured_output_unsupported(exc.__context__):
        return True
    return False


def _is_agent_structured_output_failure(exc):
    """Check if the model silently failed to produce structured output via ToolStrategy.

    Catches KeyError: 'structured_response' — the SDK failure when a model using
    ToolStrategy calls real MCP tools but then outputs plain text instead of calling
    the `respond` tool, leaving structured_response absent from the LangGraph state.

    This is a non-deterministic failure (the same model may succeed on retry with a
    fresh agent context) — distinct from _is_structured_output_unsupported which catches
    hard API rejections where retrying is pointless.
    """
    if isinstance(exc, KeyError) and exc.args and exc.args[0] == "structured_response":
        return True
    # Recurse into ExceptionGroup layers (Python 3.11+ asyncio wrapping)
    if isinstance(exc, BaseExceptionGroup):
        return any(_is_agent_structured_output_failure(e) for e in exc.exceptions)
    if exc.__cause__ and _is_agent_structured_output_failure(exc.__cause__):
        return True
    if exc.__context__ and not exc.__suppress_context__:
        return _is_agent_structured_output_failure(exc.__context__)
    return False


def _check_agent_model_capability(model, provider_type, model_name):
    """No-op — retained for call-site compatibility. Capability is evaluated at runtime."""
    pass


_TOOL_STRATEGY_RESPOND_HINT = (
    "\n\n**IMPORTANT — how to submit your final answer**: When you have gathered "
    "sufficient information and completed your analysis, you MUST submit your findings "
    "by calling the `respond` tool with your complete structured output. "
    "Do NOT write your analysis as plain text — always use the `respond` tool to "
    "deliver the final answer. Failure to call `respond` will cause the session to fail."
)


def _build_initial_message_tool_strategy_hint(model, provider_type=None):
    """Return a ToolStrategy respond-tool hint if the SDK will use ToolStrategy for this model.

    The Splunk Agent SDK has two strategies for structured output:
    - ProviderStrategy (OpenAI, Azure, some Anthropic): sends response_format=json_schema
      alongside tool definitions. The model handles both natively.
    - ToolStrategy (Ollama, Mistral, others): adds a fake `respond` tool. The model must
      explicitly call `respond(structured_response=<JSON>)` when done gathering data.

    With ToolStrategy, some models will call real MCP tools correctly but then output
    their final answer as plain text instead of calling `respond`, leaving
    structured_response absent from the LangGraph state. An explicit prompt reminder
    improves reliability but does not guarantee success with all models.

    The ``provider_type`` argument captures the TrackMe-side decision to FORCE
    ToolStrategy on Anthropic / Google models (via
    ``force_tool_strategy_for_provider`` — see the module-level shim). The
    hint helper otherwise probes ``langchain.agents.factory._supports_provider_strategy``,
    which is a DIFFERENT function from the SDK-side
    ``splunklib.ai.engines.langchain._supports_provider_strategy`` the force
    helper patches. Without the ``provider_type`` hint, Anthropic / Google
    models forced onto ToolStrategy would be reported by the langchain
    probe as still ProviderStrategy-capable and the ``respond(...)`` reminder
    would be silently dropped — degrading agent reliability for the providers
    that need the reminder MOST (the constraint exists precisely because
    their structured-output path is unusable here).

    **No impact on non-forced providers.** For provider_type values that are
    NOT in ``_PROVIDERS_NEEDING_TOOL_STRATEGY`` (OpenAI / Azure / Mistral /
    Ollama / Custom / Splunk Hosted), the forced-path early return is skipped
    and the langchain probe runs identically to before — so the hint
    injection behaviour for those providers is byte-identical to the
    pre-#1821 behaviour.

    Returns the hint string when ToolStrategy is detected (either by explicit
    force or by langchain probe), empty string otherwise.
    """
    # Forced-ToolStrategy path: when the caller signals the active provider
    # is one we route through ``force_tool_strategy_for_provider``, the SDK
    # will use ToolStrategy regardless of what the langchain probe reports —
    # so the respond-tool hint is the right reminder to inject.
    if (provider_type or "").lower() in _PROVIDERS_NEEDING_TOOL_STRATEGY:
        return _TOOL_STRATEGY_RESPOND_HINT
    try:
        from langchain.agents.factory import _supports_provider_strategy
        if not _supports_provider_strategy(model):
            return _TOOL_STRATEGY_RESPOND_HINT
    except Exception:
        pass
    return ""


def _is_tool_result_bug(exc):
    """Check if an exception (possibly nested in ExceptionGroup) is a known
    LangGraph / Splunk-AI-SDK state-corruption bug that warrants a retry.

    The function name is historical — originally it matched only the
    ``tool_use``/``tool_result`` mismatch family (where the Anthropic
    BadRequestError reports a ``tool_use`` block without its paired
    ``tool_result``). It now matches a broader set of equivalent SDK-side
    state-corruption signatures, all of which produce the same outcome — a
    transient, retry-able failure with no underlying issue in our agent
    code or tools.

    Currently matched signatures:

      * ``"tool_use" + "tool_result"`` in the exception text — the
        Anthropic-side mismatch this helper was originally written for.
      * ``"No AIMessage found in input"`` — surfaced when LangGraph's
        ``tool_node._parse_input`` reverse-iterates the message history
        and finds zero ``AIMessage`` instances (the AIMessage that
        triggered the tool call has been pruned or dropped from the
        state). Same root cause family — a state inconsistency between
        the agent's perceived call and the SDK's persisted state — and
        a retry typically clears it because the agent rebuilds context
        on the next attempt.

    The SDK wraps the underlying error inside multiple layers of
    ExceptionGroup/BaseExceptionGroup. ``str(ExceptionGroup)`` only shows
    the outer message ("unhandled errors in a TaskGroup"), not the inner
    error. We must recursively inspect sub-exceptions to find the actual
    error.
    """
    # Direct check on the exception message — both signatures.
    exc_text = str(exc)
    if "tool_use" in exc_text and "tool_result" in exc_text:
        return True
    if "No AIMessage found in input" in exc_text:
        return True
    # Check nested ExceptionGroup sub-exceptions
    if isinstance(exc, BaseExceptionGroup):
        for sub_exc in exc.exceptions:
            if _is_tool_result_bug(sub_exc):
                return True
    # Check chained exceptions (__cause__ or __context__)
    if exc.__cause__ and _is_tool_result_bug(exc.__cause__):
        return True
    if exc.__context__ and not exc.__suppress_context__ and _is_tool_result_bug(exc.__context__):
        return True
    return False


# ---------------------------------------------------------------------------
# Transient provider/network error classifier — drives retry-on-blip
# ---------------------------------------------------------------------------
#
# RATIONALE
# ---------
# An AI advisor job that hits a network blip or a provider-side overload
# blip should retry rather than fail terminally. Before this helper, the
# retry loop in each ``_run_*_advisor_agent`` recognised only two SDK
# bugs (structured-output and ``tool_use``/``tool_result``); every
# other transient — ``APITimeoutError``, ``OverloadedError``,
# ``RateLimitError``, ``httpx.ReadTimeout``, a ``503``, a ``529`` —
# went straight to ``status="error"`` after a single try.
#
# Combined with the new per-HTTP-call timeout of
# ``_PER_CALL_HTTP_TIMEOUT_SEC`` (90s by default), the user-visible
# behaviour goes from "10-minute spinner then hard failure" to
# "90s wait, brief backoff, retry succeeds in 90% of cases".
#
# CLASSIFICATION RULES
# --------------------
# Class names are matched by STRING, not isinstance — we do not import
# the provider SDKs. This means a deployment that has only Anthropic
# wired up doesn't pay the cost of pulling in ``openai`` /
# ``google.api_core`` exception classes (and a future deployment that
# adds a fourth provider doesn't need a code change here as long as the
# class name is in the set).
#
# Recursion mirrors ``_is_tool_result_bug`` — the Agent SDK wraps real
# exceptions in nested ``BaseExceptionGroup`` layers, and the actual
# transient error is buried several levels deep.
#
# DO NOT add ``asyncio.TimeoutError`` to the set: that signal comes
# from our OUTER ``asyncio.wait_for(..., timeout=hard_timeout)`` and
# means the whole job has exhausted its wall-clock budget. Retrying
# would just re-enter the same wait and time out again.

# Class names (across providers) that indicate a transient / retry-friendly
# failure. String-matched against ``type(exc).__name__``.
_TRANSIENT_PROVIDER_ERROR_CLASSES = frozenset({
    # Anthropic SDK (anthropic.APIError tree)
    "APITimeoutError",          # SDK gave up before response arrived
    "APIConnectionError",       # could not establish / lost connection
    "APIStatusError",           # generic — we re-check status_code below
    "OverloadedError",          # Anthropic 529 (server explicitly overloaded)
    "RateLimitError",           # Anthropic 429
    "InternalServerError",      # 500
    "ServiceUnavailableError",  # 503 (some providers spell it differently)
    "APIError",                 # parent class, in case nothing more specific
    # OpenAI SDK (same class names — both APIs inherit a similar tree)
    # — covered by the Anthropic entries above (identical class names).
    # OpenAI also defines:
    "APIResponseValidationError",  # malformed response = retry once
    # Google google.api_core.exceptions
    "DeadlineExceeded",         # Google's APITimeoutError equivalent
    "ServiceUnavailable",       # Google 503 (note: no trailing "Error")
    "ResourceExhausted",        # Google 429 (rate limit / quota)
    "Aborted",                  # Google transient, recommended retry
    "Unavailable",              # grpc 14
    "RetryError",               # google.api_core catch-all
    "InternalServerError",      # already in set; mentioned for clarity
    # httpx (transport layer — both anthropic and openai use it underneath)
    "ReadTimeout",
    "ConnectTimeout",
    "WriteTimeout",
    "PoolTimeout",
    "ConnectError",
    "ReadError",
    "WriteError",
    "RemoteProtocolError",      # connection dropped mid-response
    "NetworkError",             # parent httpx network exception class
    "TimeoutException",         # httpx parent timeout class
})


def _is_transient_provider_error(exc):
    """True if the exception (possibly nested in ExceptionGroup / cause /
    context) is a transient provider or network error worth retrying.

    Matches by exception class NAME, optionally cross-checked against
    ``status_code`` for ``*StatusError`` / ``HTTPStatusError`` shapes
    where the class name alone (``APIStatusError``) is too generic — a
    400 should not retry; a 503 should.

    NOTE: ``asyncio.TimeoutError`` and our own ``RuntimeError`` /
    ``ValueError`` instances are deliberately NOT matched here — the
    former is the outer wall-clock cap (retrying loses the budget), the
    latter are programming errors that retries cannot fix.
    """
    if exc is None:
        return False

    cls_name = type(exc).__name__

    # Direct class-name match against the known-transient set.
    if cls_name in _TRANSIENT_PROVIDER_ERROR_CLASSES:
        # Special case: ``APIStatusError`` is a parent class — both
        # ``BadRequestError`` (400) and ``InternalServerError`` (500)
        # inherit from it. If status_code is exposed AND non-transient,
        # do NOT retry.
        if cls_name in ("APIStatusError", "HTTPStatusError"):
            status = getattr(exc, "status_code", None)
            if status is None:
                resp = getattr(exc, "response", None)
                if resp is not None:
                    status = getattr(resp, "status_code", None)
            if isinstance(status, int) and status not in _TRANSIENT_HTTP_CODES:
                return False
        return True

    # HTTP status probe even when class name didn't match — some
    # providers wrap their HTTP errors in custom classes whose name
    # we don't know but which expose a numeric status code.
    status = getattr(exc, "status_code", None)
    if status is None:
        resp = getattr(exc, "response", None)
        if resp is not None:
            status = getattr(resp, "status_code", None)
    if isinstance(status, int) and status in _TRANSIENT_HTTP_CODES:
        return True

    # Nested ExceptionGroup sub-exceptions
    if isinstance(exc, BaseExceptionGroup):
        for sub_exc in exc.exceptions:
            if _is_transient_provider_error(sub_exc):
                return True

    # Chained exceptions (__cause__ / __context__)
    if exc.__cause__ and _is_transient_provider_error(exc.__cause__):
        return True
    if (
        exc.__context__
        and not exc.__suppress_context__
        and _is_transient_provider_error(exc.__context__)
    ):
        return True

    return False


# Backoff schedule for the transient-retry path. Indexed by the NEXT
# attempt number (1-based). Attempt 1 is the initial try (no sleep).
# 5s + 15s gives the second and third attempts a chance to ride out a
# rolling provider blip without burning the user's wall-clock budget.
_TRANSIENT_RETRY_BACKOFF_SEC = [0.0, 5.0, 15.0, 30.0]


def _transient_retry_backoff_sec(next_attempt):
    """Sleep seconds before ``next_attempt`` of the retry loop. Bounded
    to the last entry of the schedule for safety."""
    if next_attempt < 1:
        return 0.0
    idx = min(next_attempt - 1, len(_TRANSIENT_RETRY_BACKOFF_SEC) - 1)
    return _TRANSIENT_RETRY_BACKOFF_SEC[idx]


# ---------------------------------------------------------------------------
# Agent error chain formatter
# ---------------------------------------------------------------------------
#
# The Splunk Agent SDK runs the agent inside multiple nested
# ``anyio.create_task_group()`` blocks (one for the MCP client session,
# one for the agent context-manager itself). Any exception raised by the
# underlying LLM provider, network stack, or tool implementation is
# re-raised by anyio wrapped in ``BaseExceptionGroup("unhandled errors in
# a TaskGroup", [...])`` — once per task-group layer. ``str(exc)`` on the
# outer wrapper only returns ``"unhandled errors in a TaskGroup (1 sub-
# exception)"``, hiding the real root cause from the user.
#
# ``format_agent_error_chain`` recursively unwraps the exception group(s)
# to find the leaf exception(s), then renders a two-line summary:
#
#   line 1 — interpretation: human-readable hint (when we recognise the
#            class), HTTP status, "transient" flag for retry-friendly
#            codes, request_id when available
#   line 2 — raw: ``[<fully-qualified class name>] <str(exc)>``
#
# Line 2 is ALWAYS included so an unknown provider's error body is
# preserved verbatim — the operator never loses information.
#
# Design notes:
#   - Class-name duck-typing, not isinstance: we don't need to import
#     anthropic / openai / google / httpx SDKs (some of which may not be
#     installed in every deployment).
#   - Status code probed under multiple attribute names because providers
#     don't agree (``status_code`` on anthropic/openai, ``code`` on
#     google's grpc layer, ``response.status_code`` on httpx-wrapped).
#   - Wrapped in try/except: the formatter must never mask the real
#     exception by raising one of its own. On any internal error, fall
#     back to ``str(exc)``.

# Transient HTTP codes — retry-friendly across providers
_TRANSIENT_HTTP_CODES = frozenset({429, 500, 502, 503, 504, 529})

# Class-name → human-readable hint. Class names are matched by string,
# not isinstance, so we don't need to import the provider SDKs. The hint
# is just the lead-in for the summary line; the raw exception output
# always follows on line 2 so unknown classes lose nothing.
_AGENT_ERROR_CLASS_HINTS = {
    # Anthropic
    "OverloadedError": "provider overloaded (Anthropic 529)",
    "RateLimitError": "rate limit hit",
    "APITimeoutError": "provider request timed out",
    "APIConnectionError": "network error reaching provider",
    "APIStatusError": "provider returned HTTP error status",
    "InternalServerError": "provider internal error",
    "ServiceUnavailableError": "provider service unavailable",
    "BadRequestError": "provider rejected request as malformed",
    "AuthenticationError": "provider authentication failed",
    "PermissionDeniedError": "provider denied permission",
    # Google api_core
    "Unavailable": "provider service unavailable (Google 503 / gRPC 14)",
    "ResourceExhausted": "provider quota exhausted (Google 429 / gRPC 8)",
    "DeadlineExceeded": "provider deadline exceeded",
    "ServerError": "provider server-side error",
    # httpx (network layer)
    "ConnectError": "network connection failed",
    "ConnectTimeout": "network connect timeout",
    "ReadTimeout": "network read timeout",
    "TimeoutException": "network timeout",
    "HTTPStatusError": "HTTP error status from provider",
    # asyncio
    "TimeoutError": "asyncio timeout",
    "CancelledError": "task cancelled",
}


def _exception_fqn(exc):
    """Return ``module.ClassName`` for the exception class, or just
    ``ClassName`` when the class lives in ``builtins`` / ``__main__``.

    Best-effort. Falls back to ``type(exc).__name__`` if the module
    attribute is missing for any reason."""
    try:
        cls = type(exc)
        mod = getattr(cls, "__module__", None)
        name = getattr(cls, "__name__", repr(cls))
        if mod and mod not in ("builtins", "__main__"):
            return f"{mod}.{name}"
        return name
    except Exception:
        return repr(type(exc))


def _walk_exception_leaves(exc):
    """Recursively descend ``BaseExceptionGroup`` / ``ExceptionGroup`` to
    return the leaf (non-group) exception instances.

    ``BaseExceptionGroup`` exposes ``.exceptions`` as the sub-exception
    list. A leaf is any exception without a non-empty ``.exceptions``
    attribute. This handles arbitrarily nested groups — the SDK's
    real-world traceback for a 529 has two levels of wrapping.
    """
    sub = getattr(exc, "exceptions", None)
    if sub:
        leaves = []
        for s in sub:
            leaves.extend(_walk_exception_leaves(s))
        return leaves
    return [exc]


def _format_leaf_exception(exc):
    """Format a single non-group leaf exception into a two-line message:

      line 1 — summary: human-readable hint, status, transient flag,
                        request_id (where available)
      line 2 — ``[<fqn>] <str(exc)>``  (the raw exception output,
                        always preserved up to a generous 2000-char cap)

    Both lines are always emitted. When we don't recognise the class,
    line 1 just shows the FQN — and line 2 still carries the full
    exception output so the operator sees the provider's actual message.

    Internal helper. Wrapped by ``format_agent_error_chain`` which also
    handles ExceptionGroup unwrapping and overall fall-back-to-str."""
    cls_name = getattr(type(exc), "__name__", "Exception")
    fqn = _exception_fqn(exc)
    hint = _AGENT_ERROR_CLASS_HINTS.get(cls_name)

    # Probe status code under the names different SDKs use:
    #   - anthropic / openai: ``.status_code`` on the exception itself
    #   - httpx-wrapped: ``.response.status_code``
    #   - google api_core: ``.code`` (grpc StatusCode enum or HTTP int)
    status = None
    try:
        status = getattr(exc, "status_code", None)
        if status is None:
            response = getattr(exc, "response", None)
            if response is not None:
                status = getattr(response, "status_code", None)
        if status is None:
            status = getattr(exc, "code", None)
    except Exception:
        status = None
    # Only treat status as a transient HTTP code when it's actually an
    # integer — google's gRPC ``code`` attribute can be a StatusCode enum
    # which we shouldn't accidentally render as "HTTP <enum>".
    status_int = status if isinstance(status, int) else None

    # Probe request_id (anthropic / openai both expose it on the
    # exception itself or in the response headers)
    req_id = None
    try:
        req_id = getattr(exc, "request_id", None)
        if not req_id:
            response = getattr(exc, "response", None)
            headers = getattr(response, "headers", None) if response is not None else None
            if headers and hasattr(headers, "get"):
                req_id = headers.get("x-request-id") or headers.get("request-id")
    except Exception:
        req_id = None

    # Build the summary line. When neither hint nor status nor req_id
    # gives us anything, fall back to the FQN so the line is never empty.
    summary_parts = []
    if hint:
        summary_parts.append(hint)
    if status_int is not None:
        summary_parts.append(f"HTTP {status_int}")
        if status_int in _TRANSIENT_HTTP_CODES:
            summary_parts.append("transient — retry typically succeeds")
    if req_id:
        summary_parts.append(f"request_id={req_id}")
    summary = " — ".join(summary_parts) if summary_parts else fqn

    # Raw exception output — always included. Generous cap to preserve
    # full provider error bodies while avoiding pathological cases.
    try:
        raw = str(exc).strip()
    except Exception:
        raw = repr(exc)
    if len(raw) > 2000:
        raw = raw[:1997] + "..."

    return f"{summary}\n[{fqn}] {raw}"


def format_agent_error_chain(exc):
    """Top-level error formatter — call this from every advisor's
    ``_worker`` ``except Exception`` block instead of ``str(exc)``.

    Recursively unwraps ``BaseExceptionGroup`` / ``ExceptionGroup`` to
    find the underlying leaf exception(s), then formats each leaf with
    ``_format_leaf_exception``. Multi-leaf groups (e.g. parallel tool
    calls that all failed) are joined with a clear delimiter so each
    cause is visible.

    The formatter is wrapped in try/except so its own failure NEVER
    masks the real exception — on any internal error, it falls back to
    ``str(exc)`` (the current behaviour before this helper was added).

    See ``ai-context/ai-advisors/agent-infrastructure.md`` § Error
    formatting for the rationale, examples per provider, and the
    design decision to use class-name duck-typing rather than
    isinstance.
    """
    try:
        leaves = _walk_exception_leaves(exc)
        if not leaves:
            return str(exc)
        if len(leaves) == 1:
            return _format_leaf_exception(leaves[0])
        # Multi-leaf: render each leaf separated by a clear delimiter so
        # the operator sees every cause when parallel tool calls failed.
        sections = [
            f"Sub-error {i + 1} of {len(leaves)}:\n{_format_leaf_exception(leaf)}"
            for i, leaf in enumerate(leaves)
        ]
        return "\n\n".join(sections)
    except Exception:
        # Defensive: NEVER let the formatter itself mask the real
        # exception. Fall back to the prior behaviour.
        try:
            return str(exc)
        except Exception:
            return repr(exc)


def _vtenant_allows_model_disable(vtenant_account):
    """Return True if the tenant allows automated ML model disablement."""
    return vtenant_account.get("ai_mladvisor_allow_model_disable", "0") == "1"


async def _run_ml_advisor_agent(service, model, config, tenant_id, component, object_id, object_name, mode,
                                user_context=None, automated=False, vtenant_account=None, job_id=None, server_name=None):
    """
    Run the ML Outlier Advisor agent asynchronously.

    Args:
        service: Splunk service connection
        model: SDK model (AnthropicModel, GoogleModel, or OpenAIModel)
        config: AI provider configuration dict (from get_ai_config)
        tenant_id: Tenant identifier
        component: Component type (dsm, dhm, flx, etc.)
        object_id: Entity _key hash in KV Store (used for KV lookups and scoring queries)
        object_name: Entity name (used for KPI metric queries where the dimension is 'object')
        mode: "inspect" (read-only analysis with recommendations) or "act" (apply changes)
        user_context: Optional free-text instructions from the user to guide the agent

    Returns:
        MLAdvisorResult (Pydantic model)
    """

    # Pin per-advisor logger for this async context.  All log calls
    # from this function's body AND from the shared infrastructure it
    # invokes (tool_middleware, _append_job_progress, …) resolve to the
    # ML Advisor's logger via ``_log()``.  Redundant with the
    # ContextVar default but explicit for symmetry with the other 5
    # advisors and clarity at the entry point.
    set_current_advisor_logger("trackme.rest.ai.ml_advisor")

    # Lazy imports: SDK requires Python 3.13+ (splunklib.ai version gate)
    from splunklib.ai.agent import Agent
    from splunklib.ai.messages import HumanMessage
    from splunklib.ai.hooks import before_model
    from splunklib.ai.limits import AgentLimits
    from splunklib.ai.tool_settings import ToolSettings, LocalToolSettings, ToolAllowlist

    # Resolve the model name for logging
    model_name = config.get("ai_model", "unknown")
    provider_type = config.get("ai_provider", "unknown")
    provider_name = config.get("provider_name", "unknown")

    # Read agent orchestration limits from provider config (with sensible defaults)
    if mode == "inspect":
        allowed_tags = ["ml_read", "maintenance_read"]
        agent_token_limit = max(1, int(config.get("ai_agent_token_limit", "150000")))
        agent_step_limit = max(1, int(config.get("ai_agent_step_limit", "20")))
    else:  # "act"
        # ``entity_metadata_write`` is the shared tag for cross-advisor
        # entity-metadata tools (labels, notes, …) defined in
        # ``trackme_ai_agent_tools``. Each specialised advisor opts in here
        # so the Agent SDK ToolAllowlist exposes them. ``maintenance_*`` are
        # the shared per-entity maintenance tools (read everywhere, write for
        # act-capable advisors). Concierge stays out of the write tags — it has
        # no static write tools by design.
        allowed_tags = [
            "ml_read",
            "ml_write",
            "entity_metadata_write",
            "maintenance_read",
            "maintenance_write",
        ]
        agent_token_limit = max(1, int(config.get("ai_agent_act_token_limit", "200000")))
        agent_step_limit = max(1, int(config.get("ai_agent_act_step_limit", "40")))

    _log().info(
        f"ML Advisor agent starting: mode={mode}, model={model_name}, "
        f"provider={provider_type} ({provider_name}), "
        f"token_limit={agent_token_limit}, step_limit={agent_step_limit}, "
        f"entity={object_name} ({object_id})"
    )

    # Build the initial context message — pin the current time so the LLM has
    # an unambiguous "now" anchor. Without this, models tend to infer the year
    # from training-data priors (skewed to 2024-2025) and produce epochs whose
    # year is wrong, which then get silently dropped at training time.
    _now_epoch = int(time.time())
    _now_iso_utc = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(_now_epoch))

    initial_message = (
        f"Analyze the ML outlier detection models for this TrackMe entity:\n\n"
        f"- **Tenant ID**: {tenant_id}\n"
        f"- **Component**: {component}\n"
        f"- **Object ID** (_key hash, use for KV lookups and scoring queries): {object_id}\n"
        f"- **Object Name** (entity name, use for KPI metric queries): {object_name}\n"
        f"- **Mode**: {mode}\n"
        f"- **Current time** (use this — do NOT infer): {_now_iso_utc} "
        f"(epoch {_now_epoch})\n\n"
        f"When proposing period exclusions, use ISO date strings anchored on the "
        f"current time above (e.g. \"2026-01-29\"). Do not compute epoch seconds "
        f"yourself — pass the date string and the API will convert it.\n\n"
    )

    if mode == "inspect":
        initial_message += (
            "Perform a read-only inspection. Analyze the entity's outlier models, "
            "metric patterns, and scoring history. Report your findings with specific, "
            "actionable recommendations but do NOT apply any changes."
        )
    else:
        initial_message += (
            "**MODE: ACT — You MUST apply changes using write tools.**\n\n"
            "Analyze the entity's outlier models, metric patterns, and scoring history. "
            "Then EXECUTE the appropriate remediation actions by calling the write tools:\n"
            "- Use `update_model_rules` to fix model configuration (thresholds, time_factor, etc.)\n"
            "- Use `set_false_positive` to clear false positive alerts\n"
            "- Use `add_period_exclusion` to exclude genuine anomaly windows from training\n"
            "- Use `trigger_model_retrain` to retrain models after configuration changes\n\n"
            "Do NOT just recommend — you MUST call the write tools to apply changes. "
            "Document every action in the actions_taken array of your response."
        )

        # Inject prior inspect result if available (saves redundant read phase)
        prior_result = _get_recent_inspect_result(service, tenant_id, object_id)
        if prior_result:
            initial_message += (
                f"\n\n**PRIOR INSPECTION RESULTS (completed within the last 30 minutes)**\n"
                f"A recent inspect run already analyzed this entity. Use these findings as "
                f"your starting point: call `get_entity_outlier_context` once to confirm "
                f"the entity state is unchanged, then proceed directly to the write tools.\n\n"
                f"```json\n{json.dumps(prior_result, indent=2)}\n```"
            )

    # Append user-provided context/instructions if present
    if user_context:
        initial_message += (
            f"\n\n**OPERATOR INSTRUCTIONS** (from the user running this analysis):\n"
            f"{user_context}"
        )

    # For models using SDK ToolStrategy (Ollama, Mistral, etc.), remind the model
    # it must call the `respond` tool to submit structured output.  ProviderStrategy
    # models (OpenAI, Azure, Anthropic) handle structured output natively and don't
    # need this hint.
    initial_message += _build_initial_message_tool_strategy_hint(model, provider_type)

    # Automated model-disable guard: inject constraint when automated=True and allow_model_disable=0
    if automated and not _vtenant_allows_model_disable(vtenant_account or {}):
        initial_message += (
            "\n\n**AUTOMATED MODE CONSTRAINT — MODEL DISABLE**: You must NOT call any write "
            "tool to fully disable an ML model in this automated run. Model disablement "
            "requires analyst review and is blocked by tenant policy. If disabling is "
            "warranted, include it as a recommendation in your reasoning_trace only."
        )

    # Sanitize SSL_CERT_FILE — Splunk may set this to a path that doesn't exist
    # in the subprocess environment, causing httpx to crash when creating the
    # ChatOpenAI transport.  We temporarily remove it and restore after the
    # agent completes to avoid permanently affecting other threads.
    _ssl_cert_file = os.environ.get("SSL_CERT_FILE")
    _ssl_removed = False
    if _ssl_cert_file and not os.path.isfile(_ssl_cert_file):
        del os.environ["SSL_CERT_FILE"]
        _ssl_removed = True

    # Tool-level model-disable guard: propagate the vtenant policy to the MCP
    # subprocess via environment variable inherited at subprocess start time.
    _model_disable_guard_prev = os.environ.get("TRACKME_AI_ALLOW_MODEL_DISABLE")
    os.environ["TRACKME_AI_ALLOW_MODEL_DISABLE"] = (
        "1" if _vtenant_allows_model_disable(vtenant_account or {}) else "0"
    )

    max_attempts = 3  # 1 initial + 2 retries for SDK tool_result bug
    last_error = None

    # Token/step usage tracking — captured via before_model hook (fires before each
    # model call; derived from req.state.messages since upstream PR #770 removed
    # the cached AgentState.token_count / total_steps fields).  The last captured
    # value approximates total usage (slightly underestimates by the last response's
    # output tokens, which is acceptable for cost monitoring purposes).
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
        # Heartbeat: refresh ``last_activity`` so the watchdog's
        # inactivity check sees liveness BEFORE entering the LLM call.
        # The May 2026 incident hung *during* an LLM round-trip — tool
        # calls had already updated ``last_activity`` (via
        # ``_append_job_progress`` in the tool middleware) but no
        # subsequent before_model fired because the SDK never
        # returned from the previous turn.  Refreshing here gives
        # the watchdog a clean "we're about to call the LLM" timestamp
        # so an LLM hang is detected from that point, not from the
        # last preceding tool call.
        try:
            _refresh_agent_heartbeat(service, job_id)
        except Exception:
            pass  # heartbeats are best-effort liveness signals

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
                            ML_ADVISOR_SYSTEM_PROMPT, config, vtenant_account
                        ),
                        service=service,
                        tool_settings=ToolSettings(
                            local=LocalToolSettings(allowlist=ToolAllowlist(tags=allowed_tags)),
                            remote=None,
                        ),
                        output_schema=MLAdvisorResult,
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
                                    "ML Advisor",
                                    job_id=job_id,
                                    service=service,
                                    advisor_kind="ml_advisor",
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
                        _log().info(
                            f"ML Advisor agent invoke starting: job_id={job_id}, mode={mode}, attempt={attempt}/{max_attempts}"
                        )
                        result = await agent.invoke([HumanMessage(content=initial_message)])
                        output = result.structured_output

                        actions_count = len(output.actions_taken) if isinstance(output, MLAdvisorResult) else 0
                        entity_status = output.entity_status if isinstance(output, MLAdvisorResult) else "unknown"
                        _log().info(
                            f"ML Advisor agent completed: mode={mode}, model={model_name}, "
                            f"entity_status={entity_status}, actions_taken_count={actions_count}, "
                            f"token_count={_token_count[0]}, steps={_steps_taken[0]}"
                        )

                        # Log a warning if act mode produced no actions
                        if mode == "act" and actions_count == 0:
                            _log().warning(
                                "ML Advisor act mode produced no actions_taken — "
                                "the model may have skipped write tool execution"
                            )

                        return output, _token_count[0], _steps_taken[0]

            except Exception as e:
                if _is_structured_output_unsupported(e):
                    # Hard API rejection (e.g. Ollama 400 "does not support tools") —
                    # no point retrying, the model cannot participate in the agentic loop.
                    raise RuntimeError(
                        f"Model '{model_name}' (provider: {provider_type}) does not support "
                        f"tool use or structured output, which is required by the ML Advisor "
                        f"agent. Please configure a model with function-calling support. "
                        f"Commercial API providers (OpenAI, Anthropic, Azure OpenAI) are "
                        f"recommended for reliable agentic workflows."
                    ) from e
                if _is_agent_structured_output_failure(e) and attempt < max_attempts:
                    # Model called tools but didn't call the `respond` tool at the end —
                    # non-deterministic with smaller open-source models. Retry with fresh
                    # agent context; the prompt hint may succeed on the next attempt.
                    _log().warning(
                        f"ML Advisor agent did not produce structured output "
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
                # Transient provider / network error — network blip,
                # provider 429/500/503/529, anthropic OverloadedError,
                # httpx.ReadTimeout etc. Retry with exponential backoff.
                # Combined with the per-call HTTP timeout patch installed
                # at module load, the worst-case wait between attempts
                # is bounded; in practice the second attempt nearly
                # always succeeds for transient blips.
                #
                # IMPORTANT — act-mode safety: gated to inspect mode.
                # In act mode the agent has write tools allowlisted
                # (``ml_write``, ``entity_metadata_write``) and may
                # have already executed non-idempotent operations
                # like ``add_period_exclusion`` or
                # ``trigger_model_retrain`` before the transient
                # surfaced. Retrying would restart ``agent.invoke()``
                # with a fresh conversation; the LLM would re-issue
                # the same write tools and the side effects would
                # duplicate. Inspect mode has read-only tools
                # (``ml_read`` only), so retry is always safe there.
                # See CodeRabbit review on PR #1754.
                if (
                    _is_transient_provider_error(e)
                    and attempt < max_attempts
                    and mode != "act"
                ):
                    delay = _transient_retry_backoff_sec(attempt + 1)
                    _log().warning(
                        f"ML Advisor agent hit transient provider error "
                        f"(attempt {attempt}/{max_attempts}, sleeping {delay}s before retry): "
                        f"{type(e).__name__}: {str(e)[:300]}"
                    )
                    await asyncio.sleep(delay)
                    last_error = e
                    continue
                # Diagnostic log when we recognise the error as
                # transient but the act-mode guard blocks the retry —
                # makes the act-mode case visible to operators rather
                # than a silent fall-through to ``raise``.
                if (
                    _is_transient_provider_error(e)
                    and mode == "act"
                ):
                    _log().warning(
                        f"ML Advisor agent hit transient provider error in act mode "
                        f"(attempt {attempt}/{max_attempts}) — NOT retrying because "
                        f"write tools may have executed; job will surface as error. "
                        f"{type(e).__name__}: {str(e)[:300]}"
                    )
                # SDK bug: LangGraph fails to produce tool_result for a tool_use,
                # causing Anthropic API to reject the next message. The error is
                # nested inside ExceptionGroup layers, so we recursively check.
                #
                # IMPORTANT — act-mode safety: same gating as the transient-
                # retry block above. CodeRabbit's revised analysis on PR #1754
                # (after my initial "by definition no write tool completed"
                # argument was challenged) is correct: ``tool_result_bug``
                # detects the LAST tool_use missing its tool_result pairing,
                # but EARLIER tool calls in the same conversation may already
                # have completed successfully. In act mode those earlier
                # tools include writes (``ml_write``, ``entity_metadata_write``)
                # whose side effects have landed. A retry restarts the agent
                # with a fresh conversation; the LLM may re-issue the same
                # write tools and duplicate the side effects. Gate to inspect
                # mode only.
                if (
                    _is_tool_result_bug(e)
                    and attempt < max_attempts
                    and mode != "act"
                ):
                    _log().warning(
                        f"ML Advisor agent hit SDK tool_result bug (attempt {attempt}/{max_attempts}), "
                        f"retrying with fresh agent context..."
                    )
                    last_error = e
                    continue
                if _is_tool_result_bug(e) and mode == "act":
                    _log().warning(
                        f"ML Advisor agent hit SDK tool_result bug in act mode "
                        f"(attempt {attempt}/{max_attempts}) — NOT retrying because "
                        f"earlier write tools may have already executed; job will "
                        f"surface as error."
                    )
                raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error

    finally:
        # Restore SSL_CERT_FILE if we removed it
        if _ssl_removed and _ssl_cert_file:
            os.environ["SSL_CERT_FILE"] = _ssl_cert_file
        # Restore model-disable guard env var
        if _model_disable_guard_prev is None:
            os.environ.pop("TRACKME_AI_ALLOW_MODEL_DISABLE", None)
        else:
            os.environ["TRACKME_AI_ALLOW_MODEL_DISABLE"] = _model_disable_guard_prev


def start_ml_advisor_async(
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
    Start the ML Outlier Advisor agent asynchronously.

    Creates a job record, spawns a background thread, and returns immediately
    with the job_id for polling.

    Args:
        system_service: Splunk service with system auth (for config access)
        user_service: Splunk service with user auth (for RBAC)
        request_info: REST handler request info
        tenant_id: Tenant identifier
        component: Component type
        object_id: Entity _key hash in KV Store
        object_name: Entity name (used for KPI metric queries)
        mode: "inspect" or "act"
        provider_name: AI provider name (None = first configured)
        user_context: Optional free-text instructions from the user
        launched_by: Audit attribution for the run — ``"ui"`` (default,
            manual launch from a TrackMe panel), ``"ai_assistant"`` (chat
            bridge, Phase 2), or ``"automation"`` (scheduled batch). Caller
            (REST handler) is responsible for validating the value before
            passing it through.
        chat_session_id: Free-form session identifier from the chat
            assistant. Only meaningful when ``launched_by="ai_assistant"`` —
            traces a run back to the conversation that requested it.

    Returns:
        dict with {job_id, status} or raises exception
    """
    global _active_agents

    # 1. Load AI provider config
    model, config = get_sdk_model(system_service, provider_name=provider_name)

    # 2. Check concurrency limit
    with _active_agents_lock:
        if _active_agents >= _MAX_CONCURRENT_AGENTS_DEFAULT:
            raise RuntimeError(
                f"AI agent at maximum capacity ({_MAX_CONCURRENT_AGENTS_DEFAULT} concurrent). "
                "Please try again later."
            )
        _active_agents += 1

    # 3. Create job record and build service — wrapped in try/except to release
    # the concurrency slot if setup fails before the worker thread starts.
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
        # Release the slot since the worker thread will never start
        with _active_agents_lock:
            _active_agents = max(0, _active_agents - 1)
        raise

    # 5. Capture request context for deferred index resolution in _worker
    splunkd_uri = f"{system_service.scheme}://{system_service.host}:{system_service.port}"
    session_key = request_info.system_authtoken
    server_name = request_info.server_servername

    # Audit-dashboard captures (see enrich_agent_event_for_audit).
    # Mutable holder so the thread's _worker() can stamp the start time AFTER
    # the worker actually begins running — this excludes thread spawn /
    # scheduling overhead from duration_ms and keeps interactive vs
    # automated runs comparable.  See enrich_agent_event_for_audit.
    _run_start_time = [time.time()]
    _request_user = getattr(request_info, "user", None) or None

    # Helper: index an AI agent event to the tenant summary index
    # Runs inside the _worker thread — resolves tenant index lazily to avoid blocking the API response.
    def _index_agent_event(svc, result_dict, agent_mode, status, error_msg=None, token_count=0, steps_taken=0):
        """Index AI agent results/errors as events in the summary index."""
        try:
            from trackme_libs import trackme_idx_for_tenant

            # Resolve tenant summary index (deferred to worker thread)
            try:
                idx_settings = trackme_idx_for_tenant(session_key, splunkd_uri, tenant_id)
                tenant_summary_idx = idx_settings.get("trackme_summary_idx", "trackme_summary")
            except Exception:
                tenant_summary_idx = "trackme_summary"

            sourcetype = f"trackme:ai_agent:ml_advisor:{agent_mode}"
            event = {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "component": component,
                "object_category": f"splk-{component}",
                "object_id": object_id,
                "object": object_name,
                "mode": agent_mode,
                "status": status,
                "provider_name": provider_name or "default",
                "model": config.get("ai_model", "unknown"),
                "automated": False,
                "token_count": token_count,
                "steps_taken": steps_taken,
                # Audit-attribution fields — let downstream search distinguish
                # manual UI launches from chat-bridge launches and trace runs
                # back to the conversation that authorised them.
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
                source="trackme:ai_agent",
                sourcetype=sourcetype,
                host=server_name,
            )
            _log().info(f"Indexed AI agent event: job={job_id}, mode={agent_mode}, status={status}, token_count={token_count}")
        except Exception as idx_e:
            # Audit event lost permanently (no retry path).  Use ERROR
            # so audit-pipeline failures surface in error monitoring.
            _log().error(f"Failed to index AI agent event (job={job_id}): {idx_e}")

    # Watchdog coordination — shared safety net for SDK hangs that
    # ``asyncio.wait_for`` fails to surface (see
    # ``_make_agent_worker_watchdog`` docstring).  ``_watchdog_stop``
    # is set in the worker's ``finally``; ``_watchdog_fired`` is set
    # by the on-breach callback so the worker's exception handlers
    # detect "watchdog already wrote the error" and skip duplicate
    # KV writes.
    _watchdog_stop, _watchdog_fired, _start_watchdog = _make_agent_worker_watchdog(
        advisor_label="ML Advisor",
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

    # 6. Spawn background thread
    def _worker():
        try:
            _run_start_time[0] = time.time()  # capture INSIDE worker — see _run_start_time comment above
            # Spawn the watchdog AFTER stamping the start time so
            # ``elapsed_s`` checks line up with the worker's own
            # accounting.
            _start_watchdog()
            result, token_count, steps_taken = asyncio.run(
                asyncio.wait_for(
                    _run_ml_advisor_agent(
                        agent_service, model, config, tenant_id, component, object_id, object_name, mode,
                        user_context=user_context,
                        server_name=server_name, job_id=job_id,
                    ),
                    timeout=_resolve_hard_timeout_sec(mode),
                )
            )
            # If the watchdog already declared the run failed, the
            # KV record is in ``error`` state.  Don't override it
            # with a late "complete" write — that would silently
            # destroy the user's failure notification and resurrect
            # a doomed run.
            if _watchdog_fired.is_set():
                _log().warning(
                    f"ML Advisor worker returned successfully AFTER "
                    f"watchdog abort (job={job_id}); preserving the "
                    f"watchdog's error state — discarding late result."
                )
                return
            # Store result
            result_dict = result.model_dump() if result else {"summary": "Agent completed without structured output"}
            _update_agent_job(system_service, job_id, "complete", result=result_dict)

            # Index the result event
            _index_agent_event(agent_service, result_dict, mode, "success",
                               token_count=token_count, steps_taken=steps_taken)

        except Exception as e:
            error_str = format_agent_error_chain(e)

            # Hard timeout fired (see ``_resolve_hard_timeout_sec``).
            # Almost always an SDK hang inside parallel-tool aggregation
            # or structured-output extraction — neither raises an
            # exception nor returns; only this outer ``asyncio.wait_for``
            # rescues us (when it works at all — see watchdog above
            # for the production-observed case where it doesn't).
            # Log clearly with the actual elapsed time, mark the job
            # error with a real message (not the empty
            # ``str(TimeoutError())``), index a real audit event with
            # ``status=error``, and ``return`` so the tool-result-bug
            # path below doesn't accidentally classify this.
            if isinstance(e, asyncio.TimeoutError):
                if _watchdog_fired.is_set():
                    return  # watchdog already wrote the error
                budget_s = _resolve_hard_timeout_sec(mode)
                elapsed_s = int(time.time() - _run_start_time[0])
                timeout_msg = (
                    f"Agent run exceeded {budget_s}s "
                    f"(elapsed: {elapsed_s}s, mode={mode}) — likely "
                    f"SDK hang in tool-aggregation or structured-"
                    f"output extraction"
                )
                _log().error(
                    f"ML Advisor agent TIMEOUT (job={job_id}, "
                    f"mode={mode}, elapsed={elapsed_s}s): {timeout_msg}"
                )
                _update_agent_job(system_service, job_id, "error", error=timeout_msg)
                _index_agent_event(agent_service, None, mode, "error", error_msg=timeout_msg)
                return  # ``finally`` still runs → _release_agent_slot fires


            # Detect the known SDK bug: tool_use without tool_result
            # The agent may have already taken actions before this error occurred.
            # Return a partial result so the UI can show what happened.
            is_tool_result_bug = _is_tool_result_bug(e)

            if _watchdog_fired.is_set():
                return  # watchdog already wrote the error
            if is_tool_result_bug:
                # Terminal failure path — retries are exhausted by the
                # time we reach this branch, and possibly partial writes
                # have already been applied.  Use ERROR so this surfaces
                # in error monitoring rather than blending in with
                # benign retry noise.
                _log().error(
                    f"ML Advisor agent hit known SDK state-corruption bug (job={job_id}): "
                    f"the agent may have completed partial actions before the error. "
                    f"This is a known limitation in the Splunk Agent SDK's LangGraph engine "
                    f"(tool_use/tool_result mismatch family — includes 'No AIMessage found in input')."
                )
                partial_result = {
                    "entity_status": "unknown",
                    "summary": (
                        "The AI agent encountered a known SDK state-corruption error during execution. "
                        "The agent may have completed some actions before the error. "
                        "Please check the entity's outlier configuration to verify what changes were applied, "
                        "and re-run the analysis if needed."
                    ),
                    "recommendations": [
                        {
                            "priority": "high",
                            "description": (
                                "Re-run the ML Advisor in inspect mode to verify the current state of the entity "
                                "and confirm which actions (if any) were successfully applied."
                            ),
                        }
                    ],
                    "anomaly_windows": [],
                    "actions_taken": [],
                    "reasoning_trace": f"Agent execution was interrupted by an SDK error: {error_str[:300]}",
                    "_partial_result": True,
                }
                _update_agent_job(system_service, job_id, "complete", result=partial_result)
                _index_agent_event(agent_service, partial_result, mode, "partial_error", error_msg=error_str)
            else:
                _log().error(f"ML Advisor agent error (job={job_id}): {e}", exc_info=True)
                _update_agent_job(system_service, job_id, "error", error=error_str)
                _index_agent_event(agent_service, None, mode, "error", error_msg=error_str)

        finally:
            # Stop the watchdog FIRST so it doesn't race with the
            # release_agent_slot below or fire after we're done.
            _watchdog_stop.set()
            _release_agent_slot(job_id)

    thread = threading.Thread(target=_worker, daemon=True, name=f"ml_advisor_{job_id[:8]}")
    thread.start()

    return {"job_id": job_id, "status": "running"}


def start_ml_advisor_from_search_context(
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
    Start the ML Outlier Advisor agent from a streaming command context.

    Same as start_ml_advisor_async() but accepts streaming command context
    (service, session_key, splunkd_uri, server_name) instead of request_info.
    Used by the automated mladvisor scheduled backend.

    Returns:
        dict with {job_id, status} or raises exception
    """
    global _active_agents

    # 1. Load AI provider config
    model, config = get_sdk_model(service, provider_name=provider_name)

    # 2. Check concurrency limit
    with _active_agents_lock:
        if _active_agents >= _MAX_CONCURRENT_AGENTS_DEFAULT:
            raise RuntimeError(
                f"AI agent at maximum capacity ({_MAX_CONCURRENT_AGENTS_DEFAULT} concurrent). "
                "Please try again later."
            )
        _active_agents += 1

    # 3. Create job record and build agent service
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
            _active_agents = max(0, _active_agents - 1)
        raise

    # End-to-end run timer for the audit dashboard.
    # Mutable holder so the thread's _worker() can stamp the start time AFTER
    # the worker actually begins running — this excludes thread spawn /
    # scheduling overhead from duration_ms and keeps interactive vs
    # automated runs comparable.  See enrich_agent_event_for_audit.
    _run_start_time = [time.time()]

    # 4. Helper: index an AI agent event to the tenant summary index
    def _index_agent_event(svc, result_dict, agent_mode, status, error_msg=None, token_count=0, steps_taken=0):
        try:
            from trackme_libs import trackme_idx_for_tenant

            try:
                idx_settings = trackme_idx_for_tenant(session_key, splunkd_uri, tenant_id)
                tenant_summary_idx = idx_settings.get("trackme_summary_idx", "trackme_summary")
            except Exception:
                tenant_summary_idx = "trackme_summary"

            sourcetype = f"trackme:ai_agent:ml_advisor:{agent_mode}"
            event = {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "component": component,
                "object_category": f"splk-{component}",
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
                # of ``"ui"``.  The dashboard's base SPL filters on
                # ``automated="true"`` so this is redundant for
                # filtering — but it keeps audit attribution
                # accurate in the recent-runs table.
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
                source="trackme:ai_agent:mladvisor",
                sourcetype=sourcetype,
                host=server_name,
            )
            _log().info(f"Indexed automated AI agent event: job={job_id}, mode={agent_mode}, status={status}, token_count={token_count}")
        except Exception as idx_e:
            # Audit event lost permanently (no retry path).  Use ERROR
            # so audit-pipeline failures surface in error monitoring.
            _log().error(f"Failed to index automated AI agent event (job={job_id}): {idx_e}")

    # Watchdog coordination — see ``_make_agent_worker_watchdog``
    # docstring.  Same shared safety net as the interactive
    # ``start_ml_advisor_async`` worker, scoped to the automated
    # run's service / auth context (passes ``service`` for KV
    # updates rather than ``system_service``).
    _watchdog_stop, _watchdog_fired, _start_watchdog = _make_agent_worker_watchdog(
        advisor_label="ML Advisor",
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

    # 5. Spawn background thread
    def _worker():
        try:
            _run_start_time[0] = time.time()  # capture INSIDE worker — see _run_start_time comment above
            _start_watchdog()
            result, token_count, steps_taken = asyncio.run(
                asyncio.wait_for(
                    _run_ml_advisor_agent(
                        agent_service, model, config, tenant_id, component, object_id, object_name, mode,
                        automated=True, vtenant_account=vtenant_account or {},
                        server_name=server_name, job_id=job_id,
                    ),
                    timeout=_resolve_hard_timeout_sec(mode),
                )
            )
            if _watchdog_fired.is_set():
                _log().warning(
                    f"ML Advisor automated worker returned successfully "
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
            # Almost always an SDK hang inside parallel-tool aggregation
            # or structured-output extraction — neither raises an
            # exception nor returns; only this outer ``asyncio.wait_for``
            # rescues us (when it does — the watchdog is the
            # production-observed backstop).
            if isinstance(e, asyncio.TimeoutError):
                if _watchdog_fired.is_set():
                    return  # watchdog already wrote the error
                budget_s = _resolve_hard_timeout_sec(mode)
                elapsed_s = int(time.time() - _run_start_time[0])
                timeout_msg = (
                    f"Agent run exceeded {budget_s}s "
                    f"(elapsed: {elapsed_s}s, mode={mode}) — likely "
                    f"SDK hang in tool-aggregation or structured-"
                    f"output extraction"
                )
                _log().error(
                    f"ML Advisor agent TIMEOUT (job={job_id}, "
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
                # partial writes.  ERROR (not WARNING) so it surfaces
                # in error monitoring.
                _log().error(
                    f"ML Advisor agent hit SDK tool_result bug (job={job_id}): "
                    f"automated run, partial actions may have been applied."
                )
                partial_result = {
                    "entity_status": "unknown",
                    "summary": "Automated inspection interrupted by SDK error. Partial actions may have been applied.",
                    "recommendations": [],
                    "anomaly_windows": [],
                    "actions_taken": [],
                    "reasoning_trace": f"Agent interrupted by SDK error: {error_str[:300]}",
                    "_partial_result": True,
                }
                _update_agent_job(service, job_id, "complete", result=partial_result)
                _index_agent_event(agent_service, partial_result, mode, "partial_error", error_msg=error_str)
            else:
                _log().error(f"ML Advisor automated agent error (job={job_id}): {e}", exc_info=True)
                _update_agent_job(service, job_id, "error", error=error_str)
                _index_agent_event(agent_service, None, mode, "error", error_msg=error_str)

        finally:
            _watchdog_stop.set()
            _release_agent_slot(job_id)

    thread = threading.Thread(target=_worker, daemon=True, name=f"ml_advisor_auto_{job_id[:8]}")
    thread.start()

    return {"job_id": job_id, "status": "running"}

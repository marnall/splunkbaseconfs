"""
bin/tools.py — local tools exposed to the agentic Agent.

splunklib.ai discovers this file automatically when a handler enables
`tool_settings=ToolSettings(local=True)`. Each `@registry.tool()`-decorated
function becomes an invocable tool whose signature, docstring and (optional)
ToolContext are advertised to the LLM.

This module ONLY runs on Python 3.13+ (splunklib.ai is imported eagerly at
load). For Splunk 10.0/10.1 fallback workers this file is never imported.

Tool design philosophy:
  • Each tool does ONE thing well. The LLM composes them.
  • Tools that read Splunk data take ctx.service and run as the calling user.
  • Tools that need to write (KV, lookup) are explicit (no surprises).
  • Tools never raise GuardrailBlockedError; they return structured errors so
    the Agent can recover.

NOTE: Do NOT add `from __future__ import annotations` here. splunklib.ai's
ToolRegistry inspects raw type objects via func.__annotations__ to detect
ToolContext parameters; if annotations become strings, ctx-stripping fails
and pydantic chokes trying to schemify the ToolContext class.
"""
import sys
if sys.version_info < (3, 13):
    raise ImportError("bin/tools.py requires Python 3.13+ (agentic path only)")

# bootstrap puts bin/lib + site-packages on sys.path before tools.py is imported
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from bootstrap import setup_paths
setup_paths()

import logging
from typing import Any

from splunklib.ai.registry import ToolContext, ToolRegistry  # type: ignore
from splunklib.results import JSONResultsReader  # type: ignore

LOG = logging.getLogger("aiqa.tools")

registry = ToolRegistry()


# ---------------------------------------------------------------------------
# Schema-discovery tools — let the Agent look up what indexes/fields exist
# before generating SPL, instead of hallucinating field names.
# ---------------------------------------------------------------------------

@registry.tool(tags=["schema", "spl"])
def list_indexes(ctx: ToolContext) -> list[str]:
    """Return the names of all indexes the calling user can search.

    Useful when the user asks "what data do we have?" or when generating SPL
    that should reference a real index name. Empty list if no indexes
    are accessible.
    """
    try:
        return [ix.name for ix in ctx.service.indexes if not ix.name.startswith("_")]
    except Exception as e:
        ctx.logger.warning("list_indexes failed: %s", e)
        return []


@registry.tool(tags=["schema", "spl"])
def list_sourcetypes(ctx: ToolContext, index: str, max_count: int = 50) -> list[str]:
    """Return distinct sourcetypes present in the given index (last 24h sample).

    :param index: Index name to inspect (must be accessible to caller).
    :param max_count: Cap on how many sourcetypes to return.
    """
    try:
        stream = ctx.service.jobs.oneshot(
            f"| metadata type=sourcetypes index={index} | head {max_count} | fields sourcetype",
            output_mode="json",
            earliest_time="-24h@h",
            latest_time="now",
        )
        result = JSONResultsReader(stream)
        return [r["sourcetype"] for r in result if isinstance(r, dict) and "sourcetype" in r]
    except Exception as e:
        ctx.logger.warning("list_sourcetypes(%s) failed: %s", index, e)
        return []


@registry.tool(tags=["schema", "spl"])
def sample_fields(ctx: ToolContext, index: str, sourcetype: str, sample_size: int = 100) -> list[str]:
    """Return the field names found in a small sample of events for an index/sourcetype.

    Useful when generating SPL that depends on specific field names — call
    this BEFORE assuming a field exists.
    """
    try:
        stream = ctx.service.jobs.oneshot(
            f"search index={index} sourcetype={sourcetype} | head {sample_size} | fieldsummary | fields field",
            output_mode="json",
            earliest_time="-1h@h",
            latest_time="now",
        )
        result = JSONResultsReader(stream)
        return [r["field"] for r in result if isinstance(r, dict) and "field" in r]
    except Exception as e:
        ctx.logger.warning("sample_fields(%s,%s) failed: %s", index, sourcetype, e)
        return []


# ---------------------------------------------------------------------------
# Template discovery — surface saved query templates to the Agent so it can
# offer a starting point or pick a template that matches the user's intent.
# Templates are NL→SPL patterns stored in the mcp_query_templates KV collection.
# v3 records have NL only; v4 records also carry `spl` and `tags`.
# ---------------------------------------------------------------------------

import re as _re

_TEMPLATE_TOKEN_RE = _re.compile(r"\w+", _re.UNICODE)

# Words that show up in nearly every Splunk question and add no signal to a
# template lookup. Keep this list small — over-stripping hurts recall.
_STOPWORDS = frozenset({
    "a", "an", "and", "any", "are", "as", "at", "be", "by", "for",
    "from", "give", "has", "have", "how", "i", "in", "is", "it", "its",
    "list", "many", "me", "my", "of", "on", "or", "show", "that", "the",
    "to", "us", "want", "was", "we", "what", "when", "where", "which",
    "who", "with", "you", "your",
})


def _tokenize_template_text(text: str) -> set[str]:
    """Lowercase + split on \\w+ and drop stopwords. Used for relevance scoring."""
    if not text:
        return set()
    return {
        t for t in (m.group(0).lower() for m in _TEMPLATE_TOKEN_RE.finditer(text))
        if len(t) > 1 and t not in _STOPWORDS
    }


def _score_template(record: dict, query_tokens: set[str]) -> float:
    """Cheap relevance score: weighted token overlap against name + nl + tags.

    The Agent re-ranks anyway, so this just has to pull the right few candidates
    out of a few hundred KV rows.
    """
    if not query_tokens:
        return 0.0
    score = 0.0
    weights = {
        "name": 3.0,
        "natural_language": 2.0,
        "description": 1.0,
        "tags": 2.0,
    }
    for field, weight in weights.items():
        toks = _tokenize_template_text(str(record.get(field) or ""))
        overlap = len(query_tokens & toks)
        if overlap:
            score += weight * overlap
    return score


def _format_template_record(r: dict) -> dict:
    """Shape a raw KV row into the dict structure tools return to the LLM."""
    return {
        "template_id": r.get("template_id", ""),
        "name": r.get("name", ""),
        "description": r.get("description", ""),
        "natural_language": r.get("natural_language", ""),
        "category": r.get("category", ""),
        # v4 fields — may be empty on legacy v3 rows.
        "spl": r.get("spl", "") or "",
        "tags": r.get("tags", "") or "",
    }


@registry.tool(tags=["templates"])
def search_templates(
    ctx: ToolContext,
    query: str = "",
    category: str = "",
    limit: int = 5,
) -> list[dict]:
    """Search saved query templates ranked by relevance to a natural-language query.

    Templates are reusable NL→SPL patterns (the mcp_query_templates KV collection).
    Call this when the user's question might match a known pattern — if a returned
    template has a non-empty `spl` field that fits the question, reuse / adapt it
    rather than generating SPL from scratch. If `spl` is empty (legacy v3 row),
    treat `natural_language` as an intent example.

    :param query: Free-text terms matched against template name / description /
                  natural_language / tags. Pass the user's NL question (or a
                  paraphrase). Empty string = return most recent templates.
    :param category: Restrict to one of: Security, Performance, Network,
                     Application, Infrastructure, Other. Empty = all categories.
    :param limit: Max number of templates to return (default 5, max 20).

    Returns up to `limit` records sorted by relevance to `query` (or by recency
    when query is empty). Each record contains template_id, name, description,
    natural_language, category, spl, tags.
    """
    try:
        # Don't use `int(limit or 5)` — that turns 0 into 5 instead of clamping to 1.
        limit = max(1, min(int(limit), 20))
    except (TypeError, ValueError):
        limit = 5
    try:
        coll = ctx.service.kvstore["mcp_query_templates"]
        kv_filter = {"category": category} if category else {}
        # Pull a larger candidate pool when re-ranking — KV `limit` would clip
        # before we apply relevance scoring.
        pool_size = max(limit * 8, 50) if query else limit
        records = coll.data.query(query=kv_filter, limit=pool_size) or []

        if not query:
            # No query → just return what KV gave us (KV doesn't guarantee an
            # order, but for a small template library this is fine).
            return [_format_template_record(r) for r in records[:limit]]

        query_tokens = _tokenize_template_text(query)
        scored = [(_score_template(r, query_tokens), r) for r in records]
        scored = [(s, r) for s, r in scored if s > 0]
        scored.sort(key=lambda sr: sr[0], reverse=True)
        return [_format_template_record(r) for _, r in scored[:limit]]
    except Exception as e:
        ctx.logger.warning("search_templates failed: %s", e)
        return []


@registry.tool(tags=["templates"])
def get_template(ctx: ToolContext, template_id: str) -> dict:
    """Fetch a single template by template_id.

    Use this after `search_templates` has identified a strong match and you
    want to confirm the full SPL / tags before reusing the template. Returns
    an empty dict if no such template exists.

    :param template_id: UUID-form template_id (the field, not the KV _key).
    """
    if not template_id:
        return {}
    try:
        coll = ctx.service.kvstore["mcp_query_templates"]
        rows = coll.data.query(query={"template_id": template_id}, limit=1) or []
        return _format_template_record(rows[0]) if rows else {}
    except Exception as e:
        ctx.logger.warning("get_template(%s) failed: %s", template_id, e)
        return {}


# ---------------------------------------------------------------------------
# SPL validation — cheap pre-flight before executing a generated SPL.
# Uses splunkd's dispatch dry-run (preview=true, exec_mode=normal) so we don't
# burn a real search slot, but still get a syntax error if the SPL is wrong.
# ---------------------------------------------------------------------------

@registry.tool(tags=["spl", "validation"])
def validate_spl_syntax(ctx: ToolContext, spl: str) -> dict[str, Any]:
    """Validate that an SPL string parses cleanly without dispatching it.

    Returns {valid: bool, error: str}. If valid is False, error contains
    splunkd's parser message — the Agent can use that to repair the SPL.
    """
    try:
        # `parse` REST endpoint returns the parsed search tree if valid;
        # raises HTTPError(400, ...) otherwise.
        ctx.service.post("search/parser", q=spl)
        return {"valid": True, "error": ""}
    except Exception as e:
        return {"valid": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Dry-run executor — small-sample probe to see whether the SPL works at all
# before committing the user's quota to a full run.
# ---------------------------------------------------------------------------

@registry.tool(tags=["spl", "execution"])
def execute_spl_dry_run(
    ctx: ToolContext,
    spl: str,
    earliest: str = "-1h@h",
    latest: str = "now",
    sample_size: int = 10,
) -> dict[str, Any]:
    """Run an SPL against Splunk capped at `sample_size` rows.

    Returns {success: bool, count: int, fields: list[str], data: list[dict],
    error: str}. The Agent can use this to confirm the SPL actually returns
    something before showing it to the user.
    """
    try:
        capped = f"{spl} | head {sample_size}"
        stream = ctx.service.jobs.oneshot(
            capped, output_mode="json",
            earliest_time=earliest, latest_time=latest,
        )
        result = JSONResultsReader(stream)
        rows = [r for r in result if isinstance(r, dict)]
        fields = list(rows[0].keys()) if rows else []
        return {
            "success": True,
            "count": len(rows),
            "fields": fields,
            "data": rows,
            "error": "",
        }
    except Exception as e:
        return {
            "success": False,
            "count": 0,
            "fields": [],
            "data": [],
            "error": str(e),
        }


if __name__ == "__main__":
    # Required by splunklib.ai's local-tool discovery — the SDK invokes this
    # module as a child process to enumerate the registry.
    registry.run()

"""Shared SQL-safety policy for hdxsearch and hdxsql.

Two entry points share a single function-name denylist:

- `validate_where(expr)` — for a user-supplied WHERE-clause subtree pasted into
  a connector-built SELECT. Rejects subqueries, bare SELECTs, and table
  references (the escape vectors specific to that splice point) in addition to
  the function denylist.
- `validate_statement(stmt)` — for a complete user-supplied statement. Limits
  the top-level node to read-only constructs (Select / Union family / With /
  EXPLAIN-Command) and rejects `INTO OUTFILE`. Does NOT reject
  Subquery/Select/Table inside the body because those are legitimate
  constructs in a self-contained user query.

Both validators raise `SqlSafetyError`, a subclass of `HdxCommandFatalError`,
so the existing top-level `except HdxCommandFatalError` in each command
catches them uniformly.
"""

import os
import sys
from typing import Tuple, Type

from errors import HdxCommandFatalError

# Match hdxsearch.py's bootstrap so the vendored sqlglot wins over any
# site-packages copy that might be present.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError


# ClickHouse functions that read from external sources or escape the local query context.
# These are the realistic exfiltration / SSRF vectors a malicious clause could reach for;
# arbitrary computation on local columns is fine, so we denylist by name rather than allowlist.
DENYLISTED_FUNCTIONS: frozenset = frozenset(
    {"file", "url", "remote", "remotesecure", "clusterallreplicas", "executequery"}
)


class SqlSafetyError(HdxCommandFatalError):
    """A user-visible error raised by the SQL-safety validators.

    Subclass of `HdxCommandFatalError` so the top-level error handlers in
    `HdxSearch.generate` and `HdxSql.generate` catch it without changes.
    """

    pass


def _reject_where_node(node: exp.Expression) -> SqlSafetyError:
    return SqlSafetyError(
        f"WHERE clause contains a disallowed expression ({type(node).__name__}). "
        "Subqueries, cross-table references, and specific server-side functions are not permitted."
    )


def _reject_denylisted_function(node: exp.Expression, fn_name: str) -> SqlSafetyError:
    return SqlSafetyError(
        f"Query contains a disallowed function ({fn_name}). "
        "Functions that read from external sources or escape the local query context are not permitted."
    )


def _is_denylisted_function(node: exp.Expression) -> Tuple[bool, str]:
    """Return (is_denylisted, function_name_lower) for the given node.

    sqlglot represents functions two ways: known functions get typed subclasses
    (exp.Url, exp.Initcap, ...) whose canonical name comes from sql_name();
    unknown function names are parsed as exp.Anonymous with the raw name.
    Check both paths so e.g. `url(...)` is caught whether or not sqlglot has a
    dedicated node for it.

    sql_name() is not implemented on every Func subclass. When it raises, fall
    back to the Python class name lower-cased so a denylisted function whose
    sql_name() happens to fail (e.g. `exp.Url.sql_name()` regressing in a
    future sqlglot bump) cannot slip past the denylist.
    """
    if isinstance(node, exp.Anonymous):
        name = node.name.lower()
        return (name in DENYLISTED_FUNCTIONS, name)
    if isinstance(node, exp.Func):
        try:
            name = type(node).sql_name().lower()
        except (NotImplementedError, AssertionError):
            name = type(node).__name__.lower()
        return (name in DENYLISTED_FUNCTIONS, name)
    return (False, "")


def validate_where(expr: exp.Expression) -> None:
    """Validate a user-supplied WHERE subtree before it is spliced into the assembled query.

    The connector's table/column allowlist only constrains the structural SQL it builds itself;
    the user-supplied WHERE is pasted into that SQL. Walk the parsed AST and reject anything that
    could reach outside the configured table: subqueries (arbitrary SELECTs), bare table refs
    (cross-table reads), and the denylisted functions above.

    Raises:
        SqlSafetyError: if the expression contains a disallowed construct.
    """
    for node in expr.walk():
        if isinstance(node, (exp.Subquery, exp.Select, exp.Table)):
            raise _reject_where_node(node)
        is_bad, fn_name = _is_denylisted_function(node)
        if is_bad:
            raise _reject_where_node(node)


# Top-level statement types accepted by validate_statement. EXPLAIN and its
# variants are represented as exp.Command and handled separately below.
_ACCEPTED_TOP_LEVEL_TYPES: Tuple[Type[exp.Expression], ...] = (
    exp.Select,
    exp.Union,
    exp.Intersect,
    exp.Except,
    exp.With,
)


def _is_accepted_top_level(stmt: exp.Expression) -> bool:
    if isinstance(stmt, _ACCEPTED_TOP_LEVEL_TYPES):
        return True
    # EXPLAIN and its variants (AST/SYNTAX/PIPELINE/PLAN/ESTIMATE) all parse
    # as an exp.Command with name="EXPLAIN" and carry the wrapped statement
    # as raw text. `_validate_explain_body` re-parses it so the denylist
    # tree walk also reaches the inner statement (closing a bypass).
    if isinstance(stmt, exp.Command):
        name = (stmt.name or "").upper()
        if name.startswith("EXPLAIN"):
            return True
    return False


def _has_into_outfile(stmt: exp.Expression) -> bool:
    """Return True if any Select in the tree carries an INTO OUTFILE clause.

    Defensive: the current vendored sqlglot raises at the parse layer for
    INTO OUTFILE, so this check is reached only if a future upgrade starts
    parsing it structurally.
    """
    for select in stmt.find_all(exp.Select):
        into = select.args.get("into")
        if into is None:
            continue
        # IntoOutfile / similar dedicated subclass introduced upstream.
        if type(into).__name__ in ("IntoOutfile", "OutFile"):
            return True
        # Generic Into whose target identifies an OUTFILE marker.
        target = into.args.get("this") if hasattr(into, "args") else None
        if target is not None:
            target_name = getattr(target, "name", "") or ""
            if str(target_name).upper() == "OUTFILE":
                return True
    return False


# EXPLAIN variant keywords that may prefix the inner statement inside the body
# literal of an `EXPLAIN <variant> <stmt>` Command. Stripped before re-parse so
# the denylist tree walk and read-only check apply to the underlying statement.
_EXPLAIN_VARIANT_KEYWORDS: Tuple[str, ...] = ("AST", "SYNTAX", "PIPELINE", "PLAN", "ESTIMATE")

# Defense-in-depth bound on EXPLAIN nesting recursion. ClickHouse itself doesn't
# meaningfully nest beyond one level; capping protects against pathological input.
_MAX_EXPLAIN_NESTING: int = 4


def strip_explain_variant_prefix(body: str) -> Tuple[str, str]:
    """Strip a leading EXPLAIN-variant keyword from an EXPLAIN body, returning
    the variant token (uppercase, empty for plain EXPLAIN) and the underlying
    statement text.

    The body literal of an EXPLAIN Command carries the text *after* the EXPLAIN
    keyword itself — e.g. `EXPLAIN PIPELINE SELECT 1` yields body
    `PIPELINE SELECT 1`. Plain `EXPLAIN SELECT 1` yields body `SELECT 1` with
    no variant to strip. The variant token is returned so callers (hdxsql's
    render-substitute path) can re-prepend it to the modified inner SQL.
    """
    stripped = body.lstrip()
    upper = stripped.upper()
    for kw in _EXPLAIN_VARIANT_KEYWORDS:
        if upper.startswith(kw + " ") or upper == kw:
            return (kw, stripped[len(kw) :].lstrip())
    return ("", stripped)


def _validate_explain_body(stmt: exp.Command, depth: int) -> None:
    """Re-parse the body literal of an EXPLAIN Command and recursively validate it.

    sqlglot parses `EXPLAIN <stmt>` as an exp.Command whose body is a single
    raw string literal — the inner statement is NOT structurally parsed, so
    the denylist tree walk never sees its function nodes. Without this
    re-parse, `EXPLAIN SELECT url('...')` would slip past validation.
    """
    if depth > _MAX_EXPLAIN_NESTING:
        raise SqlSafetyError(
            f"EXPLAIN statements nested more than {_MAX_EXPLAIN_NESTING} levels deep are not permitted."
        )

    body_node = stmt.args.get("expression")
    if body_node is None:
        # Bare `EXPLAIN` with no body — nothing to re-parse, treat as accepted
        # (the top-level read-only check has already passed).
        return

    if isinstance(body_node, exp.Literal) and body_node.is_string:
        body_text = body_node.this
    else:
        # Unexpected shape (future sqlglot upgrade may parse EXPLAIN structurally);
        # treat as a validation failure with a user-meaningful message.
        raise SqlSafetyError(
            "Unable to validate EXPLAIN body: unexpected internal AST shape. "
            "Please simplify the query or report this as a bug."
        )

    _, inner_sql = strip_explain_variant_prefix(body_text)

    try:
        parsed_inner = sqlglot.parse(inner_sql, dialect="clickhouse")
    except SqlglotError as e:
        raise SqlSafetyError(f"EXPLAIN body could not be parsed for safety validation: {e}")

    if len(parsed_inner) != 1 or parsed_inner[0] is None:
        raise SqlSafetyError("EXPLAIN body must contain exactly one statement.")

    _validate_statement_inner(parsed_inner[0], depth + 1)


def _validate_statement_inner(stmt: exp.Expression, depth: int) -> None:
    """Internal recursive worker. See `validate_statement` for the public contract."""
    if not _is_accepted_top_level(stmt):
        type_name = type(stmt).__name__
        if isinstance(stmt, exp.Command):
            type_name = f"{type_name}({stmt.name})"
        raise SqlSafetyError(
            f"Only read-only statements are permitted (SELECT, UNION/INTERSECT/EXCEPT, "
            f"WITH, or EXPLAIN). Rejected statement type: {type_name}."
        )

    if _has_into_outfile(stmt):
        raise SqlSafetyError(
            "Query contains an INTO OUTFILE clause. Writing query results to the server filesystem is not permitted."
        )

    for node in stmt.walk():
        is_bad, fn_name = _is_denylisted_function(node)
        if is_bad:
            raise _reject_denylisted_function(node, fn_name)

    # The vendored sqlglot vintage represents EXPLAIN as a Command with the body
    # carried as a single text literal — the inner statement is NOT structurally
    # parsed, so the tree walk above never sees its function nodes. Re-parse the
    # body and recursively validate it to close the denylist bypass.
    if isinstance(stmt, exp.Command) and (stmt.name or "").upper().startswith("EXPLAIN"):
        _validate_explain_body(stmt, depth)


def validate_statement(stmt: exp.Expression) -> None:
    """Validate a complete user-supplied statement for hdxsql.

    Rules:

    1. The **top-level** node type must be one of Select / Union / Intersect / Except /
       With, or an exp.Command whose name starts with "EXPLAIN" (covering EXPLAIN,
       EXPLAIN AST, EXPLAIN SYNTAX, EXPLAIN PIPELINE, EXPLAIN PLAN, EXPLAIN ESTIMATE).
       Anything else is rejected with an error naming the rejected type — this catches
       INSERT, ALTER, DROP, TRUNCATE, RENAME, OPTIMIZE, SYSTEM, KILL, GRANT, ATTACH,
       DETACH, etc. The check is on the top-level node only, so `INSERT INTO t SELECT 1`
       is rejected even though a Select node lives inside.
    2. INTO OUTFILE on any Select in the tree is rejected (defensive — the vendored
       sqlglot raises a parse error before we get here, but a future upgrade may parse it).
    3. The entire AST is walked for denylisted function names (exp.Anonymous by
       name.lower(), exp.Func subclasses by sql_name().lower()).
    4. Unlike validate_where, this validator does NOT reject Subquery/Select/Table
       nodes inside the body — those are legitimate in a self-contained user query.

    The caller is responsible for asserting `len(sqlglot.parse(...)) == 1` before
    invoking this function; multi-statement input is rejected at the caller boundary.

    Raises:
        SqlSafetyError: on any rejection.
    """
    _validate_statement_inner(stmt, depth=0)

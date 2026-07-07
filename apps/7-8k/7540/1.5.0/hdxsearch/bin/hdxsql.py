#!/usr/bin/env python3

import sys
import os
import json
import signal
import threading
import time
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

from hdxclient import HdxClient, QueryParams
from errors import HdxCommandFatalError
from cluster_config import ClusterConfig
from app_version import build_admin_comment
from utils import format_bytes

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

from sql_safety import (
    validate_statement,
    strip_explain_variant_prefix,
)


# Hydrolix currently fails per-query `readonly=1`; emit 0 — the SETTINGS key
# is still reserved so users cannot set it themselves.
# set to 1 when HDX-11493 is done
# another version check would be required for setting this to 1
_READONLY_SETTING_VALUE: int = 0

# Minimum cluster version required for `params=`. The user-visible error
# message names "6.0" verbatim.
_MIN_PARAMS_VERSION: Tuple[int, int, int] = (6, 0, 0)

# Streaming wire format; must match HdxClient.stream_query's decoder.
_STREAMING_FORMAT: str = "JSONCompactEachRowWithNamesAndTypes"

# Reserved SETTINGS keys: user-supplied entries with these keys (case-
# insensitive) are dropped before connector entries are appended.
# `hdx_query_comment` is intentionally NOT here — see `_merge_settings` for
# its concat behavior with the `comment=` option.
_RESERVED_SETTING_KEYS: frozenset = frozenset(
    {
        "hdx_query_admin_comment",
        "readonly",
        "hdx_query_max_memory_usage",
        "hdx_query_max_attempts",
        "hdx_query_max_execution_time",
        "hdx_query_max_result_rows",
        "max_block_size",
    }
)

# Cancellation poll loop: number of consecutive transient errors tolerated
# before disabling the monitor. At 5s per iteration this is ~25s of transient
# failures before we give up — enough to ride out a splunkd reconnect without
# orphaning a long-running query on the cluster.
_CANCEL_POLL_MAX_CONSECUTIVE_ERRORS: int = 5


class HdxSqlFatalError(HdxCommandFatalError):
    """A user-visible fatal error from `hdxsql`.

    Mirrors `HdxSearchFatalError`; subclassing `HdxCommandFatalError` lets the
    top-level `except` in `generate()` dispatch via `error_exit(err.escaped())`
    uniformly with `hdxsearch`.
    """

    pass


@Configuration(generates_timeorder=False)
class HdxSql(GeneratingCommand):
    """
    hdxsql passes a user-supplied SQL statement through to a configured
    Hydrolix cluster and streams the result rows back to Splunk.

    Unlike `hdxsearch`, which composes SQL from option slots, hdxsql is a
    near-pass-through: the connector parses, validates (read-only + function
    denylist + INTO OUTFILE rejection — see sql_safety.py), merges a
    connector-controlled SETTINGS bundle, optionally clamps LIMIT for
    `maxrows=`, and sends the rendered SQL.

    Splunk-recognized fields (`_time`, `host`, `_raw`, ...) are populated
    only when the user aliases a column to that name in the SELECT.

    Example:

        | hdxsql query="SELECT toUnixTimestamp(timestamp) AS _time, app,
                          count() AS n
                        FROM hydro.logs
                        WHERE timestamp BETWEEN
                              fromUnixTimestamp({earliest:Int64})
                          AND fromUnixTimestamp({latest:Int64})
                        GROUP BY timestamp, app"
                  params="{\\"earliest\\":1700000000,\\"latest\\":1700003600}"
                  cluster="prod"
                  maxrows=1000
    """

    query: str = Option(
        require=True,
        doc="A complete ClickHouse SELECT-shaped statement (SELECT, "
        "UNION/INTERSECT/EXCEPT, WITH, or EXPLAIN of any of the above).",
    )
    cluster: str = Option(
        require=False,
        validate=validators.Fieldname(),
        doc="The name of the Hydrolix cluster to query. Defaults to the configured default cluster.",
    )
    params: str = Option(
        require=False,
        doc="JSON-encoded mapping of parameter names to values, bound to "
        "ClickHouse parameter placeholders (`{name:Type}`) in `query=`. "
        "Requires Hydrolix 6.0 or higher.",
    )
    maxrows: int = Option(
        require=False,
        validate=validators.Integer(minimum=0),
        doc="Overall row cap. Bound to `hdx_query_max_result_rows` AND to an "
        "AST-level LIMIT clamp/injection. Value 0 means 'no cap'.",
    )
    timeout: int = Option(
        require=False,
        validate=validators.Integer(minimum=0),
        doc="Query execution time cap in seconds. Bound to "
        "`hdx_query_max_execution_time`. Value 0 means 'no connector-applied "
        "timeout'.",
    )
    fetchsize: int = Option(
        require=False,
        validate=validators.Integer(minimum=0),
        doc="Bound to ClickHouse's `max_block_size` SETTING — server emit "
        "chunk size, affects memory and time-to-first-row. Value 0 means "
        "'do not set'.",
    )
    comment: str = Option(
        require=False,
        doc="Free-form human-readable comment forwarded as `hdx_query_comment` "
        "on the Hydrolix query, useful for attribution in query telemetry. "
        "Does NOT replace `hdx_query_admin_comment`.",
    )

    def generate(self) -> Generator[Dict[str, Any], None, None]:
        try:
            yield from self._run_query()
        except HdxCommandFatalError as err:
            self.error_exit(err.escaped())
            raise

    def _cluster_config(self) -> ClusterConfig:
        return ClusterConfig.from_service(self.service, self.cluster)

    def _parse_params(self) -> Optional[Dict[str, Any]]:
        """Parse `self.params` JSON; raise on malformed or non-object root.

        Returns the parsed dict, or `None` when `self.params` was not supplied.
        Validation happens before any HTTP call — including before the version
        probe — so a malformed `params=` never reaches the network.
        """
        if not self.params:
            return None
        try:
            parsed = json.loads(self.params)
        except json.JSONDecodeError as e:
            raise HdxSqlFatalError(f"`params=` must be valid JSON: {e}")
        if not isinstance(parsed, dict):
            raise HdxSqlFatalError(
                f"`params=` must be a JSON object mapping name to value; got {type(parsed).__name__}."
            )
        return parsed

    def _check_params_version(self, hdx_cli: HdxClient) -> None:
        """Probe the cluster's server version; raise if below `_MIN_PARAMS_VERSION`.

        Called only when `self.params` was supplied — the no-params code path
        never reads `server_version`, per the spec ("No `params=` means no
        version probe").
        """
        sv = hdx_cli.server_version
        if sv is None or sv < _MIN_PARAMS_VERSION:
            version_str = f"{sv[0]}.{sv[1]}.{sv[2]}" if sv is not None else "unknown"
            raise HdxSqlFatalError(
                f"Hydrolix versions 6.0 and greater support query "
                f"parameterization. Configured cluster is at version "
                f"{version_str}."
            )

    def _run_query(self) -> Generator[Dict[str, Any], None, None]:
        cluster_config = self._cluster_config()
        hdx_cli = cluster_config.make_client(self.logger)

        # Always emit the bytes-received warning, even on early validation failure.
        try:
            try:
                parsed_statements = sqlglot.parse(self.query, dialect="clickhouse")
            except SqlglotError as e:
                # Some constructs (INTO OUTFILE, KILL QUERY, DETACH) raise at parse
                # time. Surface a user-meaningful message rather than a bare traceback.
                raise HdxSqlFatalError(f"Failed to parse `query=`: {e}")

            if len(parsed_statements) != 1 or parsed_statements[0] is None:
                raise HdxSqlFatalError(
                    f"`query=` must contain exactly one SQL statement; got {len(parsed_statements)}."
                )
            stmt = parsed_statements[0]

            # Read-only check + denylist walk + INTO OUTFILE rejection.
            validate_statement(stmt)

            # Validate `params=` JSON before the version probe so malformed JSON
            # is rejected without any HTTP call.
            params_dict = self._parse_params()
            if params_dict is not None:
                self._check_params_version(hdx_cli)

            # Pick the AST node that will carry the merged SETTINGS clause (and
            # optional LIMIT clamp). For EXPLAIN, `finalize` substitutes the
            # rendered inner SQL back into the Command's body literal.
            target_node, finalize = self._select_settings_node(stmt)

            # A set-op with an outer LIMIT or ORDER BY forces sqlglot's
            # ClickHouse generator to wrap the whole thing in a subquery,
            # which displaces SETTINGS and FORMAT inside the wrapper where
            # ClickHouse rejects them. Reject and tell the user to wrap
            # themselves.
            if isinstance(target_node, (exp.Union, exp.Intersect, exp.Except)) and (
                target_node.args.get("limit") is not None or target_node.args.get("order") is not None
            ):
                raise HdxSqlFatalError(
                    "Top-level UNION/INTERSECT/EXCEPT with an outer LIMIT or "
                    "ORDER BY is not supported by hdxsql. Wrap the set-op in "
                    "a SELECT: SELECT * FROM ((<a>) UNION ALL (<b>)) AS u "
                    "ORDER BY … LIMIT N."
                )

            connector_settings = self._build_connector_settings()
            self._merge_settings(target_node, connector_settings)

            if self.maxrows is not None and self.maxrows > 0:
                self._inject_limit(target_node, self.maxrows)

            # Attach the streaming FORMAT clause. For plain SELECT, UNION, and
            # WITH … SELECT the `target_node` is the outer renderable and
            # `set("format", ...)` produces a single trailing FORMAT in the
            # render output (overriding any user-supplied FORMAT on the same
            # node — matching hdxsearch's behavior, where the user's response
            # serialization is intentionally replaced by the connector's).
            #
            # For EXPLAIN, `target_node` is the *inner* re-parsed body that we
            # substitute back into the outer Command via `finalize()`. FORMAT
            # belongs on the outer Command (ClickHouse parses `EXPLAIN <stmt>
            # FORMAT …`), and sqlglot's `exp.Command` does not honor
            # `set("format", ...)` in this vintage — so we string-append after
            # the outer render.
            is_explain_outer = isinstance(stmt, exp.Command) and (stmt.name or "").upper().startswith("EXPLAIN")
            if is_explain_outer:
                # FORMAT is appended to the outer Command after render. If the
                # user wrote `EXPLAIN … SELECT … FORMAT JSON`, the re-parsed
                # inner body carries that FORMAT and would render it inside
                # the EXPLAIN body — producing a double-FORMAT against the
                # connector clause we append below.
                target_node.set("format", None)
            else:
                target_node.set("format", _STREAMING_FORMAT)

            finalize()
            query_str = stmt.sql(dialect="clickhouse")
            if is_explain_outer:
                query_str = f"{query_str} FORMAT {_STREAMING_FORMAT}"

            sid = getattr(self.metadata.searchinfo, "sid", None)
            was_cancelled = threading.Event()

            def _cancel_hdx_query() -> None:
                """Cancel the HDX query: close connection and kill on server."""
                if was_cancelled.is_set():
                    return
                was_cancelled.set()
                # Each step is independent — a failure to close the local
                # response must not skip the server-side KILL, since the
                # cluster keeps billing the query until KILL lands.
                try:
                    hdx_cli.cancel_streaming()
                except Exception as e:
                    self.logger.warning("cancel_streaming failed: %s", e, exc_info=True)
                try:
                    hdx_cli.kill_query(sid)
                except Exception as e:
                    self.logger.warning("kill_query failed: %s", e, exc_info=True)

            def _sigterm_handler(signum: int, frame: Any) -> None:
                """Handle SIGTERM from Splunk when the job is killed during streaming."""
                self.logger.info("Received SIGTERM, cancelling HDX query")
                _cancel_hdx_query()

            signal.signal(signal.SIGTERM, _sigterm_handler)

            def _poll_for_cancellation() -> None:
                """Poll Splunk job status; cancel HDX query if job is stopped/deleted."""
                # Tolerate transient poll failures (network blip, splunkd
                # reconnect) — a single exception must not silently disable
                # cancellation for the rest of the query. Only give up after
                # repeated consecutive failures, at which point log at error
                # level so the failure is visible.
                consecutive_errors = 0
                while True:
                    time.sleep(5)
                    try:
                        job = self.service.job(sid)
                        if getattr(job, "isFinalized", "0") == "1" or getattr(job, "dispatchState", "") == "KILLED":
                            self.logger.info("Job %s was stopped/killed, cancelling HDX query", sid)
                            _cancel_hdx_query()
                            return
                        consecutive_errors = 0
                    except Exception as poll_err:
                        # `.status` is the splunklib convention; normalize to
                        # str because some SDK versions surface it as a string
                        # (wrapping urllib's HTTPError) while others use int.
                        if str(getattr(poll_err, "status", "")) == "404":
                            self.logger.info("Job %s was deleted, cancelling HDX query", sid)
                            _cancel_hdx_query()
                            return
                        consecutive_errors += 1
                        if consecutive_errors >= _CANCEL_POLL_MAX_CONSECUTIVE_ERRORS:
                            self.logger.error(
                                "Job status poll failed %d consecutive times, disabling cancellation monitor: %s",
                                consecutive_errors,
                                poll_err,
                                exc_info=True,
                            )
                            return
                        self.logger.warning(
                            "Job status poll error (attempt %d/%d, will retry): %s",
                            consecutive_errors,
                            _CANCEL_POLL_MAX_CONSECUTIVE_ERRORS,
                            poll_err,
                        )

            threading.Thread(target=_poll_for_cancellation, daemon=True).start()

            try:
                qp: QueryParams = dict(params_dict) if params_dict is not None else {}
                # `stream_query` (not `select_streaming`) — we've already validated
                # and attached FORMAT; the sibling round-trips through sqlglot,
                # which fails for some shapes hdxsql renders.
                column_metadata, row_iterator = hdx_cli.stream_query(query_str, params=qp)
                column_names: List[str] = [col["name"] for col in column_metadata]
                if was_cancelled.is_set():
                    self.logger.info(
                        "Job %s was cancelled before row iteration started, closing HDX connection",
                        sid,
                    )
                    hdx_cli.cancel_streaming()
                    return
                for row_values in row_iterator:
                    yield {name: value for name, value in zip(column_names, row_values)}
            except Exception as err:
                if not was_cancelled.is_set():
                    raise HdxSqlFatalError(f"Error executing query: {err}")
                # Cancelled: log the suppressed exception for post-mortem
                # — it may be the cancel-induced connection close, but may
                # also be a genuine server error that raced with the cancel.
                self.logger.warning(
                    "Suppressed exception after cancellation: %s",
                    err,
                    exc_info=True,
                )
        finally:
            self.write_warning(f"Hydrolix bytes received: {format_bytes(hdx_cli.bytes_received)}")

    def _select_settings_node(self, stmt: exp.Expression) -> Tuple[exp.Expression, Callable[[], None]]:
        """Pick the AST node that will carry the connector SETTINGS (and
        optional LIMIT clamp), and return a finalize callback the caller
        invokes after mutation but before rendering.

        For most shapes the target IS the top-level statement and finalize
        is a no-op. EXPLAIN is special: sqlglot carries its body as a raw
        text literal, so we strip the variant keyword, re-parse the inner
        statement, and the finalize callback substitutes the rendered inner
        SQL back into the outer Command's body literal.
        """
        # EXPLAIN: re-parse the body literal and substitute back on finalize.
        if isinstance(stmt, exp.Command) and (stmt.name or "").upper().startswith("EXPLAIN"):
            body_node = stmt.args.get("expression")
            if not isinstance(body_node, exp.Literal) or not body_node.is_string:
                raise HdxSqlFatalError("Unable to process EXPLAIN body: unexpected internal AST shape.")
            variant, inner_sql = strip_explain_variant_prefix(body_node.this)
            try:
                parsed_inner = sqlglot.parse(inner_sql, dialect="clickhouse")
            except SqlglotError as e:
                raise HdxSqlFatalError(f"Failed to parse EXPLAIN body for SETTINGS merge: {e}")
            if len(parsed_inner) != 1 or parsed_inner[0] is None:
                raise HdxSqlFatalError("EXPLAIN body must contain exactly one statement.")
            inner = parsed_inner[0]

            # Recurse to handle e.g. `EXPLAIN WITH cte AS (...) SELECT ...`
            # — the inner node may itself need target selection (it's a
            # Select with `with_` arg in this sqlglot vintage, so the
            # recursion bottoms out immediately — but be defensive).
            inner_target, inner_finalize = self._select_settings_node(inner)

            def finalize() -> None:
                inner_finalize()
                rendered_inner = inner.sql(dialect="clickhouse")
                new_body = f"{variant} {rendered_inner}".strip() if variant else rendered_inner
                stmt.args["expression"] = exp.Literal.string(new_body)

            return (inner_target, finalize)

        # In this sqlglot vintage `WITH … SELECT` parses as a Select with
        # the WITH bound via the Select's `with_` arg — so an `exp.With`
        # top-level node would only appear in some other shape. Handle both
        # defensively: descend if exp.With, otherwise the Select itself
        # carries the WITH and is the right target.
        if isinstance(stmt, exp.With):
            return (stmt.this, _noop_finalize)

        # Select (including WITH … SELECT), Union/Intersect/Except — the
        # outer node is the SETTINGS target. ClickHouse's parser would
        # reject a SETTINGS clause attached anywhere else, and the spec is
        # explicit about the outer-set-op rule.
        return (stmt, _noop_finalize)

    def _merge_settings(
        self,
        node: exp.Expression,
        connector_settings: Dict[str, exp.Expression],
    ) -> None:
        """Drop reserved-key entries from the node's existing SETTINGS and
        append the connector's entries.

        sqlglot stores SETTINGS as a list of `exp.EQ` (or equivalents)
        under `node.args["settings"]`. Each entry's `.this` is the LHS —
        an `exp.Column` in practice, whose `.name` is the bare key string.
        We match the reserved-key set case-insensitively.

        Same logic for "no existing SETTINGS" and "user has SETTINGS
        already" — sqlglot returns `None` when absent, treated as empty.
        Non-reserved user keys pass through unchanged.
        """
        existing: List[exp.Expression] = list(node.args.get("settings") or [])

        # hdx_query_comment is the one user-attribution key that isn't a
        # safety-critical reserved key. When both an inline
        # `SETTINGS hdx_query_comment='X'` and a `comment=Y` option are
        # supplied, concatenate the two strings into a single value
        # ("inline; option") so neither half of user intent is silently
        # dropped. When only the inline is supplied (no option), pass it
        # through unchanged. When only the option is supplied, the connector
        # entry stands alone — same as today.
        user_inline_comment = _extract_inline_string(existing, "hdx_query_comment")
        if user_inline_comment is not None and "hdx_query_comment" in connector_settings:
            option_node = connector_settings["hdx_query_comment"].expression
            if isinstance(option_node, exp.Literal) and option_node.is_string:
                connector_settings["hdx_query_comment"] = _eq_node(
                    "hdx_query_comment",
                    exp.Literal.string(f"{user_inline_comment}; {option_node.this}"),
                )

        kept: List[exp.Expression] = []
        for entry in existing:
            # Defensive: entries we don't recognize are kept as-is rather
            # than dropped — this matches "Non-reserved user keys pass
            # through unchanged" in the spec and avoids surprising users
            # whose SETTINGS clause contains expressions we don't model.
            lhs = entry.this if hasattr(entry, "this") else None
            key = getattr(lhs, "name", "") if lhs is not None else ""
            key_lower = key.lower() if key else ""
            if key_lower in _RESERVED_SETTING_KEYS:
                continue
            # hdx_query_comment is NOT in _RESERVED_SETTING_KEYS. Drop the
            # inline entry only when the connector is also emitting one (we
            # absorbed the inline value into the connector entry above and
            # don't want two same-name SETTINGS in the rendered SQL).
            if key_lower == "hdx_query_comment" and "hdx_query_comment" in connector_settings:
                continue
            kept.append(entry)
        # Connector entries are appended in insertion order. dict insertion
        # order is preserved in Python 3.7+, which gives us a stable
        # always-emitted-first / option-derived-second ordering.
        merged = kept + list(connector_settings.values())
        node.set("settings", merged)

    def _build_connector_settings(self) -> Dict[str, exp.Expression]:
        """Build the per-invocation connector-controlled SETTINGS dict.

        Always-emit keys are unconditional; option-derived keys are emitted
        only when the option was supplied AND its value is non-zero
        (numerics) or non-empty (strings) — per the spec's "Value 0 means
        'no cap': the SETTING is omitted" semantics.
        """
        settings: Dict[str, exp.Expression] = {}

        # Always-emit keys.
        settings["hdx_query_admin_comment"] = _eq_node(
            "hdx_query_admin_comment",
            exp.Literal.string(build_admin_comment(self.metadata.searchinfo, self.search_results_info)),
        )
        settings["readonly"] = _eq_node("readonly", exp.Literal.number(_READONLY_SETTING_VALUE))
        # Emitted as raw bytes (2 * 1024**3 = 2147483648). DO NOT change to a
        # unit-suffixed string like `'2 GiB'`: ClickHouse's settings parser
        # treats the space as the end of the number, sees an unknown unit, and
        # silently falls back to interpreting the leading `2` as bytes — i.e.
        # a 2-BYTE memory cap that fails every real query with "Query memory
        # limit exceeded ... maximum: 2.00 B". The unitless integer is
        # unambiguous and matches what Hydrolix surfaces in query telemetry.
        _HDX_QUERY_MAX_MEMORY_USAGE_BYTES = 2 * 1024**3
        settings["hdx_query_max_memory_usage"] = _eq_node(
            "hdx_query_max_memory_usage",
            exp.Literal.number(_HDX_QUERY_MAX_MEMORY_USAGE_BYTES),
        )
        settings["hdx_query_max_attempts"] = _eq_node("hdx_query_max_attempts", exp.Literal.number(1))

        # Option-derived keys. `Option(require=False)` leaves unsupplied
        # options as `None`; numeric options use `> 0` (treating 0 as
        # "no cap" per spec); string options use truthiness.
        if self.timeout is not None and self.timeout > 0:
            settings["hdx_query_max_execution_time"] = _eq_node(
                "hdx_query_max_execution_time", exp.Literal.number(self.timeout)
            )
        if self.maxrows is not None and self.maxrows > 0:
            settings["hdx_query_max_result_rows"] = _eq_node(
                "hdx_query_max_result_rows", exp.Literal.number(self.maxrows)
            )
        if self.fetchsize is not None and self.fetchsize > 0:
            settings["max_block_size"] = _eq_node("max_block_size", exp.Literal.number(self.fetchsize))
        if self.comment:
            settings["hdx_query_comment"] = _eq_node("hdx_query_comment", exp.Literal.string(self.comment))

        return settings

    def _inject_limit(self, node: exp.Expression, n: int) -> None:
        """Clamp or attach a top-level LIMIT to `node`.

        - No existing LIMIT: attach `LIMIT n`.
        - Existing integer-literal LIMIT M: replace with min(M, n).
        - Existing non-literal LIMIT: leave unchanged and warn. The
          `hdx_query_max_result_rows` SETTING is still applied as the
          server-side safety belt.
        """
        existing = node.args.get("limit")
        if existing is None:
            # Attaching a structural LIMIT to a set-op forces sqlglot to wrap
            # the whole thing in a subquery, which displaces SETTINGS and
            # FORMAT. Skip the AST attach and rely on
            # `hdx_query_max_result_rows` as the server-side cap.
            if isinstance(node, (exp.Union, exp.Intersect, exp.Except)):
                self.write_warning(
                    "maxrows-based LIMIT injection skipped: the query's "
                    "top-level node is a UNION/INTERSECT/EXCEPT set-operation, "
                    "and attaching a structural LIMIT to it would force a "
                    "subquery wrap that displaces SETTINGS and FORMAT. The "
                    "hdx_query_max_result_rows SETTING is still applied as "
                    "the server-side row cap."
                )
                return
            node.set("limit", exp.Limit(expression=exp.Literal.number(n)))
            return

        # exp.Limit.expression is the count node.
        count = existing.expression if isinstance(existing, exp.Limit) else None
        if isinstance(count, exp.Literal) and not count.is_string:
            try:
                m = int(count.name)
            except (ValueError, TypeError):
                # Defensive: a Literal that's not integer-shaped — bail
                # like the non-literal branch.
                self.write_warning(
                    "maxrows-based LIMIT clamping skipped: existing LIMIT is "
                    "not an integer literal. The hdx_query_max_result_rows "
                    "SETTING is still applied."
                )
                return
            clamped = min(m, n)
            existing.set("expression", exp.Literal.number(clamped))
            return

        # Non-literal LIMIT expression (subquery, column ref, ...): leave
        # alone and warn. SETTINGS-level cap still applies via the
        # connector_settings dict already merged above.
        self.write_warning(
            "maxrows-based LIMIT clamping skipped: existing LIMIT is a "
            "non-literal expression. The hdx_query_max_result_rows SETTING "
            "is still applied."
        )


def _eq_node(key: str, value: exp.Expression) -> exp.Expression:
    """Build a SETTINGS entry node of the shape sqlglot produces for parsed
    SETTINGS — `exp.EQ(this=Column(<key>), expression=<value>)`.

    sqlglot represents `readonly=1` as EQ with the LHS as a `Column` (not an
    `Identifier`). We use `exp.to_identifier` to construct the LHS and
    sqlglot wraps it appropriately at render time; either shape round-trips
    to the same SQL.
    """
    return exp.EQ(this=exp.to_identifier(key), expression=value)


def _noop_finalize() -> None:
    """Default finalize callback for non-EXPLAIN target nodes."""
    return None


def _extract_inline_string(settings: List[exp.Expression], key: str) -> Optional[str]:
    """Return the string value of a SETTINGS entry whose key (case-insensitive)
    matches `key`, or None if no such entry exists or the entry's RHS is not a
    string literal. Used by `_merge_settings` to detect the user's inline
    `hdx_query_comment` for the concat-with-option contract.
    """
    target = key.lower()
    for entry in settings:
        lhs = entry.this if hasattr(entry, "this") else None
        name = getattr(lhs, "name", "") if lhs is not None else ""
        if name and name.lower() == target:
            rhs = entry.expression if hasattr(entry, "expression") else None
            if isinstance(rhs, exp.Literal) and rhs.is_string:
                return rhs.this
            return None
    return None


dispatch(HdxSql, sys.argv, sys.stdin, sys.stdout, __name__)

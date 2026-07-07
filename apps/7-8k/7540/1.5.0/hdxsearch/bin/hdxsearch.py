#!/usr/bin/env python3

import sys
import os
import signal
import threading
import time
from typing import Generator, Any, Iterable, List, Dict, Set, Union, Tuple
from hdxclient import HdxClient, Column, AliasColumn, SummaryColumn, QueryParams
from errors import HdxClientError, HdxCommandFatalError
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

# The SQL-safety policy (denylist + WHERE validator) lives in a sibling module so
# hdxsql shares the exact same rules. See hdxsearch/bin/sql_safety.py.
from sql_safety import validate_where


# type="events" is intentionally omitted. The default type="streaming" places this command in
# Splunk's streaming pipeline, allowing results to flow to the user incrementally as rows are
# yielded. Using type="events" would place the command in the events pipeline, causing Splunk
# to buffer the entire result set before displaying anything.
@Configuration(generates_timeorder=True)
class HdxSearch(GeneratingCommand):
    """
    hdxsearch command queries the hdx cluster and generates events for Splunk to consume.

    Example:

        | hdxsearch table="hydro.logs"
                    fields="app,rows_read,bytes_read,source_type"
                    raw="message" time="timestamp"
                    where="app='query-head'"
                    cluster="cluster_name"
    """

    limit: int = Option(
        require=False,
        validate=validators.Integer(0),
        doc="Maximum number of rows to retrieve from the table or `0` to retrieve all rows. Defaults to the limit value configured for the cluster being queried.",
    )
    where: str = Option(
        require=False,
        doc="A SQL expression to filter the results of the query. Predicates on summary alias columns "
        "are rewritten to a HAVING clause prior to execution. Defaults to no filter.",
    )
    raw: str = Option(
        require=False,
        validate=validators.Fieldname(),
        doc='The name of a field whose raw value should be sent to the "Event" column of the SPL query output. Either `fields` or `raw` must be specified.',
    )
    time: str = Option(
        require=False,
        validate=validators.Fieldname(),
        doc="The name of a field in `table` to treat as the event timestamp. Defaults to the primary key of the table.",
    )
    fields: Iterable[str] = Option(
        require=False,
        validate=validators.List(),
        doc="A comma-delimited list of fields to retrieve from the table, or `*`, which returns all the fields. Either `fields` or `raw` must be specified.",
    )  # TODO forbid _raw and _time special-purpose fields
    table: str = Option(
        require=True, validate=validators.Fieldname(), doc="The Hydrolix table to query in the form `project.table`."
    )
    cluster: str = Option(
        require=False,
        validate=validators.Fieldname(),
        doc="The name of the Hydrolix cluster to query. Defaults to the configured default cluster.",
    )
    nocache: bool = Option(
        require=False,
        default=False,
        validate=validators.Boolean(),
        doc="If set to `true`, query results will be excluded from caching. Defaults to false to take advantage of caching by using Hydrolix query caching.",
    )
    comment: str = Option(
        require=False,
        doc="An optional human-readable comment forwarded as `hdx_query_comment` on the Hydrolix query, useful for attribution in query telemetry.",
    )

    def generate(self) -> Generator[Any, None, None]:
        if not self.fields and not self.raw:
            self.write_error("Invalid query. At least one of 'fields' or 'raw' must be specified")
            exit(1)

        try:
            for event in self._run_query():
                yield event
        except HdxCommandFatalError as err:
            self.error_exit(err.escaped())
            raise

    def _cluster_config(self) -> ClusterConfig:
        return ClusterConfig.from_service(self.service, self.cluster)

    @staticmethod
    def _fetch_columns(hdx_cli: HdxClient, project: str, table: str) -> List[Union[Column, AliasColumn, SummaryColumn]]:
        """
        Fetch column metadata
        """

        try:
            columns = hdx_cli.describe(project, table)
        except Exception as err:
            raise HdxSearchFatalError(f"Failed to retrieve columns for table '{project}.{table}': {err}")

        if not columns:
            raise HdxSearchFatalError(f"Table '{project}.{table}' does not exist or has no columns")
        return columns

    def _validate_fields(self, columns: List[Union[Column, AliasColumn, SummaryColumn]]) -> None:
        column_names = {col.name for col in columns}
        any_invalid_fields = False
        if self.fields:
            for field in self.fields:
                if field != "*":
                    # "*" is always a valid field specifier, for better or worse
                    try:
                        field_ident = HdxClient.parse_identifier(field)
                    except SqlglotError:
                        any_invalid_fields = True
                        self.write_warning(f"Invalid field '{field}' for table '{self.table}'")
                        continue
                    if field_ident not in column_names:
                        any_invalid_fields = True
                        self.write_warning(f"Unknown field '{field}' for table '{self.table}'")
        if self.raw:
            try:
                raw_ident = HdxClient.parse_identifier(self.raw)
                if raw_ident not in column_names:
                    any_invalid_fields = True
                    self.write_warning(f"Unknown field '{self.raw}' (used as raw) for table '{self.table}'")
            except SqlglotError:
                any_invalid_fields = True
                self.write_warning(f"Invalid field '{self.raw}' (used as raw) for table '{self.table}'")
        if any_invalid_fields:
            raise HdxSearchFatalError("Unknown or invalid fields. See warnings above.")

    def _resolve_time_field(
        self, columns: List[Union[Column, AliasColumn, SummaryColumn]], hdx_client: HdxClient, project: str, table: str
    ) -> exp.Identifier:
        """
        Validate or auto-detect time field given the columns available on the table and an hdx_client with
        which to perform auto-detection if necessary. Returns an Identifier for use in query building.
        """
        column_map = {col.name for col in columns}
        if self.time:
            try:
                parsed = HdxClient.parse_identifier(self.time)
                if parsed not in column_map:
                    self.write_warning(
                        f"Unknown field '{self.time}' (used as time) for table '{self.table}'. Using primary key instead."
                    )
                else:
                    return parsed
            except SqlglotError:
                self.write_warning(
                    f"Invalid field '{self.time}' (used as time) for table '{self.table}'. Using primary key instead."
                )

        try:
            return hdx_client.get_pk_for_table(project, table)
        except HdxClientError as e:
            raise HdxSearchFatalError(
                "Error resolving primary timestamp column. You may set it explicitly with the `time` parameter. "
                + e.message
            )
        except Exception as err:
            raise HdxSearchFatalError(f"Error resolving primary timestamp column: {err}")

    def _run_query(self) -> Generator[Dict[str, Any], None, None]:
        conf = self._cluster_config()

        parsed = exp.to_table(self.table, dialect="clickhouse")
        if not parsed.db:
            raise HdxSearchFatalError("Invalid table format. Expected 'project.table'")
        table = exp.table_(parsed.name, db=parsed.db, quoted=True)

        hdx_cli = conf.make_client(self.logger)
        columns = self._fetch_columns(hdx_cli, table.db, table.name)
        self._validate_fields(columns)
        time_field = self._resolve_time_field(columns, hdx_cli, table.db, table.name)
        limit_value = self.limit if self.limit is not None else conf.default_limit

        settings: List[exp.Expression] = [
            exp.EQ(
                this=exp.to_identifier("hdx_query_admin_comment"),
                expression=exp.Literal.string(build_admin_comment(self.metadata.searchinfo, self.search_results_info)),
            ),
        ]

        if self.comment:
            settings.append(
                exp.EQ(
                    this=exp.to_identifier("hdx_query_comment"),
                    expression=exp.Literal.string(self.comment),
                )
            )

        if not self.nocache:
            settings.append(sqlglot.parse_one("use_query_cache=true", dialect="clickhouse"))

        sv = hdx_cli.server_version
        query_str, params = self._generate_query_str(
            table,
            columns,
            time_field,
            limit_value,
            settings,
            use_params=sv is not None and sv >= (5, 12, 0),
        )

        sid = getattr(self.metadata.searchinfo, "sid", None)
        was_cancelled = threading.Event()

        def _cancel_hdx_query() -> None:
            """Cancel the HDX query: close connection and kill on server."""
            if was_cancelled.is_set():
                return
            was_cancelled.set()
            hdx_cli.cancel_streaming()
            hdx_cli.kill_query(sid)

        def _sigterm_handler(signum: int, frame: Any) -> None:
            """Handle SIGTERM from Splunk when the job is killed during streaming."""
            self.logger.info("Received SIGTERM, cancelling HDX query")
            _cancel_hdx_query()

        signal.signal(signal.SIGTERM, _sigterm_handler)

        def _poll_for_cancellation() -> None:
            """Poll Splunk job status; cancel HDX query if job is stopped/deleted."""
            while True:
                time.sleep(5)
                try:
                    job = self.service.job(sid)
                    if getattr(job, "isFinalized", "0") == "1" or getattr(job, "dispatchState", "") == "KILLED":
                        self.logger.info("Job %s was stopped/killed, cancelling HDX query", sid)
                        _cancel_hdx_query()
                        return
                except Exception as poll_err:
                    if getattr(poll_err, "status", None) == 404:
                        self.logger.info("Job %s was deleted, cancelling HDX query", sid)
                        _cancel_hdx_query()
                    else:
                        self.logger.warning("Job status poll failed, disabling cancellation monitor: %s", poll_err)
                    return

        threading.Thread(target=_poll_for_cancellation, daemon=True).start()

        try:
            # Streaming uses JSONCompactEachRowWithNamesAndTypes format:
            # Line 1: ["col1", "col2", ...] - column names
            # Line 2: ["String", "UInt64", ...] - column types
            # Line 3+: [val1, val2, ...] - data rows (one JSON array per line)
            # See https://clickhouse.com/docs/interfaces/formats#jsoncompacteachrowwithnamesandtypes
            column_metadata, row_iterator = hdx_cli.select_streaming(query_str, params=params)
            column_names: List[str] = [col["name"] for col in column_metadata]
            # Cancellation may have been detected during execution (kill_query was called) but
            # the query completed before the kill took effect. Stop streaming now.
            if was_cancelled.is_set():
                self.logger.info("Job %s was cancelled before row iteration started, closing HDX connection", sid)
                hdx_cli.cancel_streaming()
                return
            # Each row from the iterator is an array of values (no column names included).
            # We name it `row_values` to make this explicit, then zip with column_names to create dicts.
            for row_values in row_iterator:
                yield {name: value for name, value in zip(column_names, row_values)}
        except Exception as err:
            if not was_cancelled.is_set():
                raise HdxSearchFatalError(f"Error executing query: {err}")
            # Job was intentionally cancelled; exit silently
        finally:
            self.write_warning(f"Hydrolix bytes received: {format_bytes(hdx_cli.bytes_received)}")

    def _generate_query_str(
        self,
        table: exp.Table,
        columns: List[Union[Column, AliasColumn, SummaryColumn]],
        time_field: exp.Identifier,
        limit_value: int,
        settings: List[exp.Expression],
        use_params: bool = True,
    ) -> Tuple[str, QueryParams]:
        """
        generates a query for the configured scan, with time_field underlying the _time magic variable,
        and using JSONCompact format

        CALLER INVARIANT: `self.fields` and `self.raw` must refer to extant fields on `table` that can
        be parsed as Identifiers (except for `*`, which may be present in `self.fields`)
        """
        from_dt = int(self.metadata.searchinfo.earliest_time)
        to_dt = int(self.metadata.searchinfo.latest_time)

        # Build time expression: toUnixTimestamp("time_field") AS _time
        # time_field is an Identifier with proper quoting already set
        time_col = exp.column(time_field)
        time_expr = exp.alias_(exp.func("toUnixTimestamp", time_col), "_time")

        summary_column_names = [c.name for c in columns if c.is_aggregate()]
        is_summary_table = len(summary_column_names) != 0

        dimensions: List[exp.Expression] = [time_expr]
        aggregations: List[exp.Expression] = []

        # Add user-requested fields
        if self.fields:
            for field in self.fields:
                if field == "*":
                    if is_summary_table:
                        raise HdxSearchFatalError(
                            f"The table {table} is a summary table, so the fields wildcard may not be used to query it"
                        )
                    else:
                        self.write_warning(
                            "Using SELECT * is not recommended and may lead to performance issues on tables with many columns."
                        )
                        dimensions.append(exp.Star())
                elif (field_parsed := HdxClient.parse_identifier(field)) in summary_column_names:
                    # this is a summary field (aggregation)
                    aggregations.append(exp.column(field_parsed))
                else:
                    # either this is a non-aggregated field on a summary table, or it's not a summary table to begin with
                    dimensions.append(exp.column(field_parsed))

        # Add raw field with alias
        if self.raw:
            raw_field_parsed = HdxClient.parse_identifier(self.raw)
            if raw_field_parsed in summary_column_names:
                aggregations.append(exp.alias_(exp.column(raw_field_parsed), "_raw"))
            else:
                dimensions.append(exp.alias_(exp.column(raw_field_parsed), "_raw"))

        # Build time range condition; use parameterized placeholders on Hydrolix ≥ 5.12,
        # inline literals on older clusters (placeholder syntax causes parse errors pre-5.12)
        time_col = exp.column(time_field)
        if use_params:
            params: QueryParams = {"from_dt": from_dt, "to_dt": to_dt}
            from_ts = exp.func("fromUnixTimestamp", sqlglot.parse_one("{from_dt: Int64}", dialect="clickhouse"))
            to_ts = exp.func("fromUnixTimestamp", sqlglot.parse_one("{to_dt: Int64}", dialect="clickhouse"))
        else:
            params = {}
            from_ts = exp.func("fromUnixTimestamp", exp.Literal.number(from_dt))
            to_ts = exp.func("fromUnixTimestamp", exp.Literal.number(to_dt))
        time_condition = exp.Between(this=time_col, low=from_ts, high=to_ts)

        # Assemble query
        query = sqlglot.select(*dimensions, *aggregations).from_(table).where(time_condition)

        # Add user-provided WHERE clause, splitting aggregate predicates into HAVING.
        if self.where:
            parsed_where = sqlglot.parse_one(self.where, dialect="clickhouse")
            validate_where(parsed_where)

            if is_summary_table:
                # Given the choice between placing a predicate in HAVING vs WHERE, we prefer
                # WHERE when the predicate does not depend on aggregate results. If a predicate
                # references only GROUP BY keys (i.e., is constant within each group), then
                # filtering in WHERE vs HAVING is equivalent, but WHERE is preferable because
                # it can drop rows before aggregation, reducing work.
                original_conjuncts = (
                    list(parsed_where.flatten()) if isinstance(parsed_where, exp.And) else [parsed_where]
                )

                where_conjuncts: List[exp.Expression] = []
                having_conjuncts: List[exp.Expression] = []

                for conjunct in original_conjuncts:
                    # Compare by .name because parse_identifier always quotes,
                    # while WHERE-clause identifiers may be unquoted.
                    col_names = {col.this.name for col in conjunct.find_all(exp.Column)}
                    if not col_names.isdisjoint(s.name for s in summary_column_names):
                        having_conjuncts.append(conjunct)
                    else:
                        where_conjuncts.append(conjunct)

                for pred in where_conjuncts:
                    query = query.where(pred, append=True)
                for pred in having_conjuncts:
                    query = query.having(pred, append=True)
            else:
                query = query.where(parsed_where)

        # Add GROUP BY (if this is a summary query)
        if len(aggregations) != 0:
            flattened_dimension_columns: Set[exp.Column] = {e for d in dimensions for e in d.find_all(exp.Column)}

            # Add implicit dimensions from SummaryColumn default_expr traversal.
            # ClickHouse expands ALIAS columns at query time and raises error code 215 when a dimension
            # referenced inside an aggregate expression is missing from GROUP BY.
            agg_col_map: Dict[str, SummaryColumn] = {c.name.name: c for c in columns if c.is_aggregate()}  # type: ignore[misc]
            implicit_groupby_columns: Set[exp.Column] = {
                exp.column(HdxClient.parse_identifier(implied_groupby_column))
                for agg_col_expr in aggregations
                for col_node in agg_col_expr.find_all(exp.Column)
                if (summary_column := agg_col_map.get(col_node.name))
                if summary_column.implicit_group_by_dims
                for implied_groupby_column in summary_column.implicit_group_by_dims
            }

            query = query.group_by(*flattened_dimension_columns, *implicit_groupby_columns)

        # Add ORDER BY _time DESC
        query = query.order_by(exp.Ordered(this=exp.column("_time"), desc=True))

        # Add LIMIT if positive
        if limit_value > 0:
            query = query.limit(limit_value)

        # Construct SETTINGS
        query.set("settings", settings)

        return query.sql(dialect="clickhouse"), params


class HdxSearchFatalError(HdxCommandFatalError):
    """
    An error that is enough on its own to terminate the query. Will be presented to the user with minimal wrapping
    """

    pass


dispatch(HdxSearch, sys.argv, sys.stdin, sys.stdout, __name__)

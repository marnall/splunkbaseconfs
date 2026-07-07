from abc import abstractmethod
from dataclasses import dataclass, field
import logging
import re
import sys
import os
import ssl
from typing_extensions import Protocol
import urllib.parse
import json
import base64
import textwrap
import time
from datetime import datetime, date
from graphlib import TopologicalSorter
import requests
from typing import Any, List, Dict, Optional, Set, Union, TypedDict, Iterator, Tuple
from proxy_config import ProxyConfig
from errors import HdxClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import sqlglot
from sqlglot import expressions
from sqlglot.errors import SqlglotError


def _configure_system_ca_bundle(logger: logging.Logger) -> None:
    """Point requests at the OS CA bundle when one is available.

    requests reads REQUESTS_CA_BUNDLE dynamically at request time, so setting it
    here is effective even if requests was already imported by another Splunk app.
    The operator can pre-set REQUESTS_CA_BUNDLE in splunk-launch.conf to override this detection.
    """
    if "REQUESTS_CA_BUNDLE" in os.environ:
        logger.info("Using CA bundle from REQUESTS_CA_BUNDLE env var: %s", os.environ["REQUESTS_CA_BUNDLE"])
        return
    candidates = [
        ssl.get_default_verify_paths().cafile,  # returns None when not configured (common on macOS/Windows)
        "/etc/ssl/cert.pem",
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
        "/etc/ssl/ca-bundle.pem",
    ]
    ca_bundle = next((p for p in candidates if p and os.path.exists(p)), None)
    if ca_bundle:
        logger.info("Using OS CA bundle for TLS verification: %s", ca_bundle)
        os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle
    else:
        logger.warning("No OS CA bundle found; requests will fall back to certifi. Set REQUESTS_CA_BUNDLE to override.")


class TableField(Protocol):
    """A field in a HDX table"""

    name: expressions.Identifier
    type: str

    @abstractmethod
    def is_aggregate(self) -> bool: ...


@dataclass(frozen=True)
class Column(TableField):
    """A 'regular' SQL column (no CH/HDX special semantics)"""

    name: expressions.Identifier
    type: str

    def is_aggregate(self) -> bool:
        return False


@dataclass(frozen=True)
class AliasColumn(TableField):
    """A grouper/dimension alias (CH special semantics, supported by HDX)"""

    name: expressions.Identifier
    type: str
    default_expr: str

    def is_aggregate(self) -> bool:
        return False


@dataclass(frozen=True)
class SummaryColumn(TableField):
    """An aggregator alias (HDX special semantics)"""

    name: expressions.Identifier
    type: str
    default_expr: str
    # A minimum sufficient set of GROUP BY columns necessary to query this summary column
    implicit_group_by_dims: Set[str] = field(default_factory=set)

    def is_aggregate(self) -> bool:
        return True


class JsonCompactColumnMeta(TypedDict):
    """Metadata for a single column in JSONCompact response."""

    name: str
    type: str


class JSONCompactResponse(TypedDict):
    """ClickHouse JSONCompact response format."""

    meta: List[JsonCompactColumnMeta]
    data: List[List[Any]]


QueryParams = Dict[str, Union[str, int, float, bool, datetime, date]]


class HdxClient:
    def __init__(
        self,
        endpoint: str,
        auth_type: str,
        username: Optional[str],
        password: Optional[str],
        api_token: Optional[str],
        proxy_config: Optional[ProxyConfig],
        logger: logging.Logger,
    ):
        if auth_type == "bearer":
            auth_header = f"Bearer {api_token}"
        else:
            auth = f"{username}:{password}".encode("utf-8")
            auth_header = f"Basic {base64.b64encode(auth).decode('utf-8')}"
        self.host = urllib.parse.urlparse(endpoint).netloc
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Authorization": auth_header,
        }
        self.path = "/query?enable_http_compression=1"
        self.proxy_config = proxy_config
        self.logger = logger
        try:
            _configure_system_ca_bundle(self.logger)
        except Exception as e:
            self.logger.warning("CA bundle detection failed; REQUESTS_CA_BUNDLE not set: %s", e)
        self._streaming_response: Optional[requests.Response] = None
        self._active_query_id: Optional[str] = None
        self.bytes_received: int = 0
        self._version_fetched: bool = False
        self._server_version: Optional[Tuple[int, int, int]] = None

    def _fetch_server_version(self) -> Optional[Tuple[int, int, int]]:
        try:
            proxies = {"https": self.proxy_config.to_url()} if self.proxy_config else None
            response = requests.get(
                f"https://{self.host}/version",
                headers=self.headers,
                proxies=proxies,
            )
            response.raise_for_status()
            # RC/dev builds may report `x` in the patch slot (e.g. v6.0.x-rc.1-118-g7bbe5ec3); treat as 0.
            match = re.match(r"^v(\d+)\.(\d+)\.(\d+|[xX])", response.text.strip())
            if not match:
                self.logger.warning("Unexpected /version response format: %s", response.text)
                return None
            patch = match.group(3)
            return (int(match.group(1)), int(match.group(2)), 0 if patch.lower() == "x" else int(patch))
        except Exception as e:
            self.logger.warning("Failed to fetch server version: %s", e)
            return None

    @property
    def server_version(self) -> Optional[Tuple[int, int, int]]:
        if not self._version_fetched:
            self._server_version = self._fetch_server_version()
            self._version_fetched = True
        return self._server_version

    @staticmethod
    def _serialize_param(value: Union[str, int, float, bool, datetime, date]) -> Tuple[str, str]:
        if isinstance(value, bool):
            return ("Bool", "true" if value else "false")
        if isinstance(value, int):
            return ("Int64", str(value))
        if isinstance(value, float):
            return ("Float64", str(value))
        if isinstance(value, str):
            return ("String", value)
        if isinstance(value, datetime):
            return ("DateTime", value.replace(tzinfo=None, microsecond=0).isoformat(sep=" "))
        if isinstance(value, date):
            return ("Date", value.isoformat())
        raise TypeError(f"Unsupported parameter type: {type(value)}")

    @staticmethod
    def _build_param_query_string(params: QueryParams) -> str:
        serialized = {f"param_{name}": HdxClient._serialize_param(value)[1] for name, value in params.items()}
        return "&" + urllib.parse.urlencode(serialized)

    @staticmethod
    def parse_identifier(s: str) -> expressions.Identifier:
        """Parse a potentially-quoted identifier string into an Identifier AST node.

        All identifiers are marked as quoted=True for safety, since column names
        may contain special characters that require quoting.

        Dotted names (e.g., kubernetes.container_id) are treated as a single identifier,
        not as table.column — the full string is preserved as the identifier name.
        """
        try:
            parsed = sqlglot.parse_one(s, dialect="clickhouse")
            if isinstance(parsed, expressions.Column) and not parsed.table:
                ident: expressions.Identifier = parsed.this
                return expressions.to_identifier(ident.name, quoted=True)
            if isinstance(parsed, expressions.Identifier):
                return expressions.to_identifier(parsed.name, quoted=True)
        except SqlglotError:
            # parsing may fail when, for example, the column name is a quoted CH expression that involves a keyword
            # in testing, we found `countIf(and(equals(cdn, 'fastly'), not(is_shield)))`.
            pass
        return expressions.to_identifier(s, quoted=True)

    @staticmethod
    def _compute_aggregate_columns(alias_definitions: Dict[str, str]) -> Dict[str, Set[str]]:
        """
        CALLER INVARIANT: All `alias_definitions` must be from the same source of truth (eg, a single DESCRIBE result)

        Args:
            alias_definitions: keys are alias names as SQL strings, values are aliased expressions as SQL strings
                (eg `foo AS bar` has k=bar, v=foo)

        Returns:
            Dict mapping each aggregate column name to the set of non-aggregate column names it directly references
            in its default_expr AST. The value `Set` does NOT include transitive dependencies -- it is the minimum necessary
            set of group by columns to use the aggregation (preferring aliases over raw columns, given the choice)
        """
        # Parse all expressions
        parsed_aliases = {name: sqlglot.parse_one(sql, dialect="clickhouse") for name, sql in alias_definitions.items()}

        alias_names = set(alias_definitions)

        @dataclass(frozen=True)
        class _AliasInfo:
            is_direct_aggregation: (
                bool  # True if this alias's expression directly contains an AggFunc node (at any depth)
            )
            dimension_dependencies: Set[
                str
            ]  # all column names outside AggFunc subtrees (need GROUP BY if this is a summary alias)
            alias_dependencies: Set[str]  # alias names this alias depends upon

        alias_dependency_meta: Dict[str, _AliasInfo] = {}

        for name, expr in parsed_aliases.items():
            # Walk the AST but stop descending into AggFunc subtrees, so we can partition
            # column references to ID groupers
            aggregators: list[expressions.AggFunc] = []  # collected AggFunc subtrees for a second pass
            dimension_dependencies: Set[str] = set()  # all columns outside AggFunc (any column, not just aliases)
            alias_dependencies: Set[str] = set()  # subset of outer_refs that are known aliases

            # Outer pass (down to AggFunc)
            for node in expr.walk(prune=lambda n: isinstance(n, expressions.AggFunc)):
                if isinstance(node, expressions.AggFunc):
                    aggregators.append(node)
                elif isinstance(node, expressions.Column):
                    dimension_dependencies.add(node.name)
                    if node.name in alias_names:
                        alias_dependencies.add(node.name)

            # Inner pass (inside AggFunc subtrees)
            alias_dependencies |= {
                n.name
                for agg in aggregators
                for n in agg.walk()
                if isinstance(n, expressions.Column) and n.name in alias_names
            }

            alias_dependency_meta[name] = _AliasInfo(
                is_direct_aggregation=len(aggregators) > 0,
                dimension_dependencies=dimension_dependencies,
                # alias_dependencies spans both inside and outside AggFunc — we need the full
                # alias-to-alias graph to determine which aliases are transitively aggregate
                alias_dependencies=alias_dependencies,
            )

        # Resolve transitive aggregates: an alias is aggregate (and direct) if it directly contains
        # (anywhere in its AST) an AggFunc or references another alias that is aggregate (i.e.,
        # transitively)
        is_aggregation: Dict[str, bool] = {}
        # Topological ordering ensures all dependencies are handled by the time we get to their dependants
        for name in TopologicalSorter(
            {name: alias_meta.alias_dependencies - {name} for name, alias_meta in alias_dependency_meta.items()}
        ).static_order():
            alias_meta = alias_dependency_meta[name]
            is_transitive_aggregation = any(is_aggregation.get(dep, False) for dep in alias_meta.alias_dependencies)
            is_aggregation[name] = alias_meta.is_direct_aggregation or is_transitive_aggregation

        # For each aggregate alias, return the set of non-aggregate columns it references outside AggFunc boundaries
        return {
            name: {
                ref for ref in alias_dependency_meta[name].dimension_dependencies if not is_aggregation.get(ref, False)
            }
            for name in alias_names
            if is_aggregation[name]
        }

    def describe(self, project: str, table: str) -> List[Union[Column, AliasColumn, SummaryColumn]]:
        """
        Look up table schema and partition into groupers, aliased groupers, and [summary] aggregators
        """
        query = f"DESCRIBE TABLE {project}.{table} FORMAT JSONCompact"
        result: JSONCompactResponse = self._query(query)

        # Un-flattenning the JSONCompact results for DESCRIBE (since we don't necessarily control column order for DESCRIBE rows)
        meta = result.get("meta", [])
        col_indices = {col["name"]: i for i, col in enumerate(meta)}
        name_idx = col_indices["name"]
        type_idx = col_indices["type"]
        default_type_idx = col_indices["default_type"]
        default_expr_idx = col_indices["default_expression"]
        rows = result.get("data", [])

        # first, ID which columns are aliases
        alias_columns: Dict[str, str] = {
            row[name_idx]: row[default_expr_idx] for row in rows if row[default_type_idx] == "ALIAS"
        }
        # then, among the aliases, determine which are aggregates
        aggregate_columns = self._compute_aggregate_columns(alias_columns)

        def classify_column(row: List[Any]) -> Union[Column, AliasColumn, SummaryColumn]:
            name_str, col_type = row[name_idx], row[type_idx]
            name = HdxClient.parse_identifier(name_str)

            if name_str not in alias_columns:
                return Column(name=name, type=col_type)
            elif name_str in aggregate_columns:
                return SummaryColumn(
                    name=name,
                    type=col_type,
                    default_expr=alias_columns[name_str],
                    implicit_group_by_dims=aggregate_columns[name_str],
                )
            else:
                return AliasColumn(name=name, type=col_type, default_expr=alias_columns[name_str])

        return [classify_column(row) for row in rows]

    def show_databases(self) -> List[str]:
        """Return list of database names from the HDX cluster."""
        query = "SHOW DATABASES FORMAT JSONCompact"
        result: JSONCompactResponse = self._query(query)
        return [row[0] for row in result.get("data", [])]

    def show_tables(self, database: str, settings: Optional[List[str]] = None) -> List[str]:
        """Return list of table names in the specified database."""
        query = (
            sqlglot.select("name")
            .from_("system.tables")
            .where(expressions.EQ(this=expressions.column("database"), expression=expressions.Literal.string(database)))
        )
        if settings:
            settings_exprs = [sqlglot.parse_one(setting, dialect="clickhouse") for setting in settings]
            query.set("settings", settings_exprs)
        query.set("format", "JSONCompact")
        result: JSONCompactResponse = self._query(query.sql(dialect="clickhouse"))
        return [row[0] for row in result.get("data", [])]

    def describe_table_raw(self, project: str, table: str, settings: Optional[List[str]] = None) -> JSONCompactResponse:
        """Return raw DESCRIBE TABLE output without column classification."""
        qualified_table = expressions.table_(table, db=project, quoted=True).sql(dialect="clickhouse")
        settings_clause = f" SETTINGS {', '.join(settings)}" if settings else ""
        query = f"DESCRIBE TABLE {qualified_table}{settings_clause} FORMAT JSONCompact"
        return self._query(query)

    @staticmethod
    def _primary_keys_query(project: str, table: str) -> str:
        """
        Generate a Hydrolix SQL query that returns a single column `primary_key` with JSONCompact format, containing
        the primary keys for the named table
        """
        return textwrap.dedent(
            f"""
               SELECT primary_key FROM system.tables
               WHERE database = '{project}' AND table = '{table}'
            """
        )

    def get_pk_for_table(self, project: str, table: str) -> expressions.Identifier:
        """
        Returns the name of the table's primary key column as an Identifier
        """
        query = self._primary_keys_query(project, table)
        primary_keys = [keyrow[0] for keyrow in self.select(query).get("data", [])]
        if len(primary_keys) == 1:
            return HdxClient.parse_identifier(primary_keys[0])
        else:
            raise HdxClientError(
                f"Expected exactly 1 primary key for {project}.{table}, found {len(primary_keys)}: {primary_keys}"
            )

    def _query(self, sql_query: str, params: Optional[QueryParams] = None) -> Any:
        """
        This function *assumes* that `sql_query` has been validated a-priori. Use `select()` for SELECT queries that should be validated.
        Execute an arbitrary SQL statement against the HDX cluster without validation.
        """
        url = f"https://{self.host}{self.path}"
        if params:
            if self.server_version is not None and self.server_version >= (5, 12, 0):
                url += self._build_param_query_string(params)
            else:
                self.logger.debug("Skipping parameterized mode: server_version=%s", self.server_version)
        try:
            proxies = {"https": self.proxy_config.to_url()} if self.proxy_config else None

            self.logger.info("Running query: %s", sql_query)

            response = requests.post(
                url,
                data=sql_query,
                headers=self.headers,
                proxies=proxies,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            # HTTPError is only raised by raise_for_status(), so response exists
            body = response.text or "<empty body>"
            code = response.headers.get("X-Clickhouse-Exception-Code", "unknown")
            raise HdxClientError(f"HTTP {response.status_code} - {response.reason} (code {code}): {body}") from e
        except requests.RequestException as e:
            raise HdxClientError(f"Connection error: {e}") from e

        query_id = response.headers.get("X-Clickhouse-Query-Id")
        # Use Content-Length (compressed wire size) when available; fall back to decompressed size
        content_length = response.headers.get("content-length")
        query_bytes = int(content_length) if content_length is not None else len(response.content)
        self.bytes_received += query_bytes
        self.logger.info("Query finished (query_id=%s), query_bytes=%d", query_id, query_bytes)

        try:
            return response.json() if response.text else {}
        except json.JSONDecodeError as e:
            raise HdxClientError(f"Failed to parse JSON response: {e}\nBody:\n{response.text}")

    def select(self, sql_query: str, params: Optional[QueryParams] = None) -> JSONCompactResponse:
        """
        Execute a SELECT query against the HDX cluster.

        The query is validated and normalized to ensure it contains exactly one SELECT statement.
        """
        sanitized_query = self.validate_and_normalize_query(sql_query, "JSONCompact")
        return self._query(sanitized_query, params=params)

    def _query_streaming(self, sql_query: str, params: Optional[QueryParams] = None) -> Iterator[str]:
        """Execute query and return iterator of response lines."""
        url = f"https://{self.host}{self.path}&hdx_query_streaming_result=true"
        if params:
            if self.server_version is not None and self.server_version >= (5, 12, 0):
                url += self._build_param_query_string(params)
            else:
                self.logger.debug("Skipping parameterized mode: server_version=%s", self.server_version)
        self._active_query_id = None
        response = None
        try:
            proxies = {"https": self.proxy_config.to_url()} if self.proxy_config else None
            self.logger.info("Running streaming query: %s", sql_query)
            start_time = time.monotonic()

            # hdx_query_streaming_result=true enables server-side streaming in Hydrolix v5.12+.
            # Unknown query parameters are silently ignored by older versions, so this is safe to
            # send unconditionally.
            response = requests.post(
                url,
                data=sql_query,
                headers=self.headers,
                proxies=proxies,
                stream=True,
                timeout=None,
            )
            response.raise_for_status()
            self._streaming_response = response
        except requests.HTTPError as e:
            if response is None:
                raise HdxClientError("Unexpected error: HTTPError raised but response is None") from e
            body = response.text or "<empty body>"
            code = response.headers.get("X-Clickhouse-Exception-Code", "unknown")
            raise HdxClientError(f"HTTP {response.status_code} - {response.reason} (code {code}): {body}") from e
        except requests.RequestException as e:
            raise HdxClientError(f"Connection error: {e}") from e

        self._active_query_id = response.headers.get("X-Clickhouse-Query-Id")
        self.logger.info("Response headers: %s", dict(response.headers))

        # Use Content-Length (compressed wire size) when available; fall back to counting decompressed bytes per line
        # For streaming responses with chunked transfer encoding, Content-Length is not available.
        # Counting pre-decompression (wire) bytes would require intercepting raw chunks before
        # urllib3 decompresses them, which means handling gzip decompression manually.
        # Instead, we use Content-Length when present (non-chunked responses), and fall back to
        # counting decompressed bytes per line otherwise.
        content_length = response.headers.get("content-length")
        if content_length is not None:
            self.logger.info("Streaming response has Content-Length=%s (pre-decompression)", content_length)
        else:
            self.logger.info("Streaming response has no Content-Length, counting decompressed bytes")
        streaming_bytes = 0

        try:
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    if content_length is None:
                        line_bytes = len(line.encode("utf-8"))
                        streaming_bytes += line_bytes
                    yield line
        finally:
            if content_length is not None:
                streaming_bytes = int(content_length)
            self.bytes_received += streaming_bytes
            self._streaming_response = None
            self.logger.info(
                "Streaming query finished (query_id=%s) in %.2fs, query_bytes=%d",
                self._active_query_id,
                time.monotonic() - start_time,
                streaming_bytes,
            )
            response.close()

    def select_streaming(
        self, sql_query: str, params: Optional[QueryParams] = None
    ) -> Tuple[List[JsonCompactColumnMeta], Iterator[List[Any]]]:
        """
        Execute a connector-built SELECT query with streaming response.

        Asserts that `sql_query` is a single SELECT that sqlglot can round-trip,
        and attaches the `JSONCompactEachRowWithNamesAndTypes` FORMAT clause by parsing and
        re-rendering. This contract is tuned for `hdxsearch`, which always
        assembles SQL of that shape.

        For user-authored queries (joins, CTEs, UNION, EXPLAIN, bare-expression
        SELECTs, etc.) — i.e. anything that may not round-trip through
        sqlglot's parser — use `stream_query` instead. The caller is then
        responsible for upstream validation and for attaching the FORMAT
        clause to the query string.

        Returns:
            Tuple of (column_metadata, row_iterator)
            - column_metadata: List[{"name": str, "type": str}]
            - row_iterator: Iterator yielding List[Any] for each row
        """
        sanitized_query = self.validate_and_normalize_query(sql_query, "JSONCompactEachRowWithNamesAndTypes")
        return self.stream_query(sanitized_query, params=params)

    def stream_query(
        self, sql_query: str, params: Optional[QueryParams] = None
    ) -> Tuple[List[JsonCompactColumnMeta], Iterator[List[Any]]]:
        """
        Execute a caller-prepared query with streaming response.

        Sends `sql_query` as-is and returns (metadata, row_iterator) parsed
        from the JSONCompactEachRowWithNamesAndTypes header.

        Caller preconditions:

        1. Validation: this method does NOT call `validate_and_normalize_query`.
           Callers MUST apply their own safety policy (see
           `bin/sql_safety.py::validate_statement`) first.
        2. FORMAT: the query MUST already carry a FORMAT clause compatible
           with the streaming decoder (JSONCompactEachRowWithNamesAndTypes);
           otherwise metadata parsing will fail.

        Use this instead of `select_streaming` for queries that don't survive
        sqlglot's round-trip parse (bare-expression SELECT with SETTINGS,
        UNION, EXPLAIN-as-opaque-Command).
        """
        line_iterator = self._query_streaming(sql_query, params=params)

        # Parse metadata from first 2 lines
        try:
            names_line = next(line_iterator)
            types_line = next(line_iterator)

            column_names: List[str] = json.loads(names_line)
            column_types: List[str] = json.loads(types_line)

            if len(column_names) != len(column_types):
                raise HdxClientError(f"Metadata mismatch: {len(column_names)} names but {len(column_types)} types")

            metadata: List[JsonCompactColumnMeta] = [
                JsonCompactColumnMeta(name=name, type=typ) for name, typ in zip(column_names, column_types)
            ]
        except StopIteration:
            raise HdxClientError("Empty response: expected column metadata")
        except json.JSONDecodeError as e:
            raise HdxClientError(f"Failed to parse column metadata: {e}")

        # Return metadata + iterator for data rows
        return metadata, self._parse_data_rows(line_iterator)

    _QUERY_STATS_PREFIX = "X-HDX-Query-Stats:"

    def _parse_data_rows(self, line_iterator: Iterator[str]) -> Iterator[List[Any]]:
        """Parse remaining lines as data rows, skipping malformed rows."""
        for line in line_iterator:
            # When hdx_query_streaming_result=true is honored by the server, turbine appends query
            # stats to the response body since headers are already committed. This always appears
            # after all data rows. When the flag is not supported or ignored, stats are sent as
            # the X-HDX-Query-Stats response header instead.
            if line.startswith(self._QUERY_STATS_PREFIX):
                self.logger.info("Query stats: %s", line[len(self._QUERY_STATS_PREFIX) :])
                continue
            try:
                row_data: List[Any] = json.loads(line)
                yield row_data
            except json.JSONDecodeError as e:
                self.logger.warning(f"Skipping malformed row: {e} | line: {line!r}")

    def cancel_streaming(self) -> bool:
        """Close the active streaming response, interrupting iter_lines() on the streaming thread.
        Returns True if there was an active streaming response, False otherwise."""
        response = self._streaming_response
        if response is not None:
            response.close()
            return True
        return False

    def kill_query(self, sid: Optional[str]) -> bool:
        """
        Kill the active query. If a query ID is available (server streaming supported), uses
        KILL QUERY WHERE query_id = '...' directly. Falls back to the SID-based pattern match
        for older Hydrolix versions that don't support server-side streaming.

        The SID fallback retries indefinitely — the query may not yet be registered in
        system.processes when the kill is first attempted.

        Returns True if the kill was sent successfully, False if neither query_id nor sid is available.
        """
        query_id = self._active_query_id
        if query_id:
            try:
                self._query(f"KILL QUERY WHERE query_id = '{query_id}' ASYNC FORMAT JSONCompact")
                self.logger.info("Kill query sent for query_id=%s", query_id)
                return True
            except HdxClientError as e:
                self.logger.warning("kill_query failed for query_id=%s: %s", query_id, e)
                return False

        if not sid:
            return False

        attempt = 0
        while True:
            if attempt > 0:
                time.sleep(1)
            attempt += 1
            try:
                # KILL QUERY WHERE filters system.processes directly — no separate SELECT needed.
                # If query already completed, KILL QUERY will do nothing.
                result = self._query(f"KILL QUERY WHERE query LIKE '%sid:{sid}''%' ASYNC FORMAT JSONCompact")
                rows = result.get("data", [])
                if rows:
                    self.logger.info("Kill query sent for sid=%s", sid)
                    return True
                self.logger.info("Query for sid=%s not yet found (attempt %d), retrying", sid, attempt)
            except HdxClientError as e:
                self.logger.warning("kill_query attempt %d failed: %s", attempt, e)

    @staticmethod
    def validate_and_normalize_query(query_str: str, format: str) -> str:
        """
        Parse query_str to verify that it is valid ClickHouse SQL with exactly one SELECT statement.
        Returns the normalized query with the specified FORMAT clause
        """
        try:
            parsed = sqlglot.parse_one(query_str, dialect="clickhouse")
            parsed_select_statements = list(parsed.find_all(expressions.Select))
            if len(parsed_select_statements) != 1:
                raise HdxClientError(
                    f"Invalid query parameters. Assembled query contains {len(parsed_select_statements)} SELECT statements:\n{query_str}"
                )
            parsed.set("format", format)
            return parsed.sql(dialect="clickhouse")
        except SqlglotError as err:
            raise HdxClientError(f"Invalid query parameters. Unable to parse the query:\n{query_str}\n\nError: {err}")

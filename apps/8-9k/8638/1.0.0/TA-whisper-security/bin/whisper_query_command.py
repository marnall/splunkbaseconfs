"""Generating search command for ad-hoc Whisper Knowledge Graph queries.

``| whisperquery query="MATCH (h:HOSTNAME {name: $domain}) RETURN h.name"
  params="domain=suspicious.com" [max_results=1000]``

Executes arbitrary Cypher queries against the Whisper API and returns
results as Splunk events. Includes query validation to reject write
operations.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
from typing import TYPE_CHECKING, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
    validators,
)
from whisper_logging import get_logger, setup_logging  # noqa: E402

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient

logger = get_logger("query_command")
setup_logging("query_command")

# Write operations forbidden in read-only graph
_WRITE_OPS_RE = re.compile(
    r"\b(CREATE|DELETE|DETACH\s+DELETE|SET|REMOVE|MERGE|DROP|LOAD\s+CSV)\b",
    re.IGNORECASE,
)

# Maximum results to prevent runaway queries
DEFAULT_MAX_RESULTS = 10000


def validate_query(query: str) -> list[str]:
    """Validate a Cypher query for safety.

    Args:
        query: The Cypher query string.

    Returns:
        List of validation error messages. Empty if valid.
    """
    errors: list[str] = []
    if not query or not query.strip():
        errors.append("Query string is empty")
        return errors

    match = _WRITE_OPS_RE.search(query)
    if match:
        errors.append(f"Write operation '{match.group(0)}' is not allowed — the Whisper Knowledge Graph is read-only")

    return errors


def decode_params_b64(b64_str: str) -> dict[str, Any]:
    """Decode a base64-encoded JSON parameter string.

    Allows complex JSON values (arrays, nested objects) to be passed
    as query parameters without SPL quote-escaping issues.

    Args:
        b64_str: Base64-encoded JSON string.

    Returns:
        Dictionary of parameter name-value pairs.

    Raises:
        ValueError: If the string is not valid base64 or JSON.
    """
    if not b64_str or not b64_str.strip():
        return {}
    try:
        decoded = base64.b64decode(b64_str.strip()).decode("utf-8")
        return json.loads(decoded)
    except Exception as exc:
        raise ValueError(f"Invalid base64 params: {exc}") from exc


def parse_params(params_str: str) -> dict[str, str]:
    """Parse a parameter string into a dictionary.

    Supports formats: ``key=value,key2=value2`` or JSON.

    Args:
        params_str: The parameter string.

    Returns:
        Dictionary of parameter name-value pairs.
    """
    if not params_str or not params_str.strip():
        return {}

    params_str = params_str.strip()

    # Try JSON first
    if params_str.startswith("{"):
        try:
            return json.loads(params_str)
        except json.JSONDecodeError:
            pass

    # Key=value comma-separated format
    params: dict[str, str] = {}
    for pair in params_str.split(","):
        pair = pair.strip()
        if "=" not in pair:
            continue
        key, _, value = pair.partition("=")
        params[key.strip()] = value.strip()

    return params


def execute_query(
    client: WhisperAPIClient,
    query: str,
    parameters: dict[str, str] | None = None,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> list[dict[str, Any]]:
    """Execute a Cypher query and return results as Splunk events.

    Args:
        client: Configured WhisperAPIClient.
        query: The Cypher query string.
        parameters: Optional query parameters.
        max_results: Maximum number of results to return.

    Returns:
        List of event dictionaries ready for Splunk.

    Raises:
        WhisperAPIRequestError: If the API returns an error.
        ValueError: If the query fails validation.
    """
    # Validate query
    errors = validate_query(query)
    if errors:
        raise ValueError("; ".join(errors))

    now = time.time()
    result = client.query(query, parameters=parameters or {})

    rows = result.get("rows", [])
    columns = result.get("columns", [])
    statistics = result.get("statistics", {})
    query_time_ms = statistics.get("executionTimeMs", 0)
    row_count = statistics.get("rowCount", len(rows))

    # Build events
    events: list[dict[str, Any]] = []
    for row in rows[:max_results]:
        event: dict[str, Any] = {"_time": now}

        # Map columns to field names
        if isinstance(row, dict):
            for col in columns:
                value = row.get(col)
                if value is not None:
                    # Use column alias as field name
                    event[col] = _flatten_value(value)
        elif isinstance(row, list):
            for i, col in enumerate(columns):
                if i < len(row) and row[i] is not None:
                    event[col] = _flatten_value(row[i])

        # Add metadata — timing breakdown (#405)
        timing = result.get("_timing", {})
        event["whisper_query_time_ms"] = query_time_ms
        event["whisper_round_trip_ms"] = timing.get("round_trip_ms", 0)
        event["whisper_network_latency_ms"] = timing.get("network_latency_ms", 0)
        event["whisper_row_count"] = row_count

        events.append(event)

    # Ensure uniform field set so the Splunk chunked v2 protocol
    # sees all fields in the first event chunk.
    _normalize_event_fields(events)

    return events


SCHEMA_MODES = ("labels", "relationships", "properties", "schema", "full")


def execute_schema_query(
    client: WhisperAPIClient,
    mode: str = "labels",
) -> list[dict[str, Any]]:
    """Execute a schema introspection query.

    Modes:
        - ``labels``: node labels via ``CALL db.labels()``
        - ``relationships``: edge types via ``CALL db.relationshipTypes()``
        - ``properties``: property keys via ``CALL db.propertyKeys()``
        - ``schema``: rich schema via ``CALL db.schema()`` (descriptions,
          examples, counts, fast/slow patterns, best practices)
        - ``full``: combined schema + property keys

    Args:
        client: Configured WhisperAPIClient.
        mode: One of 'labels', 'relationships', 'properties', 'schema', 'full'.

    Returns:
        List of event dictionaries with Splunk-ready fields.

    Raises:
        WhisperAPIRequestError: If the API returns an error.
        ValueError: If mode is invalid.
    """
    if mode not in SCHEMA_MODES:
        raise ValueError(f"Invalid schema mode '{mode}'. Valid: {', '.join(SCHEMA_MODES)}")

    if mode == "full":
        return _execute_full_schema(client)

    queries = {
        "labels": "CALL db.labels()",
        "relationships": "CALL db.relationshipTypes()",
        "properties": "CALL db.propertyKeys()",
        "schema": "CALL db.schema()",
    }

    events = execute_query(client, queries[mode])

    # Add schema_mode field for filtering in Splunk
    for event in events:
        event["whisper_schema_mode"] = mode

    return events


def _execute_full_schema(client: WhisperAPIClient) -> list[dict[str, Any]]:
    """Execute combined schema introspection (schema + property keys).

    Combines ``db.schema()`` (nodes, relationships, tips) with
    ``db.propertyKeys()`` (all property keys) into a single result set.
    Each event includes a ``whisper_schema_mode`` field for filtering.

    The combined result set is normalized so that every event contains
    the same fields (defaulting to empty string for missing ones). This
    prevents the Splunk chunked v2 protocol from dropping fields that
    only appear in one of the two query result sets.

    Args:
        client: Configured WhisperAPIClient.

    Returns:
        List of event dictionaries from both queries.
    """
    # Get full schema (nodes, relationships, tips)
    schema_events = execute_query(client, "CALL db.schema()")
    for event in schema_events:
        event["whisper_schema_mode"] = "schema"

    # Get all property keys
    property_events = execute_query(client, "CALL db.propertyKeys()")
    for event in property_events:
        event["whisper_schema_mode"] = "properties"

    combined = schema_events + property_events

    # Normalize across both query results so the Splunk chunked v2
    # protocol sees all fields (schema + property key fields).
    _normalize_event_fields(combined)

    return combined


def _normalize_event_fields(events: list[dict[str, Any]]) -> None:
    """Ensure all events have a uniform field set.

    The Splunk SDK GeneratingCommand chunked v2 protocol determines the
    field schema from the first event chunk. If later events introduce
    new fields (e.g. relationship events with sourceLabels/targetLabels
    after node events that lack them), those fields are silently dropped.

    This function computes the union of all keys across all events and
    fills missing fields with empty strings so every event advertises
    the complete field set.

    Args:
        events: List of event dictionaries to normalize in-place.
    """
    if not events:
        return
    all_keys: set[str] = set()
    for event in events:
        all_keys.update(event.keys())
    for event in events:
        for key in all_keys:
            event.setdefault(key, "")


def _flatten_value(value: Any) -> Any:
    """Flatten complex values for Splunk compatibility.

    Args:
        value: A value from the query result.

    Returns:
        A Splunk-compatible value (string, number, or JSON string for complex types).
    """
    if isinstance(value, dict):
        # Node/relationship objects — extract name or convert to JSON
        if "name" in value:
            return value["name"]
        return json.dumps(value, default=str)
    if isinstance(value, list):
        # Serialize lists to JSON strings for Splunk compatibility
        flattened = [_flatten_value(v) for v in value]
        return json.dumps(flattened, default=str)
    return value


# ─── Splunk SDK Command Wrappers ─────────────────────────────────────────


@Configuration()
class WhisperQueryCommand(GeneratingCommand):
    """Generating search command for ad-hoc Whisper Knowledge Graph queries.

    Usage::

        | whisperquery query="MATCH (h:HOSTNAME {name: $domain}) RETURN h.name"
          params="domain=suspicious.com" [max_results=1000]
    """

    query = Option(name="query", require=True)
    params = Option(name="params", require=False, default="")
    params_b64 = Option(name="params_b64", require=False, default="")
    max_results = Option(name="max_results", require=False, default=DEFAULT_MAX_RESULTS, validate=validators.Integer())

    def generate(self):
        """Execute a Cypher query and yield results as Splunk events.

        Yields:
            Splunk event dictionaries.
        """
        from whisper_command_helpers import get_api_client_from_service

        try:
            client = get_api_client_from_service(self.service)
        except RuntimeError as exc:
            logger.error("action=whisperquery status=error reason=client_init_failed", exc_info=True)
            self.error_exit(exc, str(exc))
            return

        # params_b64 takes precedence over params (avoids SPL quote-escaping issues)
        if self.params_b64:
            try:
                parameters = decode_params_b64(self.params_b64)
            except ValueError as exc:
                logger.error("action=whisperquery status=error reason=invalid_params_b64", exc_info=True)
                self.error_exit(exc, str(exc))
                return
        else:
            parameters = parse_params(self.params) if self.params else {}

        try:
            events = execute_query(client, self.query, parameters=parameters, max_results=self.max_results)
            yield from events
        except (ValueError, Exception) as exc:
            logger.error("action=whisperquery status=error reason=query_failed", exc_info=True)
            self.error_exit(exc, str(exc))
        finally:
            client.close()


@Configuration()
class WhisperSchemaCommand(GeneratingCommand):
    """Generating search command for Whisper Knowledge Graph schema introspection.

    Modes:
        - ``labels``: all node labels
        - ``relationships``: all relationship types
        - ``properties``: all property keys (via ``db.propertyKeys()``)
        - ``schema``: rich schema with descriptions, examples, counts,
          fast/slow patterns, and best practices (via ``db.schema()``)
        - ``full``: combined schema + property keys

    Usage::

        | whisperschema [mode=labels|relationships|properties|schema|full]
    """

    mode = Option(name="mode", require=False, default="labels")

    def generate(self):
        """Execute a schema introspection query and yield results.

        Yields:
            Splunk event dictionaries.
        """
        from whisper_command_helpers import get_api_client_from_service

        try:
            client = get_api_client_from_service(self.service)
        except RuntimeError as exc:
            logger.error("action=whisperschema status=error reason=client_init_failed", exc_info=True)
            self.error_exit(exc, str(exc))
            return

        try:
            events = execute_schema_query(client, mode=self.mode)
            yield from events
        except (ValueError, Exception) as exc:
            logger.error("action=whisperschema status=error reason=schema_query_failed", exc_info=True)
            self.error_exit(exc, str(exc))
        finally:
            client.close()


if __name__ == "__main__":
    dispatch(WhisperQueryCommand, sys.argv, sys.stdin, sys.stdout, __name__)

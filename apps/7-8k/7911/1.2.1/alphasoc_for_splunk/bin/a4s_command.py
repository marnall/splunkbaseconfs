from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

sys.path.insert(0, make_splunkhome_path(["etc", "apps", "alphasoc_for_splunk", "bin"]))

from a4slib.config import ConfigError, CredentialError
from a4slib.http_client import (
    AlphaSOCHttpClient,
    APIError,
    LakeQuery,
)
from a4slib.query_parsing import QueryParsingError, parse_request
from a4slib.splunk_service import service_from_searchinfo
from a4slib.splunklib.searchcommands import Configuration, GeneratingCommand, dispatch
from a4slib.transforms import flatten_event

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

    from a4slib.http_client import StreamMessage

# Streaming configuration for Splunk SCP v2 chunking.
# Each OCSF event type has a different field schema (DNS has query.hostname, IP has dst_endpoint.ip, etc.).
# Splunk SCP v2 rejects varying field sets within a single chunk, so we start with 1 event per chunk.
# After processing enough events, we increase chunk size for better performance.
# One event per chunk initially (handles schema variation)
MAXRESULT_ROWS_INITIAL = 1
MAXRESULT_ROWS_AFTER_THRESHOLD = 1000  # Larger chunks after threshold
MAXRESULT_ROWS_THRESHOLD = 500  # Switch to larger chunks after this many events


HELP_TEXT = """\
| alphasoc — Query raw OCSF telemetry from AlphaSOC's data lake.

Usage:
  | alphasoc                                                            (all events)
  | alphasoc [class_name=<classes>] [log_source=<sources>] <filter_expression>
  | alphasoc help

Reserved positional assignments:
  class_name    Comma-separated list of OCSF class names.
                Examples: "DNS Activity", "Network Activity", "DNS Activity, Network Activity".
                Accepts: Title Case, snake_case, dash-separated.
  log_source    Comma-separated list of data origins to include.
                Examples: "aws-route53", "aws-vpc-flow, azure-vnet-flow".
                See: https://docs.alphasoc.com/data_origins/overview/ for available origins.
  Note: class_name/log_source must be standalone tokens (not directly combined with AND/OR or parentheses).

Expression:
  Use positional tokens for filter expressions (field=value with AND/OR and parentheses).
  Values containing spaces must be single-quoted:
    http_request.user_agent='Mozilla/5.0 (Windows)'.

Query fields (OCSF v1.5.0 paths):
  Device:       device.ip, device.hostname, device.uid, device.mac, actor.user.name
  Network:      dst_endpoint.ip, dst_endpoint.port, connection_info.protocol_name
  DNS:          query.hostname, query.type
  HTTP:         http_request.user_agent, http_request.http_method
  TLS:          tls.certificate.fingerprints.0.value, tls.certificate.fingerprint,
                tls.certificate.subject, tls.certificate.issuer
  Audit:        src_endpoint.ip, metadata.product.uid

Examples:
  | alphasoc                                                 (fetch all events in time range)
  | alphasoc device.ip=10.0.0.5
  | alphasoc device.ip=10.0.0.5 AND query.hostname=evil.com
  | alphasoc class_name="DNS Activity"
  | alphasoc class_name="DNS Activity, Network Activity"
  | alphasoc log_source="aws-route53"
  | alphasoc class_name="dns_activity"                        (snake_case also accepted)
  | alphasoc class_name="DNS Activity" device.ip=10.0.0.5
  | alphasoc device.ip=10.0.0.5 class_name=dns_activity        (trailing assignment also supported)

The time range is required and taken from the Splunk time picker. Ensure a time range
is selected before running the command.

Note: Results are streamed from the data lake. Large queries may be limited or rejected by the server.\
"""


def _epoch_to_iso8601(epoch: float) -> str:
    """Convert a Unix epoch float to an ISO 8601 UTC string."""
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@Configuration()
class AlphaSOCSearch(GeneratingCommand):
    """Query raw OCSF telemetry from AlphaSOC's data lake."""

    _stream_error_count: int = 0

    def generate(self) -> Generator[dict[str, object], None, None]:
        try:
            request = parse_request(list(self.fieldnames or []))
        except QueryParsingError as exc:
            self.write_error(str(exc))
            return

        if request.is_help:
            yield {"_raw": HELP_TEXT}
            return

        time_range = self._time_range()
        if time_range is None:
            return
        since, until = time_range

        service = service_from_searchinfo(self.search_results_info)
        try:
            client = AlphaSOCHttpClient.from_service(service)
        except (CredentialError, ConfigError) as exc:
            self.write_error(str(exc))
            return

        stream = client.query(
            LakeQuery(
                since=since,
                until=until,
                query=request.query,
                class_name=request.class_name,
                log_source=request.log_source,
            ),
        )

        yield from self._stream_events(stream)

    def _stream_events(self, stream: Iterator[StreamMessage]) -> Generator[dict[str, object], None, None]:
        """Transform and yield events from the NDJSON stream.

        Handles exceptions that occur during stream iteration (network errors, API errors).
        """
        # Each OCSF event type has a different body schema (DNS has body.fqdn,
        # IP has body.destIP, etc.).  Setting _maxresultrows = 1 forces each
        # event into its own SCP v2 chunk so Splunk accepts varying field sets.
        self._record_writer._maxresultrows = MAXRESULT_ROWS_INITIAL  # noqa: SLF001  # ty:ignore[invalid-assignment]

        self._stream_error_count = 0

        count = 0
        skipped = 0
        limited = False
        max_rows_increased = False

        try:
            for message in stream:
                # Check for error message (has 'error' field)
                if "error" in message:
                    self._handle_stream_error(message)
                    continue

                # Check for event message (has 'data' field)
                elif "data" in message:
                    if message.get("limitReached"):
                        limited = True
                    result = self._process_event(message.get("data", {}))
                    if result is not None:
                        yield result
                        count += 1
                        if not max_rows_increased and count > MAXRESULT_ROWS_THRESHOLD:
                            self._record_writer._maxresultrows = MAXRESULT_ROWS_AFTER_THRESHOLD  # noqa: SLF001  # ty:ignore[invalid-assignment]
                            max_rows_increased = True
                    else:
                        skipped += 1

        except APIError as exc:
            self.logger.exception("Data lake API error during streaming.")
            self.write_error("{0}", str(exc))
            return

        self._finalize_stream(count, skipped, limited=limited)

    def _process_event(self, event: dict[str, dict]) -> dict[str, object] | None:
        try:
            return flatten_event(event)
        except Exception as exc:  # noqa: BLE001
            event_uid = event.get("metadata", {}).get("uid", "unknown")
            self.logger.warning("Error transforming event (uid=%s): %s", event_uid, exc, exc_info=True)
        return None

    def _handle_stream_error(self, message: StreamMessage) -> None:
        """Handle a non-fatal error message from the stream."""
        error_msg = str(message.get("error", "Unknown error"))
        self.logger.warning("Stream error: %s", error_msg)
        self._stream_error_count += 1

    def _finalize_stream(
        self,
        count: int,
        skipped: int,
        *,
        limited: bool,
    ) -> None:
        """Write final warnings after processing the stream."""
        warnings: list[str] = []

        if self._stream_error_count:
            warnings.append(
                f"Server reported {self._stream_error_count} stream error message(s). See search.log for full details."
            )

        if skipped:
            warnings.append(f"{skipped} event(s) skipped due to transform errors (check logs for details).")

        if count == 0:
            warnings.append("No results found.")
        elif limited:
            msg = (
                f"Results were limited by the AlphaSOC data lake after {count} events. "
                "Narrow your time range or add filters to refine the query."
                " Use | alphasoc help for filtering syntax."
            )
            warnings.append(msg)

        if warnings:
            self.write_warning("\n".join(warnings))

    def _time_range(self) -> tuple[str, str] | None:
        """Extract time range from Splunk search context. Returns None if unavailable."""
        result = self._search_context_time_range()
        if result is not None:
            return result

        self.write_error(
            "Could not extract time range from search context. Ensure a time range is selected in the time picker."
        )
        return None

    def _search_context_time_range(self) -> tuple[str, str] | None:
        """Try to extract (since, until) from the Splunk search context. Returns None on any failure."""
        try:
            info = self.search_results_info
        except AttributeError:
            self.logger.warning("Could not access search_results_info.", exc_info=True)
            return None

        if info is None:
            self.logger.warning("search_results_info is None, cannot extract time range.")
            return None

        # SearchResultsInfo uses __getattr__ which masks missing keys;
        # __dict__ gives direct access to the underlying data.
        try:
            et = info.__dict__["search_et"]
            lt = info.__dict__["search_lt"]
        except KeyError:
            self.logger.warning("search_et/search_lt missing from search context.", exc_info=True)
            return None

        if not et or not lt:
            self.logger.warning("search_et or search_lt is empty: et=%r lt=%r", et, lt)
            return None

        try:
            return _epoch_to_iso8601(float(et)), _epoch_to_iso8601(float(lt))
        except (ValueError, TypeError):
            self.logger.warning("Could not parse time range values et=%r lt=%r.", et, lt, exc_info=True)
            return None

    def _protocol_v2_option_parser(self, arg: str) -> list[str]:
        """Custom option parser to handle protocol v2 arguments."""
        return [arg]


dispatch(AlphaSOCSearch, sys.argv, sys.stdin, sys.stdout, __name__)

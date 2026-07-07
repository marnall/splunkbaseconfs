from typing import Any, Dict, List, Union, TypeVar, Callable, Optional
from datetime import datetime, timezone, timedelta
from textwrap import shorten
import os
import re
import csv
import json
import signal
import logging

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from splunklib.searchcommands.internals import CsvDialect
from splunklib.searchcommands.search_command import SearchCommand
import requests

UNAUTHORIZED_ERROR = (
    "Invalid or expired API Key. Please perform the app setup again with a new API Key if the issue persists."
)

_STAGE = os.getenv("APP_ENVIRONMENT", "PROD")
_CANCEL_URL = (
    f"https://api.{_STAGE}.query.ai/search/v2/graphql"
    if _STAGE in ("dev", "test")
    else "https://api.query.ai/search/v2/graphql"
)

_CANCEL_TIMEOUT = timedelta(minutes=1)

try:
    from typing_extensions import override  # pyright: ignore[reportAssignmentType]
except ImportError:
    # typing.override is 3.12+; on 3.9-3.11 we need typing_extensions, fall back to a no-op if absent.
    _F = TypeVar("_F", bound=Callable[..., Any])

    def override(func: _F) -> _F:
        return func


def cancel_query(api_key: str, query_id: str, logger: logging.Logger) -> None:
    timeout = (timedelta(seconds=3.05), _CANCEL_TIMEOUT)
    timeout = (timeout[0].total_seconds(), timeout[1].total_seconds())

    try:
        logger.info(f"Cancelling query {query_id}")
        with requests.Session() as http:
            response = http.post(
                _CANCEL_URL,
                timeout=timeout,
                headers={"content-type": "application/json", "x-token-authorization": api_key},
                data=json.dumps(
                    {
                        "operationName": "cancel_search",
                        "query": "mutation cancel_search($id: ID!) { cancel_search(id: $id) { status } }",
                        "variables": {"id": query_id},
                    }
                ),
            )

        logger.info(f"Cancel response headers: {response.headers!r}")
        response.raise_for_status()

        if response.headers.get("content-type") != "application/json":
            logger.info(f"Cancel response body: {shorten(response.text, width=1024)}")
            raise RuntimeError("Server did not cancel query. See application logs for details")

        payload: dict[str, Any] = response.json()
        errors = payload.get("errors")
        if errors:
            logger.info(f"Cancel errors: {errors!r}")

        try:
            status = payload["data"]["cancel_search"]["status"]
            logger.info(f"Query status: {status}")
        except KeyError:
            logger.warning(f"Response did not indicate status: {payload!r}")

    except Exception:
        logger.exception("Failed to cancel query")


class SplunkCancelCallback(FileSystemEventHandler):
    def __init__(self, command: SearchCommand, callback: Callable[[], None]):
        assert command.logger is not None

        self.logger = command.logger
        self.stopped = False
        self.command = command
        self.callback = callback

        info_csv_path: str = self.command._input_header.get("infoPath")  # pyright: ignore
        dispatch_dir: str = os.path.dirname(info_csv_path)

        self.observer = Observer()
        self.observer.schedule(self, dispatch_dir, recursive=False)

        for s in (signal.SIGTERM, signal.SIGHUP):
            signal.signal(s, lambda n, _: self.logger.info(f"Received {signal.Signals(n).name}"))

    def watch(self) -> None:
        self.observer.start()

    def unwatch(self) -> None:
        self.observer.stop()

    @override
    def on_created(self, event: FileSystemEvent):
        self._handle_event(event)

    @override
    def on_modified(self, event: FileSystemEvent):
        self._handle_event(event)

    def _handle_event(self, event: FileSystemEvent):
        try:
            src_path: str = os.fsdecode(event.src_path)
            src_basename = os.path.basename(src_path)

            if self.stopped:
                return

            if src_basename == "status.csv":
                if _parse_status(src_path) not in ("FAILED", "CANCELED", "FINALIZING", "DONE"):
                    return
            elif src_basename != "finalize":
                return

            self.stopped = True
            self.callback()
            self.observer.stop()
            self.command.finish()

        except Exception as exc:
            self.logger.warning(f"Error when handling {event!r}", exc_info=exc)


def _parse_status(path: str) -> Union[None, str]:
    result: dict[str, str] = {}

    # We expect this file to have only a single row, but if that's not the case, we'll return the last one
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f, dialect=CsvDialect)
        fields = next(reader)
        values = next(reader)

    result = {k: v for k, v in zip(fields, values)}
    return result.get("state")


def convert_utc_time_to_epoch(utc_time_string: str, logger: logging.Logger, pid: str) -> Dict[str, Any]:
    """
    Convert a UTC time string to an epoch timestamp.

    This function takes a UTC time string in the format "%Y-%m-%dT%H:%M:%S.%fZ" and converts it to
    an epoch timestamp, which represents the number of seconds since January 1, 1970 (Unix epoch).

    Args:
        utc_time_string (str): A string containing the UTC time in the format "%Y-%m-%dT%H:%M:%S.%fZ".
        logger (logging.Logger): A Logger object for logging error messages.
        pid (str): A process identifier (PID) to include in error messages for identification.

    Returns:
        Dict[str, Any]: A dictionary containing the epoch time as "epoch_time" if successful.
            If the time conversion fails, an error message is included in the dictionary.

    Note:
        If the time conversion fails, an error message is logged using the provided logger,
        and the dictionary contains an "Error" key with an error message.

    Example:
        convert_to_epoch("2023-09-12T14:30:00.123Z", logger, "12345")

    Returns:
        {"epoch_time": 1692000600.123}
    """
    try:
        utc_dt = datetime.strptime(utc_time_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    except Exception as e:
        logger.error(f"PID {pid}: Time conversion failed with exception: {e}")
        return {
            "Error": f"Incorrect time format: please check and verify entity config or contact Query Support with Traceback: {e}"
        }
    epoch_timestamp = (utc_dt - datetime(1970, 1, 1)).total_seconds()
    return {"epoch_time": epoch_timestamp}


_FSQL_PREFIX_RE = re.compile(r"\|\s*fsql\s+", re.IGNORECASE)


def extract_fsql_args_from_raw_search(raw_search: str) -> Optional[str]:
    """Extract the FSQL query args from a Splunk raw search string.

    Locates `| fsql` (case-insensitive) and returns the argument substring
    that follows, stopping at the first pipe (`|`) found outside of single-
    or double-quoted regions. This lets a user pipe FSQL results into
    downstream commands (e.g. `| fsql ... | queryagent ask="list users"`)
    without the trailing stage being slurped into the FSQL query body.
    """
    match = _FSQL_PREFIX_RE.search(raw_search)
    if not match:
        return None

    start = match.end()
    i = start
    quote: Optional[str] = None
    while i < len(raw_search):
        c = raw_search[i]
        if quote is not None:
            if c == "\\" and i + 1 < len(raw_search):
                i += 2
                continue
            if c == quote:
                quote = None
        elif c == '"' or c == "'":
            quote = c
        elif c == "|":
            break
        i += 1

    return raw_search[start:i].strip()


def parse_csv_option(value: Union[str, None]) -> List[str]:
    """
    Parse a user-supplied `platforms="..."` / `events="..."` option into a list.

    Connectors and OCSF classes reach the Splunk command as a single comma-
    separated string. A connector name can legitimately contain a comma (e.g.
    Acme, Inc.), so users can wrap any item in double quotes to protect its
    commas. Double quotes inside a quoted value are escaped by doubling them,
    matching RFC 4180.

    The emitted list is sent on the wire as a JSON array, which removes the
    comma ambiguity downstream. Names with commas cannot round-trip through
    the legacy CSV path even on old SQB deployments.
    """
    if not value:
        return []
    reader = csv.reader([value], skipinitialspace=True)
    empty: List[str] = []
    row = next(reader, empty)
    return [item.strip() for item in row if item.strip()]


def epoch_to_iso8601(epoch_timestamp: int) -> str:
    """
    Convert an epoch timestamp to ISO 8601 format in the UTC time zone.

    Args:
        epoch_timestamp (int): Epoch timestamp to convert.

    Returns:
        str: ISO 8601 formatted timestamp in UTC time zone.
    """
    utc_datetime = datetime.fromtimestamp(epoch_timestamp, tz=timezone.utc)
    return utc_datetime.isoformat()


def extract_error(response: requests.Response) -> str:
    if response.status_code == 401:
        return f"Error: {UNAUTHORIZED_ERROR}"

    try:
        # Attempt to parse the JSON response
        try:
            response_json = response.json()
        except (json.JSONDecodeError, ValueError):
            response_json = None

        # Function to escape curly braces in a string
        def escape_curly_braces(text: str) -> str:
            return text.replace("{", "{{").replace("}", "}}")

        # Check for error in JSON response
        if response_json and "error" in response_json:
            error_message = escape_curly_braces(response_json["error"])
            return f"Error: {error_message}"
        # Check for text in response
        elif response.text:
            error_message = escape_curly_braces(response.text)
            return f"Error: {error_message}"
        # Check for HTTP status reason
        elif response.reason:
            error_message = escape_curly_braces(response.reason)
            return f"Error: {response.status_code} {error_message}"
        else:
            return "Error: Unknown error occurred"
    except Exception as e:
        return f"Error: {str(e)}"

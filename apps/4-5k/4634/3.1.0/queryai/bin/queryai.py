import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

from types import ModuleType
from typing import Any, Dict, List, Tuple, Iterator, Optional, Generator
from datetime import datetime, timedelta
import re
import json
import time
import inspect
import logging

from utils import (
    SplunkCancelCallback,
    cancel_query,
    extract_error,
    epoch_to_iso8601,
    parse_csv_option,
)
from auth_token import (
    PROXY_REALM,
    API_KEY_REALM,
    PROXY_USERNAME,
    API_KEY_USERNAME,
    retrieve_password,
)
from loggerutil import setup_logging
from typing_extensions import TypedDict
from basic_help_payload import HELP_ALL_PAYLOAD, HELP_SEARCH_PAYLOAD
from splunklib.searchcommands import Option, Configuration, GeneratingCommand, dispatch
import requests

STAGE = os.getenv("APP_ENVIRONMENT", "PROD")
SEARCH_URL = (
    f"https://api.{STAGE}.query.ai/search/translation/splunk"
    if STAGE in ("dev", "test")
    else "https://api.query.ai/search/translation/splunk"
)

# Realms and username to be used for storing and retrieving passwords using storage/passwords
DEFAULT_TIMEOUT = 480  # 8 mins
SYNTAX_DOC_URL = "https://docs.query.ai/docs/federated-search-from-splunk#command-syntax"
CHUNK_SIZE = 16384
MAXRESULT_ROWS_INITIAL = 1
MAXRESULT_ROWS_AFTER_THRESHOLD = 1000
MAXRESULT_ROWS_THRESHOLD = 500
start = None


# Exception to be raised when there is any exception while making API request
class APIError(Exception):
    pass


class SplunkQBResponse(TypedDict, total=False):
    statusCode: int
    results: Dict[str, Any]
    errors: List[str]


def flatten_results_and_collect_errors(
    results: Iterator[SplunkQBResponse], error_list: List[str]
) -> Iterator[Dict[str, Any]]:
    for result in results:
        errors = result.get("errors", [])
        if errors:
            error_list.extend(errors)

        if result.get("results", {}):
            deserialized_results = result.get("results", {})
            for entity_results in deserialized_results.values():
                if isinstance(entity_results, list):
                    yield from entity_results


@Configuration()
class QueryAISearch(GeneratingCommand):
    splunk_module: Optional[ModuleType] = None
    errors: List[str] = []
    if STAGE in ("dev", "test", "PROD"):
        import splunk  # type: ignore

        splunk_module = splunk
        logger: logging.Logger = setup_logging(splunk_module, "queryai")

    # Precompiled regex for structured query detection
    # Build pattern components:
    _KEY_PATTERN = r"[\w.]+"
    _SINGLE_VALUE = r"('[^']*'|[*\w.-]+)"
    _IN_VALUES = r"\(\s*" + _SINGLE_VALUE + r"(\s*,\s*" + _SINGLE_VALUE + r")*\s*\)"
    _CONDITION = (
        r"(NOT\s+)?"
        + _KEY_PATTERN
        + r"\s*"
        + r"(?:"
        + r"(?:=|!=)\s*"
        + _SINGLE_VALUE
        + r"|"
        + r"IN\s*"
        + _IN_VALUES
        + r")"
    )
    _STRUCTURED_PATTERN = re.compile(
        r"^" + _CONDITION + r"(?:\s+(?:(?:AND|OR)\s+)?" + _CONDITION + r")*$", re.IGNORECASE
    )

    # FSQL top-level statements always begin with one of these keywords. Mirrors
    # `isFsqlQuery` in ecr-splunk-query-builder so both sides classify identically.
    _FSQL_PATTERN = re.compile(r"^\s*(QUERY|SUMMARIZE|STATS|EXPLAIN)\b", re.IGNORECASE)

    search = Option(require=False)

    platforms = Option(require=False)

    help = Option(require=False, default=None)

    connectors = Option(require=False)

    hide_nulls = Option(require=False, default="True")

    limit = Option(require=False, default=-1)  # -1 or negative indicating infinite or ignore limit by default

    exclude_connectors = Option(require=False)

    events = Option(require=False)

    exclude_events = Option(require=False)

    pid = str(os.getpid())
    search_url = SEARCH_URL

    _waiting_for_query_id: bool = False
    _query_id: Optional[str] = None
    _api_key: Optional[str] = None

    @staticmethod
    def validate_search_params(
        search: str, help: str, events: str, exclude_events: str, connectors: str, exclude_connectors: str
    ):
        if not search and not help and not events and not connectors and not exclude_events and not exclude_connectors:
            raise ValueError(
                f"The `| queryai` command let's you directly search distributed data sources without needing to index that data into splunk. Run `| queryai help=all` to understand how to run federated searches."
            )

    @staticmethod
    def validate_help_and_sub_options(_help: str, *args: List[str]):
        if _help:
            for arg in args:
                if arg:
                    raise ValueError(
                        f"help option doesn't support any sub-option. Use `| queryai help=all` to know more about its usage."
                    )

    @staticmethod
    def validate_include_and_exclude(include: str, exclude: str, sub_option_one: str, sub_option_two: str):
        if include and exclude:
            raise ValueError(f"Only one out of `{sub_option_one}` and `{sub_option_two}` params should be provided.")

    @staticmethod
    def validate_limit(limit: str):
        try:
            int(limit)
        except Exception as e:
            raise ValueError(
                "The value of limit is not integer convertible. Please use integer value for the limit parameter."
            )
        if int(limit) == 0:
            raise ValueError("0 is an invalid limit, please use a value greater than 0.")

    @staticmethod
    def validate_hide_nulls(hide_nulls: str):
        """Validate that hide_nulls is a valid boolean value."""
        if hide_nulls is None:
            return

        if not isinstance(hide_nulls, str):
            hide_nulls = str(hide_nulls)

        # Define valid boolean values (case-insensitive)
        valid_true_values = {"true", "t", "yes", "y", "1", "on"}
        valid_false_values = {"false", "f", "no", "n", "0", "off"}
        valid_values = valid_true_values | valid_false_values

        # Check if the value is valid
        if hide_nulls.lower().strip() not in valid_values:
            raise ValueError(
                f"Invalid value for 'hide_nulls': '{hide_nulls}'. Accepted values are: {', '.join(sorted(valid_values))} (case-insensitive). For more information on the command syntax, visit: {SYNTAX_DOC_URL}"
            )

    @staticmethod
    def validate_csv(values: Optional[str]):
        if values is not None:
            if not values or not isinstance(values, str):
                raise ValueError(
                    f"Value must be a string enclosed in double quotes. Use comma to separate multiple platform values. For more information on the command syntax, visit: {SYNTAX_DOC_URL}"
                )

    def validate_unstructured_query_for_additional_params(self):
        if (
            self.help
            or self.connectors
            or self.events
            or self.exclude_connectors
            or self.exclude_events
            or self.limit != -1
            or self.platforms
        ):
            raise ValueError(
                f"Only `search` param is supported with unstructured or natural query. Remove additional params in your query and try again."
            )

    # Make POST request to search URL and fetch results
    def get_api_results(
        self, payload: Dict[str, Any], headers: Dict[str, Any], timeout: float
    ) -> Generator[SplunkQBResponse, None, None]:
        cert_path = os.path.join(os.path.dirname(__file__), "../certs/fullchain.pem")
        try:
            verify = cert_path if os.path.isfile(cert_path) else True

            with requests.Session() as session:
                session.verify = verify
                session.headers.update(headers)
                self.logger.info(
                    f"PID {self.pid}: Making POST request to {self.search_url} with payload {payload} ..."
                )

                self._waiting_for_query_id = True

                with session.post(
                    self.search_url, stream=True, data=json.dumps(payload), timeout=(3.05, timeout + 2.0)
                ) as response:
                    self.logger.info(
                        f"PID {self.pid}: Received response in {response.elapsed} with status HTTP {response.status_code}"
                    )

                    query_id = response.headers.get("x-query-id")
                    trace_id = response.headers.get("x-amzn-trace-id")
                    self.logger.info(f"PID {self.pid}: response headers are: {response.headers}")
                    self.logger.info(f"PID {self.pid}: x-query-id: {response.headers.get('x-query-id')}")
                    self.logger.info(f"PID {self.pid}: x-amzn-trace-id: {trace_id}")

                    if response.status_code != 200:
                        error = extract_error(response)
                        yield SplunkQBResponse(statusCode=response.status_code, errors=[error])
                        return

                    self._query_id = query_id
                    self._waiting_for_query_id = False

                    for line in response.iter_lines(delimiter=b"\n", chunk_size=CHUNK_SIZE):
                        if line:
                            try:
                                parsed_data = json.loads(line)
                                assert isinstance(parsed_data, dict)
                                if "statusCode" in parsed_data and parsed_data["statusCode"] == 200:
                                    if "errors" in parsed_data and parsed_data["errors"]:
                                        yield SplunkQBResponse(
                                            statusCode=200, errors=parsed_data["errors"]
                                        )  # Yield platform errors coming in response from QB
                                    if "results" in parsed_data and parsed_data["results"]:
                                        yield SplunkQBResponse(
                                            statusCode=200, results=parsed_data["results"]
                                        )  # Yield valid JSON data coming in response from QB
                                else:
                                    yield SplunkQBResponse(
                                        statusCode=parsed_data["statusCode"], errors=parsed_data["errors"]
                                    )  # Yield Error coming in response
                            except json.JSONDecodeError as e:
                                self.logger.error(f"Error decoding chunk of response: {e}")
                            except AssertionError:
                                self.logger.error(f"Assertion error: Parsed data is not a dictionary")

        except requests.exceptions.RequestException as e:
            error_msg = f"API request to Search URL: {self.search_url} failed due to error: {str(e)}"
            self.logger.error(f"PID {self.pid}: {error_msg}", exc_info=True)
            self._waiting_for_query_id = False
            raise APIError(error_msg)

        self.logger.info(f"PID {self.pid}: API results fetched successfully, starting to yield the results...")

    # Helper function for executing the search API
    def execute_search(self, payload: Dict[str, Any], api_key: str) -> Generator[SplunkQBResponse, None, None]:
        headers = {
            "Content-Type": "application/json",
            "x-token-authorization": api_key,
        }
        search_results = self.get_api_results(payload, headers, DEFAULT_TIMEOUT)
        return search_results

    def construct_basic_help_message(self, _help: str) -> Generator[SplunkQBResponse, None, None]:
        """Returns the basic static help payload based on the sub-option.
        Allowed suboptions are:
            >>> `all`
            >>> `search`
        """

        if _help == "all":
            yield SplunkQBResponse(statusCode=200, results=HELP_ALL_PAYLOAD)
        else:
            yield SplunkQBResponse(statusCode=200, results=HELP_SEARCH_PAYLOAD)

    # Log error response with caller information and return the same
    def error_response(self, message: str):
        caller_info = inspect.stack()[1]  # Retrieve information about the immediate caller
        caller_name = caller_info.function
        caller_module = inspect.getmodule(caller_info.frame).__name__  # pyright: ignore[reportOptionalMemberAccess]
        line_number = caller_info.lineno

        full_message = f"PID {self.pid}: {message!r}. Called from {caller_module}.{caller_name} (Line {line_number})"
        self.logger.error(full_message)
        self.write_error(f"{message!r}")

    def cancel(self) -> None:
        try:
            if self._waiting_for_query_id:
                # If we have an request in flight, exiting before we get back the query ID means we cannot cancel, but
                # the query may still continue executing in the backend. So we'll wait a little before giving up.
                self.logger.info("Waiting for query to be submitted before cancelling")

                for _ in range(45):
                    if self._query_id is not None:
                        break
                    self.logger.info(".")
                    time.sleep(1.0)

            if self._api_key is not None and self._query_id is not None:
                cancel_query(self._api_key, self._query_id, self.logger)
                self.write_warning("Backend query cancelled")
            else:
                self.logger.info("No backend query to cancel")

        except Exception as exc:
            self.logger.exception("Could not cancel backend query")
            self.write_warning(f"Could not cancel backend query: {exc}")

    def get_results(self, search_payload, api_key) -> Generator[SplunkQBResponse, None, None]:
        """
        Fetch the results

        :param search_payload
        :param api_key

        :return: Generator to fetch the rows
        :rtype: Generator[SplunkQBResponse, None, None]
        """
        if self.help in ("all", "search") or (
            not self.search
            and not self.help
            and not self.events
            and not self.connectors
            and not self.exclude_events
            and not self.exclude_connectors
        ):
            # Invoke the construction of help message only if either help is set OR
            # NONE of search, help or events commands are set.
            return self.construct_basic_help_message(self.help)
        else:
            return self.execute_search(search_payload, api_key)

    def is_fsql_query_in_results(
        self, results: Generator[SplunkQBResponse, None, None], error_list: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Check if the response contains `_fsql_query`, which indicates that the user
        made an unstructured/natural query search. SQB responds with a valid fsql query
        which then app uses to re-request for FSQL query to fetch results.

        :param results
        :type results: Generator[SplunkQBResponse, None, None]
        :return: Valid fsql query if found else empty string
        :rtype: str
        """
        for row in flatten_results_and_collect_errors(results, error_list):
            # Return if the result contains only one row and that row has `_fsql_query` key
            return (row.get("_fsql_query", ""), error_list)

        # If no rows, then return empty string
        return ("", error_list)

    @classmethod
    def is_fsql_query(cls, query: str) -> bool:
        """Detect whether the user typed FSQL directly (e.g. `QUERY *.* WITH ...`).

        FSQL queries should bypass the natural-language agent entirely and be sent
        to SQB with `is_fsql=True`..
        """
        if not query or not isinstance(query, str):
            return False
        return cls._FSQL_PATTERN.match(query) is not None

    @classmethod
    def is_structured_query(cls, query: str) -> bool:
        """Determine if a query is structured (key=value format) or natural language.

        Uses a precompiled regex pattern for optimal performance when called repeatedly.

        Structured queries follow the pattern:
        - * (wildcard to match everything)
        - key = value or key = 'value'
        - key != value
        - key IN (val1, val2, 'val3')
        - NOT key = value or NOT key IN (val1, val2)
        - Multiple conditions with AND/OR connectives or implicit AND (space-separated)
        - Supports wildcards in values: *, *abc, abc*, *abc*

        Returns:
            True if the query is structured, False if it's natural language
        """
        if not query or not isinstance(query, str):
            return False

        query = query.strip()

        # Special case: standalone asterisk means "match everything"
        if query == "*":
            return True

        # Use precompiled pattern for better performance
        return cls._STRUCTURED_PATTERN.match(query) is not None

    def generate(self):
        self.logger.info(f"PID {self.pid}: Starting a new search.")
        self.logger.info(f"PID {self.pid}: STAGE is {STAGE}")
        self.logger.info(f"PID {self.pid}: search query is {self.search}")
        self.logger.info(f"PID {self.pid}: value of help option is {self.help}")
        self.logger.info(f"PID {self.pid}: platforms list is {self.platforms}")
        self.logger.info(f"PID {self.pid}: exclude connectors list is {self.exclude_connectors}")
        self.logger.info(f"PID {self.pid}: events is {self.events}")
        self.logger.info(f"PID {self.pid}: exclude_events is {self.exclude_events}")
        self.logger.info(f"PID {self.pid}: hide_nulls is {self.hide_nulls}")

        cancel = SplunkCancelCallback(self, self.cancel)
        cancel.watch()

        try:
            self.validate_search_params(
                self.search, self.help, self.events, self.exclude_events, self.connectors, self.exclude_connectors
            )
            self.validate_help_and_sub_options(
                self.help,
                self.platforms,
                self.connectors,
                self.exclude_connectors,
                self.events,
                self.exclude_events,
            )
            self.validate_csv(self.platforms)
            self.validate_csv(self.connectors)
            self.validate_csv(self.exclude_connectors)
            self.validate_csv(self.events)
            self.validate_csv(self.exclude_events)
            self.validate_hide_nulls(self.hide_nulls)
            self.validate_limit(self.limit)
            self.validate_include_and_exclude(self.events, self.exclude_events, "events", "exclude_events")
            self.validate_include_and_exclude(
                self.platforms, self.exclude_connectors, "platforms", "exclude_connectors"
            )
            self.validate_include_and_exclude(
                self.connectors, self.exclude_connectors, "connectors", "exclude_connectors"
            )
            self.validate_include_and_exclude(self.connectors, self.platforms, "connectors", "platforms")
        except ValueError as e:
            self.error_response(str(e))
            return

        if self._record_writer:
            self._record_writer._maxresultrows = MAXRESULT_ROWS_INITIAL

        if isinstance(self.logger, dict):
            return self.error_response(str(self.logger["Error"]))

        api_key = retrieve_password(self, API_KEY_REALM, API_KEY_USERNAME)
        self._api_key = api_key

        if not (api_key):
            error_message = "Query API Key not found in the configuration. Please complete the app setup."
            return self.error_response(error_message)

        proxy_server = retrieve_password(self, PROXY_REALM, PROXY_USERNAME)
        if proxy_server:
            self.logger.info(f"PID {self.pid}: proxy server is {proxy_server}")
            os.environ["HTTP_PROXY"] = proxy_server
            os.environ["HTTPS_PROXY"] = proxy_server

        _is_fsql_query = self.is_fsql_query(self.search)
        _is_structured_query = self.is_structured_query(self.search)

        # Connector / event lists are sent as JSON arrays so that names
        # containing a comma (e.g. "Acme, Inc.") round-trip unambiguously.
        # SQB still accepts legacy CSV on these fields, so older backend
        # deployments stay compatible during the rollout.
        search_payload: dict[str, Any] = {
            "query": self.search,
            "help": self.help,
            "events": parse_csv_option(self.events),
            "platforms": parse_csv_option(self.platforms or self.connectors),
            "exclude_events": parse_csv_option(self.exclude_events),
            "exclude_platforms": parse_csv_option(self.exclude_connectors),
            "remove_unpopulated": self.hide_nulls,
            # TODO: during the SQB FSQL-migration rollout we send both the
            # legacy `is_structured_query` and the new (inverted-polarity)
            # `needs_nl_translation` fields. Each SQB handler reads only its
            # own field and ignores the other. Once SQB drops the legacy
            # handler, the four legacy fields below can be removed.
            #
            # FSQL inputs flip both flags to "structured / no NL" so SQB's
            # legacy router doesn't fall into the natural-language agent path.
            "is_structured_query": _is_structured_query or _is_fsql_query,
            "needs_nl_translation": not _is_structured_query and not _is_fsql_query,
            "limit": int(self.limit),
            "splunk_username": self.metadata.searchinfo.username,  # pyright: ignore
        }
        if _is_fsql_query:
            search_payload["is_fsql"] = True

        try:
            if self.search_results_info:
                search_payload.update(
                    {
                        "start_time": epoch_to_iso8601((self.search_results_info.__dict__)["search_et"]),
                        "end_time": epoch_to_iso8601((self.search_results_info.__dict__)["search_lt"]),
                    }
                )
        except Exception as e:
            # Search for the last two years
            self.logger.info(f"PID {self.pid}: Adding time range as the last 2 years.")
            two_years_ago_iso = (datetime.now() - timedelta(days=365 * 2)).isoformat()
            current_iso = datetime.now().isoformat()
            search_payload.update({"start_time": two_years_ago_iso, "end_time": current_iso})

        yielded_rows = 0
        try:
            results = self.get_results(search_payload, api_key)

            fsql_errors: List[str] = []
            if self.search and not _is_structured_query and not _is_fsql_query:
                # Restrict other params
                self.validate_unstructured_query_for_additional_params()

                # Process the help sub-command as usual
                # The unstructured to fsql query check only needs to be done
                # for search sub-command.
                _fsql_query, fsql_errors = self.is_fsql_query_in_results(results, fsql_errors)
                if _fsql_query:
                    # This could be a natural language, hence request SQB
                    # to check if the response contains a _fsql_query.
                    # If yes, then re-request SQB with is_fsql set to True.
                    # If fsql query found in the response
                    # then set the params to enable FSQL mode
                    # and re-request SQB.
                    search_payload["is_fsql"] = True
                    search_payload["query"] = _fsql_query

                    # Since the FSQL query is now found, disable the
                    # unstructured query by setting the `is_structured_query`
                    # to True. However, `is_fsql` set to True means, it'll be treated as
                    # FSQL search at SQB. While this step is unnecessary, but it is meaningful
                    # to set this to True.
                    search_payload["is_structured_query"] = True
                    # We already have the translated FSQL in hand,
                    # so the second request must not route back through the NL
                    # agent. Legacy handler reads `is_structured_query`; new
                    # handler reads `needs_nl_translation`.
                    search_payload["needs_nl_translation"] = False

                    # write this FSQL query to UI warnings.
                    self.write_warning(f"FSQL Query: {_fsql_query}")

                    # Make another request to SQB
                    results = self.get_results(search_payload, api_key)

            max_rows_increased = False
            self.errors: List[str] = [*fsql_errors]

            for row in flatten_results_and_collect_errors(results, self.errors):
                yield row
                yielded_rows += 1

                if yielded_rows % 1000 == 0:
                    self.logger.info(f"PID {self.pid}: Yielded {yielded_rows} records so far.")

                if not max_rows_increased and yielded_rows > MAXRESULT_ROWS_THRESHOLD:
                    self._record_writer._maxresultrows = (  # pyright: ignore[reportOptionalMemberAccess]
                        MAXRESULT_ROWS_AFTER_THRESHOLD
                    )
                    self.logger.info(
                        f"PID {self.pid}: Increased _maxresultrows to {MAXRESULT_ROWS_AFTER_THRESHOLD} after yielding {yielded_rows} rows."
                    )
                    max_rows_increased = True

            self.logger.info(f"PID {self.pid}: Search results yielding completed.")
        except APIError as e:
            # Handle the APIError exception and show the error accordingly.
            self.logger.error(f"PID {self.pid}: Exception {type(e)} occurred - {str(e)}", exc_info=True)
            error_message = f"API Error: {str(e)}"
            self.errors.append(error_message)

        except Exception as e:
            error_message = f"Unexpected Error: {str(e)}"
            self.errors.append(error_message)

        self.logger.info(f"PID {self.pid}: Errors reported while performing search. Errors - {self.errors}")

        # splunklib's write_warning/write_error call .format() on the message,
        # which raises KeyError on literal '{...}' substrings (e.g. pyparsing
        # grammar dumps in FSQL backend errors). Escape braces before writing.
        if yielded_rows > 0:
            for error in self.errors:
                self.write_warning(error.replace("{", "{{").replace("}", "}}"))
        else:
            for error in self.errors:
                self.write_error(error.replace("{", "{{").replace("}", "}}"))

        self.logger.info(f"PID {self.pid}: Search completed.")


dispatch(QueryAISearch, sys.argv, sys.stdin, sys.stdout, __name__)

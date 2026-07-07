import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

from types import ModuleType
from typing import Any, Dict, List, Iterator, Optional, Generator, cast
from datetime import datetime, timedelta
import json
import time
import inspect
import logging

from utils import (
    SplunkCancelCallback,
    cancel_query,
    extract_error,
    epoch_to_iso8601,
    extract_fsql_args_from_raw_search,
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
from splunklib.searchcommands import Configuration, GeneratingCommand, dispatch
import requests

STAGE = os.getenv("APP_ENVIRONMENT", "PROD")
SQB_ENDPOINT = (
    f"https://api.{STAGE}.query.ai/search/translation/splunk"
    if STAGE in ("dev", "test")
    else "https://api.query.ai/search/translation/splunk"
)

DEFAULT_TIMEOUT = 480  # 8 mins
SYNTAX_DOC_URL = "https://docs.query.ai/docs/running-fsql-from-splunk"
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
class QueryAIFSQLSearch(GeneratingCommand):
    splunk_module: Optional[ModuleType] = None
    errors: List[str] = []
    if STAGE in ("dev", "test", "PROD"):
        import splunk  # type: ignore

        splunk_module = splunk
        logger: logging.Logger = setup_logging(splunk_module, "fsql")

    pid = str(os.getpid())
    search_url = SQB_ENDPOINT

    _waiting_for_query_id: bool = False
    _query_id: Optional[str] = None
    _api_key: Optional[str] = None

    def _protocol_v2_option_parser(self, arg):
        """DO NOT REMOVE THIS OVERRIDDEN METHOD.
        Override to treat all arguments as positional (no option parsing).
        It is mainly required because for fsql_query in `| fsql <fsql_query>`,
        that contains equals `=` operator, base method is used to parse Option/Value
        pairs in the query. It directly splits the query on `=` and leads to issues
        because in fsql, we need to read `=` as part of the fsql query string rather
        treating it special.
        """
        # Return the argument as a single item list to treat it as positional
        return [arg]

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
                    f"[FSQL] PID {self.pid}: Making POST request to {self.search_url} with payload {payload} ..."
                )

                self._waiting_for_query_id = True

                with session.post(
                    self.search_url, stream=True, data=json.dumps(payload), timeout=(3.05, timeout + 2.0)
                ) as response:
                    self.logger.info(
                        f"[FSQL] PID {self.pid}: Received response in {response.elapsed} with status HTTP {response.status_code}"
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
            self.logger.error(f"[FSQL] PID {self.pid}: {error_msg}", exc_info=True)
            self._waiting_for_query_id = False
            raise APIError(error_msg)

        self.logger.info(f"[FSQL] PID {self.pid}: API results fetched successfully, starting to yield the results...")

    # Helper function for executing the FSQL API
    def execute_fsql_search(self, payload: Dict[str, Any], api_key: str) -> Generator[SplunkQBResponse, None, None]:
        headers = {
            "Content-Type": "application/json",
            "x-token-authorization": api_key,
        }
        self.logger.info(f"[FSQL] PID {self.pid}: Executing FSQL search with payload: {payload}")
        search_results = self.get_api_results(payload, headers, DEFAULT_TIMEOUT)
        return search_results

    # Log error response with caller information and return the same
    def error_response(self, message: str):
        caller_info = inspect.stack()[1]  # Retrieve information about the immediate caller
        caller_name = caller_info.function
        caller_module = inspect.getmodule(caller_info.frame).__name__  # pyright: ignore[reportOptionalMemberAccess]
        line_number = caller_info.lineno

        full_message = (
            f"[FSQL] PID {self.pid}: {message!r}. Called from {caller_module}.{caller_name} (Line {line_number})"
        )
        self.logger.error(full_message)
        self.write_error(f"{message!r}")

    def get_fsql_query_from_cmdline(self) -> Optional[str]:
        """Construct fsql query from string provided after `| fsql` command"""
        # 1. Splunk splits command on spaces unless quoted
        parts: List[str] = []
        parts = getattr(self, "fieldnames", None) or parts
        if not parts:
            searchinfo = getattr(self.metadata, "searchinfo", None)
            parts = cast(List[str], getattr(searchinfo, "args", [])) if searchinfo else []

        # Quoted query appears as single part -> return directly
        if len(parts) == 1:
            return parts[0]

        # 2. Unquoted: reconstruct from raw search string
        raw_search = None
        searchinfo = getattr(self.metadata, "searchinfo", None)
        # searchinfo has below structure for unquoted fsql query such as: | fsql QUERY inventory_info.message, inventory_info.time
        # searchinfo: {'args': ['QUERY', 'inventory_info.message', 'inventory_info.time'], 'raw_args': ['QUERY', 'inventory_info.message', 'inventory_info.time'],
        # 'dispatch_dir': '...', 'sid': '...', 'app': 'search', 'owner': '...', 'username': '...', 'session_key': '...', 'splunkd_uri': 'https://splunk_host:port', 'splunk_version': '9.1.1',
        # 'search': '| fsql QUERY inventory_info.message, inventory_info.time', 'command': 'fsql', 'maxresultrows': ..., 'earliest_time': ..., 'latest_time': ...}
        if searchinfo:
            raw_search = getattr(searchinfo, "search", None)

        if raw_search:
            # Capture args after '| fsql', stopping at the next pipe stage so
            # downstream commands (e.g. `| queryagent ...`) aren't sent to SQB.
            arg = extract_fsql_args_from_raw_search(raw_search)
            if arg is not None:
                return arg

        if not parts:
            error_message = (
                f"Unable to read FSQL query. Provide a valid query after '| fsql'. Syntax docs: {SYNTAX_DOC_URL}"
            )
            return self.error_response(error_message)

        # 3. last resort - join split parts with spaces (may be incorrect as it removes commas etc)
        return " ".join(parts)

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

    def generate(self):
        assert self.logger is not None
        cancel = SplunkCancelCallback(self, self.cancel)
        cancel.watch()

        self.logger.info(f"[FSQL] PID {self.pid}: Starting a new search.")
        self.logger.info(f"[FSQL] PID {self.pid}: STAGE is {STAGE}")

        # Fetch and LOG the FSQL query
        self.fsql = self.get_fsql_query_from_cmdline()
        self.logger.info(f"[FSQL] PID {self.pid}: search query is {self.fsql}")

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
            self.logger.info(f"[FSQL] PID {self.pid}: proxy server is {proxy_server}")
            os.environ["HTTP_PROXY"] = proxy_server
            os.environ["HTTPS_PROXY"] = proxy_server

        search_payload: dict[str, Any] = {"query": self.fsql, "is_fsql": True}

        # Add the time window
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
            self.logger.info(f"[FSQL] PID {self.pid}: Adding time range as the last 2 years.")
            two_years_ago_iso = (datetime.now() - timedelta(days=365 * 2)).isoformat()
            current_iso = datetime.now().isoformat()
            search_payload.update({"start_time": two_years_ago_iso, "end_time": current_iso})

        yielded_rows = 0
        try:
            results = []
            results = self.execute_fsql_search(search_payload, api_key)

            max_rows_increased = False
            self.errors: List[str] = []

            for row in flatten_results_and_collect_errors(results, self.errors):
                yield row
                yielded_rows += 1

                if yielded_rows % 1000 == 0:
                    self.logger.info(f"[FSQL] PID {self.pid}: Yielded {yielded_rows} records so far.")

                if not max_rows_increased and yielded_rows > MAXRESULT_ROWS_THRESHOLD:
                    self._record_writer._maxresultrows = (  # pyright: ignore[reportOptionalMemberAccess]
                        MAXRESULT_ROWS_AFTER_THRESHOLD
                    )
                    self.logger.info(
                        f"[FSQL] PID {self.pid}: Increased _maxresultrows to {MAXRESULT_ROWS_AFTER_THRESHOLD} after yielding {yielded_rows} rows."
                    )
                    max_rows_increased = True

            self.logger.info(f"[FSQL] PID {self.pid}: Search results yielding completed.")
        except APIError as e:
            # Handle the APIError exception and show the error accordingly.
            self.logger.error(f"[FSQL] PID {self.pid}: Exception {type(e)} occurred - {str(e)}", exc_info=True)
            error_message = f"API Error: {str(e)}"
            self.errors.append(error_message)

        except Exception as e:
            error_message = f"Unexpected Error: {str(e)}"
            self.errors.append(error_message)

        self.logger.info(f"[FSQL] PID {self.pid}: Errors reported while performing search. Errors - {self.errors}")

        if yielded_rows > 0:
            for error in self.errors:
                self.write_warning(error)
        else:
            for error in self.errors:
                self.write_error(error)

        self.logger.info(f"[FSQL] PID {self.pid}: Search completed.")


dispatch(QueryAIFSQLSearch, sys.argv, sys.stdin, sys.stdout, __name__)

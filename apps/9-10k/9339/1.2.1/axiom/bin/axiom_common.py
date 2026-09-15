#!/usr/bin/env python
# coding=utf-8

import os
import re
import signal
import sys
import uuid
import json
from collections.abc import MutableMapping
from datetime import datetime, timezone
from time import sleep
from typing import List, Optional, Tuple
from urllib.parse import quote

import requests
import splunk.mining.dcutils as dcu

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client
from splunklib4data.relative_time_calculator import RelativeTimeCalculator


DEFAULT_API_BASE_URL = "https://api.axiom.co"
DEFAULT_MGMT_PORT = 8089
DEFAULT_TOKEN_NAME = "axiom_token"
DEFAULT_SOURCE = "axquery.py"
DEFAULT_SOURCETYPE = "axiom_query:json"
DEFAULT_HOST = "api.axiom.co"
DEFAULT_HTTP_TIMEOUT = (5, 60)
DEFAULT_MAX_RETRIES = 2
APL_SOURCE = "splunkapp"
# Axiom names the one-row aggregate table that accompanies a bucketed summarize.
TOTALS_TABLE_NAME = "_totals"
MAX_RETRY_DELAY_SECONDS = 5
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
SENSITIVE_LOG_PATTERNS = (
    (re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE), "Bearer <redacted>"),
    (re.compile(r"xaat-[A-Za-z0-9._~+/=-]+"), "xaat-<redacted>"),
)


class AxiomApiError(RuntimeError):
    """Raised for Axiom API failures that should be visible to Splunk users."""


class AxiomQueryCompileError(ValueError):
    """Raised when Splunk-shaped query input cannot be compiled safely to APL."""


def dict_to_kv_str(d):
    """Convert a dictionary to a comma-separated key=value string for logs."""
    return ", ".join([f"{t[0]}={t[1]}" for t in d.items()])


def redact_sensitive(value):
    """Redact token-shaped values before they reach Splunk logs or errors."""
    text = str(value)
    for pattern, replacement in SENSITIVE_LOG_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def dict_to_log_kv_str(d):
    """Convert a dictionary to Splunk-friendly comma-separated key=value log fields."""
    return ", ".join(
        f"{log_field_name(key)}={log_field_value(value)}"
        for key, value in d.items()
    )


def log_field_name(key):
    """Return a field name Splunk can extract without relying on key normalization."""
    return re.sub(r"[^A-Za-z0-9_]", "_", str(key)).strip("_")


def log_field_value(value):
    """Return a parseable log value, quoting values that contain separators."""
    if value is None:
        return "None"

    text = str(value)
    if text == "":
        return '""'
    if re.search(r"[\s,=\"]", text):
        return json.dumps(text)
    return text


def flatten_dict(dictionary, parent_key="", separator="."):
    """Recursively flatten a nested dictionary using dotted compound keys."""
    items = []
    for key, value in dictionary.items():
        new_key = parent_key + separator + key if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(flatten_dict(value, parent_key=new_key, separator=separator).items())
        elif isinstance(value, list):
            for index, nested_value in enumerate(value):
                items.extend(
                    flatten_dict({str(index): nested_value}, parent_key=new_key, separator=separator).items()
                )
        else:
            items.append((new_key, value))
    return dict(items)


def flatten_row_for_splunk(row, parent_key="", separator="."):
    """Flatten an Axiom row into Splunk fields with the same shape ``spath`` produces.

    Nested objects become dotted compound keys, so ``{"attributes": {"http": ...}}``
    yields ``attributes.http.method``. Arrays are exploded the way ``spath`` /
    ``KV_MODE = json`` name them: the key gains a ``{}`` suffix and every element is
    collected into a multivalue field. Scalar arrays yield ``key{}`` (``email.to`` ->
    ``email.to{}``); arrays of objects yield ``key{}.subfield`` (``answers`` ->
    ``answers{}.rdata``). This keeps events synthesised by a generating command
    byte-for-byte consistent with the same OCSF data indexed and read back through
    ``spath`` -- so props-based knowledge (e.g. the OCSF CIM add-on's calculated
    fields, which reference ``'answers{}.rdata'``) resolves identically on both.

    Differs from :func:`flatten_dict`, which expands lists into numeric-index keys and
    is kept as-is for the status and response-header paths that rely on that behavior.
    """
    items = {}

    def add(name, value):
        # Repeated names come from sibling array elements: collect as multivalue,
        # matching how splunklib and spath represent ``key{}`` fields.
        if name in items:
            current = items[name]
            if not isinstance(current, list):
                current = [current]
            current.append(value)
            items[name] = current
        else:
            items[name] = value

    def walk(node, name):
        if isinstance(node, MutableMapping):
            for key, value in node.items():
                walk(value, name + separator + key if name else key)
        elif isinstance(node, (list, tuple)):
            for element in node:
                walk(element, name + "{}")
        else:
            add(name, node)

    walk(row or {}, parent_key)
    return items


class SplunkContext:
    """Helpers for Splunk runtime metadata and management API access."""

    @staticmethod
    def get_mgmt_port(job_id, dcu_module=dcu, logger=None):
        port = DEFAULT_MGMT_PORT
        try:
            port = int(dcu_module.splunk.getLocalServerInfo().split(":").pop().strip())
        except Exception as e:
            if logger:
                logger.warning(
                    f"jobId={job_id}, unable to determine management port automatically, due to: {e}"
                )
        return port

    @staticmethod
    def get_searchinfo(command):
        return getattr(getattr(command, "_metadata", None), "searchinfo", None)

    @staticmethod
    def get_dispatch_time_range(command):
        searchinfo = SplunkContext.get_searchinfo(command)
        if not searchinfo:
            return (None, None)

        return (
            SplunkContext._positive_epoch(getattr(searchinfo, "earliest_time", None)),
            SplunkContext._positive_epoch(getattr(searchinfo, "latest_time", None)),
        )

    @staticmethod
    def _positive_epoch(value):
        try:
            epoch = float(value)
        except (TypeError, ValueError):
            return None
        return epoch if epoch > 0 else None


class CredentialStore:
    """Fetch Axiom API tokens from Splunk storage/passwords."""

    def __init__(self, client_module=client, logger=None, command_name=None):
        self.client_module = client_module
        self.logger = logger
        self.command_name = command_name

    def log_prefix(self, job_id):
        prefix = f"jobId={job_id}"
        if self.command_name:
            prefix += f", command={self.command_name}"
        return prefix

    def get_token(self, searchinfo, token_name, mgmt_port, job_id):
        app_names = [searchinfo.app]

        last_error = None
        for app_name in app_names:
            try:
                service = self.client_module.Service(
                    token=searchinfo.session_key,
                    owner=searchinfo.owner,
                    app=app_name,
                    port=mgmt_port,
                )
                credentials = service.storage_passwords
                for credential in credentials:
                    if credential.username == token_name:
                        if self.logger:
                            self.logger.debug(
                                f"{self.log_prefix(job_id)}, axiom_token_retrieval=successful, app={app_name}"
                            )
                        return credential.clear_password
            except Exception as e:
                last_error = e
                if self.logger:
                    self.logger.warning(
                        f"{self.log_prefix(job_id)}, axiom_token_lookup_failed_for_app={app_name}, error={redact_sensitive(e)}"
                    )

        if last_error:
            if self.logger:
                self.logger.error(f"{self.log_prefix(job_id)}, axiom_token_retrieval={redact_sensitive(last_error)}")
            raise last_error

        raise ValueError(
            f'axiom_token_name={token_name}, axiom_token_retrieval="not found in Splunk storage/passwords."'
        )


class AxiomCommandRuntimeMixin:
    """Shared runtime plumbing for Splunk custom command classes.

    The mixin resolves logger/client/requests modules from the command module at
    call time so tests and Splunk runtime patching still work at module level.
    """

    def command_module(self):
        return sys.modules[self.__module__]

    def module_logger(self):
        return getattr(self.command_module(), "logger", None)

    def module_dcu(self):
        return getattr(self.command_module(), "dcu", dcu)

    def module_client(self):
        return getattr(self.command_module(), "client", client)

    def module_requests(self):
        return getattr(self.command_module(), "requests", requests)

    def get_command_name(self):
        configured_name = getattr(self, "command_name", None)
        if configured_name:
            return configured_name
        return self.__class__.__name__.lower()

    def log_prefix(self):
        return f"jobId={self.job_id}, command={self.get_command_name()}"

    def initialize_runtime(self, create_session=True, install_signal_handlers=True):
        self.job_id = str(uuid.uuid1())
        self.exit_requested = False
        if create_session:
            self.session = self.module_requests().Session()
        if install_signal_handlers:
            self.install_signal_handlers()

    def install_signal_handlers(self):
        signal.signal(signal.SIGTERM, self.handle_exit)
        signal.signal(signal.SIGHUP, self.handle_exit)
        signal.signal(signal.SIGINT, self.handle_exit)

    def handle_exit(self, signum, frame):
        self.exit_requested = True

    def get_mgmt_port(self):
        return SplunkContext.get_mgmt_port(
            self.job_id,
            dcu_module=self.module_dcu(),
            logger=self.module_logger(),
        )

    def get_axiom_token(self):
        return CredentialStore(
            client_module=self.module_client(),
            logger=self.module_logger(),
            command_name=self.get_command_name(),
        ).get_token(
            SplunkContext.get_searchinfo(self),
            self.tokenName,
            self.mgmtPort,
            self.job_id,
        )

    def resolve_query_time_range(self):
        return TimeRangeResolver.resolve_for_command(
            self,
            start_time=getattr(self, "startTime", None),
            end_time=getattr(self, "endTime", None),
            earliest=getattr(self, "earliest", None),
            latest=getattr(self, "latest", None),
        )

    def axiom_client(self, session=None):
        return AxiomClient(
            session or getattr(self, "session", None),
            logger=self.module_logger(),
            command_name=self.get_command_name(),
        )

    def post_to_axiom(self, apl, startTime, endTime, axiom_token, cursor=None):
        return self.axiom_client().query_apl(
            apl,
            startTime,
            endTime,
            axiom_token,
            cursor=cursor,
            job_id=self.job_id,
        )

    def get_axiom_datasets(self, token):
        session = self.module_requests().Session()
        return self.axiom_client(session).list_datasets(token, job_id=self.job_id)

    def get_axiom_fields(self, token):
        session = self.module_requests().Session()
        return self.axiom_client(session).list_fields(
            self.dataset,
            token,
            job_id=self.job_id,
        )


class TimeRangeResolver:
    """Normalize Splunk and command time ranges to Axiom RFC3339 strings."""

    TIME_PATTERN1 = re.compile(
        r"^"
        r"\d{4}-\d{2}-\d{2}T"
        r"\d{2}:\d{2}:\d{2}"
        r"(?:\.\d{3,9})?Z"
        r"$"
    )

    TIME_PATTERN2 = re.compile(
        r"""
        ^(?:
            [-+]
            (?:\d+)?
            (?:yrs|yr|years|year|y|weeks|week|w|secs|seconds|second|sec|s|quarters|quarter|qtrs|qtr|q|months|month|mon|minutes|minute|mins|min|m|hrs|hr|hours|hour|h|days|day|d)
            (?:
                @(?:yrs|yr|years|year|y|secs|seconds|second|sec|s|quarters|quarter|qtrs|qtr|q|months|month|mon|minutes|minute|mins|min|m|hrs|hr|hours|hour|h|days|day|d)$
                |@(?:weeks|week|w)(?:[0-7])?$
                |$
            )
            |
            (?:
                @(?:yrs|yr|years|year|y|secs|seconds|second|sec|s|quarters|quarter|qtrs|qtr|q|months|month|mon|minutes|minute|mins|min|m|hrs|hr|hours|hour|h|days|day|d)$
                |@(?:weeks|week|w)(?:[0-7])?$
                |$
            )
        )
    """,
        re.VERBOSE,
    )

    RFC3339_RE = re.compile(
        r"^(\d{4})-(\d{2})-(\d{2})T"
        r"(\d{2}):(\d{2}):(\d{2})"
        r"(?:\.(\d{1,9}))?"
        r"(Z|[+-]\d{2}:\d{2})$"
    )

    @classmethod
    def validate_time_arg(cls, timestring: str, arg_name: str) -> str:
        if not timestring:
            raise ValueError(f"{arg_name} cannot be empty")

        if timestring == "now":
            return cls.epoch_to_rfc3339(datetime.now(tz=timezone.utc).timestamp())

        if cls.TIME_PATTERN1.match(timestring):
            return timestring

        if cls.TIME_PATTERN2.match(timestring):
            rtc = RelativeTimeCalculator()
            try:
                timestamp = rtc.parse_and_calculate(timestring)
            except ValueError as e:
                raise ValueError(
                    f"Invalid relative time for {arg_name}: {timestring!r} ({e})"
                ) from e

            return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        raise ValueError(
            f"Invalid {arg_name} format: {timestring!r}. "
            "Expected RFC3339 (YYYY-MM-DDTHH:MM:SSZ) or supported relative time."
        )

    @classmethod
    def resolve_for_command(
        cls,
        command,
        start_time=None,
        end_time=None,
        earliest=None,
        latest=None,
    ) -> Tuple[Optional[str], Optional[str]]:
        resolved_start = cls._resolve_start(command, start_time, earliest)
        resolved_end = cls._resolve_end(command, end_time, latest)
        return (resolved_start, resolved_end)

    @classmethod
    def _resolve_start(cls, command, start_time, earliest):
        if start_time:
            return cls.validate_time_arg(start_time, "startTime")
        if earliest:
            return cls.validate_time_arg(earliest, "earliest")

        dispatch_start, _ = SplunkContext.get_dispatch_time_range(command)
        if dispatch_start is not None:
            return cls.epoch_to_rfc3339(dispatch_start)
        return None

    @classmethod
    def _resolve_end(cls, command, end_time, latest):
        if end_time:
            return cls.validate_time_arg(end_time, "endTime")
        if latest:
            return cls.validate_time_arg(latest, "latest")

        _, dispatch_end = SplunkContext.get_dispatch_time_range(command)
        if dispatch_end is not None:
            return cls.epoch_to_rfc3339(dispatch_end)
        return None

    @staticmethod
    def epoch_to_rfc3339(epoch_seconds) -> str:
        dt = datetime.fromtimestamp(float(epoch_seconds), tz=timezone.utc)
        if dt.microsecond:
            return dt.isoformat(timespec="microseconds").replace("+00:00", "Z")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @classmethod
    def rfc3339_to_ns(cls, ts: str) -> int:
        m = cls.RFC3339_RE.match(ts)
        if not m:
            raise ValueError(f"Invalid RFC3339 timestamp: {ts}")

        if ts.endswith("Z"):
            base, tz = ts[:-1], "Z"
        else:
            i = max(ts.rfind("+"), ts.rfind("-"))
            base, tz = (ts[:i], ts[i:]) if i >= 10 else (ts, "Z")

        whole, frac = (base.split(".", 1) + [""])[:2]
        iso = whole + (f".{(frac + '000000')[:6]}" if frac else "") + ("" if tz == "Z" else tz)
        dt = datetime.fromisoformat(iso)
        if tz == "Z":
            dt = dt.replace(tzinfo=timezone.utc)

        sec_ns = int(dt.timestamp()) * 1_000_000_000
        if frac:
            digits = "".join(ch for ch in frac if ch.isdigit())
            frac_ns = int((digits + "000000000")[:9])
        else:
            frac_ns = 0
        return sec_ns + frac_ns

    @staticmethod
    def ns_to_rfc3339(ns: int) -> str:
        sec, frac_ns = divmod(ns, 1_000_000_000)
        dt = datetime.fromtimestamp(sec, tz=timezone.utc)
        return f"{dt.replace(microsecond=0).isoformat().replace('+00:00','Z')[:-1]}.{frac_ns:09d}Z"

    @classmethod
    def rfc3339_to_epoch_microseconds(cls, ts: str) -> str:
        ns = cls.rfc3339_to_ns(ts)
        ns_str = str(ns)
        return ".".join((ns_str[:10], ns_str[10:16]))


class AxiomClient:
    """HTTP client for the Axiom API endpoints used by the Splunk commands."""

    def __init__(
        self,
        session=None,
        logger=None,
        api_base_url=DEFAULT_API_BASE_URL,
        max_retries=DEFAULT_MAX_RETRIES,
        command_name=None,
    ):
        self.session = session or requests.Session()
        self.logger = logger
        self.api_base_url = api_base_url.rstrip("/")
        self.max_retries = max_retries
        self.command_name = command_name

    def log_prefix(self, job_id):
        prefix = f"jobId={job_id}"
        if self.command_name:
            prefix += f", command={self.command_name}"
        return prefix

    def query_apl(self, apl, start_time, end_time, token, cursor=None, job_id=None):
        url = f"{self.api_base_url}/v1/datasets/_apl?format=tabular&apl-source={APL_SOURCE}"
        payload = {"apl": apl}
        if start_time:
            payload["startTime"] = start_time
        if end_time:
            payload["endTime"] = end_time
        if cursor:
            payload["cursor"] = cursor

        if self.logger:
            self.logger.debug(f'{self.log_prefix(job_id)}, url="{url}", payload={payload}')

        return self._request(
            "post",
            url,
            token,
            job_id=job_id,
            json=payload,
            accept_encoding="zstd",
            timeout=DEFAULT_HTTP_TIMEOUT,
        )

    def list_datasets(self, token, job_id=None):
        url = f"{self.api_base_url}/v2/datasets"
        return self._request(
            "get",
            url,
            token,
            job_id=job_id,
            accept_encoding="gzip",
            timeout=DEFAULT_HTTP_TIMEOUT,
        )

    def list_fields(self, dataset_id, token, job_id=None):
        encoded_dataset = quote(dataset_id, safe="")
        url = f"{self.api_base_url}/v2/datasets/{encoded_dataset}/fields"
        return self._request(
            "get",
            url,
            token,
            job_id=job_id,
            accept_encoding="gzip",
            timeout=DEFAULT_HTTP_TIMEOUT,
        )

    def _request(self, method, url, token, job_id=None, accept_encoding="gzip", **kwargs):
        headers = {
            "Accept": "application/json",
            "Accept-encoding": accept_encoding,
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        attempt = 0
        request = getattr(self.session, method)

        while True:
            try:
                response = request(url, headers=headers, **kwargs)
            except requests.exceptions.Timeout as err:
                if self._should_retry_exception(attempt):
                    self._sleep_before_retry(None, attempt, job_id, "timeout")
                    attempt += 1
                    continue
                self._log_error(job_id, f"Axiom API request timed out after {attempt + 1} attempts")
                raise AxiomApiError(
                    f"Axiom API request timed out after {attempt + 1} attempts."
                ) from err
            except requests.exceptions.ConnectionError as err:
                self._log_error(job_id, f"Axiom API connection failed: {redact_sensitive(err)}")
                raise AxiomApiError("Axiom API connection failed. Check network access to api.axiom.co.") from err
            except requests.exceptions.RequestException as err:
                self._log_error(job_id, f"Axiom API request failed: {redact_sensitive(err)}")
                raise AxiomApiError(f"Axiom API request failed: {redact_sensitive(err)}") from err

            status_code = int(getattr(response, "status_code", 0) or 0)
            if status_code == 200:
                if self.logger:
                    self.logger.debug(f"{self.log_prefix(job_id)}, http_status={status_code}, http_msg=successful")
                return response

            self._log_response_body(response, job_id)
            if self._should_retry_response(response, attempt):
                self._sleep_before_retry(response, attempt, job_id, f"HTTP {status_code}")
                attempt += 1
                continue

            message = self._error_message(response)
            self._log_error(job_id, message)
            raise AxiomApiError(message)

    def _should_retry_exception(self, attempt):
        return attempt < self.max_retries

    def _should_retry_response(self, response, attempt):
        status_code = int(getattr(response, "status_code", 0) or 0)
        return status_code in RETRYABLE_STATUS_CODES and attempt < self.max_retries

    def _sleep_before_retry(self, response, attempt, job_id, reason):
        delay = self._retry_delay(response, attempt)
        if self.logger:
            self.logger.warning(
                f"{self.log_prefix(job_id)}, axiom_api_retry={attempt + 1}, reason={reason}, retry_after={delay}"
            )
        sleep(delay)

    @staticmethod
    def _retry_delay(response, attempt):
        retry_after = None
        if response is not None:
            retry_after = getattr(response, "headers", {}).get("Retry-After")

        try:
            delay = float(retry_after) if retry_after is not None else 2 ** attempt
        except (TypeError, ValueError):
            delay = 2 ** attempt

        return max(0, min(delay, MAX_RETRY_DELAY_SECONDS))

    def _log_error(self, job_id, message):
        if self.logger:
            self.logger.error(f"{self.log_prefix(job_id)}, {redact_sensitive(message)}")

    def _error_message(self, response):
        status_code = int(getattr(response, "status_code", 0) or 0)
        body = self._response_body(response)
        detail = f" Details: {body}" if body else ""

        if status_code in (401, 403):
            return (
                f"Axiom API authentication failed (HTTP {status_code}). "
                f"Check the Axiom API token configured in Splunk storage/passwords.{detail}"
            )
        if status_code == 404:
            return (
                "Axiom API resource not found (HTTP 404). "
                f"Check the dataset and field names used by the command.{detail}"
            )
        if status_code == 429:
            return (
                "Axiom API rate limit exceeded (HTTP 429). "
                f"Retry later or reduce the requested data volume.{detail}"
            )
        return f"Axiom API request failed (HTTP {status_code}).{detail}"

    def _log_response_body(self, response, job_id):
        if self.logger:
            self.logger.debug(f"{self.log_prefix(job_id)}, resp_body={self._response_body(response)}")

    @staticmethod
    def _response_body(response):
        try:
            data = response.json()
            if isinstance(data, dict):
                return redact_sensitive(dict_to_kv_str(data))[:1024]
            return redact_sensitive(data)[:1024]
        except Exception:
            return redact_sensitive(getattr(response, "text", ""))[:1024]


class AplPipeline:
    """APL parsing and construction helpers."""

    FIELD_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    BRACKETED_FIELD_RE = re.compile(r"^\['((?:\\'|\\\\|[^'])+)'\]$")
    FIELD_NAME_RE = re.compile(r"^[A-Za-z_@%*][A-Za-z0-9_@.%*\-\[\]]*$")
    SIMPLE_ALIAS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    DURATION_RE = re.compile(r"^[1-9]\d*(?:ms|s|m|h|d)$")
    SPLUNK_FIELD_UNSAFE_RE = re.compile(r"[^A-Za-z0-9_]+")

    @staticmethod
    def split(query: str) -> List[str]:
        parts: List[str] = []
        buf: List[str] = []

        in_single_quote = False
        in_double_quote = False
        in_line_comment = False
        in_block_comment = False
        escape_next = False

        i = 0
        n = len(query)

        def flush_buffer():
            s = "".join(buf).strip()
            if s:
                parts.append(s)

        while i < n:
            ch = query[i]
            nxt = query[i + 1] if i + 1 < n else ""

            if in_line_comment:
                buf.append(ch)
                if ch == "\n":
                    in_line_comment = False
                i += 1
                continue

            if in_block_comment:
                buf.append(ch)
                if ch == "*" and nxt == "/":
                    buf.append(nxt)
                    in_block_comment = False
                    i += 2
                else:
                    i += 1
                continue

            if in_single_quote or in_double_quote:
                buf.append(ch)
                if escape_next:
                    escape_next = False
                elif ch == "\\":
                    escape_next = True
                elif in_double_quote and ch == '"':
                    in_double_quote = False
                elif in_single_quote and ch == "'":
                    in_single_quote = False
                i += 1
                continue

            if ch == "/" and nxt == "/":
                buf.append(ch)
                buf.append(nxt)
                in_line_comment = True
                i += 2
                continue

            if ch == "/" and nxt == "*":
                buf.append(ch)
                buf.append(nxt)
                in_block_comment = True
                i += 2
                continue

            if ch == '"':
                buf.append(ch)
                in_double_quote = True
                i += 1
                continue

            if ch == "'":
                buf.append(ch)
                in_single_quote = True
                i += 1
                continue

            if ch == "|":
                flush_buffer()
                buf = []
                i += 1
                continue

            buf.append(ch)
            i += 1

        flush_buffer()
        return parts

    @classmethod
    def get_sort_direction(cls, apl):
        apl_functions = cls.split(apl)
        sort_function_indices = [
            i for i, x in enumerate(apl_functions) if re.match(r"sort\s+by\s+_time(?:\s+(?:asc|desc))?$", x)
        ]
        if len(sort_function_indices) != 1:
            raise ValueError(
                'apl query must contain "| sort by \'_time\'", optionally with (asc|desc) when \'paginate\' option is used.'
            )

        sort_function_index = sort_function_indices.pop()
        last_arg = apl_functions[sort_function_index].split().pop()
        return last_arg if last_arg in ["asc", "desc"] else "desc"

    @classmethod
    def get_or_set_limit(cls, apl, paging, page_size, event_limit):
        apl_functions = cls.split(apl)
        limit_function_indices = [
            i for i, x in enumerate(apl_functions) if re.match(r"limit\s+\d+$", x)
        ]

        if len(limit_function_indices) >= 1:
            limit_function_index = limit_function_indices.pop()
            event_limit = int(apl_functions[limit_function_index].split().pop())
            if paging:
                page_size = event_limit if event_limit < page_size else page_size
                apl = re.sub(r"\|\s*limit\s+\d+$", f"| limit {page_size}", apl)
        elif paging:
            apl += f" | limit {page_size}"

        if paging == "time":
            apl = apl + ' | extend axiom_hash = hash_md5(strcat_array(pack_array(*), ""))'

        return (apl, event_limit, page_size)

    @staticmethod
    def quote_dataset(dataset):
        dataset = (dataset or "").strip()
        if not dataset:
            raise ValueError("dataset cannot be empty")
        return "['" + dataset.replace("\\", "\\\\").replace("'", "\\'") + "']"

    @staticmethod
    def quote_search_literal(value):
        return '"' + (value or "").replace("\\", "\\\\").replace('"', '\\"') + '"'

    @staticmethod
    def quote_scalar_literal(value):
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"

    @staticmethod
    def field_list(fields) -> List[str]:
        if not fields:
            return []
        if isinstance(fields, str):
            return [field.strip() for field in fields.split(",") if field.strip()]
        return [str(field).strip() for field in fields if str(field).strip()]

    @classmethod
    def format_field(cls, field):
        if field == "*" or field.startswith("["):
            if field == "*" or cls.BRACKETED_FIELD_RE.match(field):
                return field
        if field.startswith("["):
            return "['" + field.replace("\\", "\\\\").replace("'", "\\'") + "']"
        if cls.FIELD_IDENTIFIER_RE.match(field):
            return field
        return "['" + field.replace("\\", "\\\\").replace("'", "\\'") + "']"

    @classmethod
    def formatted_field_list(cls, fields) -> List[str]:
        return [cls.format_field(field) for field in cls.field_list(fields)]

    @classmethod
    def output_field_name(cls, field):
        match = cls.BRACKETED_FIELD_RE.match(field)
        if not match:
            return field
        return match.group(1).replace("\\'", "'").replace("\\\\", "\\")

    @classmethod
    def splunk_field_name(cls, field, default="field"):
        field_name = cls.output_field_name(str(field or ""))
        safe_name = cls.SPLUNK_FIELD_UNSAFE_RE.sub("_", field_name)
        safe_name = re.sub(r"_+", "_", safe_name).strip("_")
        if not safe_name:
            safe_name = default
        if safe_name[0].isdigit():
            safe_name = f"_{safe_name}"
        return safe_name

    @classmethod
    def projection_field_list(cls, fields, include_time=True) -> List[str]:
        raw_fields = cls.field_list(fields)
        if not raw_fields or "*" in raw_fields:
            return []

        field_names = [cls.output_field_name(field) for field in raw_fields]
        if include_time and "_time" not in field_names:
            raw_fields = ["_time"] + raw_fields

        return [cls.format_field(field) for field in raw_fields]

    @staticmethod
    def split_csv(value) -> List[str]:
        if not value:
            return []

        parts = []
        buf = []
        depth = 0
        quote = None
        escape_next = False

        for ch in str(value):
            if quote:
                buf.append(ch)
                if escape_next:
                    escape_next = False
                elif ch == "\\":
                    escape_next = True
                elif ch == quote:
                    quote = None
                continue

            if ch in ("'", '"'):
                quote = ch
                buf.append(ch)
                continue
            if ch == "(":
                depth += 1
                buf.append(ch)
                continue
            if ch == ")":
                depth = max(0, depth - 1)
                buf.append(ch)
                continue
            if ch == "," and depth == 0:
                part = "".join(buf).strip()
                if part:
                    parts.append(part)
                buf = []
                continue
            buf.append(ch)

        part = "".join(buf).strip()
        if part:
            parts.append(part)
        return parts

    @classmethod
    def compile_search_query(cls, query):
        return SplSearchCompiler(cls).compile(query)

    @staticmethod
    def parse_field_mapping(mapping):
        if not mapping:
            raise ValueError("on cannot be empty")

        if "=" in mapping:
            local_field, axiom_field = [part.strip() for part in mapping.split("=", 1)]
        else:
            local_field = axiom_field = mapping.strip()

        if not local_field or not axiom_field:
            raise ValueError("on must be either <field> or <splunk-field>=<axiom-field>")

        return (local_field, axiom_field)

    @staticmethod
    def unique_values(values):
        seen = set()
        unique = []
        for value in values:
            if value is None or value == "":
                continue
            marker = (type(value).__name__, repr(value))
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(value)
        return unique

    @classmethod
    def iter_value_batches(cls, values, batch_size):
        batch_size = cls.validate_limit(batch_size, default_limit=250, max_limit=1000)
        unique_values = cls.unique_values(values)
        for index in range(0, len(unique_values), batch_size):
            yield unique_values[index:index + batch_size]

    @staticmethod
    def validate_limit(limit, default_limit=100, max_limit=50000):
        if limit is None:
            return default_limit
        limit = int(limit)
        if limit < 1:
            raise ValueError("limit must be greater than zero")
        if limit > max_limit:
            raise ValueError(f"limit must be less than or equal to {max_limit}")
        return limit

    @classmethod
    def build_sample_apl(cls, dataset, limit=20, fields=None):
        return GeneratedAplBuilder(cls).build_sample(dataset, limit=limit, fields=fields)

    @classmethod
    def build_search_apl(cls, dataset, search=None, where=None, fields=None, sort="_time desc", limit=100, q=None):
        return GeneratedAplBuilder(cls).build_search(
            dataset,
            search=search,
            where=where,
            fields=fields,
            sort=sort,
            limit=limit,
            q=q,
        )

    @classmethod
    def build_stats_apl(cls, dataset, q=None, stats=None, by=None, limit=1000):
        return GeneratedAplBuilder(cls).build_stats(
            dataset,
            q=q,
            stats=stats,
            by=by,
            limit=limit,
        )

    @classmethod
    def build_timechart_apl(cls, dataset, q=None, agg=None, span="1m", by=None, limit=10000):
        return GeneratedAplBuilder(cls).build_timechart(
            dataset,
            q=q,
            agg=agg,
            span=span,
            by=by,
            limit=limit,
        )

    @classmethod
    def build_enrich_apl(cls, dataset, axiom_key_field, values, fields, limit=None):
        return GeneratedAplBuilder(cls).build_enrich(
            dataset,
            axiom_key_field,
            values,
            fields,
            limit=limit,
        )


class SplSearchToken:
    def __init__(self, token_type, value=None, quoted=False):
        self.type = token_type
        self.value = value
        self.quoted = quoted


class SplSearchCompiler:
    """Compile a small Splunk-search-like predicate subset to APL search syntax."""

    COMPARISON_OPERATORS = {"=", "!=", ">", ">=", "<", "<="}

    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.tokens = []
        self.index = 0

    def compile(self, query):
        if query is None or str(query).strip() == "":
            return ""

        self.tokens = self.tokenize(str(query))
        self.index = 0
        expression = self.parse_expression()
        if self.current().type != "EOF":
            raise AxiomQueryCompileError(f"Unsupported query syntax near {self.current().value!r}")
        return expression.to_apl(self.pipeline)

    def tokenize(self, query):
        tokens = []
        i = 0
        n = len(query)

        while i < n:
            ch = query[i]
            if ch.isspace():
                i += 1
                continue
            if ch == "(":
                tokens.append(SplSearchToken("LPAREN", ch))
                i += 1
                continue
            if ch == ")":
                tokens.append(SplSearchToken("RPAREN", ch))
                i += 1
                continue
            if ch == ",":
                tokens.append(SplSearchToken("COMMA", ch))
                i += 1
                continue
            if ch == ":":
                tokens.append(SplSearchToken("COLON", ch))
                i += 1
                continue
            if ch in ("'", '"'):
                tokens.append(self.read_quoted(query, i))
                i = tokens[-1].end
                continue
            if ch in ("!", ">", "<", "="):
                op = ch
                if i + 1 < n and query[i + 1] == "=":
                    op += "="
                    i += 1
                if op == "!":
                    raise AxiomQueryCompileError("Unsupported operator '!'; use != or NOT")
                tokens.append(SplSearchToken("OP", op))
                i += 1
                continue

            start = i
            while i < n and not query[i].isspace() and query[i] not in "()=!:<>,":
                i += 1
            value = query[start:i]
            upper = value.upper()
            if upper in ("AND", "OR", "NOT", "IN"):
                tokens.append(SplSearchToken(upper, value))
            else:
                tokens.append(SplSearchToken("WORD", value))

        tokens.append(SplSearchToken("EOF", None))
        return tokens

    def read_quoted(self, query, start):
        quote = query[start]
        i = start + 1
        buf = []
        escape_next = False
        while i < len(query):
            ch = query[i]
            if escape_next:
                buf.append(ch)
                escape_next = False
            elif ch == "\\":
                escape_next = True
            elif ch == quote:
                token = SplSearchToken("STRING", "".join(buf), quoted=True)
                token.end = i + 1
                return token
            else:
                buf.append(ch)
            i += 1
        raise AxiomQueryCompileError("Unterminated quoted string in query")

    def current(self):
        return self.tokens[self.index]

    def peek(self, offset=1):
        position = self.index + offset
        if position >= len(self.tokens):
            return SplSearchToken("EOF", None)
        return self.tokens[position]

    def advance(self):
        token = self.current()
        self.index += 1
        return token

    def match(self, token_type):
        if self.current().type == token_type:
            return self.advance()
        return None

    def expect(self, token_type, message):
        token = self.match(token_type)
        if not token:
            raise AxiomQueryCompileError(message)
        return token

    def starts_primary(self, token):
        return token.type in ("WORD", "STRING", "LPAREN", "NOT")

    def parse_expression(self):
        return self.parse_and()

    def parse_and(self):
        node = self.parse_or()
        while True:
            if self.match("AND"):
                node = SplSearchBinaryNode("and", node, self.parse_or())
                continue
            if self.starts_primary(self.current()) and self.current().type not in ("OR", "RPAREN", "COMMA", "EOF"):
                node = SplSearchBinaryNode("and", node, self.parse_or())
                continue
            return node

    def parse_or(self):
        node = self.parse_not()
        while self.match("OR"):
            node = SplSearchBinaryNode("or", node, self.parse_not())
        return node

    def parse_not(self):
        if self.match("NOT"):
            return SplSearchNotNode(self.parse_not())
        return self.parse_primary()

    def parse_primary(self):
        if self.match("LPAREN"):
            node = self.parse_expression()
            self.expect("RPAREN", "Expected ')' in query")
            return node

        token = self.advance()
        if token.type not in ("WORD", "STRING"):
            raise AxiomQueryCompileError(f"Expected search term near {token.value!r}")

        if token.type == "WORD" and self.is_field_operator_start(self.current()):
            return self.parse_field_predicate(token.value)

        return SplSearchTermNode(token.value)

    def is_field_operator_start(self, token):
        return token.type in ("OP", "COLON", "IN") or (
            token.type == "NOT" and self.peek().type == "IN"
        )

    def parse_field_predicate(self, field):
        if not self.pipeline.FIELD_NAME_RE.match(field):
            raise AxiomQueryCompileError(f"Unsupported field name {field!r}")

        if self.match("COLON"):
            return SplSearchFieldNode(field, ":", [self.parse_value()])

        if self.match("IN"):
            return SplSearchFieldNode(field, "IN", self.parse_value_list())

        if self.match("NOT"):
            self.expect("IN", "Expected IN after NOT in field predicate")
            return SplSearchFieldNode(field, "NOT IN", self.parse_value_list())

        op = self.expect("OP", "Expected field comparison operator").value
        if op not in self.COMPARISON_OPERATORS:
            raise AxiomQueryCompileError(f"Unsupported comparison operator {op!r}")
        return SplSearchFieldNode(field, op, [self.parse_value()])

    def parse_value_list(self):
        self.expect("LPAREN", "Expected '(' before IN values")
        values = []
        while True:
            values.append(self.parse_value())
            if self.match("COMMA"):
                continue
            break
        self.expect("RPAREN", "Expected ')' after IN values")
        return values

    def parse_value(self):
        token = self.advance()
        if token.type not in ("WORD", "STRING"):
            raise AxiomQueryCompileError(f"Expected comparison value near {token.value!r}")
        return SplSearchValue(token.value, quoted=token.quoted)


class SplSearchValue:
    NUMBER_RE = re.compile(r"^-?(?:\d+|\d+\.\d+)$")

    def __init__(self, text, quoted=False):
        self.text = str(text)
        self.quoted = quoted

    def has_wildcard(self):
        return "*" in self.text

    def is_existence_marker(self):
        return self.text == "*"

    def is_string(self):
        return self.quoted or not (
            self.NUMBER_RE.match(self.text)
            or self.text.lower() in ("true", "false")
        )

    def scalar_literal(self, pipeline):
        if not self.quoted:
            lowered = self.text.lower()
            if lowered == "true":
                return "true"
            if lowered == "false":
                return "false"
            if self.NUMBER_RE.match(self.text):
                return self.text
        return pipeline.quote_scalar_literal(self.text)

    def search_literal(self, pipeline):
        return pipeline.quote_search_literal(self.text)


class SplSearchTermNode:
    def __init__(self, value):
        self.value = value

    def to_apl(self, pipeline):
        if self.value == "*":
            return "*"
        return pipeline.quote_search_literal(self.value)


class SplSearchFieldNode:
    def __init__(self, field, operator, values):
        self.field = field
        self.operator = operator.upper() if operator in ("IN", "NOT IN") else operator
        self.values = values

    def to_apl(self, pipeline):
        field = pipeline.format_field(self.field)
        value = self.values[0]

        if self.operator == ":":
            return f"{field}:{value.search_literal(pipeline)}"

        if self.operator in ("=", "!="):
            expression = self.equality_to_apl(pipeline, field, value)
            if self.operator == "!=" and not value.is_existence_marker():
                return self.negate_equality_expression(expression)
            return expression

        if self.operator in (">", ">=", "<", "<="):
            return f"{field} {self.operator} {value.scalar_literal(pipeline)}"

        if self.operator in ("IN", "NOT IN"):
            expression = self.in_to_apl(pipeline, field)
            if self.operator == "NOT IN":
                return f"(not {self.parenthesize(expression)})"
            return expression

        raise AxiomQueryCompileError(f"Unsupported field operator {self.operator!r}")

    def equality_to_apl(self, pipeline, field, value):
        if value.is_existence_marker():
            return f"isnotempty({field})" if self.operator == "=" else f"isempty({field})"
        if value.has_wildcard():
            return f"{field}:{value.search_literal(pipeline)}"
        if value.is_string():
            return f"{field} =~ {value.scalar_literal(pipeline)}"
        return f"{field} == {value.scalar_literal(pipeline)}"

    @staticmethod
    def negate_equality_expression(expression):
        if " =~ " in expression:
            return expression.replace(" =~ ", " !~ ", 1)
        if " == " in expression:
            return expression.replace(" == ", " != ", 1)
        return f"(not {SplSearchFieldNode.parenthesize(expression)})"

    @staticmethod
    def parenthesize(expression):
        expression = str(expression)
        if expression.startswith("(") and expression.endswith(")"):
            return expression
        return f"({expression})"

    def in_to_apl(self, pipeline, field):
        if any(value.has_wildcard() for value in self.values):
            expressions = []
            for value in self.values:
                if value.is_existence_marker():
                    expressions.append(f"isnotempty({field})")
                else:
                    expressions.append(f"{field}:{value.search_literal(pipeline)}")
            return "(" + " or ".join(expressions) + ")"

        operator = "in~" if all(value.is_string() for value in self.values) else "in"
        literals = ", ".join(value.scalar_literal(pipeline) for value in self.values)
        return f"{field} {operator} ({literals})"


class SplSearchNotNode:
    def __init__(self, child):
        self.child = child

    def to_apl(self, pipeline):
        return f"(not {self.child.to_apl(pipeline)})"


class SplSearchBinaryNode:
    def __init__(self, operator, left, right):
        self.operator = operator
        self.left = left
        self.right = right

    def to_apl(self, pipeline):
        return f"({self.left.to_apl(pipeline)} {self.operator} {self.right.to_apl(pipeline)})"


class GeneratedAplBuilder:
    """Build APL for commands that expose Splunk-style options."""

    def __init__(self, pipeline):
        self.pipeline = pipeline

    def build_sample(self, dataset, limit=20, fields=None):
        limit = self.pipeline.validate_limit(limit, default_limit=20)
        apl = f"{self.pipeline.quote_dataset(dataset)} | sort by _time desc | limit {limit}"
        project_fields = self.pipeline.projection_field_list(fields)
        if project_fields:
            apl += " | project-keep " + ", ".join(project_fields)
        return apl

    def build_search(self, dataset, search=None, where=None, fields=None, sort="_time desc", limit=100, q=None):
        limit = self.pipeline.validate_limit(limit, default_limit=100)
        stages = [self.pipeline.quote_dataset(dataset)]

        if q:
            stages.append(f"search {self.pipeline.compile_search_query(q)}")
        if search:
            stages.append(f"search {self.pipeline.quote_search_literal(search)}")
        if where:
            stages.append(f"where {where}")

        if sort:
            stages.append(f"sort by {sort}")
        stages.append(f"limit {limit}")

        project_fields = self.pipeline.projection_field_list(fields)
        if project_fields:
            stages.append("project-keep " + ", ".join(project_fields))

        return " | ".join(stages)

    def build_stats(self, dataset, q=None, stats=None, by=None, limit=1000):
        limit = self.pipeline.validate_limit(limit, default_limit=1000)
        stages = [self.pipeline.quote_dataset(dataset)]
        if q:
            stages.append(f"search {self.pipeline.compile_search_query(q)}")

        summarize = "summarize " + ", ".join(self.parse_aggregations(stats or "count"))
        by_fields = self.pipeline.formatted_field_list(by)
        if by_fields:
            summarize += " by " + ", ".join(by_fields)
        stages.append(summarize)
        if by_fields and limit:
            stages.append(f"limit {limit}")
        return " | ".join(stages)

    def build_timechart(self, dataset, q=None, agg=None, span="1m", by=None, limit=10000):
        if not self.pipeline.DURATION_RE.match(str(span or "")):
            raise ValueError("span must be a positive APL duration such as 30s, 5m, 1h, or 1d")
        limit = self.pipeline.validate_limit(limit, default_limit=10000)

        stages = [self.pipeline.quote_dataset(dataset)]
        if q:
            stages.append(f"search {self.pipeline.compile_search_query(q)}")

        summarize = "summarize " + ", ".join(self.parse_aggregations(agg or "count"))
        by_fields = ["bin(_time, " + str(span) + ")"] + self.pipeline.formatted_field_list(by)
        summarize += " by " + ", ".join(by_fields)
        stages.append(summarize)
        stages.append("sort by _time asc")
        stages.append(f"limit {limit}")
        return " | ".join(stages)

    def parse_aggregations(self, value):
        parts = self.pipeline.split_csv(value or "count")
        if not parts:
            parts = ["count"]

        return [self.parse_aggregation(part) for part in parts]

    def parse_aggregation(self, term):
        match = re.match(r"^(?P<expr>.+?)\s+as\s+(?P<alias>[A-Za-z_][A-Za-z0-9_]*)$", term, re.IGNORECASE)
        if match:
            expression = match.group("expr").strip()
            alias = match.group("alias")
        else:
            expression = term.strip()
            alias = None

        apl_expression, default_alias = self.aggregation_expression(expression)
        alias = alias or default_alias
        return f"{alias}={apl_expression}"

    def aggregation_expression(self, expression):
        if re.match(r"^count(?:\(\))?$", expression, re.IGNORECASE):
            return ("count()", "count")

        percentile_match = re.match(
            r"^(?:p|perc|percentile)(?P<pct>\d+(?:\.\d+)?)\((?P<field>[^(),]+)\)$",
            expression,
            re.IGNORECASE,
        )
        if percentile_match:
            field = percentile_match.group("field").strip()
            pct = percentile_match.group("pct")
            return (
                f"percentile({self.pipeline.format_field(field)}, {pct})",
                f"p{self.safe_alias_number(pct)}_{self.default_field_alias(field)}",
            )

        function_match = re.match(
            r"^(?P<func>[A-Za-z_][A-Za-z0-9_]*)\((?P<args>.*)\)$",
            expression,
        )
        if not function_match:
            raise AxiomQueryCompileError(f"Unsupported stats expression {expression!r}")

        func = function_match.group("func").lower()
        args = self.pipeline.split_csv(function_match.group("args"))

        if func == "dc":
            func = "dcount"
        if func == "perc":
            func = "percentile"

        allowed = {
            "sum",
            "avg",
            "min",
            "max",
            "dcount",
            "stdev",
            "variance",
            "percentile",
        }
        if func not in allowed:
            raise AxiomQueryCompileError(f"Unsupported stats function {function_match.group('func')!r}")

        if func == "percentile":
            if len(args) != 2:
                raise AxiomQueryCompileError("percentile requires a field and percentile value")
            field, pct = args[0].strip(), args[1].strip()
            if not re.match(r"^\d+(?:\.\d+)?$", pct):
                raise AxiomQueryCompileError("percentile value must be numeric")
            return (
                f"percentile({self.pipeline.format_field(field)}, {pct})",
                f"p{self.safe_alias_number(pct)}_{self.default_field_alias(field)}",
            )

        if len(args) != 1:
            raise AxiomQueryCompileError(f"{func} requires exactly one field")
        field = args[0].strip()
        return (
            f"{func}({self.pipeline.format_field(field)})",
            f"{func}_{self.default_field_alias(field)}",
        )

    @staticmethod
    def safe_alias_number(value):
        return str(value).replace(".", "_")

    @staticmethod
    def default_field_alias(field):
        return re.sub(r"[^A-Za-z0-9_]", "_", field).strip("_") or "value"

    def build_enrich(self, dataset, axiom_key_field, values, fields, limit=None):
        unique_values = self.pipeline.unique_values(values)
        if not unique_values:
            raise ValueError("enrichment values cannot be empty")

        requested_fields = self.pipeline.field_list(fields)
        if not requested_fields:
            raise ValueError("fields cannot be empty")

        axiom_key = self.pipeline.format_field(axiom_key_field)
        literals = ", ".join(self.pipeline.quote_scalar_literal(value) for value in unique_values)
        if "*" in requested_fields:
            arg_fields = "*"
        else:
            arg_fields = ", ".join(
                self.pipeline.format_field(field)
                for field in requested_fields
                if self.pipeline.output_field_name(field) != "_time"
            )
            if not arg_fields:
                arg_fields = axiom_key

        row_limit = self.pipeline.validate_limit(limit or len(unique_values), default_limit=len(unique_values))
        return (
            f"{self.pipeline.quote_dataset(dataset)} | where {axiom_key} in ({literals}) "
            f"| summarize arg_max(_time, {arg_fields}) by {axiom_key} | limit {row_limit}"
        )


class AxiomResponseMapper:
    """Convert Axiom API responses into Splunk events."""

    @staticmethod
    def get_status_data(response_json):
        if not response_json:
            return None
        if "status" not in response_json:
            return None
        return flatten_dict(response_json["status"], parent_key="status")

    @staticmethod
    def get_header_data(headers):
        return flatten_dict(headers, parent_key="resp_headers")

    @staticmethod
    def get_query_data(response_json):
        """Select the result table that carries the rows a command should emit.

        Verified against api.axiom.co: most queries return a single table named '0',
        but a time-bucketed ``summarize ... by bin(_time, ...)`` returns two -- the
        series as '0' and a one-row aggregate as '_totals'. Only the series has
        ``_time``, so taking the last table drops the time series entirely (SPL-72).
        Ignore the totals table, then prefer whichever table carries ``_time``.
        """
        if not response_json:
            return None
        tables = response_json.get("tables") or []
        if not tables:
            return None

        candidates = [t for t in tables if t and t.get("name") != TOTALS_TABLE_NAME] or tables

        for table in candidates:
            if "_time" in AxiomResponseMapper.get_column_headings(table):
                return table

        return candidates[-1]

    @staticmethod
    def get_column_headings(table):
        if not table:
            return []
        return [field["name"] for field in table.get("fields", [])]

    @staticmethod
    def get_columns(table):
        if not table:
            return None
        return table.get("columns") if "columns" in table else None

    @staticmethod
    def iter_table_rows(table):
        if not table:
            return
        headings = AxiomResponseMapper.get_column_headings(table)
        columns = AxiomResponseMapper.get_columns(table) or []
        for row_values in zip(*columns):
            yield dict(zip(headings, row_values))

    @staticmethod
    def rows_by_key(table, key_field):
        keyed_rows = {}
        for row in AxiomResponseMapper.iter_table_rows(table):
            value = row.get(key_field)
            if value is not None and value != "":
                keyed_rows[str(value)] = row
        return keyed_rows

    @staticmethod
    def row_to_splunk_event(
        row,
        source=DEFAULT_SOURCE,
        sourcetype=DEFAULT_SOURCETYPE,
        host=DEFAULT_HOST,
        event_fields=None,
        include_raw=True,
    ):
        """Wrap an Axiom row as a Splunk event that already carries its fields.

        The row's keys are emitted as real Splunk fields so callers never need to
        append ``| spath``. ``_raw`` still holds the unflattened row for the Events
        tab and for anything that reads it. Reporting commands pass
        ``include_raw=False`` to get a clean stats table with no event metadata.
        """
        wrapper = {}
        if include_raw:
            wrapper.update({
                "host": host,
                "source": source,
                "sourcetype": sourcetype,
            })

        wrapper.update(flatten_row_for_splunk(row))

        if "_time" in row:
            wrapper["_time"] = TimeRangeResolver.rfc3339_to_epoch_microseconds(row["_time"])
        if event_fields:
            wrapper.update(event_fields)
        if include_raw:
            wrapper["_raw"] = row
        return wrapper

    @staticmethod
    def resource_records_to_events(records, timestamp=None):
        event_time = int((timestamp or datetime.now()).timestamp())
        for record in records or []:
            event = {"_time": event_time}
            for key in sorted(record.keys(), key=lambda x: x.lower()):
                event[key] = record[key]
            yield event

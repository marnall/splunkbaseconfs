"""tessian_api.py.

This script defines a Splunk modular input, which ingests data from the
Tessian API.

Notes:
* We rely on the user having configured the application, during which
  they set their API key, subdomain and environment.
* We implement the API polling agnostic to the endpoint called. The only
  per-endpoint or per-input parameter is the interval that this script
  runs at, which is managed by Splunk.
* If you're reading this before familiarising yourself with how Splunk
  apps work, go check out the Splunk docs out first. Otherwise the structure
  and approach to libraries won't make sense.
"""

from __future__ import annotations

import base64
import json
import logging
import logging.handlers
import os
import os.path
import sys
import time
from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus
from typing import Any
from xml.dom import minidom

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "third_party"))

import requests  # pylint: disable=import-error, wrong-import-position
import splunk  # pylint: disable=import-error, wrong-import-position
from dateutil import parser  # pylint: disable=import-error, wrong-import-position
from splunklib.modularinput import (  # pylint: disable=wrong-import-position
    Argument,
    Event,
    EventWriter,
    InputDefinition,
    Scheme,
    Script,
    ValidationDefinition,
)


class APICallError(Exception):
    """Custom exception for API calls that do not return a 200 code."""

    def __init__(self, request_path: str, status_code: int, text: str):
        self.request_path = request_path
        self.status_code = status_code
        self.text = text

        super().__init__(
            f"Endpoint returned a non-200 code path={self.request_path} "
            f"status={self.status_code} message={self.text}",
        )


class Endpoint(str, Enum):
    """Tessian API endpoints available in this modular input."""

    EVENTS = "events"
    GROUPS = "groups"
    COMPANY_RISK = "company_risk"
    USER_MONITORING = "user_monitoring"
    ANOMALIES = "anomalies"
    AUDIT = "audit"


class Environment(str, Enum):
    """Environments that we can call the API in."""

    US = "tessian-app.com"
    EU = "tessian-platform.com"


ENDPOINT_ID_TO_PATH_MAP = {
    Endpoint.EVENTS: "api/v1/events",
    Endpoint.GROUPS: "api/v1/groups",
    Endpoint.COMPANY_RISK: "api/v1/risk/company",
    Endpoint.USER_MONITORING: "api/v1/monitoring/users",
    Endpoint.ANOMALIES: "reporting/anomalies/v1",
    Endpoint.AUDIT: "api/v1/audits",
}

ENDPOINT_RESULTS_MAP = {
    Endpoint.EVENTS: "results",
    Endpoint.USER_MONITORING: "results",
    Endpoint.COMPANY_RISK: "results",
    Endpoint.GROUPS: "groups",
    Endpoint.ANOMALIES: "data",
    Endpoint.AUDIT: "results",
}

# Endpoints serve the event timestamp under different keys -
# this helps us get the right one
ENDPOINT_EVENT_TIMESTAMP_MAP = {
    Endpoint.EVENTS: "updated_at",
    Endpoint.USER_MONITORING: "last_connection",
    Endpoint.COMPANY_RISK: "timestamp",
    Endpoint.GROUPS: "updated_at",
    Endpoint.ANOMALIES: "anomalous_period_start",
    Endpoint.AUDIT: "timestamp",
}

API_URL = (
    "https://{subdomain}.{environment}/{path}?after_checkpoint={checkpoint}&limit=100"
)
API_URL_NO_CHECKPOINT = "https://{subdomain}.{environment}/{path}?limit=100"
LOGGING_STANZA_NAME = "python"
LOGGING_FILE_NAME = "tessian_email_security.log"
LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
CHECKPOINT_PATH = "{base}/{filename}.txt"
CATCH_UP_SLEEP_TIME = 10
MAX_CALLS_PER_INTERVAL = 20
TENANT_INFO_MAX_RETRIES = 3
TENANT_INFO_RETRY_BASE_DELAY = 2
TRUNCATE_MARKER = "...[truncated]"
TRUNCATABLE_EVENT_FIELDS = [
    "guardian_details.warning_messages",
    "architect_details.warning_messages",
    "guardian_details.justifications",
    "architect_details.justifications",
]


@dataclass
class TenantConfiguration:
    """Stores the tenant information we need to make API calls."""

    subdomain: str
    environment: Environment
    api_key: str
    max_event_size: int = 0


class TessianAPI(Script):
    """Implements a modular input for Tessian API endpoints."""

    def __init__(self):
        # Needed as it doesn't inherit, somehow
        Script.__init__(self)
        self.logger = self._initialize_logging()

    def get_scheme(self) -> Scheme:
        """Generates the schema for the Tessian API modular input.

        :return: An object describing the modular input
        """
        scheme = Scheme("Tessian Email Security")
        scheme.description = "Pull security events from Tessian API."
        scheme.use_external_validation = True

        # This allows Splunk to spawn an instance of this script for
        # every input created - which in turn allows per-input control
        # of the polling interval
        scheme.use_single_instance = False

        endpoint_arg = Argument("endpoint")
        endpoint_arg.data_type = Argument.data_type_string
        endpoint_arg.description = "Identifier for the endpoint to poll."
        endpoint_arg.required_on_create = True
        scheme.add_argument(endpoint_arg)

        # Note that we allow the user to set interval but we cannot
        # define it for validation here as it is a Splunk-owned parameter.
        # If we define it, Splunk will fail to load this script.

        return scheme

    def validate_input(self, definition: ValidationDefinition) -> None:
        """Validates the configuration of the data input.

        :param definition: An object representing the validation for
                            input parameters
        """
        endpoint = definition.parameters["endpoint"]

        if endpoint.upper() not in Endpoint.__members__:
            self.logger.error("Invalid API endpoint selected.")
            raise ValueError("Invalid API endpoint selected.")

    def stream_events(self, inputs: InputDefinition, ew: EventWriter) -> None:
        """Calls API endpoints for the provided modular inputs.

        This is called by Splunk with a set of inputs. The method then makes an API
        call for each of those inputs, converting the response results into Events
        and sending them to Splunk. It also handles checkpointing.

        :param inputs: An input definition object that describes one or more modular
                        inputs. This is provided by Splunk
        :param ew: An event writer object that accepts events which are then written
                                to Splunk
        """

        # If we can't get tenant info, exit early to avoid weird errors
        # later on
        try:
            tenant_config = self._get_tenant_info()
        except Exception:
            self.logger.exception("Failed to get tenant info, aborting run")
            return

        call_count = 0
        additional_results = True
        for input_name, input_item in inputs.inputs.items():
            if input_item.get("endpoint") == Endpoint.COMPANY_RISK:
                self.logger.warning(
                    "The company_risk endpoint is deprecated and will be "
                    "removed in a future release. "
                    "Please remove this data input: %s",
                    input_name,
                )
                continue
            self.logger.info("Polling %s", input_name)
            # Makes a series of calls if there are additional results, with
            # a delay between each call. Does not matter if this overruns
            # the next interval as Splunk will not start a second task
            while additional_results and call_count < MAX_CALLS_PER_INTERVAL:
                try:
                    checkpoint = self._get_checkpoint(
                        input_name=input_name,
                        input_metadata=inputs.metadata,
                    )
                    response = self._call_api(
                        tenant_config=tenant_config,
                        input_item=input_item,
                        checkpoint=checkpoint,
                    )
                    self._convert_response_to_events(
                        input_name=input_name,
                        input_item=input_item,
                        event_writer=ew,
                        response=response,
                        tenant_config=tenant_config,
                    )
                    self._set_checkpoint(
                        input_name=input_name,
                        input_metadata=inputs.metadata,
                        input_item=input_item,
                        response=response,
                        existing_checkpoint=checkpoint,
                    )
                    additional_results = response.get("additional_results", False)
                except Exception:
                    self.logger.exception("Hit an exception")
                    break
                call_count += 1
                if additional_results:
                    self.logger.info("More results for %s - sleeping...", input_name)
                    time.sleep(CATCH_UP_SLEEP_TIME)
            self.logger.info("Finished polling %s", input_name)

    def _initialize_logging(self) -> logging.Logger:
        logger = logging.getLogger("splunk.tessian_email_security")
        slunk_home_env = os.environ["SPLUNK_HOME"]

        logging_default_config_file = os.path.join(slunk_home_env, "etc", "log.cfg")
        logging_local_config_file = os.path.join(slunk_home_env, "etc", "log-local.cfg")
        base_log_path = os.path.join("var", "log", "splunk")

        splunk_log_handler = logging.handlers.RotatingFileHandler(
            os.path.join(slunk_home_env, base_log_path, LOGGING_FILE_NAME),
            mode="a",
        )
        splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        logger.addHandler(splunk_log_handler)
        splunk.setupSplunkLogger(
            logger,
            logging_default_config_file,
            logging_local_config_file,
            LOGGING_STANZA_NAME,
        )
        return logger

    def _convert_response_to_events(
        self,
        input_name: str,
        input_item: dict[str, Any],
        event_writer: EventWriter,
        response: dict[str, Any],
        tenant_config: TenantConfiguration | None = None,
    ) -> None:
        """Extracts the results from an API response and converts them to
        Splunk Event objects, submitted to the EventWriter.

        :param input_name: The name of the modular input, provided by Splunk
        :param input_item: The description dictionary of the
            modular input, provided by Splunk
        :param event_writer: An event writer object to submit events to
        :param response: An API response for the modular input
        :param tenant_config: Tenant configuration, used for max_event_size
        """
        results = response.get(ENDPOINT_RESULTS_MAP[input_item["endpoint"]], [])
        self.logger.info(
            "Writing %d events for %s",
            len(results),
            input_item["endpoint"],
        )
        max_event_size = (
            tenant_config.max_event_size
            if tenant_config and tenant_config.max_event_size > 0
            else 0
        )
        should_truncate = (
            max_event_size > 0 and input_item["endpoint"] == Endpoint.EVENTS
        )
        for result in results:
            try:
                event = Event()
                event.stanza = input_name
                event.source = input_name
                timestamp_field = ENDPOINT_EVENT_TIMESTAMP_MAP[input_item["endpoint"]]
                if result.get(timestamp_field):
                    event.time = parser.isoparse(result[timestamp_field]).timestamp()

                # Pop the checkpoint out of the event, if it is there
                result.pop("checkpoint", None)
                if should_truncate:
                    result = self._truncate_event(result, max_event_size)
                event.data = json.dumps(result)
                event_writer.write_event(event)
            except Exception:  # noqa: PERF203
                self.logger.exception(
                    "Could not convert a log for the %s input",
                    input_name,
                )

    def _get_checkpoint(
        self,
        input_name: str,
        input_metadata: dict[str, Any],
    ) -> str | None:
        """Tries to get a checkpoint for a modular input, if one exists.

        :param input_name: The name of the modular input, provided by Splunk
        :param input_metadata: The modular input metadata object, provided by Splunk.
                                Shold contain the checkpoint_dir key
        :return: A checkpoint string, if one exists
        """
        if "checkpoint_dir" not in input_metadata:
            self.logger.warning(
                "Checkpoint directory is not present in metadata for %s",
                input_name,
            )
            return None

        encoded_name = base64.b64encode(input_name.encode())
        expected_path = CHECKPOINT_PATH.format(
            base=input_metadata["checkpoint_dir"],
            filename=encoded_name.decode(),
        )
        if not os.path.isfile(expected_path):
            return None

        with open(
            CHECKPOINT_PATH.format(
                base=input_metadata["checkpoint_dir"],
                filename=encoded_name.decode(),
            ),
            "r",
            encoding="utf-8",
        ) as file_handle:
            checkpoint = file_handle.read()

        if checkpoint:
            self.logger.info("Checkpoint: %s", checkpoint)
            return checkpoint

        return None

    def _set_checkpoint(
        self,
        input_name: str,
        input_metadata: dict[str, Any],
        input_item: dict[str, Any],
        response: dict[str, Any],
        existing_checkpoint: str | None = None,
    ) -> None:
        """Given the description of an input and the response it collected,
        extract and save a checkpoint if one exists.

        :param input_name: Name of the input, provided by Splunk
        :param input_metadata: The input metadata object, provided by Splunk
        :param input_item: The description of the input, provided by Splunk
        :param response: The API call response for this input
        :param existing_checkpoint: An existing checkpoint for
            this input, defaults to None
        """
        # If checkpoint is not in response it means we have not had a successful
        # response/we received no response body. In this case, we do not want to
        # overwrite the existing checkpoint as it will go to empty and we will
        # start pulling from the beginning of time again.
        if existing_checkpoint and "checkpoint" not in response:
            return

        # The anomalies endpoint puts checkpoints in each result object
        if (
            input_item["endpoint"] == Endpoint.ANOMALIES
            and ENDPOINT_RESULTS_MAP[Endpoint.ANOMALIES]
            in response  # Endpoint may return 200 but have no data
            and len(response[ENDPOINT_RESULTS_MAP[Endpoint.ANOMALIES]]) > 0
        ):
            checkpoint = response[ENDPOINT_RESULTS_MAP[Endpoint.ANOMALIES]][0].get(
                "checkpoint",
                "",
            )
        else:
            checkpoint = response.get("checkpoint", "")

        if not checkpoint:
            self.logger.warning(
                "No checkpoint found for %s endpoint",
                input_item["endpoint"],
            )

        # Encode the input name since it can contain all sorts of chars
        encoded_name = base64.b64encode(input_name.encode())

        with open(
            CHECKPOINT_PATH.format(
                base=input_metadata["checkpoint_dir"],
                filename=encoded_name.decode(),
            ),
            "w",
            encoding="utf-8",
        ) as file_handle:
            file_handle.write(checkpoint)

    def _get_tenant_info(self) -> TenantConfiguration:
        """Assembles tenant information into a TenantConfiguration object, by
        grabbing it from the secret store/config files.

        :return: A populated tenant configuration object
        """
        for attempt in range(1, TENANT_INFO_MAX_RETRIES + 1):
            try:
                apikey_resp = self.service.storage_passwords.get(
                    "tessian_realm:apikey0:",
                    app="TessianEmailSecurity",
                )
                apikey_obj = minidom.parseString(apikey_resp["body"].read())
                keys = apikey_obj.getElementsByTagName("s:key")
                clear_keys = list(
                    filter(lambda x: x.getAttribute("name") == "clear_password", keys)
                )
                tenant_config = self.service.confs["tenant"]["tenant://0"]
                try:
                    # We need to look this up from 'content' unlike environment/subdomain
                    # because __getitem__ is overriden but __getattr__ is not.
                    max_event_size = int(tenant_config.content.get("max_event_size", 0))
                except (ValueError, TypeError):
                    self.logger.warning("Invalid max_event_size value, defaulting to 0")
                    max_event_size = 0
                return TenantConfiguration(
                    tenant_config["subdomain"],
                    Environment[tenant_config["environment"].upper()],
                    clear_keys[0].firstChild.nodeValue,
                    max_event_size=max_event_size,
                )
            except Exception:  # noqa: PERF203
                if attempt < TENANT_INFO_MAX_RETRIES:
                    delay = TENANT_INFO_RETRY_BASE_DELAY**attempt
                    self.logger.warning(
                        "Could not get tenant info (attempt %d/%d), retrying in %ds",
                        attempt,
                        TENANT_INFO_MAX_RETRIES,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    self.logger.exception(
                        "Could not get tenant info after %d attempts",
                        TENANT_INFO_MAX_RETRIES,
                    )
                    raise
        raise RuntimeError("Failed to get tenant info")

    @staticmethod
    def _truncate_string(value: str, max_length: int) -> str:
        """Truncates a string to the given max length, adding a marker.

        :param value: The string to truncate
        :param max_length: Maximum allowed length including marker
        :return: The truncated string with marker, or original if short enough
        """
        if len(value) <= max_length:
            return value
        marker = TRUNCATE_MARKER
        if max_length <= len(marker):
            return marker[:max_length]
        return value[: max_length - len(marker)] + marker

    def _truncate_event(
        self,
        event: dict[str, Any],
        max_size: int,
    ) -> dict[str, Any]:
        """Truncates long text fields in an event to fit within max_size bytes.

        Only targets fields listed in TRUNCATABLE_EVENT_FIELDS. Fields are
        processed in priority order, truncating the minimum needed to fit.

        :param event: The event dictionary to truncate
        :param max_size: Maximum serialized JSON size in bytes
        :return: The event dictionary, potentially with truncated fields
        """
        serialized = json.dumps(event)
        if len(serialized.encode("utf-8")) <= max_size:
            return event

        # try to truncate each field in priority order
        for field_path in TRUNCATABLE_EVENT_FIELDS:
            # event fields are described in dot notation, so we need to traverse
            # the event dictionary to find the field we want to truncate
            parts = field_path.split(".")
            parent = event
            for part in parts[:-1]:
                if isinstance(parent, dict) and part in parent:
                    parent = parent[part]
                else:
                    parent = None
                    break

            if parent is None or not isinstance(parent, dict):
                continue

            key = parts[-1]
            if key not in parent:
                continue

            value = parent[key]

            # calculate the current overshoot
            overshoot = len(json.dumps(event).encode("utf-8")) - max_size
            if overshoot <= 0:
                break

            # truncate the string if it's too long and it isn't shorter than
            # the marker
            if isinstance(value, str) and len(value) > len(TRUNCATE_MARKER):
                target_len = max(len(TRUNCATE_MARKER), len(value) - overshoot)
                parent[key] = self._truncate_string(value, target_len)
            # Truncate individual string elements longest to shortest
            elif isinstance(value, list):
                str_indices = [
                    (i, v) for i, v in enumerate(value) if isinstance(v, str)
                ]
                str_indices.sort(key=lambda x: len(x[1]), reverse=True)
                for idx, item_val in str_indices:
                    overshoot = len(json.dumps(event).encode("utf-8")) - max_size
                    if overshoot <= 0:
                        break
                    if len(item_val) > len(TRUNCATE_MARKER):
                        target_len = max(
                            len(TRUNCATE_MARKER),
                            len(item_val) - overshoot,
                        )
                        value[idx] = self._truncate_string(item_val, target_len)

            if len(json.dumps(event).encode("utf-8")) <= max_size:
                break

        final_size = len(json.dumps(event).encode("utf-8"))
        if final_size > max_size:
            self.logger.warning(
                "Event still exceeds max_event_size after truncation "
                "(size=%d, limit=%d, id=%s). Consider increasing max_event_size.",
                final_size,
                max_size,
                event.get("id"),
            )

        return event

    def _call_api(
        self,
        tenant_config: TenantConfiguration,
        input_item: dict[str, Any],
        checkpoint: str | None = None,
    ) -> dict[str, Any]:
        """Calls the relevant API endpoint.

        :param tenant_config: A populated TenantConfiguration
            object containing the API key, subdomain and
            environment.
        :param input_item: A dictionary describing the modular
            input config, provided by Splunk
        :param checkpoint: An API checkpoint, defaults to None
        :return: A dictionary of the API call response
        """
        if checkpoint:
            request_path = API_URL.format(
                subdomain=tenant_config.subdomain,
                environment=tenant_config.environment.value,
                path=ENDPOINT_ID_TO_PATH_MAP[input_item["endpoint"]],
                checkpoint=checkpoint if checkpoint else "",
            )
        else:
            request_path = API_URL_NO_CHECKPOINT.format(
                subdomain=tenant_config.subdomain,
                environment=tenant_config.environment.value,
                path=ENDPOINT_ID_TO_PATH_MAP[input_item["endpoint"]],
            )

        app_version = self.service.apps["TessianEmailSecurity"].version

        if not tenant_config.api_key.isascii():
            self.logger.warning(
                "The API key contains non-ASCII characters. This usually "
                "means the key was copied incorrectly - please check your "
                "API key configuration.",
            )

        resp = requests.get(
            url=request_path,
            headers={
                "Authorization": f"API-Token {tenant_config.api_key}".encode("utf-8"),
                "API-Client": "Tessian-Email-Security-Splunk-App",
                "API-Client-Version": app_version.encode("utf-8"),
                "User-Agent": (
                    "Tessian-Email-Security-Splunk-App "
                    f"{app_version} "
                    f"(via: {requests.utils.default_headers().get('User-Agent')})"
                ).encode("utf-8"),
            },
        )
        self.logger.info("Request made")

        if resp.status_code == HTTPStatus.OK:
            return resp.json()

        # If not 200, raise an exception and break the call loop
        raise APICallError(request_path, resp.status_code, resp.text)


if __name__ == "__main__":
    sys.exit(TessianAPI().run(sys.argv))

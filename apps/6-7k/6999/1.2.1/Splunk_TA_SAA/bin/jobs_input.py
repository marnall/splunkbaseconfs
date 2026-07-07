"""Input to load completed jobs via the Poll endpoint from Splunk Attack Analyzer
"""

import logging
import sys
import traceback

import import_declare_test  # noqa: F401
import structlog
from saa_client import get_configured_client
from saa_consts import ADDON_NAME
from saa_utils import redact_token_for_logging
from saa_exceptions import SAAInputException
from solnlib import conf_manager
from solnlib import log as solnlib_logs
from solnlib.modular_input import KVStoreCheckpointer
from splunklib import modularinput as smi
from typing import cast
import datetime


def logger_factory(input_name: str) -> logging.Logger:
    """Creates a file logger to log into _internal"""

    normalized_input = input_name.split("/")[-1]
    return solnlib_logs.Logs().get_logger(f"Splunk_TA_SAA_{normalized_input}")


def logger_for_input(input_name) -> structlog.stdlib.BoundLogger:
    """Wraps the basic logger into a structlog logger"""

    normalized_input = input_name.split("/")[-1]
    structlog.configure(
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=logger_factory,
        processors=[structlog.processors.LogfmtRenderer(key_order=["input_name", "event"], bool_as_flag=False)],
    )
    return structlog.get_logger(normalized_input)


class JobsInput(smi.Script):
    """Jobs Input"""

    def get_scheme(self):
        scheme = smi.Scheme("jobs_input")
        scheme.description = "jobs_input input"  # type: ignore
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True  # type: ignore
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument("name", title="Name", description="Name", required_on_create=True),
        )
        scheme.add_argument(smi.Argument("api_key_id", title="API Key ID", required_on_create=False))
        scheme.add_argument(smi.Argument("username", title="Username", required_on_create=False))
        scheme.add_argument(smi.Argument("since", title="Backfill from Epoch", required_on_create=False))
        scheme.add_argument(smi.Argument("since_options", title="Backfill", required_on_create=False))

        scheme.add_argument(
            smi.Argument(
                "forensic_components",
                title="Forensic Components",
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        since = definition.parameters.get("since")

        if since:
            try:
                cast(str, since)
                int(since)
            except ValueError:
                raise ValueError("'since' should be an integer.")

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        for input_name, input_item in inputs.inputs.items():
            input_name = cast(str, input_name)

            logger = logger_for_input(input_name)
            try:
                if not self._input_definition:
                    raise SAAInputException("Did not receive an input definition")

                session_key = self._input_definition.metadata["session_key"]

                # Set up Logging
                logger = cast(logging.Logger, logger)

                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=ADDON_NAME,
                    conf_name=f"{ADDON_NAME.lower()}_settings",
                )
                logger.setLevel(log_level)
                logger = cast(structlog.stdlib.BoundLogger, logger)

                # Parse input settings
                param_account = input_item.get("account")
                param_index = input_item.get("index")
                param_source = input_item.get("source") or ""
                param_since = input_item.get("since")
                param_since_options = input_item.get("since_options")
                param_api_key_id = input_item.get("api_key_id") or ""
                param_username = input_item.get("username") or ""
                param_ingest_forensics = input_item.get("ingest_forensics")
                param_forensic_components = input_item.get("forensic_components")

                if param_ingest_forensics is None:
                    param_ingest_forensics = False
                else:
                    param_ingest_forensics = bool(int(param_ingest_forensics))

                if param_forensic_components:
                    param_forensic_components = param_forensic_components.split("|")
                else:
                    # If no components, nothing to ingest
                    param_ingest_forensics = False
                    param_forensic_components = []

                # Determine Backfill
                since = None  # By default, we don't backfill

                if param_since_options:
                    curr_time = datetime.datetime.now()

                    if param_since_options == "1":
                        one_day_ago_time = curr_time - datetime.timedelta(days=1)
                        since = int(one_day_ago_time.timestamp())

                    elif param_since_options == "7":
                        seven_days_ago_time = curr_time - datetime.timedelta(days=7)
                        since = int(seven_days_ago_time.timestamp())

                    elif param_since_options == "14":
                        fourteen_days_ago_time = curr_time - datetime.timedelta(days=14)
                        since = int(fourteen_days_ago_time.timestamp())

                if param_since:
                    since = param_since

                log = logger.bind(
                    input_name=input_name,
                    account=param_account,
                    index=param_index,
                    source=param_source,
                    since=since,
                    since_options=param_since_options,
                    api_key_id=param_api_key_id,
                    username=param_username,
                    ingest_forensics=param_ingest_forensics,
                    param_forensic_components=param_forensic_components,
                )

                log.info("starting collection")

                # Checkpointing

                normalized_input_name = input_name.split("/")[-1]
                checkpoint_collection = "Splunk_TA_SAA_checkpointer"
                checkpointer = KVStoreCheckpointer(
                    checkpoint_collection,
                    session_key,
                    ADDON_NAME,
                )

                checkpoint_name = f"saa_jobs_modular_input_{normalized_input_name}"
                checkpoint = checkpointer.get(checkpoint_name)
                checkpoint_next_token = None

                log.info("searching for checkpoint", checkpoint_name=checkpoint_name)

                if checkpoint is not None:
                    checkpoint_next_token = checkpoint.get("next_token")
                    log.info("found existing checkpoint", token=checkpoint_next_token)
                else:
                    log.info("did not find checkpoint")

                # Get configured client instance
                client = get_configured_client(session_key, log, param_account)

                log.bind(proxies=client.proxies)

                client.test_connectivity()

                # Query for jobs and write to event writer
                log.info("Getting data from an external API")
                query_params = {
                    "source": param_source,
                    "api_key_id": param_api_key_id,
                    "username": param_username,
                }

                if since:
                    query_params["since"] = since

                if checkpoint_next_token is not None:
                    query_params = {"token": checkpoint_next_token}

                next_token = client.poll_jobs(
                    params=query_params,
                    event_writer=ew,
                    checkpointer=checkpointer,
                    checkpoint_name=checkpoint_name,
                    index=param_index,
                    forensic_components=param_forensic_components,
                    input_name=input_name,
                    ingest_forensics=param_ingest_forensics,
                )

                log.info(
                    "saving checkpoint",
                    checkpoint_name=checkpoint_name,
                    token=redact_token_for_logging(next_token),
                )
                checkpointer.update(
                    checkpoint_name,
                    {"next_token": next_token},
                )

                log.info("End of the modular input")
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.error(
                    f"Exception raised while ingesting data for jobs_input: {exc}. Traceback: {traceback.format_exc()}"
                )


if __name__ == "__main__":
    EXIT_CODE = JobsInput().run(sys.argv)
    sys.exit(EXIT_CODE)

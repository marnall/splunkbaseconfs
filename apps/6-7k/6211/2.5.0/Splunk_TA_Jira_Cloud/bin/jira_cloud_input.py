#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import json
import os.path
import sys
import traceback
from datetime import datetime, timedelta

import import_declare_test  # noqa
import jira_cloud_utils as utils
import jira_cloud_consts as jcc
from jira_cloud_checkpoint import JiraCloudCheckpoint as Checkpoint
from jira_cloud_connect import Connect
from solnlib import conf_manager
from splunklib import modularinput as smi


def collect_events(event_writer, config, logger, proxy):
    input_name = config.get("input_name")
    domain = config.get("domain")
    endpoint = "/rest/api/3/auditing/record"
    input_start_time = config.get("start_time")
    checkpoint = Checkpoint(
        logger=logger,
        input_name=input_name,
        session_key=config.get("session_key"),
    )
    checkpoint_start_time = checkpoint.get_start_time()
    datetime_now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[
        :23
    ]  # strftime returns '2021-10-07T11:34:44.275176'

    if checkpoint_start_time:
        start_time = checkpoint_start_time
        logger.debug(
            f"start_time set to value taken from checkpoint (start_time: {start_time})"
        )
    elif input_start_time and input_start_time != "":
        start_time = f"{input_start_time}.000"
        logger.info(
            f"start_time set to input UTC Start Time (start_time: {start_time})"
        )
    else:
        start_time = datetime_now
        logger.info(f"start_time set to current time (start_time: {start_time})")
    offset = 0
    limit = 1000

    connect = Connect(logger=logger, proxy=proxy)
    records_len = limit
    while records_len == limit:
        params = {
            "from": start_time,
            "offset": offset,
            "limit": limit,
        }
        r = connect.get(
            domain=domain,
            endpoint=endpoint,
            username=config.get("username"),
            token=config.get("token"),
            params=params,
        )
        j = r.json()
        events = j.get("records")
        records_len = len(events)
        logger.info(
            f"request to domain: {domain}, endpoint: {endpoint}, params: {params}; "
            + f"response info: { utils.clone(dictionary=j,exclude_keys=['records']) }; "
            + f"events returned: {records_len}"
        )
        if records_len == 0 and not checkpoint_start_time:
            checkpoint.update_start_time(value=start_time)
        offset += records_len
        for raw_event in events:
            if "created" not in raw_event:
                event_created = datetime_now
                logger.warning(
                    f"created section not found in event ({raw_event}); "
                    + f"event time is set to current timestamp ({datetime_now})"
                )
            else:
                event_created = raw_event["created"][:23]
            event_epoch_time = (
                (
                    datetime.strptime(event_created, "%Y-%m-%dT%H:%M:%S.%f")
                    - datetime(1970, 1, 1)
                )
                / timedelta(milliseconds=1)
                / 1000
            )
            smi_event = smi.Event(
                data=json.dumps(raw_event),
                sourcetype=jcc.JIRA_AUDITS_SOURCETYPE,
                source=input_name,
                host=Connect.build_hostname(domain=config.get("domain")),
                # host=None,
                index=config.get("index"),
                time=event_epoch_time,
            )
            try:
                event_writer.write_event(smi_event)
                logger.debug(
                    f"Event has been written to Splunk (raw_event_id: {raw_event['id']})"
                )
            except Exception as e:
                msg = f"Error writing event having id ({raw_event['id']}) to Splunk: {traceback.format_exc()}"
                utils.add_ucc_error_logger(
                    logger=logger,
                    logger_type=jcc.SERVER_ERROR,
                    exception=e,
                    msg_before=msg,
                )
                break
            checkpoint_start_time = checkpoint.get_start_time()
            if checkpoint_start_time:
                checkpoint_epoch_time = (
                    (
                        datetime.strptime(checkpoint_start_time, "%Y-%m-%dT%H:%M:%S.%f")
                        - datetime(1970, 1, 1)
                    )
                    / timedelta(milliseconds=1)
                    / 1000
                )
            if not checkpoint_start_time or event_epoch_time >= checkpoint_epoch_time:
                event_epoch_time_int = int(event_epoch_time)
                event_epoch_time_milliseconds = (
                    round((event_epoch_time - event_epoch_time_int), 3) * 1000
                )
                checkpoint_time = (
                    datetime.utcfromtimestamp(event_epoch_time_int)
                    + timedelta(milliseconds=event_epoch_time_milliseconds)
                    + timedelta(milliseconds=1)
                )
                checkpoint_time = checkpoint_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23]
                # checkpoint has to be shifted at least by a millisecond
                # from (in API REST call) creates "or equal" condition
                checkpoint.update_start_time(value=checkpoint_time)
        utils.log_events_ingested(
            logger=logger,
            modular_input_name=input_name,
            sourcetype=jcc.JIRA_AUDITS_SOURCETYPE,
            n_events=records_len,
            index=config.get("index"),
            account=config.get("api_token"),
            host=Connect.build_hostname(domain=domain),
        )


class BaseScript(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        pass

    def stream_events(self, inputs, event_writer):
        session_key = self._input_definition.metadata["session_key"]
        input_name = (list(inputs.inputs.keys())[0]).split("//")[1]
        logfile_name = jcc.JIRA_CLOUD_AUDIT_LOGFILE_PREFIX + input_name
        _logger = utils.set_logger(session_key, logfile_name)

        try:
            for input_name, input_items in inputs.inputs.items():
                input_items["input_name"] = input_name
            api_token = input_items.get("api_token")
            api_token_details = utils.get_api_token_details(
                session_key, _logger, api_token
            )
            config = {
                "session_key": session_key,
                "input_name": input_items["input_name"],
                "index": input_items["index"],
                "logger": _logger,
                "start_time": input_items.get("from"),
                "api_token": api_token,
            }
            config.update(api_token_details)

            _logger.debug("Getting proxy settings")
            proxy_settings = utils.get_proxy_settings(session_key, _logger)

            collect_events(event_writer, config, _logger, proxy_settings)
        except Exception as e:
            msg = "Error while streaming events for input {}: {}".format(
                input_name, traceback.format_exc()
            )
            utils.add_ucc_error_logger(
                logger=_logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format(
                    (list(inputs.inputs.keys())[0]).replace("://", ":")
                ),
                msg_before=msg,
            )


class JiraCloudInput(BaseScript):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("jira_cloud_input")
        scheme.description = "Jira input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )

        scheme.add_argument(
            smi.Argument(
                "use_existing_checkpoint",
                required_on_create=False,
            )
        )
        return scheme


if __name__ == "__main__":
    exit_code = JiraCloudInput().run(sys.argv)
    sys.exit(exit_code)

#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import datetime
import json
import sys
import time
import traceback
import signal

import import_declare_test  # noqa
import okta_utils as utils
from splunklib import modularinput as smi
from solnlib.modular_input import event_writer
from constant import *


class OKTA_IDENTITY_CLOUD(smi.Script):
    def __init__(self):
        super().__init__()
        self._logfile_prefix = "splunk_ta_okta_identity_cloud_input"
        self.logger = None
        self._session_key = None
        self._checkpoint_data = {}
        self._time_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        self._cache = {}
        self._checkpoint_name = None
        self._checkpointer = None
        self._source = "OktaIM2"
        self._sourcetype = None
        self._index = None
        self._eventhost = None
        self._input_name = None
        self._global_account = None
        self._query_window_size = QUERY_WINDOW_SIZE
        self._now: datetime = time.time
        self.classic_ew = event_writer.ClassicEventWriter()
        self._logs_delay = 30
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        """
        Save the current state of checkpoint in case
        of any un-expectd failure
        """
        self.logger.info("Terminated unexpectedly, updating checkpoint")
        self.save_checkpoint()
        sys.exit(1)

    def get_scheme(self):
        scheme = smi.Scheme("okta_identity_cloud")
        scheme.description = "Okta Identity Cloud Inputs"
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
                "metric",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "global_account",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "start_date",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "end_date",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "use_existing_checkpoint",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_uris",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "fetch_stats",
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition):
        return

    def _initialise_kvstore_checkpoint(self, metric, start_date):
        try:
            self._checkpointer = utils.Checkpointer(self._session_key, self.logger)
            self._checkpoint_data = self._checkpointer.get(
                self._checkpoint_name, metric, start_date=start_date
            )
        except Exception as e:
            msg = "Error while fetching checkpoint information. Reason: {}".format(
                traceback.format_exc()
            )
            utils.add_ucc_error_logger(
                self.logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=UCC_EXECPTION_EXE_LABEL.format("checkpoint"),
                msg_before=msg,
            )
            sys.exit(1)

    def _log_ingested_events(self, event_counter):
        utils.log_events_ingested(
            self.logger,
            utils.MODULAR_INPUT_NAME.format(self._input_name),
            self._sourcetype,
            event_counter,
            self._index,
            self._global_account,
        )

    def _set_logger(self):
        """
        Set Logger Instance
        """
        self.logger = utils.set_logger(
            self._session_key, f"{self._logfile_prefix}-{self._input_name}"
        )

    def _handle_migration(self, metric):
        """
        Handles the upgrade scenario where "ts" was saved in the checkpoint.
        Adds "start_date" to ensure compatibility with the new code design.
        """
        if metric == "log" and not self._checkpoint_data.get("start_date"):
            self._checkpoint_data["start_date"] = self._checkpoint_data.get("ts")

    def stream_events(self, inputs, ew):
        """
        Stream events for all metric types
        """
        self._session_key = self._input_definition.metadata["session_key"]

        self._input_name, input = [
            [key.split("/")[-1], val] for key, val in inputs.inputs.items()
        ][0]
        input["input_name"] = self._input_name
        self._checkpoint_name = f"{self._input_name}_checkpoints"
        self._index = input["index"]
        self._global_account = input["global_account"]
        metric = input["metric"][:-1]
        self._set_logger()
        self._sourcetype = f"{self._source}:{metric}"
        self._logs_delay = int(input.get("logs_delay"))
        start_date = input.get("start_date")
        end_date = input.get("end_date")
        self._query_window_size = int(input.get("query_window_size"))

        try:
            if not start_date:
                msg = "Start Date is required but not provided."
                utils.add_ucc_error_logger(
                    self.logger,
                    CONFIGURATION_ERROR,
                    ValueError(msg),
                    exc_label=UCC_EXECPTION_EXE_LABEL.format("configuration"),
                    msg_before=msg,
                )
                raise ValueError(msg)

            self._initialise_kvstore_checkpoint(metric, start_date)
            self._handle_migration(metric)
            self.event_collector = utils.EventCollector(
                ew, self._session_key, input, self.logger
            )
            self._get_auth_type()
            self.logger.info(f"Starting data collection")

            if metric == "log":
                total_event_counter = self.stream_logs_data(
                    self._checkpoint_data["start_date"], end_date
                )
            else:
                total_event_counter = self.stream_data(metric, ew, input)

            self.logger.info(
                "Total {} events ingested : {}".format(metric, total_event_counter)
            )
            self.logger.info("Data collection completed")
        except Exception as e:
            msg = f"Exception raised during data ingestion: {str(e)}\n{traceback.format_exc()}"
            utils.add_ucc_error_logger(
                self.logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=UCC_EXECPTION_EXE_LABEL.format("general"),
                msg_before=msg,
            )
            raise

    def stream_data(self, metric, ew, input):
        url = None
        total_event_counter = 0
        while True:
            response, is_alive, next_url = self.event_collector.fetch_events(
                self._checkpoint_data["ts"], url
            )
            if not response or response.status_code not in (200, 201):
                sys.exit(1)

            raw_events = response.json()
            event_counter = 0
            for raw_event in raw_events:
                if metric in ["app", "group"]:
                    try:
                        self.event_collector.fetch_enrichment_data(response, raw_event)
                    except Exception as e:
                        raise RuntimeError(
                            f"Failed to fetch enrichment data for {metric} "
                            f"event id={raw_event.get('id')}"
                        ) from e
                if metric != "log":  # metric in ['app', 'group', 'user']
                    raw_event.pop("_links", None)
                    if metric == "user":
                        time = (
                            datetime.datetime.strptime(
                                raw_event["lastUpdated"], "%Y-%m-%dT%H:%M:%S.%fZ"
                            )
                            .replace(tzinfo=datetime.timezone.utc)
                            .timestamp()
                        )
                    elif metric == "group":
                        time = (
                            datetime.datetime.strptime(
                                max(
                                    raw_event["lastUpdated"],
                                    raw_event["lastMembershipUpdated"],
                                ),
                                "%Y-%m-%dT%H:%M:%S.%fZ",
                            )
                            .replace(tzinfo=datetime.timezone.utc)
                            .timestamp()
                        )
                    else:
                        time = None  # metric == "app"
                        collect_uris = int(input.get("collect_uris", 1))
                        if collect_uris == 0:
                            self.logger.debug("Removing redirect URIs if any")
                            utils.remove_redirect_uris(raw_event, self.logger)

                try:
                    event = smi.Event(
                        data=json.dumps(raw_event),
                        sourcetype=self._sourcetype,
                        time=time,
                        index=self._index,
                        host=self._eventhost,
                    )
                    ew.write_event(event)
                    event_counter = event_counter + 1
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to ingest {metric} event id={raw_event.get('id')}"
                    ) from e
            total_event_counter = total_event_counter + event_counter
            self._log_ingested_events(event_counter)

            # Collect data using Next link for Users, Apps, Groups
            if metric != "log":
                url = next_url

            self._checkpoint_data = self.event_collector.update_timestamp(
                metric, raw_events, self._checkpoint_data
            )

            if metric != "app":
                self.save_checkpoint()

            if not is_alive:
                break
        return total_event_counter

    def _get_auth_type(self):
        """
        Set _eventhost based on the auth_type selected
        """
        self.logger.debug(
            f"Auth Type of selected account - '{self._global_account}' is {self.event_collector.auth_type}"
        )
        self._eventhost = self.event_collector.account_domain

    def _normalize_time_range(self, start_time: datetime, end_time: datetime):
        """
        Yield tuples of start and end times that represent hourly intervals within the
        given time range.

        Args:
            start_time (datetime): The start time of the time range.
            end_time (datetime): The end time of the time range.

        Yields:
            Tuple[datetime, datetime]: A tuple containing the start and end times of an
            hourly interval within the time range.
        """
        delta = datetime.timedelta(seconds=self._query_window_size)
        while end_time - start_time > delta:
            _end_time = start_time + delta
            yield start_time, _end_time
            start_time = _end_time
        yield start_time, end_time

    def _get_relative_time(self, **kwargs):
        """
        Args:
            days/hours/mins...
            example: days=7,hours=4
                    _get_relative_time(days=4, hours=3)
                    _get_relative_time(days=4)

        Returns:
            Tuple[datetime, datetime]: relative time and current time
        """
        now = datetime.datetime.fromtimestamp(self._now(), tz=datetime.timezone.utc)
        return now - datetime.timedelta(**kwargs), now

    def _get_timerange(self, start_date, end_date):
        """
        Get the time datatype from string type
        """
        return utils.string_to_time(self._time_format, start_date), end_date

    def _calculate_end_date(self, **kwargs):
        """
        Caculate end_date applying buffer
        """
        return (
            datetime.datetime.fromtimestamp(self._now(), tz=datetime.timezone.utc)
            - datetime.timedelta(**kwargs)
        ).replace(tzinfo=None)

    def _get_end_date(self, start_date, end_date, next_link):
        """
        Get end_date based on certain circumstances
        If next_link found in checkpoint, make sure end_date would be same
        as it was at the time of making the API call.
        """
        self.logger.debug(
            f"Getting end_date: {end_date}, start_date: {start_date}, next_link: {next_link}"
        )
        is_user_provided_endate = False
        if next_link and self._checkpoint_data.get("end_date"):
            end_date = utils.string_to_time(
                self._time_format, self._checkpoint_data.get("end_date")
            )
        elif end_date:
            is_user_provided_endate = True
            if self._checkpoint_data.get("status") == "completed":
                self.logger.info(
                    "Events are already ingested for input {} between {} to {}.".format(
                        "log type", start_date, end_date
                    )
                )
                self.logger.info("Data collection completed")
                sys.exit(0)
            end_date = utils.string_to_time(self._time_format, end_date)
        else:
            end_date = self._calculate_end_date(seconds=self._logs_delay)
        self.logger.debug(
            f"Done fetching end_date. Is user_provided_end_date: {is_user_provided_endate}"
        )
        return end_date, is_user_provided_endate

    def stream_logs_data(self, start_date, end_date):
        """
        Handle data ingestion for logs metric
        """
        next_link = self._checkpoint_data.get("next_link")
        end_date, is_user_provided_endate = self._get_end_date(
            start_date, end_date, next_link
        )
        _start_date, _end_date = self._get_timerange(start_date, end_date)
        self.logger.info(
            f"start_date after _get_timerange - {_start_date}, end_date - {_end_date}"
        )
        total_event_counter = 0

        # loop through the timerange in batches and make API call to fetch events
        for _start_date, _end_date in self._normalize_time_range(
            _start_date, _end_date
        ):
            _start_date = utils.time_to_string(self._time_format, _start_date)
            _end_date = utils.time_to_string(self._time_format, _end_date)
            self.logger.info(
                f"start fetching data for start_date - {_start_date}, and end_date - {_end_date}"
            )
            batchwise_events_count = 0
            try:
                while True:
                    events, next_link = self.event_collector.fetch_log_events(
                        _start_date, _end_date, next_link
                    )
                    self._cache = {
                        "start_date": _start_date,
                        "end_date": _end_date,
                        "next_link": next_link,
                    }
                    self.ingest_events(events)
                    total_event_counter += len(events)
                    batchwise_events_count += len(events)
                    self._log_ingested_events(len(events))
                    if not next_link:
                        self._cache["start_date"] = _end_date
                        self._cache.pop("end_date")
                        self._cache.pop("next_link")
                        break
                self._log_events_count(total_event_counter, batchwise_events_count)
            except Exception as e:
                self._log_events_count(total_event_counter, batchwise_events_count)
                msg = f"Exception raised: {str(e)}, saving the checkpoint info"
                utils.add_ucc_error_logger(
                    self.logger,
                    GENERAL_EXCEPTION,
                    e,
                    exc_label=UCC_EXECPTION_EXE_LABEL.format("general"),
                    msg_before=msg,
                )
                self.save_checkpoint()
                sys.exit(1)

            # saving the checkpoint on every batch completion
            self.save_checkpoint()
        self._handle_onetime_collection(is_user_provided_endate)
        return total_event_counter

    def _log_events_count(self, total_event_counter, batchwise_events_count):
        self.logger.info(
            f"Total event ingested - {total_event_counter}, Events ingested in this batch - {batchwise_events_count}"
        )

    def _handle_onetime_collection(self, is_user_provided_endate):
        """
        If data collection is for specific timerange only.
        User provided end_date found.
        """
        if is_user_provided_endate:
            self.logger.info(
                "User provided End date found, updating status as completed"
            )
            self._cache["status"] = "completed"
            self.save_checkpoint()

    def save_checkpoint(self):
        try:
            self.logger.debug("Saving Checkpoint Info to KVStore")
            checkpoint_info = self._cache if self._cache else self._checkpoint_data
            self._checkpointer[self._checkpoint_name] = checkpoint_info
            self.logger.debug(
                f"Checkpoint updated for {self._checkpoint_name} to : {checkpoint_info}"
            )
        except Exception as e:
            msg = (
                f"Failed to update the checkpoint details. Exception raised - {str(e)}"
            )
            utils.add_ucc_error_logger(
                self.logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=UCC_EXECPTION_EXE_LABEL.format("checkpoint"),
                msg_before=msg,
            )
            raise

    def ingest_events(self, events):
        """
        Ingest events in splunk using classicEventWriter() of solnlib
        """
        self.classic_ew.write_events(
            [
                self.classic_ew.create_event(
                    data=json.dumps(event),
                    time=datetime.datetime.strptime(
                        event["published"], "%Y-%m-%dT%H:%M:%S.%fZ"
                    )
                    .replace(tzinfo=datetime.timezone.utc)
                    .timestamp(),
                    sourcetype=self._sourcetype,
                    host=self._eventhost,
                    index=self._index,
                )
                for event in events
            ]
        )


if __name__ == "__main__":
    exit_code = OKTA_IDENTITY_CLOUD().run(sys.argv)
    sys.exit(exit_code)

#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import os
import sys
import json
import pytz
import traceback
import signal
import import_declare_test  # noqa
import jira_cloud_utils as utils
import jira_cloud_consts as jcc
from datetime import datetime, timedelta
from jira_cloud_connect import Connect
from splunklib import modularinput as smi
from jira_cloud_checkpoint import JiraCloudCheckpoint as Checkpoint


class JiraIssuesCollector:
    """Class for collecting Jira Issues"""

    def __init__(self, event_writer, config, logger, proxy):
        self.event_writer = event_writer
        self.config = config
        self.logger = logger
        self.connect = Connect(logger=logger, proxy=proxy)
        self.checkpoint_updated = False
        self.event_ingested = 0

    def exit_gracefully(self, signum, frame):
        """This method handles sigterm and updates the checkpoint"""

        self.logger.info(
            "Execution about to get stopped for input '{}' due to SIGTERM.".format(
                self.config["input_name"]
            )
        )
        try:
            if not self.checkpoint_updated and self.event_ingested:
                self.logger.info(
                    "Total events received = {} | Total events ingested = {}".format(
                        self.event_received, self.event_ingested
                    )
                )
                self.logger.info(
                    "Updating the checkpoint before exiting gracefully for the input: {}".format(
                        self.config["input_name"]
                    )
                )
                ckpt_date = self.convert_string_to_datetime(
                    self.event_time, date_format=jcc.JIRA_EVENT_DATE_FORMAT
                )
                self.save_checkpoint(ckpt_date, self.event_time)

        except Exception as exc:
            msg = "Unable to save checkpoint before SIGTERM termination. Error: {}".format(
                exc
            )
            utils.add_ucc_error_logger(
                logger=self.logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=exc,
                exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format("jira_cloud_issues_input"),
                msg_before=msg,
            )
        sys.exit(0)

    def collect_events(self):
        """This method collects the jira issue events"""

        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

        # for windows machine
        if os.name == "nt":
            signal.signal(signal.SIGBREAK, self.exit_gracefully)

        try:
            self.checkpoint = Checkpoint(
                logger=self.logger,
                input_name=jcc.KVSTORE_COLLECTION_NAME,
                session_key=self.config.get("session_key"),
            )
            self.checkpoint_data = self.checkpoint.get_checkpoint_data(
                self.config.get("input_name")
            )
        except Exception as e:
            msg = "Error while fetching checkpoint information. Reason: {}".format(
                traceback.format_exc()
            )
            utils.add_ucc_error_logger(
                logger=self.logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format("jira_cloud_issues_input"),
                msg_before=msg,
            )
            sys.exit(1)

        if self.checkpoint_data:
            self.start_date = self.checkpoint_data["startDate"]
            self.last_event_ts = self.checkpoint_data["last_event_timestamp"]
        else:
            self.start_date = self.config.get("start_date")
            self.last_event_ts = ""

        self.params = dict()
        self.params["fields"] = jcc.JIRA_ISSUE_DEFAULT_FIELDS_PARAM
        self.timezone = self.get_system_timezone()
        self.logger.debug(
            "The user's system default timezone is {}".format(self.timezone)
        )

        if self.config.get("include"):
            self.params["fields"] = "{},{}".format(
                self.config.get("time_field"), self.config.get("include")
            )
        elif self.config.get("exclude"):
            if self.config.get("time_field") in self.config.get("exclude"):
                self.logger.error(
                    'Cannot exclude the time field "{}" which will be used for checkpointing'.format(
                        self.config.get("time_field")
                    )
                )
                sys.exit(1)
            else:
                exclude_fields_list = [
                    field
                    for field in self.config.get("exclude", []).split(",")
                    if field not in jcc.JIRA_ISSUE_DEFAULT_EXCLUDED_FIELDS
                ]
                exclude_fields = ",".join(
                    f"-{field.strip()}" for field in exclude_fields_list
                )
                if exclude_fields:
                    self.params["fields"] = self.params["fields"] + "," + exclude_fields

        self.logger.info("Starting data collection.")

        # Collecting data for minute window to avoid data duplication
        if self.last_event_ts:
            self.logger.info("Collecting data for 1 minute time window.")
            self.compute_start_end_date()
            jql_query = self.build_jql_query()
            self.params["jql"] = jql_query
            self.jira_issues_collector()
            self.last_event_ts = ""
            self.start_date = self.end_date

        self.compute_start_end_date()
        jql_query = self.build_jql_query()
        self.params["jql"] = jql_query
        self.jira_issues_collector()

        self.logger.info("End of Data Collection.")

    def compute_start_end_date(self):
        """This method computes the start_date and end_date for collecting the data"""
        if isinstance(self.start_date, str):
            self.start_date = self.convert_string_to_datetime(self.start_date)
        if self.last_event_ts:
            self.end_date = self.start_date + timedelta(minutes=1)
        else:
            self.end_date = datetime.utcnow()

    def jira_issues_collector(self):
        """This method collects the jira issues"""

        self.last_page = 0
        self.event_ingested = 0
        self.event_received = 0
        self.logger.info("Query parameters = {}".format(self.params))

        while not self.last_page:
            self.checkpoint_updated = False
            response = self.connect.get(
                domain=self.config.get("domain"),
                endpoint=jcc.JIRA_ISSUES_SEARCH_ENDPOINT,
                username=self.config.get("username"),
                token=self.config.get("token"),
                params=self.params,
            )

            response = response.json()
            events = response.get("issues")
            total_events = len(events)

            if total_events > 0 and self.last_event_ts:
                last_event_ts_dt = self.convert_string_to_datetime(
                    self.last_event_ts, date_format=jcc.JIRA_EVENT_DATE_FORMAT
                )
                last_ts = events[-1]["fields"][self.config["time_field"]]
                last_ts = self.convert_string_to_datetime(
                    last_ts, date_format=jcc.JIRA_EVENT_DATE_FORMAT
                )

                if last_ts <= last_event_ts_dt:
                    self.logger.info(
                        "Events of this page are already ingested in the previous invocation. Hence, skipping this page."
                    )
                    if not response["isLast"]:
                        self.params["nextPageToken"] = response["nextPageToken"]
                        continue
                    else:
                        self.save_checkpoint(self.end_date)
                        self.checkpoint_updated = True
                        break
                else:
                    events = self.filter_duplicate_events(events, last_event_ts_dt)

            if events:
                if not response["isLast"]:
                    self.params["nextPageToken"] = response["nextPageToken"]
                else:
                    self.last_page = 1
                self.event_received += total_events
                self.ingest_events(events)
            else:
                self.save_checkpoint(self.end_date)
                self.checkpoint_updated = True
                break

        self.logger.info(
            "Total events received = {} | Total events ingested = {}".format(
                self.event_received, self.event_ingested
            )
        )

    def filter_duplicate_events(self, events, last_event_ts_dt):
        """This method filters the duplicate events and creates a list of fresh events to be ingested

        Args:
            events (list): list of total events
            last_event_ts_dt (Object) : last event's timestamp found from checkpoint

        Returns:
            new_events (list): list of fresh events to be ingested
        """

        for idx in range(len(events)):
            event_dt = self.convert_string_to_datetime(
                events[idx]["fields"][self.config["time_field"]],
                date_format=jcc.JIRA_EVENT_DATE_FORMAT,
            )

            if event_dt > last_event_ts_dt:
                return events[idx:]

    def ingest_events(self, events):
        """This method writes events to the eventwriter and updates the checkpoint.

        Args:
            events (list): list of events to be ingested
        """

        try:
            for raw_event in events:
                self.event_time = raw_event["fields"][self.config["time_field"]]
                formatted_event_date = self.convert_string_to_datetime(
                    self.event_time, date_format=jcc.JIRA_EVENT_DATE_FORMAT
                )
                etime = self.convert_timezone(formatted_event_date).timestamp()

                smi_event = smi.Event(
                    data=json.dumps(raw_event),
                    sourcetype=jcc.JIRA_ISSUES_SOURCETYPE,
                    source=self.config.get("input_name"),
                    host=Connect.build_hostname(domain=self.config.get("domain")),
                    index=self.config.get("index"),
                    time=etime,
                )
                self.event_writer.write_event(smi_event)
                self.event_ingested += 1
            utils.log_events_ingested(
                logger=self.logger,
                modular_input_name=f'{self.config.get("input_type")}://{self.config.get("input_name")}',
                sourcetype=jcc.JIRA_ISSUES_SOURCETYPE,
                n_events=len(events),
                index=self.config.get("index"),
                account=self.config.get("api_token"),
                host=Connect.build_hostname(domain=self.config.get("domain")),
                license_usage_source=self.config.get("input_name"),
            )
        except Exception as e:
            msg = "Error writing event to Splunk: {}".format(traceback.format_exc())
            utils.add_ucc_error_logger(
                logger=self.logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format("jira_cloud_issues_input"),
                msg_before=msg,
            )
            sys.exit(1)

        finally:
            if not self.last_page:
                self.save_checkpoint(formatted_event_date, self.event_time)
            else:
                self.save_checkpoint(self.end_date)

            self.checkpoint_updated = True

    def build_jql_query(self):
        """This method build the jql query for data collection

        Returns:
            jql_query (str): jql_query
        """

        filter_data = (
            "AND " + self.config.get("filter_data")
            if self.config.get("filter_data")
            else ""
        )

        self.logger.debug(
            "Converting start_date and end_date to {} timezone".format(self.timezone)
        )
        start_date_tz = self.convert_timezone(self.start_date, self.timezone)
        end_date_tz = self.convert_timezone(self.end_date, self.timezone)

        query_start_date = self.convert_datetime_to_string(start_date_tz)
        query_end_date = self.convert_datetime_to_string(end_date_tz)

        # Quote each project key to avoid JQL errors when a project key
        # matches a JQL reserved word (e.g. "AS", "IN", "OR").
        raw_projects = self.config.get("projects")
        quoted_projects = ",".join(
            '"{}"'.format(p.strip()) for p in raw_projects.split(",")
        )

        jql_query = jcc.JQL_QUERY_FORMAT.format(
            quoted_projects,
            filter_data,
            self.config.get("time_field"),
            query_start_date,
            self.config.get("time_field"),
            query_end_date,
            self.config.get("time_field"),
        )

        return jql_query

    def get_system_timezone(self):
        """This method fetches the timezone of the jira user

        Returns:
            timezone (str): timezone of the jira user
        """

        response = self.connect.get(
            domain=self.config.get("domain"),
            endpoint=jcc.JIRA_ISSUES_GET_TIMEZONE,
            username=self.config.get("username"),
            token=self.config.get("token"),
        )
        response = response.json()
        return response["timeZone"]

    def save_checkpoint(self, checkpoint_date, event_ts=""):
        """This method updates the checkpoint"""
        converted_end_date = self.convert_timezone(checkpoint_date)
        converted_end_date = self.convert_datetime_to_string(converted_end_date)
        checkpoint_data = {
            "startDate": converted_end_date,
            "last_event_timestamp": event_ts,
        }
        self.checkpoint.update_checkpoint_data(
            self.config.get("input_name"), checkpoint_data
        )

    def convert_timezone(self, date, timezone="UTC"):
        """This method converts the timezone of the given date

        Args:
            date (Object): date to be convereted provided timezone
            timezone (str) : timezone in which the event has to be converted

        Returns:
            date (Object): date convereted in provided timezone
        """
        if date.tzinfo is None:
            utc = pytz.UTC
            date = utc.localize(date)
        timezone = pytz.timezone(timezone)
        converted_date = date.astimezone(timezone)
        return converted_date

    def convert_datetime_to_string(self, date, date_format=jcc.JIRA_QUERY_DATE_FORMAT):
        """This method converts the datetime object to string

        Args:
            date (Object): date to be convereted in str in provided date format
            date_format (Any) : date format like "%Y-%m-%d %H:%M"

        Returns:
            convereted_date (str): date converted in string
        """
        return datetime.strftime(date, date_format)

    def convert_string_to_datetime(self, date, date_format=jcc.JIRA_QUERY_DATE_FORMAT):
        """This method converts the string to datetime object

        Args:
            date (str): date to be convereted in datetime object
            date_format (Any) : date format like "%Y-%m-%d %H:%M"

        Returns:
            convereted_date (Object): date converted in datetime object
        """
        return datetime.strptime(date, date_format)


class JIRA_CLOUD_ISSUES_INPUT(smi.Script):
    def __init__(self):
        super(JIRA_CLOUD_ISSUES_INPUT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("jira_cloud_issues_input")
        scheme.description = "Jira Issues"
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
                "api_token",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "projects",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "start_date",
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
                "include",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "exclude",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "time_field",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "filter_data",
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, event_writer):
        session_key = self._input_definition.metadata["session_key"]
        for input_name, input_items in inputs.inputs.items():
            input_items["input_name"] = input_name.split("://")[-1]
            input_items["input_type"] = input_name.split("://")[0]

        logfile_name = jcc.JIRA_CLOUD_ISSUES_LOGFILE_PREFIX + input_items["input_name"]
        logger = utils.set_logger(session_key, logfile_name)
        try:
            logger.info("Modular Input Started.")
            api_token = input_items.get("api_token")
            api_token_details = utils.get_api_token_details(
                session_key, logger, api_token
            )

            logger.debug("Getting proxy settings")
            proxy_settings = utils.get_proxy_settings(session_key, logger)

            input_items["session_key"] = session_key
            input_items.update(api_token_details)

            jira_issues_collector = JiraIssuesCollector(
                event_writer, input_items, logger, proxy_settings
            )
            jira_issues_collector.collect_events()
            logger.info("Modular Input Exited.")

        except Exception as e:
            msg = "Error while streaming events for input {}: {}".format(
                input_name, traceback.format_exc()
            )
            utils.add_ucc_error_logger(
                logger=logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format("jira_cloud_issues_input"),
                msg_before=msg,
            )


if __name__ == "__main__":
    exit_code = JIRA_CLOUD_ISSUES_INPUT().run(sys.argv)
    sys.exit(exit_code)

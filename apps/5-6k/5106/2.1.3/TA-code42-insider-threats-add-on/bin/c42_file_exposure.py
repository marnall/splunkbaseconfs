import lib_path
import sys
from datetime import timedelta
from datetime import datetime
import time
from _incydr_sdk.file_events.client import InvalidQueryException

from splunktaucclib.modinput_wrapper.base_modinput import BaseModInput
from splunklib.modularinput.argument import Argument
from c42_util import (
    Code42ModInput,
    get_app_version,
    get_now,
    InvalidIntervalException,
)
from incydr import EventQuery
from requests import HTTPError, Timeout
from dateutil import parser

C42_FILE_EVENT_MIN_POLLING_INTERVAL = 300
C42_FILE_EVENT_INITIAL_DAYS_BACK = 90
C42_EVENT_SORT_KEY = "event.inserted"
C42_EVENT_SORT_DIR = "asc"

version = get_app_version()


class InvalidSavedSearchException(Exception):
    def __init__(self, saved_search_id):
        self.saved_search_id = saved_search_id

    def __repr__(self):
        return f"InvalidSavedSearchException: {self.saved_search_id} not found."


class FileExposureModInput(Code42ModInput, BaseModInput):

    checkpoint_key = None
    checkpoint_key_timestamp_fallback = None

    def __init__(self):
        super().__init__("ta_code42_insider_threats_add_on", "c42_file_exposure", False)

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super().get_scheme()
        scheme.title = "File Exposure"
        scheme.description = "Go to the add-on's configuration UI and configure modular inputs under the Inputs menu."
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(
            Argument("name", title="Name", description="", required_on_create=True)
        )
        scheme.add_argument(
            Argument(
                "delay_interval",
                title="Delay Interval",
                description="Do not ingest events newer than this number of seconds.",
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                "c42_account",
                title="Code42 API Client",
                description="The Code42 API Client used to query for file events. Must include the 'File Events Read' permission. Your product plan must also include full API access.",
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                "min_risk_score",
                title="Minimum Risk Score",
                description="The minimum risk score an event must have in order to be ingested. Setting this value to 0 will cause all events to be ingested.",
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            Argument(
                "saved_search_id",
                title="Saved Search ID",
                description=(
                    "The ID of a saved file event search. For ingesting custom file event queries (overrides min_risk_score value)."
                ),
            )
        )
        scheme.add_argument(
            Argument(
                "page_size",
                title="Page Size",
                description=("The page size to use when retrieving events."),
            )
        )
        scheme.add_argument(
            Argument(
                "days_back",
                title="Days back",
                description=("Days back to query. Events older than this number of days will not be ingested."),
            )    
        )
        return scheme

    def get_app_name(self):
        return "TA-code42-insider-threats-add-on"

    def get_account_fields(self):
        return ["c42_account"]

    def get_checkbox_fields(self):
        return []

    def get_global_checkbox_fields(self):
        return []

    def validate_input(self, definition):
        """validate the input stanza"""
        if int(definition.parameters["interval"]) < C42_FILE_EVENT_MIN_POLLING_INTERVAL:
            raise InvalidIntervalException(
                "c42_file_exposure", C42_FILE_EVENT_MIN_POLLING_INTERVAL
            )

    def collect_events(self, ew, retry_seconds=60):
        """The main method that creates events in Splunk from Code42 File Events."""

        self.checkpoint_key = self.get_input_stanza_names()
        self.checkpoint_key_timestamp_fallback = (
            self.checkpoint_key + "-timestamp-fallback"
        )
        previous_version = self.get_check_point("c42_app_version")
        if previous_version != version:
            self.handle_upgrade(previous_version)

        try:
            self.log_info(f"{self.checkpoint_key} - Preparing to search for new Code42 File Exposure events.")
            self.raise_interval_error_if_needed(
                C42_FILE_EVENT_MIN_POLLING_INTERVAL, "File Exposure"
            )

            def _handle_v2_response(response):
                try:
                    events = response.file_events
                    num_events = len(events)
                    self.log_debug(f"{self.checkpoint_key} - Query in progress. Current page events: {num_events}. Total events: {response.total_count}. Current page token: {response.next_pg_token}")
                    if num_events > 0:
                        self.log_info(f"{self.checkpoint_key} - Processing {num_events} V2 file events beginning from {events[0].event.ingested.isoformat()}.")
                    else:
                        self.log_info(f"{self.checkpoint_key} - No new events to process.")
                    for event_data in events:
                        self.write_event(ew, event_data)
                    if num_events > 0:
                        last_event_id = events[-1].event.id
                        self.save_check_point(self.checkpoint_key, last_event_id)
                        # event insertion timestamp is a nullable field
                        last_event_insertion_ts = events[-1].event.inserted.timestamp()
                        if last_event_insertion_ts:
                            self.save_check_point(
                                self.checkpoint_key_timestamp_fallback,
                                last_event_insertion_ts,
                            )
                except Exception as err:
                    self.log_error(repr(err))

            sdk = self.initialize_sdk()

            delay_interval = self.get_arg("delay_interval")
            min_risk_score = self.get_arg("min_risk_score")
            saved_search_id = self.get_arg("saved_search_id")
            page_size = self.get_arg("page_size")
            checkpoint = self.get_check_point(self.checkpoint_key)
            days_back = self.get_arg("days_back")
            try:
                if days_back:
                    days_back = int(self.get_arg("days_back"))
                else:
                    days_back =  C42_FILE_EVENT_INITIAL_DAYS_BACK
            except ValueError:
                days_back = C42_FILE_EVENT_INITIAL_DAYS_BACK

            try:
                if delay_interval:
                    query_end_date = get_now() - timedelta(seconds = int(delay_interval))
                else:
                    query_end_date = get_now()
            except ValueError:
                query_end_date = get_now()


            # older app versions stored checkpoint as float timestamp.
            # we handle those here until the next run containing events will store checkpoint as the last eventId
            if isinstance(checkpoint, (int, float)):
                start_date = checkpoint
                checkpoint = ""
            else:
                initial_days_back = get_now() - timedelta(
                    days=days_back
                )
                start_date = initial_days_back.timestamp()

            if not saved_search_id:
                try:
                    min_risk_score = int(min_risk_score)
                except (ValueError, TypeError):
                    self.log_warning(
                        f"{self.checkpoint_key} - Error handling 'min_risk_score' value, defaulting to '1'. Bad value: {min_risk_score}"
                    )
                    min_risk_score = 1
                # Minimum risk score is a "greater than or equal to" but the SDK 
                # only offers "greater than", so subtract 1.
                modified_risk_score = min_risk_score - 1
                query = EventQuery(
                    sort_key=C42_EVENT_SORT_KEY
                ).date_range(term="event.inserted", start_date=start_date, end_date=query_end_date).greater_than("risk.score", modified_risk_score)
            else:
                try:
                    saved_search = self.validate_saved_search_id(saved_search_id, sdk)
                    query = EventQuery().from_saved_search(saved_search=saved_search)
                    # Saved searches can have sort direction and key which might mess
                    # up our checkpoint handling, so clear those.
                    query.sort_dir = C42_EVENT_SORT_DIR
                    query.sort_key = C42_EVENT_SORT_KEY

                    if delay_interval and int(delay_interval) > 0:
                        query = EventQuery(sort_key=C42_EVENT_SORT_KEY
                            ).date_range(term="event.inserted", end_date=query_end_date).subquery(query)
                except HTTPError as e:
                    if "404" in str(e):
                        raise InvalidSavedSearchException(saved_search_id)
                    else:
                        raise e

            if page_size:
                query.page_size = page_size

            if isinstance(checkpoint, str):
                query.page_token = checkpoint

            

            self.log_info(
                f"{self.checkpoint_key} - Executing Code42 search -- query: {query}, events on or after: {checkpoint}"
            )

            try:
                response = sdk.file_events.v2.search(query)
            except (Timeout, HTTPError, InvalidQueryException) as e:
                self.log_error_with_traceback(e)
                # try again
                time.sleep(retry_seconds)
                try:
                    response = sdk.file_events.v2.search(query)
                except InvalidQueryException as e:
                    self.log_error_with_traceback(e)

                    # strip out any timestamp filters from the query, since we'll be supplying our own
                    groups = [
                        x
                        for x in query.groups
                        if "event.inserted" not in [y.term for y in x.filters]
                    ]

                    # If the page token is invalid,
                    # we want to use the insertion timestamp of the last checkpointed event as a fallback.
                    ts_checkpoint = self.get_check_point(
                        self.checkpoint_key_timestamp_fallback
                    )
                    if ts_checkpoint:
                        if isinstance(ts_checkpoint, (int, float)):
                            ts_checkpoint_seconds = ts_checkpoint
                        else:
                            ts_checkpoint_seconds = parser.parse(ts_checkpoint).timestamp()
                        self.log_error(
                            f"{self.checkpoint_key} - File event search returned a 400 Invalid Page Token Error for token '{checkpoint}'. "
                            f"Falling back to last checkpointed event insertion timestamp '{ts_checkpoint_seconds}'."
                        )
                        start_date = ts_checkpoint_seconds
                    else:
                        self.log_error(
                            f"{self.checkpoint_key} - File event search returned a 400 Invalid Page Token Error for token '{checkpoint}'. "
                            f"Passing blank checkpoint and querying for events matching filters from the last {days_back} days."
                        )
                        initial_days_back = get_now() - timedelta(
                            days=days_back
                        )
                        start_date = initial_days_back.timestamp()

                    query = EventQuery(groups=groups).date_range(term="event.inserted", start_date=start_date)
                    if page_size:
                        query.page_size = page_size
                    response = sdk.file_events.v2.search(query)

            _handle_v2_response(response)
            while response.next_pg_token is not None:
                response = sdk.file_events.v2.search(query)
                _handle_v2_response(response)

        except KeyError as err:
            # version 1.2.0+ requires api clients for authentication.
            # Notify after upgrade if it hasn't been re-configured yet.
            if err.args[0] == "api_client_id":
                self.notify_api_client_config_required()
            else:
                raise err

        except Exception as e:
            self.log_error_with_traceback(e)

    def validate_saved_search_id(self, saved_search_id, sdk):
        try:
            return sdk.file_events.v2.get_saved_search(saved_search_id)
        except:
            raise InvalidSavedSearchException(saved_search_id)


    def handle_upgrade(self, previous_version):
        """Logic to handle configuration changes after upgrades."""
        self.log_info(f"handle_upgrade:: previous_version={previous_version}")
        # prior to 1.4.0 we weren't storing version
        if previous_version is None:
            checkpoint = self.get_check_point(self.checkpoint_key)
            if checkpoint:
                account_name = self.get_arg("c42_account")["name"]
                data = {
                    "min_risk_score": self.get_arg("min_risk_score"),
                    "saved_search_id": self.get_arg("saved_search_id"),
                    "index": self.get_arg("index"),
                    "c42_account": account_name,
                }
                self.save_check_point("c42_app_version", version)
                self.update_mod_input_config(**data)
        else:
            self.save_check_point("c42_app_version", version)


if __name__ == "__main__":
    exitcode = FileExposureModInput().run(sys.argv)
    sys.exit(exitcode)

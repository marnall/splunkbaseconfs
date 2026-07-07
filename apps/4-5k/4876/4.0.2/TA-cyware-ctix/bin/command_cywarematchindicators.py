"""Custom search command for Cyware CTIX indicator correlation."""

import sys
import time
import traceback
import datetime
import six
import hashlib
import ta_cyware_ctix_declare  # noqa: F401

from ta_cyware_ctix.kvstore_helper import (
    IndicatorManager,
    KVStoreUnavailableError,
)
from ta_cyware_ctix.logging_helper import get_logger
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option

logger = get_logger("correlation_command")

REDIRECT_TO_LOG_FILE_MSG = f"See {'ta_cyware_ctix_correlation_command.log'} for more details."


class StopExecutionError(Exception):
    """Useful for stopping execution and break out from deep inside recursive loop."""

    pass


@Configuration()
class CywareMatchIndicatorsCommand(EventingCommand):
    """Cyware CTIX match indicators custom command."""

    indicator_type = Option(name="indicator_type", require=True)

    is_first_invocation = True
    indicator_mgr = None
    start_time = None
    total_events = 0
    past_matched_indicators_dict = {}
    needle = set()
    final_indicators = []

    def _write_error(self, msg):
        """Log error message to Splunk UI from where this custom command was triggered."""
        self.write_error(f"{msg} {REDIRECT_TO_LOG_FILE_MSG}")
        exit(0)

    def validate(self, indicator_type):
        """Validate the provided indicator_type field."""
        valid_types = [
            "file",
            "url",
            "domain_name",
            "ipv4_addr",
            "ipv6_addr",
            "windows_registry_key",
            "email_addr",
            "autonomous_system",
            "network_traffic",
        ]
        if indicator_type not in valid_types:
            logger.error(
                f"message=validate_fields_error | Given indicator_type is not valid: {indicator_type}"
            )
            self._write_error(
                f"Not valid indicator_type. Valid types: {', '.join(valid_types)}"
            )
        return True

    def get_multi_value_fields(self, field_values, value):
        """Return field values from multi value fields."""
        for item in value:
            if isinstance(item, six.string_types) and item.strip() and item != "-":
                field_values.add(item.strip())

    def get_field_value_set(self, event):
        """Return field values."""
        field_values = set()
        for key, value in event.items():
            if key != "index" and key != "count":
                if (
                    isinstance(value, six.string_types)
                    and value.strip()
                    and value != "-"
                ):
                    field_values.add(value.strip())
                elif isinstance(value, (list, tuple, set)):
                    self.get_multi_value_fields(field_values, value)
        return field_values

    def correlate(self, events):
        """Perform correlation on given Splunk events and ingest into matched lookup."""
        count = 0
        new_matched_indicators_count = {}
        new_matched_indicators_index = {}
        already_matched_indicators = set()

        for event in events:
            count += 1
            match_count = event.get("count", 1)
            haystack = self.get_field_value_set(event)
            # Find matches using needle dictionary keys
            matched_event_results = haystack.intersection(self.needle.keys())

            for matched_event in matched_event_results:
                if matched_event in already_matched_indicators:
                    new_matched_indicators_count[matched_event] = (
                        new_matched_indicators_count.get(matched_event, 0)
                        + int(match_count)
                    )
                else:
                    new_matched_indicators_count[matched_event] = (
                        new_matched_indicators_count.get(matched_event, 0)
                        + int(match_count)
                        + self.past_matched_indicators_dict.get(matched_event, {}).get(
                            "count", 0
                        )
                    )
                new_matched_indicators_index[matched_event] = (
                    {event.get("index")}
                    .union(new_matched_indicators_index.get(matched_event, set()))
                    .union(
                        self.past_matched_indicators_dict.get(matched_event, {}).get(
                            "correlationIndices", {}
                        )
                    )
                )
                already_matched_indicators.add(matched_event)

        self.total_events += count

        ind = {}
        for indicator in new_matched_indicators_count.keys():
            needle_data = self.needle.get(indicator, {})
            ctix_id = needle_data.get("ctix_id")
            valid_until = needle_data.get("valid_until")
            ind = {
                "_key": hashlib.md5(indicator.strip().encode()).hexdigest(),
                "indicator": indicator,
                "ctix_id": ctix_id,
                "valid_until": valid_until,
                "correlationIndices": list(new_matched_indicators_index.get(indicator)),
                "lastMatchTime": self.latest_time,
                "count": new_matched_indicators_count.get(indicator),
            }
            self.final_indicators.append(ind)

    def commit(self):
        """Commit final changes back to Splunk."""
        try:
            if not len(self.final_indicators):
                return
            logger.info(
                "message=committing_matching_indicators | Committing the matching indicators ..."
            )
            self.indicator_mgr.upsert_matched_indicators(self.final_indicators)
            logger.info(
                "message=committed_matching_indicators | Committed the matching indicators: "
                f"total={len(self.final_indicators)}"
            )

        except Exception as ex:
            logger.error(
                f"message=failed_to_commit | Failed to commit matched indicators: count={len(self.final_indicators)} "
                f"error={ex}"
            )
            raise

    def initialize(self):
        """Initialize the correlation environment and load data into memory."""
        self.matched_key_field = "indicator"
        self.master_lookup_field = "indicator"

        self.indicator_mgr = IndicatorManager(
            self.indicator_type, session_key=self.session_key
        )

        logger.info("message=fetching_indicators | Fetching indicators ...")
        indicators = self.indicator_mgr.get_master_indicators_data(
            fields=[self.master_lookup_field, "ctix_id", "valid_until"]
        )

        past_matched_indicators = self.indicator_mgr.get_matched_indicators_data(
            fields=["indicator", "count", "correlationIndices"]
        )
        for indicator in past_matched_indicators:
            self.past_matched_indicators_dict.update(
                {
                    indicator.get("indicator"): {
                        "count": int(indicator.get("count", 0)),
                        "correlationIndices": set(
                            indicator.get("correlationIndices", [])
                        ),
                    }
                }
            )
        # Initialize needle as dictionary to store indicator -> ctix_id and valid_until mapping
        self.needle = {}
        for indicator in indicators:
            indicator_value = indicator.get(self.master_lookup_field)
            ctix_id = indicator.get("ctix_id")
            valid_until = indicator.get("valid_until")
            if indicator_value:
                self.needle[indicator_value] = {"ctix_id": ctix_id, "valid_until": valid_until}

        logger.info(
            f"message=fetched_indicators | Fetched indicators: count={len(self.needle)} type={self.indicator_type}"
        )

    def process_latest_time(self, latest_time):
        """Handle empty latest time when Time Range is 'All Time'."""
        if not latest_time:
            return time.time()
        else:
            return float(latest_time)

    def check_metadata_preview(self):
        """Check metadata preview."""
        if self.metadata.preview:
            return

    def transform(self, events):
        """Transform method of Eventing Command."""
        try:
            self.session_key = self.search_results_info.auth_token

            # splunklib expects this method to be of type generator else throws error
            if False:  # NOSONAR
                yield

            self.check_metadata_preview()

            if self.is_first_invocation:
                self.is_first_invocation = False
                self.start_time = time.time()
                logger.info(
                    'message=command_start_execution | Starting the "{}" command execution: earliest={} latest={} '
                    'sid={}'.format(
                        self.name,
                        datetime.datetime.fromtimestamp(self.metadata.searchinfo.earliest_time),
                        datetime.datetime.fromtimestamp(self.metadata.searchinfo.latest_time),
                        self.metadata.searchinfo.sid
                    )
                )
                logger.info(
                    f"message=received_params | Received parameters: indicator_type={self.indicator_type}"
                )
                self.latest_time = self.process_latest_time(
                    self.metadata.searchinfo.latest_time
                )

                self.validate(self.indicator_type)
                self.initialize()

                if not len(self.needle):
                    logger.info(
                        "message=no_indicators_found | No indicators were found, correlation won't be performed."
                    )
                else:
                    logger.info(
                        "message=start_correlation | Performing correlation ..."
                    )

            else:
                logger.debug(
                    "message=intermediate_call_counter | Intermediate call from Splunk"
                )

            if not len(self.needle):
                return

            self.correlate(events)

        except StopExecutionError:
            pass

        except KVStoreUnavailableError as ex:
            logger.error(
                f"message=kvstore_unavailable_error | KVStore Unavailable: {ex}"
            )
            self._write_error(f"KVStore Unavailable: {ex}")

        except Exception as ex:
            logger.error(
                f"message=unknown_error | Unknown error occurred: {traceback.format_exc()}"
            )
            self._write_error(f"Unknown Error: {ex}")

        finally:
            if self._finished:
                try:
                    self.commit()
                except KVStoreUnavailableError:
                    pass

                except Exception as ex:
                    logger.error(
                        f"message=unknown_error | Unknown error occurred: {traceback.format_exc()}"
                    )
                    self._write_error(f"Unknown Error: {ex}")

                logger.info(
                    f"message=stats_correlation | Correlation Stats: matching_indicators={len(self.final_indicators)} "
                    f"indicators={len(self.needle)} events={self.total_events}"
                )

                elapsed_seconds = time.time() - self.start_time
                logger.info(
                    f'message=command_end_execution | End of the "{self.name}" command execution. Total time taken: '
                    f'elapsed_seconds={elapsed_seconds:.3f}'
                )


dispatch(CywareMatchIndicatorsCommand, sys.argv, sys.stdin, sys.stdout, __name__)

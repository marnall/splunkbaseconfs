import sys
import time
import traceback
import datetime
import six
import hashlib

import ta_analyst1_declare  # noqa: F401
from solnlib.utils import is_true
import analyst1_helpers.kvstore as kvstore
from analyst1_logging import get_logger, log_event
import logging
from analyst1_helpers.constants import SAVEDSEARCHES_DICT
from analyst1_helpers.conf_helper import get_conf_file
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option

from utils import compute_a1_key


REDIRECT_TO_LOG_FILE_MSG = "See {} for more details.".format(
    "ta_analyst1_correlation_command.log"
)


class StopExecutionError(Exception):
    """Usefull for stopping execution and break out from deep inside recursive loop."""

    pass


@Configuration()
class Analyst1MatchIndicatorsCommand(EventingCommand):
    """Analyst1 match indicators custom command."""

    indicator_type = Option(name="indicator_type", require=True)

    is_first_invocation = True
    indicator_mgr = None
    start_time = None
    total_events = 0
    past_matched_indicators_dict = {}
    needle = set()
    final_indicators = []
    logger = None

    def _write_error(self, msg):
        """Log error message to Splunk UI from where this custom command was triggered."""
        self.write_error("{} {}".format(msg, REDIRECT_TO_LOG_FILE_MSG))
        exit(0)

    def validate(self, indicator_type):
        if indicator_type not in SAVEDSEARCHES_DICT.keys():
            self.logger.error(
                "message=invalid_indicator_type | Given indicator_type is not valid: {}".format(
                    indicator_type
                )
            )
            self._write_error("Not valid indicator_type.")
        return True

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
                    for item in value:
                        if (
                            isinstance(item, six.string_types)
                            and item.strip()
                            and item != "-"
                        ):
                            field_values.add(item.strip())
        return field_values

    def correlate(self, events):
        """Perform correlation on given Splunk events and ingest into matched lookup."""
        count = 0
        new_matched_indicators_count = dict()
        new_matched_indicators_index = dict()
        for event in events:
            count += 1
            match_Count = event.get("count") or 0
            haystack = self.get_field_value_set(event)
            matched_event_results = haystack.intersection(self.needle)
            for matched_event in matched_event_results:
                new_matched_indicators_count[matched_event] = (
                    new_matched_indicators_count.get(matched_event, 0)
                    + int(match_Count)
                    + (self.past_matched_indicators_dict.get(matched_event, {}).get("count") or 0)
                )
                index_value = event.get("index")
                index_set = {index_value} if index_value else set()
                new_matched_indicators_index[matched_event] = (
                    index_set
                    .union(new_matched_indicators_index.get(matched_event, set()))
                    .union(
                        self.past_matched_indicators_dict.get(matched_event, {}).get(
                            "correlationIndices"
                        ) or set()
                    )
                )
        self.total_events += count

        for indicator in new_matched_indicators_count.keys():
            # Ensure indicator is a string before processing
            if indicator:
                ind = {
                    "_key": hashlib.sha256(str(indicator).strip().encode()).hexdigest(),
                    "value": indicator,
                    "correlationIndices": list(new_matched_indicators_index.get(indicator) or set()),
                    "lastMatchTime": self.latest_time,
                    "count": new_matched_indicators_count.get(indicator),
                }
                self.final_indicators.append(ind)

    def commit(self):
        """Commit final changes back to Splunk."""
        try:
            if not len(self.final_indicators):
                return
            self.logger.info(
                "message=committing_matching_indicators | Committing the matching indicators ..."
            )
            self.indicator_mgr.upsert_matched_indicators(self.final_indicators)
            self.logger.info(
                "message=committed_matching_indicators |"
                " Committed the matching indicators: total={}".format(
                    len(self.final_indicators)
                )
            )

        except Exception as ex:
            self.logger.error(
                "message=failed_to_commit | Failed to commit matched indicators: count={} error={}".format(
                    len(self.final_indicators), ex
                )
            )
            raise

    def initialize(self):
        """Initialize the correlation environment and load data into memory."""
        kv_conf_stanza = get_conf_file(
            file="ta_analyst1_settings",
            stanza="splunk_rest_host",
            session_key=self.session_key,
        )
        skip_index = is_true(kv_conf_stanza.get("skip_index"))
        if skip_index:
            self.indicator_mgr = kvstore.IndicatorManager(
                self.indicator_type, session_key=self.session_key
            )
        else:
            self.indicator_mgr = kvstore.IndicatorManager(
                self.indicator_type, service=self.service
            )
        self.logger.info("message=fetching_indicators | Fetching indicators ...")
        indicators = self.get_master_indicators_data()
        past_matched_indicators = self.get_matched_indicators()
        for indicator in past_matched_indicators:
            value = indicator.get("value")
            if value:  # Skip None values
                self.past_matched_indicators_dict.update(
                    {
                        value: {
                            "count": int(indicator.get("count") or 0),
                            "correlationIndices": set(indicator.get("correlationIndices") or []),
                        }
                    }
                )
        self.logger.info(
            "message=fetched_indicator | Fetched indicators: count={} type={}".format(
                len(indicators), self.indicator_type
            )
        )
        for indicator in indicators:
            value = indicator.get("value")
            if value:  # Only add non-None values to the needle set
                self.needle.add(value)

    def get_master_indicators_data(self):
        return self.indicator_mgr.get_master_indicators_data(
            types=self.indicator_type, fields=["value"]
        )

    def get_matched_indicators(self):
        indicators = self.indicator_mgr.get_matched_indicators_data(
            types=self.indicator_type, fields=["value", "count", "correlationIndices"]
        )
        return indicators


    def process_latest_time(self, latest_time):
        """Handle empty latest time when Time Range is 'All Time'."""
        if not latest_time:
            return time.time()
        else:
            return float(latest_time)

    def transform(self, events):
        """Transform method of Eventing Command."""
        try:
            self.session_key = self.search_results_info.auth_token
            self.logger = get_logger("ta_analyst1_matchindicators")
            # splunklib expects this method to be of type generator else throws error
            if False:
                yield

            if self.metadata.preview:
                return

            if self.is_first_invocation:
                self.is_first_invocation = False
                self.start_time = time.time()

                # STRUCTURED LOGGING: Correlation start event - trackable start time
                # Before: self.logger.info('message=start_execution | Starting the "{}" command...')
                log_event(self.logger, {
                    'action': 'correlation_started',
                    'command': self.name,
                    'earliest_time': datetime.datetime.utcfromtimestamp(
                        self.metadata.searchinfo.earliest_time
                    ).isoformat(),
                    'latest_time': datetime.datetime.utcfromtimestamp(
                        self.metadata.searchinfo.latest_time
                    ).isoformat(),
                    'search_id': self.metadata.searchinfo.sid,
                    'indicator_type': self.indicator_type
                }, log_level=logging.INFO)
                self.logger.info(
                    "message=received_params | Received parameters: indiator_type={}".format(
                        self.indicator_type
                    )
                )
                self.latest_time = self.process_latest_time(
                    self.metadata.searchinfo.latest_time
                )

                self.validate(self.indicator_type)

                self.initialize()
                if not len(self.needle):
                    self.logger.info(
                        "message=no_indicators_found | No indicators were found, correlation won't be performed."
                    )
                else:
                    self.logger.info(
                        "message=start_correlation | Performing correlation ..."
                    )

            else:
                self.logger.debug(
                    "message=intermediate_call_counter | Intermediate call from Splunk"
                )

            if not len(self.needle):
                return

            self.correlate(events)

        except StopExecutionError:
            pass

        except kvstore.KVStoreUnavailbleError as ex:
            # STRUCTURED LOGGING: KVStore error - enables alerting on infrastructure issues
            # Before: self.logger.error("message=kvstore_unavailable_error | KVStore Unavailable...")
            log_event(self.logger, {
                'action': 'correlation_failed',
                'command': self.name,
                'error_type': 'KVStoreUnavailable',
                'error_msg': str(ex),
                'indicator_type': self.indicator_type
            }, log_level=logging.ERROR)
            self.logger.error(
                "message=kvstore_unavailable_error | KVStore Unavailable: {}".format(ex)
            )
            self._write_error("KVStore Unavailable: {}".format(ex))

        except Exception as ex:
            # STRUCTURED LOGGING: Unknown correlation error
            log_event(self.logger, {
                'action': 'correlation_failed',
                'command': self.name,
                'error_type': type(ex).__name__,
                'error_msg': str(ex),
                'indicator_type': self.indicator_type
            }, log_level=logging.ERROR)
            self.logger.error(
                "message=unknown_error | Unknown error occured: {}".format(
                    traceback.format_exc()
                )
            )
            self._write_error("Unknown Error: {}".format(ex))

        finally:
            # Note:
            # The "return" statement in finally block will override any important Exception raised in
            # try-except block so avoid using it in this block.

            if self._finished:
                try:
                    self.commit()
                except kvstore.KVStoreUnavailbleError:
                    # Error log is already logged in commit() method
                    # Don't log traceback if KVStore is unavailable.
                    pass

                except Exception as ex:
                    self.logger.error(
                        "message=unknown_error | Unknown error occured: {}".format(
                            traceback.format_exc()
                        )
                    )
                    self._write_error("Unknown Error: {}".format(ex))
                # STRUCTURED LOGGING: Correlation completion with metrics
                # Before: self.logger.info("message=stats_correlation | Correlation Stats...")
                elapsed_seconds = time.time() - self.start_time
                duration_ms = int(elapsed_seconds * 1000)

                log_event(self.logger, {
                    'action': 'correlation_completed',
                    'command': self.name,
                    'matching_indicators': len(self.final_indicators),
                    'total_indicators': len(self.needle),
                    'total_events': self.total_events,
                    'elapsed_seconds': f"{elapsed_seconds:.3f}",
                    'duration_ms': duration_ms,
                    'indicator_type': self.indicator_type
                }, log_level=logging.INFO)


dispatch(Analyst1MatchIndicatorsCommand, sys.argv, sys.stdin, sys.stdout, __name__)

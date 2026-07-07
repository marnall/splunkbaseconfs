import sys
import time
import traceback
import datetime
import six
import hashlib
import import_declare_test
import requests

from solnlib.splunkenv import get_splunkd_uri
import silent_push_helpers.kvstore as kvstore
from silent_push_helpers.logger_manager import setup_logging
from silent_push_helpers.conf_helper import get_conf_file
from silent_push_helpers.constants import VERIFY_INTERNAL_SSL
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option


REDIRECT_TO_LOG_FILE_MSG = "See {} for more details.".format(
    "ta_silent_push_correlation_command.log"
)


class StopExecutionError(Exception):
    """Usefull for stopping execution and break out from deep inside recursive loop."""

    pass


@Configuration()
class SilentPushMatchIndicatorsCommand(EventingCommand):
    """Silent Push match indicators custom command."""

    indicator_type = Option(name="indicator_type", require=True)

    is_first_invocation = True
    indicator_mgr = None
    start_time = None
    total_events = 0
    past_matched_indicators_dict = {}
    needle = set()
    final_indicators = []
    logger = None
    notable_event_count_dict = dict()

    def _write_error(self, msg):
        """Log error message to Splunk UI from where this custom command was triggered."""
        self.write_error("{} {}".format(msg, REDIRECT_TO_LOG_FILE_MSG))
        exit(0)

    def validate(self, indicator_type):
        """Validate the provided indicator_type field."""
        if indicator_type not in ("ip", "domain"):
            self.logger.error(
                "message=validate_fields_error | Given indicator_type is not valid: {}".format(
                    indicator_type
                )
            )
            self._write_error("Not valid indicator_type.")
        return True

    def get_multi_value_fileds(self, field_values, value):
        """Return field values from multi value fields."""
        for item in value:
            if (
                isinstance(item, six.string_types)
                and item.strip()
                and item != "-"
            ):
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
                    self.get_multi_value_fileds(field_values, value)
        return field_values

    def correlate(self, events):
        """Perform correlation on given Splunk events and ingest into matched lookup."""
        count = 0
        new_matched_indicators_count = dict()
        new_matched_indicators_index = dict()
        already_matched_indicators = set()
        for event in events:
            count += 1
            match_count = event.get("count", 1)
            haystack = self.get_field_value_set(event)
            matched_event_results = haystack.intersection(self.needle)
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
                    set([event.get("index")])
                    .union(new_matched_indicators_index.get(matched_event, set()))
                    .union(
                        self.past_matched_indicators_dict.get(matched_event, {}).get(
                            "correlationIndices", {}
                        )
                    )
                )
                already_matched_indicators.add(matched_event)

                self.notable_event_count_dict[matched_event] = match_count
        self.total_events += count

        ind = {}
        for indicator in new_matched_indicators_count.keys():
            ind = {
                "_key": hashlib.md5(indicator.strip().encode()).hexdigest(),
                self.matched_key_field: indicator,
                "correlationIndices": list(new_matched_indicators_index.get(indicator)),
                "lastMatchTime": self.latest_time,
                "count": new_matched_indicators_count.get(indicator),
            }
            self.final_indicators.append(ind)

    def check_es_app_exists(self):
        """Check if ES app exists."""
        try:
            headers = {
                "Authorization": "Splunk {}".format(self.session_key),
                "Content-Type": "application/json"
            }
            response = requests.get(
                get_splunkd_uri() + "/servicesNS/-/SplunkEnterpriseSecuritySuite/",
                headers=headers,
                verify=VERIFY_INTERNAL_SSL
            )
            if response.status_code != 200:
                self.logger.debug(
                    "message=response_returned | {} : {}".format(
                        response.status_code,
                        response.text
                    )
                )
                return False
            return True
        except Exception:
            self.logger.error(
                "message=failed_to_check_es_app | Failed to check ES app exists : {}".format(
                    traceback.format_exc()
                )
            )
            raise

    def generate_notable(self):
        """Generate notable events in ES."""
        try:
            if not len(self.final_indicators):
                self.logger.info(
                    "message=no_correlated_data_found | No matched indicators found."
                )
                return

            headers = {
                "Authorization": "Splunk {}".format(self.session_key),
                "Content-Type": "application/x-www-form-urlencoded"
            }

            body = {
                'output_mode': 'json',
                'earliest_time': self.metadata.searchinfo.earliest_time,
                'latest_time': self.metadata.searchinfo.latest_time
            }
            notable_event_count = 0
            for indicator in self.final_indicators:
                correlated_indices = ",".join(indicator.get("correlationIndices"))
                for _ in range(int(self.notable_event_count_dict.get(indicator.get(self.matched_key_field)))):
                    body["search"] = '| makeresults count=1 | eval rule_title="Silent Push Indicator: {}", security_domain="Threat", rule_description="Indicator found in {} index", severity="unknown" | sendalert notable param.mapfields=rule_id,rule_name,nes_fields,drilldown_name,drilldown_search,governance,control,default_owner,drilldown_earliest_offset,drilldown_latest_offset,next_steps,investigation_profiles,extract_artifacts,recommended_actions'.format(  # noqa: E501
                        indicator.get(self.matched_key_field),
                        correlated_indices
                    )

                    response = requests.post(
                        get_splunkd_uri() + "/services/search/v2/jobs/export/",
                        headers=headers,
                        data=body,
                        verify=VERIFY_INTERNAL_SSL
                    )
                    if response.status_code != 200:
                        raise Exception(response.text)
                    response = response.json()
                    notable_event_count += 1

            self.logger.info(
                "message=generate_notable_event_success | Successfully generated {} notable events.".format(
                    notable_event_count
                )
            )

        except Exception:
            self.logger.error(
                "message=failed_to_generate_notable | Failed to generate notable of matched indicators : {}".format(
                    traceback.format_exc()
                )
            )
            raise

    def commit(self):
        """Commit final changes back to Splunk."""
        try:
            if not len(self.final_indicators):
                return
            self.logger.info(
                "message=committing_mataching_indicators | Committing the matching indicators ..."
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
            file="silentpushappforsplunk_settings",
            stanza="splunk_rest_host",
            session_key=self.session_key,
        )
        collection_type = kv_conf_stanza.get("collection_type")
        self.matched_key_field = self.indicator_type
        self.master_lookup_field = "name"

        if collection_type == "lookup":
            self.indicator_mgr = kvstore.IndicatorManager(
                self.indicator_type, session_key=self.session_key
            )
        else:
            self.indicator_mgr = kvstore.IndicatorManager(
                self.indicator_type, service=self.service
            )
        self.logger.info("message=fetching_indicators | Fetching indicators ...")
        indicators = self.indicator_mgr.get_master_indicators_data(
            types=self.indicator_type, fields=[self.master_lookup_field]
        )

        past_matched_indicators = self.indicator_mgr.get_matched_indicators_data(
            types=self.indicator_type, fields=[self.matched_key_field, "count", "correlationIndices"]
        )
        for indicator in past_matched_indicators:
            self.past_matched_indicators_dict.update(
                {
                    indicator.get(self.matched_key_field): {
                        "count": int(indicator.get("count")),
                        "correlationIndices": set(indicator.get("correlationIndices", [])),
                    }
                }
            )
        for indicator in indicators:
            self.needle.add(indicator.get(self.master_lookup_field))
        self.logger.info(
            "message=fetched_indicators | Fetched indicators: count={} type={}".format(
                len(self.needle), self.indicator_type
            )
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

    def generate_es_notable(self):
        """Generate ES notable."""
        try:
            if self.check_es_app_exists():
                self.logger.info(
                    "message=generate_notable_event "
                    "| started generating notable events of correlated data."
                )
                self.generate_notable()
            else:
                self.logger.info(
                    "message=no_es_app_exists "
                    "| ES app does not exist. Skipping generation of notable events for the correlated data."
                )
        except Exception as ex:
            self.logger.error(
                "message=unknown_error | Unknown error occured: {}".format(
                    traceback.format_exc()
                )
            )
            self._write_error("Unknown Error: {}".format(ex))
            raise

    def transform(self, events):
        """Transform method of Eventing Command."""
        try:
            self.session_key = self.search_results_info.auth_token
            self.logger = setup_logging("ta_silent_push_correlation_command")
            # splunklib expects this method to be of type generator else throws error
            if False:
                yield
            self.check_metadata_preview()
            if self.is_first_invocation:
                self.is_first_invocation = False
                self.start_time = time.time()
                self.logger.info(
                    'message=command_start_execution | Starting the "{}" command execution:'
                    " earliest={} latest={} sid={}".format(
                        self.name,
                        datetime.datetime.fromtimestamp(
                            self.metadata.searchinfo.earliest_time
                        ).isoformat(),
                        datetime.datetime.fromtimestamp(
                            self.metadata.searchinfo.latest_time
                        ).isoformat(),
                        self.metadata.searchinfo.sid,
                    )
                )
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
            self.logger.error(
                "message=kvstore_unavailable_error | KVStore Unavailable: {}".format(ex)
            )
            self._write_error("KVStore Unavailable: {}".format(ex))

        except Exception as ex:
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
                self.logger.info(
                    "message=stats_correlation "
                    "| Correlation Stats: matching_indicators={} indicators={} events={}".format(
                        len(self.final_indicators), len(self.needle), self.total_events
                    )
                )

                self.generate_es_notable()

                elapsed_seconds = time.time() - self.start_time
                self.logger.info(
                    'message=command_end_execution | End of the "{}" command execution.'
                    " Total time taken: elapsed_seconds={:.3f}".format(
                        self.name, elapsed_seconds
                    )
                )


dispatch(SilentPushMatchIndicatorsCommand, sys.argv, sys.stdin, sys.stdout, __name__)

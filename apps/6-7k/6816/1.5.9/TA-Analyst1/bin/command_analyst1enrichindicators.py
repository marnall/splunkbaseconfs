import sys
import time
import traceback
import datetime
import six
import hashlib

import ta_analyst1_declare  # noqa: F401
from solnlib.utils import is_true
import analyst1_helpers.kvstore as kvstore
from analyst1_logging import get_logger
from analyst1_helpers.constants import MASTER_LOOKUP_DICT
from analyst1_helpers.conf_helper import get_conf_file
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option

from utils import compute_a1_key

REDIRECT_TO_LOG_FILE_MSG = "See {} for more details.".format(
    "ta_analyst1_enrichment_command.log"
)


class StopExecutionError(Exception):
    """Usefull for stopping execution and break out from deep inside recursive loop."""

    pass


@Configuration()
class Analyst1EnrichIndicatorsCommand(EventingCommand):
    """Analyst1 match indicators custom command."""

    indicator_type = Option(name="indicator_type", require=True)

    fields = Option(name="fields", require=False)

    is_first_invocation = True
    indicator_mgr = None
    start_time = None
    total_events = 0
    total_match_events = 0
    ready_results = []
    match_indicator_keys = set()
    needle = set()
    logger = None
    session_key = None

    def _write_error(self, msg):
        """Log error message to Splunk UI from where this custom command was triggered."""
        self.write_error("{} {}".format(msg, REDIRECT_TO_LOG_FILE_MSG))
        exit(0)

    def validate(self, indicator_type, fields):
        if indicator_type not in MASTER_LOOKUP_DICT.keys():
            self.logger.error(
                "message=invalid_indicator_type | Given indicator_type is not valid: {}".format(
                    indicator_type
                )
            )
            self._write_error("Not valid indicator_type.")
        if not fields:
            conf = get_conf_file(
                file="macros",
                session_key=self.session_key,
                stanza="analyst1_{}s_target_indicator_fields".format(indicator_type),
            )
            macro_definition = conf.get("definition", {})
            self.logger.info(
                "message=fetching_macro_definiton | Fetched macro with fields:{}".format(
                    macro_definition
                )
            )
            if macro_definition in ("", None):
                msg = (
                    'Either provide "fields" parameter or fill the value of "{}: Target Fields" '
                    "in Correlation Settings.".format(indicator_type.title())
                )
                self.logger.error("message=invalid_fields | {}".format(msg))
                self._write_error(msg)
            fields = macro_definition
        self.fields = [x.strip() for x in fields.split(",")]
        return True

    def get_field_value_set(self, event):
        field_values = set()

        for key, value in event.items():
            if key not in self.fields:
                continue

            if isinstance(value, six.string_types):
                if value.strip() and value != "-":
                    field_values.add(compute_a1_key(value.strip()))
            elif isinstance(value, (list, tuple, set)):
                field_values.update(
                    compute_a1_key(item.strip())
                    for item in value
                    if isinstance(item, six.string_types) and item.strip() and item != "-"
                )
        return field_values

    def enrich(self, events):
        """Perform enrichment on given Splunk events and yield."""
        match_indicator_keys = set()
        match_results = []
        total_count = 0
        match_count = 0
        for event in events:
            total_count += 1
            haystack = self.get_field_value_set(event)
            matched_event_results = haystack.intersection(self.needle)
            if matched_event_results:
                match_count += 1
                event["analyst1_matched_key"] = list(matched_event_results)
                match_indicator_keys = match_indicator_keys.union(matched_event_results)
                match_results.append(event)

            else:
                self.ready_results.append(event)

        self.total_events += total_count
        self.total_match_events += match_count
        indicator_metadata = self.indicator_mgr.get_master_indicators_data_from_keys(
            match_indicator_keys
        )
        indicator_metadata_dict = dict()
        for indicator in indicator_metadata:
            indicator_metadata_dict.update({indicator.get("_key"): indicator})
        for match_result in match_results:
            matched_keys = match_result.get("analyst1_matched_key")
            update_raw = {}
            for matched_key in matched_keys:
                temp = indicator_metadata_dict.get(matched_key)
                for k, v in temp.items():
                    if type(v) != list:
                        update_raw[k] = {v}.union(set(update_raw.get(k, {})))
                    else:
                        update_raw[k] = set(v).union(set(update_raw.get(k, {})))

            for k, v in update_raw.items():
                if k != "_key":
                    match_result.update({"analyst1_{}".format(k): list(v)})

            self.ready_results.append(match_result)

    def initialize(self):
        """Initialize the enrichment environment and load data into memory."""
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
        indicators = self.indicator_mgr.get_master_indicators_data(
            types=self.indicator_type, fields=["_key"]
        )
        self.logger.info(
            "message=fetched_indicator | Fetched indicators: count={} type={}".format(
                len(indicators), self.indicator_type
            )
        )
        for indicator in indicators:
            self.needle.add(indicator.get("_key"))

    def transform(self, events):
        """Transform method of Eventing Command."""
        try:
            self.session_key = self.search_results_info.auth_token
            self.logger = get_logger("ta_analyst1_enrichindicators")
            # splunklib expects this method to be of type generator else throws error
            if False:
                yield

            if self.metadata.preview:
                return

            if self.is_first_invocation:
                self.is_first_invocation = False
                self.start_time = time.time()
                self.logger.info(
                    'message=start_execution | Starting the "{}" command execution:'
                    " earliest={} latest={} sid={}".format(
                        self.name,
                        datetime.datetime.utcfromtimestamp(
                            self.metadata.searchinfo.earliest_time
                        ).isoformat(),
                        datetime.datetime.utcfromtimestamp(
                            self.metadata.searchinfo.latest_time
                        ).isoformat(),
                        self.metadata.searchinfo.sid,
                    )
                )
                self.logger.info(
                    "message=received_params | Received parameters: indiator_type={} & fields={}".format(
                        self.indicator_type, self.fields
                    )
                )

                self.validate(self.indicator_type, self.fields)

                self.initialize()
                if not len(self.needle):
                    self.logger.info(
                        "message=no_indicators_found | No indicators were found, enrichment won't be performed."
                    )
                else:
                    self.logger.info(
                        "message=start_enrichment | Performing enrichment ..."
                    )

            else:
                self.logger.debug(
                    "message=intermediate_call_counter | Intermediate call from Splunk"
                )

            if not len(self.needle):
                for event in events:
                    yield event

            else:
                self.enrich(events)
                while self.ready_results:
                    yield self.ready_results.pop()

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
                self.logger.info(
                    "message=stats_enrichment "
                    "| Enrichment Stats: matching_indicators={} indicators={} events={}".format(
                        self.total_match_events, len(self.needle), self.total_events
                    )
                )
                elapsed_seconds = time.time() - self.start_time
                self.logger.info(
                    'message=end_execution | End of the "{}" command execution.'
                    " Total time taken: elapsed_seconds={:.3f}".format(
                        self.name, elapsed_seconds
                    )
                )


dispatch(Analyst1EnrichIndicatorsCommand, sys.argv, sys.stdin, sys.stdout, __name__)

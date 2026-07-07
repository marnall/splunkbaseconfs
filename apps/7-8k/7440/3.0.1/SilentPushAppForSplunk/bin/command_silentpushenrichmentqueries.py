import import_declare_test
import sys
import time
import traceback
import six
import json
from copy import deepcopy
from silent_push_helpers.logger_manager import setup_logging
from silent_push_helpers.rest_helper import RestHelper
from silent_push_helpers.conf_helper import get_credentials
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option
from solnlib.utils import is_true

logger = setup_logging("ta_silent_push_enrichment_queries_custom_command")

REDIRECT_TO_LOG_FILE_MSG = "See {} for more details.".format(
    "ta_silent_push_enrichment_queries_custom_command.log"
)


@Configuration()
class SilentPushEnrichmentQueriesCommand(EventingCommand):
    """SilentPushEnrichmentQueriesCommand Class."""

    account_name = Option(name="account_name", require=True)
    indicator = Option(name="indicator", require=True)
    explain = Option(name="explain", require=False)
    scan_data = Option(name="scan_data", require=False)
    field_flag = Option(name="field_flag", require=False, default=False)

    indicators = set()
    events = []
    domain_enrichment_events = 0
    ipv4_enrichment_events = 0
    ipv6_enrichment_events = 0

    def _write_error(self, msg):
        """Log error message to Splunk UI from where this custom command was triggered."""
        self.write_error("{} {}".format(msg, REDIRECT_TO_LOG_FILE_MSG))
        exit(0)

    def get_multi_value_fileds(self, value):
        """Return field values from multi value fields."""
        for item in value:
            if (
                isinstance(item, six.string_types)
                and item.strip()
                and item != "-"
            ):
                self.indicators.add(item.strip())

    def get_indicators_from_events(self, events):
        """Get indicators from events."""
        for event in events:
            self.events.append(event)
            value = event.get(self.indicator)
            if (
                isinstance(value, six.string_types)
                and value.strip()
                and value != "-"
            ):
                self.indicators.add(value.strip())
            elif isinstance(value, (list, tuple, set)):
                self.get_multi_value_fileds(value)

    def append_event_data(self, splunk_event, indicator_data):
        """Append indicator data to the given Splunk event."""
        splunk_event_copy = deepcopy(splunk_event)
        ioc_event = deepcopy(indicator_data)
        splunk_event_copy.update({"sp_{}".format(k): v for k, v in ioc_event.items()})

        return splunk_event_copy

    def transform(self, events):
        """Transform method."""
        try:
            logger.info("message=command_start_execution | Started Custom Command Script Execution.")
            start_time = time.time()
            session_key = self._metadata.searchinfo.session_key
            silent_push_config = {
                "session_key": session_key,
            }
            account_info = get_credentials(self.account_name, session_key)
            silent_push_config.update(account_info)

            if is_true(self.field_flag):
                self.get_indicators_from_events(events)

            else:
                rest_helper_obj = RestHelper(silent_push_config, logger)
                params = dict()

                params['explain'] = self.explain
                params['scan_data'] = self.scan_data

                data = rest_helper_obj.get_enrichment_queries(self.indicator, params)
                logger.info("message=command_info | Silent Push Info : Json Data Retrived.")
                yield {
                    "_raw": {"sp": data["response"]},
                    "_time": time.time()
                }

        except Exception as ex:
            logger.error(
                "message=unknown_error | Unknown error occured: {}".format(
                    traceback.format_exc()
                )
            )
            self._write_error("Unknown Error: {}".format(ex))
        finally:
            if self._finished:
                if is_true(self.field_flag):
                    logger.info(
                        f'message=command_info | Total indicators received from given '
                        f'search query are: {len(self.indicators)}'
                    )
                    silent_push_config.update({
                        "explain": self.explain,
                        "scan_data": self.scan_data,
                        "indicators": self.indicators,
                    })
                    rest_helper_obj = RestHelper(silent_push_config, logger)
                    rest_helper_obj.initialise_indicators()
                    # Get enrichment domain data
                    domain_datas = rest_helper_obj.get_enrichment_domain_data()

                    indicator_domain_map = {data.get("host_flags")[0].get("domain"): data for data in domain_datas}
                    temp_events = deepcopy(self.events)
                    for event in temp_events:
                        silentpush_ioc_data = indicator_domain_map.get(event.get(self.indicator, "").lower())
                        if silentpush_ioc_data:
                            yield self.append_event_data(event, silentpush_ioc_data)
                            self.events.remove(event)
                            self.domain_enrichment_events += 1

                    logger.info(
                        "message=events_collected | Total events for Domain enrichment"
                        " yielded in Splunk are {}".format(self.domain_enrichment_events)
                    )

                    # Get enrichment IPv4 data
                    ipv4_datas = rest_helper_obj.get_enrichment_ipv4_data()
                    indicator_ipv4_map = {data.get("ip"): data for data in ipv4_datas}
                    temp_events = deepcopy(self.events)
                    for event in temp_events:
                        silentpush_ioc_data = indicator_ipv4_map.get(event.get(self.indicator, ""))
                        if silentpush_ioc_data:
                            yield self.append_event_data(event, silentpush_ioc_data)
                            self.events.remove(event)
                            self.ipv4_enrichment_events += 1

                    logger.info(
                        "message=events_collected | Total events for IPv4 enrichment"
                        " yielded in Splunk are {}".format(self.ipv4_enrichment_events))

                    # Get enrichment IPv6 data
                    ipv6_datas = rest_helper_obj.get_enrichment_ipv6_data()
                    indicator_ipv6_map = {data.get("ip"): data for data in ipv6_datas}
                    temp_events = deepcopy(self.events)
                    for event in temp_events:
                        silentpush_ioc_data = indicator_ipv6_map.get(event.get(self.indicator, ""))
                        if silentpush_ioc_data:
                            yield self.append_event_data(event, silentpush_ioc_data)
                            self.events.remove(event)
                            self.ipv6_enrichment_events += 1

                    logger.info(
                        "message=events_collected | Total events for IPv6 enrichment"
                        " yielded in Splunk are {}".format(self.ipv6_enrichment_events)
                    )

                    # yield remaining events
                    for event in self.events:
                        yield event
                    logger.info(
                        "message=events_collected | Total events without enrichment"
                        " yielded in Splunk are {}".format(len(self.events))
                    )
                    logger.info(
                        "message=events_collected | Total events yielded in Splunk with enrichment"
                        " are {}".format(
                            self.domain_enrichment_events + self.ipv4_enrichment_events + self.ipv6_enrichment_events
                        )
                    )
                logger.info(
                    'message=command_end_execution | End of the "{}" command execution.'
                    " Total time taken: elapsed_seconds={:.3f}".format(
                        self.name, time.time() - start_time
                    )
                )


dispatch(SilentPushEnrichmentQueriesCommand, sys.argv, sys.stdin, sys.stdout, __name__)

import ta_intsights_declare  # noqa: F401
import os
import sys
import time
import six
import traceback
import itertools
from datetime import datetime
from log_manager import setup_logging, generate_log_file_name
from api_client import APIClient
from command_utils import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRY,
    MatchedIOCsLock,
    IOCsManager,
    is_iterator_empty,
    update_last_scan_time,
    process_latest_time,
    MATCHED_LOOKUP,
    LOOKUP_METADATA,
)
from errors import (
    StopExecutionError,
    CustomException,
)
from splunklib.searchcommands import (
    Configuration,
    EventingCommand,
    Option,
    dispatch,
    validators,
)
from intsights_utils import is_macro_definition_true, get_action_fields_list

TAG = "Splunk Match"
COMMENT = "The IOC matched an indicator in your environment at {timestamp}"
DEFAULT_BATCH_SIZE = 500
MACRO_NAME = "intsights_enable_tags_comments_api_calls"
ACTION_FIELDS_MACROS = {
    "IpAddresses": "intsights_ips_target_indicator_action_fields",
    "Domains": "intsights_domains_target_indicator_action_fields",
    "Emails": "intsights_emails_target_indicator_action_fields",
    "Hashes": "intsights_hashes_target_indicator_action_fields",
    "Urls": "intsights_urls_target_indicator_action_fields"
}

logger_name = os.path.splitext(os.path.basename(__file__))[0]
logger = setup_logging(logger_name)


@Configuration()
class IntSightsMatchIOCsCommand(EventingCommand):
    """
    IntSights match IOCs custom command.

    :param: is_matched: To correlate only already matched IOCs?
    :param: batch_size: Minimum number of iocs to update in lookup as soon as found.
    """

    ioc_type = Option(name="ioc_type", require=True)
    batch_size = Option(name="batch_size", default=DEFAULT_BATCH_SIZE, validate=validators.Integer(minimum=1))
    backoff_factor = Option(
        name="backoff_factor", default=DEFAULT_BACKOFF_FACTOR, validate=validators.Integer(minimum=0)
    )
    max_retry = Option(name="max_retry", default=DEFAULT_MAX_RETRY, validate=validators.Integer(minimum=0))

    _matched_iocs_lock = None
    _iocs_manager = None
    _api_client = None

    starttime = time.time()
    events = iter([])
    check_empty = True

    action_fields = []
    matched_iocs = None
    iocs_to_update = []
    already_matched_once_count = 0
    newly_matched_count = 0
    first_match = set()

    @property
    def matched_iocs_lock(self):
        """Set matched_iocs_lock as property."""
        if self._matched_iocs_lock is None:
            self._matched_iocs_lock = MatchedIOCsLock(self.service, logger)
        return self._matched_iocs_lock

    @property
    def iocs_manager(self):
        """Set iocs_manager as property."""
        if self._iocs_manager is None:
            self._iocs_manager = IOCsManager(self.service, logger, self.backoff_factor, self.max_retry)
        return self._iocs_manager

    @property
    def api_client(self):
        """Set api_client as property."""
        if self._api_client is None:
            self._api_client = APIClient(self.session_key, logger)
        return self._api_client

    @classmethod
    def get_field_value_set(cls, event):
        """Return field values."""
        field_values = set()
        for key, value in event.items():
            if key != "index" and key != "count" and key not in cls.action_fields:
                if isinstance(value, six.string_types) and value.strip() and value != "-":
                    field_values.add(value.strip())
                elif isinstance(value, (list, tuple, set)):
                    for item in value:
                        if isinstance(item, six.string_types) and item.strip() and item != "-":
                            field_values.add(item.strip())
        return field_values

    def update_iocs(self, new_matched_iocs, new_matched_iocs_index, new_matched_iocs_action):
        """Update matched IOCs."""
        current_time = time.time()
        batch_already_matched_once_count = 0
        batch_newly_matched_count = 0
        for ioc in self.matched_iocs:
            if not new_matched_iocs.get(ioc["value"]):
                continue
            ioc["matchCount"] = int(ioc["matchCount"]) + new_matched_iocs[ioc["value"]]
            ioc["lastSeen"] = self.latest_time
            ioc["lastMatchTime"] = current_time
            if ioc.get("correlationIndices"):
                if isinstance(ioc.get("correlationIndices"), list):
                    ioc["correlationIndices"] = list(
                        set(ioc.get("correlationIndices")).union(new_matched_iocs_index[ioc["value"]])
                    )
                else:
                    ioc["correlationIndices"] = list(
                        set([ioc.get("correlationIndices")]).union(new_matched_iocs_index[ioc["value"]])
                    )
            else:
                ioc["correlationIndices"] = list(new_matched_iocs_index[ioc["value"]])

            if ioc.get("actions") and new_matched_iocs_action.get(ioc["value"]):
                if isinstance(ioc.get("actions"), list):
                    ioc["actions"] = list(
                        set(ioc.get("actions")).union(new_matched_iocs_action[ioc["value"]])
                    )
                else:
                    ioc["actions"] = list(
                        set([ioc.get("actions")]).union(new_matched_iocs_action[ioc["value"]])
                    )
            elif new_matched_iocs_action.get(ioc["value"]):
                ioc["actions"] = list(new_matched_iocs_action[ioc["value"]])
            self.iocs_to_update.append(ioc)
            self.already_matched_once_count += 1
            batch_already_matched_once_count += 1
            new_matched_iocs.pop(ioc["value"])
        logger.info("Count of matched IOCs in batch which are already matched once = {}"
                    .format(batch_already_matched_once_count))

        # Process new_matched_iocs which were matched for first time
        for ioc_value in new_matched_iocs.keys():
            ioc = {
                "value": ioc_value,
                "lastSeen": self.latest_time,
                "firstSeen": self.earliest_time,
                "matchCount": new_matched_iocs[ioc_value],
                "lastMatchTime": current_time,
                "correlationIndices": list(new_matched_iocs_index[ioc_value])
            }
            if new_matched_iocs_action.get(ioc_value):
                ioc.update({"actions": list(new_matched_iocs_action[ioc_value])})
            self.iocs_to_update.append(ioc)
            self.newly_matched_count += 1
            batch_newly_matched_count += 1
            self.first_match.add(ioc_value)
        logger.info("Count of matched IOCs in batch which are matched for the first time = {}"
                    .format(batch_newly_matched_count))

    def post_metadata_to_intsights(self, new_matched_ioc_values):
        """Post metadata of new matched iocs to intsights platform."""
        logger.info("Posting metadata to IntSights Platform.")
        comment_text = COMMENT.format(timestamp=datetime.utcnow().strftime(r"%Y-%m-%dT%H:%M:%SZ"))
        tags = []
        comments = []
        for ioc_value in new_matched_ioc_values:
            tags.append({"iocValue": ioc_value, "tag": TAG})
            comments.append({"iocValue": ioc_value, "comment": comment_text})

        try:
            self.api_client.post_tags(tags)
            logger.info("Posted Tags of {} IOCs.".format(len(tags)))
        except Exception as ex:
            err_msg = "Error while posting Tags: {}".format(ex.reason if isinstance(ex, CustomException) else str(ex))
            logger.error(err_msg)
            self.write_warning(err_msg)

        try:
            self.api_client.post_comments(comments)
            logger.info("Posted Comments of {} IOCs.".format(len(comments)))
        except Exception as ex:
            err_msg = "Error while posting Comments: {}".format(
                ex.reason if isinstance(ex, CustomException) else str(ex)
            )
            logger.error(err_msg)
            self.write_warning(err_msg)

    def correlate(self, iocs, events):
        """Correlate iocs with provided splunk events' fields."""
        # Get set of IOC values
        ioc_values = set()
        for ioc in iocs:
            if isinstance(ioc.get("value"), six.string_types):
                ioc_values.add(ioc["value"])

        # Correlate IOC values with splunk event fields' value
        self.events_count = 0
        self.indicators_count = 0
        new_matched_ioc_values = set()
        new_matched_iocs = dict()
        new_matched_iocs_index = dict()
        new_matched_iocs_action = dict()
        for event in events:
            field_values = self.get_field_value_set(event)
            match_Count = event.get("count")

            # Take intersection of sets for correlation
            matched_ioc_values = field_values & ioc_values

            for matched_ioc_value in matched_ioc_values:
                new_matched_ioc_values.add(matched_ioc_value)
                new_matched_iocs[matched_ioc_value] = new_matched_iocs.get(matched_ioc_value, 0) + int(match_Count)
                new_matched_iocs_index[matched_ioc_value] = set([event.get("index")]).union(
                    new_matched_iocs_index.get(matched_ioc_value, set())
                )

                for each in self.action_fields:
                    action_values = event.get(each)
                    if isinstance(action_values, six.string_types):
                        if action_values.strip() == "-":
                            new_matched_iocs_action[matched_ioc_value] = set().union(
                                new_matched_iocs_action.get(matched_ioc_value, set())
                            )
                        else:
                            new_matched_iocs_action[matched_ioc_value] = set([action_values]).union(
                                new_matched_iocs_action.get(matched_ioc_value, set())
                            )
                    else:
                        new_matched_iocs_action[matched_ioc_value] = set(action_values).union(
                            new_matched_iocs_action.get(matched_ioc_value, set())
                        )

                self.indicators_count += 1

            if len(new_matched_iocs) >= self.batch_size:
                self.update_iocs(new_matched_iocs, new_matched_iocs_index, new_matched_iocs_action)
                new_matched_iocs = dict()
                new_matched_iocs_index = dict()
                new_matched_iocs_action = dict()

            self.events_count += 1

        if len(new_matched_iocs) > 0:
            self.update_iocs(new_matched_iocs, new_matched_iocs_index, new_matched_iocs_action)

        try:
            for sub_list in range(0, len(self.iocs_to_update), self.batch_size):
                logger.info("Updating the batch of {} matched IOCs.".format(self.batch_size))
                self.iocs_manager.update_matched_iocs(self.iocs_to_update[sub_list:sub_list + self.batch_size])
            logger.info("Updated {} matched IOCs which are already matched once."
                        .format(self.already_matched_once_count))
            logger.info("Updated {} matched IOCs which are matched for the first time."
                        .format(self.newly_matched_count))
            macro_value = is_macro_definition_true(self.session_key, MACRO_NAME)
            if macro_value:
                logger.info(
                    "The macro {} is set to True. Outgoing api calls to tags and comments api are enabled.".format(
                        MACRO_NAME
                    )
                )
            else:
                logger.info(
                    "The macro {} is not set to True. Outgoing api calls to tags and comments api are disabled.".format(
                        MACRO_NAME
                    )
                )
        except Exception as e:
            err_msg = "Error while fetching the {} macro definition : {}".format(MACRO_NAME, str(e))
            logger.error(err_msg)
            self.write_error(err_msg)
            exit(0)

        # Post only for first time matched iocs
        if len(self.first_match) > 0 and macro_value:
            self.post_metadata_to_intsights(self.first_match)

    def transform(self, events):
        """Transform method of Eventing Command."""
        # To avoid error, make it generator (required for eventing command)
        if False:
            yield

        if (not self.search_results_info) or (self.metadata.preview):
            return

        events = is_iterator_empty(events)
        if self.check_empty:
            if events is None:
                return
            else:
                self.check_empty = False

        self.events = itertools.chain(self.events, events)
        if self._finished:
            self.proceed_correlate()

    def proceed_correlate(self):
        """Transform method of Eventing Command."""
        # To avoid error, make it generator (required for eventing command)

        self.latest_time = process_latest_time(self.metadata.searchinfo.latest_time)
        update_last_scan_time(self.service, self.latest_time, LOOKUP_METADATA, MATCHED_LOOKUP)

        logger.info('Starting the "{}" command execution.'.format(self.name))
        logger.info("SID: {}".format(self.metadata.searchinfo.sid))
        self.events_count = 0
        self.indicators_count = 0

        try:
            self.session_key = self.search_results_info.auth_token
            self.earliest_time = float(self.metadata.searchinfo.earliest_time)
            if not hasattr(self, "latest_time"):
                self.latest_time = process_latest_time(self.metadata.searchinfo.latest_time)

            logger.info(
                'Received the Splunk events in time range from "{} ({})" to "{} ({})".'.format(
                    self.earliest_time,
                    datetime.fromtimestamp(self.earliest_time),
                    self.latest_time,
                    datetime.fromtimestamp(self.latest_time),
                )
            )
            iocs = []
            logger.info('Fetching the "matched" IOCs.')
            self.matched_iocs = self.iocs_manager.get_matched_iocs()
            logger.info('Fetching the "master" IOCs of type "{}".'.format(self.ioc_type))
            iocs = self.iocs_manager.get_all_iocs_by_type(types=[self.ioc_type], fields=["value"])
            logger.info("Received {} IOCs.".format(len(iocs)))

            if not len(iocs):
                logger.info("No IOCs found for correlation.")
                raise StopExecutionError()

            action_fields_macro = ACTION_FIELDS_MACROS.get(self.ioc_type)
            self.action_fields.extend(get_action_fields_list(self.session_key,
                                                             action_fields_macro))

            self.correlate(iocs, self.events)

        except StopExecutionError:
            pass

        except CustomException as ex:
            logger.error(ex.reason)

            # Display an error message on Splunk UI, below the search panel.
            self.write_error(ex.message)

        except Exception:
            logger.error('Error occured while executing "{}" command -- {}'.format(self.name, traceback.format_exc()))
            self.write_error(
                ('Internal error occured while executing "{}" custom command.' ' Please check "{}" file.').format(
                    self.name, generate_log_file_name(logger_name)
                )
            )

        logger.info(
            "Found total {} indicators out of {} processed events.".format(self.indicators_count, self.events_count)
        )
        logger.info("Time taken - {} seconds.".format(time.time() - self.starttime))
        logger.info('Completed the execution of "{}" command.'.format(self.name))


if __name__ == "__main__":
    dispatch(IntSightsMatchIOCsCommand, sys.argv, sys.stdin, sys.stdout, __name__)

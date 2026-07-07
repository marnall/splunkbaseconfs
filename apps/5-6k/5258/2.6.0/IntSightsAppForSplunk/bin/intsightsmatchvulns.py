import ta_intsights_declare  # noqa: F401
import os
import sys
import time
import six
import traceback
import itertools

from datetime import datetime
from log_manager import setup_logging, generate_log_file_name
from command_utils import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRY,
    MatchedVulnerabilitiesLock,
    VulnerabilitiesManager,
    is_iterator_empty,
    update_last_scan_time,
    process_latest_time,
    VULN_MATCHED_LOOKUP,
    VULN_LOOKUP_METADATA,
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

DEFAULT_BATCH_SIZE = 500

logger_name = os.path.splitext(os.path.basename(__file__))[0]
logger = setup_logging(logger_name)


@Configuration()
class IntSightsMatchVulnsCommand(EventingCommand):
    """
    IntSights match Vulnerabilities custom command.

    :param: is_matched: To correlate only already matched Vulnerabilities?
    :param: batch_size: Minimum number of vulnerabilities to update in lookup as soon as found.
    """

    is_matched = Option(name="is_matched", default=False, validate=validators.Boolean())
    batch_size = Option(name="batch_size", default=DEFAULT_BATCH_SIZE, validate=validators.Integer(minimum=1))
    backoff_factor = Option(
        name="backoff_factor", default=DEFAULT_BACKOFF_FACTOR, validate=validators.Integer(minimum=0)
    )
    max_retry = Option(name="max_retry", default=DEFAULT_MAX_RETRY, validate=validators.Integer(minimum=0))

    _matched_vulns_lock = None
    _vulns_manager = None

    check_empty = True
    events = iter([])

    @property
    def matched_vulns_lock(self):
        """Set matched_vulns_lock as property."""
        if self._matched_vulns_lock is None:
            self._matched_vulns_lock = MatchedVulnerabilitiesLock(self.service, logger)
        return self._matched_vulns_lock

    @property
    def vulns_manager(self):
        """Set vulns_manager as property."""
        if self._vulns_manager is None:
            self._vulns_manager = VulnerabilitiesManager(self.service, logger, self.backoff_factor, self.max_retry)
        return self._vulns_manager

    @classmethod
    def get_field_value_set(cls, event):
        """Return field values."""
        field_values = set()
        for key, value in event.items():
            if key != "index":
                if isinstance(value, six.string_types) and value.strip():
                    field_values.add(value.strip())
                elif isinstance(value, (list, tuple, set)):
                    for item in value:
                        if isinstance(item, six.string_types) and item.strip():
                            field_values.add(item.strip())
        return field_values

    def update_vulns(self, new_matched_vulns, new_matched_vulns_index):
        """Update matched Vulnerabilities."""
        logger.info("Updating the batch of {} matched Vulnerabilities.".format(len(new_matched_vulns)))
        try:
            self.matched_vulns_lock.acquire()
            current_time = time.time()
            matched_vulns = self.vulns_manager.get_matched_vulns()
            # Process new_matched_vulns which were already matched once
            vulns_to_update = []
            already_matched_once_count = 0
            newly_matched_count = 0
            for vuln in matched_vulns:
                if not new_matched_vulns.get(vuln["cveId"]):
                    continue
                vuln["matchCount"] = int(vuln["matchCount"]) + new_matched_vulns[vuln["cveId"]]
                vuln["lastSeen"] = self.latest_time
                vuln["lastMatchTime"] = current_time
                if vuln.get("correlationIndices"):
                    if isinstance(vuln.get("correlationIndices"), list):
                        vuln["correlationIndices"] = list(
                            set(vuln.get("correlationIndices")).union(new_matched_vulns_index[vuln["cveId"]])
                        )
                    else:
                        vuln["correlationIndices"] = list(
                            set([vuln.get("correlationIndices")]).union(new_matched_vulns_index[vuln["cveId"]])
                        )
                else:
                    vuln["correlationIndices"] = list(new_matched_vulns_index[vuln["cveId"]])
                already_matched_once_count += 1
                vulns_to_update.append(vuln)
                new_matched_vulns.pop(vuln["cveId"])

            # Process new_matched_vulns which were matched for first time
            for vuln_id in new_matched_vulns.keys():
                vuln = {
                    "cveId": vuln_id,
                    "lastSeen": self.latest_time,
                    "firstSeen": self.earliest_time,
                    "matchCount": new_matched_vulns[vuln_id],
                    "lastMatchTime": current_time,
                    "correlationIndices": list(new_matched_vulns_index[vuln_id]),
                }
                newly_matched_count += 1
                vulns_to_update.append(vuln)

            self.vulns_manager.update_matched_vulns(vulns_to_update)
        finally:
            logger.info("Updated {} matched vulnerabilities which are already matched once."
                        .format(already_matched_once_count))
            logger.info("Updated {} matched vulnerabilities which are matched for the first time."
                        .format(newly_matched_count))
            self.matched_vulns_lock.release()

    def correlate(self, vulns):
        """Correlate Vulnerabilities with provided splunk events' fields."""
        # Get set of Vulnerability values
        vuln_values = set()
        for vuln in vulns:
            if isinstance(vuln.get("cveId"), six.string_types):
                vuln_values.add(vuln["cveId"])

        # Correlate Vulnerability values with splunk event fields' value
        self.events_count = 0
        self.sightings_count = 0
        new_matched_vuln_ids = set()
        new_matched_vulns = dict()
        new_matched_vulns_index = dict()
        for event in self.events:
            field_values = self.get_field_value_set(event)

            # Take intersection of sets for correlation
            matched_vuln_ids = field_values & vuln_values

            for matched_vuln_id in matched_vuln_ids:
                new_matched_vuln_ids.add(matched_vuln_id)
                new_matched_vulns[matched_vuln_id] = new_matched_vulns.get(matched_vuln_id, 0) + 1
                new_matched_vulns_index[matched_vuln_id] = set([event.get("index")]).union(
                    new_matched_vulns_index.get(matched_vuln_id, set())
                )
                self.sightings_count += 1

            if len(new_matched_vulns) >= self.batch_size:
                self.update_vulns(new_matched_vulns, new_matched_vulns_index)
                new_matched_vulns = dict()
                new_matched_vulns_index = dict()

            self.events_count += 1

        if len(new_matched_vulns) > 0:
            self.update_vulns(new_matched_vulns, new_matched_vulns_index)

    def transform(self, events):
        """Transform method of Eventing Command."""
        # To avoid error, make it generator (required for eventing command)
        if False:
            yield

        if (not self.search_results_info) or (self.metadata.preview):
            return

        if self.check_empty:
            if self.is_matched:
                self.latest_time = process_latest_time(self.metadata.searchinfo.latest_time)
                update_last_scan_time(self.service, self.latest_time, VULN_LOOKUP_METADATA, VULN_MATCHED_LOOKUP)

            events = is_iterator_empty(events)
            if events is None:
                return
            else:
                self.check_empty = False

        self.events = itertools.chain(self.events, events)
        if self._finished:
            self.proceed_correlate()

    def proceed_correlate(self):
        """Proceeding for preparing prerequisites for correlation."""
        logger.info('Starting the "{}" command execution.'.format(self.name))
        logger.info("SID: {}".format(self.metadata.searchinfo.sid))
        starttime = time.time()
        self.events_count = 0
        self.sightings_count = 0

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
            logger.info('Fetching the "{}" Vulnerabilities.'.format("matched" if self.is_matched else "unmatched"))
            vulns = []
            if self.is_matched:
                vulns = self.vulns_manager.get_matched_vulns(fields=["cveId"])
            else:
                vulns = self.vulns_manager.get_unmatched_vulns(fields=["cveId"])
            logger.info("Received {} Vulnerabilities.".format(len(vulns)))

            if not len(vulns):
                logger.info("No Vulnerabilities found for correlation.")
                raise StopExecutionError()

            self.correlate(vulns)

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
            "Found total {} indicators out of {} processed events.".format(self.sightings_count, self.events_count)
        )
        logger.info("Time taken - {} seconds.".format(time.time() - starttime))
        logger.info('Completed the execution of "{}" command.'.format(self.name))


if __name__ == "__main__":
    dispatch(IntSightsMatchVulnsCommand, sys.argv, sys.stdin, sys.stdout, __name__)

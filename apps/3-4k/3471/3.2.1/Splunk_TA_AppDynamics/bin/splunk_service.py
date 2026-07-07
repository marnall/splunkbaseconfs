import json
import os
import pickle

from solnlib import log

logger = log.Logs().get_logger("splunk_service")


class SplunkService:
    """
    Writes modular input events to Splunk and maintains a pickle backlog file
    for events that fail to write (retried on next run or when flush_backlog=True).
    """

    def __init__(self, helper, index, sourcetype, event_writer):
        self.input_name = f"splunk_ta_appdynamics://{helper.get_arg('name')}"
        self.index = index
        self.sourcetype = sourcetype
        self.helper = helper
        self.event_writer = event_writer
        self.source_logger = helper.logger
        self.cnt_events_written_success = 0
        self.cnt_events_written_error = 0
        directory = os.path.join(os.path.dirname(__file__), "..", "backlog")
        os.makedirs(directory, exist_ok=True)
        self.backlog_file = os.path.join(directory, f"{sourcetype}_backlog.dat")
        logger.debug("Initialized splunk_service for input %s", self.input_name)
        log.modular_input_start(self.source_logger, self.input_name)

    def send_data(self, source, data, time=None, flush_backlog=True):
        """Enqueue one event for writing; optionally flush backlog. On failure, event is added to backlog."""
        if not data:
            if os.path.exists(self.backlog_file) and flush_backlog:
                self._flush_backlog()
            return
        event = None
        try:
            event = self.helper.new_event(
                source=source,
                index=self.index,
                sourcetype=self.sourcetype,
                data=json.dumps(data, sort_keys=True),
                time=time,
            )
            self.event_writer.write_event(event)
            self.cnt_events_written_success += 1
            event = None
            if os.path.exists(self.backlog_file) and flush_backlog:
                self._flush_backlog()
        except Exception as e:
            self.helper.log_error("Exception while writing event: {}".format(e))
            logger.error("Exception while writing event: %s", e)
            self.cnt_events_written_error += 1
            log.log_exception(self.source_logger, e, self.input_name)
            if event is not None:
                self._add_backlog([event])

    def _flush_backlog(self):
        """Read backlog file, write all events, then clear the file. Failed writes are re-backlogged."""
        if not os.path.exists(self.backlog_file):
            return
        events = []
        with open(self.backlog_file, "rb+") as f:
            while True:
                try:
                    events.append(pickle.load(f))
                except EOFError:
                    f.truncate(0)
                    break
        if not events:
            return
        self.helper.log_info("Read {} from backlog {}".format(len(events), self.backlog_file))
        logger.info("Read %d from backlog %s", len(events), self.backlog_file)

        failed_events = []
        for event in events:
            try:
                self.event_writer.write_event(event)
                self.cnt_events_written_success += 1
            except Exception as e:
                self.cnt_events_written_error += 1
                failed_events.append(event)

        if failed_events:
            self._add_backlog(failed_events)

    def _add_backlog(self, events):
        """Append events to the backlog file."""
        if not events:
            return
        with open(self.backlog_file, "ab") as f:
            for event in events:
                pickle.dump(event, f)
        self.helper.log_info("Wrote {} backlog to {}".format(len(events), self.backlog_file))
        logger.info("Wrote %d backlog to %s", len(events), self.backlog_file)

    def log_exception(self, exception):
        log.log_exception(self.source_logger, exception, self.input_name)

    def log_events_ingested(self):
        log.events_ingested(
            logger,
            self.input_name,
            self.sourcetype,
            self.cnt_events_written_success,
            self.index,
        )
        log.modular_input_end(self.source_logger, self.input_name)
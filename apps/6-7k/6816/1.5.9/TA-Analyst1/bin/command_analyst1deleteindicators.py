import ta_analyst1_declare  # noqa: F401
import sys
from itertools import tee
from splunklib.searchcommands import dispatch
from splunklib.searchcommands import (
    StreamingCommand,
    Configuration,
)
from analyst1_helpers.splunk_ingestor import KVStoreIngestor
from analyst1_logging import get_logger
from analyst1_helpers.event import Event


class StopExecutionError(Exception):
    """Usefull for stopping execution and break out from deep inside recursive loop."""

    pass


@Configuration()
class Analyst1DeleteIndicators(StreamingCommand):
    """Mandiant retire indicators custom command."""

    _ingestor = None

    def _write_error(self, msg):
        """Log error message to Splunk UI from where this custom command was triggered."""
        self.write_error(f"{msg}. See ta_analyst1_deleteindicators.log for more details.")

    def stream(self, events):
        try:
            self.session_key = self.search_results_info.auth_token
            logger = get_logger("ta_analyst1_deleteindicators")
            logger.info(f"LOGGER {self.logger.getEffectiveLevel()}")
            logger.info("Starting to delete indicators from kvstore lookups.")
            stream_events, ingest_events = tee(events)
            self.ingestor.ingest(self.filter_events(ingest_events))

            logger.info("Ending the Custom Command Execution")

            for each_event in stream_events:
                if each_event.get("removed"):
                    yield each_event

        except Exception as e:
            self._write_error(str(e))

    def filter_events(self, events):
        for each_event in events:
            if not each_event.get("removed", False):
                continue
            yield Event(each_event)

    @property
    def ingestor(self):
        if not self._ingestor:
            self._ingestor = KVStoreIngestor(
                splunk_service=self.service, session_key=self.session_key
            )
        return self._ingestor


dispatch(Analyst1DeleteIndicators, sys.argv, sys.stdin, sys.stdout, __name__)

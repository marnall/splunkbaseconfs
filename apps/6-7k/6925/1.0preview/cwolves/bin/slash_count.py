import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    ReportingCommand,
)

# TODO: this function is in development


@Configuration()
class SlashCount(StreamingCommand):
    def stream(self, records):
        self.logger.debug("CountMatchesCommand: %s", self)  # logs command line

        for record in records:
            record["thank you"] = "for using our plugin"
            yield record

        # yield {"hello": "world", "_time": "2018-01-01T00:00:00.000-00:00"}


dispatch(SlashCount, sys.argv, sys.stdin, sys.stdout, __name__)

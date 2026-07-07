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
            # record["hello"] = "world"
            for field in self.fieldnames:
                if field.startswith("time"):
                    field_name = field[:-6]
                    record[field_name + "_start"] = record[field][0]
                    record[field_name + "_end"] = record[field][1]
            yield record

        # yield {"hello": "world", "_time": "2018-01-01T00:00:00.000-00:00"}


dispatch(SlashCount, sys.argv, sys.stdin, sys.stdout, __name__)

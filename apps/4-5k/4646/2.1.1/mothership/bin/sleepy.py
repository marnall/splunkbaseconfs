import sys
import time
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option

@Configuration()
class MyCommand(StreamingCommand):
    seconds = Option(require=True)

    def stream(self, records):
        time.sleep(int(self.seconds))
        for record in records:
            yield record


dispatch(MyCommand, sys.argv, sys.stdin, sys.stdout, __name__)
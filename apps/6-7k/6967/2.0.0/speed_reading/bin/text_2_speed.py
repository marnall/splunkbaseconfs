import sys
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()

class speedText(StreamingCommand):

    field  = Option(name='field',  require=True)
    def stream(self, events):
        dest_field = "speed"
        for event in events:
            yield event

dispatch(speedText, sys.argv, sys.stdin, sys.stdout, __name__)
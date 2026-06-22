import sys
import import_declare_test

from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators
from geoip_command import stream

@Configuration()
class GeoipCommand(StreamingCommand):

    field = Option(name='field', require=False, validate=validators.Fieldname(), default='ip')
    prefix = Option(name='prefix', require=False, default='')
    databases = Option(name='databases', require=True)

    def stream(self, events):
        return stream(self, events)

dispatch(GeoipCommand, sys.argv, sys.stdin, sys.stdout, __name__)
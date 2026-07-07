import sys
import import_declare_test

from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators
from base64process import stream

@Configuration()
class B64Command(StreamingCommand):
    """

    ##Syntax
    b64 action=<str> field=<str>

    ##Description
    Encodes or decodes the specified field using base64

    """

    action = Option(name='action', require=True)
    field = Option(name='field', require=True, validate=validators.Fieldname())

    def stream(self, events):
        return stream(self, events)

dispatch(B64Command, sys.argv, sys.stdin, sys.stdout, __name__)
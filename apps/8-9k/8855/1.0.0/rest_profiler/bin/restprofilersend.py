import sys
import import_declare_test

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators
from rest_profiler_send import generate

@Configuration()
class RestprofilersendCommand(GeneratingCommand):
    """

    ##Syntax
    restprofilersend profile=<profile_name> mode=<preview|send>

    ##Description
    Executes (mode=send) or previews (mode=preview) a saved REST Profiler profile and returns the composed request and/or the HTTP response as a single event.

    """
    profile = Option(name='profile', require=True)
    mode = Option(name='mode', require=False, default='send')

    def generate(self):
       return generate(self)

dispatch(RestprofilersendCommand, sys.argv, sys.stdin, sys.stdout, __name__)
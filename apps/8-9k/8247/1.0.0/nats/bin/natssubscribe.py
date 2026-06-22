import sys
import import_declare_test

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators
from nats_subscribe_command import generate

@Configuration()
class NatssubscribeCommand(GeneratingCommand):
    """

    ##Syntax
    | natssubscribe subject=<subject> account=<account>

    ##Description
    Subscribe to NATS subject and stream messages in real-time

    """
    subject = Option(name='subject', require=True)
    account = Option(name='account', require=True)

    def generate(self):
       return generate(self)

dispatch(NatssubscribeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
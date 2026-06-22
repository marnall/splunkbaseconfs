import sys
import import_declare_test

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators
from list_remote_actions import generate

@Configuration()
class ListremoteactionsCommand(GeneratingCommand):
    account = Option(name='account', require=True)
    log_level = Option(name='log_level', require=False, default='ERROR')

    def generate(self):
       return generate(self)

dispatch(ListremoteactionsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
import sys
import import_declare_test

from splunklib.searchcommands import \
    dispatch, EventingCommand, Configuration, Option, validators
from run_remote_action import transform

@Configuration()
class RunremoteactionCommand(EventingCommand):

    account = Option(name='account', require=True)
    remote_action_id = Option(name='remote_action_id', require=True)
    device_uid = Option(name='device_uid', require=True, validate=validators.Fieldname())
    params = Option(name='params', require=False, default='')
    reason = Option(name='reason', require=False, default='')
    log_level = Option(name='log_level', require=False, default='ERROR')
    external_source = Option(name='external_source', require=False, default='Splunk')
    expires_in_minutes = Option(name='expires_in_minutes', require=False, validate=validators.Integer(), default='60')
    external_reference = Option(name='external_reference', require=False, default='')

    def transform(self, events):
       return transform(self, events)

dispatch(RunremoteactionCommand, sys.argv, sys.stdin, sys.stdout, __name__)
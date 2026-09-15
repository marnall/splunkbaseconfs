import sys
import import_declare_test

from splunklib.searchcommands import \
    dispatch, EventingCommand, Configuration, Option, validators
from mispfuse_command_logic import transform

@Configuration()
class MispfusepushCommand(EventingCommand):
    """

    ##Syntax
    mispfusepush account=<string> (template=<string>)?

    ##Description
    Push the incoming search results to a configured MISP instance as events/attributes using a MISPFuse template.

    """

    account = Option(name='account', require=True)
    template = Option(name='template', require=False, default='network_ioc')
    grouping = Option(name='grouping', require=False)
    group_field = Option(name='group_field', require=False, validate=validators.Fieldname())
    event_info = Option(name='event_info', require=False)
    distribution = Option(name='distribution', require=False, validate=validators.Integer(minimum=0, maximum=4))
    threat_level_id = Option(name='threat_level_id', require=False, validate=validators.Integer(minimum=1, maximum=4))
    analysis = Option(name='analysis', require=False, validate=validators.Integer(minimum=0, maximum=2))
    tags = Option(name='tags', require=False)
    to_ids = Option(name='to_ids', require=False, validate=validators.Boolean())
    publish = Option(name='publish', require=False, validate=validators.Boolean())

    def transform(self, events):
       return transform(self, events)

dispatch(MispfusepushCommand, sys.argv, sys.stdin, sys.stdout, __name__)
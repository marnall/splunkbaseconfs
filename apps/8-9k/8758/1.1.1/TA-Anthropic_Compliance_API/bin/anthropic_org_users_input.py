import import_declare_test

import sys

from splunklib import modularinput as smi
from anthropic_org_users_input_helper import stream_events, validate_input


class ANTHROPIC_ORG_USERS_INPUT(smi.Script):
    def __init__(self):
        super(ANTHROPIC_ORG_USERS_INPUT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('anthropic_org_users_input')
        scheme.description = 'Org Users'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                'account',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'fetch_groups',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'fetch_org_roles',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = ANTHROPIC_ORG_USERS_INPUT().run(sys.argv)
    sys.exit(exit_code)
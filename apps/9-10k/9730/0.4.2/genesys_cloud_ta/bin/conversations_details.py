import import_declare_test

import sys

from splunklib import modularinput as smi
from conversations_details_helper import stream_events, validate_input


class CONVERSATIONS_DETAILS(smi.Script):
    def __init__(self):
        super(CONVERSATIONS_DETAILS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('conversations_details')
        scheme.description = 'Conversations Details'
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
                'start_date',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = CONVERSATIONS_DETAILS().run(sys.argv)
    sys.exit(exit_code)
import import_declare_test

import sys

from splunklib import modularinput as smi
from subnet_input_helper import stream_events, validate_input


class SUBNET_DETAIL(smi.Script):
    def __init__(self):
        super(SUBNET_DETAIL, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('subnet_detail')
        scheme.description = 'Detail Subnets'
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
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = SUBNET_DETAIL().run(sys.argv)
    sys.exit(exit_code)
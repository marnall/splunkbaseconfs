import import_declare_test

import sys

from splunklib import modularinput as smi
from opencti_stream_helper import stream_events, validate_input


class OPENCTI_STREAM(smi.Script):
    def __init__(self):
        super(OPENCTI_STREAM, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('opencti_stream')
        scheme.description = 'OpenCTI Stream'
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
                'stream_id',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'import_from',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'input_type',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = OPENCTI_STREAM().run(sys.argv)
    sys.exit(exit_code)
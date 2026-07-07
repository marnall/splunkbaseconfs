import import_declare_test

import sys

from splunklib import modularinput as smi
from vrm_data_helper import stream_events


class VRM_DATA(smi.Script):
    def __init__(self):
        super(VRM_DATA, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('vrm_data')
        scheme.description = 'VRM Data'
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
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = VRM_DATA().run(sys.argv)
    sys.exit(exit_code)

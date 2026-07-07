import import_declare_test

import json
import sys

from splunklib import modularinput as smi
from sensors_helper import stream_events


class SENSORS(smi.Script):
    def __init__(self):
        super(SENSORS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('sensors')
        scheme.description = 'Sensors'
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
    exit_code = SENSORS().run(sys.argv)
    sys.exit(exit_code)
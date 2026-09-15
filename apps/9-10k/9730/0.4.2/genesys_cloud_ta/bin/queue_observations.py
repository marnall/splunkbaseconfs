import import_declare_test

import sys

from splunklib import modularinput as smi
from queue_observations_helper import stream_events, validate_input


class QUEUE_OBSERVATIONS(smi.Script):
    def __init__(self):
        super(QUEUE_OBSERVATIONS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('queue_observations')
        scheme.description = 'Queue Observations'
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
    exit_code = QUEUE_OBSERVATIONS().run(sys.argv)
    sys.exit(exit_code)
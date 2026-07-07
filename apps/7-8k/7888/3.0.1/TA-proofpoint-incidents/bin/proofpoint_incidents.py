import import_declare_test

import sys

from splunklib import modularinput as smi
from proofpoint_incidents_helper import stream_events, validate_input


class PROOFPOINT_INCIDENTS(smi.Script):
    def __init__(self):
        super(PROOFPOINT_INCIDENTS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('proofpoint_incidents')
        scheme.description = 'proofpoint_incidents'
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
                'collection_method',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'start_date',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'end_date',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'custom_sourcetype',
                required_on_create=True,
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
        return stream_events(self,inputs, ew)


if __name__ == '__main__':
    exit_code = PROOFPOINT_INCIDENTS().run(sys.argv)
    sys.exit(exit_code)
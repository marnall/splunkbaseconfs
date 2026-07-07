import import_declare_test
import sys

from splunklib import modularinput as smi
from findings_exposures_helper import stream_events


class FINDINGS_EXPOSURES(smi.Script):
    def __init__(self):
        super(FINDINGS_EXPOSURES, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('findings_exposures')
        scheme.description = 'Findings & Exposures'
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
    exit_code = FINDINGS_EXPOSURES().run(sys.argv)
    sys.exit(exit_code)

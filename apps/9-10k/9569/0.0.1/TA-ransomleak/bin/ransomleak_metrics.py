import import_declare_test

import sys

from splunklib import modularinput as smi
from metrics_helper import stream_events, validate_input


class RANSOMLEAK_METRICS(smi.Script):
    def __init__(self):
        super(RANSOMLEAK_METRICS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('ransomleak_metrics')
        scheme.description = 'Programme Metrics'
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
                'metrics',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'lookback_days',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'team',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'channel',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = RANSOMLEAK_METRICS().run(sys.argv)
    sys.exit(exit_code)
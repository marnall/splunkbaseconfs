import import_declare_test

import sys

from splunklib import modularinput as smi
from statseeker_memory_metrics_helper import stream_events, validate_input


class STATSEEKER_MEMORY_METRICS(smi.Script):
    def __init__(self):
        super(STATSEEKER_MEMORY_METRICS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('statseeker_memory_metrics')
        scheme.description = 'Memory Metrics'
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
                'metric_fields',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'metadata_fields',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'timefilter',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'sample_interval',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'page_size',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'device_filter',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'device_name_filter',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'name_filter',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = STATSEEKER_MEMORY_METRICS().run(sys.argv)
    sys.exit(exit_code)
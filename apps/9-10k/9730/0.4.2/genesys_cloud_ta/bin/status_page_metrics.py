import import_declare_test

import sys

from splunklib import modularinput as smi
from status_page_metrics_helper import stream_events, validate_input


class STATUS_PAGE_METRICS(smi.Script):
    def __init__(self):
        super(STATUS_PAGE_METRICS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('status_page_metrics')
        scheme.description = 'System Services Status'
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
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = STATUS_PAGE_METRICS().run(sys.argv)
    sys.exit(exit_code)
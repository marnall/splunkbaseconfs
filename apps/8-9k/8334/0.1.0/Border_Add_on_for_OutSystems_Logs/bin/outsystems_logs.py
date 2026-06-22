import import_declare_test

import sys

from splunklib import modularinput as smi
from outsystems_logs_helper import stream_events, validate_input


class OUTSYSTEMS_LOGS(smi.Script):
    def __init__(self):
        super(OUTSYSTEMS_LOGS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('outsystems_logs')
        scheme.description = 'OutSystems Platform Logs'
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
                'endpoint',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'event_delay',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'date_offset_hours',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'fetch_chunk_minutes',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'sleep_time_ms',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'start_time',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'end_time',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = OUTSYSTEMS_LOGS().run(sys.argv)
    sys.exit(exit_code)
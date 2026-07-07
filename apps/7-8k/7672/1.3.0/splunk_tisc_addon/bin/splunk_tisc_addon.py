import import_declare_test

import sys

from splunklib import modularinput as smi
from splunk_tisc_addon_helper import stream_events, validate_input


class SPLUNK_TISC_ADDON(smi.Script):
    def __init__(self):
        super(SPLUNK_TISC_ADDON, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('splunk_tisc_addon')
        scheme.description = 'Input'
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
                'days_till_expiry',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'never_expire',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'additional_attributes',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'filters',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'json_filters',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'advanced',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = SPLUNK_TISC_ADDON().run(sys.argv)
    sys.exit(exit_code)
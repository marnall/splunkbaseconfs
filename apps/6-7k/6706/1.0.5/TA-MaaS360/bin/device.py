import import_declare_test

import sys

from splunklib import modularinput as smi
from input_device import stream_events, validate_input


class DEVICE(smi.Script):
    def __init__(self):
        super(DEVICE, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('device')
        scheme.description = 'Device'
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
                'maas360_account',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'device_status',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'platform',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'managed_status',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'plc_compliance',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'rule_compliance',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'app_compliance',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'pswd_compliance',
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = DEVICE().run(sys.argv)
    sys.exit(exit_code)
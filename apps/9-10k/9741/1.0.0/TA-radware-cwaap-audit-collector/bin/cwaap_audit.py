import import_declare_test

import sys

from splunklib import modularinput as smi
from cwaap_audit_helper import stream_events, validate_input


class CWAAP_AUDIT(smi.Script):
    def __init__(self):
        super(CWAAP_AUDIT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('cwaap_audit')
        scheme.description = 'Radware CWAAP audit log'
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
                'account_id',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'api_key',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'initial_lookback_minutes',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'max_backfill_minutes',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = CWAAP_AUDIT().run(sys.argv)
    sys.exit(exit_code)
import import_declare_test

import sys

from splunklib import modularinput as smi
from ipf_input_helper import stream_events, validate_input


class IPF_INPUT(smi.Script):
    def __init__(self):
        super(IPF_INPUT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('ipf_input')
        scheme.description = 'IP Fabric Input'
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
                'ipf_url',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'snapshot_id',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'use_ipf_timestamp',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'load_intent_checks',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'only_count',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'table_path',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'table_filter',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = IPF_INPUT().run(sys.argv)
    sys.exit(exit_code)
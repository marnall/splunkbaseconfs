import import_declare_test

import sys

from splunklib import modularinput as smi
from powerplatform_flow_runs_helper import stream_events, validate_input


class POWERPLATFORM_FLOWS_RUNS(smi.Script):
    def __init__(self):
        super(POWERPLATFORM_FLOWS_RUNS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('powerplatform_flows_runs')
        scheme.description = 'Power Platform Flow Runs'
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
                'service_account',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'app_registration',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'use_proxy',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'include_actions',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = POWERPLATFORM_FLOWS_RUNS().run(sys.argv)
    sys.exit(exit_code)
import import_declare_test

import json
import sys
import nessus_pro_plugin_handler

from splunklib import modularinput as smi


class NESSUS_PRO_PLUGIN(smi.Script):
    def __init__(self):
        super(NESSUS_PRO_PLUGIN, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('nessus_pro_plugin')
        scheme.description = 'Nessus Professional Plugin Data'
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
                'start_date',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        nessus_pro_plugin_handler.validate_input(self, definition)


    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        nessus_pro_plugin_handler.stream_events(self, inputs, event_writer)


if __name__ == '__main__':
    exit_code = NESSUS_PRO_PLUGIN().run(sys.argv)
    sys.exit(exit_code)
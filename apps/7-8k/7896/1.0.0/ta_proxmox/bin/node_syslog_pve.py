import import_declare_test

import sys

from splunklib import modularinput as smi
from ta_proxmox_input_node_syslog import stream_events, validate_input


class NODE_SYSLOG_PVE(smi.Script):
    def __init__(self):
        super(NODE_SYSLOG_PVE, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('node_syslog_pve')
        scheme.description = 'Node Syslog (PVE)'
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
                'pveserver',
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = NODE_SYSLOG_PVE().run(sys.argv)
    sys.exit(exit_code)
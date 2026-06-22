import import_declare_test

import sys

from splunklib import modularinput as smi
from maze_investigations_search_helper import stream_events, validate_input


class MAZE_INVESTIGATIONS_SEARCH(smi.Script):
    def __init__(self):
        super(MAZE_INVESTIGATIONS_SEARCH, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('maze_investigations_search')
        scheme.description = 'Investigations Search'
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
                'backfill_days',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = MAZE_INVESTIGATIONS_SEARCH().run(sys.argv)
    sys.exit(exit_code)
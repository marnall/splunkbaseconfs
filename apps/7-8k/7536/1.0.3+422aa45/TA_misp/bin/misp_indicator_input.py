import import_declare_test

import sys

from splunklib import modularinput as smi
from misp_indicator_input_helper import stream_events, validate_input


class MISP_INDICATOR_INPUT(smi.Script):
    def __init__(self):
        super(MISP_INDICATOR_INPUT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('misp_indicator_input')
        scheme.description = 'MISP Indicator Input'
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
                'misp_instance',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'max_requests',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'import_period',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'types',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'to_ids',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'published',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'include_tags',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'exclude_tags',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'warning_list',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'continuous_importing',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'override_timestamps',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'normalize_field_names',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'normalized_field_prefix',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'expand_tags',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = MISP_INDICATOR_INPUT().run(sys.argv)
    sys.exit(exit_code)
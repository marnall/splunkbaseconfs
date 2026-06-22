import import_declare_test

import json
import sys
import elastic_data_input_handler

from splunklib import modularinput as smi


class ELASTIC_DATA_INPUT(smi.Script):
    def __init__(self):
        super(ELASTIC_DATA_INPUT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('elastic_data_input')
        scheme.description = 'elastic_data_input'
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
                'es_index',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'time_field',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'batch_size',
                required_on_create=True,
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
                'advanced_filter_query',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        elastic_data_input_handler.validate_input(definition.metadata['session_key'], self, definition)


    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        elastic_data_input_handler.stream_events(self._input_definition.metadata['session_key'], self, inputs, event_writer)



if __name__ == '__main__':
    exit_code = ELASTIC_DATA_INPUT().run(sys.argv)
    sys.exit(exit_code)
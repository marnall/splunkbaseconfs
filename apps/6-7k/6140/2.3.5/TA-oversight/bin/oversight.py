import import_declare_test
import input_module_oversight as input_module
import sys
import json

from splunklib import modularinput as smi

class OVERSIGHT(smi.Script):

    def __init__(self):
        super(OVERSIGHT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('oversight')
        scheme.description = 'Oversight'
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
                'asset_group',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'source_expression',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'source_fields',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'id_field',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'id_field_rename',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'mv_id_field',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'enrichment_expression',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'enrichment_fields',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'source_filter',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'inventory_filter',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'inventory_source',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'aggregation_fields',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'replicate',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'cron',
                required_on_create=True,
            )
        )
        
        return scheme

    def validate_input(self, definition):
        input_module.validate_input(self, definition)


    def stream_events(self, inputs, ew):
        input_module.stream_events(self, inputs, ew)


if __name__ == '__main__':
    exit_code = OVERSIGHT().run(sys.argv)
    sys.exit(exit_code)
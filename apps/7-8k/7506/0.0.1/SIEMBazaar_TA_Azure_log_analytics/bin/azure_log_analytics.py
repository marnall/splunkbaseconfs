import import_declare_test

import json
import sys

from splunklib import modularinput as smi

#manual imports
from sb_utils import set_logger
import sb_flv
import im_azure_loganalytics as input_module


class AZURE_LOG_ANALYTICS(smi.Script):
    def __init__(self):
        super(AZURE_LOG_ANALYTICS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('azure_log_analytics')
        scheme.description = 'Azure Log Analytics'
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
                'azure_account',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'sb_license',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'query',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'since_date',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'event_delay',
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return input_module.validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        for input_name, input_item in inputs.inputs.items():
            try:
                session_key = self._input_definition.metadata["session_key"]
                logger = set_logger(session_key,input_name)
                self.logger = logger
                self.session_key = session_key
                flv_ok = sb_flv.flv(self, input_item, "2")
                if flv_ok:
                    logger.info(f"Starting data collection for {input_name}")
                    input_module.collect_events(self, input_name, input_item, ew)  
            except Exception as e:
                logger.error(f"Error in data collection for {input_name}: {e}")  
                sys.exit(2)  # Error

if __name__ == '__main__':
    exit_code = AZURE_LOG_ANALYTICS().run(sys.argv)
    sys.exit(exit_code)
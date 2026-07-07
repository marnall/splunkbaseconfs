import import_declare_test

import json
import sys

import common.log as log

logger = log.get_logger(__file__)

from splunklib import modularinput as smi
from mandiant_utils import get_credentials


class MANDIANT_ADVANTAGE_MONITORING_ALERTS(smi.Script):
    def __init__(self):
        super(MANDIANT_ADVANTAGE_MONITORING_ALERTS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('mandiant_advantage_monitoring_alerts')
        scheme.description = 'Mandiant Digital Threat Monitoring Alerts'
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
                'mandiant_advantage_account',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'alerts_days_back',
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)

        try:
            # Keep all code (including imports) inside this higher level try block
            # to make sure that error logs always gets printed in log file
            import sys
            import os
            sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', 'modinputs', 'alerts')))
            sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', 'common')))
            import collector
            import utility
            utility.disable_external_lib_logging()

            event_writer = ew
            meta_configs = self._input_definition.metadata
            session_key = meta_configs.get("session_key")
            account_info = get_credentials(input_items[1]['mandiant_advantage_account'], session_key)
            account_info["name"] = input_items[1]['mandiant_advantage_account']
            ac = collector.AlertCollector()
            ac.run(input_items[1], account_info, event_writer, session_key)
        except Exception:
            logger.error(traceback.format_exc())

if __name__ == '__main__':
    exit_code = MANDIANT_ADVANTAGE_MONITORING_ALERTS().run(sys.argv)
    sys.exit(exit_code)
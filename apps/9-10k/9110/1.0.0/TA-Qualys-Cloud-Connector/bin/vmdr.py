import import_declare_test

import sys
import os

from splunklib import modularinput as smi
import common.log as log

# Remove proxy environment variables to prevent conflicts with configured proxy settings
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(proxy_var, None)

logger = log.get_logger(__file__)

class VMDR(smi.Script):
    def __init__(self):
        super(VMDR, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('vmdr')
        scheme.description = 'VMDR'
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
        scheme.add_argument(
            smi.Argument(
                'use_multi_threading',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'num_threads',
                required_on_create=False,
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
            import sys
            import os
            import traceback

            sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', 'modinputs', 'vmdr')))
            sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', 'common')))

            import collector
            import utility

            utility.disable_external_lib_logging()

            event_writer = ew
            meta_configs = self._input_definition.metadata
            session_key = meta_configs.get("session_key")

            account_name = input_items[1]['account']
            account_info = collector._load_account(session_key, account_name)
            account_info["name"] = account_name

            ac = collector.VmdrCollector()
            ac.run(input_items[1], account_info, event_writer, session_key)
        except Exception:
            logger.error(traceback.format_exc())


if __name__ == '__main__':
    exit_code = VMDR().run(sys.argv)
    sys.exit(exit_code)
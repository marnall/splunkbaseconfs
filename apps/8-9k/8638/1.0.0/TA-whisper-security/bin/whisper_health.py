import import_declare_test

import json
import logging
import sys
import time

from splunklib import modularinput as smi

logger = logging.getLogger(__name__)


class WHISPER_HEALTH(smi.Script):
    def __init__(self):
        super(WHISPER_HEALTH, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('whisper_health')
        scheme.description = 'Whisper API Health Check'
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
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        from whisper_command_helpers import get_api_client_from_inputs
        from whisper_health_input import (
            SOURCETYPE,
            collect_health_event,
            format_event,
            load_checkpoint,
            save_checkpoint,
        )

        for input_name, input_item in inputs.inputs.items():
            try:
                index = input_item.get("index", "_internal")
                checkpoint_dir = inputs.metadata.get("checkpoint_dir", "")

                # Resolve credentials via the service context
                from whisper_config import get_config
                account_name = input_item.get("account", "default")
                config = get_config(self.service, account_name=account_name)

                event_data = collect_health_event(
                    base_url=config.base_url,
                    api_key=config.api_key,
                    timeout=config.timeout,
                    proxy=config.proxy_url,
                )

                event = smi.Event(
                    data=format_event(event_data),
                    index=index,
                    sourcetype=SOURCETYPE,
                )
                ew.write_event(event)

                save_checkpoint(checkpoint_dir, input_name, time.time())

                ew.log(
                    "INFO",
                    "action=health_check input=%s status=%s response_time_ms=%d"
                    % (
                        input_name,
                        event_data.get("status", "UNKNOWN"),
                        event_data.get("response_time_ms", 0),
                    ),
                )

            except Exception as exc:
                ew.log("ERROR", "action=health_check input=%s error=%s" % (input_name, exc))


if __name__ == '__main__':
    exit_code = WHISPER_HEALTH().run(sys.argv)
    sys.exit(exit_code)

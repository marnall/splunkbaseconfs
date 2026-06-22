import import_declare_test

import json
import logging
import sys
import time

from splunklib import modularinput as smi

logger = logging.getLogger(__name__)


class WHISPER_THREAT_INTEL(smi.Script):
    def __init__(self):
        super(WHISPER_THREAT_INTEL, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('whisper_threat_intel')
        scheme.description = 'Whisper ES Threat Intel Feed'
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
                'max_indicators',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'include_infrastructure',
                required_on_create=False,
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
        from whisper_threat_intel_input import (
            SOURCETYPE,
            DEFAULT_MAX_INDICATORS,
            assess_indicators,
            format_intel_events,
            format_summary_event,
            load_checkpoint,
            save_checkpoint,
            seed_initial_indicators,
        )

        for input_name, input_item in inputs.inputs.items():
            try:
                index = input_item.get("index", "whisper")
                checkpoint_dir = inputs.metadata.get("checkpoint_dir", "")
                max_indicators = int(input_item.get("max_indicators", DEFAULT_MAX_INDICATORS))
                include_infra = str(input_item.get("include_infrastructure", "false")).lower() in (
                    "true", "1", "yes",
                )

                client = get_api_client_from_inputs(input_item, self.service)
                start_time = time.monotonic()

                # Bootstrap indicators from the Whisper API graph
                # No KV Store dependency — works on IDM (Splunk Cloud Classic)
                ew.log("INFO", "action=threat_intel_seed input=%s reason=graph_seeding" % input_name)
                indicators = seed_initial_indicators(client)

                ip_records, domain_records = assess_indicators(
                    client, indicators, max_indicators=max_indicators,
                    include_infrastructure=include_infra,
                )
                client.close()

                # Write intel records as events (event-based architecture)
                # Downstream saved searches populate KV Store from these events
                intel_events = format_intel_events(ip_records, domain_records)
                for event_data in intel_events:
                    event = smi.Event(
                        data=json.dumps(event_data, default=str),
                        index=index,
                        sourcetype=SOURCETYPE,
                    )
                    ew.write_event(event)

                elapsed = time.monotonic() - start_time

                ip_count = len(ip_records)
                domain_count = len(domain_records)
                ip_stats = {"inserted": ip_count, "errors": 0}
                domain_stats = {"inserted": domain_count, "errors": 0}

                # Write summary event
                summary = smi.Event(
                    data=format_summary_event(ip_stats, domain_stats, elapsed),
                    index=index,
                    sourcetype=SOURCETYPE,
                )
                ew.write_event(summary)

                save_checkpoint(checkpoint_dir, input_name, time.time())

                ew.log(
                    "INFO",
                    "action=threat_intel input=%s ip_events=%d domain_events=%d elapsed_s=%.1f"
                    % (
                        input_name,
                        ip_count,
                        domain_count,
                        elapsed,
                    ),
                )

            except Exception as exc:
                ew.log("ERROR", "action=threat_intel input=%s error=%s" % (input_name, exc))


if __name__ == '__main__':
    exit_code = WHISPER_THREAT_INTEL().run(sys.argv)
    sys.exit(exit_code)

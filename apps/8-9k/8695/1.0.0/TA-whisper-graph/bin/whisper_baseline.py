import import_declare_test

import json
import logging
import sys
import time

from splunklib import modularinput as smi

logger = logging.getLogger(__name__)


class WHISPER_BASELINE(smi.Script):
    def __init__(self):
        super(WHISPER_BASELINE, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('whisper_baseline')
        scheme.description = 'Whisper Attack Surface Baseline'
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
                'domains',
                required_on_create=True,
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
        from whisper_baseline_input import (
            SOURCETYPE,
            SPF_SOURCETYPE,
            build_snapshot,
            collect_baseline,
            collect_domain_compliance,
            format_event,
            format_summary_event,
            load_checkpoint,
            parse_domain_list,
            save_checkpoint,
        )
        from whisper_change_detector import (
            CHANGE_SOURCETYPE,
            build_risk_event,
            detect_changes,
            format_change_event,
            is_high_priority,
        )

        for input_name, input_item in inputs.inputs.items():
            try:
                domains_str = input_item.get("domains", "")
                domains = parse_domain_list(domains_str)
                if not domains:
                    logger.warning("No domains configured for input %s", input_name)
                    continue

                index = input_item.get("index", "whisper")
                checkpoint_dir = inputs.metadata.get("checkpoint_dir", "")

                client = get_api_client_from_inputs(input_item, self.service)
                start_time = time.monotonic()

                # Load previous checkpoint for change detection
                prev_checkpoint = load_checkpoint(checkpoint_dir, input_name)
                prev_snapshot = prev_checkpoint.get("snapshot", {})

                # Collect current baseline
                events, stats = collect_baseline(client, domains)

                # Collect SPF compliance data for each domain
                spf_events = []
                for domain in domains:
                    domain = domain.strip().lower()
                    if not domain:
                        continue
                    spf_event = collect_domain_compliance(client, domain)
                    if spf_event:
                        spf_events.append(spf_event)

                client.close()

                # Write baseline events
                for event_data in events:
                    event = smi.Event(
                        data=format_event(event_data),
                        index=index,
                        sourcetype=SOURCETYPE,
                    )
                    ew.write_event(event)

                # Write SPF compliance events
                for event_data in spf_events:
                    event = smi.Event(
                        data=json.dumps(event_data, default=str),
                        index=index,
                        sourcetype=SPF_SOURCETYPE,
                    )
                    ew.write_event(event)

                # Build snapshot and detect changes
                current_snapshot = build_snapshot(events)
                if prev_snapshot:
                    changes = detect_changes(prev_snapshot, current_snapshot)
                    for change in changes:
                        event = smi.Event(
                            data=format_change_event(change),
                            index=index,
                            sourcetype=CHANGE_SOURCETYPE,
                        )
                        ew.write_event(event)
                        if is_high_priority(change):
                            risk = build_risk_event(change)
                            risk_event = smi.Event(
                                data=json.dumps(risk, default=str),
                                index="risk",
                                sourcetype="stash",
                            )
                            ew.write_event(risk_event)

                # Save checkpoint
                elapsed = time.monotonic() - start_time
                save_checkpoint(
                    checkpoint_dir,
                    input_name,
                    time.time(),
                    current_snapshot,
                )

                # Write summary event
                summary_stats = {
                    **stats,
                    "spf_domains_checked": len(spf_events),
                }
                summary = smi.Event(
                    data=format_summary_event(summary_stats, elapsed),
                    index=index,
                    sourcetype=SOURCETYPE,
                )
                ew.write_event(summary)

                ew.log(
                    "INFO",
                    "action=baseline input=%s records=%d spf=%d domains=%d elapsed_s=%.1f"
                    % (
                        input_name,
                        stats.get("total_records", 0),
                        len(spf_events),
                        stats.get("domains_processed", 0),
                        elapsed,
                    ),
                )

            except Exception as exc:
                ew.log("ERROR", "action=baseline input=%s error=%s" % (input_name, exc))


if __name__ == '__main__':
    exit_code = WHISPER_BASELINE().run(sys.argv)
    sys.exit(exit_code)

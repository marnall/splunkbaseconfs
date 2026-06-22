import import_declare_test

import json
import logging
import sys

from splunklib import modularinput as smi

logger = logging.getLogger(__name__)


class WHISPER_MULTITENANT(smi.Script):
    def __init__(self):
        super(WHISPER_MULTITENANT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('whisper_multitenant')
        scheme.description = 'Whisper Multi-Tenant Attack Surface'
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
                'client_id',
                required_on_create=True,
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
                'max_domains',
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
        from whisper_multitenant_input import (
            CHANGE_SOURCETYPE,
            SOURCETYPE,
            SUMMARY_SOURCETYPE,
            collect_tenant_baseline,
            format_tenant_summary,
            validate_tenant_config,
        )
        from whisper_baseline_input import (
            SPF_SOURCETYPE,
            DNSSEC_SOURCETYPE,
            collect_domain_compliance,
            format_event,
            parse_domain_list,
        )
        from whisper_change_detector import format_change_event

        for input_name, input_item in inputs.inputs.items():
            try:
                config = {
                    "client_id": input_item.get("client_id", ""),
                    "domains": input_item.get("domains", ""),
                    "max_domains": int(input_item.get("max_domains", 500)),
                }

                errors = validate_tenant_config(config)
                if errors:
                    logger.error(
                        "Invalid tenant config for %s: %s", input_name, "; ".join(errors)
                    )
                    continue

                index = input_item.get("index", "whisper")
                checkpoint_dir = inputs.metadata.get("checkpoint_dir", "")
                client_id = config["client_id"]

                client = get_api_client_from_inputs(input_item, self.service)
                result = collect_tenant_baseline(client, config, checkpoint_dir)

                # Collect compliance data for tenant domains
                domains = parse_domain_list(config["domains"])
                spf_events = []
                dnssec_events = []
                for domain in domains:
                    domain = domain.strip().lower()
                    if not domain:
                        continue
                    spf_event, dnssec_event = collect_domain_compliance(client, domain)
                    if spf_event:
                        spf_event["client_id"] = client_id
                        spf_events.append(spf_event)
                    if dnssec_event:
                        dnssec_event["client_id"] = client_id
                        dnssec_events.append(dnssec_event)

                client.close()

                # Write baseline events
                for event_data in result["events"]:
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

                # Write DNSSEC compliance events
                for event_data in dnssec_events:
                    event = smi.Event(
                        data=json.dumps(event_data, default=str),
                        index=index,
                        sourcetype=DNSSEC_SOURCETYPE,
                    )
                    ew.write_event(event)

                # Write change events
                for change in result["changes"]:
                    event = smi.Event(
                        data=format_change_event(change),
                        index=index,
                        sourcetype=CHANGE_SOURCETYPE,
                    )
                    ew.write_event(event)

                # Write risk events
                for risk in result["risk_events"]:
                    event = smi.Event(
                        data=json.dumps(risk, default=str),
                        index="risk",
                        sourcetype="stash",
                    )
                    ew.write_event(event)

                # Write summary
                summary = smi.Event(
                    data=format_tenant_summary(client_id, result["stats"]),
                    index=index,
                    sourcetype=SUMMARY_SOURCETYPE,
                )
                ew.write_event(summary)

                ew.log(
                    "INFO",
                    "action=multitenant input=%s client=%s records=%d spf=%d dnssec=%d changes=%d"
                    % (
                        input_name,
                        client_id,
                        result["stats"].get("total_records", 0),
                        len(spf_events),
                        len(dnssec_events),
                        result["stats"].get("changes_detected", 0),
                    ),
                )

            except Exception as exc:
                ew.log(
                    "ERROR",
                    "action=multitenant input=%s error=%s" % (input_name, exc),
                )


if __name__ == '__main__':
    exit_code = WHISPER_MULTITENANT().run(sys.argv)
    sys.exit(exit_code)

#!/usr/bin/env python
"""Modular input: Terrace Networks Threat Feed.
Periodically pulls IPs from an IP list config and ingests as threat indicators.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

import splunklib.modularinput as smi


class TerraceThreatFeedInput(smi.Script):
    """Polls the Terrace Networks IP feed and writes events to Splunk."""

    def get_scheme(self):
        scheme = smi.Scheme("Terrace Networks Threat Feed")
        scheme.description = (
            "Periodically polls a Terrace Networks IP list config "
            "and ingests malicious IPs as threat indicators."
        )
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.streaming_mode = smi.Scheme.streaming_mode_xml

        arg = smi.Argument("api_key")
        arg.title = "API Key"
        arg.data_type = smi.Argument.data_type_string
        arg.required_on_create = True
        arg.description = "Terrace Networks API key (format: KeyID.KeySecret)"
        scheme.add_argument(arg)

        arg = smi.Argument("base_url")
        arg.title = "Base URL"
        arg.data_type = smi.Argument.data_type_string
        arg.required_on_create = False
        arg.description = "API base URL (default: https://api.terracenetworks.com)"
        scheme.add_argument(arg)

        arg = smi.Argument("config_id")
        arg.title = "IP List Config ID"
        arg.data_type = smi.Argument.data_type_string
        arg.required_on_create = True
        arg.description = "KSUID of the IP list config to pull from"
        scheme.add_argument(arg)

        return scheme

    def validate_input(self, validation_definition):
        api_key = validation_definition.parameters.get("api_key", "")
        if "." not in api_key:
            raise ValueError(
                "API key must be in KeyID.KeySecret format (contains a dot separator)"
            )
        config_id = validation_definition.parameters.get("config_id", "")
        if not config_id:
            raise ValueError("config_id is required")

    def stream_events(self, inputs, ew):
        for input_name, input_item in inputs.inputs.items():
            self._process_input(input_name, input_item, inputs, ew)

    def _process_input(self, input_name, input_item, inputs, ew):
        api_key = input_item["api_key"]
        base_url = input_item.get("base_url", "https://api.terracenetworks.com")
        config_id = input_item["config_id"]
        target_index = input_item.get("index", "main")

        from terrace_api import TerraceClient

        client = TerraceClient(api_key=api_key, base_url=base_url)

        try:
            indicators = client.pull_ip_feed(config_id)
        except Exception as e:
            ew.log(
                smi.EventWriter.ERROR,
                f"Terrace feed pull failed for {input_name}: {e}",
            )
            return

        count = 0
        for indicator in indicators:
            event = smi.Event()
            event.stanza = input_name
            event.sourcetype = "terrace:ip_feed"
            event.index = target_index

            # CIM Threat Intelligence data model fields
            ip = indicator.get("src_ip", "")
            classification = indicator.get("classification", "malicious")

            if classification == "malicious":
                weight = 100
            elif classification == "suspicious":
                weight = 50
            else:
                weight = 10

            enriched = {
                # CIM required fields
                "ip": ip,
                "threat_key": f"terrace:{ip}",
                "threat_match_field": "src_ip",
                "threat_match_value": ip,
                "description": f"Terrace Networks: {ip}",
                "weight": weight,
                # CIM recommended fields
                "threat_collection": "ip_intel",
                "threat_collection_key": f"terrace:{ip}",
                "threat_source": "Terrace Networks",
                "threat_source_type": "feed",
                "threat_category": classification,
                # Terrace-specific fields
                "source": "terrace",
                "first_seen": indicator.get("first_seen", ""),
                "dst_ips": indicator.get("dst_ips", 0),
                "dst_ports": indicator.get("dst_ports", 0),
                "exploits": indicator.get("exploits", []),
            }

            # Set event time from the indicator timestamp if available
            ts = indicator.get("timestamp")
            if ts:
                event.time = ts

            event.data = json.dumps(enriched)
            ew.write_event(event)
            count += 1

        ew.log(
            smi.EventWriter.INFO,
            f"Terrace feed ingested {count} indicators for {input_name}",
        )


if __name__ == "__main__":
    sys.exit(TerraceThreatFeedInput().run(sys.argv))

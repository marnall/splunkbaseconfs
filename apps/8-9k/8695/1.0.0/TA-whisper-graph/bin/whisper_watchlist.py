import import_declare_test

import json
import logging
import sys
import time

from splunklib import modularinput as smi

logger = logging.getLogger(__name__)


class WHISPER_WATCHLIST(smi.Script):
    def __init__(self):
        super(WHISPER_WATCHLIST, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('whisper_watchlist')
        scheme.description = 'Whisper Watchlist Enrichment'
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
                'account',
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        from whisper_command_helpers import get_api_client_from_inputs
        from whisper_field_mapper import apply_prefix
        from whisper_watchlist_input import (
            SOURCETYPE,
            DEFAULT_MAX_INDICATORS,
            enrich_watchlist,
            format_summary_event,
            load_checkpoint,
            load_watchlist_from_csv,
            save_checkpoint,
        )

        for input_name, input_item in inputs.inputs.items():
            try:
                index = input_item.get("index", "whisper")
                checkpoint_dir = inputs.metadata.get("checkpoint_dir", "")
                max_indicators = int(input_item.get("max_indicators", DEFAULT_MAX_INDICATORS))

                client = get_api_client_from_inputs(input_item, self.service)
                start_time = time.monotonic()

                # Load indicators from CSV watchlist file (no KV Store dependency)
                # Works on IDM (Splunk Cloud Classic) where KV Store is inaccessible
                import os
                splunk_home = os.environ.get("SPLUNK_HOME", "")
                csv_path = os.path.join(
                    splunk_home, "etc", "apps", "TA-whisper-graph",
                    "lookups", "whisper_watchlist.csv",
                )
                indicators = []
                if os.path.isfile(csv_path):
                    indicators = load_watchlist_from_csv(csv_path)

                if not indicators:
                    logger.info("No indicators found in watchlist CSV for %s", input_name)
                    client.close()
                    continue

                enrichment_events, stats = enrich_watchlist(
                    client, indicators,
                    max_indicators=max_indicators,
                )
                client.close()

                # Write enrichment records as events (event-based architecture)
                # Downstream saved search populates KV Store from these events
                for event_data in enrichment_events:
                    event = smi.Event(
                        data=json.dumps(event_data, default=str),
                        index=index,
                        sourcetype=SOURCETYPE,
                    )
                    ew.write_event(event)

                    # Also emit a flat whisper:enrichment event for dashboards
                    raw = event_data.pop("_raw_enrichment", None)
                    if raw:
                        flat = apply_prefix(raw, prefix="whisper_")
                        indicator = event_data.get("indicator", "")
                        itype = event_data.get("indicator_type", "")
                        if itype == "domain":
                            flat["domain"] = indicator
                        else:
                            flat.setdefault("whisper_ip", indicator)
                        flat["indicator"] = indicator
                        flat["indicator_type"] = itype
                        # Flatten list values to comma-separated strings
                        # so JSON stays single-line for proper field extraction
                        for k, v in flat.items():
                            if isinstance(v, list):
                                flat[k] = ", ".join(str(i) for i in v)
                        enrichment_event = smi.Event(
                            data=json.dumps(flat, default=str),
                            index=index,
                            sourcetype="whisper:enrichment",
                        )
                        ew.write_event(enrichment_event)

                elapsed = time.monotonic() - start_time

                # Write summary event
                summary = smi.Event(
                    data=format_summary_event(stats, elapsed),
                    index=index,
                    sourcetype=SOURCETYPE,
                )
                ew.write_event(summary)

                save_checkpoint(checkpoint_dir, input_name, time.time())

                ew.log(
                    "INFO",
                    "action=watchlist input=%s enriched=%d skipped=%d errors=%d elapsed_s=%.1f"
                    % (
                        input_name,
                        stats.get("enriched", 0),
                        stats.get("skipped", 0),
                        stats.get("errors", 0),
                        elapsed,
                    ),
                )

            except Exception as exc:
                ew.log("ERROR", "action=watchlist input=%s error=%s" % (input_name, exc))


if __name__ == '__main__':
    exit_code = WHISPER_WATCHLIST().run(sys.argv)
    sys.exit(exit_code)

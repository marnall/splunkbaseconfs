#!/usr/bin/env python3

import os, sys

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
LIB_DIR = os.path.abspath(os.path.join(THIS_DIR, os.pardir, "lib"))
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

import logging
import json
import traceback
from datetime import datetime, timezone
from splunklib.modularinput import Scheme, Argument, Event, EventWriter, Script
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from api_client import MethodAuditClient
from checkpoint import load_checkpoint, save_checkpoint

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

class MethodAuditInput(Script):
    @staticmethod
    def _to_epoch(timestamp_str):
        """
        Convert ISO timestamp string to epoch seconds for Splunk.
        Handles formats like:
        - 2025-01-15T09:30:00Z
        - 2025-01-15T09:30:00.123456Z
        """
        if not timestamp_str:
            return None

        # Try with microseconds
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            return int(dt.timestamp())
        except ValueError:
            pass

        # Try without microseconds
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
            return int(dt.timestamp())
        except ValueError:
            logger.warning(f"Could not parse timestamp: {timestamp_str}")
            return None

    def get_scheme(self):
        scheme = Scheme("method_audit_logs")
        scheme.title = "Method Security Audit Log Ingestion"
        scheme.description = "Ingest audit events about your usage of the Method Security Platform via API"
        scheme.use_external_validation = True
        scheme.streaming_mode = Scheme.streaming_mode_xml
        scheme.use_single_instance = False

        scheme.add_argument(Argument("start_time", title="Start Time", required_on_create=True))
        scheme.add_argument(Argument("timezone", title="Timezone", required_on_create=False))
        scheme.add_argument(Argument("base_url", title="Base URL", required_on_create=True))
        scheme.add_argument(Argument("client_id", title="Client ID", required_on_create=True))
        scheme.add_argument(Argument("client_secret", title="Client Secret", required_on_create=True))

        return scheme

    def validate_input(self, validation_definition):
        base_url = validation_definition.parameters.get("base_url")
        client_id = validation_definition.parameters.get("client_id")
        client_secret = validation_definition.parameters.get("client_secret")
        user_timezone = validation_definition.parameters.get("timezone") or "UTC"

        if not base_url:
            raise ValueError("base_url is required")
        if not client_id:
            raise ValueError("client_id is required")
        if not client_secret:
            raise ValueError("client_secret is required")

        # Validate timezone
        try:
            ZoneInfo(user_timezone)
        except ZoneInfoNotFoundError:
            raise ValueError(
                f"Invalid timezone '{user_timezone}'. Must be a valid IANA timezone name "
                f"(e.g., UTC, America/New_York, America/Los_Angeles). "
                f"See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
            )

        # Test connectivity and credentials
        try:
            client = MethodAuditClient(base_url, client_id, client_secret, timezone=user_timezone)
            client.validate_credentials()
        except ValueError as e:
            # Re-raise ValueError from validate_credentials with context
            raise ValueError(f"Credential validation failed: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error during validation: {e}")

        return

    def stream_events(self, inputs, ew: EventWriter):
        chkpt_dir = inputs.metadata.get("checkpoint_dir")
        if not chkpt_dir:
            ew.log("WARN", "No checkpoint_dir provided; will use ephemeral checkpointing")
        for stanza_name, stanza in inputs.inputs.items():
            # stanza might be a rich stanza object (with .parameters),
            # or a dict (in CLI piped mode). Support both.
            if hasattr(stanza, "parameters"):
                params = stanza.parameters
            elif isinstance(stanza, dict):
                params = stanza
            else:
                ew.log("WARN", f"Unrecognized stanza object type for {stanza_name}: {type(stanza)}")
                continue

            base_url = params["base_url"]
            client_id = params["client_id"]
            client_secret = params["client_secret"]
            start_time = params["start_time"]
            user_timezone = params.get("timezone") or "UTC"  # Default to UTC if not specified

            # Load checkpoint (if available)
            cp = {}
            if chkpt_dir:
                cp = load_checkpoint(chkpt_dir, stanza_name)
            last_time = cp.get("last_time")
            since = last_time or start_time

            client = MethodAuditClient(base_url, client_id, client_secret, timezone=user_timezone)

            # Track event count for logging
            event_count = 0

            # Set end_time to current time - this defines the window we're querying
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Stream through events via the API client
            try:
                for ev in client.stream_events(start_time=since, end_time=current_time):
                    # Convert to Splunk event
                    ts = ev.get("timestamp")
                    ev_json = json.dumps(ev)

                    epoch_time = self._to_epoch(ts)
                    event = Event(
                        data=ev_json,
                        stanza=stanza_name,
                        sourcetype="method:audit",
                        time=str(epoch_time) if epoch_time else None,
                    )
                    ew.write_event(event)
                    event_count += 1

                # After successful run, save checkpoint with current time
                # This ensures next run starts from "now" and doesn't reprocess old events
                ew.log("INFO", f"Processed {event_count} events for {stanza_name}. Updating checkpoint to {current_time}")

                if chkpt_dir:
                    save_checkpoint(chkpt_dir, stanza_name, {
                        "last_time": current_time
                    })
            except Exception as e:
                # Log full traceback
                tb = traceback.format_exc()
                ew.log("ERROR", f"Exception in stanza {stanza_name}: {e}. Traceback: {tb}")
                # Do **not** let exception escape and crash the loop
                # Optionally you could choose to skip saving the checkpoint,
                # or save the old checkpoint (so next run retries).
                continue

if __name__ == "__main__":
    sys.exit(MethodAuditInput().run(sys.argv))

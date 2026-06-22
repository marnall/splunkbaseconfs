#!/usr/bin/env python3
"""
Nucleus Security Logs Modular Input for Splunk
Collects audit logs from Nucleus Security API
"""

import sys
import os

# Add bin directory to path for vendored packages (requests, urllib3, etc.)
bin_dir = os.path.dirname(os.path.abspath(__file__))
if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)

# Remove certifi from path to avoid cacert.pem issues - use system certs instead
sys.path = [p for p in sys.path if 'certifi' not in p.lower()]

# Error handling for imports
try:
    import json
    import time
    import hashlib
    import requests
    from datetime import datetime, timezone, timedelta
    from splunklib.modularinput import Script, Scheme, Argument, Event, EventWriter
except ImportError as e:
    # Write error to stderr so Splunk logs it
    sys.stderr.write(f"FATAL: Failed to import required modules: {e}\n")
    sys.stderr.write(f"Python version: {sys.version}\n")
    sys.stderr.write(f"sys.path: {sys.path}\n")
    sys.exit(1)

# Force requests to use system CA bundle instead of bundled certifi
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_CA_BUNDLE'] = ''


DT_FORMAT = "%Y-%m-%d %H:%M:%S"


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def parse_dt_utc(dt_str: str) -> datetime:
    # API says UTC
    return datetime.strptime(dt_str, DT_FORMAT).replace(tzinfo=timezone.utc)


def fmt_dt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(DT_FORMAT)


class NucleusLogsInput(Script):
    """Modular input for collecting Nucleus Security audit logs"""

    def get_scheme(self):
        """Define the modular input scheme for Splunk introspection"""
        scheme = Scheme("Nucleus Logs (REST)")
        scheme.description = "Poll Nucleus /nucleus/api/logs and ingest logs"
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.streaming_mode = Scheme.streaming_mode_xml

        # Required arguments
        base_url_arg = Argument("base_url")
        base_url_arg.description = "Base URL of your Nucleus Security instance (e.g., https://your-instance.nucleussec.com)"
        base_url_arg.required_on_create = True
        base_url_arg.required_on_edit = False
        scheme.add_argument(base_url_arg)

        api_key_arg = Argument("api_key")
        api_key_arg.description = "API key for authentication with Nucleus Security"
        api_key_arg.required_on_create = True
        api_key_arg.required_on_edit = False
        scheme.add_argument(api_key_arg)

        # Optional arguments
        limit_arg = Argument("limit")
        limit_arg.description = "Number of logs to fetch per API call (default: 500)"
        limit_arg.required_on_create = False
        scheme.add_argument(limit_arg)

        initial_arg = Argument("initial_since_minutes")
        initial_arg.description = "On first run, fetch logs from this many minutes ago (default: 60)"
        initial_arg.required_on_create = False
        scheme.add_argument(initial_arg)

        verify_arg = Argument("verify_ssl")
        verify_arg.description = "Verify SSL certificates (default: true)"
        verify_arg.required_on_create = False
        scheme.add_argument(verify_arg)

        sourcetype_arg = Argument("event_sourcetype")
        sourcetype_arg.description = "Sourcetype for ingested events (default: nucleus:logs)"
        sourcetype_arg.required_on_create = False
        scheme.add_argument(sourcetype_arg)

        return scheme

    def validate_input(self, definition):
        base_url = definition.parameters.get("base_url", "").strip()
        if not base_url.startswith("https://"):
            raise ValueError("base_url must start with https://")
        # Optional: do a quick auth check here (HEAD/GET with limit=1) if desired.

    def _ckpt_path(self, checkpoint_dir: str, stanza_name: str) -> str:
        safe = stanza_name.replace("/", "_").replace("\\", "_")
        return os.path.join(checkpoint_dir, f"{safe}.json")

    def _load_ckpt(self, ckpt_file: str) -> dict:
        if os.path.exists(ckpt_file):
            with open(ckpt_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_ckpt(self, ckpt_file: str, ckpt: dict):
        os.makedirs(os.path.dirname(ckpt_file), exist_ok=True)
        tmp = ckpt_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ckpt, f)
        os.replace(tmp, ckpt_file)

    def stream_events(self, inputs, ew: EventWriter):
        session = requests.Session()

        for stanza_name, params in inputs.inputs.items():
            # params is already a dict of parameter name -> value
            base_url = params["base_url"].rstrip("/")
            api_key = params["api_key"].strip()
            limit = int(params.get("limit", "500"))
            verify_ssl = str(params.get("verify_ssl", "true")).lower() != "false"
            sourcetype = params.get("event_sourcetype", "nucleus:logs")

            checkpoint_dir = inputs.metadata["checkpoint_dir"]
            ckpt_file = self._ckpt_path(checkpoint_dir, stanza_name)
            ckpt = self._load_ckpt(ckpt_file)

            last_datetime_str = ckpt.get("last_datetime")
            last_dt_hashes = set(ckpt.get("last_dt_hashes", []))

            # Bootstrap window if no checkpoint exists
            if not last_datetime_str:
                initial_since = int(params.get("initial_since_minutes", "60"))
                after_dt = datetime.now(timezone.utc) - timedelta(minutes=initial_since)
                after_str = fmt_dt(after_dt)
                last_datetime_str = fmt_dt(after_dt)  # boundary for first run
                last_dt_hashes = set()
            else:
                after_str = last_datetime_str

            headers = {
                "accept": "application/json",
                "x-apikey": api_key,
            }

            url = f"{base_url}/nucleus/api/logs"

            # Page through results using start/limit
            start = 0
            newest_dt = parse_dt_utc(last_datetime_str)
            newest_hashes = set(last_dt_hashes)

            # Collect then emit in chronological order (nice for checkpoints)
            collected = []

            while True:
                params = {
                    "start": start,
                    "limit": limit,
                    "after": after_str,
                }
                resp = session.get(url, headers=headers, params=params, verify=verify_ssl, timeout=60)

                # Basic rate-limit handling
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "5"))
                    time.sleep(min(max(retry_after, 1), 60))
                    continue

                resp.raise_for_status()
                page = resp.json()

                if not page:
                    break

                collected.extend(page)
                start += limit

            # Sort ascending by datetime so checkpoint moves forward cleanly
            def sort_key(e):
                return parse_dt_utc(e.get("datetime", "1970-01-01 00:00:00"))
            collected.sort(key=sort_key)

            for e in collected:
                dt_str = e.get("datetime")
                details = e.get("details", "")
                if not dt_str:
                    continue

                dt = parse_dt_utc(dt_str)
                h = sha1(dt_str + "\n" + details)

                # Deduplicate only at the boundary second (because after is inclusive)
                if dt == parse_dt_utc(last_datetime_str) and h in last_dt_hashes:
                    continue

                # Emit as JSON (newline-delimited)
                ew.write_event(Event(
                    data=json.dumps(e, separators=(",", ":")),
                    time=dt.timestamp(),
                    sourcetype=sourcetype,
                    index=inputs.metadata.get("index"),
                ))

                # Advance checkpoint tracker
                if dt > newest_dt:
                    newest_dt = dt
                    newest_hashes = {h}
                elif dt == newest_dt:
                    newest_hashes.add(h)

            # Persist checkpoint after successful run
            new_ckpt = {
                "last_datetime": fmt_dt(newest_dt),
                "last_dt_hashes": list(newest_hashes),
            }
            self._save_ckpt(ckpt_file, new_ckpt)


if __name__ == "__main__":
    try:
        sys.exit(NucleusLogsInput().run(sys.argv))
    except Exception as e:
        # Log any unhandled exceptions
        sys.stderr.write(f"FATAL ERROR in nucleus_logs.py: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

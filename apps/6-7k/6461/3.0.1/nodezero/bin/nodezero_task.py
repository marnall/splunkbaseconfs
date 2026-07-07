"""NodeZero modular input -- pulls pentest data from H3 GraphQL API."""

import contextlib
import csv
import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import import_declare_test  # noqa: F401 — side-effect import; must run before other imports to set up sys.path

from solnlib import conf_manager
from solnlib.log import events_ingested
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi
from splunklib.modularinput.event_writer import EventWriter

from h3queries import H3Queries
from horizon3client import H3APIClient
from horizon3client.exceptions import APIError, AuthorizationError, InternalError
from logs import set_up_logging

APP_NAME = "nodezero"
ACCOUNT_CONF = "nodezero_accounts"
ACCOUNT_REALM = f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{ACCOUNT_CONF}"
DEFAULT_API_URL = "api.horizon3ai.com"

# Pentest states that have finished data available for ingestion
FINISHED_STATES = {"done", "ended"}

# Number of rows between checkpoint updates during CSV indexing
CHECKPOINT_CHUNK_SIZE = 10_000

SOURCETYPE_MAP = {
    "hosts": "h3:nodezero:api:host_export_csv",
    "weaknesses": "h3:nodezero:api:weakness_export_csv",
    "action_logs": "h3:nodezero:api:action_logs_export_csv",
}

PARENT = os.path.sep + os.path.pardir
APP_PATH = os.path.abspath(__file__ + PARENT + os.path.sep)
h3queries = H3Queries()


class NodezeroTask(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("nodezero_task")
        scheme.description = "Input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(smi.Argument("name", title="Name", description="Name", required_on_create=True))
        scheme.add_argument(smi.Argument("description", required_on_create=False))
        scheme.add_argument(smi.Argument("account", required_on_create=True))
        scheme.add_argument(smi.Argument("n0_index", required_on_create=True))
        scheme.add_argument(smi.Argument("start_date", required_on_create=False))
        scheme.add_argument(smi.Argument("pull_hosts", required_on_create=False))
        scheme.add_argument(smi.Argument("pull_weaknesses", required_on_create=False))
        scheme.add_argument(smi.Argument("pull_action_logs", required_on_create=False))

        return scheme

    def validate_input(self, definition):
        """Validate that the configured account exists and has valid credentials."""
        account_name = definition.parameters.get("account")
        if not account_name:
            raise ValueError("Account is required")
        session_key = definition.metadata.get("session_key")
        if not session_key:
            return  # can't validate without session key
        try:
            self.get_account_config(account_name, session_key)
        except Exception as e:
            raise ValueError(f"Account '{account_name}' is not configured or has invalid credentials: {e}") from e

    def stream_events(self, inputs, ew):
        input_item = next(iter(inputs.inputs.items()))[1]
        session_key = self.service.token
        logger = set_up_logging(session_key)
        h3_api_key, api_url = self.get_account_config(input_item["account"], session_key)
        logger.debug(f"Using API URL: {api_url}")

        try:
            h3 = H3APIClient(h3_api_key, api_url=api_url)
        except Exception as e:
            logger.fatal(f"Error initializing Horizon3 API connection: {e}")
            return

        # Determine date cutoff (default: 90 days ago)
        start_date = input_item.get("start_date", "").strip()
        cutoff = start_date or (datetime.now(tz=timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
        logger.info(f"Pulling pentests scheduled after {cutoff}")

        pentests = self.pull_pentests(h3, logger, cutoff=cutoff)
        if not pentests:
            logger.warning("No pentests returned from API")
            return

        checkpoint = checkpointer.KVStoreCheckpointer("nodezero_ta_opstatus", session_key, APP_NAME)
        new_ops = self.compare_pulled_ops_to_checkpoints(pentests, checkpoint, logger)

        for op in new_ops:
            if op.get("op_name", "").lower().startswith("sample"):
                logger.debug(f"Skipping sample op: {op['op_id']}")
                continue

            if op["op_state"] not in FINISHED_STATES:
                logger.debug(f"Op: {op['op_id']} has state: {op['op_state']}. Not pulling data this time...")
                continue

            try:
                self.process_op(ew, input_item, logger, h3, checkpoint, op)
            except AuthorizationError as e:
                logger.error(f"Authorization error: {e}")
                ew.log(EventWriter.ERROR, f"Authorization error: {e}")
                break

        logger.debug(f"new_ops length: {len(new_ops)}")

    # -- Account configuration ------------------------------------------------

    def get_account_config(self, account_name, session_key):
        """Get API key and URL from the account configuration.

        Uses solnlib ConfManager which handles encrypted field decryption
        automatically via the UCC credential store.

        Returns (api_key, api_url) tuple. api_url defaults to prod US if not set.
        """
        cfm = conf_manager.ConfManager(session_key, APP_NAME, realm=ACCOUNT_REALM)
        stanza = cfm.get_conf(ACCOUNT_CONF).get(account_name)
        api_key = stanza["api_key"]
        api_url = stanza.get("api_url", DEFAULT_API_URL) or DEFAULT_API_URL
        return api_key, api_url

    # -- Data pulling ---------------------------------------------------------

    def pull_pentests(self, h3: H3APIClient, logger: logging.Logger, cutoff: str = ""):
        """Fetch completed pentests from the API, stopping at the date cutoff.

        Uses the modern pentests_page query which returns ISO date strings.
        Maps Pentest fields to the checkpoint field names used internally.
        """
        all_ops = []
        page_num = 1
        page_size = 100
        try:
            while True:
                result = h3._gql(
                    query=h3queries.pentests_page,
                    variables={
                        "page_input": {
                            "page_num": page_num,
                            "page_size": page_size,
                            "order_by": "scheduled_at",
                            "sort_order": "DESC",
                        }
                    },
                )
                pentests = result["data"]["pentests_page"]["pentests"]
                if not pentests:
                    break

                # Map Pentest API fields to internal checkpoint field names
                for p in pentests:
                    p["op_name"] = p.pop("name", "")
                    p["op_state"] = p.pop("state", "")
                    p["scheduled_timestamp"] = p.get("scheduled_at", "")
                    p["completed_timestamp"] = p.get("completed_at", "")
                    p["host_tabs_count"] = p.get("hosts_count", 0)
                    p["weakness_tabs_count"] = p.get("weaknesses_count", 0)
                    p["credentials_count"] = p.get("credentials_count", 0)
                    p["impacts_headline_count"] = p.get("impacts_count", 0)

                # Filter by date cutoff — scheduled_at is ISO string, compare directly
                if cutoff:
                    filtered = []
                    past_cutoff = 0
                    for op in pentests:
                        ts = str(op.get("scheduled_at", "") or "")[:10]
                        if ts >= cutoff:
                            filtered.append(op)
                        else:
                            past_cutoff += 1
                    all_ops.extend(filtered)
                    logger.debug(f"Page {page_num}: {len(filtered)} pentests after cutoff, {past_cutoff} before")
                    if past_cutoff > 0 and len(filtered) == 0:
                        logger.debug(f"All pentests on page {page_num} are before {cutoff}, stopping")
                        break
                else:
                    all_ops.extend(pentests)

                if len(pentests) < page_size:
                    break
                page_num += 1
        except (InternalError, APIError) as e:
            logger.critical(f"CRITICAL ERROR: {e}. Pentests not pulled")
            return None
        return all_ops

    def _get_presigned_url(self, h3, query, variables, data_key, op_id, logger):
        """Fetch a presigned download URL from the API."""
        try:
            result = h3._gql(query, variables)
            url = result["data"][data_key]
            if not url:
                logger.warning(f"No download URL returned for {op_id} ({data_key})")
                return None
            return url
        except (InternalError, APIError) as e:
            logger.error(f"Error getting {data_key} for {op_id}: {e}")
            return None

    def _download_to_tempfile(self, h3, url, op_id, data_type, logger):
        """Download a CSV from a presigned URL to a local temp file.

        Returns the temp file path on success, or None on failure.
        The caller is responsible for cleaning up the temp file.
        """
        path = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", suffix=f".{data_type}.csv", delete=False) as fd:
                path = fd.name
                resp = h3.download_stream(url)
                try:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            fd.write(chunk)
                finally:
                    resp.close()

            if os.path.getsize(path) == 0:
                logger.warning(f"Downloaded empty {data_type} CSV for {op_id}")
                os.unlink(path)
                return None

            return path
        except Exception as e:
            logger.error(f"Error downloading {data_type} CSV for {op_id}: {e}")
            if path is not None:
                with contextlib.suppress(OSError):
                    os.unlink(path)
            return None

    def _stream_csv_events(
        self,
        csv_path,
        ew,
        input_item,
        op,
        data_type,
        logger,
        checkpoint,
        checkpoint_field,
        skip_rows=0,
    ):
        """Index a local CSV file into Splunk events with chunked checkpointing.

        Uses csv.DictReader to correctly handle multi-line quoted fields
        (e.g., Description containing embedded newlines).

        Returns total rows (skip_rows + newly written), or None if
        the file can't be read at all.
        """
        op_id = op["op_id"]
        count = 0
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    return 0

                # Skip rows already indexed in a previous partial run
                for _ in range(skip_rows):
                    try:
                        next(reader)
                    except StopIteration:
                        break

                for row in reader:
                    event = smi.Event(
                        data=json.dumps(row),
                        host=op_id,
                        index=input_item["n0_index"],
                        source="nodezero_modinput",
                        sourcetype=SOURCETYPE_MAP[data_type],
                    )
                    ew.write_event(event)
                    count += 1

                    total = skip_rows + count
                    if count % CHECKPOINT_CHUNK_SIZE == 0:
                        op[checkpoint_field] = total
                        checkpoint.update(op_id, op)
                        logger.debug(f"Checkpoint: {total} {data_type} rows for {op_id}")
        except Exception as e:
            logger.error(f"Error parsing {data_type} CSV for {op_id} after {count} rows: {e}")
            if count == 0:
                return None

        total = skip_rows + count
        logger.debug(f"Streamed {count} {data_type} events for {op_id} (total={total})")
        return total

    def _pull_data_type(
        self,
        h3,
        ew,
        input_item,
        logger,
        checkpoint,
        op,
        data_type,
        query,
        variables,
        data_key,
        checkpoint_field,
    ):
        """Download, index, and checkpoint a single data type for an op.

        Handles the full lifecycle: skip-if-done, presigned URL fetch,
        download to temp file, resume-aware streaming, final checkpoint,
        and temp file cleanup.
        """
        op_id = op["op_id"]
        pulled = op.get(checkpoint_field)

        # Already complete — nothing to do
        if pulled in (1, "done"):
            return

        url = self._get_presigned_url(h3, query, variables, data_key, op_id, logger)
        if not url:
            return

        csv_path = self._download_to_tempfile(h3, url, op_id, data_type, logger)
        if not csv_path:
            return

        try:
            skip_rows = pulled if isinstance(pulled, int) and pulled > 1 else 0
            total = self._stream_csv_events(
                csv_path, ew, input_item, op, data_type, logger, checkpoint, checkpoint_field, skip_rows=skip_rows
            )
            if total is not None:
                op[checkpoint_field] = "done"
                checkpoint.update(op_id, op)
                if total > 0:
                    with contextlib.suppress(Exception):
                        events_ingested(
                            logger=logger,
                            modular_input_name=f"nodezero_task://{input_item.get('name', 'unknown')}",
                            sourcetype=SOURCETYPE_MAP[data_type],
                            n_events=total,
                            index=input_item["n0_index"],
                            account=input_item.get("account", ""),
                        )
        finally:
            with contextlib.suppress(OSError):
                os.unlink(csv_path)

    # -- Checkpoint and indexing ----------------------------------------------

    def compare_pulled_ops_to_checkpoints(
        self,
        op_statuses,
        checkpoint: checkpointer.KVStoreCheckpointer,
        logger: logging.Logger,
    ):
        new_ops = []

        for h3_op in op_statuses:
            checkpoint_data = checkpoint.get(h3_op["op_id"])

            if checkpoint_data is None:
                logger.debug(f"New op! {h3_op['op_id']}")
                for flag in ["pulled_weaknesses", "pulled_hosts", "pulled_action_logs"]:
                    h3_op[flag] = 0
                checkpoint.update(h3_op["op_id"], h3_op)
                new_ops.append(checkpoint.get(h3_op["op_id"]))
                continue

            if checkpoint_data["op_state"] != h3_op["op_state"]:
                logger.info(
                    f"Updating op_id {h3_op['op_id']} from {checkpoint_data['op_state']} to {h3_op['op_state']}",
                )
                for flag in ["pulled_weaknesses", "pulled_hosts", "pulled_action_logs"]:
                    h3_op[flag] = checkpoint_data.get(flag, 0)
                checkpoint.update(h3_op["op_id"], h3_op)
                new_ops.append(checkpoint.get(h3_op["op_id"]))
                continue

            complete = (1, "done")
            pull_flags = ["pulled_weaknesses", "pulled_hosts", "pulled_action_logs"]
            if any(checkpoint_data.get(f) not in complete for f in pull_flags):
                new_ops.append(checkpoint.get(h3_op["op_id"]))

        return new_ops

    def process_op(self, ew, input_item, logger, h3, checkpoint, op):
        op_id = op["op_id"]

        # UCC checkbox fields come as string "1"/"0" — treat missing/empty as enabled (default)
        def _enabled(field):
            val = input_item.get(field)
            return val is None or str(val) not in ("0", "false", "False")

        if _enabled("pull_hosts"):
            self._pull_data_type(
                h3,
                ew,
                input_item,
                logger,
                checkpoint,
                op,
                "hosts",
                h3queries.hosts_csv_url,
                {"op_id": op_id},
                "hosts_csv_url",
                "pulled_hosts",
            )
        else:
            logger.debug(f"Skipping hosts for {op_id} (disabled in input config)")

        if _enabled("pull_weaknesses"):
            self._pull_data_type(
                h3,
                ew,
                input_item,
                logger,
                checkpoint,
                op,
                "weaknesses",
                h3queries.weaknesses_csv_url,
                {"op_id": op_id},
                "weaknesses_csv_url",
                "pulled_weaknesses",
            )
        else:
            logger.debug(f"Skipping weaknesses for {op_id} (disabled in input config)")

        if _enabled("pull_action_logs"):
            self._pull_data_type(
                h3,
                ew,
                input_item,
                logger,
                checkpoint,
                op,
                "action_logs",
                h3queries.action_logs_csv_url,
                {"input": {"op_id": op_id}},
                "action_logs_csv_presigned_url",
                "pulled_action_logs",
            )
        else:
            logger.debug(f"Skipping action_logs for {op_id} (disabled in input config)")


if __name__ == "__main__":
    exit_code = NodezeroTask().run(sys.argv)
    sys.exit(exit_code)

"""
fleak_mapping.py - Custom search command for OCSF mapping via Zephflow API.

Usage: | fleakmapping rule_name=<name>

Fetches the DAG definition from the KV Store by rule_name, creates (or reuses)
a Zephflow workflow, and maps Splunk events to OCSF format in batches.
If Zephflow is unreachable or returns an error, raw events are passed through
untouched so the search pipeline does not crash.
"""

import sys
import json
import os
import logging
import urllib.request
import urllib.error

# Use the splunklib vendored with this app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import splunklib.searchcommands as sc
import splunklib.client as client

logger = logging.getLogger(__name__)

BATCH_SIZE = int(os.environ.get("FLEAK_BATCH_SIZE", "100"))

# In-memory cache: rule_name -> workflow_id
# Avoids recreating the same workflow on every search chunk.
_workflow_cache = {}

# Config cache (populated once per search process)
_config = None


def _http_post(url, payload, api_token="", timeout=30):
    """Send a JSON POST request and return the parsed response."""
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _create_workflow(dag_json, base_url, api_token=""):
    """Register a DAG with Zephflow and return the assigned workflow ID."""
    url = f"{base_url}/api/v1/workflows"
    result = _http_post(url, dag_json, api_token, timeout=10)
    return result["id"]


def _build_runtime_dag(feel_rule, parser_config=None):
    """Build the executable DAG expected by Zephflow.

    If parser_config is provided, prepend parser nodes so the raw log
    is parsed into structured fields before the FEEL eval runs.
    """
    dag = []

    if parser_config:
        configs = json.loads(parser_config) if isinstance(parser_config, str) else parser_config
        for i, pc in enumerate(configs):
            node_id = f"parser_{i}"
            next_id = f"parser_{i + 1}" if i < len(configs) - 1 else "eval"
            dag.append({
                "id": node_id,
                "commandName": "parser",
                "config": pc,
                "outputs": [next_id],
            })

    dag.append({
        "id": "eval",
        "commandName": "eval",
        "config": {"expression": feel_rule},
        "outputs": [],
    })

    return {"dag": dag}


def _run_batch(workflow_id, events, base_url, api_token=""):
    """
    Send a list of events to Zephflow for mapping.
    Returns the list of OCSF-mapped output events.
    """
    url = f"{base_url}/api/v1/execution/run/{workflow_id}/batch"
    result = _http_post(url, events, api_token, timeout=30)
    output_events = result.get("output", {}).get("outputEvents", {})
    if not output_events:
        return []
    # outputEvents is keyed by the terminal node id — return the first value.
    return list(output_events.values())[0]


def _flatten(obj, prefix=""):
    """
    Recursively flatten a nested dict into dot-notation keys.
    Lists are JSON-encoded so Splunk can store them as a single field value.
    """
    items = {}
    for k, v in obj.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.update(_flatten(v, key))
        elif isinstance(v, list):
            items[key] = json.dumps(v, ensure_ascii=False)
        else:
            items[key] = v
    return items


@sc.Configuration(distributed=False)
class FleakMappingCommand(sc.StreamingCommand):
    """Map Splunk events to OCSF format using the Zephflow engine."""

    rule_name = sc.Option(name="rule_name", require=True)

    def stream(self, records):
        cfg = self._get_config()
        if not cfg["zephflow_base_url"]:
            logger.error("fleak_mapping: zephflow_base_url not configured in fleak.conf")
            yield from records
            return

        rule = self._lookup_rule(self.rule_name)
        if rule is None:
            logger.error("fleak_mapping: rule '%s' not found in KV Store", self.rule_name)
            yield from records
            return

        dag_json = self._rule_to_dag(rule)
        if dag_json is None:
            logger.error("fleak_mapping: rule '%s' has no executable definition", self.rule_name)
            yield from records
            return

        try:
            workflow_id = self._get_or_create_workflow(self.rule_name, dag_json, cfg)
        except Exception as exc:
            logger.warning(
                "fleak_mapping: failed to create Zephflow workflow (%s), passing through raw events.", exc
            )
            yield from records
            return

        batch, originals = [], []
        for record in records:
            event = dict(record)
            # Splunk uses _raw, Zephflow parser expects __raw__
            if "_raw" in event and "__raw__" not in event:
                event["__raw__"] = event["_raw"]
            batch.append(event)
            originals.append(record)
            if len(batch) >= BATCH_SIZE:
                yield from self._process_batch(workflow_id, batch, originals, cfg)
                batch, originals = [], []

        if batch:
            yield from self._process_batch(workflow_id, batch, originals, cfg)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_config(self):
        """URL from fleak.conf; token from storage/passwords. Env vars fall back for dev."""
        global _config
        if _config is not None:
            return _config
        url = ""
        token = ""
        try:
            svc = client.connect(
                token=self.service.token,
                host="localhost",
                port=8089,
                scheme="https",
                app="fleak_ocsf_mapper",
                owner="nobody",
            )
            try:
                stanza = svc.confs["fleak"]["general"]
                url = dict(stanza.content).get("zephflow_base_url") or ""
            except Exception as exc:
                logger.warning("fleak_mapping: failed to read fleak.conf: %s", exc)
            try:
                for p in svc.storage_passwords:
                    if p.realm == "fleak_ocsf_mapper" and p.username == "zephflow_api_token":
                        token = p.clear_password
                        break
            except Exception as exc:
                logger.warning("fleak_mapping: failed to read storage/passwords: %s", exc)
        except Exception as exc:
            logger.warning("fleak_mapping: unable to connect to splunkd: %s", exc)
        _config = {
            "zephflow_base_url": url or os.environ.get("ZEPHFLOW_BASE_URL", ""),
            "zephflow_api_token": token or os.environ.get("ZEPHFLOW_API_TOKEN", ""),
        }
        return _config

    def _lookup_rule(self, rule_name):
        """Return the matching KV Store rule row, or None if not found."""
        try:
            svc = client.connect(
                token=self.service.token,
                host="localhost",
                port=8089,
                scheme="https",
                app="fleak_ocsf_mapper",
                owner="nobody",
            )
            rows = svc.kvstore["ocsf_mapping_rules"].data.query(
                query=json.dumps({"rule_name": rule_name, "status": "Active"}),
                sort="updated_at:-1",
                limit=1,
            )
            if rows:
                return rows[0]
        except Exception as exc:
            logger.error("fleak_mapping: KV Store lookup failed: %s", exc)
        return None

    def _rule_to_dag(self, rule):
        """Build the runtime DAG from the stored rule representation."""
        feel_rule = rule.get("feel_rule")
        if feel_rule:
            return _build_runtime_dag(feel_rule, rule.get("parser_config"))

        return None

    def _get_or_create_workflow(self, rule_name, dag_json, cfg):
        """Return a cached workflow ID, creating the workflow if necessary."""
        if rule_name not in _workflow_cache:
            _workflow_cache[rule_name] = _create_workflow(
                dag_json, cfg["zephflow_base_url"], cfg["zephflow_api_token"]
            )
            logger.info("fleak_mapping: created workflow %s for rule '%s'",
                        _workflow_cache[rule_name], rule_name)
        return _workflow_cache[rule_name]

    def _process_batch(self, workflow_id, batch, originals, cfg):
        """
        Map one batch of events through Zephflow.
        Falls back to yielding the original records if anything goes wrong.
        """
        try:
            ocsf_events = _run_batch(
                workflow_id, batch, cfg["zephflow_base_url"], cfg["zephflow_api_token"]
            )
            if ocsf_events and len(ocsf_events) == len(originals):
                # Pair mapped output with originals so Splunk's Events tab
                # still renders: it needs _time, and _raw lets users see the
                # source log alongside the OCSF fields.
                for event, original in zip(ocsf_events, originals):
                    out = _flatten(event)
                    if "_time" in original:
                        out["_time"] = original["_time"]
                    if "_raw" in original:
                        out["_raw"] = original["_raw"]
                    yield out
                return
            if ocsf_events:
                logger.warning(
                    "fleak_mapping: Zephflow returned %d events for %d inputs; passing through raw events to avoid silent loss.",
                    len(ocsf_events), len(originals),
                )
            else:
                logger.warning("fleak_mapping: Zephflow returned empty output, passing through raw events.")
        except urllib.error.URLError as exc:
            logger.warning("fleak_mapping: Zephflow unreachable (%s), passing through raw events.", exc)
        except Exception as exc:
            logger.warning("fleak_mapping: batch execution failed (%s), passing through raw events.", exc)

        yield from originals


if __name__ == "__main__":
    sc.dispatch(FleakMappingCommand, sys.argv, sys.stdin, sys.stdout, __name__)

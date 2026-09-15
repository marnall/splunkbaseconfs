"""
OCI Function: Service Connector Hub -> Splunk HEC push
--------------------------------------------------------
Takes a batch of records from an OCI Service Connector Hub task
(source is Logging or Streaming, target is Functions), cleans each one
up, and POSTs it to a Splunk HTTP Event Collector endpoint.

This is the push-side replacement for the archived pull-based Splunk
Addon for OCI (app 5222) and the archived Splunk Cloud Addon for OCI
(app 7021) - neither works on Splunk 9.3+/10 since they shipped an OCI
SDK binary compiled for Python 3.7.

Env vars (set these in func.yaml or with `fn config`):
  SPLUNK_HEC_URL     e.g. https://splunk.example.com:8088/services/collector/event
  SPLUNK_HEC_TOKEN   HEC token GUID
  SPLUNK_INDEX       target index (optional - the HEC token can default this too)
  SPLUNK_VERIFY_SSL  "true" | "false"  (default: true)
  SPLUNK_HOST        value to stamp in the "host" field (optional)
  HEC_BATCH_SIZE     max events per HEC POST (default: 50)
"""

import io
import os
import json
import gzip
import base64
import logging
import requests
from fdk import response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SPLUNK_HEC_URL = os.getenv("SPLUNK_HEC_URL")
SPLUNK_HEC_TOKEN = os.getenv("SPLUNK_HEC_TOKEN")
SPLUNK_INDEX = os.getenv("SPLUNK_INDEX")
SPLUNK_HOST = os.getenv("SPLUNK_HOST", "oci-service-connector-hub")
# TLS verification is on by default and stays on unless someone
# explicitly sets SPLUNK_VERIFY_SSL=false - useful for a lab HEC
# endpoint with a self-signed cert, but shouldn't be turned off in
# production.
VERIFY_SSL = os.getenv("SPLUNK_VERIFY_SSL", "true").lower() != "false"
BATCH_SIZE = int(os.getenv("HEC_BATCH_SIZE", "50"))

# Maps OCI's "source"/"type" fields to Splunk sourcetypes. Same
# sourcetypes the old TA used, so existing CIM-mapped dashboards and
# searches (like the Splunk App for OCI, app 5289) keep working.
SOURCETYPE_MAP = {
    "com.oraclecloud.vcn.flowlog": "oci:flowlogs",
    # "flowlog" not "flowlogs" here on purpose - see the same map in
    # bin/oci_stream.py for why (substring matching picks up both)
    "com.oraclecloud.loadbalancer": "oci:loadbalancer",
    "com.oraclecloud.objectstorage": "oci:objectstorage",
    "com.oraclecloud.workloadprotection.cloudguard": "oci:cloudguard:problem",
    "com.oraclecloud.cloudguard.problem": "oci:cloudguard:problem",
    # bin/oci_stream.py's copy of this map has the full story on each
    # of these, including why Cloud Guard ends up with two different
    # real patterns pointing at the same sourcetype.
}
DEFAULT_SOURCETYPE = "oci:log"


def normalize_payload(data):
    """Whatever shape Service Connector Hub hands us, get it decoded,
    decompressed if needed, and parsed into a list of record dicts."""
    if isinstance(data, io.BytesIO):
        data = data.read()

    if isinstance(data, (bytes, bytearray)) and data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)

    if isinstance(data, (bytes, bytearray)):
        data = data.decode("utf-8")

    if isinstance(data, str):
        data = json.loads(data)

    records = data if isinstance(data, list) else [data]
    return records


def guess_sourcetype(record):
    """Checks oracle.loggroupid first - we found a real production
    Audit log record where the CloudEvents "type" field
    ("com.oraclecloud.logging.GetGeneratedUnifiedAgentConfiguration")
    had no "audit" in it at all, but oracle.loggroupid was OCI's own
    literal "_Audit". Kept in sync with the same function in
    bin/oci_stream.py - check that file's comments for the full story.
    """
    log_group_id = (record.get("oracle") or {}).get("loggroupid", "")
    if log_group_id == "_Audit":
        return "oci:audit"

    src = (
        record.get("type")
        or record.get("eventType")
        or record.get("source", "")
    )
    for key, sourcetype in SOURCETYPE_MAP.items():
        if key in str(src):
            return sourcetype
    return DEFAULT_SOURCETYPE


def extract_host(record):
    """Tries to pull a meaningful 'host' value out of the event. See
    the same function in bin/oci_stream.py for the full explanation -
    kept in sync by hand across both files."""
    data = record.get("data") or {}

    identity = data.get("identity") or {}
    tenant_id = identity.get("tenantId")
    if tenant_id:
        return str(tenant_id).strip() or None

    additional_details = data.get("additionalDetails") or {}
    tenant_id = additional_details.get("tenantId")
    if tenant_id:
        return str(tenant_id).strip() or None

    tenant_id = record.get("oracle.tenantid")
    if tenant_id:
        return str(tenant_id).strip() or None

    return None


def sanitize_payload_for_splunk(record):
    """Renames any JSON key that collides with one of Splunk's own
    reserved field names. We ran into this for real: OCI Audit records
    have a top-level "source" key (usually empty) that, combined with
    KV_MODE=json in props.conf, shadows Splunk's actual source metadata
    at search time. Returns a new dict rather than touching the one
    passed in - see bin/oci_stream.py's copy for the full writeup."""
    if "source" not in record:
        return record
    fixed = dict(record)
    fixed["oci_source"] = fixed.pop("source")
    return fixed


def build_hec_event(record):
    """Wraps one OCI record in a Splunk HEC event envelope."""
    sourcetype = guess_sourcetype(record)
    host = extract_host(record) or SPLUNK_HOST
    safe_record = sanitize_payload_for_splunk(record)

    event = {
        "event": safe_record,
        "sourcetype": sourcetype,
        "source": "oci:service_connector_hub",
        "host": host,
    }
    if SPLUNK_INDEX:
        event["index"] = SPLUNK_INDEX

    # Use OCI's own timestamp when it's there instead of just letting
    # Splunk stamp arrival time.
    ts = record.get("time") or record.get("eventTime")
    if ts:
        try:
            import dateutil.parser  # lightweight, add to requirements.txt
            event["time"] = dateutil.parser.isoparse(ts).timestamp()
        except Exception:
            pass  # if that fails, Splunk's default (now) is fine

    return event


def send_to_hec(events):
    if not events:
        return

    headers = {
        "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
        "Content-Type": "application/json",
    }

    # HEC's fine with multiple JSON event objects just concatenated
    # together in one POST body.
    for i in range(0, len(events), BATCH_SIZE):
        chunk = events[i : i + BATCH_SIZE]
        body = "".join(json.dumps(e) for e in chunk)

        resp = requests.post(
            SPLUNK_HEC_URL,
            headers=headers,
            data=body,
            verify=VERIFY_SSL,
            timeout=15,
        )
        if resp.status_code != 200:
            logger.error(
                "HEC POST failed status=%s body=%s", resp.status_code, resp.text
            )
            resp.raise_for_status()
        else:
            logger.info("Sent %d events to Splunk HEC", len(chunk))


def handler(ctx, data: io.BytesIO = None):
    if not SPLUNK_HEC_URL or not SPLUNK_HEC_TOKEN:
        logger.error("SPLUNK_HEC_URL / SPLUNK_HEC_TOKEN not configured")
        return response.Response(
            ctx, status_code=500, response_data="Missing HEC configuration"
        )

    try:
        records = normalize_payload(data)
        events = [build_hec_event(r) for r in records]
        send_to_hec(events)
        return response.Response(
            ctx,
            status_code=200,
            response_data=json.dumps({"forwarded": len(events)}),
            headers={"Content-Type": "application/json"},
        )
    except Exception as e:
        logger.exception("Failed to process/forward OCI records")
        return response.Response(
            ctx, status_code=500, response_data=f"Error: {e}"
        )

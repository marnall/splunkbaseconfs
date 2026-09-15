#!/usr/bin/env python3
"""
bin/oci_stream.py

A Splunk modular input that pulls messages off an OCI Stream using
API-key auth - Tenancy OCID, User OCID, Fingerprint, private key .pem,
optional passphrase, region. Same fields the archived "Splunk Addon
for OCI" (Splunkbase app 5222) used to ask for.

We didn't just reuse 5222 because it shipped pre-compiled Python 3.7
binaries for its crypto dependencies, and those stopped loading once
Splunk moved its embedded Python past 9.2. Nothing here is pre-compiled
or bundled - the `oci` SDK gets pip-installed at deploy time against
whatever Python this Splunk instance is actually running, so it
shouldn't break the same way when Splunk upgrades again. See README.md
and bin/requirements.txt for the install step.

The modular input protocol is implemented by hand here (stdlib only)
rather than pulling in splunklib as a dependency:
  --scheme               -> print <scheme> XML, exit
  --validate-arguments   -> read stanza config from stdin XML, validate
  (no args)              -> read config from stdin XML, run forever,
                             writing events as XML to stdout
"""

import io
import os
import sys
import json
import time
import base64
import gzip
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

APP_NAME = "TA-Oracle-OCI"
CHECKPOINT_DIR_ENV = "checkpoint_dir"

# If bin/lib exists (that's where requirements.txt gets pip-installed
# to), add it to the path so imports work. Kept separate from Splunk's
# own site-packages on purpose - we don't want this app touching
# anything shared.
_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
if os.path.isdir(_LIB_DIR) and _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

# This map has a twin copy in oci-function/func.py. The two scripts run
# in completely separate places (one inside Splunk, one inside an OCI
# Function) so there's no way to share a Python import between them -
# if you change something here, go change it there too or push and
# pull will start producing different sourcetypes for the same event.
#
# We checked these against Oracle's own documentation
# (https://docs.oracle.com/en-us/iaas/log-analytics/doc/oci-parser-details.html)
# rather than guessing. Matching happens on the "type" field, not
# "source" - every real OCI Logging payload we've seen puts a resource
# name or OCID in "source" (a subnet OCID for flow logs, a load
# balancer's name, etc.), which is different per environment and never
# tells you what service it came from. "type" is the CloudEvents field
# that reliably follows com.oraclecloud.<service>.<action>.
SOURCETYPE_MAP = {
    "com.oraclecloud.vcn.flowlog": "oci:flowlogs",
    # Real confirmed type: com.oraclecloud.vcn.flowlogs.DataEvent
    # The key here is "flowlog" (no trailing s) on purpose - matching
    # is substring-based (see guess_sourcetype_from_record below), so
    # this shorter key still catches the confirmed DataEvent pattern
    # above, plus also catches a singular "com.oraclecloud.vcn.flowlog"
    # variant we came across in a YouTube tutorial. We're not treating
    # that video as a reliable source though - its sample JSON disagrees
    # with Oracle's own VCN Flow Logs docs on several fields (bytes vs
    # bytesOut, startMs/endMs vs startTime/endTime, no flowid/version at
    # all). Matching it anyway doesn't cost us anything, but if you ever
    # see this pattern in a real production payload, update this note.
    "com.oraclecloud.loadbalancer": "oci:loadbalancer",
    # Confirmed real: com.oraclecloud.loadbalancer.access / .error
    # (this also catches .waf and .waa, which is fine for now since
    # there's no separate sourcetype for those yet)
    "com.oraclecloud.objectstorage": "oci:objectstorage",
    # Confirmed real: com.oraclecloud.objectstorage.getobject / .getbucket
    "com.oraclecloud.workloadprotection.cloudguard": "oci:cloudguard:problem",
    # Confirmed real: com.oraclecloud.workloadprotection.cloudguarddatasource.wlp_scheduled_query_logs
    #                 com.oraclecloud.workloadprotection.cloudguardtarget.recipelog
    # A production check earlier only turned up this pattern - Cloud
    # Guard's own scan/query activity, not actual Problem events. That
    # doesn't mean Problem events don't exist though, just that this
    # particular check happened not to catch one. There's a second, real
    # pattern for that:
    "com.oraclecloud.cloudguard.problem": "oci:cloudguard:problem",
    # Confirmed via a real example payload on Oracle's own Cloud
    # Infrastructure blog, not just API docs:
    # com.oraclecloud.cloudguard.problemremediated
    # com.oraclecloud.cloudguard.problemdetected (this one from a
    # third-party SIEM vendor's default parser for the same event)
    # https://blogs.oracle.com/cloud-infrastructure/integrating-cloud-guard-logging-analytics-part-1
    # Our read is these are two genuinely different Cloud Guard event
    # categories - scan/agent activity vs. actual Problem lifecycle
    # events - that can both show up in the same tenancy. Not a
    # contradiction to pick one side of, so both map to the same
    # sourcetype here since either way it's Cloud Guard doing the
    # finding. Worth checking which pattern(s) actually show up in a
    # given client's real data before assuming full coverage.
}
DEFAULT_SOURCETYPE = "oci:log"


def guess_sourcetype_from_record(record):
    """This is the actual detection logic, working on an already-parsed
    dict. It checks oracle.loggroupid first - we found a real Audit log
    record in production where the CloudEvents "type" field was
    "com.oraclecloud.logging.GetGeneratedUnifiedAgentConfiguration" (no
    "audit" in it anywhere), but oracle.loggroupid was OCI's own literal
    "_Audit" value. So that's the more reliable signal for Audit
    specifically.

    After that it falls back to "type" (what VCN Flow Logs call their
    envelope field) or "eventType" (what Audit and most other Logging
    envelopes call it - yes, these are genuinely different field names
    for the same concept across OCI services, confirmed against
    Oracle's own docs for each one). Deliberately not "source" (see the
    comment above SOURCETYPE_MAP for why) and not "cloudEventsVersion"
    either - that one's just a fixed string like "0.1" on every
    CloudEvents message regardless of type, and an earlier version of
    this code accidentally checked that instead of eventType, which
    meant every eventType-style record silently fell through to
    DEFAULT_SOURCETYPE. If none of that matches, DEFAULT_SOURCETYPE."""
    if not isinstance(record, dict):
        return DEFAULT_SOURCETYPE

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


def guess_sourcetype(payload_str):
    """Same as guess_sourcetype_from_record() but takes a raw string.
    Kept around for anything still calling it that way. If you already
    have a parsed dict, just call guess_sourcetype_from_record()
    directly instead - no reason to parse the same JSON twice."""
    try:
        record = json.loads(payload_str)
    except (ValueError, TypeError):
        return DEFAULT_SOURCETYPE
    return guess_sourcetype_from_record(record)


def extract_host(record):
    """Tries to pull a meaningful 'host' value out of the event itself,
    so Splunk's host field shows which OCI tenancy something came from
    instead of just defaulting to this collector's own hostname for
    every single event.

    OCI doesn't use one consistent place to put tenancy info across log
    types, annoyingly, so this checks three different spots, each one
    checked against a real Oracle source:

    1. data.identity.tenantId - this is where Audit puts it. Confirmed
       against Oracle's own Audit event reference:
       https://docs.oracle.com/en-us/iaas/Content/Audit/Reference/logeventreference.htm
    2. data.additionalDetails.tenantId - Cloud Guard Problem events put
       it here instead, since they don't even have an "identity" object.
       Confirmed via a real example payload on Oracle's Cloud
       Infrastructure blog:
       https://blogs.oracle.com/cloud-infrastructure/integrating-cloud-guard-logging-analytics-part-1
    3. oracle.tenantid - no "data" nesting this time, and lowercase.
       This is VCN Flow Logs' own convention, a third different shape.
       Confirmed against Oracle's official VCN Flow Logs reference:
       https://docs.oracle.com/en-us/iaas/Content/Logging/Reference/details_for_vcn_flow_logs.htm

    If none of the three show up, this returns None and Splunk just
    uses its normal default rather than us forcing something in. Feel
    free to add more of these as real samples turn up for other log
    types - same approach as SOURCETYPE_MAP, only add what's confirmed.

    One thing worth knowing: tenantId is one fixed value for the whole
    tenancy, so every event from a given tenancy ends up with the same
    host. That's grouping by tenancy, not by individual caller or IP.
    If you actually need per-caller detail for Audit records
    specifically, data.identity.ipAddress is the field for that
    (confirmed in the same Audit reference above).
    """
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
    """Renames any JSON key that would collide with one of Splunk's own
    reserved field names, before the event goes out. We ran into a real
    case of this: OCI Audit records have a literal top-level "source"
    key (usually just an empty string), and with KV_MODE=json turned on
    in props.conf, that key shadows Splunk's actual source metadata
    field at search time. Every Audit event's source column just went
    blank because of it. Returns a new dict rather than modifying the
    one passed in."""
    if "source" not in record:
        return record
    fixed = dict(record)
    fixed["oci_source"] = fixed.pop("source")
    return fixed


def decode_message_value(raw_value):
    """OCI Streaming sends message content base64-encoded - what the SDK
    hands back as msg.value is still the raw base64, not the actual
    payload. This undoes that before we try to treat it as JSON or write
    it out to Splunk.

    Some messages turn out to be gzip-compressed on top of the base64,
    too - we saw this happen in practice with larger/batched payloads,
    where decoding from base64 lands you on gzip magic bytes instead of
    plain JSON text. Trying to decode that straight to utf-8 just
    throws, and without handling it the code used to silently give back
    the raw undecoded base64. This mirrors the same gzip check already
    in oci-function/func.py's normalize_payload() - both encoding layers
    apply the same way whether the event came through push or pull, so
    both scripts need this.

    If it's still not valid base64/utf-8 after all that, this just
    returns the value untouched - keeps things working if a future SDK
    version starts auto-decoding on its own, or if something ever
    publishes plain content without the base64 wrapper."""
    if raw_value is None:
        return ""
    if isinstance(raw_value, (bytes, bytearray)):
        raw_value = raw_value.decode("utf-8", errors="replace")

    try:
        decoded_bytes = base64.b64decode(raw_value)
    except Exception:
        return raw_value  # wasn't valid base64 at all

    if decoded_bytes[:2] == b"\x1f\x8b":
        try:
            decoded_bytes = gzip.decompress(decoded_bytes)
        except Exception:
            pass  # not actually valid gzip despite the magic bytes; fall through

    try:
        return decoded_bytes.decode("utf-8")
    except Exception:
        return raw_value


# --------------------------------------------------------------------------
# The scheme - this is what Splunk calls with --scheme to find out what
# fields this input needs
# --------------------------------------------------------------------------

def do_scheme():
    print(
        """<scheme>
  <title>OCI Streaming (API Key Pull)</title>
  <description>Pulls messages from an OCI Stream using API-key (Tenancy/User OCID + private key) authentication.</description>
  <use_external_validation>true</use_external_validation>
  <streaming_mode>xml</streaming_mode>
  <use_single_instance>false</use_single_instance>
  <endpoint>
    <args>
      <arg name="tenancy_ocid"><title>Tenancy OCID</title><data_type>string</data_type><required_on_create>true</required_on_create></arg>
      <arg name="user_ocid"><title>User OCID</title><data_type>string</data_type><required_on_create>true</required_on_create></arg>
      <arg name="fingerprint"><title>Fingerprint</title><data_type>string</data_type><required_on_create>true</required_on_create></arg>
      <arg name="key_file"><title>Private Key File Path</title><data_type>string</data_type><required_on_create>true</required_on_create></arg>
      <arg name="pass_phrase"><title>Private Key Passphrase</title><data_type>string</data_type><required_on_create>false</required_on_create></arg>
      <arg name="region"><title>Region</title><data_type>string</data_type><required_on_create>true</required_on_create></arg>
      <arg name="stream_ocid"><title>Stream OCID</title><data_type>string</data_type><required_on_create>true</required_on_create></arg>
      <arg name="stream_endpoint"><title>Stream Endpoint</title><data_type>string</data_type><required_on_create>true</required_on_create></arg>
      <arg name="sourcetype_override"><title>Sourcetype Override (optional - leave blank to auto-detect per event, same as the HEC/push method)</title><data_type>string</data_type><required_on_create>false</required_on_create></arg>
      <arg name="worker_processes"><title>Worker Processes</title><data_type>number</data_type><required_on_create>false</required_on_create></arg>
      <arg name="message_limit"><title>Message Limit</title><data_type>number</data_type><required_on_create>false</required_on_create></arg>
      <arg name="retry_interval"><title>Retry Interval (sec)</title><data_type>number</data_type><required_on_create>false</required_on_create></arg>
      <arg name="poll_interval"><title>Poll Interval (sec)</title><data_type>number</data_type><required_on_create>false</required_on_create></arg>
    </args>
  </endpoint>
</scheme>"""
    )


# --------------------------------------------------------------------------
# Parsing the XML Splunk feeds us on stdin - used both for
# --validate-arguments and for the actual run
# --------------------------------------------------------------------------

def read_config(stream):
    """Turns the XML Splunk sends on stdin into a dict of stanza name ->
    params."""
    root = ET.parse(stream).getroot()
    server_host = root.findtext("server_host")
    server_uri = root.findtext("server_uri")
    session_key = root.findtext("session_key")
    checkpoint_dir = root.findtext("checkpoint_dir")

    stanzas = []
    for stanza_el in root.findall(".//stanza") or root.findall(".//configuration/stanza"):
        name = stanza_el.get("name")
        params = {}
        for param_el in stanza_el.findall("param"):
            params[param_el.get("name")] = param_el.text
        stanzas.append((name, params))

    return {
        "server_host": server_host,
        "server_uri": server_uri,
        "session_key": session_key,
        "checkpoint_dir": checkpoint_dir,
        "stanzas": stanzas,
    }


# --------------------------------------------------------------------------
# Pulling the passphrase from Splunk's own storage/passwords instead of
# keeping it in plaintext inputs.conf
# --------------------------------------------------------------------------

def get_stored_passphrase(server_uri, session_key, realm, username):
    """
    Looks up a passphrase that was stored with:
      $SPLUNK_HOME/bin/splunk add secret-storage-password ...
    (or through Settings > Password storage in the app's context).
    Returns None if there's nothing stored - which is fine, that just
    means the key doesn't have a passphrase.
    """
    if not server_uri or not session_key:
        return None
    try:
        import requests
        # server_uri points at Splunk's own management port, normally
        # the local loopback (https://127.0.0.1:8089), which presents
        # Splunk's own server cert rather than something a public CA
        # signed. So we verify against that cert specifically instead of
        # just disabling verification (verify=False would happily accept
        # anyone's cert, including an attacker's). Every Splunk instance
        # has this cert sitting at SPLUNK_HOME/etc/auth/appserver.pem.
        splunk_home = os.environ.get("SPLUNK_HOME", "")
        server_cert = os.path.join(splunk_home, "etc", "auth", "appserver.pem")
        verify = server_cert if (splunk_home and os.path.isfile(server_cert)) else True
        url = f"{server_uri}/servicesNS/nobody/{APP_NAME}/storage/passwords"
        resp = requests.get(
            url,
            headers={"Authorization": f"Splunk {session_key}"},
            params={"output_mode": "json", "search": f"realm={realm}"},
            verify=verify,
            timeout=10,
        )
        resp.raise_for_status()
        entries = resp.json().get("entry", [])
        for e in entries:
            content = e.get("content", {})
            if content.get("username") == username:
                return content.get("clear_password")
    except Exception as e:
        sys.stderr.write(f"WARN could not fetch stored passphrase: {e}\n")
    return None


# --------------------------------------------------------------------------
# What Splunk calls with --validate-arguments before saving a stanza
# --------------------------------------------------------------------------

def do_validate(stream):
    cfg = read_config(stream)
    for name, params in cfg["stanzas"]:
        required = [
            "tenancy_ocid", "user_ocid", "fingerprint", "key_file",
            "region", "stream_ocid", "stream_endpoint",
        ]
        missing = [r for r in required if not params.get(r)]
        if missing:
            _fail(f"Missing required parameter(s) for [{name}]: {', '.join(missing)}")
        key_file = params.get("key_file")
        if key_file and not os.path.isfile(key_file):
            _fail(f"key_file not found on this instance: {key_file}")
    sys.exit(0)


def _fail(message):
    print(f'<error><message>{escape(message)}</message></error>')
    sys.exit(1)


# --------------------------------------------------------------------------
# Writing events back out in Splunk's XML streaming format
# --------------------------------------------------------------------------

def write_event(stanza, data, sourcetype, index=None, source="oci:stream", host=None):
    idx_attr = f' index="{escape(index)}"' if index else ""
    host_tag = f'<host>{escape(host)}</host>' if host else ""
    sys.stdout.write(
        f'<stream><event stanza="{escape(stanza)}"{idx_attr}>'
        f'<source>{escape(source)}</source>'
        f'<sourcetype>{escape(sourcetype)}</sourcetype>'
        f'{host_tag}'
        f'<data>{escape(data)}</data>'
        f'<done/></event></stream>\n'
    )
    sys.stdout.flush()


# --------------------------------------------------------------------------
# Checkpointing, so we can pick up roughly where we left off after a
# restart instead of starting over
# --------------------------------------------------------------------------

def _safe_checkpoint_name(stanza):
    """Stanza names look like 'oci_stream://prod', and '/' plus ':'
    aren't safe to use in filenames on every platform, so this cleans
    the name up before it's used for a checkpoint file."""
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in stanza)


def load_checkpoint(checkpoint_dir, stanza):
    stanza = _safe_checkpoint_name(stanza)
    path = os.path.join(checkpoint_dir, f"{stanza}.checkpoint")
    if os.path.isfile(path):
        try:
            with open(path) as f:
                return json.load(f).get("cursor")
        except Exception:
            return None
    return None


def save_checkpoint(checkpoint_dir, stanza, cursor):
    stanza = _safe_checkpoint_name(stanza)
    path = os.path.join(checkpoint_dir, f"{stanza}.checkpoint")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"cursor": cursor}, f)
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Handling expired cursors
# --------------------------------------------------------------------------
#
# OCI Streaming group cursors expire after enough inactivity or once
# they hit their max TTL (see
# https://docs.oracle.com/iaas/api/#/en/streaming/20180418/Message/GetMessages).
# That's expected and recoverable, not a sign anything's actually wrong
# with the config or credentials, so we catch it here and just create a
# new cursor and keep going instead of getting stuck retrying with one
# that's never going to work again.

def _is_cursor_expired_error(e):
    return (
        getattr(e, "status", None) == 400
        and "expired" in str(getattr(e, "message", "")).lower()
    )


def create_fresh_group_cursor(stream_client, stream_ocid, name, server_host):
    import oci
    # OCI won't accept ':' or '/' in group/instance names, and both the
    # raw stanza name (like "oci_stream://default") and arbitrary
    # hostnames can contain those. Reusing the same cleanup we already
    # do for checkpoint filenames rather than passing either through raw.
    safe_name = _safe_checkpoint_name(name)
    safe_host = _safe_checkpoint_name(server_host) if server_host else "hf"
    cursor_details = oci.streaming.models.CreateGroupCursorDetails(
        group_name=f"splunk-{safe_name}",
        instance_name=f"splunk-{safe_host}",
        type=oci.streaming.models.CreateGroupCursorDetails.TYPE_TRIM_HORIZON,
        commit_on_get=True,
    )
    return stream_client.create_group_cursor(stream_ocid, cursor_details).data.value


# --------------------------------------------------------------------------
# The actual polling loop
# --------------------------------------------------------------------------

def do_run(stream):
    cfg = read_config(stream)
    server_uri = cfg["server_uri"]
    session_key = cfg["session_key"]
    checkpoint_dir = cfg["checkpoint_dir"] or "."

    if not cfg["stanzas"]:
        sys.stderr.write("No stanza configuration received; exiting.\n")
        sys.exit(1)

    # single_instance is set to false, so Splunk runs one process per
    # enabled stanza - meaning there's always exactly one stanza here.
    name, params = cfg["stanzas"][0]

    try:
        import oci
    except ImportError:
        sys.stderr.write(
            "FATAL: `oci` package not installed for this Python interpreter. "
            "Run: $SPLUNK_HOME/bin/splunk cmd python3 -m pip install oci "
            "--target=$SPLUNK_HOME/etc/apps/TA-Oracle-OCI/bin/lib\n"
        )
        sys.exit(1)

    pass_phrase = params.get("pass_phrase") or get_stored_passphrase(
        server_uri, session_key, realm=APP_NAME, username=name
    )

    auth_config = {
        "user": params["user_ocid"],
        "tenancy": params["tenancy_ocid"],
        "fingerprint": params["fingerprint"],
        "key_file": params["key_file"],
        "region": params["region"],
    }
    if pass_phrase:
        auth_config["pass_phrase"] = pass_phrase

    oci.config.validate_config(auth_config)

    stream_client = oci.streaming.StreamClient(
        auth_config, service_endpoint=params["stream_endpoint"]
    )

    stream_ocid = params["stream_ocid"]
    sourcetype_override = params.get("sourcetype_override") or None
    message_limit = int(params.get("message_limit") or 10000)
    retry_interval = int(params.get("retry_interval") or 90)
    poll_interval = int(params.get("poll_interval") or 10)

    cursor = load_checkpoint(checkpoint_dir, name)
    if not cursor:
        cursor = create_fresh_group_cursor(
            stream_client, stream_ocid, name, cfg["server_host"]
        )

    while True:
        try:
            get_response = stream_client.get_messages(
                stream_ocid, cursor, limit=message_limit
            )
            messages = get_response.data

            for msg in messages:
                if msg.value is None:
                    continue
                payload = decode_message_value(msg.value)

                record = None
                try:
                    record = json.loads(payload)
                except (ValueError, TypeError):
                    record = None

                if isinstance(record, dict):
                    sourcetype = sourcetype_override or guess_sourcetype_from_record(record)
                    host = extract_host(record)
                    record = sanitize_payload_for_splunk(record)
                    payload = json.dumps(record)
                else:
                    sourcetype = sourcetype_override or DEFAULT_SOURCETYPE
                    host = None

                write_event(name, payload, sourcetype, host=host)

            cursor = get_response.headers.get("opc-next-cursor", cursor)
            save_checkpoint(checkpoint_dir, name, cursor)

            time.sleep(poll_interval)

        except oci.exceptions.ServiceError as e:
            if e.status == 429:
                sys.stderr.write(f"Throttled by OCI, backing off {retry_interval}s\n")
                time.sleep(retry_interval)
            elif _is_cursor_expired_error(e):
                sys.stderr.write(
                    "Cursor expired (expected/recoverable) - creating a "
                    "fresh cursor and continuing.\n"
                )
                try:
                    cursor = create_fresh_group_cursor(
                        stream_client, stream_ocid, name, cfg["server_host"]
                    )
                    save_checkpoint(checkpoint_dir, name, cursor)
                except Exception as inner_e:
                    sys.stderr.write(
                        f"Failed to create replacement cursor: {inner_e}\n"
                    )
                    time.sleep(retry_interval)
            else:
                sys.stderr.write(f"OCI service error: {e}\n")
                time.sleep(retry_interval)
        except Exception as e:
            sys.stderr.write(f"Unexpected error in poll loop: {e}\n")
            time.sleep(retry_interval)


# --------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--scheme":
        do_scheme()
    elif len(sys.argv) > 1 and sys.argv[1] == "--validate-arguments":
        do_validate(sys.stdin)
    else:
        do_run(sys.stdin)

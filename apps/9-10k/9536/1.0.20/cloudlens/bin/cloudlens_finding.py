#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EventTimeline custom alert action: cloudlens_finding

Reads the alert payload Splunk passes on STDIN, takes the triggering result
row, and writes a normalized finding into the cloudlens_findings KV store
collection via the Splunk REST API. The finding anchors the investigation
workspace (finding_id, anchor entities, alert_time, triggering event id).

Safe by design: never raises out to Splunk (logs + non-zero exit on error),
and only writes fields the collection schema defines.
"""
import csv
import datetime
import gzip
import hashlib
import json
import math
import os
import random
import re
import sys
import time
from urllib.parse import quote

try:
    # Splunk ships this internal REST helper with the platform runtime used by
    # modular alert actions; unlike splunklib it is available by default.
    import splunk.rest as rest
except Exception:  # pragma: no cover - Splunk runtime normally provides this
    rest = None


class ResultFileError(RuntimeError):
    """The alert payload did not contain a readable Splunk results file."""


REST_RETRY_ATTEMPTS = 3
REST_RETRY_STATUSES = {"408", "429", "500", "502", "503", "504"}
REST_RETRY_BASE_SECONDS = 0.25
KV_BATCH_SIZE = 100
MIN_CLOUDTRAIL_EPOCH = 1136073600.0  # 2006-01-01 UTC
MAX_FUTURE_SKEW_SECONDS = 7 * 24 * 60 * 60


def log(msg):
    # Splunk classifies all modular-alert stderr output as ERROR. Successful
    # progress is intentionally quiet; durable state is available in KV Store.
    return None


def log_error(msg):
    sys.stderr.write("cloudlens_finding: %s\n" % msg)


def _response_status(response):
    return str(getattr(response, "status", "") or "")


def _retry_delay(response, attempt):
    headers = getattr(response, "headers", None) or {}
    retry_after = headers.get("Retry-After") if hasattr(headers, "get") else None
    try:
        return min(10.0, max(0.0, float(retry_after)))
    except (TypeError, ValueError):
        # Small jitter prevents simultaneous alert actions from retrying in lockstep.
        return min(4.0, REST_RETRY_BASE_SECONDS * (2 ** attempt) + random.uniform(0, 0.1))


def rest_request(endpoint, session_key, retry_statuses=None, **kwargs):
    """Call Splunk REST with bounded retries for transient platform failures."""
    retry_statuses = retry_statuses or REST_RETRY_STATUSES
    last_response, last_content, last_error = None, "", None
    for attempt in range(REST_RETRY_ATTEMPTS):
        try:
            last_response, last_content = rest.simpleRequest(
                endpoint, sessionKey=session_key, **kwargs
            )
            if (_response_status(last_response) not in retry_statuses
                    or attempt + 1 >= REST_RETRY_ATTEMPTS):
                return last_response, last_content
            log("transient REST status %s for %s; retry %d/%d" % (
                _response_status(last_response), endpoint, attempt + 1,
                REST_RETRY_ATTEMPTS - 1,
            ))
            time.sleep(_retry_delay(last_response, attempt))
        except Exception as exc:
            last_error = exc
            if attempt + 1 >= REST_RETRY_ATTEMPTS:
                raise
            log("transient REST error for %s; retry %d/%d: %s" % (
                endpoint, attempt + 1, REST_RETRY_ATTEMPTS - 1, exc,
            ))
            time.sleep(_retry_delay(None, attempt))
    if last_error:
        raise last_error
    return last_response, last_content


def iter_result_rows(results_file):
    """Yield rows from the Splunk alert results CSV file.

    Splunk normally passes a gzipped CSV to custom alert actions, but some
    ad-hoc/dev paths and older versions can hand over a plain CSV. Support both
    so ordinary Splunk alerts do not silently produce no EventTimeline finding.
    """
    if not results_file:
        raise ResultFileError("alert payload has no results_file")
    try:
        # CloudTrail records can contain large request/response documents.
        # Python's CSV default field limit is too small for valid Splunk rows.
        csv.field_size_limit(min(sys.maxsize, 10 * 1024 * 1024))
        with open(results_file, "rb") as probe:
            is_gzip = probe.read(2) == b"\x1f\x8b"
        opener = gzip.open if is_gzip else open
        with opener(results_file, "rt", newline="", encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.DictReader(fh, strict=True)
            if not reader.fieldnames:
                raise ResultFileError("alert results file has no CSV header")
            headers = [str(name or "").strip() for name in reader.fieldnames]
            if any(not name for name in headers):
                raise ResultFileError("alert results file has an empty CSV header")
            if len(headers) != len(set(headers)):
                raise ResultFileError("alert results file has duplicate CSV headers")
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ResultFileError("alert results file has a malformed CSV row")
                yield row
    except ResultFileError:
        raise
    except Exception as exc:
        raise ResultFileError("could not read results file: %s" % exc)


def result_rows(results_file):
    """Return all rows from the Splunk alert results CSV file.

    Kept for tests and diagnostics. Production alert execution uses the
    streaming iterator above so large result files are not read into memory.
    """
    return list(iter_result_rows(results_file))


def set_if_absent(row, key, value):
    if value is None:
        return
    if row.get(key) not in (None, ""):
        return
    if isinstance(value, (dict, list)):
        try:
            value = json.dumps(value, sort_keys=True)
        except Exception:
            value = str(value)
    value = str(value).strip()
    if value:
        row[key] = value


def dotted_value(data, path):
    cur = data
    for part in path.split("."):
      if isinstance(cur, dict) and part in cur:
          cur = cur[part]
      else:
          return None
    return cur


def first_path(data, *paths):
    for path in paths:
        value = dotted_value(data, path)
        if value not in (None, ""):
            return value
    return None


def first_resource_arn(data):
    resources = data.get("resources") if isinstance(data, dict) else None
    if isinstance(resources, list):
        for item in resources:
            if isinstance(item, dict):
                arn = item.get("ARN") or item.get("arn")
                if arn:
                    return arn
    return None


def augment_row_from_raw(row):
    """Populate common CloudTrail fields from raw JSON when Splunk did not.

    This is intentionally lightweight and local to the alert action. The full
    timeline still uses cloudlens_normalize_aws in SPL, but generic Splunk
    alerts need enough canonical fields here to create a useful finding anchor.
    """
    raw = first_nonempty(row, "_raw", "raw")
    if not raw:
        return row
    try:
        event = json.loads(raw)
    except Exception:
        return row
    if not isinstance(event, dict):
        return row
    records = event.get("Records")
    if isinstance(records, list) and records and isinstance(records[0], dict):
        event = records[0]

    set_if_absent(row, "eventName", event.get("eventName"))
    set_if_absent(row, "eventTime", event.get("eventTime"))
    set_if_absent(row, "_time", event.get("eventTime"))
    set_if_absent(row, "eventID", event.get("eventID"))
    set_if_absent(row, "eventSource", event.get("eventSource"))
    set_if_absent(row, "awsRegion", event.get("awsRegion"))
    set_if_absent(row, "sourceIPAddress", event.get("sourceIPAddress"))
    set_if_absent(row, "src", event.get("sourceIPAddress"))
    set_if_absent(row, "userAgent", event.get("userAgent"))
    set_if_absent(row, "recipientAccountId", event.get("recipientAccountId"))
    set_if_absent(row, "aws_account_id", event.get("recipientAccountId"))
    set_if_absent(row, "errorCode", event.get("errorCode"))
    set_if_absent(row, "errorMessage", event.get("errorMessage"))
    set_if_absent(row, "resources{}.ARN", first_resource_arn(event))

    identity = event.get("userIdentity") if isinstance(event.get("userIdentity"), dict) else {}
    set_if_absent(row, "userIdentity.arn", identity.get("arn"))
    set_if_absent(row, "user_arn", identity.get("arn"))
    set_if_absent(row, "userIdentity.principalId", identity.get("principalId"))
    set_if_absent(row, "userIdentity.accountId", identity.get("accountId"))
    set_if_absent(row, "userIdentity.accessKeyId", identity.get("accessKeyId"))
    set_if_absent(row, "userIdentity.type", identity.get("type"))
    set_if_absent(row, "userIdentity.userName", identity.get("userName"))
    set_if_absent(row, "userIdentity.invokedBy", identity.get("invokedBy"))

    session_context = identity.get("sessionContext") if isinstance(identity.get("sessionContext"), dict) else {}
    session_issuer = session_context.get("sessionIssuer") if isinstance(session_context.get("sessionIssuer"), dict) else {}
    set_if_absent(row, "userIdentity.sessionContext.sessionIssuer.arn", session_issuer.get("arn"))
    set_if_absent(row, "userIdentity.sessionContext.sessionIssuer.userName", session_issuer.get("userName"))
    role_session_name = ((identity.get("arn") or "").rsplit("/", 1)[-1]
                         if identity.get("type") == "AssumedRole" else "")
    set_if_absent(row, "cl_session_issuer_arn", session_issuer.get("arn"))
    set_if_absent(row, "cl_session_issuer_name", session_issuer.get("userName"))
    set_if_absent(row, "cl_role_session_name", role_session_name)
    set_if_absent(row, "cl_session_name", role_session_name)

    params = event.get("requestParameters") if isinstance(event.get("requestParameters"), dict) else {}
    for name in (
        "bucketName", "bucket", "resourceArn", "resourceARN", "userName", "roleName", "groupName",
        "policyArn", "policyName", "roleArn", "accessKeyId", "instanceId",
        "groupId", "trailName", "name", "keyId", "secretId", "parameterName",
        "snapshotId", "volumeId", "vpcId", "subnetId", "routeTableId",
        "networkAclId", "functionName", "repositoryName", "tableName",
        "dbInstanceIdentifier", "clusterIdentifier", "loadBalancerName",
    ):
        set_if_absent(row, "requestParameters.%s" % name, params.get(name))
    items = first_path(event, "requestParameters.instancesSet.items")
    if isinstance(items, list) and items:
        first_item = items[0] if isinstance(items[0], dict) else {}
        set_if_absent(row, "requestParameters.instancesSet.items{}.instanceId", first_item.get("instanceId"))

    console_login = first_path(event, "responseElements.ConsoleLogin")
    created_access_key = first_path(event, "responseElements.accessKey.accessKeyId")
    mfa_used = first_path(event, "additionalEventData.MFAUsed")
    set_if_absent(row, "responseElements.ConsoleLogin", console_login)
    set_if_absent(row, "responseElements.accessKey.accessKeyId", created_access_key)
    set_if_absent(row, "additionalEventData.MFAUsed", mfa_used)

    set_if_absent(row, "cl_action", event.get("eventName"))
    set_if_absent(row, "cl_event_id", event.get("eventID"))
    set_if_absent(row, "cl_service", event.get("eventSource"))
    set_if_absent(row, "cl_region", event.get("awsRegion"))
    set_if_absent(row, "cl_src_ip", event.get("sourceIPAddress"))
    set_if_absent(row, "cl_user_agent", event.get("userAgent"))
    set_if_absent(row, "cl_account_id", event.get("recipientAccountId") or identity.get("accountId"))
    principal_type = str(identity.get("type") or "").strip()
    invoked_by = identity.get("invokedBy")
    set_if_absent(row, "cl_principal_type", principal_type)
    set_if_absent(row, "cl_invoked_by", invoked_by)
    set_if_absent(row, "cl_principal_id", identity.get("arn") or invoked_by or identity.get("principalId") or identity.get("accessKeyId"))
    set_if_absent(row, "cl_access_key", identity.get("accessKeyId"))
    error_code = str(event.get("errorCode") or "").strip()
    error_message = str(event.get("errorMessage") or "").strip()
    set_if_absent(row, "cl_cloud", "aws" if event.get("eventSource") or event.get("eventName") else "")
    set_if_absent(row, "cl_outcome", "failure" if (
        (error_code and error_code.lower() != "success") or error_message
    ) else "success")
    set_if_absent(row, "cl_error", event.get("errorCode") or event.get("errorMessage"))
    return row


def collapse_repeated_scalar(value):
    """Collapse exact duplicate scalar values produced by Splunk multivalue CSVs."""
    value = str(value).strip()
    if not value:
        return ""

    lines = [part.strip() for part in value.splitlines() if part.strip()]
    if len(lines) > 1 and len(set(lines)) == 1:
        return lines[0]

    tokens = value.split()
    if len(tokens) > 1 and len(set(tokens)) == 1:
        return tokens[0]

    if len(tokens) > 1 and len(tokens) % 2 == 0:
        mid = len(tokens) // 2
        first = " ".join(tokens[:mid])
        second = " ".join(tokens[mid:])
        if first == second:
            return first

    return value


def first_nonempty(row, *field_names):
    """Return the first present, non-empty field from a Splunk result row."""
    for name in field_names:
        value = row.get(name)
        if value is None:
            continue
        value = collapse_repeated_scalar(value)
        if is_meaningful(value):
            return value
    return ""


def is_meaningful(value):
    value = collapse_repeated_scalar(value)
    return bool(value and value.lower() not in ("null", "none", "n/a", "na", "unknown", "-"))


def split_result_values(value):
    """Split Splunk CSV multivalue renderings while preserving scalar strings."""
    value = collapse_repeated_scalar(value)
    if not value:
        return []

    parts = []
    for chunk in value.replace(";", "\n").replace(",", "\n").splitlines():
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)

    if len(parts) == 1:
        tokens = parts[0].split()
        if len(tokens) > 1 and all(
            token.startswith("arn:") or token.startswith("AKIA") or token.startswith("ASIA")
            for token in tokens
        ):
            parts = tokens

    unique = []
    for part in parts:
        if is_meaningful(part) and part not in unique:
            unique.append(part)
    return unique


SAFE_SOURCE_COMPONENT = re.compile(r"^[A-Za-z0-9_.:-]+$")
AWS_SERVICE_VALUE = re.compile(r"^[A-Za-z0-9._-]+\.amazonaws\.com(?:\.cn)?$", re.IGNORECASE)


def safe_source_component(value):
    value = first_nonempty({"v": value}, "v")
    if not value or len(value) > 256 or not SAFE_SOURCE_COMPONENT.match(value):
        return ""
    return value


def spl_string_token(value):
    """Escape a saved-search token that is substituted inside an SPL string."""
    value = collapse_repeated_scalar(value or "")[:4096]
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", " ").replace("\n", " ")


def spl_search_term(value):
    """Return a safe non-empty raw-search term for saved-search dispatch."""
    value = collapse_repeated_scalar(value or "")
    if not is_meaningful(value) or value == "*":
        return "__eventtimeline_no_value__"
    return spl_string_token(value)


def hydration_search_terms(finding, anchor_event_id):
    """Prefer selective evidence over shared AWS service identities."""
    values = {
        "event": anchor_event_id,
        "principal": finding.get("cl_principal_id"),
        "username": finding.get("cl_username"),
        "ip": finding.get("cl_src_ip"),
        "resource": finding.get("cl_resource_id"),
    }
    selective = any(
        is_meaningful(values[name]) and not AWS_SERVICE_VALUE.match(collapse_repeated_scalar(values[name]))
        for name in ("event", "principal", "username", "ip", "resource")
    )
    terms = {}
    for name, value in values.items():
        scalar = collapse_repeated_scalar(value or "")
        if selective and AWS_SERVICE_VALUE.match(scalar):
            scalar = ""
        terms[name] = spl_search_term(scalar)
    return terms


def bounded_text(value, maximum=2048):
    return collapse_repeated_scalar(value or "")[:maximum]


def first_unambiguous(row, *field_names):
    """Return a field only when it resolves to one unique value.

    Timeline anchors must not guess when a detection aggregates multiple
    principals or resources into one row. Returning empty forces the timeline to
    use safer resource/account context instead of attaching activity to the
    wrong identity.
    """
    for name in field_names:
        values = split_result_values(row.get(name))
        if len(values) == 1:
            return values[0]
    return ""


def cloudtrail_resource(row):
    """Best-effort resource anchor from standard AWS CloudTrail fields."""
    canonical = first_unambiguous(row, "cl_resource_id", "target_resource")
    if canonical:
        return canonical

    bucket = first_unambiguous(
        row,
        "requestParameters.bucketName",
        "requestParameters.bucket",
        "requestParameters.bucket_name",
        "bucketName",
        "bucket_name",
        "bucket",
    )
    if bucket:
        return bucket if bucket.startswith("arn:") else "arn:aws:s3:::%s" % bucket

    account_id = first_unambiguous(
        row,
        "cl_account_id",
        "recipientAccountId",
        "userIdentity.accountId",
        "accountId",
        "aws_account_id",
        "awsAccountId",
        "awsAccountID",
        "cloud_account_id",
    )
    iam_user = first_unambiguous(row, "requestParameters.userName", "userName", "dest_user")
    if iam_user and account_id:
        return iam_user if iam_user.startswith("arn:") else "arn:aws:iam::%s:user/%s" % (account_id, iam_user)
    iam_role = first_unambiguous(row, "requestParameters.roleName", "roleName")
    if iam_role and account_id:
        return iam_role if iam_role.startswith("arn:") else "arn:aws:iam::%s:role/%s" % (account_id, iam_role)
    iam_group = first_unambiguous(row, "requestParameters.groupName", "groupName")
    if iam_group and account_id:
        return iam_group if iam_group.startswith("arn:") else "arn:aws:iam::%s:group/%s" % (account_id, iam_group)

    return first_unambiguous(
        row,
        "resources{}.ARN",
        "resources.{}.ARN",
        "resources.ARN",
        "requestParameters.resourceArn",
        "requestParameters.resourceARN",
        "resource_arn",
        "resource",
        "object_id",
        "object",
        "dest",
        "dest_host",
        "dvc",
        "host",
        "asset",
        "url",
        "requestParameters.roleArn",
        "requestParameters.policyArn",
        "requestParameters.policyName",
        "requestParameters.instanceId",
        "requestParameters.instancesSet.items{}.instanceId",
        "requestParameters.instancesSet.items.{}.instanceId",
        "requestParameters.groupId",
        "requestParameters.trailName",
        "requestParameters.name",
        "requestParameters.keyId",
        "requestParameters.accessKeyId",
        "responseElements.accessKey.accessKeyId",
        "requestParameters.secretId",
        "requestParameters.parameterName",
        "requestParameters.snapshotId",
        "requestParameters.volumeId",
        "requestParameters.vpcId",
        "requestParameters.subnetId",
        "requestParameters.routeTableId",
        "requestParameters.networkAclId",
        "requestParameters.functionName",
        "requestParameters.repositoryName",
        "requestParameters.tableName",
        "requestParameters.dbInstanceIdentifier",
        "requestParameters.clusterIdentifier",
        "requestParameters.loadBalancerName",
    )


def config_value(cfg, name, default=""):
    return (
        cfg.get(name)
        or cfg.get("param.%s" % name)
        or cfg.get("action.cloudlens_finding.param.%s" % name)
        or default
    )


def config_int(cfg, name, default, minimum=0, maximum=None):
    try:
        value = int(config_value(cfg, name, default))
    except (TypeError, ValueError):
        value = default
    if value < minimum:
        value = minimum
    if maximum is not None and value > maximum:
        value = maximum
    return value


def config_bool(cfg, name, default=False):
    value = config_value(cfg, name, "1" if default else "0")
    return str(value).strip().lower() in ("1", "true", "yes", "on", "enabled")


def payload_search_name(payload, cfg):
    return (
        payload.get("search_name")
        or payload.get("savedsearch_name")
        or payload.get("alert_name")
        or payload.get("name")
        or cfg.get("search_name")
        or cfg.get("savedsearch_name")
        or cfg.get("alert_name")
        or cfg.get("name")
        or ""
    )


def try_parse_alert_time(value):
    """Return a validated epoch, or None when the source value is unusable."""
    value = collapse_repeated_scalar(value or "")
    if not value:
        return None
    maximum = time.time() + MAX_FUTURE_SKEW_SECONDS
    try:
        numeric = float(value)
        if math.isfinite(numeric):
            if abs(numeric) >= 100000000000:
                numeric /= 1000.0
            return numeric if MIN_CLOUDTRAIL_EPOCH <= numeric <= maximum else None
    except (TypeError, ValueError):
        pass

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        parsed = None
    if parsed is None:
        for pattern in ("%Y-%m-%d %H:%M:%S.%f %z", "%Y-%m-%d %H:%M:%S %z", "%m/%d/%Y:%H:%M:%S %z"):
            try:
                parsed = datetime.datetime.strptime(value, pattern)
                break
            except (TypeError, ValueError):
                continue
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    timestamp = parsed.timestamp()
    return timestamp if math.isfinite(timestamp) and MIN_CLOUDTRAIL_EPOCH <= timestamp <= maximum else None


def parse_alert_time(value, fallback=None):
    """Return a bounded epoch, preserving the legacy explicit-fallback API."""
    parsed = try_parse_alert_time(value)
    if parsed is not None:
        return parsed
    fallback = time.time() if fallback is None else fallback
    try:
        fallback = float(fallback)
    except (TypeError, ValueError):
        fallback = time.time()
    if not math.isfinite(fallback):
        fallback = time.time()
    return float(fallback)


def normalize_severity(value, default="medium"):
    value = str(value or default or "medium").strip().lower()
    aliases = {
        "info": "informational", "information": "informational",
        "warning": "medium", "warn": "medium", "moderate": "medium",
        "urgent": "critical", "severe": "critical",
    }
    value = aliases.get(value, value)
    return value if value in ("informational", "low", "medium", "high", "critical") else "medium"


def infer_cloud(row, principal="", account_id=""):
    explicit = first_nonempty(row, "cl_cloud", "cloud_provider", "provider").lower()
    aliases = {"amazon": "aws", "amazon web services": "aws", "splunk": "external"}
    if explicit:
        return aliases.get(explicit, explicit[:64])
    source = " ".join((
        first_nonempty(row, "eventSource", "cl_service"),
        first_nonempty(row, "sourcetype", "cl_source_sourcetype"),
        principal,
    )).lower()
    if ("amazonaws.com" in source or "cloudtrail" in source or principal.startswith("arn:aws:")
            or (str(account_id).isdigit() and len(str(account_id)) == 12
                and first_nonempty(row, "eventName", "cl_action", "eventID", "cl_event_id"))):
        return "aws"
    return "aws" if first_nonempty(row, "eventName", "eventID", "sourceIPAddress") else "external"


def infer_username(row, principal=""):
    """Return the best user or role-session label available for tuning.

    CloudTrail detections normally emit only the canonical principal. Preserve
    an explicit username when present, otherwise derive the IAM user or assumed
    role session component without mislabeling an IAM role name as a user.
    """
    canonical = first_unambiguous(row, "cl_username")
    if canonical:
        return canonical
    principal_type = first_nonempty(row, "cl_principal_type", "userIdentity.type").lower()
    if principal_type in ("awsservice", "awsaccount"):
        return ""
    explicit = first_unambiguous(
        row,
        "userIdentity.userName",
        "userName",
        "username",
        "src_user",
        "user",
    )
    if explicit:
        return explicit
    principal = str(principal or "").strip()
    lower = principal.lower()
    if ":assumed-role/" in lower or ":user/" in lower:
        return principal.rsplit("/", 1)[-1]
    if lower.endswith(":root"):
        return "root"
    if not lower.startswith("arn:") and ":" in principal:
        return principal.rsplit(":", 1)[-1]
    if principal and not lower.startswith("arn:") and "/" not in principal:
        return principal
    return ""


def build_finding(payload, row):
    """Map a result row + alert config into a collection-shaped finding."""
    cfg = payload.get("configuration", {}) or {}
    if not isinstance(cfg, dict):
        cfg = {}
    row = augment_row_from_raw(row or {})
    now = time.time()

    # CloudTrail eventTime is authoritative for evidence chronology. Splunk
    # _time remains the fallback for generic saved-search results.
    time_source = ""
    time_value = None
    for field in ("eventTime", "event_time", "_time"):
        if first_nonempty(row, field):
            time_source = field
            time_value = row.get(field)
            break
    if time_value is None and payload.get("_time") not in (None, ""):
        time_source = "payload._time"
        time_value = payload.get("_time")
    alert_time = try_parse_alert_time(time_value)
    if alert_time is None:
        raise ValueError("alert result has no valid eventTime, event_time, or _time")

    detection = first_nonempty(row, "detection", "signature", "rule_name", "search_name") or payload_search_name(payload, cfg) or "unknown"
    anchor_event_id = first_unambiguous(row, "cl_event_id", "eventID", "eventId", "event_id")
    principal = first_unambiguous(
        row,
        "cl_principal_id",
        "user_arn",
        "userArn",
        "userARN",
        "aws_user_arn",
        "source_arn",
        "sourceArn",
        "principal_arn",
        "principalArn",
        "principalId",
        "userIdentity.arn",
        "userIdentity.principalId",
        "userIdentity.accessKeyId",
        "src_user_id",
        "user_id",
        "src_user",
        "user",
        "dest_user",
        "identity",
        "principal",
        "owner",
    )
    resource = cloudtrail_resource(row)
    src_ip = first_unambiguous(row, "cl_src_ip", "sourceIPAddress", "src_ip", "source_ip", "clientip", "src")
    username = infer_username(row, principal)
    account_id = first_unambiguous(row, "cl_account_id", "recipientAccountId", "userIdentity.accountId", "accountId", "aws_account_id", "awsAccountId", "awsAccountID", "cloud_account_id")
    action = first_nonempty(row, "cl_action", "eventName", "event_name", "action", "search_name", "rule_name", "rule_title")
    source_index = safe_source_component(first_unambiguous(row, "cl_source_index", "index", "_index", "orig_index"))
    source_sourcetype = safe_source_component(first_unambiguous(row, "cl_source_sourcetype", "sourcetype", "_sourcetype", "orig_sourcetype"))
    cloud = infer_cloud(row, principal, account_id)
    principal_type = first_nonempty(row, "cl_principal_type", "userIdentity.type")
    finding = {
        "detection": bounded_text(detection, 512),
        "severity": normalize_severity(first_nonempty(row, "severity", "urgency", "priority"), config_value(cfg, "severity", "medium")),
        "mitre_technique": bounded_text(first_unambiguous(
            row, "mitre_technique", "mitre_technique_id", "technique_id", "attack_technique"
        ), 256),
        "mitre_tactic": bounded_text(first_unambiguous(
            row, "mitre_tactic", "tactic", "attack_tactic"
        ), 256),
        "cl_cloud": bounded_text(cloud, 64),
        "cl_account_id": bounded_text(account_id, 256),
        "cl_principal_id": bounded_text(principal),
        "cl_principal_type": bounded_text(principal_type, 64),
        "cl_username": bounded_text(username, 512),
        "cl_role_session_name": bounded_text(first_unambiguous(row, "cl_role_session_name", "cl_session_name"), 512),
        "cl_session_issuer_arn": bounded_text(first_unambiguous(row, "cl_session_issuer_arn", "userIdentity.sessionContext.sessionIssuer.arn")),
        "cl_session_issuer_name": bounded_text(first_unambiguous(row, "cl_session_issuer_name", "userIdentity.sessionContext.sessionIssuer.userName"), 512),
        "cl_invoked_by": bounded_text(first_unambiguous(row, "cl_invoked_by", "userIdentity.invokedBy"), 512),
        "cl_resource_id": bounded_text(resource, 4096),
        "cl_src_ip": bounded_text(src_ip, 256),
        "cl_action": bounded_text(action, 512),
        "cl_event_id": bounded_text(anchor_event_id, 512),
        "cl_source_index": source_index,
        "cl_source_sourcetype": source_sourcetype,
        "alert_time": alert_time,
        "alert_time_source": time_source,
        "detection_time": now,
        "status": bounded_text(config_value(cfg, "default_status", "new"), 64) or "new",
        "assignee": "",
        "timeline_anchor_status": "manual",
        "hydration_status": "manual",
        "hydration_attempts": 0,
        "hydration_last_error": "",
        "hydration_updated_at": now,
        "hydration_truncated": False,
        "hydration_limit": 0,
        "hydration_source_mode": "",
        "hydration_profile": "compact",
        "hydration_generation": "",
    }
    finding["dedup_key"] = finding_dedup_key(finding)
    finding_id = "cl-" + hashlib.sha256(finding["dedup_key"].encode("utf-8")).hexdigest()[:12]
    finding["_key"] = finding_id
    finding["finding_id"] = finding_id
    # Carry the triggering event id if the detection surfaced it (used by the
    # hydration search to flag is_alert on the exact event).
    return finding, anchor_event_id


def chunked(values, size=KV_BATCH_SIZE):
    """Yield bounded lists so KV requests stay below practical REST limits."""
    size = max(1, min(int(size), KV_BATCH_SIZE))
    for offset in range(0, len(values), size):
        yield values[offset:offset + size]


def batch_upsert_kv_records(session_key, collection, records, batch_size=KV_BATCH_SIZE):
    """Persist records with bounded /batch_save calls.

    KV Store replaces an existing document when its key is saved, so callers
    must provide the complete server-owned record rather than a partial patch.
    """
    records = list(records or [])
    if not records:
        return 0
    base_endpoint = "/servicesNS/nobody/cloudlens/storage/collections/data/%s" % collection
    written = 0
    for batch in chunked(records, batch_size):
        for record in batch:
            if not isinstance(record, dict) or not record.get("_key"):
                raise RuntimeError("record for %s has no _key" % collection)
        response, content = rest_request(
            base_endpoint + "/batch_save",
            session_key,
            method="POST",
            jsonargs=json.dumps(batch),
        )
        status = str(getattr(response, "status", ""))
        if status not in ("200", "201", "204"):
            raise RuntimeError("KV batch write failed collection=%s status=%s body=%s" %
                               (collection, status or "?", content))
        written += len(batch)
    return written


def batch_find_kv_records(session_key, collection, queries, limit=1,
                          batch_size=KV_BATCH_SIZE):
    """Return one result list per query using bounded /batch_find calls."""
    queries = list(queries or [])
    if not queries:
        return []
    endpoint = "/servicesNS/nobody/cloudlens/storage/collections/data/%s/batch_find" % collection
    results = []
    bounded_limit = max(1, min(int(limit), 100))
    for batch in chunked(queries, batch_size):
        payload = [{"query": query, "limit": bounded_limit} for query in batch]
        response, content = rest_request(
            endpoint,
            session_key,
            method="POST",
            jsonargs=json.dumps(payload),
        )
        status = str(getattr(response, "status", ""))
        if status not in ("200", "201"):
            raise RuntimeError("KV batch find failed collection=%s status=%s body=%s" %
                               (collection, status or "?", content))
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        try:
            batch_results = json.loads(content or "[]")
        except ValueError:
            raise RuntimeError("KV batch find returned invalid JSON for collection=%s" % collection)
        if not isinstance(batch_results, list) or len(batch_results) != len(batch):
            raise RuntimeError("KV batch find returned an unexpected result count for collection=%s" % collection)
        results.extend(rows if isinstance(rows, list) else [] for rows in batch_results)
    return results


def upsert_kv_record(session_key, collection, record):
    return batch_upsert_kv_records(session_key, collection, [record]) == 1


def list_kv_records(session_key, collection):
    endpoint = "/servicesNS/nobody/cloudlens/storage/collections/data/%s" % collection
    response, content = rest_request(
        endpoint,
        session_key,
        method="GET",
        getargs={"output_mode": "json", "count": "0"},
    )
    if str(getattr(response, "status", "")) != "200":
        raise RuntimeError("KV read failed collection=%s status=%s body=%s" %
                           (collection, getattr(response, "status", "?"), content))
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    try:
        return json.loads(content or "[]")
    except ValueError:
        return []


def query_kv_records(session_key, collection, query, limit=20):
    endpoint = "/servicesNS/nobody/cloudlens/storage/collections/data/%s" % collection
    response, content = rest_request(
        endpoint,
        session_key,
        method="GET",
        getargs={
            "output_mode": "json",
            "query": json.dumps(query, separators=(",", ":")),
            "limit": str(max(1, min(int(limit), 100))),
        },
    )
    if str(getattr(response, "status", "")) != "200":
        raise RuntimeError("KV query failed collection=%s status=%s body=%s" %
                           (collection, getattr(response, "status", "?"), content))
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    try:
        rows = json.loads(content or "[]")
    except ValueError:
        raise RuntimeError("KV query returned invalid JSON for collection=%s" % collection)
    return rows if isinstance(rows, list) else []


def automatic_timeline_generation_enabled(session_key):
    """Return the global timeline mode, defaulting safely to manual.

    A missing or unreadable setting must never fan out raw CloudTrail searches
    from an alert action. Administrators explicitly opt in from Setup.
    """
    try:
        rows = query_kv_records(
            session_key,
            "cloudlens_settings",
            {"setting": "automatic_timeline_generation"},
            limit=1,
        )
        if not rows:
            return False
        value = str(rows[0].get("value") or "").strip().lower()
        return value in ("1", "true", "yes", "on", "enabled", "automatic")
    except Exception as exc:
        log("timeline mode setting unavailable; using manual generation: %s" % exc)
        return False


def delete_kv_record(session_key, collection, key):
    if not key:
        return False
    endpoint = "/servicesNS/nobody/cloudlens/storage/collections/data/%s/%s" % (
        collection, quote(str(key), safe="")
    )
    response, content = rest_request(
        endpoint,
        session_key,
        method="DELETE",
    )
    status = str(getattr(response, "status", ""))
    if status in ("200", "204", "404"):
        return status != "404"
    raise RuntimeError("KV delete failed collection=%s status=%s body=%s" %
                       (collection, status or "?", content))



def finding_dedup_key(finding):
    """Return a conservative cross-detection duplicate key for a finding."""
    cloud = str(finding.get("cl_cloud") or "aws").strip().lower()
    account = str(finding.get("cl_account_id") or "").strip()
    event_id = str(finding.get("cl_event_id") or "").strip()
    if event_id:
        return "event|%s|%s|%s" % (cloud, account, event_id)

    try:
        alert_time = "%.3f" % float(finding.get("alert_time") or 0)
    except (TypeError, ValueError):
        alert_time = "0"
    anchor = "|".join([
        cloud,
        account,
        str(finding.get("cl_action") or "").strip(),
        str(finding.get("cl_principal_id") or "").strip(),
        str(finding.get("cl_resource_id") or "").strip(),
        str(finding.get("cl_src_ip") or "").strip(),
        alert_time,
    ])
    return "anchor|" + hashlib.sha256(anchor.encode("utf-8")).hexdigest()[:24]


def matching_duplicate_finding(findings, finding):
    dedup_key = finding.get("dedup_key") or finding_dedup_key(finding)
    for existing in findings or []:
        if (existing.get("dedup_key") or finding_dedup_key(existing)) == dedup_key:
            return existing
    return None


def dedup_claim_key(finding):
    value = finding.get("dedup_key") or finding_dedup_key(finding)
    return "dedup-" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def dedup_claim_record(finding, created_at=None):
    return {
        "_key": dedup_claim_key(finding),
        "dedup_key": finding.get("dedup_key") or finding_dedup_key(finding),
        "finding_id": finding.get("finding_id") or "",
        "created_at": time.time() if created_at is None else created_at,
    }


def claim_finding_dedup(session_key, finding, stale_seconds=300):
    """Persist canonical dedup ownership without conflict-based KV writes.

    The finding ID is derived from the cross-detection dedup key, so all
    concurrent alert actions for one event converge on the same owner and the
    same finding record.
    """
    collection = "cloudlens_dedup_claims"
    record = dedup_claim_record(finding)
    # Finding IDs are canonical across saved-search names, so every concurrent
    # owner of this claim is the same logical finding. Batch-save avoids the
    # expected 409 conflicts that Splunk records as health errors.
    upsert_kv_record(session_key, collection, record)
    return None


def stored_duplicate_query(finding):
    dedup_key = finding.get("dedup_key") or finding_dedup_key(finding)
    legacy = {
        "cl_cloud": finding.get("cl_cloud") or "aws",
        "cl_account_id": finding.get("cl_account_id") or "",
    }
    event_id = finding.get("cl_event_id") or ""
    if event_id:
        legacy["cl_event_id"] = event_id
    else:
        legacy.update({
            "cl_action": finding.get("cl_action") or "",
            "cl_principal_id": finding.get("cl_principal_id") or "",
            "cl_resource_id": finding.get("cl_resource_id") or "",
            "cl_src_ip": finding.get("cl_src_ip") or "",
            "alert_time": finding.get("alert_time") or 0,
        })
    return {"$or": [{"_key": finding.get("_key")}, {"dedup_key": dedup_key}, legacy]}


def stored_duplicate_finding(session_key, finding):
    rows = query_kv_records(
        session_key,
        "cloudlens_findings",
        stored_duplicate_query(finding),
        limit=5,
    )
    return matching_duplicate_finding(rows, finding)


def write_finding(session_key, finding):
    # Upsert by deterministic key. This prevents duplicate findings when the
    # same scheduled search window or manual rerun sees the same triggering
    # event again.
    return upsert_kv_record(session_key, "cloudlens_findings", finding)


def build_alert_timeline_record(finding, row, anchor_event_id):
    """Create a minimal timeline row for the alert itself.

    CloudTrail hydration later adds richer context, but the triggering alert
    always receives a visible investigation anchor first.
    """
    principal = finding.get("cl_principal_id") or finding.get("cl_src_ip") or "alert"
    event_id = anchor_event_id or finding.get("cl_event_id") or finding["finding_id"]
    action = finding.get("cl_action") or finding.get("detection") or "Alert"
    service = first_nonempty(row, "cl_service", "eventSource", "security_domain", "app", "source", "sourcetype") or finding.get("cl_cloud") or "Alert"
    row_key = "%s::alert::%s" % (finding["finding_id"], hashlib.sha256(str(event_id).encode("utf-8")).hexdigest()[:12])
    record = {
        "_key": row_key,
        "finding_id": finding["finding_id"],
        "element_type": "event",
        "timeline_scope": "both",
        "followup_id": "alert",
        "followup_label": "Alert trigger",
        "node_id": principal,
        "node_kind": "principal" if finding.get("cl_principal_id") else "ip",
        "label": principal,
        "parent_id": finding.get("cl_src_ip") if finding.get("cl_src_ip") != principal else "",
        "event_time": finding.get("alert_time") or time.time(),
        "outcome": first_nonempty(row, "cl_outcome", "status_label", "status", "disposition") or "alert",
        "is_alert": "true",
        "detail": (
            first_nonempty(row, "description", "rule_description", "drilldown_search")
            or " ".join(part for part in (action, finding.get("cl_resource_id") or "") if part).strip()
            or finding.get("detection")
            or ""
        ),
        "cl_action": action,
        "cl_cloud": finding.get("cl_cloud") or "aws",
        "cl_account_id": finding.get("cl_account_id") or "",
        "cl_region": first_nonempty(row, "cl_region", "region", "awsRegion"),
        "cl_service": service,
        "cl_resource_id": finding.get("cl_resource_id") or "",
        "cl_principal_id": finding.get("cl_principal_id") or "",
        "cl_access_key": first_unambiguous(row, "cl_access_key", "userIdentity.accessKeyId", "access_key", "accessKeyId"),
        "cl_session_name": finding.get("cl_role_session_name") or first_nonempty(row, "cl_session_name", "session", "src_session"),
        "cl_role_session_name": finding.get("cl_role_session_name") or first_nonempty(row, "cl_session_name", "session", "src_session"),
        "cl_session_issuer_arn": finding.get("cl_session_issuer_arn") or first_nonempty(row, "userIdentity.sessionContext.sessionIssuer.arn"),
        "cl_session_issuer_name": finding.get("cl_session_issuer_name") or first_nonempty(row, "userIdentity.sessionContext.sessionIssuer.userName"),
        "cl_src_ip": finding.get("cl_src_ip") or "",
        "cl_user_agent": first_nonempty(row, "cl_user_agent", "userAgent", "user_agent"),
        "cl_error": first_nonempty(row, "cl_error", "errorCode", "reason"),
        "cl_event_id": anchor_event_id or finding.get("cl_event_id") or "",
        "cl_source_index": finding.get("cl_source_index") or first_nonempty(row, "index"),
        "cl_source_sourcetype": finding.get("cl_source_sourcetype") or first_nonempty(row, "sourcetype"),
    }
    return record


def write_alert_timeline_row(session_key, finding, row, anchor_event_id):
    """Persist one canonical alert anchor and clean up older legacy anchors."""
    record = build_alert_timeline_record(finding, row, anchor_event_id)
    row_key = record["_key"]
    result = upsert_kv_record(session_key, "cloudlens_investigation", record)
    try:
        alert_rows = query_kv_records(
            session_key,
            "cloudlens_investigation",
            {"finding_id": finding["finding_id"], "is_alert": "true"},
            limit=100,
        )
        for existing in alert_rows:
            existing_key = existing.get("_key")
            if existing_key and existing_key != row_key:
                delete_kv_record(session_key, "cloudlens_investigation", existing_key)
                log("removed duplicate alert timeline anchor %s for finding %s" %
                    (existing_key, finding["finding_id"]))
    except Exception as exc:
        # The canonical row is already durable. Legacy cleanup is best-effort
        # and can be retried if this finding is processed again.
        log("duplicate alert timeline cleanup failed for finding %s: %s" %
            (finding.get("finding_id"), exc))
    return result


def dispatch_hydration(session_key, finding, anchor_event_id, payload_cfg=None):
    """Assemble an investigation timeline for an automatic or manual request.

    Dispatches the 'CloudLens - Hydrate Investigation' saved search with the
    anchor entities and a window that spans the lookback before the alert
    through a short lookahead after it.

    The window is anchored on the finding's alert_time (epoch): earliest is
    (default) 2h before the alert, latest is the alert time + a short
    lookahead so any immediate follow-on activity is captured.
    """
    # Default: the 2 hours before the alert (as specified), plus a short
    # lookahead so immediate follow-on activity (e.g. a GetObject exfil right
    # after DeleteBucketEncryption) is captured. Both are overridable per
    # saved search via action.cloudlens_finding.param.{lookback,lookahead}_secs.
    cfg = (payload_cfg or {})
    LOOKBACK_SECS = config_int(cfg, "lookback_secs", 2 * 60 * 60, minimum=300, maximum=24 * 60 * 60)
    LOOKAHEAD_SECS = config_int(cfg, "lookahead_secs", 30 * 60, minimum=0, maximum=6 * 60 * 60)
    MAX_TIMELINE_EVENTS = config_int(cfg, "max_timeline_events", 2000, minimum=100, maximum=10000)
    MAX_CORRELATION_EVENTS = min(20000, max(MAX_TIMELINE_EVENTS + 1, MAX_TIMELINE_EVENTS * 4))
    MAX_TIME_SECS = config_int(cfg, "hydration_max_time_secs", 300, minimum=30, maximum=1800)
    alert_time = try_parse_alert_time(finding.get("alert_time"))
    if alert_time is None:
        finding["_hydration_error"] = "Finding has no valid alert_time; hydration was not dispatched."
        return False
    earliest = "%d" % int(math.floor(alert_time - LOOKBACK_SECS))
    latest = "%d" % int(math.ceil(alert_time + LOOKAHEAD_SECS))

    source_index = safe_source_component(finding.get("cl_source_index"))
    source_sourcetype = safe_source_component(finding.get("cl_source_sourcetype"))
    source_mode = "exact" if source_index else "macro_fallback"

    # Disable the macro branch when exact source metadata is available. When
    # an aggregate alert omitted index metadata, the configured CloudTrail
    # macro remains the bounded fallback source.
    include_role_lineage = config_bool(cfg, "include_role_lineage")
    hydration_profile = "role_lineage" if include_role_lineage else "compact"
    timeline_scope = "resource" if is_meaningful(finding.get("cl_resource_id")) else "user"
    hydration_generation = first_nonempty(finding, "hydration_generation") or new_hydration_generation(finding)
    finding["hydration_profile"] = hydration_profile
    finding["hydration_generation"] = hydration_generation
    search_terms = hydration_search_terms(finding, anchor_event_id)
    anchor_principal = finding.get("cl_principal_id")
    anchor_username = finding.get("cl_username")
    anchor_ip = finding.get("cl_src_ip")
    anchor_resource = finding.get("cl_resource_id")
    if hydration_profile == "compact" and timeline_scope == "resource":
        anchor_principal = ""
        anchor_username = ""
        anchor_ip = ""
        search_terms["principal"] = "__eventtimeline_no_value__"
        search_terms["username"] = "__eventtimeline_no_value__"
        search_terms["ip"] = "__eventtimeline_no_value__"
    elif hydration_profile == "compact":
        anchor_resource = ""
        search_terms["resource"] = "__eventtimeline_no_value__"
    args = {
        "dispatch.earliest_time": earliest,
        "dispatch.latest_time": latest,
        "dispatch.max_time": str(MAX_TIME_SECS),
        "force_dispatch": "1",
        "trigger_actions": "1",
        "args.finding_id": finding["finding_id"],
        "args.hydration_dispatch_id": spl_string_token(finding.get("hydration_dispatch_id")),
        "args.hydration_generation": spl_string_token(hydration_generation),
        "args.hydration_profile": hydration_profile,
        "args.timeline_scope": timeline_scope,
        "args.anchor_cloud": spl_string_token(finding.get("cl_cloud")),
        "args.anchor_principal": spl_string_token(anchor_principal),
        "args.anchor_username": spl_string_token(anchor_username),
        "args.anchor_ip": spl_string_token(anchor_ip),
        "args.anchor_resource": spl_string_token(anchor_resource),
        "args.anchor_account": spl_string_token(finding.get("cl_account_id")),
        "args.anchor_event_id": spl_string_token(anchor_event_id),
        "args.search_event_term": search_terms["event"],
        "args.search_principal_term": search_terms["principal"],
        "args.search_username_term": search_terms["username"],
        "args.search_ip_term": search_terms["ip"],
        "args.search_resource_term": search_terms["resource"],
        "args.anchor_time": "%.3f" % alert_time,
        "args.source_index": source_index or "__cloudlens_no_index__",
        "args.source_sourcetype": source_sourcetype or "*",
        "args.fallback_index": "__cloudlens_no_index__" if source_index else "*",
        "args.source_mode": source_mode,
        "args.max_timeline_events": str(MAX_TIMELINE_EVENTS),
        "args.max_timeline_events_plus_one": str(MAX_TIMELINE_EVENTS + 1),
        "args.max_correlation_events": str(MAX_CORRELATION_EVENTS),
    }
    try:
        search_name = (
            "CloudLens - Hydrate Investigation"
            if hydration_profile == "role_lineage"
            else "CloudLens - Hydrate Investigation Compact"
        )
        search_endpoint = "/servicesNS/nobody/cloudlens/saved/searches/%s" % quote(search_name, safe="")
        endpoint = search_endpoint + "/dispatch"
        response, content = rest_request(
            endpoint,
            session_key,
            method="POST",
            postargs=args,
        )
        status = str(getattr(response, "status", ""))
        body = content.decode("utf-8", "replace") if isinstance(content, bytes) else str(content or "")
        if status == "400" and "disabled" in body.lower():
            # This is an internal on-demand helper, not a user-facing detector.
            # Repair stale local overrides left by upgrades, then retry once.
            enabled_response, enabled_content = rest_request(
                search_endpoint,
                session_key,
                method="POST",
                postargs={"disabled": "0"},
            )
            if str(getattr(enabled_response, "status", "")) not in ("200", "201"):
                raise RuntimeError("could not enable hydration helper status=%s body=%s" %
                                   (getattr(enabled_response, "status", "?"), enabled_content))
            response, content = rest_request(
                endpoint,
                session_key,
                method="POST",
                postargs=args,
            )
            status = str(getattr(response, "status", ""))
        if status not in ("200", "201"):
            raise RuntimeError("dispatch failed status=%s body=%s" %
                               (status or "?", content))
        log("dispatched %s hydration job for finding %s (window %s..%s source=%s max_events=%d max_time=%ds)"
            % (hydration_profile, finding["finding_id"], earliest, latest,
               source_mode, MAX_TIMELINE_EVENTS, MAX_TIME_SECS))
        return True
    except Exception as exc:
        # Non-fatal: the finding is already written and the investigation view
        # can still hydrate on demand. Log and continue.
        finding["_hydration_error"] = bounded_text(exc, 1000)
        log("hydration dispatch failed (non-fatal): %s" % exc)
        return False


def should_hydrate_finding(finding):
    """Return true when a finding has enough AWS context to justify raw search.

    Imported alerts and aggregate alerts always receive an alert-anchor row.
    Hydration should only fan out into raw CloudTrail when at least one useful
    pivot exists; otherwise a production deployment can spend scheduler slots
    on broad searches that cannot match anything specific.
    """
    if finding.get("cl_cloud") != "aws" and not safe_source_component(finding.get("cl_source_index")):
        return False
    return any(is_meaningful(finding.get(field)) for field in (
        "cl_event_id",
        "cl_principal_id",
        "cl_resource_id",
        "cl_src_ip",
    ))


MAINTENANCE_COLLECTIONS = {
    "retention_findings": "cloudlens_findings",
    "retention_triage": "cloudlens_finding_triage",
    "retention_investigation": "cloudlens_investigation",
    "retention_dedup_claims": "cloudlens_dedup_claims",
}


def strip_legacy_timeline_raw(session_key, max_passes=5):
    """Remove legacy raw payloads from bounded KV batches during upgrades."""
    processed = 0
    for _pass in range(max(1, min(int(max_passes), 5))):
        rows = query_kv_records(
            session_key,
            "cloudlens_investigation",
            {"cl_raw_event": {"$gt": ""}},
            limit=100,
        )
        if not rows:
            break
        updates = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("_key"):
                continue
            row.pop("cl_raw_event", None)
            row.pop("_user", None)
            updates.append(row)
        if updates:
            processed += batch_upsert_kv_records(
                session_key, "cloudlens_investigation", updates
            )
        if len(rows) < 100:
            break
    log("legacy timeline raw migration stripped %d record(s)" % processed)
    return 0


def run_retention_cleanup(payload, mode, session_key):
    """Delete only the bounded keys selected by a retention saved search."""
    if mode == "strip_legacy_timeline_raw":
        try:
            return strip_legacy_timeline_raw(session_key)
        except Exception as exc:
            log_error("legacy timeline raw migration failed: %s" % exc)
            return 5
    collection = MAINTENANCE_COLLECTIONS.get(mode)
    if not collection:
        log_error("unsupported maintenance mode: %s" % mode)
        return 2
    seen = deleted = missing = failed = 0
    try:
        for row in iter_result_rows(payload.get("results_file")):
            seen += 1
            key = first_nonempty(row, "_key", "key")
            if not key:
                failed += 1
                log_error("retention row %d has no _key" % seen)
                continue
            try:
                if delete_kv_record(session_key, collection, key):
                    deleted += 1
                else:
                    missing += 1
            except Exception as exc:
                failed += 1
                log_error("retention delete failed collection=%s key=%s: %s" %
                          (collection, bounded_text(key, 256), exc))
    except ResultFileError as exc:
        log_error(str(exc))
        return 6
    log("retention mode=%s processed=%d deleted=%d missing=%d failed=%d" %
        (mode, seen, deleted, missing, failed))
    return 5 if failed else 0


def complete_hydration(payload, session_key):
    """Persist the terminal result emitted by the hydration saved search."""
    seen = completed = failed = 0
    completion_rows = []
    try:
        for row in iter_result_rows(payload.get("results_file")):
            seen += 1
            completion_rows.append(row)
    except ResultFileError as exc:
        log_error(str(exc))
        return 6

    valid_rows = []
    for row_number, row in enumerate(completion_rows, 1):
        finding_id = first_nonempty(row, "finding_id", "_key")
        if not finding_id:
            failed += 1
            log_error("hydration completion row %d has no finding_id" % row_number)
        else:
            valid_rows.append((finding_id, row))

    try:
        matches_by_row = batch_find_kv_records(
            session_key,
            "cloudlens_findings",
            [{"$or": [{"_key": finding_id}, {"finding_id": finding_id}]} for finding_id, _row in valid_rows],
            limit=1,
        )
    except Exception as exc:
        failed += len(valid_rows)
        log_error("hydration completion batch lookup failed: %s" % exc)
        matches_by_row = [[] for _item in valid_rows]

    updates = []
    for (finding_id, row), matches in zip(valid_rows, matches_by_row):
        try:
            if not matches:
                raise RuntimeError("finding no longer exists")
            finding = matches[0]
            completion_dispatch_id = first_nonempty(row, "hydration_dispatch_id")
            completion_generation = first_nonempty(row, "hydration_generation")
            completion_profile = first_nonempty(row, "hydration_profile") or "compact"
            current_dispatch_id = first_nonempty(finding, "hydration_dispatch_id")
            current_generation = first_nonempty(finding, "hydration_generation")
            if (completion_generation and current_generation
                    and hydration_generation_rank(completion_generation) < hydration_generation_rank(current_generation)):
                log("ignored stale hydration completion for finding %s" % finding_id)
                continue
            active_status = first_nonempty(finding, "hydration_status").lower()
            if (completion_dispatch_id and current_dispatch_id
                    and completion_dispatch_id != current_dispatch_id
                    and (not completion_generation or completion_generation == current_generation)
                    and active_status in ("pending", "dispatching", "dispatched", "retry_pending")):
                log("ignored mismatched active hydration completion for finding %s" % finding_id)
                continue
            count = max(0, int(float(row.get("hydration_result_count") or 0)))
            finding["_key"] = finding.get("_key") or finding_id
            finding["finding_id"] = finding_id
            finding["hydration_status"] = "complete" if count else "complete_zero"
            finding["hydration_result_count"] = count
            finding["hydration_truncated"] = (
                first_nonempty(row, "hydration_truncated").lower() == "true"
            )
            try:
                finding["hydration_limit"] = max(
                    0, int(float(row.get("hydration_limit") or 0))
                )
            except (TypeError, ValueError):
                finding["hydration_limit"] = 0
            finding["hydration_source_mode"] = bounded_text(
                first_nonempty(row, "hydration_source_mode"), 32
            )
            finding["hydration_profile"] = bounded_text(completion_profile, 32)
            if completion_generation:
                finding["hydration_generation"] = bounded_text(completion_generation, 64)
            finding["hydration_last_error"] = ""
            if completion_dispatch_id:
                finding["hydration_dispatch_id"] = completion_dispatch_id
            finding["hydration_completed_at"] = time.time()
            finding["hydration_updated_at"] = finding["hydration_completed_at"]
            updates.append(finding)
        except Exception as exc:
            failed += 1
            log_error("hydration completion failed finding=%s: %s" %
                      (bounded_text(finding_id, 256), exc))

    if updates:
        try:
            batch_upsert_kv_records(session_key, "cloudlens_findings", updates)
            completed = len(updates)
        except Exception as exc:
            failed += len(updates)
            log_error("hydration completion batch write failed: %s" % exc)
    log("hydration completion processed=%d completed=%d failed=%d" %
        (seen, completed, failed))
    return 5 if failed else 0


RETRY_FINDING_FIELDS = (
    "finding_id", "detection", "severity", "mitre_technique", "mitre_tactic",
    "cl_cloud", "cl_account_id",
    "cl_principal_id", "cl_principal_type", "cl_username", "cl_role_session_name",
    "cl_session_issuer_arn", "cl_session_issuer_name", "cl_invoked_by",
    "cl_resource_id", "cl_src_ip", "cl_action",
    "cl_event_id", "cl_source_index", "cl_source_sourcetype",
    "alert_time", "detection_time", "status", "assignee",
    "dedup_key", "timeline_anchor_status", "hydration_status",
    "hydration_attempts", "hydration_last_error", "hydration_updated_at",
    "hydration_completed_at", "hydration_result_count", "hydration_dispatch_id",
    "hydration_truncated", "hydration_limit", "hydration_source_mode",
    "hydration_profile", "hydration_generation",
    "hydration_retry_reason",
)


def retry_finding_from_row(row):
    finding = {field: row.get(field, "") for field in RETRY_FINDING_FIELDS}
    finding_id = first_nonempty(row, "finding_id", "_key")
    if not finding_id:
        raise ValueError("hydration retry row has no finding_id")
    finding["finding_id"] = finding_id
    finding["_key"] = finding_id
    finding["alert_time"] = try_parse_alert_time(row.get("alert_time"))
    try:
        finding["hydration_attempts"] = max(0, int(row.get("hydration_attempts") or 0))
    except (TypeError, ValueError):
        finding["hydration_attempts"] = 0
    return finding


def persist_hydration_state(session_key, finding, status, error=""):
    finding["hydration_status"] = status
    finding["hydration_last_error"] = bounded_text(error, 1000)
    finding["hydration_updated_at"] = time.time()
    finding.pop("_hydration_error", None)
    return write_finding(session_key, finding)


def new_hydration_dispatch_id(finding):
    """Create an opaque attempt ID before dispatch for race-safe completion."""
    seed = "%s|%s|%s|%s" % (
        finding.get("finding_id") or "",
        finding.get("hydration_attempts") or 0,
        time.time_ns(),
        random.random(),
    )
    return "clh-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


def new_hydration_generation(finding):
    """Create a sortable generation ID so late completions cannot win."""
    epoch_ms = int(time.time() * 1000)
    seed = "%s|%s|%s" % (finding.get("finding_id") or "", epoch_ms, random.random())
    suffix = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    return "clg-%013d-%s" % (epoch_ms, suffix)


def hydration_generation_rank(value):
    match = re.match(r"^clg-(\d{13})-", str(value or ""))
    return int(match.group(1)) if match else 0


def retry_pending_hydrations(payload, cfg, session_key):
    """Retry durable hydration work emitted by the internal retry search."""
    max_attempts = config_int(cfg, "hydration_retry_max_attempts", 5, minimum=1, maximum=20)
    rows_seen = succeeded = failed = skipped = 0
    retry_candidates = []
    initial_updates = []
    expected_dispatch_ids = {}
    try:
        for row in iter_result_rows(payload.get("results_file")):
            rows_seen += 1
            try:
                finding = retry_finding_from_row(row)
                expected_dispatch_ids[finding["finding_id"]] = first_nonempty(
                    finding, "hydration_dispatch_id"
                )
                attempts = finding["hydration_attempts"]
                if attempts >= max_attempts or not should_hydrate_finding(finding):
                    skipped += 1
                    if not should_hydrate_finding(finding):
                        finding["hydration_status"] = "not_applicable"
                        finding["hydration_last_error"] = ""
                        finding["hydration_updated_at"] = time.time()
                        initial_updates.append(finding)
                    continue
                if finding.get("alert_time") is None:
                    raise ValueError("hydration retry row has no valid alert_time")
                finding["hydration_attempts"] = attempts + 1
                finding["hydration_dispatch_id"] = new_hydration_dispatch_id(finding)
                finding["hydration_generation"] = new_hydration_generation(finding)
                finding["hydration_profile"] = (
                    "role_lineage" if config_bool(cfg, "include_role_lineage") else "compact"
                )
                retry_reason = bounded_text(row.get("hydration_retry_reason"), 1000)
                # Persist the retry lease before dispatch. The completion
                # action may run immediately and must never be overwritten by
                # a late "dispatched" write from this process.
                finding["hydration_status"] = "dispatched"
                finding["hydration_last_error"] = retry_reason
                finding["hydration_updated_at"] = time.time()
                initial_updates.append(finding)
                retry_candidates.append(finding)
            except Exception as exc:
                failed += 1
                log_error("hydration retry row %d failed: %s" % (rows_seen, exc))
    except ResultFileError as exc:
        log_error(str(exc))
        return 6

    if initial_updates:
        try:
            current_groups = batch_find_kv_records(
                session_key,
                "cloudlens_findings",
                [{"_key": finding["finding_id"]} for finding in initial_updates],
                limit=1,
            )
            merged_updates = []
            merged_retry_candidates = []
            retry_ids = {finding["finding_id"] for finding in retry_candidates}
            for desired, matches in zip(initial_updates, current_groups):
                if not matches:
                    failed += 1
                    log_error("hydration retry finding no longer exists: %s" % desired["finding_id"])
                    continue
                current = matches[0]
                expected_dispatch_id = expected_dispatch_ids.get(desired["finding_id"])
                current_dispatch_id = first_nonempty(current, "hydration_dispatch_id")
                if (expected_dispatch_id and current_dispatch_id
                        and expected_dispatch_id != current_dispatch_id):
                    skipped += 1
                    log("ignored stale hydration retry lease for finding %s" % desired["finding_id"])
                    continue
                for field in (
                    "hydration_status", "hydration_attempts", "hydration_dispatch_id",
                    "hydration_last_error", "hydration_updated_at",
                    "hydration_profile", "hydration_generation",
                ):
                    if field in desired:
                        current[field] = desired[field]
                current["_key"] = current.get("_key") or desired["finding_id"]
                current["finding_id"] = desired["finding_id"]
                merged_updates.append(current)
                if desired["finding_id"] in retry_ids:
                    merged_retry_candidates.append(current)
            initial_updates = merged_updates
            retry_candidates = merged_retry_candidates
            if initial_updates:
                batch_upsert_kv_records(session_key, "cloudlens_findings", initial_updates)
        except Exception as exc:
            failed += len(retry_candidates)
            log_error("hydration retry lease batch write failed; no jobs dispatched: %s" % exc)
            retry_candidates = []

    dispatch_failures = []
    for finding in retry_candidates:
        if dispatch_hydration(session_key, finding, finding.get("cl_event_id"), cfg):
            succeeded += 1
        else:
            error = finding.get("_hydration_error") or "Hydration dispatch failed after bounded REST retries."
            finding["hydration_status"] = (
                "failed" if finding["hydration_attempts"] >= max_attempts else "retry_pending"
            )
            finding["hydration_last_error"] = bounded_text(error, 1000)
            finding["hydration_updated_at"] = time.time()
            dispatch_failures.append(finding)
            failed += 1

    if dispatch_failures:
        try:
            current_rows = batch_find_kv_records(
                session_key,
                "cloudlens_findings",
                [{"_key": finding["finding_id"]} for finding in dispatch_failures],
                limit=1,
            )
            guarded_updates = []
            for failed_finding, matches in zip(dispatch_failures, current_rows):
                if not matches:
                    continue
                current = matches[0]
                if first_nonempty(current, "hydration_dispatch_id") != failed_finding["hydration_dispatch_id"]:
                    continue
                current.update({
                    "hydration_status": failed_finding["hydration_status"],
                    "hydration_last_error": failed_finding["hydration_last_error"],
                    "hydration_updated_at": failed_finding["hydration_updated_at"],
                })
                current["_key"] = current.get("_key") or failed_finding["finding_id"]
                guarded_updates.append(current)
            batch_upsert_kv_records(session_key, "cloudlens_findings", guarded_updates)
        except Exception as exc:
            log_error("hydration retry failure-state batch write failed: %s" % exc)
    log("hydration retry processed %d row(s), dispatched %d, failed %d, skipped %d" %
        (rows_seen, succeeded, failed, skipped))
    # The state is durable and another scheduled pass will retry transient
    # failures, so do not mark the internal saved-search action itself failed.
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        log_error("expected --execute as first arg")
        return 1
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError as exc:
        log_error("bad payload JSON: %s" % exc)
        return 2

    if not isinstance(payload, dict):
        log_error("payload JSON must be an object")
        return 2
    session_key = payload.get("session_key")
    if not session_key:
        log_error("no session_key in payload")
        return 3
    if rest is None:
        log_error("splunk.rest unavailable; cannot write finding")
        return 4

    cfg = payload.get("configuration", {}) or {}
    if not isinstance(cfg, dict):
        cfg = {}
    maintenance_mode = str(cfg.get("maintenance_mode") or "").strip().lower()
    internal_mode = bool(
        maintenance_mode
        or config_bool(cfg, "hydration_complete_only")
        or config_bool(cfg, "hydration_retry_only")
    )
    results_file = payload.get("results_file")
    if internal_mode and results_file and not os.path.exists(results_file):
        # Splunk does not materialize a result file for some zero-row scheduled
        # searches. That is a valid no-work run, not an alert-action failure.
        return 0
    if maintenance_mode:
        return run_retention_cleanup(payload, maintenance_mode, session_key)
    if config_bool(cfg, "hydration_complete_only"):
        return complete_hydration(payload, session_key)
    if config_bool(cfg, "hydration_retry_only"):
        return retry_pending_hydrations(payload, cfg, session_key)
    automatic_timeline = automatic_timeline_generation_enabled(session_key)
    max_findings = config_int(cfg, "max_findings_per_alert", 100, minimum=1, maximum=10000)
    max_hydrations = config_int(cfg, "max_hydrations_per_alert", 10, minimum=0, maximum=1000)
    rows_seen = 0
    written = 0
    deduplicated = 0
    hydrated = 0
    skipped = 0
    failed = 0
    candidates = []
    candidate_ids = set()
    try:
        for row in iter_result_rows(payload.get("results_file")):
            rows_seen += 1
            if len(candidates) >= max_findings:
                skipped += 1
                continue
            try:
                finding, anchor_event_id = build_finding(payload, row)
                if automatic_timeline:
                    finding["timeline_anchor_status"] = "pending"
                    finding["hydration_status"] = "pending"
                if finding["finding_id"] in candidate_ids:
                    deduplicated += 1
                    continue
                candidate_ids.add(finding["finding_id"])
                candidates.append((finding, anchor_event_id, row))
            except Exception as exc:
                failed += 1
                log_error("row %d failed; continuing with remaining alert results: %s" % (rows_seen, exc))
    except ResultFileError as exc:
        log_error(str(exc))
        return 6

    new_items = []
    if candidates:
        try:
            stored_rows = batch_find_kv_records(
                session_key,
                "cloudlens_findings",
                [stored_duplicate_query(finding) for finding, _anchor, _row in candidates],
                limit=5,
            )
            for item, matches in zip(candidates, stored_rows):
                finding = item[0]
                if matching_duplicate_finding(matches, finding):
                    deduplicated += 1
                else:
                    new_items.append(item)
        except Exception as exc:
            failed += len(candidates)
            log_error("finding duplicate batch lookup failed; no findings written: %s" % exc)

    if new_items:
        try:
            batch_upsert_kv_records(
                session_key,
                "cloudlens_dedup_claims",
                [dedup_claim_record(finding) for finding, _anchor, _row in new_items],
            )
        except Exception as exc:
            failed += len(new_items)
            log_error("dedup claim batch write failed; no findings written: %s" % exc)
            new_items = []

    dispatch_items = []
    if automatic_timeline and new_items:
        anchor_records = []
        for finding, anchor_event_id, row in new_items:
            try:
                anchor_records.append(build_alert_timeline_record(finding, row, anchor_event_id))
                finding["timeline_anchor_status"] = "ready"
            except Exception as exc:
                finding["timeline_anchor_status"] = "failed"
                log_error("alert timeline record failed for finding %s: %s" %
                          (finding.get("finding_id"), exc))
        try:
            batch_upsert_kv_records(session_key, "cloudlens_investigation", anchor_records)
        except Exception as exc:
            for finding, _anchor, _row in new_items:
                finding["timeline_anchor_status"] = "failed"
            log_error("alert timeline anchor batch write failed: %s" % exc)

        for finding, anchor_event_id, _row in new_items:
            finding["hydration_updated_at"] = time.time()
            if not should_hydrate_finding(finding):
                finding["hydration_status"] = "not_applicable"
            elif len(dispatch_items) >= max_hydrations:
                finding["hydration_status"] = "deferred"
            else:
                finding["hydration_attempts"] = 1
                finding["hydration_status"] = "dispatched"
                finding["hydration_dispatch_id"] = new_hydration_dispatch_id(finding)
                finding["hydration_generation"] = new_hydration_generation(finding)
                finding["hydration_profile"] = (
                    "role_lineage" if config_bool(cfg, "include_role_lineage") else "compact"
                )
                dispatch_items.append((finding, anchor_event_id))

    if new_items:
        try:
            batch_upsert_kv_records(
                session_key,
                "cloudlens_findings",
                [finding for finding, _anchor, _row in new_items],
            )
            written = len(new_items)
        except Exception as exc:
            failed += len(new_items)
            log_error("finding batch write failed; hydration jobs were not dispatched: %s" % exc)
            dispatch_items = []

    failed_dispatches = []
    for finding, anchor_event_id in dispatch_items:
        if dispatch_hydration(session_key, finding, anchor_event_id, cfg):
            hydrated += 1
        else:
            finding["hydration_status"] = "retry_pending"
            finding["hydration_last_error"] = bounded_text(
                finding.get("_hydration_error") or "Hydration dispatch failed after bounded REST retries.", 1000
            )
            finding["hydration_updated_at"] = time.time()
            finding.pop("_hydration_error", None)
            failed_dispatches.append(finding)

    if failed_dispatches:
        try:
            batch_upsert_kv_records(session_key, "cloudlens_findings", failed_dispatches)
        except Exception as exc:
            failed += len(failed_dispatches)
            log_error("hydration failure-state batch write failed: %s" % exc)
    if rows_seen == 0:
        log("no result rows; nothing to write")
        return 0
    if skipped:
        log("skipped %d row(s) after max_findings_per_alert=%d" % (skipped, max_findings))
    log("processed %d result row(s), wrote %d finding(s), skipped %d duplicate row(s), failed %d row(s), timeline_mode=%s, dispatched %d hydration job(s)"
        % (rows_seen, written, deduplicated, failed,
           "automatic" if automatic_timeline else "manual", hydrated))
    return 5 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

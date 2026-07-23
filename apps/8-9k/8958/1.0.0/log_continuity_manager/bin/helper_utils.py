"""Shared helpers for the Log Continuity Manager CSV MVP.

The module deliberately keeps persistence behind small functions/classes so the
same business rules can later be reused by a KV Store-backed implementation.
"""

from __future__ import annotations

import csv
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence


APP_NAME = "log_continuity_manager"

VALID_MONITORING_TYPES = {
    "host_index",
    "host_index_sourcetype",
    "host_index_source",
}

SEVERITY_THRESHOLDS_MINUTES = (
    ("7D+", 7 * 24 * 60),
    ("72H+", 72 * 60),
    ("48H+", 48 * 60),
    ("24H+", 24 * 60),
    ("12H+", 12 * 60),
    ("6H+", 6 * 60),
    ("1H+", 60),
    ("30M+", 30),
)

VALID_SEVERITIES = {name for name, _minutes in SEVERITY_THRESHOLDS_MINUTES}

DEFAULT_PERIOD_MINUTES = 60
MIN_PERIOD_MINUTES = 1
MAX_PERIOD_MINUTES = 60 * 24 * 365

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class ValidationError(ValueError):
    """Raised when user-provided lookup data is invalid."""


class NotFoundError(KeyError):
    """Raised when a requested lookup row does not exist."""


def app_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def lookup_path(filename: str) -> str:
    return os.path.join(app_root(), "lookups", filename)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime(ISO_FORMAT)


def parse_utc(value: object, field_name: str = "timestamp") -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    normalized = text
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be an ISO-8601 UTC timestamp, got {text!r}"
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def normalize_host(host: object) -> str:
    text = str(host or "").strip()
    if not text:
        raise ValidationError("host is required")
    return text.lower()


def validate_monitoring_type(monitoring_type: object) -> str:
    value = str(monitoring_type or "").strip()
    if value not in VALID_MONITORING_TYPES:
        allowed = ", ".join(sorted(VALID_MONITORING_TYPES))
        raise ValidationError(f"monitoring_type must be one of: {allowed}")
    return value


def validate_period_minutes(period_minutes: object) -> int:
    try:
        raw_value = str(period_minutes).strip()
        numeric_value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("period_minutes must be an integer") from exc

    if not numeric_value.is_integer():
        raise ValidationError("period_minutes must be an integer")
    value = int(numeric_value)

    if value < MIN_PERIOD_MINUTES or value > MAX_PERIOD_MINUTES:
        raise ValidationError(
            "period_minutes must be between "
            f"{MIN_PERIOD_MINUTES} and {MAX_PERIOD_MINUTES}"
        )
    return value


def parse_bool(value: object, default: bool = False) -> bool:
    if value is None or str(value).strip() == "":
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y", "enabled", "enable"}:
        return True
    if text in {"0", "false", "f", "no", "n", "disabled", "disable"}:
        return False
    raise ValidationError(f"boolean value expected, got {value!r}")


def clean_optional(value: object) -> str:
    return str(value or "").strip()


def require_field(row: Mapping[str, object], field_name: str) -> str:
    value = clean_optional(row.get(field_name))
    if not value:
        raise ValidationError(f"{field_name} is required")
    return value


def calculate_severity(interruption_minutes: object) -> str:
    try:
        minutes = int(float(str(interruption_minutes).strip()))
    except (TypeError, ValueError) as exc:
        raise ValidationError("interruption_minutes must be numeric") from exc

    for severity, threshold in SEVERITY_THRESHOLDS_MINUTES:
        if minutes >= threshold:
            return severity
    return ""


def target_identity(row: Mapping[str, object]) -> str:
    monitoring_type = validate_monitoring_type(row.get("monitoring_type"))
    host_key = normalize_host(row.get("host_key") or row.get("host"))
    index = require_field(row, "index")

    parts = [monitoring_type, host_key, index]
    if monitoring_type == "host_index_sourcetype":
        parts.append(require_field(row, "sourcetype"))
    elif monitoring_type == "host_index_source":
        parts.append(require_field(row, "source"))
    return "|".join(parts)


def stable_id(prefix: str, row: Mapping[str, object]) -> str:
    identity = target_identity(row)
    return f"{prefix}_{uuid.uuid5(uuid.NAMESPACE_URL, identity).hex}"


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def validate_target_shape(row: MutableMapping[str, object]) -> MutableMapping[str, object]:
    monitoring_type = validate_monitoring_type(row.get("monitoring_type"))
    row["monitoring_type"] = monitoring_type
    row["host"] = require_field(row, "host")
    row["host_key"] = normalize_host(row.get("host_key") or row.get("host"))
    row["index"] = require_field(row, "index")
    row["period_minutes"] = str(validate_period_minutes(row.get("period_minutes")))

    sourcetype = clean_optional(row.get("sourcetype"))
    source = clean_optional(row.get("source"))

    if monitoring_type == "host_index_sourcetype" and not sourcetype:
        raise ValidationError("sourcetype is required for host_index_sourcetype")
    if monitoring_type == "host_index_source" and not source:
        raise ValidationError("source is required for host_index_source")

    row["sourcetype"] = sourcetype
    row["source"] = source

    redundancy_mode = clean_optional(row.get("redundancy_mode"))
    redundancy_group = clean_optional(row.get("redundancy_group"))
    min_active_members = clean_optional(row.get("min_active_members"))
    if redundancy_mode:
        if not redundancy_group:
            raise ValidationError("redundancy_group is required when redundancy_mode is set")
        if not min_active_members:
            min_active_members = "1"
        try:
            min_members = validate_period_minutes(min_active_members)
        except ValidationError as exc:
            raise ValidationError("min_active_members must be a positive integer") from exc
        row["redundancy_mode"] = redundancy_mode
        row["redundancy_group"] = redundancy_group
        row["min_active_members"] = str(min_members)
    else:
        row["redundancy_mode"] = ""
        row["redundancy_group"] = ""
        row["min_active_members"] = ""
    return row


def read_csv_rows(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return []
        return [dict(row) for row in reader]


def write_csv_rows(
    path: str,
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, object]],
) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(
        prefix=".tmp_",
        suffix=".csv",
        dir=directory or None,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def ensure_fields(row: Mapping[str, object], fieldnames: Sequence[str]) -> Dict[str, str]:
    return {field: clean_optional(row.get(field)) for field in fieldnames}


def validate_field_name(name: str) -> None:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ValidationError(f"invalid field name: {name!r}")

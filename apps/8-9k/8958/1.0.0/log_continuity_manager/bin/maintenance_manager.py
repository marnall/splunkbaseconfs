"""Maintenance window management and matching helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Mapping, MutableMapping, Optional

from helper_utils import (
    NotFoundError,
    ValidationError,
    clean_optional,
    format_utc,
    lookup_path,
    new_id,
    normalize_host,
    parse_bool,
    parse_utc,
    read_csv_rows,
    utc_now,
    validate_monitoring_type,
    write_csv_rows,
)


MAINTENANCE_FIELDS = [
    "window_id",
    "enabled",
    "target_id",
    "monitoring_type",
    "host",
    "host_key",
    "index",
    "sourcetype",
    "source",
    "start_time",
    "end_time",
    "reason",
    "created_at",
    "updated_at",
]


class MaintenanceManager:
    """Manage maintenance windows in a lookup CSV."""

    def __init__(self, csv_path: Optional[str] = None) -> None:
        self.csv_path = csv_path or lookup_path("maintenance_windows.csv")

    def list_windows(self, include_disabled: bool = True) -> List[Dict[str, str]]:
        rows = read_csv_rows(self.csv_path)
        if include_disabled:
            return rows
        return [row for row in rows if parse_bool(row.get("enabled"), default=True)]

    def get_window(self, window_id: str) -> Dict[str, str]:
        window_id = clean_optional(window_id)
        for row in self.list_windows():
            if row.get("window_id") == window_id:
                return row
        raise NotFoundError(f"window_id not found: {window_id}")

    def create_window(self, window: Mapping[str, object]) -> Dict[str, str]:
        now = format_utc(utc_now())
        row: MutableMapping[str, object] = dict(window)
        row.setdefault("enabled", "1")
        row.setdefault("window_id", new_id("window"))
        row.setdefault("created_at", now)
        row["updated_at"] = now
        row = self._validate_window(row)
        rows = self.list_windows()
        if any(existing.get("window_id") == row.get("window_id") for existing in rows):
            raise ValidationError(f"window_id already exists: {row.get('window_id')}")
        rows.append(self._serialize(row))
        self._write(rows)
        return self.get_window(str(row["window_id"]))

    def update_window(self, window_id: str, updates: Mapping[str, object]) -> Dict[str, str]:
        rows = self.list_windows()
        window_id = clean_optional(window_id)
        for idx, existing in enumerate(rows):
            if existing.get("window_id") != window_id:
                continue
            merged: MutableMapping[str, object] = dict(existing)
            merged.update(dict(updates))
            merged["window_id"] = window_id
            merged["created_at"] = existing.get("created_at", "")
            merged["updated_at"] = format_utc(utc_now())
            rows[idx] = self._serialize(self._validate_window(merged))
            self._write(rows)
            return self.get_window(window_id)
        raise NotFoundError(f"window_id not found: {window_id}")

    def delete_window(self, window_id: str) -> Dict[str, str]:
        rows = self.list_windows()
        window_id = clean_optional(window_id)
        remaining = [row for row in rows if row.get("window_id") != window_id]
        if len(remaining) == len(rows):
            raise NotFoundError(f"window_id not found: {window_id}")
        self._write(remaining)
        return {"window_id": window_id, "deleted": "1"}

    def active_windows(
        self,
        target: Mapping[str, object],
        at_time: Optional[datetime] = None,
    ) -> List[Dict[str, str]]:
        check_time = at_time or utc_now()
        return [
            window
            for window in self.list_windows(include_disabled=False)
            if self.window_matches_target(window, target)
            and self.window_contains_time(window, check_time)
        ]

    def is_in_maintenance(
        self,
        target: Mapping[str, object],
        at_time: Optional[datetime] = None,
    ) -> bool:
        return bool(self.active_windows(target, at_time=at_time))

    def window_contains_time(
        self,
        window: Mapping[str, object],
        at_time: Optional[datetime] = None,
    ) -> bool:
        if not parse_bool(window.get("enabled"), default=True):
            return False
        check_time = at_time or utc_now()
        if check_time.tzinfo is None:
            check_time = check_time.replace(tzinfo=utc_now().tzinfo)
        start = parse_utc(window.get("start_time"), "start_time")
        end = parse_utc(window.get("end_time"), "end_time")
        if start is None or end is None:
            raise ValidationError("maintenance windows require start_time and end_time")
        return start <= check_time <= end

    def window_matches_target(
        self,
        window: Mapping[str, object],
        target: Mapping[str, object],
    ) -> bool:
        target_id = clean_optional(window.get("target_id"))
        if target_id and target_id == clean_optional(target.get("target_id")):
            return True

        checks = {
            "monitoring_type": clean_optional(target.get("monitoring_type")),
            "host_key": clean_optional(target.get("host_key") or target.get("host")).lower(),
            "index": clean_optional(target.get("index")),
            "sourcetype": clean_optional(target.get("sourcetype")),
            "source": clean_optional(target.get("source")),
        }

        for field, target_value in checks.items():
            window_value = clean_optional(window.get(field))
            if field == "host_key" and not window_value and clean_optional(window.get("host")):
                window_value = normalize_host(window.get("host"))
            if window_value and window_value != target_value:
                return False
        return any(clean_optional(window.get(field)) for field in checks)

    def _validate_window(
        self,
        row: MutableMapping[str, object],
    ) -> MutableMapping[str, object]:
        row["enabled"] = "1" if parse_bool(row.get("enabled"), True) else "0"
        if clean_optional(row.get("monitoring_type")):
            row["monitoring_type"] = validate_monitoring_type(row.get("monitoring_type"))
        if clean_optional(row.get("host")) or clean_optional(row.get("host_key")):
            row["host_key"] = normalize_host(row.get("host_key") or row.get("host"))

        start = parse_utc(row.get("start_time"), "start_time")
        end = parse_utc(row.get("end_time"), "end_time")
        if start is None or end is None:
            raise ValidationError("start_time and end_time are required")
        if end <= start:
            raise ValidationError("end_time must be after start_time")

        row["start_time"] = format_utc(start)
        row["end_time"] = format_utc(end)
        if not clean_optional(row.get("target_id")) and not clean_optional(row.get("host_key")):
            raise ValidationError("maintenance window requires target_id, host, or host_key")
        return row

    def _serialize(self, row: Mapping[str, object]) -> Dict[str, str]:
        return {field: clean_optional(row.get(field)) for field in MAINTENANCE_FIELDS}

    def _write(self, rows: List[Mapping[str, object]]) -> None:
        write_csv_rows(self.csv_path, MAINTENANCE_FIELDS, rows)

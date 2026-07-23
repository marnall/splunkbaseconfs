"""CSV-backed target management for Log Continuity Manager."""

from __future__ import annotations

from typing import Dict, List, Mapping, MutableMapping, Optional

from helper_utils import (
    NotFoundError,
    ValidationError,
    clean_optional,
    format_utc,
    lookup_path,
    new_id,
    parse_bool,
    read_csv_rows,
    stable_id,
    utc_now,
    validate_target_shape,
    write_csv_rows,
)


TARGET_FIELDS = [
    "target_id",
    "enabled",
    "monitoring_type",
    "host",
    "host_key",
    "index",
    "sourcetype",
    "source",
    "period_minutes",
    "owner",
    "description",
    "redundancy_mode",
    "redundancy_group",
    "min_active_members",
    "created_at",
    "updated_at",
]


class TargetManager:
    """Manage monitoring targets in a lookup CSV.

    The class is intentionally storage-light: callers can replace the CSV read
    and write behavior with a KV Store adapter later while preserving validation.
    """

    def __init__(self, csv_path: Optional[str] = None) -> None:
        self.csv_path = csv_path or lookup_path("monitoring_targets.csv")

    def list_targets(self, include_disabled: bool = True) -> List[Dict[str, str]]:
        rows = read_csv_rows(self.csv_path)
        if include_disabled:
            return rows
        return [row for row in rows if parse_bool(row.get("enabled"), default=True)]

    def get_target(self, target_id: str) -> Dict[str, str]:
        target_id = clean_optional(target_id)
        for row in self.list_targets():
            if row.get("target_id") == target_id:
                return row
        raise NotFoundError(f"target_id not found: {target_id}")

    def create_target(self, target: Mapping[str, object]) -> Dict[str, str]:
        now = format_utc(utc_now())
        row: MutableMapping[str, object] = dict(target)
        row.setdefault("enabled", "1")
        row.setdefault("period_minutes", "60")
        row.setdefault("created_at", now)
        row["updated_at"] = now
        validate_target_shape(row)

        requested_id = clean_optional(row.get("target_id"))
        row["target_id"] = requested_id or stable_id("target", row)
        self._assert_unique(row)

        rows = self.list_targets()
        rows.append(self._serialize(row))
        self._write(rows)
        return self.get_target(str(row["target_id"]))

    def update_target(self, target_id: str, updates: Mapping[str, object]) -> Dict[str, str]:
        rows = self.list_targets()
        target_id = clean_optional(target_id)

        for idx, existing in enumerate(rows):
            if existing.get("target_id") != target_id:
                continue

            merged: MutableMapping[str, object] = dict(existing)
            merged.update(dict(updates))
            merged["target_id"] = target_id
            merged["created_at"] = existing.get("created_at", "")
            merged["updated_at"] = format_utc(utc_now())
            validate_target_shape(merged)
            self._assert_unique(merged, ignore_target_id=target_id)
            rows[idx] = self._serialize(merged)
            self._write(rows)
            return self.get_target(target_id)

        raise NotFoundError(f"target_id not found: {target_id}")

    def upsert_target(self, target: Mapping[str, object]) -> Dict[str, str]:
        target_id = clean_optional(target.get("target_id"))
        if target_id:
            try:
                self.get_target(target_id)
            except NotFoundError:
                return self.create_target(target)
            return self.update_target(target_id, target)

        row: MutableMapping[str, object] = dict(target)
        row.setdefault("period_minutes", "60")
        validate_target_shape(row)
        row["target_id"] = stable_id("target", row)
        try:
            self.get_target(str(row["target_id"]))
        except NotFoundError:
            return self.create_target(row)
        return self.update_target(str(row["target_id"]), row)

    def delete_target(self, target_id: str) -> Dict[str, str]:
        rows = self.list_targets()
        target_id = clean_optional(target_id)
        remaining = [row for row in rows if row.get("target_id") != target_id]
        if len(remaining) == len(rows):
            raise NotFoundError(f"target_id not found: {target_id}")
        self._write(remaining)
        return {"target_id": target_id, "deleted": "1"}

    def set_enabled(self, target_id: str, enabled: object) -> Dict[str, str]:
        enabled_value = "1" if parse_bool(enabled) else "0"
        return self.update_target(target_id, {"enabled": enabled_value})

    def _assert_unique(
        self,
        row: Mapping[str, object],
        ignore_target_id: Optional[str] = None,
    ) -> None:
        candidate = stable_id("target", row)
        for existing in self.list_targets():
            if ignore_target_id and existing.get("target_id") == ignore_target_id:
                continue
            try:
                existing_key = stable_id("target", existing)
            except ValidationError:
                continue
            if existing.get("target_id") == row.get("target_id") or existing_key == candidate:
                raise ValidationError("target already exists with the same identity")

    def _serialize(self, row: Mapping[str, object]) -> Dict[str, str]:
        serialized = {field: clean_optional(row.get(field)) for field in TARGET_FIELDS}
        serialized["enabled"] = "1" if parse_bool(serialized.get("enabled"), True) else "0"
        return serialized

    def _write(self, rows: List[Mapping[str, object]]) -> None:
        write_csv_rows(self.csv_path, TARGET_FIELDS, rows)


def create_target(target: Mapping[str, object]) -> Dict[str, str]:
    return TargetManager().create_target(target)


def update_target(target_id: str, updates: Mapping[str, object]) -> Dict[str, str]:
    return TargetManager().update_target(target_id, updates)


def delete_target(target_id: str) -> Dict[str, str]:
    return TargetManager().delete_target(target_id)

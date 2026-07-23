"""Interruption status calculation for monitored log continuity targets."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from helper_utils import (
    ValidationError,
    calculate_severity,
    clean_optional,
    format_utc,
    lookup_path,
    parse_bool,
    parse_utc,
    read_csv_rows,
    target_identity,
    utc_now,
    validate_period_minutes,
    validate_target_shape,
    write_csv_rows,
)
from maintenance_manager import MaintenanceManager
from target_manager import TARGET_FIELDS, TargetManager


STATUS_FIELDS = [
    "target_id",
    "enabled",
    "customer",
    "environment",
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
    "target_interrupted",
    "group_active_members",
    "group_min_active_members",
    "group_status",
    "suppressed_by_redundancy",
    "effective_is_interrupted",
    "effective_status",
    "last_event_time",
    "last_checked_at",
    "expected_after",
    "status",
    "is_interrupted",
    "in_maintenance",
    "interruption_minutes",
    "gap_min",
    "severity",
    "violation",
    "last_event_ts",
    "updated_at",
    "active_window_ids",
    "message",
]


class InterruptionEngine:
    """Calculate continuity status from target and observation lookups."""

    def __init__(
        self,
        target_manager: Optional[TargetManager] = None,
        maintenance_manager: Optional[MaintenanceManager] = None,
        status_csv_path: Optional[str] = None,
    ) -> None:
        self.target_manager = target_manager or TargetManager()
        self.maintenance_manager = maintenance_manager or MaintenanceManager()
        self.status_csv_path = status_csv_path or lookup_path("monitoring_status.csv")

    def calculate_all(
        self,
        observations: Optional[Iterable[Mapping[str, object]]] = None,
        at_time: Optional[datetime] = None,
        persist: bool = False,
    ) -> List[Dict[str, str]]:
        observation_index = self._index_observations(observations)
        results = [
            self.calculate_target_status(target, observation_index, at_time=at_time)
            for target in self.target_manager.list_targets(include_disabled=True)
        ]
        results = self._apply_redundancy_suppression(results)
        if persist:
            write_csv_rows(self.status_csv_path, STATUS_FIELDS, results)
        return results

    def calculate_target_status(
        self,
        target: Mapping[str, object],
        observations: Optional[Mapping[str, Mapping[str, object]]] = None,
        at_time: Optional[datetime] = None,
    ) -> Dict[str, str]:
        row = dict(target)
        validate_target_shape(row)

        check_time = at_time or utc_now()
        period = validate_period_minutes(row.get("period_minutes"))
        enabled = parse_bool(row.get("enabled"), default=True)
        observation = self._find_observation(row, observations or {})
        last_event_time = parse_utc(
            observation.get("last_event_time") if observation else row.get("last_event_time"),
            "last_event_time",
        )

        active_windows = self.maintenance_manager.active_windows(row, at_time=check_time)
        in_maintenance = bool(active_windows)

        status, interrupted, interruption_minutes, message = self._status_from_times(
            enabled=enabled,
            in_maintenance=in_maintenance,
            period_minutes=period,
            last_event_time=last_event_time,
            check_time=check_time,
        )

        expected_after = ""
        if last_event_time is not None:
            expected_after = format_utc(
                datetime.fromtimestamp(
                    last_event_time.timestamp() + (period * 60),
                    tz=last_event_time.tzinfo,
                )
            )

        return {
            "target_id": clean_optional(row.get("target_id")),
            "enabled": "1" if enabled else "0",
            "customer": clean_optional(row.get("customer")),
            "environment": clean_optional(row.get("environment")),
            "monitoring_type": clean_optional(row.get("monitoring_type")),
            "host": clean_optional(row.get("host")),
            "host_key": clean_optional(row.get("host_key")),
            "index": clean_optional(row.get("index")),
            "sourcetype": clean_optional(row.get("sourcetype")),
            "source": clean_optional(row.get("source")),
            "period_minutes": str(period),
            "owner": clean_optional(row.get("owner")),
            "description": clean_optional(row.get("description")),
            "redundancy_mode": clean_optional(row.get("redundancy_mode")),
            "redundancy_group": clean_optional(row.get("redundancy_group")),
            "min_active_members": clean_optional(row.get("min_active_members")),
            "target_interrupted": "1" if interrupted else "0",
            "group_active_members": "",
            "group_min_active_members": "",
            "group_status": "",
            "suppressed_by_redundancy": "0",
            "effective_is_interrupted": "1" if interrupted else "0",
            "effective_status": status,
            "last_event_time": format_utc(last_event_time) if last_event_time else "",
            "last_checked_at": format_utc(check_time),
            "expected_after": expected_after,
            "status": status,
            "is_interrupted": "1" if interrupted else "0",
            "in_maintenance": "1" if in_maintenance else "0",
            "interruption_minutes": str(interruption_minutes),
            "gap_min": str(interruption_minutes),
            "severity": calculate_severity(interruption_minutes) if interrupted else "",
            "violation": "1" if interrupted else "0",
            "last_event_ts": format_utc(last_event_time) if last_event_time else "",
            "updated_at": format_utc(check_time),
            "active_window_ids": ";".join(
                clean_optional(window.get("window_id")) for window in active_windows
            ),
            "message": message,
        }

    def _apply_redundancy_suppression(self, rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
        groups: Dict[str, List[Dict[str, str]]] = {}
        for row in rows:
            group = clean_optional(row.get("redundancy_group"))
            if group:
                groups.setdefault(group, []).append(row)

        for group_rows in groups.values():
            min_active = 1
            for row in group_rows:
                value = clean_optional(row.get("min_active_members"))
                if value:
                    try:
                        min_active = max(min_active, int(float(value)))
                    except ValueError:
                        min_active = max(min_active, 1)

            active_members = sum(
                1
                for row in group_rows
                if row.get("status") == "healthy" and row.get("target_interrupted") != "1"
            )
            group_status = "healthy" if active_members >= min_active else "interrupted"

            for row in group_rows:
                target_interrupted = row.get("target_interrupted") or row.get("is_interrupted") or "0"
                suppressed = "1" if target_interrupted == "1" and group_status == "healthy" else "0"
                effective_interrupted = "0" if suppressed == "1" else target_interrupted
                if suppressed == "1":
                    effective_status = "suppressed"
                    row["message"] = (
                        "Target interruption suppressed because redundancy group is healthy."
                    )
                elif effective_interrupted == "1":
                    effective_status = "interrupted"
                elif row.get("status") == "healthy":
                    effective_status = "healthy"
                else:
                    effective_status = row.get("status", "")

                row["group_active_members"] = str(active_members)
                row["group_min_active_members"] = str(min_active)
                row["group_status"] = group_status
                row["suppressed_by_redundancy"] = suppressed
                row["effective_is_interrupted"] = effective_interrupted
                row["effective_status"] = effective_status
                row["violation"] = effective_interrupted

        return rows

    def load_previous_status(self) -> List[Dict[str, str]]:
        return read_csv_rows(self.status_csv_path)

    def observations_from_status_lookup(self) -> List[Dict[str, str]]:
        return [
            {
                "target_id": row.get("target_id", ""),
                "monitoring_type": row.get("monitoring_type", ""),
                "host": row.get("host", ""),
                "host_key": row.get("host_key", ""),
                "index": row.get("index", ""),
                "sourcetype": row.get("sourcetype", ""),
                "source": row.get("source", ""),
                "last_event_time": row.get("last_event_time", ""),
            }
            for row in self.load_previous_status()
        ]

    def _status_from_times(
        self,
        enabled: bool,
        in_maintenance: bool,
        period_minutes: int,
        last_event_time: Optional[datetime],
        check_time: datetime,
    ) -> Tuple[str, bool, int, str]:
        if not enabled:
            return "disabled", False, 0, "Target is disabled."
        if in_maintenance:
            return "maintenance", False, 0, "Target is inside an active maintenance window."
        if last_event_time is None:
            return "unknown", True, period_minutes, "No last_event_time is available."

        elapsed_minutes = int(max(0, (check_time - last_event_time).total_seconds()) // 60)
        interruption_minutes = max(0, elapsed_minutes - period_minutes)
        if interruption_minutes > 0:
            return (
                "interrupted",
                True,
                interruption_minutes,
                "No matching event has arrived within the expected period.",
            )
        return "healthy", False, 0, "Events are arriving within the expected period."

    def _index_observations(
        self,
        observations: Optional[Iterable[Mapping[str, object]]],
    ) -> Dict[str, Mapping[str, object]]:
        if observations is None:
            observations = self.observations_from_status_lookup()

        indexed: Dict[str, Mapping[str, object]] = {}
        for observation in observations:
            target_id = clean_optional(observation.get("target_id"))
            if target_id:
                indexed[f"id:{target_id}"] = observation
            try:
                indexed[f"identity:{target_identity(observation)}"] = observation
            except ValidationError:
                continue
        return indexed

    def _find_observation(
        self,
        target: Mapping[str, object],
        observations: Mapping[str, Mapping[str, object]],
    ) -> Optional[Mapping[str, object]]:
        target_id = clean_optional(target.get("target_id"))
        if target_id and f"id:{target_id}" in observations:
            return observations[f"id:{target_id}"]
        return observations.get(f"identity:{target_identity(target)}")

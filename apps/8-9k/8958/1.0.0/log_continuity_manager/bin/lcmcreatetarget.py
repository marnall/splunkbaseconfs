#!/usr/bin/env python
"""Create one monitoring target from a Splunk search result row."""

from __future__ import annotations

import splunk.Intersplunk as intersplunk

from helper_utils import clean_optional
from target_manager import TargetManager


TARGET_INPUT_FIELDS = [
    "enabled",
    "monitoring_type",
    "host",
    "index",
    "sourcetype",
    "source",
    "period_minutes",
    "owner",
    "description",
    "redundancy_mode",
    "redundancy_group",
    "min_active_members",
]


def main() -> None:
    try:
        results, _unused, _settings = intersplunk.getOrganizedResults()
        if not results:
            intersplunk.outputResults(
                [{"status": "blocked", "message": "No target data was submitted."}]
            )
            return

        manager = TargetManager()
        output = []
        for submitted in results:
            base_output = {
                "host": clean_optional(submitted.get("host")),
                "monitoring_type": clean_optional(submitted.get("monitoring_type")),
                "index": clean_optional(submitted.get("index")),
                "sourcetype": clean_optional(submitted.get("sourcetype")),
                "source": clean_optional(submitted.get("source")),
                "live_event_count": clean_optional(submitted.get("live_event_count")),
                "live_last_seen": clean_optional(submitted.get("live_last_seen")),
                "validation_time_range": clean_optional(submitted.get("validation_time_range")),
                "redundancy_mode": clean_optional(submitted.get("redundancy_mode")),
                "redundancy_group": clean_optional(submitted.get("redundancy_group")),
                "min_active_members": clean_optional(submitted.get("min_active_members")),
            }

            validation_error = clean_optional(submitted.get("validation_error"))
            if validation_error:
                base_output.update({"status": "blocked", "message": validation_error})
                output.append(base_output)
                continue

            try:
                live_count = int(float(base_output["live_event_count"] or "0"))
            except ValueError:
                live_count = 0
            if live_count < 1:
                base_output.update({
                    "status": "blocked",
                    "message": "No matching live data found in the selected validation time range.",
                    "live_event_count": base_output["live_event_count"] or "0",
                })
                output.append(base_output)
                continue

            target = {
                field: clean_optional(submitted.get(field))
                for field in TARGET_INPUT_FIELDS
            }
            try:
                created = manager.create_target(target)
            except Exception as exc:
                base_output.update({"status": "blocked", "message": str(exc)})
                output.append(base_output)
                continue

            base_output.update({
                "status": "created",
                "message": "Target created in monitoring_targets.csv.",
                "target_id": created.get("target_id", ""),
                "host_key": created.get("host_key", ""),
                "redundancy_mode": created.get("redundancy_mode", ""),
                "redundancy_group": created.get("redundancy_group", ""),
                "min_active_members": created.get("min_active_members", ""),
            })
            output.append(base_output)

        intersplunk.outputResults(output)
    except Exception as exc:
        intersplunk.outputResults(
            [{"status": "blocked", "message": str(exc)}]
        )


if __name__ == "__main__":
    main()

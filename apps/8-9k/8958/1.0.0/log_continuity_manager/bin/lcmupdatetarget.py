#!/usr/bin/env python
"""Update one existing monitoring target from a Splunk search result row."""

from __future__ import annotations

import splunk.Intersplunk as intersplunk

from helper_utils import clean_optional
from target_manager import TargetManager


VALID_ACTIONS = {
    "enable",
    "disable",
    "update_period",
    "update_owner",
    "set_redundancy",
    "clear_redundancy",
    "update_min_active_members",
}


def main() -> None:
    try:
        results, _unused, _settings = intersplunk.getOrganizedResults()
        if not results:
            intersplunk.outputResults(
                [{"status": "blocked", "message": "No update request was submitted."}]
            )
            return

        manager = TargetManager()
        output = []
        for submitted in results:
            target_id = clean_optional(submitted.get("target_id"))
            action = clean_optional(submitted.get("action"))
            period_minutes = clean_optional(submitted.get("period_minutes"))
            owner = clean_optional(submitted.get("owner"))
            redundancy_group = clean_optional(submitted.get("redundancy_group"))
            redundancy_mode = clean_optional(submitted.get("redundancy_mode"))
            min_active_members = clean_optional(submitted.get("min_active_members"))
            validation_error = clean_optional(submitted.get("validation_error"))

            if validation_error:
                output.append({
                    "status": "blocked",
                    "message": validation_error,
                    "target_id": target_id,
                })
                continue
            if not target_id or target_id == "__none__":
                output.append({
                    "status": "blocked",
                    "message": "Select at least one target_id to update.",
                    "target_id": target_id,
                })
                continue
            if action not in VALID_ACTIONS:
                output.append({
                    "status": "blocked",
                    "message": f"Unsupported action: {action}",
                    "target_id": target_id,
                })
                continue

            try:
                if action == "enable":
                    updated = manager.set_enabled(target_id, "1")
                    message = "Target enabled."
                elif action == "disable":
                    updated = manager.set_enabled(target_id, "0")
                    message = "Target disabled."
                elif action == "update_period":
                    if not period_minutes:
                        output.append({
                            "status": "blocked",
                            "message": "period_minutes is required for update period.",
                            "target_id": target_id,
                        })
                        continue
                    updated = manager.update_target(target_id, {"period_minutes": period_minutes})
                    message = "Target period_minutes updated."
                elif action == "update_owner":
                    if not owner:
                        output.append({
                            "status": "blocked",
                            "message": "owner is required for update owner.",
                            "target_id": target_id,
                        })
                        continue
                    updated = manager.update_target(target_id, {"owner": owner})
                    message = "Target owner updated."
                elif action == "set_redundancy":
                    if not redundancy_group:
                        output.append({
                            "status": "blocked",
                            "message": "redundancy_group is required for set redundancy settings.",
                            "target_id": target_id,
                        })
                        continue
                    if not redundancy_mode:
                        output.append({
                            "status": "blocked",
                            "message": "redundancy_mode is required for set redundancy settings.",
                            "target_id": target_id,
                        })
                        continue
                    if not min_active_members:
                        output.append({
                            "status": "blocked",
                            "message": "min_active_members is required for set redundancy settings.",
                            "target_id": target_id,
                        })
                        continue
                    updated = manager.update_target(target_id, {
                        "redundancy_group": redundancy_group,
                        "redundancy_mode": redundancy_mode,
                        "min_active_members": min_active_members,
                    })
                    message = "Target redundancy settings updated."
                elif action == "clear_redundancy":
                    updated = manager.update_target(target_id, {
                        "redundancy_group": "",
                        "redundancy_mode": "",
                        "min_active_members": "",
                    })
                    message = "Target redundancy settings cleared."
                else:
                    if not min_active_members:
                        output.append({
                            "status": "blocked",
                            "message": "min_active_members is required for update minimum active members.",
                            "target_id": target_id,
                        })
                        continue
                    current = manager.get_target(target_id)
                    if not clean_optional(current.get("redundancy_mode")) or not clean_optional(current.get("redundancy_group")):
                        output.append({
                            "status": "blocked",
                            "message": "Target must already have redundancy settings before updating min_active_members.",
                            "target_id": target_id,
                        })
                        continue
                    updated = manager.update_target(target_id, {"min_active_members": min_active_members})
                    message = "Target min_active_members updated."
            except Exception as exc:
                output.append({
                    "status": "blocked",
                    "message": str(exc),
                    "target_id": target_id,
                })
                continue

            output.append({
                "status": "updated",
                "message": message,
                "target_id": updated.get("target_id", ""),
                "enabled": updated.get("enabled", ""),
                "period_minutes": updated.get("period_minutes", ""),
                "owner": updated.get("owner", ""),
                "redundancy_mode": updated.get("redundancy_mode", ""),
                "redundancy_group": updated.get("redundancy_group", ""),
                "min_active_members": updated.get("min_active_members", ""),
                "monitoring_type": updated.get("monitoring_type", ""),
                "host": updated.get("host", ""),
                "host_key": updated.get("host_key", ""),
                "index": updated.get("index", ""),
                "sourcetype": updated.get("sourcetype", ""),
                "source": updated.get("source", ""),
                "updated_at": updated.get("updated_at", ""),
            })

        intersplunk.outputResults(output)
    except Exception as exc:
        intersplunk.outputResults(
            [{"status": "blocked", "message": str(exc)}]
        )


if __name__ == "__main__":
    main()

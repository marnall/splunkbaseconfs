"""Change detection for DNS infrastructure baselines.

Compares current vs. previous snapshots and produces change events with
sourcetype ``whisper:attack_surface_change``. High-priority changes
(nameserver, wildcard) generate risk events for ES integration.
"""

from __future__ import annotations

import json
import time
from typing import Any

from whisper_logging import get_logger

logger = get_logger("change_detector")

# Event output constants
CHANGE_SOURCETYPE = "whisper:attack_surface_change"

# Change types
CHANGE_ADDED = "added"
CHANGE_REMOVED = "removed"

# Record types considered high-priority for risk events
HIGH_PRIORITY_RECORD_TYPES = {"NS", "MX"}

# Risk scores by change type and record type
RISK_SCORES: dict[str, dict[str, int]] = {
    "NS": {"added": 60, "removed": 50},
    "MX": {"added": 40, "removed": 30},
    "A": {"added": 20, "removed": 20},
    "CNAME": {"added": 30, "removed": 25},
    "SUBDOMAIN": {"added": 15, "removed": 10},
}

DEFAULT_RISK_SCORE = 10


def detect_changes(
    previous: dict[str, dict[str, list[str]]],
    current: dict[str, dict[str, list[str]]],
) -> list[dict[str, Any]]:
    """Compare two snapshots and detect infrastructure changes.

    Args:
        previous: Previous snapshot from checkpoint.
        current: Current snapshot from latest collection.

    Returns:
        List of change event dictionaries.
    """
    changes: list[dict[str, Any]] = []
    detected_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # All domains across both snapshots
    all_domains = sorted(set(list(previous.keys()) + list(current.keys())))

    for domain in all_domains:
        prev_records = previous.get(domain, {})
        curr_records = current.get(domain, {})

        # All record types across both snapshots for this domain
        all_types = sorted(set(list(prev_records.keys()) + list(curr_records.keys())))

        for record_type in all_types:
            prev_values = set(prev_records.get(record_type, []))
            curr_values = set(curr_records.get(record_type, []))

            # Detect additions
            for value in sorted(curr_values - prev_values):
                change_event = {
                    "domain": domain,
                    "record_type": record_type,
                    "change_type": CHANGE_ADDED,
                    "old_value": None,
                    "new_value": value,
                    "detected_at": detected_at,
                }
                change_event["risk_score"] = get_risk_score(change_event)
                changes.append(change_event)

            # Detect removals
            for value in sorted(prev_values - curr_values):
                change_event = {
                    "domain": domain,
                    "record_type": record_type,
                    "change_type": CHANGE_REMOVED,
                    "old_value": value,
                    "new_value": None,
                    "detected_at": detected_at,
                }
                change_event["risk_score"] = get_risk_score(change_event)
                changes.append(change_event)

    return changes


def is_high_priority(change: dict[str, Any]) -> bool:
    """Check whether a change event qualifies as high-priority.

    High-priority changes include nameserver and mail server changes,
    as well as wildcard DNS additions.

    Args:
        change: Change event dictionary.

    Returns:
        True if the change is high-priority.
    """
    record_type = change.get("record_type", "")
    if record_type in HIGH_PRIORITY_RECORD_TYPES:
        return True

    # Wildcard record additions
    new_value = change.get("new_value", "") or ""
    return new_value.startswith("*.") and change.get("change_type") == CHANGE_ADDED


def get_risk_score(change: dict[str, Any]) -> int:
    """Calculate a risk score for a change event.

    Args:
        change: Change event dictionary.

    Returns:
        Integer risk score.
    """
    record_type = change.get("record_type", "")
    change_type = change.get("change_type", "")
    scores = RISK_SCORES.get(record_type, {})
    return scores.get(change_type, DEFAULT_RISK_SCORE)


def build_risk_event(change: dict[str, Any]) -> dict[str, Any]:
    """Build an ES-compatible risk event from a high-priority change.

    Args:
        change: Change event dictionary.

    Returns:
        Risk event dictionary for ES risk index.
    """
    domain = change.get("domain", "")
    record_type = change.get("record_type", "")
    change_type = change.get("change_type", "")
    new_value = change.get("new_value", "")
    old_value = change.get("old_value", "")

    detail = new_value if change_type == CHANGE_ADDED else old_value
    risk_score = get_risk_score(change)

    return {
        "risk_score": risk_score,
        "risk_object": domain,
        "risk_object_type": "other",
        "risk_message": (
            f"DNS infrastructure change detected: {record_type} record {change_type} for {domain} ({detail})"
        ),
        "threat_object": detail,
        "threat_object_type": "dns",
        "source": "whisper_security",
        "search_name": "Whisper - DNS Infrastructure Change Detection",
        "mitre_attack": [
            {
                "technique_id": "T1584",
                "technique": "Compromise Infrastructure",
                "tactic": ["resource-development"],
            }
        ],
    }


def format_change_event(change: dict[str, Any]) -> str:
    """Format a change event as a JSON string.

    Args:
        change: Change event dictionary.

    Returns:
        JSON string for Splunk ingestion.
    """
    return json.dumps(change, default=str)


def format_change_summary(
    total_changes: int,
    high_priority_count: int,
    domains_affected: int,
) -> str:
    """Format a summary event for change detection results.

    Args:
        total_changes: Total number of changes detected.
        high_priority_count: Number of high-priority changes.
        domains_affected: Number of domains with changes.

    Returns:
        JSON string for Splunk event ingestion.
    """
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_changes": total_changes,
        "high_priority_changes": high_priority_count,
        "domains_affected": domains_affected,
    }
    return json.dumps(event, default=str)

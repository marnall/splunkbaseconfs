"""Multi-tenant attack surface monitoring input.

Wraps the baseline collection and change detection modules to support
multiple client tenants with separate domain lists, indexes, schedules,
and optional per-tenant API keys. Each input instance represents one
client configuration.
"""

from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING, Any

from whisper_baseline_input import (
    build_snapshot,
    collect_baseline,
    parse_domain_list,
)
from whisper_change_detector import (
    build_risk_event,
    detect_changes,
    is_high_priority,
)
from whisper_logging import get_logger

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient

logger = get_logger("multitenant_input")

# Event output constants
SOURCETYPE = "whisper:attack_surface"
CHANGE_SOURCETYPE = "whisper:attack_surface_change"
SUMMARY_SOURCETYPE = "whisper:attack_surface_summary"

# Defaults
DEFAULT_INTERVAL = 86400  # 24 hours
MIN_INTERVAL = 3600  # 1 hour
MAX_INTERVAL = 604800  # 7 days
DEFAULT_MAX_DOMAINS = 500


def validate_tenant_config(config: dict[str, Any]) -> list[str]:
    """Validate a tenant configuration.

    Args:
        config: Tenant configuration dictionary with keys:
            client_id, domains, index, api_key, etc.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: list[str] = []

    if not config.get("client_id", "").strip():
        errors.append("client_id is required")

    domains = config.get("domains", "")
    if not domains or not parse_domain_list(domains):
        errors.append("at least one domain is required")

    max_domains = config.get("max_domains", DEFAULT_MAX_DOMAINS)
    if max_domains < 1 or max_domains > 10000:
        errors.append("max_domains must be between 1 and 10000")

    return errors


def collect_tenant_baseline(
    client: WhisperAPIClient,
    config: dict[str, Any],
    checkpoint_dir: str,
) -> dict[str, Any]:
    """Collect DNS baseline for a single tenant.

    Args:
        client: Configured WhisperAPIClient (with tenant's API key).
        config: Tenant configuration with client_id, domains, index, etc.
        checkpoint_dir: Directory for checkpoint files.

    Returns:
        Dictionary with events, changes, risk_events, and stats.
    """
    client_id = config["client_id"].strip()
    domains = parse_domain_list(config.get("domains", ""))
    max_domains = config.get("max_domains", DEFAULT_MAX_DOMAINS)
    domains = domains[:max_domains]

    start_time = time.monotonic()

    # Load previous checkpoint
    prev_checkpoint = load_tenant_checkpoint(checkpoint_dir, client_id)
    prev_snapshot = prev_checkpoint.get("snapshot", {})

    # Collect current baseline
    events, collection_stats = collect_baseline(client, domains)

    # Tag events with client_id
    for event in events:
        event["client_id"] = client_id

    # Build current snapshot and detect changes
    current_snapshot = build_snapshot(events)
    changes = []
    risk_events = []

    if prev_snapshot:
        changes = detect_changes(prev_snapshot, current_snapshot)
        for change in changes:
            change["client_id"] = client_id
            if is_high_priority(change):
                risk_events.append(build_risk_event(change))

    # Save checkpoint
    elapsed = time.monotonic() - start_time
    save_tenant_checkpoint(
        checkpoint_dir,
        client_id,
        time.time(),
        current_snapshot,
    )

    return {
        "events": events,
        "changes": changes,
        "risk_events": risk_events,
        "stats": {
            **collection_stats,
            "changes_detected": len(changes),
            "high_priority_changes": len(risk_events),
            "elapsed_seconds": round(elapsed, 2),
        },
    }


# ─── Tenant Checkpointing ─────────────────────────────────────────────


def save_tenant_checkpoint(
    checkpoint_dir: str,
    client_id: str,
    timestamp: float,
    snapshot: dict[str, dict[str, list[str]]] | None = None,
) -> None:
    """Save checkpoint for a tenant.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        client_id: Unique tenant identifier.
        timestamp: Unix timestamp of collection.
        snapshot: Domain -> record type -> values mapping.
    """
    safe_id = client_id.replace("/", "_").replace(":", "_")
    path = os.path.join(checkpoint_dir, f"whisper_tenant_{safe_id}.json")
    data: dict[str, Any] = {"last_collection": timestamp}
    if snapshot is not None:
        data["snapshot"] = snapshot
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except OSError:
        logger.exception("action=save_checkpoint, status=error, client_id=%s", client_id)


def load_tenant_checkpoint(checkpoint_dir: str, client_id: str) -> dict[str, Any]:
    """Load checkpoint for a tenant.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        client_id: Unique tenant identifier.

    Returns:
        Checkpoint dict with 'last_collection' and optional 'snapshot'.
    """
    safe_id = client_id.replace("/", "_").replace(":", "_")
    path = os.path.join(checkpoint_dir, f"whisper_tenant_{safe_id}.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return {"last_collection": 0.0}


# ─── Summary Formatting ───────────────────────────────────────────────


def format_tenant_summary(
    client_id: str,
    stats: dict[str, Any],
) -> str:
    """Format a tenant collection summary event.

    Args:
        client_id: Tenant identifier.
        stats: Collection statistics.

    Returns:
        JSON string for Splunk event ingestion.
    """
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "client_id": client_id,
        "domains_processed": stats.get("domains_processed", 0),
        "domains_errors": stats.get("domains_errors", 0),
        "total_records": stats.get("total_records", 0),
        "changes_detected": stats.get("changes_detected", 0),
        "high_priority_changes": stats.get("high_priority_changes", 0),
        "elapsed_seconds": stats.get("elapsed_seconds", 0),
    }
    return json.dumps(event, default=str)

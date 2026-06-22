"""Shared checkpoint and interval validation utilities for modular inputs.

Provides save_checkpoint() and load_checkpoint() for persisting modular input
state between runs, and validate_interval() for validating collection intervals.
Replaces duplicated implementations across whisper_health_input,
whisper_threat_intel_input, whisper_watchlist_input, and whisper_baseline_input.
"""

from __future__ import annotations

import json
import os
from typing import Any

from whisper_logging import get_logger

logger = get_logger("checkpoint")


def save_checkpoint(
    checkpoint_dir: str,
    input_name: str,
    data: dict[str, Any],
    prefix: str,
) -> None:
    """Save checkpoint data for a modular input.

    Writes a JSON file containing the checkpoint data to the checkpoint
    directory. The filename is derived from the prefix and sanitized
    input name.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        input_name: Input stanza name (e.g. "whisper_health://default").
        data: Dictionary of checkpoint data to persist.
        prefix: File prefix for namespacing (e.g. "whisper_health").
    """
    safe_name = input_name.replace("://", "_").replace("/", "_")
    path = os.path.join(checkpoint_dir, f"{prefix}_{safe_name}.json")
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except OSError:
        logger.exception("action=save_checkpoint, status=error, input=%s", input_name)


def load_checkpoint(
    checkpoint_dir: str,
    input_name: str,
    prefix: str,
    default: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Load checkpoint data for a modular input.

    Reads a JSON file from the checkpoint directory. Returns the default
    value if the file does not exist or is corrupt.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        input_name: Input stanza name (e.g. "whisper_health://default").
        prefix: File prefix for namespacing (e.g. "whisper_health").
        default: Default value to return when checkpoint is missing or corrupt.
            Defaults to an empty dict if not provided.

    Returns:
        Dictionary with checkpoint data, or the default value.
    """
    if default is None:
        default = {}
    safe_name = input_name.replace("://", "_").replace("/", "_")
    path = os.path.join(checkpoint_dir, f"{prefix}_{safe_name}.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return default


def validate_interval(
    interval: int,
    min_seconds: int,
    max_seconds: int,
) -> list[str]:
    """Validate a modular input collection interval.

    Args:
        interval: Interval in seconds to validate.
        min_seconds: Minimum allowed interval in seconds.
        max_seconds: Maximum allowed interval in seconds.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: list[str] = []
    if interval < min_seconds:
        errors.append(f"interval must be at least {min_seconds} seconds")
    if interval > max_seconds:
        errors.append(f"interval must not exceed {max_seconds} seconds")
    return errors

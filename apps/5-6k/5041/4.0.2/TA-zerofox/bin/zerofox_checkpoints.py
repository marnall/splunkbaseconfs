"""Checkpoint read/write for generic intel input (new key + optional legacy fallbacks)."""

from __future__ import annotations

import os
from pathlib import Path


def intel_checkpoint_key(intel_source: str, splunk_stanza: str) -> str:
    return f"zerofox_intel::{intel_source}::{splunk_stanza}"


def _fs_safe_key(logical_key: str) -> str:
    """Splunk stanza names may contain 'scheme://id'; '/' must not appear in path segments."""
    return logical_key.replace("/", "_")


def read_text_checkpoint(checkpoint_dir: str, key: str, *, legacy_path: bool = False) -> str | None:
    if legacy_path:
        path = os.path.join(checkpoint_dir, key)
    else:
        path = os.path.join(checkpoint_dir, _fs_safe_key(key))
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def write_text_checkpoint(checkpoint_dir: str, key: str, value: str, *, legacy_path: bool = False) -> None:
    Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
    if legacy_path:
        path = os.path.join(checkpoint_dir, key)
    else:
        path = os.path.join(checkpoint_dir, _fs_safe_key(key))
    Path(path).write_text(value, encoding="utf-8")


def get_last_checked_intel(
    checkpoint_dir: str,
    intel_source: str,
    splunk_stanza: str,
    legacy_stanzas: list[str] | None = None,
) -> str | None:
    """Prefer new-key checkpoint; optionally fall back to legacy per-modinput file paths."""
    primary = intel_checkpoint_key(intel_source, splunk_stanza)
    found = read_text_checkpoint(checkpoint_dir, primary)
    if found:
        return found

    for legacy in legacy_stanzas or []:
        legacy_val = read_text_checkpoint(checkpoint_dir, legacy, legacy_path=True)
        if legacy_val:
            write_text_checkpoint(checkpoint_dir, primary, legacy_val, legacy_path=False)
            return legacy_val

    return None


def save_checkpoint_intel(checkpoint_dir: str, intel_source: str, splunk_stanza: str, value: str) -> None:
    write_text_checkpoint(
        checkpoint_dir,
        intel_checkpoint_key(intel_source, splunk_stanza),
        value,
        legacy_path=False,
    )


def legacy_stanza_full(mod_input: str, instance_name: str) -> str:
    return f"{mod_input}://{instance_name}"

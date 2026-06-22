"""Diagnostic data collection for Whisper Security Add-on.

Implements the collect_diag_info() interface for Splunk's diag command.
Collects app configuration, health status, and log data for troubleshooting.
"""

from __future__ import annotations

import json
import os

from whisper_logging import get_logger

logger = get_logger("diag")

APP_NAME = "TA-whisper-graph"


def setup(parser=None):
    """Declare CLI options for the diagnostic extension.

    Called by Splunk's diag framework before collect_diag_info() to register
    any custom command-line options or REST endpoints needed for data collection.

    Args:
        parser: Optional argparse-style parser for adding custom options.
    """
    # Presence of this function signals to the diag framework that the
    # extension follows the current contract; no custom CLI options are needed.


def collect_diag_info(diag, app_dir=None, options=None, global_options=None, **kwargs):
    """Collect diagnostic data for the Whisper Security Add-on.

    Args:
        diag: Splunk diagnostic object with add_file, add_dir, add_string methods.
        app_dir: Path to the app directory provided by the diag framework.
            Falls back to SPLUNK_HOME-based path when not supplied.
        options: Parsed CLI options from setup() (unused).
        global_options: Global diag options (unused).
        **kwargs: Reserved for forward compatibility with future diag API changes.
    """
    app_home = app_dir or os.path.join(os.environ.get("SPLUNK_HOME", ""), "etc", "apps", APP_NAME)

    # Collect default configuration (no secrets)
    default_dir = os.path.join(app_home, "default")
    if os.path.isdir(default_dir):
        diag.add_dir(default_dir, description="Default configuration files")

    # Collect local configuration (excluding passwords.conf)
    local_dir = os.path.join(app_home, "local")
    if os.path.isdir(local_dir):
        for fname in os.listdir(local_dir):
            if fname == "passwords.conf":
                continue
            fpath = os.path.join(local_dir, fname)
            if os.path.isfile(fpath):
                diag.add_file(fpath, description=f"Local config: {fname}")

    # Collect app metadata
    manifest_path = os.path.join(app_home, "app.manifest")
    if os.path.isfile(manifest_path):
        diag.add_file(manifest_path, description="App manifest")

    # Collect Whisper-specific log files
    log_dir = os.path.join(os.environ.get("SPLUNK_HOME", ""), "var", "log", "splunk")
    if os.path.isdir(log_dir):
        for fname in os.listdir(log_dir):
            if fname.startswith("whisper_") and fname.endswith(".log"):
                fpath = os.path.join(log_dir, fname)
                diag.add_file(fpath, description=f"Whisper log: {fname}")

    # Add environment summary (no secrets)
    env_summary = {
        "app_name": APP_NAME,
        "app_home": app_home,
        "app_exists": os.path.isdir(app_home),
        "python_version": _get_python_version(),
        "splunk_home": os.environ.get("SPLUNK_HOME", "not set"),
    }
    diag.add_string(
        json.dumps(env_summary, indent=2),
        description="Whisper environment summary",
    )

    logger.info("action=collect_diag, status=success")


def _get_python_version() -> str:
    import sys

    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

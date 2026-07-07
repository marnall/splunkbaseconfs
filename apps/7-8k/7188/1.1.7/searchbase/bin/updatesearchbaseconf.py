# coding=utf-8

# Standard library imports
import logging
import os
import os.path
import re
import sys
import time
import shutil  # Used for robust file copying to create backups
from datetime import datetime
from typing import Generator

# Compensating control for CVE-2026-25645 / GHSA-gc5v-m9x4-r6x2 on requests<2.33 (Python 3.9 tree).
# Must run before importing requests. See README "Vendored Python security".
_splunk_home = os.environ.get("SPLUNK_HOME")
if _splunk_home:
    _secure_tmp = os.path.join(_splunk_home, "var", "run", "searchbase", "tmp")
    os.makedirs(_secure_tmp, mode=0o700, exist_ok=True)
    # Re-tighten permissions in case the directory pre-existed from an earlier
    # run (or another component) with looser modes; os.makedirs(mode=...) is a
    # no-op when exist_ok=True and the directory already exists.
    try:
        os.chmod(_secure_tmp, 0o700)
    except OSError:
        # Best-effort hardening; the TMPDIR redirect alone still moves requests
        # away from /tmp. Failure here is logged once the logger is configured.
        pass
    os.environ["TMPDIR"] = _secure_tmp

# Prepend the vendored Python tree so we load the pinned requests (2.32.5 on
# py39, 2.34.2 on py313) instead of whatever older requests ships in Splunk's
# bundled site-packages. lib_path lives next to this script in bin/.
from lib_path import prepend_vendor_lib  # noqa: E402

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
prepend_vendor_lib(_APP_ROOT)

# Third-party imports
import requests  # noqa: E402
from splunklib.searchcommands import (
    Configuration,
    GeneratingCommand,
    Option,
    validators,
    dispatch,
)

# --- Application Configuration ---
# These constants define the core behavior of the command.
APP_NAME = "searchbase"
SPLUNK_HOME = os.environ["SPLUNK_HOME"]
S3_BASE_URL = "https://is4s.s3.amazonaws.com/"
S3_FILE_PATH = "searchbase_searchbase/searchbase.conf"
DESTINATION_DIR = os.path.join(SPLUNK_HOME, "etc", "apps", APP_NAME, "default")
DESTINATION_FILE_NAME = "searchbase.conf"

# --- Backup Configuration ---
# Directory where timestamped backups will be stored.
BACKUP_DIR = os.path.join(SPLUNK_HOME, "etc", "apps", APP_NAME, "backup")
# The maximum number of backup files to keep. Older files will be automatically deleted.
MAX_BACKUPS = 5

# --- Logging Configuration ---
# Defines the name and location of the log file for this command.
LOG_FILE_NAME = "updatesearchbaseconf.log"
LOGGER_NAME = "updatesearchbaseconf"
LOG_PATH = os.path.join(SPLUNK_HOME, "var", "log", "splunk", LOG_FILE_NAME)
LOGGER = logging.getLogger(LOGGER_NAME)

# Splunk-style log format for detailed, machine-parsable logs.
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_FORMAT = "%(asctime)s,%(msecs)03d %(levelname)-8s [%(process)d:%(threadName)s] %(name)s - %(message)s"
# Simpler format for messages that appear in the Splunk UI (stderr).
LOG_STREAM_FORMAT = "[%(levelname)s] %(message)s"

# Create convenient aliases for logging functions.
DEBUG = LOGGER.debug
INFO = LOGGER.info
ERROR = LOGGER.error
WARN = LOGGER.warning


def set_up_logging():
    """Configures file and stream logging for the command with Splunk-style format."""
    if LOGGER.handlers:
        return
    LOGGER.setLevel(logging.DEBUG)  # Capture all levels of log messages.

    # File handler for detailed, persistent logging.
    fh = logging.FileHandler(LOG_PATH)
    formatter = logging.Formatter(LOG_FILE_FORMAT, LOG_DATE_FORMAT)
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)  # Log everything to the file.
    LOGGER.addHandler(fh)

    # Stream handler for important messages to the Splunk UI (jobs inspector).
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(logging.Formatter(LOG_STREAM_FORMAT))
    sh.setLevel(logging.WARNING)  # Only show warnings and errors in the UI.
    LOGGER.addHandler(sh)
    LOGGER.propagate = False


def get_file_version(content: bytes) -> int:
    """Parses a YYYYMMDDHHMM version number from the first line of the file content."""
    try:
        # If the file is empty, there's no version to parse.
        if not content:
            INFO("File content is empty, no version to parse.")
            return 0

        # Decode the first line to a string for regex matching.
        first_line = content.splitlines()[0].decode("utf-8").strip()
        DEBUG(f"Attempting to parse first line for version: '{first_line}'")

        # Regex to find a line like '# version = 202601161030'
        match = re.search(r"#?\s*version\s*=\s*(\d+)", first_line)
        if match:
            version_str = match.group(1)
            INFO(f"Found version string: {version_str}")
            return int(version_str)
        else:
            WARN(f"Version string not found in first line: '{first_line}'")
    except (IndexError, UnicodeDecodeError, ValueError) as e:
        ERROR(f"Could not parse version number from file content. Error: {e}")
    return 0


def format_version_timestamp(version_int: int) -> str:
    """Converts a YYYYMMDDHHMM integer into a human-readable date string for UI output."""
    if version_int == 0:
        return "Not Found"
    try:
        dt_obj = datetime.strptime(str(version_int), "%Y%m%d%H%M")
        return dt_obj.strftime("%B %d, %Y, %I:%M %p")
    except ValueError:
        return f"Invalid Format ({version_int})"


def backup_existing_file(source_path: str) -> str or None:
    """
    Copies the source file to a timestamped backup file in the backup directory.
    Returns the path to the new backup file, or None if no file existed to back up.
    """
    if not os.path.exists(source_path):
        INFO(f"No existing file at {source_path} to back up.")
        return None

    try:
        # Ensure the backup directory exists.
        os.makedirs(BACKUP_DIR, exist_ok=True)
        # Create a unique, timestamped filename for the backup.
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_filename = f"{DESTINATION_FILE_NAME}.{timestamp}.bak"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        # shutil.copy2 preserves file metadata (like modification time), which is good practice.
        shutil.copy2(source_path, backup_path)
        INFO(f"Successfully backed up '{source_path}' to '{backup_path}'")
        return backup_path
    except Exception as e:
        ERROR(f"Failed to create backup for '{source_path}'. Error: {e}")
        return None


def prune_old_backups():
    """
    Keeps the most recent backups (defined by MAX_BACKUPS) and deletes older ones.
    """
    INFO(f"Pruning old backups. Keeping the latest {MAX_BACKUPS}.")
    try:
        # Get all files in the backup directory that match our backup pattern.
        backup_files = [
            f
            for f in os.listdir(BACKUP_DIR)
            if f.startswith(DESTINATION_FILE_NAME) and f.endswith(".bak")
        ]

        # Sort files by name in reverse (descending) order. This puts the newest files first.
        backup_files.sort(reverse=True)

        # If we have more backups than we want to keep...
        if len(backup_files) > MAX_BACKUPS:
            # ...get the list of files to delete (all files after the first MAX_BACKUPS).
            files_to_delete = backup_files[MAX_BACKUPS:]
            INFO(
                f"Found {len(backup_files)} backups. Deleting {len(files_to_delete)} old backups."
            )
            for filename in files_to_delete:
                file_path = os.path.join(BACKUP_DIR, filename)
                os.remove(file_path)
                INFO(f"Deleted old backup: {file_path}")
        else:
            INFO(f"Found {len(backup_files)} backups. No pruning needed.")
    except Exception as e:
        ERROR(f"Failed to prune old backups. Error: {e}")


@Configuration(type="events")
class UpdateSearchbaseConf(GeneratingCommand):
    """The main class for the updatesearchbaseconf command."""

    dryrun = Option(validate=validators.Boolean())
    force = Option(validate=validators.Boolean())

    def write_output(self, data: bytes) -> tuple[str, int]:
        """Writes the downloaded content to the destination .conf file."""
        full_path = os.path.join(DESTINATION_DIR, DESTINATION_FILE_NAME)
        INFO(f"Preparing to write {len(data)} bytes to {full_path}")
        try:
            os.makedirs(DESTINATION_DIR, exist_ok=True)
            with open(full_path, "wb") as file:
                bytes_written = file.write(data)
            INFO(f"Successfully wrote {bytes_written} bytes to {full_path}")
            return full_path, bytes_written
        except IOError as e:
            ERROR(f"Failed to write to file {full_path}. Error: {e}")
            raise

    def reload_searchbase_conf(self, session_key: str, splunkd_uri: str) -> dict:
        """Makes a REST API call to reload the 'conf-searchbase' configuration."""
        reload_url = f"{splunkd_uri}/services/configs/conf-searchbase/_reload"
        headers = {"Authorization": f"Splunk {session_key}"}

        INFO(f"Triggering targeted configuration reload at endpoint: {reload_url}")
        try:
            response = requests.post(reload_url, headers=headers)
            INFO(f"Reload request completed with status code: {response.status_code}")
            response.raise_for_status()
            message = "Successfully triggered reload of conf-searchbase."
            INFO(message)
            return {"status": "Success", "message": message}
        except requests.exceptions.RequestException as e:
            message = f"Failed to trigger reload of conf-searchbase. Error: {e}"
            ERROR(message)
            return {"status": "Failed", "message": message}

    def generate(self) -> Generator[dict, None, None]:
        """Main execution logic with backup, pruning, and enhanced logging."""
        INFO(
            f"Starting command execution. Provided options: dryrun={self.dryrun}, force={self.force}"
        )

        # 1. Check for required user action.
        if self.dryrun is None and self.force is None:
            WARN("Command run with no options. Returning error to user.")
            yield {
                "_time": time.time(),
                "status": "Error: Missing Option",
                "message": "Please specify an action. Use 'dryrun=true' to check for updates, or 'dryrun=false' to perform a safe update.",
            }
            return

        # 2. Get local and S3 file versions.
        local_version = 0
        local_file_path = os.path.join(DESTINATION_DIR, DESTINATION_FILE_NAME)
        INFO(f"Checking for local file at: {local_file_path}")
        if os.path.exists(local_file_path):
            try:
                with open(local_file_path, "rb") as f:
                    local_content = f.read()
                INFO(f"Local file found. Reading {len(local_content)} bytes.")
                local_version = get_file_version(local_content)
            except IOError as e:
                ERROR(f"Could not read local file {local_file_path}. Error: {e}")
        else:
            INFO("Local file does not exist. Local version will be considered 0.")

        url = S3_BASE_URL + S3_FILE_PATH
        INFO(f"Requesting remote file from URL: {url}")
        try:
            resp = requests.get(url, allow_redirects=True)
            INFO(f"S3 request completed with status code: {resp.status_code}")
            resp.raise_for_status()
            s3_content = resp.content
            INFO(f"Remote file downloaded. Reading {len(s3_content)} bytes.")
            s3_version = get_file_version(s3_content)
        except requests.exceptions.RequestException as e:
            ERROR(f"Failed to download file from S3. Error: {e}")
            yield {
                "_time": time.time(),
                "status": "Failed",
                "error": f"Could not download from S3: {e}",
            }
            return

        INFO(f"Version check: Local={local_version}, S3={s3_version}")

        # 3. Perform decision logic based on user input and versions.
        if self.dryrun is True:
            INFO("Action is 'dryrun=true'. Preparing dry run report.")
            recommendation = (
                "The local version is current or newer. No action is required."
            )
            if s3_version > local_version:
                recommendation = "A newer version was found in S3. To update, run with 'dryrun=false'."
            elif s3_version == 0 and local_version > 0:
                recommendation = (
                    "WARNING: Could not parse version from S3 file. DO NOT UPDATE."
                )
            INFO(f"Dry run recommendation: {recommendation}")
            yield {
                "_time": time.time(),
                "status": "Dry Run",
                "local_version_timestamp": format_version_timestamp(local_version),
                "s3_version_timestamp": format_version_timestamp(s3_version),
                "recommendation": recommendation,
            }
            return

        if self.force:
            WARN(
                f"Action is 'force=true'. Bypassing version check and proceeding with update."
            )
        elif s3_version <= local_version:
            INFO("S3 version is not newer than local. Skipping update.")
            yield {
                "_time": time.time(),
                "status": "Skipped",
                "message": f"Local version ({local_version}) is current or newer than S3 version ({s3_version}).",
                "local_version_timestamp": format_version_timestamp(local_version),
                "s3_version_timestamp": format_version_timestamp(s3_version),
            }
            return

        # 4. Perform the update process: Backup -> Write -> Reload -> Prune.
        INFO(
            f"Proceeding with update. S3 version ({s3_version}) is newer than local ({local_version}) or force=true."
        )
        session_key = self.metadata.searchinfo.session_key
        splunkd_uri = self.metadata.searchinfo.splunkd_uri

        try:
            # Backup the existing file before overwriting.
            backup_file_path = backup_existing_file(local_file_path)

            # Write the new file from S3.
            full_path, bytes_written = self.write_output(s3_content)

            # Trigger the configuration reload.
            reload_result = self.reload_searchbase_conf(session_key, splunkd_uri)

            # Prune old backups only after a successful update.
            if backup_file_path:
                prune_old_backups()

            INFO("Update and reload process completed successfully.")
            # Yield the final success message with backup information.
            yield {
                "_time": time.time(),
                "status": "Success",
                "message": f"Updated from version {local_version} to {s3_version}.",
                "bytes_written": bytes_written,
                "destination_file": full_path,
                "backup_file": backup_file_path or "N/A (no previous file existed)",
                "reload_status": reload_result["status"],
                "reload_message": reload_result["message"],
            }
        except Exception as e:
            ERROR(f"An unexpected error occurred during the update process. Error: {e}")
            yield {"_time": time.time(), "status": "Failed", "error": str(e)}


# --- Main execution block ---
if __name__ == "__main__":
    set_up_logging()
    dispatch(UpdateSearchbaseConf, sys.argv, sys.stdin, sys.stdout, __name__)

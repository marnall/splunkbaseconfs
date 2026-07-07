import os
import sys
import json
import gzip
import requests
import time
import tempfile
import fcntl
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "splunklib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "spurlib"))
from splunklib import client as splunk_client
from spurlib.api import get_proxy_settings
from spurlib._sysauth import build_config_bundle
from spurlib.logging import setup_logging
from spurlib.notify import (
    notify_feed_failure,
    notify_feed_success,
    notify_geo_feed_success,
)
from splunklib.modularinput import *

APP_NAME = "spur-enrichment-for-splunk"

# Upstream ipgeo feed regenerates ~once per day. Skip a full ~300MB MMDB
# download when the local file is younger than this — keeps hourly modular
# input crons from burning bandwidth on redundant pulls. Must stay aligned
# with the /spur_mmdb_refresh handler's fast-path (bin/spur_mmdb_refresh.py).
MMDB_FRESH_SECONDS = 24 * 60 * 60


def mmdb_target_path():
    splunk_home = os.environ.get("SPLUNK_HOME", "")
    return os.path.join(
        splunk_home, "etc", "apps", APP_NAME, "local", "data", "mmdb", "ipgeo.mmdb"
    )


def mmdb_is_fresh(path):
    if not os.path.exists(path):
        return False
    return (time.time() - os.path.getmtime(path)) < MMDB_FRESH_SECONDS


def write_checkpoint(checkpoint_file_path, checkpoint_file_new_contents):
    """
    Writes the checkpoint file to disk.

    Args:
      checkpoint_file_path (str): The path to the checkpoint file.
      checkpoint_file_new_contents (str): The new contents of the checkpoint file.
    """
    with open(checkpoint_file_path, "w") as file:
        file.write(checkpoint_file_new_contents)


def get_lock_file_path(checkpoint_dir, feed_type):
    """
    Generate lock file path for a given feed type.
    
    Args:
        checkpoint_dir: Directory for lock files
        feed_type: Type of feed
        
    Returns:
        str: Path to lock file
    """
    safe_feed_type = feed_type.replace("/", "_").replace("\\", "_")
    lock_filename = f"{safe_feed_type}.lock"
    return os.path.join(checkpoint_dir, lock_filename)


def is_lock_stale(lock_file_path, max_age_seconds=86400):
    """
    Check if a lock file is stale (older than max_age_seconds).
    
    Args:
        lock_file_path: Path to the lock file
        max_age_seconds: Maximum age in seconds before considering lock stale (default 24 hours)
        
    Returns:
        bool: True if lock is stale or doesn't exist, False otherwise
    """
    if not os.path.exists(lock_file_path):
        return True
    
    try:
        lock_age = time.time() - os.path.getmtime(lock_file_path)
        return lock_age > max_age_seconds
    except Exception:
        return True


def acquire_lock(logger, lock_file_path):
    """
    Acquire a lock for feed processing using file locking.
    Returns a file handle that must be kept open, or None if lock cannot be acquired.
    
    Args:
        logger: Logger instance
        lock_file_path: Path to the lock file
        
    Returns:
        file handle if lock acquired, None otherwise
    """
    try:
        # Ensure the directory exists
        lock_dir = os.path.dirname(lock_file_path)
        if not os.path.exists(lock_dir):
            os.makedirs(lock_dir)
        
        # Open the lock file
        lock_file = open(lock_file_path, 'w')
        
        # Try to acquire an exclusive lock (non-blocking)
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Write process info to lock file
            lock_info = {
                "pid": os.getpid(),
                "timestamp": time.time(),
                "iso_time": datetime.now(timezone.utc).isoformat()
            }
            lock_file.write(json.dumps(lock_info))
            lock_file.flush()
            logger.info("Successfully acquired lock: %s", lock_file_path)
            return lock_file
        except IOError:
            # Lock is held by another process
            lock_file.close()
            logger.warning("Could not acquire lock (already held by another process): %s", lock_file_path)
            return None
            
    except Exception as e:
        logger.error("Error acquiring lock: %s", e)
        return None


def release_lock(logger, lock_file_handle, lock_file_path):
    """
    Release a previously acquired lock.
    
    Args:
        logger: Logger instance
        lock_file_handle: File handle returned by acquire_lock
        lock_file_path: Path to the lock file
    """
    if lock_file_handle is None:
        return
    
    try:
        # Release the lock
        fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_UN)
        lock_file_handle.close()
        
        # Remove the lock file
        if os.path.exists(lock_file_path):
            os.remove(lock_file_path)
        
        logger.info("Successfully released lock: %s", lock_file_path)
    except Exception as e:
        logger.warning("Error releasing lock: %s", e)


def cleanup_stale_lock(logger, lock_file_path, max_age_seconds=86400):
    """
    Remove stale lock files that are older than max_age_seconds.
    
    Args:
        logger: Logger instance
        lock_file_path: Path to the lock file
        max_age_seconds: Maximum age in seconds before considering lock stale (default 24 hours)
        
    Returns:
        bool: True if stale lock was removed, False otherwise
    """
    if is_lock_stale(lock_file_path, max_age_seconds):
        try:
            if os.path.exists(lock_file_path):
                os.remove(lock_file_path)
                logger.info("Removed stale lock file: %s", lock_file_path)
                return True
        except Exception as e:
            logger.warning("Failed to remove stale lock file %s: %s", lock_file_path, e)
    return False


def cleanup_old_checkpoints(logger, checkpoint_dir, feed_type, current_feed_date):
    """
    Clean up old checkpoint files for the same feed type but different feed dates.
    This prevents accumulation of old checkpoint files and ensures we don't use stale data.

    Args:
        logger: Logger instance
        checkpoint_dir: Directory containing checkpoint files
        feed_type: Type of feed (e.g., 'anonymous', 'anonymous-residential')
        current_feed_date: Current feed date to keep
    """
    if not os.path.exists(checkpoint_dir):
        return
        
    try:
        # Pattern to match old checkpoint files for this feed type
        old_pattern = f"{feed_type}_"
        current_checkpoint_file = f"{feed_type}_{current_feed_date}.txt"
        legacy_checkpoint_file = f"{feed_type}.txt"
        
        files_to_remove = []
        
        for filename in os.listdir(checkpoint_dir):
            if filename.startswith(old_pattern) and filename.endswith(".txt"):
                if filename != current_checkpoint_file:
                    files_to_remove.append(filename)
            elif filename == legacy_checkpoint_file:
                # Remove legacy checkpoint files that don't include feed date
                files_to_remove.append(filename)
        
        for filename in files_to_remove:
            try:
                file_path = os.path.join(checkpoint_dir, filename)
                os.remove(file_path)
                logger.debug("Cleaned up old checkpoint file: %s", file_path)
            except Exception as e:
                logger.warning("Failed to remove old checkpoint file %s: %s", filename, e)
                
    except Exception as e:
        logger.warning("Error during checkpoint cleanup: %s", e)


def get_checkpoint_file_path(checkpoint_dir, feed_type, feed_date):
    """
    Generate checkpoint file path using feed type and feed date.

    Args:
        checkpoint_dir: Directory for checkpoint files
        feed_type: Type of feed
        feed_date: Feed date from metadata (e.g., "20250223")

    Returns:
        str: Path to checkpoint file
    """
    safe_feed_date = feed_date.replace("/", "_").replace("\\", "_")
    checkpoint_filename = f"{feed_type}_{safe_feed_date}.txt"
    return os.path.join(checkpoint_dir, checkpoint_filename)


def _fetch_feed_metadata(logger, proxy_handler_config, token, feed_type, expected_key):
    """
    Call https://feeds.spur.us/v2/{feed_type}/latest and return the metadata
    block under `expected_key` (either "json" or "mmdb"). Raises a single,
    human-readable exception when the API returns an error status, a non-JSON
    body, an `error` field, or a body missing the expected key — so callers
    surface the actual upstream problem (e.g. "Unauthorized") instead of a
    KeyError on the expected key.
    """
    url = "/".join(["https://feeds.spur.us/v2", feed_type, "latest"])
    logger.debug("Requesting %s", url)
    resp = requests.get(url, headers={"TOKEN": token}, proxies=proxy_handler_config)
    logger.debug("Got feed metadata response with http status %s", resp.status_code)

    try:
        parsed = resp.json()
    except ValueError:
        raise Exception(
            "Spur Feeds API returned HTTP %s with non-JSON body: %s"
            % (resp.status_code, (resp.text or "").strip()[:200] or "<empty>")
        )

    if resp.status_code != 200:
        api_error = parsed.get("error") if isinstance(parsed, dict) else None
        raise Exception(
            "Spur Feeds API %s for %s returned HTTP %s: %s"
            % (expected_key, feed_type, resp.status_code, api_error or parsed)
        )

    if isinstance(parsed, dict) and parsed.get("error"):
        raise Exception(
            "Spur Feeds API %s for %s returned error: %s"
            % (expected_key, feed_type, parsed["error"])
        )

    if not isinstance(parsed, dict) or expected_key not in parsed:
        raise Exception(
            "Spur Feeds API %s for %s response missing '%s' key. The token in "
            "use may not be authorized for the Feeds API. Response: %s"
            % (expected_key, feed_type, expected_key, str(parsed)[:200])
        )

    logger.debug("Got feed metadata: %s", parsed)
    return parsed[expected_key]


def get_feed_metadata(logger, proxy_handler_config, token, feed_type):
    return _fetch_feed_metadata(logger, proxy_handler_config, token, feed_type, "json")


def get_feed_metadata_mmdb(logger, proxy_handler_config, token, feed_type):
    return _fetch_feed_metadata(logger, proxy_handler_config, token, feed_type, "mmdb")


def get_feed_response(logger, proxy_handler_config, token, feed_type, feed_metadata):
    """
    Get the latest feed from the Spur API. https://feeds.spur.us/v2/{feed_type}/{feed_metadata['location']}.
    This returns the response object so that the caller can process the feed line by line.
    Be sure to use gzip.GzipFile to decompress the response and close the file when you're done.
    """
    location = feed_metadata["location"]
    if "realtime" in location:
        location = location.replace("realtime/", "")
    url = "/".join(["https://feeds.spur.us/v2", feed_type, location])
    logger.debug("Requesting %s", url)
    h = {"TOKEN": token}
    logger.debug("headers: %s", {"TOKEN": "***"})
    return requests.get(url, headers=h, proxies=proxy_handler_config, stream=True)


def get_checkpoint(logger, checkpoint_file_path, checkpoints_enabled):
    if not checkpoints_enabled:
        return {}

    checkpoint_file_contents = ""
    try:
        # read sha values from file, if exist
        with open(checkpoint_file_path, "r") as file:
            checkpoint_file_contents = file.read()
    except:
        return {}

    checkpoint = json.loads(checkpoint_file_contents)
    logger.debug(
        "checkpoint '%s' found in checkpoint file %s",
        checkpoint_file_contents,
        checkpoint_file_path,
    )
    return checkpoint


def download_feed_to_temp(logger, proxy_handler_config, token, feed_type, feed_metadata):
    """
    Download the feed file to a temporary location using x-goog-generation header for naming.
    Returns a tuple of (file_path, goog_generation).
    """
    logger.info("Downloading feed to temporary file")
    response = get_feed_response(logger, proxy_handler_config, token, feed_type, feed_metadata)
    
    # Get the x-goog-generation header for file naming
    goog_generation = response.headers.get("x-goog-generation", "unknown")
    logger.info("x-goog-generation: %s", goog_generation)
    
    # Create temp file with a name based on x-goog-generation
    temp_dir = tempfile.gettempdir()
    temp_filename = f"spur_feed_{feed_type.replace('/', '_')}_{goog_generation}.gz"
    temp_file_path = os.path.join(temp_dir, temp_filename)
    
    logger.info("Downloading feed to temp file: %s", temp_file_path)
    
    try:
        with open(temp_file_path, "wb") as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
        response.close()
        logger.info("Successfully downloaded feed to temp file")
        return temp_file_path, goog_generation
    except Exception as e:
        response.close()
        # Clean up partial file if download failed
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        logger.error("Error downloading feed to temp file: %s", e)
        raise e


def process_geo_feed(ctx, logger, token, proxy_handler_config, feed_type, input_name, ew, checkpoint_dir):
    """
    Process the geo feed.
    """
    logger.info("Processing geo feed")
    logger.debug("feed_type: %s", feed_type)
    logger.debug("input_name: %s", input_name)
    logger.debug("ew: %s", ew)

    # Fast-path: skip the ~300MB download when the local MMDB is younger than
    # the upstream regeneration cadence. Hourly crons on a daily-regenerating
    # feed otherwise burn bandwidth on redundant pulls.
    target_path = mmdb_target_path()
    if mmdb_is_fresh(target_path):
        age = int(time.time() - os.path.getmtime(target_path))
        logger.info("MMDB at %s is fresh (age=%ss, threshold=%ss); skipping download", target_path, age, MMDB_FRESH_SECONDS)
        return

    # Get lock file path and attempt to acquire lock
    lock_file_path = get_lock_file_path(checkpoint_dir, feed_type)
    logger.debug("lock_file_path: %s", lock_file_path)

    # Clean up stale locks (older than 24 hours)
    cleanup_stale_lock(logger, lock_file_path)

    # Try to acquire the lock
    lock_handle = acquire_lock(logger, lock_file_path)
    if lock_handle is None:
        logger.warning("Another instance is already processing feed type '%s', skipping", feed_type)
        return

    logger.debug("proxy_handler_config: %s", proxy_handler_config)

    try:
        # Get the feed metadata
        try:
            feed_metadata = get_feed_metadata_mmdb(
                logger, proxy_handler_config, token, feed_type
            )
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            notify_feed_failure(ctx, "Error getting spur %s feed metadata" % feed_type)
            logger.error("Error getting feed metadata: %s", e)
            logger.error("Full traceback: %s", error_details)

            # Provide more specific error message
            if "401" in str(e) or "Unauthorized" in str(e):
                raise Exception(
                    f"Invalid API token when getting {feed_type} metadata. Please check your API token configuration."
                )
            elif "403" in str(e) or "Forbidden" in str(e):
                raise Exception(
                    f"Access denied when getting {feed_type} metadata. Please check your API token permissions."
                )
            elif "timeout" in str(e).lower():
                raise Exception(
                    f"Timeout when getting {feed_type} metadata. Please check network connectivity."
                )
            else:
                raise Exception(
                    f"Error getting {feed_type} metadata: {str(e) or type(e).__name__}"
                )

        # Process the feed
        logger.debug("Attempting to retrieve feed with feed metadata: %s", feed_metadata)
        try:
            # Get the application path
            splunk_home = os.environ["SPLUNK_HOME"]
            app_local_path = os.path.join(
                splunk_home, "etc", "apps", "spur-enrichment-for-splunk", "local", "data"
            )
            mmdb_file_path = os.path.join(app_local_path, "mmdb", "ipgeo.mmdb")

            # create the app_local_path if it doesn't exist
            if not os.path.exists(app_local_path):
                os.makedirs(app_local_path)

            # create the mmdb directory if it doesn't exist
            if not os.path.exists(os.path.join(app_local_path, "mmdb")):
                os.makedirs(os.path.join(app_local_path, "mmdb"))

            response = get_feed_response(
                logger, proxy_handler_config, token, feed_type, feed_metadata
            )
            feed_generation_date = response.headers.get("x-feed-generation-date")
            logger.debug("Feed generation date: %s", feed_generation_date)

            # Write the feed to the mmdb file
            with open(mmdb_file_path, "wb") as f:
                f.write(response.raw.read())

            # Make the MMDB file world readable
            os.chmod(mmdb_file_path, 0o644)

            response.close()
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            logger.error("Error processing feed: %s", e)
            logger.error("Full traceback: %s", error_details)

            # Provide more specific error message
            if "permission" in str(e).lower() or "access" in str(e).lower():
                detailed_msg = f"Permission error processing {feed_type} feed. Check file permissions for MMDB directory: {str(e)}"
            elif "disk" in str(e).lower() or "space" in str(e).lower():
                detailed_msg = f"Disk space error processing {feed_type} feed: {str(e)}"
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                detailed_msg = f"Network error processing {feed_type} feed: {str(e)}"
            else:
                detailed_msg = (
                    f"Error processing {feed_type} feed: {str(e) or type(e).__name__}"
                )

            notify_feed_failure(ctx, detailed_msg)
            raise Exception(detailed_msg)

        # If we get here, we've successfully processed the feed, write out the date to the checkpoint file
        notify_geo_feed_success(ctx)
    finally:
        # Always release the lock
        release_lock(logger, lock_handle, lock_file_path)


def process_feed(
    ctx,
    logger,
    token,
    proxy_handler_config,
    feed_type,
    input_name,
    ew,
    checkpoint_dir,
    checkpoints_enabled,
    predownload_enabled,
):
    if feed_type == "anonymous-residential/realtime":
        checkpoints_enabled = False

    # Get lock file path and attempt to acquire lock
    lock_file_path = get_lock_file_path(checkpoint_dir, feed_type)
    logger.debug("lock_file_path: %s", lock_file_path)

    # Clean up stale locks (older than 24 hours)
    cleanup_stale_lock(logger, lock_file_path)

    # Try to acquire the lock
    lock_handle = acquire_lock(logger, lock_file_path)
    if lock_handle is None:
        logger.warning("Another instance is already processing feed type '%s', skipping", feed_type)
        return

    logger.debug("proxy_handler_config: %s", proxy_handler_config)

    try:
        # Get the feed metadata
        try:
            feed_metadata = get_feed_metadata(
                logger, proxy_handler_config, token, feed_type
            )
        except Exception as e:
            notify_feed_failure(ctx, "Error getting spur %s feed metadata" % feed_type)
            logger.error("Error getting feed metadata: %s", e)
            raise e

        # Extract the feed date from metadata — this is stable and deterministic
        feed_date = feed_metadata.get("date", "unknown")
        logger.info("Feed date: %s", feed_date)

        # Generate checkpoint file path using feed date
        checkpoint_file_path = get_checkpoint_file_path(checkpoint_dir, feed_type, feed_date)
        logger.debug("checkpoint_file_path: %s", checkpoint_file_path)

        # Clean up old checkpoint files for this feed type
        if checkpoints_enabled:
            cleanup_old_checkpoints(logger, checkpoint_dir, feed_type, feed_date)

        # Get the latest checkpoint for this feed date
        checkpoint = get_checkpoint(logger, checkpoint_file_path, checkpoints_enabled)

        # Check if we've already processed this feed date
        start_offset = 0
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        if checkpoints_enabled and checkpoint:
            if (checkpoint.get("feed_date") == feed_date and
                checkpoint.get("completed_date") is not None):
                logger.info("Feed date %s already processed (completed on %s), skipping",
                           feed_date, checkpoint.get("completed_date"))
                return
            elif (checkpoint.get("feed_date") == feed_date and
                  checkpoint.get("last_touched_date") == today and
                  "offset" in checkpoint):
                # Same feed date, same day, but not completed - resume from offset
                logger.info("Resuming processing of feed date %s from offset %s",
                           feed_date, checkpoint["offset"])
                start_offset = checkpoint["offset"]
            else:
                logger.info("Starting fresh processing for feed date %s", feed_date)
                start_offset = 0
        else:
            logger.info("No checkpoint found or checkpoints disabled, starting from offset 0")

        # Process the feed
        logger.debug("Attempting to retrieve feed with feed metadata: %s", feed_metadata)
        processed = 0
        temp_file_path = None
        
        try:
            checkpoint = {
                "offset": start_offset,
                "start_time": time.time(),
                "end_time": None,
                "completed_date": None,
                "last_touched_date": today,
                "feed_metadata": feed_metadata,
                "feed_date": feed_date,
            }
            if checkpoints_enabled:
                write_checkpoint(checkpoint_file_path, json.dumps(checkpoint))

            if predownload_enabled:
                # Download feed to temporary file first
                logger.debug("Pre-download mode enabled, downloading feed to temp file")
                temp_file_path, feed_identifier = download_feed_to_temp(
                    logger, proxy_handler_config, token, feed_type, feed_metadata
                )
                logger.info("Feed downloaded to temp file: %s", temp_file_path)

                # Process the downloaded file
                with gzip.open(temp_file_path, 'rt', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            data["feed_identifier"] = feed_identifier
                            data["feed_date"] = feed_date
                            data["feed_type"] = feed_type
                            event = Event()
                            event.stanza = input_name
                            event.sourceType = "spur_feed"
                            event.time = time.time()
                            event.data = json.dumps(data)
                            processed += 1

                            if processed < start_offset:
                                continue
                            ew.write_event(event)
                            checkpoint["offset"] = processed

                            if processed % 10000 == 0:
                                logger.debug("Wrote %s events", processed)
                                if checkpoints_enabled:
                                    write_checkpoint(
                                        checkpoint_file_path, json.dumps(checkpoint)
                                    )
                        except Exception as e:
                            logger.error("Error processing line: %s", e)
            else:
                # Stream mode (original behavior)
                response = get_feed_response(
                    logger, proxy_handler_config, token, feed_type, feed_metadata
                )
                logger.info("Got feed response")
                feed_identifier = response.headers.get("x-goog-generation", "unknown")
                feed_generation_date = response.headers.get("x-feed-generation-date")
                checkpoint["feed_generation_date"] = feed_generation_date
                logger.info("Feed generation date: %s", feed_generation_date)
                logger.info("x-goog-generation: %s", feed_identifier)

                with gzip.GzipFile(fileobj=response.raw) as f:
                    for line in f:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            data["feed_identifier"] = feed_identifier
                            data["feed_date"] = feed_date
                            data["feed_type"] = feed_type
                            event = Event()
                            event.stanza = input_name
                            event.sourceType = "spur_feed"
                            event.time = time.time()
                            event.data = json.dumps(data)
                            processed += 1

                            if processed < start_offset:
                                continue
                            ew.write_event(event)
                            checkpoint["offset"] = processed

                            if processed % 10000 == 0:
                                logger.debug("Wrote %s events", processed)
                                if checkpoints_enabled:
                                    write_checkpoint(
                                        checkpoint_file_path, json.dumps(checkpoint)
                                    )
                        except Exception as e:
                            logger.error("Error processing line: %s", e)
                response.close()
                
            checkpoint["offset"] = processed
        except Exception as e:
            checkpoint["offset"] = processed
            if checkpoints_enabled:
                write_checkpoint(checkpoint_file_path, json.dumps(checkpoint))
            logger.error("Error processing feed: %s", e)
            notify_feed_failure(ctx, "Error processing spur %s feed: %s" % (feed_type, e))
            # Clean up temp file if it exists
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    logger.debug("Cleaned up temp file: %s", temp_file_path)
                except Exception as cleanup_e:
                    logger.warning("Failed to clean up temp file %s: %s", temp_file_path, cleanup_e)
            raise e

        # If we get here, we've successfully processed the feed, write out the date to the checkpoint file
        checkpoint["end_time"] = time.time()
        checkpoint["completed_date"] = today
        checkpoint_file_new_contents = json.dumps(checkpoint)
        logger.info("Wrote %s events", processed)
        if "realtime" not in feed_type:
            notify_feed_success(ctx, processed)
        if checkpoints_enabled:
            logger.debug("Writing checkpoint file %s", checkpoint_file_path)
            write_checkpoint(checkpoint_file_path, checkpoint_file_new_contents)
        
        # Clean up temp file if it exists
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug("Cleaned up temp file: %s", temp_file_path)
            except Exception as cleanup_e:
                logger.warning("Failed to clean up temp file %s: %s", temp_file_path, cleanup_e)
    finally:
        # Always release the lock
        release_lock(logger, lock_handle, lock_file_path)


class SpurFeed(Script):
    """
    Modular input that downloads the latest spur feed and indexes it into Splunk.
    """

    def get_scheme(self):
        """When Splunk starts, it looks for all the modular inputs defined by
        its configuration, and tries to run them with the argument --scheme.
        Splunkd expects the modular inputs to print a description of the
        input in XML on stdout. The modular input framework takes care of all
        the details of formatting XML and printing it. The user need only
        override get_scheme and return a new Scheme object.

        :return: scheme, a Scheme object
        """
        scheme = Scheme("Spur Feed")
        scheme.description = (
            "Downloads the latest spur feed and indexes it into Splunk."
        )
        scheme.use_external_validation = True

        feed_type_argument = Argument("feed_type")
        feed_type_argument.title = "Feed Type"
        feed_type_argument.data_type = Argument.data_type_string
        feed_type_argument.description = "The type of feed to download. Must be one of 'anonymous, anonymous-ipv6, anonymous-residential, anonymous-residential-ipv6, anonymous-residential/realtime, ipgeo'"
        feed_type_argument.required_on_create = True
        feed_type_argument.required_on_edit = True
        scheme.add_argument(feed_type_argument)

        # Checkpoint settings
        checkpoint_argument = Argument("enable_checkpoint")
        checkpoint_argument.title = "Enable Checkpoint Files"
        checkpoint_argument.data_type = Argument.data_type_boolean
        checkpoint_argument.description = "Write out a checkpoint file to make sure the same feed isn't ingested twice."
        checkpoint_argument.required_on_create = True
        checkpoint_argument.required_on_edit = True
        scheme.add_argument(checkpoint_argument)

        # Pre-download settings
        predownload_argument = Argument("enable_predownload")
        predownload_argument.title = "Enable Pre-download"
        predownload_argument.data_type = Argument.data_type_boolean
        predownload_argument.description = "Download the full feed file to a temporary location before processing instead of streaming directly."
        predownload_argument.required_on_create = True
        predownload_argument.required_on_edit = True
        scheme.add_argument(predownload_argument)

        return scheme

    def validate_input(self, definition):
        """When using external validation, after splunkd calls the modular input with
        --scheme to get a scheme, it calls it again with --validate-arguments for
        each instance of the modular input in its configuration files, feeding XML
        on stdin to the modular input to do validation. It is called the same way
        whenever a modular input's configuration is edited.

        :param validation_definition: a ValidationDefinition object
        """
        feed_type = definition.parameters["feed_type"]
        if feed_type not in [
            "anonymous",
            "anonymous-ipv6",
            "anonymous-residential",
            "anonymous-residential-ipv6",
            "anonymous-residential/realtime",
            "ipgeo",
        ]:
            raise ValueError(
                f"feed_type must be one of 'anonymous, anonymous-ipv6, anonymous-residential, anonymous-residential-ipv6, anonymous-residential/realtime, ipgeo'; found {feed_type}"
            )

    def stream_events(self, inputs, ew):
        """This function handles all the action: splunk calls this modular input
        without arguments, streams XML describing the inputs to stdin, and waits
        for XML on stdout describing events.

        If you set use_single_instance to True on the scheme in get_scheme, it
        will pass all the instances of this input to a single instance of this
        script.

        :param inputs: an InputDefinition object
        :param event_writer: an EventWriter object
        """

        logger = setup_logging()

        session_key = inputs.metadata.get("session_key")
        scoped_service = splunk_client.Service(
            token=session_key,
            app=APP_NAME,
            owner="nobody",
        )
        bundle = build_config_bundle(scoped_service)
        token = bundle.get("token")
        proxy_handler_config = get_proxy_settings(bundle, logger)

        # Go through each input for this modular input
        for input_name, input_item in list(inputs.inputs.items()):
            logger.info("Starting spur feed ingest for input '%s'", input_name)
            if token is None or token == "":
                logger.error(
                    "No Spur API token found for input '%s'; aborting. "
                    "Configure the token via the app setup page. "
                    "Note: modular inputs run on the indexer, which has its own storage/passwords — "
                    "configuring the token on a search head does not propagate to the indexer.",
                    input_name,
                )
                notify_feed_failure(self, "No token found")
                raise ValueError("No token found")

            # Get fields from the InputDefinition object
            feed_type = input_item["feed_type"]
            if feed_type not in [
                "anonymous",
                "anonymous-ipv6",
                "anonymous-residential",
                "anonymous-residential-ipv6",
                "anonymous-residential/realtime",
                "ipgeo",
            ]:
                msg = (
                    f"feed_type must be one of 'anonymous, anonymous-ipv6, anonymous-residential, "
                    f"anonymous-residential-ipv6, anonymous-residential/realtime, ipgeo'; found {feed_type}"
                )
                logger.error("Invalid feed_type for input '%s': %s", input_name, msg)
                notify_feed_failure(self, msg)
                raise ValueError(msg)
            logger.info("Input '%s' feed_type=%s", input_name, feed_type)

            checkpoints_enabled = bool(int(input_item["enable_checkpoint"]))
            logger.info("Input '%s' checkpoints_enabled=%s", input_name, checkpoints_enabled)

            predownload_enabled = bool(int(input_item["enable_predownload"]))
            logger.info("Input '%s' predownload_enabled=%s", input_name, predownload_enabled)

            checkpoint_dir = inputs.metadata["checkpoint_dir"]
            logger.debug("checkpoint_dir: %s", checkpoint_dir)

            try:
                if feed_type == "ipgeo":
                    process_geo_feed(self, logger, token, proxy_handler_config, feed_type, input_name, ew, checkpoint_dir)
                else:
                    process_feed(
                        self,
                        logger,
                        token,
                        proxy_handler_config,
                        feed_type,
                        input_name,
                        ew,
                        checkpoint_dir,
                        checkpoints_enabled,
                        predownload_enabled,
                    )
            except Exception as e:
                logger.error("Error processing feed: %s", e)
                notify_feed_failure(
                    self, "Error processing spur %s feed: %s" % (feed_type, e)
                )
                raise e


if __name__ == "__main__":
    sys.exit(SpurFeed().run(sys.argv))

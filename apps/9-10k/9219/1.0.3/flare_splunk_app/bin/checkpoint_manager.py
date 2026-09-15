import json
import logging
import os


logger = logging.getLogger("flare_cron_job")


def _get_checkpoint_path() -> str:
    """Return the path to the checkpoint file."""
    splunk_home = os.environ.get("SPLUNK_HOME", "")
    if splunk_home:
        checkpoint_dir = os.path.join(
            splunk_home, "var", "lib", "splunk", "modinputs", "flare_splunk_app"
        )
    else:
        checkpoint_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(checkpoint_dir, exist_ok=True)
    return os.path.join(checkpoint_dir, "checkpoint.json")


def load_checkpoint() -> dict:
    """Load the checkpoint file."""
    path = _get_checkpoint_path()
    if not os.path.exists(path):
        logger.debug("No checkpoint file found at %s", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("Checkpoint loaded from %s", path)
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Failed to read checkpoint file, starting fresh: %s", e)
        return {}


def save_checkpoint(data: dict) -> None:
    """Save the checkpoint data to disk atomically."""
    path = _get_checkpoint_path()
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        # Atomic rename: if the process crashes before this line, the original checkpoint is intact
        os.replace(tmp_path, path)
        logger.info("Checkpoint saved to %s", path)
    except IOError as e:
        logger.error("Failed to save checkpoint: %s", e)
        # Clean up partial temp file if rename failed
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def reconcile_checkpoint_with_config(
    checkpoint: dict, backfill_days: int, index_name: str
) -> dict:
    """
    Compares the current config against what was saved in the checkpoint.
    If backfill_days or index_name changed, clears the checkpoint to force a full re-ingest.
    Always stamps the current config into the checkpoint before returning.
    """
    saved_backfill = checkpoint.get("_config", {}).get("backfill_days")
    saved_index = checkpoint.get("_config", {}).get("index_name")

    config_changed = False
    if saved_backfill is not None and saved_backfill != backfill_days:
        logger.info(
            "Backfill range changed from %d to %d days. Clearing checkpoint.",
            saved_backfill,
            backfill_days,
        )
        config_changed = True

    if saved_index is not None and saved_index != index_name:
        logger.info(
            "Target index changed from %s to %s. Clearing checkpoint.",
            saved_index,
            index_name,
        )
        config_changed = True

    if config_changed:
        checkpoint = {}

    checkpoint["_config"] = {"backfill_days": backfill_days, "index_name": index_name}
    return checkpoint

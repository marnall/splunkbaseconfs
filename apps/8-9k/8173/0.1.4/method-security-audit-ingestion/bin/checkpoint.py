import json
import logging
import os
from typing import Any, Dict, cast

logger = logging.getLogger(__name__)

def _safe_filename(s: str) -> str:
    # sanitize to alphanumeric + underscore
    return "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in s)

def load_checkpoint(checkpoint_dir: str, stanza_name: str) -> Dict[str, Any]:
    """
    Returns checkpoint dict (or empty dict) for given stanza.
    """
    fn = os.path.join(checkpoint_dir, _safe_filename(stanza_name) + ".chk")
    try:
        with open(fn, encoding="utf-8") as f:
            data = f.read()
        # you may store JSON or simple string; here try JSON
        return cast(Dict[str, Any], json.loads(data))
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.warning("Failed to load checkpoint for %s: %s", stanza_name, e)
        return {}

def save_checkpoint(checkpoint_dir: str, stanza_name: str, cp_obj: dict):
    """
    Save the checkpoint object (dict) for the stanza.
    """
    fn = os.path.join(checkpoint_dir, _safe_filename(stanza_name) + ".chk")
    tmp = fn + ".tmp"
    try:
        os.makedirs(checkpoint_dir, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(cp_obj))
        os.replace(tmp, fn)
    except Exception as e:
        logger.error("Failed to save checkpoint for %s: %s", stanza_name, e)

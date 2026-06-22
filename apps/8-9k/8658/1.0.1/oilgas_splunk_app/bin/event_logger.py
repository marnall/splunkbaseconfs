import logging
import os
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
APP_ROOT = SCRIPT_DIR.parent
APP_DIR_NAME = APP_ROOT.name


def resolve_splunk_home():
    configured_path = os.environ.get("SPLUNK_HOME")
    if configured_path:
        return Path(configured_path).resolve()
    return (APP_ROOT / ".." / ".." / "..").resolve()


SPLUNK_HOME = resolve_splunk_home()
SPLUNK_LOG_DIR = SPLUNK_HOME / "var" / "log" / APP_DIR_NAME
LOG_FILE_PATH = SPLUNK_LOG_DIR / "oil_gas_events.log"

SPLUNK_LOG_DIR.mkdir(parents=True, exist_ok=True)

file_handler = logging.FileHandler(str(LOG_FILE_PATH))
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[file_handler]
)

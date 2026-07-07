import ta_analyst1_declare  # noqa: F401
import os
import sys
import shutil
import traceback
from analyst1_logging import get_logger


def remove_lookup_backup():
    try:
        session_key = sys.stdin.readline().strip()
        logger = get_logger("ta_analyst1_cleanup_lookup_backup")
        logger.info("Started deleting 'Lookup backup' directory.")
        file_location_remove = os.path.join(
            os.environ.get('SPLUNK_HOME'),'etc', 'apps', ta_analyst1_declare.ta_name, 'lookups', 'Lookup backup')
        if os.path.exists(file_location_remove):
            shutil.rmtree(file_location_remove)
            logger.info(f"Removed the Lookup backup directory: {file_location_remove}")
        else:
            logger.info(f"Lookup backup directory not present: {file_location_remove}")

    except Exception:
        logger.error(f"Error occured while deleting the Lookup backup directory: {traceback.format_exc()}")

if __name__ == "__main__":
    remove_lookup_backup()

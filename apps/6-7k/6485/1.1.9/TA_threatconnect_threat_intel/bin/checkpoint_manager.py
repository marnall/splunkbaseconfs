"""Checkpoint Manager Module"""

# standard library
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))
# standard library
import datetime
import json


class CheckpointManager:
    """Checkpoint Manager Class"""

    checkpoint_path = (
        f"""{os.getenv("SPLUNK_DB", "/opt/splunk/var/lib/splunk").rstrip("/")}"""
        """/modinputs/tc_download_iocs"""
    )

    def save_checkpoint(self, key, last_run):
        """Save the value of last run in a json file named {key}"""
        with open(f"{self.checkpoint_path}/{key}.json", "w", encoding="utf-8") as file:
            json.dump({"last_run": last_run}, file)

    def get_checkpoint(self, key):
        """Retrieve the value of last run in a json file named {key}"""
        try:
            with open(f"{self.checkpoint_path}/{key}.json", encoding="utf-8") as file:
                last_run = json.load(file).get("last_run")
            if isinstance(last_run, (int, float)):
                return self.epoch_to_datetime(last_run)
            return last_run
        except Exception:  # pylint: disable=broad-except
            return None

    @staticmethod
    def epoch_to_datetime(epoch_time):
        """Convert epoch time to datetime string"""
        dt = datetime.datetime.utcfromtimestamp(epoch_time)
        return dt

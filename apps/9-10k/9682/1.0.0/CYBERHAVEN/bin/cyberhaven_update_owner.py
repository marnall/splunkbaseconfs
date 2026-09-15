# encoding = utf-8
# Always put this line at the beginning of this file
"""Splunk modular alert action that updates the owner of a Cyberhaven incident."""
import os
import sys

# CYBERHAVEN vendors its own copy of the third-party libraries it needs
# (solnlib, splunklib, splunktaucclib, requests, urllib3, ...) under lib/; it
# has no runtime dependency on TA-CYBERHAVEN's bin/ or lib/ directories.
_APP_LIB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
if _APP_LIB not in sys.path:
    sys.path.insert(0, _APP_LIB)

from splunktaucclib.alert_actions_base import ModularAlertBase  # noqa: E402
import cyberhaven_settings  # noqa: E402
import cyberhaven_update_owner_helper  # noqa: E402


class AlertActionWorkerCyberhavenUpdateOwner(ModularAlertBase):
    """Modular alert action worker that updates a Cyberhaven incident's owner."""

    def __init__(self, ta_name, alert_name):
        """Initialize the worker for the given TA and alert action name."""
        super(AlertActionWorkerCyberhavenUpdateOwner, self).__init__(ta_name, alert_name)

    def get_log_level(self):
        """Read the log level from TA-CYBERHAVEN's own [logging] stanza.

        Overrides ModularAlertBase.get_log_level(), which otherwise goes through
        splunktaucclib's UCC-style Setup_Util and looks for a globalConfig.json this
        app doesn't ship, logging "Global config JSON file not found!" on every run
        before falling back to INFO. This skips that lookup entirely.
        """
        return cyberhaven_settings.get_log_level()

    def validate_params(self):
        """Validate the alert action parameters."""
        return True

    def process_event(self, *args, **kwargs):
        """Process the alert event and return a status code."""
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = cyberhaven_update_owner_helper.process_event(self, *args, **kwargs)
        except Exception as e:
            cyberhaven_update_owner_helper._log_error(self, f"Unexpected error: {e}")
            import traceback
            cyberhaven_update_owner_helper._log_error(self, traceback.format_exc())
            return 5
        cyberhaven_update_owner_helper._log_info(self, f"Successfully returned status: {status}")
        return status


if __name__ == "__main__":
    exitcode = AlertActionWorkerCyberhavenUpdateOwner("CYBERHAVEN", "cyberhaven_update_owner").run(sys.argv)
    sys.exit(exitcode)

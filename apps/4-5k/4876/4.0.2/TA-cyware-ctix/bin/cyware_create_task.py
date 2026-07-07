
# encoding = utf-8
"""Alert action worker for cyware_create_task."""
# Always put this line at the beginning of this file
import ta_cyware_ctix_declare  # noqa: F401

import sys

from alert_actions_base import ModularAlertBase
from ta_cyware_ctix import modalert_cyware_create_task_helper


class AlertActionWorkercyware_create_task(ModularAlertBase):
    """Alert action worker for creating tasks in CTIX."""

    def __init__(self, ta_name, alert_name):
        """Initialize the alert action worker."""
        super(AlertActionWorkercyware_create_task, self).__init__(ta_name, alert_name)

    def validate_params(self):
        """Validate the alert action parameters."""
        if not self.get_param("object_id"):
            self.log_error('object_id is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("text"):
            self.log_error('text is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("deadline"):
            self.log_error('deadline is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("splunk_account"):
            self.log_error('splunk_account is a mandatory parameter, but its value is None.')
            return False

        # Validate deadline is a positive number
        try:
            deadline = int(self.get_param("deadline"))
            if deadline <= 0:
                self.log_error('deadline must be a positive number (days).')
                return False
        except (ValueError, TypeError):
            self.log_error('deadline must be a valid number.')
            return False

        # Validate text length
        text = self.get_param("text")
        if text and len(text) > 2000:
            self.log_error('Task description must not be greater than 2000 characters.')
            return False

        return True

    def process_event(self, *args, **kwargs):
        """Process the alert action event."""
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_cyware_create_task_helper.process_event(
                self, *args, **kwargs
            )
        except (AttributeError, TypeError) as ae:
            self.log_error(
                "Error: {}. Please double check spelling and also verify that "
                "a compatible version of Splunk_SA_CIM is installed.".format(str(ae))
            )
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if e:
                self.log_error(msg.format(str(e)))
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status


if __name__ == "__main__":
    exitcode = AlertActionWorkercyware_create_task(
        "TA-cyware-ctix", "cyware_create_task"
    ).run(sys.argv)
    sys.exit(exitcode)

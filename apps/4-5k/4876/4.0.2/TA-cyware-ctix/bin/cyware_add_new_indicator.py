
# encoding = utf-8
"""Alert action worker for cyware_add_new_indicator."""
# Always put this line at the beginning of this file
import ta_cyware_ctix_declare  # noqa: F401

import sys

from alert_actions_base import ModularAlertBase
from ta_cyware_ctix import modalert_cyware_add_new_indicator_helper


class AlertActionWorkercyware_add_new_indicator(ModularAlertBase):
    """Alert action worker for adding new indicators to CTIX."""

    def __init__(self, ta_name, alert_name):
        """Initialize the alert action worker."""
        super(AlertActionWorkercyware_add_new_indicator, self).__init__(ta_name, alert_name)

    def validate_params(self):
        """Validate the alert action parameters."""
        if not self.get_param("indicator_type"):
            self.log_error('indicator_type is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("indicator_value"):
            self.log_error('indicator_value is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("splunk_account"):
            self.log_error('splunk_account is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        """Process the alert action event."""
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_cyware_add_new_indicator_helper.process_event(
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
    exitcode = AlertActionWorkercyware_add_new_indicator(
        "TA-cyware-ctix", "cyware_add_new_indicator"
    ).run(sys.argv)
    sys.exit(exitcode)

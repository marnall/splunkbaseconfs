
# encoding = utf-8
"""Alert action worker for cyware_get_enriched_data."""

# Always put this line at the beginning of this file
import ta_cyware_ctix_declare  # noqa: F401

import sys

from alert_actions_base import ModularAlertBase
from ta_cyware_ctix import modalert_cyware_get_enriched_data_helper


class AlertActionWorkercyware_get_enriched_data(ModularAlertBase):
    """Alert action worker for getting enriched data from CTIX."""

    def __init__(self, ta_name, alert_name):
        """Initialize the alert action worker."""
        super(AlertActionWorkercyware_get_enriched_data, self).__init__(ta_name, alert_name)

    def validate_params(self):
        """Validate the alert action parameters."""
        if not self.get_param("indicator_value"):
            self.log_error('indicator_value is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("cyware_account"):
            self.log_error('cyware_account is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        """Process the alert action event."""
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_cyware_get_enriched_data_helper.process_event(
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
    exitcode = AlertActionWorkercyware_get_enriched_data(
        "TA-cyware-ctix", "cyware_get_enriched_data"
    ).run(sys.argv)
    sys.exit(exitcode)

# encoding = utf-8
# Always put this line at the beginning of this file
import ta_siemplify_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_send_alert_to_siemplify_helper

class AlertActionWorkersend_alert_to_siemplify(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super().__init__(ta_name, alert_name)

    def validate_params(self):
        if not self.get_param("alert_name"):
            self.log_error('alert_name is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_send_alert_to_siemplify_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error(f"Error: {str(ae)}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.")
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
    exitcode = AlertActionWorkersend_alert_to_siemplify("TA-siemplify", "send_alert_to_siemplify").run(sys.argv)
    sys.exit(exitcode)

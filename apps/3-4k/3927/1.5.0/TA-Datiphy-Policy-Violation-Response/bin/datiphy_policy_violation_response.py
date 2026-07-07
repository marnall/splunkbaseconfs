
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_datiphy_policy_violation_response_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_datiphy_policy_violation_response_helper

class AlertActionWorkerdatiphy_policy_violation_response(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerdatiphy_policy_violation_response, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("security_center_email"):
            self.log_error('security_center_email is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("soc_email_password"):
            self.log_error('soc_email_password is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("soc_email_recipient"):
            self.log_error('soc_email_recipient is a mandatory setup parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_datiphy_policy_violation_response_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error("Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(ae.message))
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if e.message:
                self.log_error(msg.format(e.message))
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status

if __name__ == "__main__":
    exitcode = AlertActionWorkerdatiphy_policy_violation_response("TA-Datiphy-Policy-Violation-Response", "datiphy_policy_violation_response").run(sys.argv)
    sys.exit(exitcode)

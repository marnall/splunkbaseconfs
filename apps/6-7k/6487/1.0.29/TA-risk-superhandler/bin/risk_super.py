# encoding = utf-8
# Always put this line at the beginning of this file
import import_declare_test

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
from ta_risk_superhandler import modalert_risk_super_helper

class AlertActionWorkerrisk_super(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerrisk_super, self).__init__(ta_name, alert_name)

    def validate_params(self):


        if not self.get_param("uc_lookup_path"):
            self.log_error('uc_lookup_path is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("uc_ref_field"):
            self.log_error('uc_ref_field is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_risk_super_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error("Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(str(ae)))#ae.message replaced with str(ae)
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(str(e)))#e.message replaced with str(ae)
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status

if __name__ == "__main__":
    exitcode = AlertActionWorkerrisk_super("TA-risk-superhandler", "risk_super").run(sys.argv)
    sys.exit(exitcode)

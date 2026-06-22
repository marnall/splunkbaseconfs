# encoding = utf-8
# Always put this line at the beginning of this file
import import_declare_test

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
import alert_create_incident_helper

class AlertActionWorkeropencti_create_incident(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkeropencti_create_incident, self).__init__(ta_name, alert_name)

    def validate_params(self):


        if not self.get_param("name"):
            self.log_error('name is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = alert_create_incident_helper.process_event(self, *args, **kwargs)
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(str(e)))
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status

if __name__ == "__main__":
    exitcode = AlertActionWorkeropencti_create_incident("TA-opencti-for-splunk-enterprise", "opencti_create_incident").run(sys.argv)
    sys.exit(exitcode)

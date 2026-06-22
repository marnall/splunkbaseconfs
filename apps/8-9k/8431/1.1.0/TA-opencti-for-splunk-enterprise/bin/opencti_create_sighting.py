# encoding = utf-8
# Always put this line at the beginning of this file
import import_declare_test

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
import alert_create_sighting_helper

class AlertActionWorkeropencti_create_sighting(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkeropencti_create_sighting, self).__init__(ta_name, alert_name)

    def validate_params(self):


        if not self.get_param("sighting_of_value"):
            self.log_error('sighting_of_value is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("where_sighted_value"):
            self.log_error('where_sighted_value is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = alert_create_sighting_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkeropencti_create_sighting("TA-opencti-for-splunk-enterprise", "opencti_create_sighting").run(sys.argv)
    sys.exit(exitcode)

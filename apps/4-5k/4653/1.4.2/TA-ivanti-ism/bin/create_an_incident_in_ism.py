
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_ivanti_ism_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_create_an_incident_in_ism_helper

class AlertActionWorkercreate_an_incident_in_ism(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkercreate_an_incident_in_ism, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("tenant"):
            self.log_error('tenant is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("customer"):
            self.log_error('customer is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("summary"):
            self.log_error('summary is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("description"):
            self.log_error('description is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("status"):
            self.log_error('status is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_create_an_incident_in_ism_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error("Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(str(ae)))
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
    exitcode = AlertActionWorkercreate_an_incident_in_ism("TA-ivanti-ism", "create_an_incident_in_ism").run(sys.argv)
    sys.exit(exitcode)

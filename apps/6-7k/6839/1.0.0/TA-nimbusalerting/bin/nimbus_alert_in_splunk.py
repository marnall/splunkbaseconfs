
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_nimbusalerting_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_nimbus_alert_in_splunk_helper

class AlertActionWorkernimbus_alert_in_splunk(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkernimbus_alert_in_splunk, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("kb_label"):
            self.log_error('kb_label is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("subsystem_id"):
            self.log_error('subsystem_id is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_nimbus_alert_in_splunk_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkernimbus_alert_in_splunk("TA-nimbusalerting", "nimbus_alert_in_splunk").run(sys.argv)
    sys.exit(exitcode)

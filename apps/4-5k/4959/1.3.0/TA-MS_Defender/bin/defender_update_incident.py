
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_ms_defender_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_defender_update_incident_helper

class AlertActionWorkerdefender_update_incident(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerdefender_update_incident, self).__init__(ta_name, alert_name)

    def validate_params(self):
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_defender_update_incident_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerdefender_update_incident("TA-MS_Defender", "defender_update_incident").run(sys.argv)
    sys.exit(exitcode)

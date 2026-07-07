
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_twilio_studio_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_execute_flow_helper

class AlertActionWorkerexecute_flow(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerexecute_flow, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("studio_flow_id"):
            self.log_error('studio_flow_id is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("twilio_api_key_sid"):
            self.log_error('twilio_api_key_sid is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_execute_flow_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerexecute_flow("TA-twilio-studio", "execute_flow").run(sys.argv)
    sys.exit(exitcode)

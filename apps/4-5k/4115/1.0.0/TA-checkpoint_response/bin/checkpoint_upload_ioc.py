
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_checkpoint_response_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_checkpoint_upload_ioc_helper

class AlertActionWorkercheckpoint_upload_ioc(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkercheckpoint_upload_ioc, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("ioc_type"):
            self.log_error('ioc_type is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("ioc_value"):
            self.log_error('ioc_value is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_checkpoint_upload_ioc_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkercheckpoint_upload_ioc("TA-checkpoint_response", "checkpoint_upload_ioc").run(sys.argv)
    sys.exit(exitcode)

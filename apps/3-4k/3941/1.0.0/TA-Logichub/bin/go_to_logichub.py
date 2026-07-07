
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_logichub_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_go_to_logichub_helper

class AlertActionWorkergo_to_logichub(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkergo_to_logichub, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("logichub_stream_url"):
            self.log_error('logichub_stream_url is a mandatory setup parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_go_to_logichub_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkergo_to_logichub("TA-Logichub", "go_to_logichub").run(sys.argv)
    sys.exit(exitcode)

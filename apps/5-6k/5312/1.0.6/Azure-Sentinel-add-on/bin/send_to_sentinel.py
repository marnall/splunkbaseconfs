
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_sentinel2_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_send_to_sentinel_helper

class AlertActionWorkersend_to_sentinel(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkersend_to_sentinel, self).__init__(ta_name, alert_name)

    def validate_params(self):
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_send_to_sentinel_helper.process_event(self, *args, **kwargs)
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
    #log_error("Started Send to Sentinel")
    exitcode = AlertActionWorkersend_to_sentinel("TA-sentinel2", "send_to_sentinel").run(sys.argv)
    #self.log_error("Completed Send to Sentinel")
    sys.exit(exitcode)


# encoding = utf-8
# Always put this line at the beginning of this file
import ta_redseal_adaptive_response_actions_declare 

import os
import sys

from alert_actions_base import ModularAlertBase 
import modalert_get_10_host_metrics_helper

class AlertActionWorkerget_10_host_metrics(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerget_10_host_metrics, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("rs_server"):
            self.log_error('rs_server is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("rs_user"):
            self.log_error('rs_user is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("rs_password"):
            self.log_error('rs_password is a mandatory setup parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            self.prepare_meta_for_cam()

            if not self.validate_params():
                return 3 
            status = modalert_get_10_host_metrics_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerget_10_host_metrics("TA-RedSeal_Adaptive_Response_Actions", "get_10_host_metrics").run(sys.argv)
    sys.exit(exitcode)


# encoding = utf-8
# Always put this line at the beginning of this file
import ta_s3_sink_alert_action_for_splunk_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_s3_sink_helper

class AlertActionWorkers3_sink(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkers3_sink, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("account_name"):
            self.log_error('account_name is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("aws_region"):
            self.log_error('aws_region is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("bucket"):
            self.log_error('bucket is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("filename"):
            self.log_error('filename is a mandatory parameter, but its value is None.')
            return False
        
        if not self.get_param("results_type"):
            self.log_error('results_type is a mandatory parameter, but its value is None.')
            return False
            
        if not self.get_param("compress_results"):
            self.log_error('compress_results is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_s3_sink_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkers3_sink("TA-s3-sink-alert-action-for-splunk", "s3_sink").run(sys.argv)
    sys.exit(exitcode)

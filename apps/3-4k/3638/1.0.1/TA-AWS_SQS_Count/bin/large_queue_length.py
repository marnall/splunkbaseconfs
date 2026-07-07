
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_aws_sqs_count_declare 

import os
import sys

from alert_actions_base import ModularAlertBase 
import modalert_large_queue_length_helper

class AlertActionWorkerlarge_queue_length(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerlarge_queue_length, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("aws_access_key"):
            self.log_error('aws_access_key is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("aws_secret_key"):
            self.log_error('aws_secret_key is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("alert_at_queue_length_of"):
            self.log_error('alert_at_queue_length_of is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:

            if not self.validate_params():
                return 3 
            status = modalert_large_queue_length_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerlarge_queue_length("TA-AWS_SQS_Count", "large_queue_length").run(sys.argv)
    sys.exit(exitcode)

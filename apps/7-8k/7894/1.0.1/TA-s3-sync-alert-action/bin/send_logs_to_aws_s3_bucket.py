
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_s3_sync_alert_action_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_send_logs_to_aws_s3_bucket_helper

class AlertActionWorkersend_logs_to_aws_s3_bucket(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkersend_logs_to_aws_s3_bucket, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("aws_access_key"):
            self.log_error('aws_access_key is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("aws_secret_key"):
            self.log_error('aws_secret_key is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("s3_bucket_name"):
            self.log_error('s3_bucket_name is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("aws_region"):
            self.log_error('aws_region is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_send_logs_to_aws_s3_bucket_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkersend_logs_to_aws_s3_bucket("TA-s3-sync-alert-action", "send_logs_to_aws_s3_bucket").run(sys.argv)
    sys.exit(exitcode)

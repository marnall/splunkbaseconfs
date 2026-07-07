
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_logichub123134_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_trigger_logichub_stream_helper

class AlertActionWorkertrigger_logichub_stream(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkertrigger_logichub_stream, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("logichub_stream_url"):
            self.log_error('logichub_stream_url is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("verify_ssl"):
            self.log_error('verify_ssl is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_trigger_logichub_stream_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkertrigger_logichub_stream("TA-logichub123134", "trigger_logichub_stream").run(sys.argv)
    sys.exit(exitcode)

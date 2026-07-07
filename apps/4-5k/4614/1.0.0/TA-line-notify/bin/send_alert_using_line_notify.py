
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_line_notify_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_send_alert_using_line_notify_helper

class AlertActionWorkersend_alert_using_line_notify(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkersend_alert_using_line_notify, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("notify_token"):
            self.log_error('notify_token is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("message_kind"):
            self.log_error('message_kind is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_send_alert_using_line_notify_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkersend_alert_using_line_notify("TA-line-notify", "send_alert_using_line_notify").run(sys.argv)
    sys.exit(exitcode)

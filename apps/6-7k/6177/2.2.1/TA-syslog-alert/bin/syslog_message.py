
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_syslog_alert_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_syslog_message_helper

class AlertActionWorkersyslog_message(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkersyslog_message, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("message_field"):
            self.log_error('message_field is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("host"):
            self.log_error('host is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("port"):
            self.log_error('port is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("proto"):
            self.log_error('proto is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("facility"):
            self.log_error('facility is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("severity"):
            self.log_error('severity is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("syslog_format"):
            self.log_error('syslog_format is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_syslog_message_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkersyslog_message("TA-syslog-alert", "syslog_message").run(sys.argv)
    sys.exit(exitcode)

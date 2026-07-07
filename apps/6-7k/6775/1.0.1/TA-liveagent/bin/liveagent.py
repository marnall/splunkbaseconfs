
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_liveagent_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_liveagent_helper

class AlertActionWorkerliveagent(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerliveagent, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("liveagent_url"):
            self.log_error('liveagent_url is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("api_key"):
            self.log_error('api_key is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("email"):
            self.log_error('email is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("subject"):
            self.log_error('subject is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("recipient_email"):
            self.log_error('recipient_email is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("message"):
            self.log_error('message is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("department_id"):
            self.log_error('department_id is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_liveagent_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerliveagent("TA-liveagent", "liveagent").run(sys.argv)
    sys.exit(exitcode)

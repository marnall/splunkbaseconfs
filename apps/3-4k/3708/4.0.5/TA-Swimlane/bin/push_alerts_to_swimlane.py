
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_swimlane_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_push_to_swimlane


class AlertActionWorkerpush_alerts_to_swimlane(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerpush_alerts_to_swimlane, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("prod_swimlane_host"):
            self.log_error('prod_swimlane_host is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("prod_username"):
            self.log_error('prod_username is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("prod_password_access_token"):
            self.log_error('prod_password_access_token is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("swimlane_app_name"):
            self.log_error('swimlane_app_name is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("push_method"):
            self.log_error('push_method is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("use_automapping"):
            self.log_error('use_automapping is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("number_of_events_to_send"):
            self.log_error('number_of_events_to_send is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_push_to_swimlane.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerpush_alerts_to_swimlane("TA-Swimlane", "push_alerts_to_swimlane").run(sys.argv)
    sys.exit(exitcode)

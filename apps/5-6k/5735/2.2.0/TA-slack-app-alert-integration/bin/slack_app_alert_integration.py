# encoding = utf-8
# Always put this line at the beginning of this file
import import_declare_test

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
import slack_app_alert_integration_implementation

class AlertActionWorkerslack_app_alert_integration(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerslack_app_alert_integration, self).__init__(ta_name, alert_name)

    def validate_params(self):


        if not self.get_param("channel"):
            self.log_error('channel is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("message"):
            self.log_error('message is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = slack_app_alert_integration_implementation.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error("Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(str(ae)))#ae.message replaced with str(ae)
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(str(e)))#e.message replaced with str(ae)
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status

if __name__ == "__main__":
    exitcode = AlertActionWorkerslack_app_alert_integration("TA-slack-app-alert-integration", "slack_app_alert_integration").run(sys.argv)
    sys.exit(exitcode)

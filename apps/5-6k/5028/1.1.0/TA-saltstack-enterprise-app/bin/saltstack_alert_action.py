
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_saltstack_enterprise_app_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_saltstack_alert_action_helper

class AlertActionWorkersaltstack_alert_action(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkersaltstack_alert_action, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("saltstack_username"):
            self.log_error('saltstack_username is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("cmd"):
            self.log_error('cmd is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("fun"):
            self.log_error('fun is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("master"):
            self.log_error('master is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_saltstack_alert_action_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkersaltstack_alert_action("TA-saltstack-enterprise-app", "saltstack_alert_action").run(sys.argv)
    sys.exit(exitcode)

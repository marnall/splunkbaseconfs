
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_puppet_tasks_actionable_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_puppet_enterprise_tasks_helper

class AlertActionWorkerpuppet_enterprise_tasks(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerpuppet_enterprise_tasks, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("severity"):
            self.log_error('severity is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("host"):
            self.log_error('host is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("environment"):
            self.log_error('environment is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("module"):
            self.log_error('module is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("description"):
            self.log_error('description is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_puppet_enterprise_tasks_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerpuppet_enterprise_tasks("TA-puppet-tasks-actionable", "puppet_enterprise_tasks").run(sys.argv)
    sys.exit(exitcode)

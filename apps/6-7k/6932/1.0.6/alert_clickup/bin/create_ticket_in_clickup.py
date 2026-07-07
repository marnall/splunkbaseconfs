
# encoding = utf-8
# Always put this line at the beginning of this file
import alert_clickup_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_create_ticket_in_clickup_helper

class AlertActionWorkercreate_ticket_in_clickup(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkercreate_ticket_in_clickup, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("clickup_api_key"):
            self.log_error('clickup_api_key is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("clickup_list_id"):
            self.log_error('clickup_list_id is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("clickup_task_name"):
            self.log_error('clickup_task_name is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_create_ticket_in_clickup_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkercreate_ticket_in_clickup("alert_clickup", "create_ticket_in_clickup").run(sys.argv)
    sys.exit(exitcode)


# encoding = utf-8
# Always put this line at the beginning of this file
import ta_manageengine_alert_action_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_open_a_request_in_manage_engine_helper

class AlertActionWorkeropen_a_request_in_manage_engine(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkeropen_a_request_in_manage_engine, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("auth_token"):
            self.log_error('auth_token is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("manageengine_url"):
            self.log_error('manageengine_url is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("subject"):
            self.log_error('subject is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("description"):
            self.log_error('description is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("category"):
            self.log_error('category is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("subcategory"):
            self.log_error('subcategory is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("group"):
            self.log_error('group is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("requester"):
            self.log_error('requester is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("priority"):
            self.log_error('priority is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("request_type"):
            self.log_error('request_type is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_open_a_request_in_manage_engine_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkeropen_a_request_in_manage_engine("TA-manageengine-alert-action", "open_a_request_in_manage_engine").run(sys.argv)
    sys.exit(exitcode)

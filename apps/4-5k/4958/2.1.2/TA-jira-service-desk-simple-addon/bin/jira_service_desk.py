# encoding = utf-8
# Always put this line at the beginning of this file
import import_declare_test

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
from ta_service_desk_simple_addon import modalert_jira_service_desk_helper

class AlertActionWorkerjira_service_desk(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerjira_service_desk, self).__init__(ta_name, alert_name)

    def validate_params(self):


        if not self.get_param("account"):
            self.log_error('account is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("jira_project"):
            self.log_error('jira_project is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("jira_issue_type"):
            self.log_error('jira_issue_type is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("jira_summary"):
            self.log_error('jira_summary is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("jira_description"):
            self.log_error('jira_description is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("jira_auto_close"):
            self.log_error('jira_auto_close is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("jira_dedup"):
            self.log_error('jira_dedup is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("jira_attachment"):
            self.log_error('jira_attachment is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("jira_results_description"):
            self.log_error('jira_results_description is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_jira_service_desk_helper.process_event(self, *args, **kwargs)
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(str(e)))
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status

if __name__ == "__main__":
    exitcode = AlertActionWorkerjira_service_desk("TA-jira-service-desk-simple-addon", "jira_service_desk").run(sys.argv)
    sys.exit(exitcode)

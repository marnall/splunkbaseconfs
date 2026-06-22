
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_send_dashboard_alert_action_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_send_dashboard_pdf_helper

class AlertActionWorkersend_dashboard_pdf(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkersend_dashboard_pdf, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("app"):
            self.log_error('app is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("dashboard_id"):
            self.log_error('dashboard_id is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("owner"):
            self.log_error('owner is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("token_map_json"):
            self.log_error('token_map_json is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("mail_to"):
            self.log_error('mail_to is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("mail_subject"):
            self.log_error('mail_subject is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("splunkd_url"):
            self.log_error('splunkd_url is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_send_dashboard_pdf_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkersend_dashboard_pdf("TA-send-dashboard-alert-action", "send_dashboard_pdf").run(sys.argv)
    sys.exit(exitcode)

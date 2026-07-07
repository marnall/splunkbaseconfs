
# encoding = utf-8
# Always put this line at the beginning of this file
import mbcr_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_mbcr_alert_helper

class AlertActionWorkermbcr_alert(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkermbcr_alert, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("account_id"):
            self.log_error('account_id is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("client_id"):
            self.log_error('client_id is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("client_secret"):
            self.log_error('client_secret is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("hostname"):
            self.log_error('hostname is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("action"):
            self.log_error('action is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_mbcr_alert_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkermbcr_alert("mbcr", "mbcr_alert").run(sys.argv)
    sys.exit(exitcode)

# encoding = utf-8
# Always put this line at the beginning of this file
import import_declare_test

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
from ta_whatsapp_alert_action import modalert_whatsapp_alert_helper

class AlertActionWorkerwhatsapp_alert(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerwhatsapp_alert, self).__init__(ta_name, alert_name)

    def validate_params(self):


        if not self.get_param("phone_number_id"):
            self.log_error('phone_number_id is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("access_token"):
            self.log_error('access_token is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("recipients_numbers"):
            self.log_error('recipients_numbers is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("template_name"):
            self.log_error('template_name is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_whatsapp_alert_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerwhatsapp_alert("TA-whatsapp-alert-action", "whatsapp_alert").run(sys.argv)
    sys.exit(exitcode)

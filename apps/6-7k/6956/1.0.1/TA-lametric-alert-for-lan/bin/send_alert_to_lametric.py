
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_lametric_alert_for_lan_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_send_alert_to_lametric_helper

class AlertActionWorkersend_alert_to_lametric(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkersend_alert_to_lametric, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("lametric_api_key"):
            self.log_error('lametric_api_key is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("lametric_ip_address"):
            self.log_error('lametric_ip_address is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("alert_message"):
            self.log_error('alert_message is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("alert_icon"):
            self.log_error('alert_icon is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("notification_sound"):
            self.log_error('notification_sound is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_send_alert_to_lametric_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkersend_alert_to_lametric("TA-lametric-alert-for-lan", "send_alert_to_lametric").run(sys.argv)
    sys.exit(exitcode)

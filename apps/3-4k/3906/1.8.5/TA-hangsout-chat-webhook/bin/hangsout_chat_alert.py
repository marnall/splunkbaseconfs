
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_hangsout_chat_webhook_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_hangsout_chat_alert_helper

class AlertActionWorkerhangsout_chat_alert(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerhangsout_chat_alert, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("webhook_url"):
            self.log_error('webhook_url is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("message_text"):
            self.log_error('message_text is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_hangsout_chat_alert_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerhangsout_chat_alert("TA-hangsout-chat-webhook", "hangsout_chat_alert").run(sys.argv)
    sys.exit(exitcode)

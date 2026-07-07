
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_netclean_proactive_api_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_netclean_proactive_api_helper

class AlertActionWorkernetclean_proactive_api(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkernetclean_proactive_api, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("client_id"):
            self.log_error('client_id is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("client_secret"):
            self.log_error('client_secret is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("default_hash_expiry"):
            self.log_error('default_hash_expiry is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("hash_field"):
            self.log_error('hash_field is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_netclean_proactive_api_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkernetclean_proactive_api("TA-netclean-proactive-api", "netclean_proactive_api").run(sys.argv)
    sys.exit(exitcode)

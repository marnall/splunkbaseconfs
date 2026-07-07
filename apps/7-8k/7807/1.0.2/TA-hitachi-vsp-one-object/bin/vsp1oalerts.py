
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_hitachi_vsp_one_object_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_vsp1oalerts_helper

class AlertActionWorkervsp1oalerts(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkervsp1oalerts, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("access_token_url"):
            self.log_error('access_token_url is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("client_id"):
            self.log_error('client_id is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("client_secret"):
            self.log_error('client_secret is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("prometheus_base_url"):
            self.log_error('prometheus_base_url is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("prometheus_region"):
            self.log_error('prometheus_region is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("prometheus_cluster_name"):
            self.log_error('prometheus_cluster_name is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("csrf_token_generation_url"):
            self.log_error('csrf_token_generation_url is a mandatory setup parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_vsp1oalerts_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkervsp1oalerts("TA-hitachi-vsp-one-object", "vsp1oalerts").run(sys.argv)
    sys.exit(exitcode)

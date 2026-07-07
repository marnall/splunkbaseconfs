
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_cyber_triage_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_triage_endpoint_helper

class AlertActionWorkertriage_endpoint(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkertriage_endpoint, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("server"):
            self.log_error('server is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("rest_port"):
            self.log_error('rest_port is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("api_key"):
            self.log_error('api_key is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("username"):
            self.log_error('username is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("password"):
            self.log_error('password is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("index"):
            self.log_error('index is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("endpoint"):
            self.log_error('endpoint is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("scan_options"):
            self.log_error('scan_options is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("malware_options"):
            self.log_error('malware_options is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("incident_name"):
            self.log_error('incident_name is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_triage_endpoint_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkertriage_endpoint("TA-cyber-triage", "triage_endpoint").run(sys.argv)
    sys.exit(exitcode)


# encoding = utf-8
# Always put this line at the beginning of this file
import da_ess_nucleaalertenhancer_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_enhance_alert_with_gemini_ai_helper

class AlertActionWorkerenhance_alert_with_gemini_ai(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerenhance_alert_with_gemini_ai, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("api_key"):
            self.log_error('api_key is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("max_output_tokens"):
            self.log_error('max_output_tokens is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("index"):
            self.log_error('index is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("sourcetype"):
            self.log_error('sourcetype is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_enhance_alert_with_gemini_ai_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerenhance_alert_with_gemini_ai("DA-ESS-NucleaAlertEnhancer", "enhance_alert_with_gemini_ai").run(sys.argv)
    sys.exit(exitcode)

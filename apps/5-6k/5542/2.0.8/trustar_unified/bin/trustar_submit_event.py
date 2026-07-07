
# encoding = utf-8
# Always put this line at the beginning of this file
import trustar_unified_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_trustar_submit_event_helper

class AlertActionWorkertrustar_submit_event(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkertrustar_submit_event, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("default_submit_enclave_id"):
            self.log_error('default_submit_enclave_id is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("default_enrich_enclave_ids"):
            self.log_error('default_enrich_enclave_ids is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("report_title"):
            self.log_error('report_title is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("custom_or_default"):
            self.log_error('custom_or_default is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("do_redact"):
            self.log_error('do_redact is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_trustar_submit_event_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkertrustar_submit_event("trustar_unified", "trustar_submit_event").run(sys.argv)
    sys.exit(exitcode)

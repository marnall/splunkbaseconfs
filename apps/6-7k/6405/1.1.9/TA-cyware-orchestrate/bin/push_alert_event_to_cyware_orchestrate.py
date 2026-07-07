
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_cyware_orchestrate_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_push_alert_event_to_cyware_orchestrate_helper

class AlertActionWorkerpush_alert_event_to_cyware_orchestrate(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerpush_alert_event_to_cyware_orchestrate, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("cyware_url"):
            self.log_error('cyware_url is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("cyware_access_key"):
            self.log_error('cyware_access_key is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("cyware_secret_key"):
            self.log_error('cyware_secret_key is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("event_title"):
            self.log_error('event_title is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("event_type"):
            self.log_error('event_type is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_push_alert_event_to_cyware_orchestrate_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerpush_alert_event_to_cyware_orchestrate("TA-cyware-orchestrate", "push_alert_event_to_cyware_orchestrate").run(sys.argv)
    sys.exit(exitcode)


# encoding = utf-8
# Always put this line at the beginning of this file
import ta_fortinetar_declare 

import os
import sys
import eventlet_util

eventlet_util.monkey_patch()

from alert_actions_base import ModularAlertBase 
import modalert_FortiGateActions_helper

class AlertActionWorkerFortiGateActions(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerFortiGateActions, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("device_mappings"):
            self.log_error('device_mappings is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("fieldname"):
            self.log_error('fieldname is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            self.prepare_meta_for_cam()

            if not self.validate_params():
                return 3 
            status = modalert_FortiGateActions_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            import traceback; self.log_error(traceback.format_exc())
            self.log_error("Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(ae))
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(e))
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status

if __name__ == "__main__":
    exitcode = AlertActionWorkerFortiGateActions("TA-FortinetAR", "FortiGateActions").run(sys.argv)
    sys.exit(exitcode)

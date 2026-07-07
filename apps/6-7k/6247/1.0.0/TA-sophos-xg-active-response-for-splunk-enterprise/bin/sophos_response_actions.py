
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_sophos_xg_active_response_for_splunk_enterprise_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_sophos_response_actions_helper

class AlertActionWorkersophos_response_actions(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkersophos_response_actions, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("device_mappings"):
            self.log_error('device_mappings is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("parameter"):
            self.log_error('parameter is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("block_field"):
            self.log_error('block_field is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("firewall_group"):
            self.log_error('firewall_group is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("rule_name"):
            self.log_error('rule_name is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("host_name"):
            self.log_error('host_name is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_sophos_response_actions_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkersophos_response_actions("TA-sophos-xg-active-response-for-splunk-enterprise", "sophos_response_actions").run(sys.argv)
    sys.exit(exitcode)

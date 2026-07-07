
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_ksi_splunk_addon_for_aws_waf_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_aws_waf_auto_block_ip_helper

class AlertActionWorkeraws_waf_auto_block_ip(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkeraws_waf_auto_block_ip, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("aws_region_name"):
            self.log_error('aws_region_name is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("waf_ipsetid"):
            self.log_error('waf_ipsetid is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("param_store_to_query"):
            self.log_error('param_store_to_query is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("param_store_to_update"):
            self.log_error('param_store_to_update is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("ip_address"):
            self.log_error('ip_address is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_aws_waf_auto_block_ip_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkeraws_waf_auto_block_ip("TA-ksi-splunk-addon-for-aws-waf", "aws_waf_auto_block_ip").run(sys.argv)
    sys.exit(exitcode)

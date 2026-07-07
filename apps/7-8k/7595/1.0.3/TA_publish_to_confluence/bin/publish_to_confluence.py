# encoding = utf-8
import import_declare_test

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
from ta_publish_to_confluence import modalert_publish_to_confluence_helper


class AlertActionWorkerpublish_to_confluence(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerpublish_to_confluence, self).__init__(ta_name, alert_name)

    def validate_params(self):


        if not self.get_param("account"):
            self.log_error('account is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("pageid"):
            self.log_error('pageid is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("action"):
            self.log_error('action is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_publish_to_confluence_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error("Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(str(ae)))#ae.message replaced with str(ae)
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(str(e)))
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status

if __name__ == "__main__":
    exitcode = AlertActionWorkerpublish_to_confluence("TA_publish_to_confluence", "publish_to_confluence").run(sys.argv)
    sys.exit(exitcode)

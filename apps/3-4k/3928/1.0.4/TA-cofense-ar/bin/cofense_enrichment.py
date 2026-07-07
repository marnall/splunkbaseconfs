
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_cofense_ar_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_cofense_enrichment_helper

class AlertActionWorkercofense_enrichment(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkercofense_enrichment, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("search_type"):
            self.log_error('search_type is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("search_for"):
            self.log_error('search_for is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("time_frame"):
            self.log_error('time_frame is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_cofense_enrichment_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error("Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(ae.message))
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if e.message:
                self.log_error(msg.format(e.message))
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status

if __name__ == "__main__":
    exitcode = AlertActionWorkercofense_enrichment("TA-cofense-ar", "cofense_enrichment").run(sys.argv)
    sys.exit(exitcode)

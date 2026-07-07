# encoding = utf-8
# Always put this line at the beginning of this file
import import_declare_test

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
from sa_dashboard_generator import modalert_generate_dashboards_helper

class AlertActionWorkergenerate_dashboards(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkergenerate_dashboards, self).__init__(ta_name, alert_name)

    def validate_params(self):


        if not self.get_param("src_app"):
            self.log_error('src_app is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("template_dashboard_id"):
            self.log_error('template_dashboard_id is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_generate_dashboards_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkergenerate_dashboards("SA-dashboard_generator", "generate_dashboards").run(sys.argv)
    sys.exit(exitcode)

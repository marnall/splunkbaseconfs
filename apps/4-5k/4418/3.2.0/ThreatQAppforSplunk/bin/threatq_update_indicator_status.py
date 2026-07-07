# encoding = utf-8
# Always put this line at the beginning of this file
import threatquotient_app_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_threatq_update_indicator_status_helper


class AlertActionWorkerthreatq_update_indicator_status(ModularAlertBase):
    def __init__(self, app_name, alert_name):
        super(AlertActionWorkerthreatq_update_indicator_status, self).__init__(app_name, alert_name)

    def validate_params(self):

        if not self.get_param("status"):
            self.log_error(
                "message=update_indicator_status_error | validate_params_status_error |"
                " status is a mandatory parameter, but its value is None.")
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_threatq_update_indicator_status_helper.process_event(
                self, *args, **kwargs
            )
        except (AttributeError, TypeError) as ae:
            self.log_error(
                "message=update_indicator_status_error | process_event_attributes_error |"
                "Error: {}. Please double check spelling and also verify that a\
                compatible version of Splunk_SA_CIM is installed.".format(
                    str(ae)
                )
            )
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(
                    "message=update_indicator_status_error | process_event_error |"
                    "{}".format(msg.format(str(e))))
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status


if __name__ == "__main__":
    exitcode = AlertActionWorkerthreatq_update_indicator_status(
        "ThreatQAppforSplunk", "threatq_update_indicator_status"
    ).run(sys.argv)
    sys.exit(exitcode)

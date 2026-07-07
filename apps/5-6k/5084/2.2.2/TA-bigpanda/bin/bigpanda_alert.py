

# encoding = utf-8
# Always put this line at the beginning of this file
import ta_bigpanda_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_bigpanda_alert_helper


class AlertActionWorkerbigpanda_alert(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerbigpanda_alert, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("app_key"):
            self.log_error('app_key is a mandatory setup parameter, but its value is None.')
            return False

        if (os.environ.get('BIGPANDA_USE_ENV_PASSWORDS') and not os.environ.get('BIGPANDA_BEARER_TOKEN')) or (not os.environ.get('BIGPANDA_USE_ENV_PASSWORDS') and not self.get_global_setting("token")):
            self.log_error('token is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_global_setting("api_url"):
            self.log_error('api_url is a mandatory setup parameter, but its value is None.')
            return False

        if not self.get_param("status"):
            self.log_error('status is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_bigpanda_alert_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerbigpanda_alert("TA-bigpanda", "bigpanda_alert").run(sys.argv)
    sys.exit(exitcode)

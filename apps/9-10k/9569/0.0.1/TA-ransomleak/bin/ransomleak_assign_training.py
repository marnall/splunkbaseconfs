# encoding = utf-8
# Always put this line at the beginning of this file
import import_declare_test

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
import ransomleak_assign_training_handler

class AlertActionWorkerransomleak_assign_training(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerransomleak_assign_training, self).__init__(ta_name, alert_name)

    def validate_params(self):


        if not self.get_param("account"):
            self.log_error('account is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("exercise_slug"):
            self.log_error('exercise_slug is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("email_field"):
            self.log_error('email_field is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("reassign_period"):
            self.log_error('reassign_period is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("max_assignments"):
            self.log_error('max_assignments is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = ransomleak_assign_training_handler.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkerransomleak_assign_training("TA-ransomleak", "ransomleak_assign_training").run(sys.argv)
    sys.exit(exitcode)

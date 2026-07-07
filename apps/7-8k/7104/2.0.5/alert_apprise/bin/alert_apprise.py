# encoding = utf-8
import os
import import_declare_test
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunktaucclib.alert_actions_base import ModularAlertBase
from alert_apprise import modalert_alert_apprise_helper

class AlertActionWorkeralert_apprise(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkeralert_apprise, self).__init__(ta_name, alert_name)

    def validate_params(self):
        # Body is required
        if not self.get_param("body"):
            self.log_error('body is a mandatory parameter, but its value is None.')
            return False
        
        # Either URL or tag must be specified
        url = self.get_param("url")
        tag = self.get_param("tag")
        
        if not url and not tag:
            self.log_error("A URL or tag needs to be specified.")
            return False
        
        # If using tag, config file must be set in settings
        if tag:
            config_file = self.get_global_setting("config_file")
            if not config_file:
                self.log_error("Using a tag requires setting a configuration file in the setup page.")
                return False
            
            if not os.path.exists(config_file):
                self.log_error("Unable to locate config file: {}".format(config_file))
                return False
        
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_alert_apprise_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error("Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(str(ae)))
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
    exitcode = AlertActionWorkeralert_apprise("alert_apprise", "alert_apprise").run(sys.argv)
    sys.exit(exitcode)

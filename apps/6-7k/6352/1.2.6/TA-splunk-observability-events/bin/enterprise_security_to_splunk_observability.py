
# encoding = utf-8
# Always put this line at the beginning of this file
import ta_splunk_observability_events_declare

import os
import sys

from alert_actions_base import ModularAlertBase
import modalert_enterprise_security_to_splunk_observability_helper

class AlertActionWorkerenterprise_security_to_splunk_observability(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerenterprise_security_to_splunk_observability, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("observability_api_token"):
            self.log_error('observability_api_token is a mandatory setup parameter, but its value is None.')
            self.addevent("observability_api_token is a mandatory setup parameter, but its value is None.", sourcetype="observability_events")
            self.writeevents(index="_internal", source="observability_events") 
            return False

        if not self.get_param("realm"):
            self.log_error('realm is a mandatory parameter, but its value is None.')
            self.addevent("realm is a mandatory parameter, but its value is None.", sourcetype="observability_events")
            self.writeevents(index="_internal", source="observability_events") 
            return False

        if not self.get_param("info_field"):
            self.log_error('info_field is a mandatory parameter, but its value is None.')
            self.addevent("info_field is a mandatory parameter, but its value is None.", sourcetype="observability_events")
            self.writeevents(index="_internal", source="observability_events") 
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_enterprise_security_to_splunk_observability_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error("Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(str(ae)))
            self.addevent("Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(str(ae)), sourcetype="observability_events")
            self.writeevents(index="_internal", source="observability_events") 
            return 4
        except Exception as e:
            msg = "ERROR Unexpected error in observability_events: {}."
            if e:
                self.log_error(msg.format("error with field: " + str(e)))
                self.addevent(msg.format("error with field: " + str(e)), sourcetype="observability_events")
                self.writeevents(index="_internal", source="observability_events")  
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
                self.addevent(msg.format(traceback.format_exc()), sourcetype="observability_events")
                self.writeevents(index="_internal", source="observability_events")  
            return 5
        return status


if __name__ == "__main__":
    exitcode = AlertActionWorkerenterprise_security_to_splunk_observability("TA-splunk-observability-events", "enterprise_security_to_splunk_observability").run(sys.argv)
    sys.exit(exitcode)

# encoding = utf-8
# Always put this line at the beginning of this file
"""Splunk custom alert action wrapper for Slack Bot Alert Connector for Splunk.

Splunk executes this file for the configured alert action. The wrapper handles
parameter validation and delegates the Slack-specific work to
``slack_bot_alert_connector_implementation``.
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import import_declare_test

from splunktaucclib.alert_actions_base import ModularAlertBase

import slack_bot_alert_connector_implementation


class AlertActionWorkerSlackBotAlertConnector(ModularAlertBase):
    """Validate Splunk alert parameters and invoke the Slack implementation."""

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerSlackBotAlertConnector, self).__init__(ta_name, alert_name)

    def validate_params(self):
        """Require the minimum fields needed to send a Slack alert."""
        if not self.get_param("channel"):
            self.log_error('channel is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("message"):
            self.log_error('message is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        """Run one alert action event and redact sensitive values on failures."""
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = slack_bot_alert_connector_implementation.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            error = slack_bot_alert_connector_implementation.redact_sensitive_text(str(ae))
            self.log_error("Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(error))
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(slack_bot_alert_connector_implementation.redact_sensitive_text(str(e))))
            else:
                import traceback
                self.log_error(msg.format(slack_bot_alert_connector_implementation.redact_sensitive_text(traceback.format_exc())))
            return 5
        return status

if __name__ == "__main__":
    exitcode = AlertActionWorkerSlackBotAlertConnector("ta-slack-bot-alert-connector", "slack_bot_alert_connector").run(sys.argv)
    sys.exit(exitcode)

# encoding = utf-8
# Always put this line at the beginning of this file

import sys

import ta_addonphantom_declare  # noqa: F401

from alert_actions_base import ModularAlertBase
import modalert_phantom_event_forwarding_helper


class AlertActionWorkerphantomeventforwarding(ModularAlertBase):
    def __init__(self, ta_name, alert_name):
        super().__init__(ta_name, alert_name)

    def validate_params(self):
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_phantom_event_forwarding_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error(
                f"Error: {ae!s}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed."
            )
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
    exitcode = AlertActionWorkerphantomeventforwarding("TA-test", "event_forwarding").run(sys.argv)
    sys.exit(exitcode)

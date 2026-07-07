#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import sys

import modalert_snow_record_helper
from alert_actions_base import ModularAlertBase


class AlertActionWorkersnow_record(ModularAlertBase):
    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkersnow_record, self).__init__(ta_name, alert_name)

    def validate_params(self):
        """Validate the input params of alert action."""
        if not self.get_param("account"):
            self.log_error("account is a mandatory parameter, but its value is None.")
            return False

        if not self.get_param("table_name"):
            self.log_error(
                "table_name is a mandatory parameter, but its value is None."
            )
            return False

        if not self.get_param("fields"):
            self.log_error("fields is a mandatory parameter, but its value is None.")
            return False
        return True

    def process_event(self, *args, **kwargs):
        """
        Process the event that trigger the alert action.

        :return status: Return the exit code 0 if sucessfull else non-zero.
        """
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_snow_record_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error(
                "Error: {}. Double check spelling and also verify that a compatible version of "
                "Splunk_SA_CIM is installed.".format(str(ae))
            )
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
    exitcode = AlertActionWorkersnow_record("Splunk_TA_snow", "snow_record").run(
        sys.argv
    )
    sys.exit(exitcode)

# encoding = utf-8
#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test

import os
import sys

import modalert_alert_pantag_helper
from splunktaucclib.alert_actions_base import ModularAlertBase


class AlertActionWorkeralert_pantag(ModularAlertBase):
    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkeralert_pantag, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("hostname"):
            self.log_error("hostname is a mandatory parameter, but its value is None.")
            return False

        if not self.get_param("action"):
            self.log_error("action is a mandatory parameter, but its value is None.")
            return False

        if not self.get_param("tags"):
            self.log_error("tags is a mandatory parameter, but its value is None.")
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_alert_pantag_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error(
                "Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(
                    str(ae)
                )
            )  # ae.message replaced with str(ae)
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(str(e)))  # e.message replaced with str(ae)
            else:
                import traceback

                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status


if __name__ == "__main__":
    exitcode = AlertActionWorkeralert_pantag(
        "Splunk_TA_paloalto_networks", "alert_pantag"
    ).run(sys.argv)
    sys.exit(exitcode)

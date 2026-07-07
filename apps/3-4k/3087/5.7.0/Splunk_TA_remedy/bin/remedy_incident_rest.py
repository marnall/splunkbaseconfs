# encoding = utf-8
#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""

* isort ignores:
- isort: skip = Should not be sorted.
* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""

import splunk_ta_remedy_declare  # isort: skip # noqa: F401

import sys

import modalert_remedy_incident_rest_helper
from alert_actions_base import ModularAlertBase


class AlertActionWorkerremedy_incident_rest(ModularAlertBase):
    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerremedy_incident_rest, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("account"):
            self.log_error("account is a mandatory parameter, but its value is None.")
            return False

        if not self.get_param("impact"):
            self.log_error("impact is a mandatory parameter, but its value is None.")
            return False

        if not self.get_param("urgency"):
            self.log_error("urgency is a mandatory parameter, but its value is None.")
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_remedy_incident_rest_helper.process_event(
                self, *args, **kwargs
            )
        except (AttributeError, TypeError) as ae:
            self.log_error(
                "Error: {}. Please double check spelling and also verify "
                "that a compatible version of Splunk_SA_CIM is installed.".format(
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
    exitcode = AlertActionWorkerremedy_incident_rest(
        "Splunk_TA_remedy", "remedy_incident_rest"
    ).run(sys.argv)
    sys.exit(exitcode)

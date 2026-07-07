# encoding = utf-8

import ta_netskopeappforsplunk_declare   # noqa: F401

import sys

from alert_actions_base import ModularAlertBase
import modalert_netskope_quarantine_file_helper


class AlertActionWorkernetskope_quarantine_file(ModularAlertBase):
    def __init__(self, ta_name, alert_name):
        super(
            AlertActionWorkernetskope_quarantine_file, self
        ).__init__(ta_name, alert_name)

    def validate_params(self):
        if not self.get_param("storage_account"):
            self.log_error(
                "storage_account is a mandatory parameter, but its value is None."
            )
            return False
        return True

    def process_event(self, *args, **kwargs):
        self.log_info("Alert script started...")
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = (
                modalert_netskope_quarantine_file_helper.process_event(
                    self, *args, **kwargs
                )
            )
        except (AttributeError, TypeError) as ae:
            self.log_error(
                "Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(
                    str(ae)
                )
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
    exitcode = AlertActionWorkernetskope_quarantine_file(
        "TA-NetSkopeAppForSplunk", "netskope_quarantine_file"
    ).run(sys.argv)
    sys.exit(exitcode)

# encoding = utf-8
# Always put this line at the beginning of this file
import soctoolkit_connector_ta_nxtp_declare

import sys

from alert_actions_base import ModularAlertBase
import modalert_send_to_soc_toolkit_helper


class AlertActionWorkersend_to_soc_toolkit(ModularAlertBase):
    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkersend_to_soc_toolkit, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_global_setting("iam"):
            self.log_error("iam is a mandatory setup parameter, but its value is None.")
            return False

        if not self.get_global_setting("realm"):
            self.log_error("realm is a mandatory setup parameter, but its value is None.")
            return False

        if not self.get_global_setting("domain"):
            self.log_error("domain is a mandatory setup parameter, but its value is None.")
            return False

        if not self.get_global_setting("client_id"):
            self.log_error("client_id is a mandatory setup parameter, but its value is None.")
            return False

        if not self.get_global_setting("client_secret"):
            self.log_error("client_secret is a mandatory setup parameter, but its value is None.")
            return False

        if not self.get_param("case_name"):
            self.log_error("case_name is a mandatory parameter, but its value is None.")
            return False

        if not self.get_param("playbook"):
            self.log_error("playbook is a mandatory parameter, but its value is None.")
            return False

        if not self.get_param("integrations"):
            self.log_error("integrations is a mandatory parameter, but its value is None.")
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_send_to_soc_toolkit_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkersend_to_soc_toolkit(
        "SOCToolkit_Connector_TA_nxtp", "send_to_soc_toolkit"
    ).run(sys.argv)
    sys.exit(exitcode)

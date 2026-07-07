# encoding = utf-8
# Always put this line at the beginning of this file

import sys

import ta_addonphantom_declare  # noqa: F401

from alert_actions_base import ModularAlertBase
import modalert_phantom_forward_helper

from phantom_utils import get_search_description


class AlertActionWorkersendtophantom(ModularAlertBase):
    def __init__(self, ta_name, alert_name):
        super().__init__(ta_name, alert_name)
        self.get_search_description()
        if self.settings["configuration"].get("phantom_server", "").endswith(" (ARR)"):
            ## NEW FOR CIM 4.12
            ## Call our queuework method() to support distributed AR actions
            self.queuework()

    def validate_arr(self, config):
        if "_cam_workers" in config and config.get("_cam_workers") in ["", '["local"]']:
            self.log_error("Worker Set provided was 'local', but an ARR server was provided")
            return False
        return True

    def validate_params(self):
        config = self.settings["configuration"]
        if len(config["phantom_server"]) == 0:
            self.log_error("Required field 'SOAR Instance' missing")
            return False
        if len(config["severity"]) == 0:
            self.log_error("Required field 'severity' missing")
            return False
        return True

    def get_search_description(self):
        search_name = self.settings.get("search_name", "")
        try:
            search_description = get_search_description(self, search_name)
            if search_description:
                self.settings["configuration"]["search_description"] = search_description
        except Exception:
            pass

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            config = self.settings["configuration"]
            if config.get("phantom_server", "").endswith(" (ARR)"):
                if not self.validate_arr(config):
                    return 3

            if not self.validate_params():
                return 3

            status = modalert_phantom_forward_helper.process_event(self, *args, **kwargs)
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
    exitcode = AlertActionWorkersendtophantom("phantom", "sendtophantom").run(sys.argv)
    sys.exit(exitcode)

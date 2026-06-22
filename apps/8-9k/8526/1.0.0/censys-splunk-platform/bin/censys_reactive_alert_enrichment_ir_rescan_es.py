# encoding = utf-8
# Always put this line at the beginning of this file
import import_declare_test  # noqa: F401

import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
from censys_app import modalert_censys_reactive_alert_enrichment_ir_rescan_es_helper


class AlertActionWorkercensys_reactive_alert_enrichment_ir_rescan_es(ModularAlertBase):
    """Alert action worker for censys reactive alert enrichment IR rescan."""

    def __init__(self, ta_name, alert_name):
        """Initialize alert action worker."""
        super(
            AlertActionWorkercensys_reactive_alert_enrichment_ir_rescan_es, self
        ).__init__(ta_name, alert_name)

    def validate_params(self):
        """Validate parameters."""
        if not self.get_param("global_account"):
            self.log_error(
                "global_account is a mandatory parameter, but its value is None."
            )
            return False

        if not self.get_param("indicator_type"):
            self.log_error(
                "indicator_type is a mandatory parameter, but its value is None."
            )
            return False
        return True

    def process_event(self, *args, **kwargs):
        """Process event."""
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_censys_reactive_alert_enrichment_ir_rescan_es_helper.process_event(
                self, *args, **kwargs
            )
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
    exitcode = AlertActionWorkercensys_reactive_alert_enrichment_ir_rescan_es(
        "censys-splunk-platform", "censys_reactive_alert_enrichment_ir_rescan_es"
    ).run(sys.argv)
    sys.exit(exitcode)

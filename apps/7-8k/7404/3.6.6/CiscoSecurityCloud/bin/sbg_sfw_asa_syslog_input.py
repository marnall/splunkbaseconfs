import sys  # noqa: I001

import import_declare_test  # noqa

from splunklib import modularinput as smi

from CiscoSecurityCloud.utils import create_and_configure_logger
from CiscoSecurityCloud.sfw_syslog.event_logger import SFWSyslogEventLogger

LOGGER = create_and_configure_logger(__name__)
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class SBGASASyslogInput(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("SBG ASA Syslog Input")
        scheme.description = "Get log data from the ASA Syslog"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument(
                "port",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "restrictToHost",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "type",
                required_on_create=False,
            )
        )
        return scheme

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            try:
                LOGGER.info(f"Start ASA_Syslog input: {normalized_input_name}")
                session_key = self._input_definition.metadata["session_key"]

                SFWSyslogEventLogger(
                    normalized_input_name, input_item, session_key
                ).log_events_throughput_and_status()

                LOGGER.info(f"Finish ASA_Syslog input: {normalized_input_name}")

            except Exception as e:
                LOGGER.info(f"Exception during executing ASA_Syslog input: {e}")
                pass


if __name__ == "__main__":
    exit_code = SBGASASyslogInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover

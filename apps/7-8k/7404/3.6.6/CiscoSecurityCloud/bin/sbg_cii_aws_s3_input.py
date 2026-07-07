import sys  # noqa: I001

import import_declare_test  # noqa

from splunklib import modularinput as smi

from CiscoSecurityCloud.utils import create_and_configure_logger
from CiscoSecurityCloud.cii.aws_s3_connection.event_logger import CIIAWSS3EventLogger

LOGGER = create_and_configure_logger(__name__)
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class CIIAWSS3Input(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("Cisco Identity Intelligence AWS S3 Input")
        scheme.description = "Cisco Identity Intelligence AWS S3 Input"
        scheme.use_external_validation = False
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "port",
                title="Port",
                description="Port for Http Event Collector",
                required_on_create=False,
            )
        )
        return scheme

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            try:
                LOGGER.info(f"Start CII AWS S3 input: {normalized_input_name}")
                session_key = self._input_definition.metadata["session_key"]

                CIIAWSS3EventLogger(
                    normalized_input_name, input_item, session_key
                ).log_events()

                LOGGER.info(f"Finish CII AWS S3 input: {normalized_input_name}")
            except Exception as e:
                LOGGER.info(f"Exception during executing CII AWS S3 input: {e}")
                pass


if __name__ == "__main__":
    exit_code = CIIAWSS3Input().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover

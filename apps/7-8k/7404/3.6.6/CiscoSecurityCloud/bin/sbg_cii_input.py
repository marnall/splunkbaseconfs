import sys  # noqa: I001

import import_declare_test  # noqa
from CiscoSecurityCloud.cii.webhook_connection.event_logger import CIIEventLogger
from CiscoSecurityCloud.utils import create_and_configure_logger
from splunklib import modularinput as smi

LOGGER = create_and_configure_logger(__name__)
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class CIIInput(smi.Script):
    """A base class that extends :class:`smi.Script`
    for implementing modular input Cisco Identity Intelligence

    Methods ``get_scheme``, ``stream_events``
    """
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        """The scheme defines the parameters understood by this modular input.

        :return: ``Scheme`` object representing the parameters for this modular input.
        """
        scheme = smi.Scheme("Cisco Identity Intelligence Input")
        scheme.description = "Cisco Identity Intelligence Input"
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
        """The method called to stream events into Splunk.
        It should do all its output through an EventWriter,
        which writes events and error messages from the module input.

        :param inputs: An ``InputDefinition`` object.
        :param event_writer: An object with methods to write events and log messages to
        Splunk.
        """
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            try:
                LOGGER.info(f"Start CII input: {normalized_input_name}")
                session_key = self._input_definition.metadata["session_key"]

                CIIEventLogger(
                    normalized_input_name, input_item, session_key
                ).log_events()

                LOGGER.info(f"Finish CII input: {normalized_input_name}")
            except Exception as e:
                LOGGER.info(f"Exception during executing CII input: {e}")
                pass


if __name__ == "__main__":
    exit_code = CIIInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover

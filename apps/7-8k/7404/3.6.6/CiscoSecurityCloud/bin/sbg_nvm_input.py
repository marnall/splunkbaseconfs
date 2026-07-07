import sys  # noqa: I001

import import_declare_test  # noqa

from splunklib import modularinput as smi

from CiscoSecurityCloud.nvm.event_logger import NVMEventLogger
from CiscoSecurityCloud.utils import create_and_configure_logger


LOGGER = create_and_configure_logger(__name__)
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class CiscoNVMInput(smi.Script):
    """A base class that extends :class:`smi.Script`
    for implementing modular input Cisco NVM.

    Methods ``get_scheme`` and ``stream_events``.
    """
    def __init__(self):
        super().__init__()

    def get_scheme(self) -> smi.Scheme:
        """The scheme defines the parameters understood by this modular input.

        :return: ``Scheme`` object representing the parameters for this modular input.
        """
        scheme = smi.Scheme("Cisco NVM Input")
        scheme.description = "Cisco NVM Input"
        scheme.use_external_validation = True
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

    def stream_events(
            self, inputs: smi.InputDefinition, event_writer: smi.EventWriter
    ) -> None:
        """The method called to stream events into Splunk. It should do all of its
        output via EventWriter rather than assuming that there is a console attached.

        :param inputs: An ``InputDefinition`` object.
        :param event_writer: An object with methods to write events and log messages to
        Splunk.
        """
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            try:
                LOGGER.info(f"Start NVM input: {normalized_input_name}")
                session_key = self._input_definition.metadata["session_key"]

                NVMEventLogger(
                    normalized_input_name, input_item, session_key
                ).log_events()

                LOGGER.info(f"Finish NVM input: {normalized_input_name}")
            except Exception as e:
                LOGGER.info(f"Exception during executing NVM input: {e}")
                pass


if __name__ == "__main__":
    exit_code = CiscoNVMInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover

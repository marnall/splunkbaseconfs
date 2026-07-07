import sys  # noqa: I001

import import_declare_test # noqa

from splunklib import modularinput as smi

from CiscoSecurityCloud.utils import create_and_configure_logger
from CiscoSecurityCloud.secure_workload.event_logger import SecureWorkloadEventLogger

LOGGER = create_and_configure_logger(__name__)


class SBGSecureWorkloadInput(smi.Script):
    """A base class that extends :class:`smi.Script`
    for implementing modular input Secure Workload.

    Methods ``get_scheme`` and ``stream_events``.
    """
    def __init__(self):
        super(SBGSecureWorkloadInput, self).__init__()

    def get_scheme(self) -> smi.Scheme:
        """The scheme defines the parameters understood by this modular input.

        :return: ``Scheme`` object representing the parameters for this modular input.
        """
        scheme = smi.Scheme("sbg_sw_input")
        scheme.description = "Get log data from the Cisco Secure Workload"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "port",
                required_on_create=True,
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
                required_on_create=True,
            )
        )
        return scheme

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter) -> None:
        """The method called to stream events into Splunk. It should do all of its
        output via EventWriter rather than assuming that there is a console attached.

        :param inputs: An ``InputDefinition`` object.
        :param ew: An object with methods to write events and log messages to
        Splunk.
        """
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            try:
                LOGGER.info("Start Secure Workload Runtime Security input: "
                            f"{normalized_input_name}")
                session_key = self._input_definition.metadata["session_key"]

                SecureWorkloadEventLogger(
                    normalized_input_name, input_item, session_key
                ).log_events_throughput_and_status()

                LOGGER.info(
                    f"Finish Secure Workload input: {normalized_input_name}"
                )
            except Exception as e:
                LOGGER.info(
                    f"Exception during executing Secure Workload input: {e}"
                )
                pass


if __name__ == "__main__":
    exit_code = SBGSecureWorkloadInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover

import sys
import import_declare_test  # noqa: F401
from splunklib import modularinput as smi
from dataminr_alerts_collector import DataminrAlertsCollectorPulse


class Input(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        """Overloaded splunklib modularinput method."""
        scheme = smi.Scheme("dataminr_api_v4")
        scheme.description = "dataminr_api_v4 input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )
        scheme.add_argument(smi.Argument("dataminr_account", title="Dataminr Account",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("alert_type", title="Alert Type",
                                         description="Select Alert Type(s) to collect.",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("lists_names", title="List Names",
                                         description="Select Lists Names from which to collect Alerts.",
                                         required_on_create=True,
                                         required_on_edit=False))
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        """Validate the input stanza."""
        return

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        """Write out the events."""
        dm_collector = DataminrAlertsCollectorPulse(inputs, event_writer)
        dm_collector.collect_events()


if __name__ == "__main__":
    exit_code = Input().run(sys.argv)
    sys.exit(exit_code)

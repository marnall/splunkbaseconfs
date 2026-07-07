import import_declare_test  # noqa F401

import sys

from splunklib import modularinput as smi
from event_input import ThousandEyesEventCollector


class EVENT(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("event")
        scheme.description = "Event"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "thousandeyes_user",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "thousandeyes_acc_group",
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        event_collector = ThousandEyesEventCollector(inputs, ew)
        event_collector.collect_events()


if __name__ == "__main__":
    exit_code = EVENT().run(sys.argv)
    sys.exit(exit_code)

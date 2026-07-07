import import_declare_test  # noqa F401

import sys

from splunklib import modularinput as smi


class ACTIVITY(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("activity_logs_stream")
        scheme.description = "Activity logs Stream"
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
        scheme.add_argument(
            smi.Argument(
                "hec_target",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "hec_token",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "activity_index",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "thousandeyes_stream_id",
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        pass


if __name__ == "__main__":
    exit_code = ACTIVITY().run(sys.argv)
    sys.exit(exit_code)

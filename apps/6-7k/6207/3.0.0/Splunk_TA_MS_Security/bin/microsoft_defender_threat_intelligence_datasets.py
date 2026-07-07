##
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test  # noqa: F401 isort: skip

import sys
import traceback

from splunklib import modularinput

from splunk_ta_mscs.app.mdti.collector import MDTIInputCollectorApp
from splunk_ta_mscs.app.mdti.di import MDTIDatasetsInputContext, AppLogContext
from splunk_ta_mscs.app.mdti.rest_model import endpoint
from splunk_ta_mscs.utils.splunklib_utils import inject_rest_to_splunklib_arguments


class MicrosoftDefenderTIArticlesInput(modularinput.Script):
    def get_scheme(self) -> modularinput.Scheme:
        scheme = modularinput.Scheme(endpoint.input_type)
        scheme.description = "Microsoft Defender Threat Intelligence Datasets"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            modularinput.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )

        inject_rest_to_splunklib_arguments(scheme=scheme, model=endpoint)

        return scheme

    def stream_events(
        self, inputs: modularinput.InputDefinition, ew: modularinput.EventWriter
    ) -> None:
        for input_name, input_config in inputs.inputs.items():
            app_ctx = MDTIDatasetsInputContext(
                splunk_app_name=input_config["__app"],
                rest_session_key=inputs.metadata["session_key"],
                input_config_dict=input_config,
                input_name=input_name.split("://")[1],
            )
            try:
                app: MDTIInputCollectorApp = app_ctx.input_collector_app()
                app.run()
            except Exception as e:
                app_ctx.base_logger.error(vars(e))
                app_ctx.base_logger.error(
                    f"Failed to run collection. Traceback: {traceback.format_exc()}"
                )
                raise


if __name__ == "__main__":
    exit_code = 1
    try:
        exit_code = MicrosoftDefenderTIArticlesInput().run(sys.argv)
    finally:
        sys.exit(exit_code)

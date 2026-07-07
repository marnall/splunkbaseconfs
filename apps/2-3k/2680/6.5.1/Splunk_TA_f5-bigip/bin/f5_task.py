##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test  # noqa: F401 isort: skip
import os
import sys
import traceback
import logging

from log_manager import setup_logging


from splunklib import modularinput as smi  # noqa: E402
from splunktaucclib.rest_handler.error import RestError  # noqa: E402

PARENT = os.path.sep + os.path.pardir
APP_PATH = os.path.abspath(__file__ + PARENT + os.path.sep + "Splunk_TA_f5_bigip")
sys.path.append(APP_PATH)


class F5_TASK(smi.Script):
    def __init__(self):
        super(F5_TASK, self).__init__()
        self.logfile_prefix = "splunk_ta_f5_bigip_input"

    def get_scheme(self):
        scheme = smi.Scheme("f5_task")
        scheme.description = "Input"
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
                "description",
                title="Description",
                description="Description for the Input",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "hec_name",
                title="HEC Name",
                description="Provide the Hec Token on which you want to collect the data.",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "servers",
                title="Servers",
                description="Select one or more servers from which you want to collect data",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "templates",
                title="Templates",
                description="Select one or more templates that describe the data you want to collect.",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        session_key = self.service.token
        try:
            for input_name, input_item in inputs.inputs.items():
                input_item["name"] = input_name.replace("f5_task://", "")
                self.logger = setup_logging(
                    session_key, f"{self.logfile_prefix}-{input_item['name']}"
                )
                self.logger.info(
                    "log level set is : {}".format(
                        logging.getLevelName(self.logger.level)
                    )
                )
                self.logger.info(
                    "Invoking process to collect events for input : {}".format(
                        input_item["name"]
                    )
                )
                sys.path.insert(
                    0,
                    os.path.abspath(
                        os.path.join(__file__, "..", "modinputs", "icontrol")
                    ),
                )
                import collector

                icontrol_collector = collector.IcontrolCollector(
                    session_key, input_item, "enabled", self.logger
                )
                failed_api_call = icontrol_collector.run()
                if not failed_api_call:
                    self.logger.info(
                        "Successfully verified/executed the data collection for enabled input: {}".format(
                            input_item["name"]
                        )
                    )
                else:
                    self.logger.error(
                        "Failed to execute the following api calls for enabled input: {}".format(
                            failed_api_call
                        )
                    )
        except RestError as re:
            raise RestError(409, re)
        except ValueError as ve:  # noqa: F841
            raise RestError(
                409,
                "Stopping data collection because we are not having enough information. Please check if all the required fields are provided in the input.",  # noqa: E501
            )
        except Exception as e:  # noqa: F841
            self.logger.error(traceback.format_exc())


if __name__ == "__main__":
    exit_code = F5_TASK().run(sys.argv)
    sys.exit(exit_code)

#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import sys
import traceback

# isort: off
import import_declare_test  # noqa: F401

from cyberark_epm_connect import CyberarkConnect
from cyberark_epm_utils import (
    get_account_details,
    get_proxy_settings,
    set_logger,
    validate_inputs_policies_and_computers,
    add_ucc_error_logger,
)
from constants import (
    GENERAL_EXCEPTION,
    UCC_EXECPTION_EXE_LABEL,
)
from splunklib import modularinput as smi


class PoliciesAndComputers(smi.Script):
    """
    This class contains methods to collect and validate data of Policy Audit category
    """

    def __init__(self):
        super(PoliciesAndComputers, self).__init__()

    def get_scheme(self):
        """
        This method collects input data from arguments
        """

        scheme = smi.Scheme("policies_and_computers")
        scheme.description = "Policies and Computers"
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
                "account_name",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_data_for",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_policy_details",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition):
        """
        This method validates input arguments for the modular input
        """
        pass

    def stream_events(self, inputs, event_writer):
        """
        This method is invoked for each input repeatedly at configured interval
        :param inputs: Input arguments for the particular modular input
        :param event_writer: Event Writer object
        """

        self.session_key = self._input_definition.metadata["session_key"]
        _logger = set_logger(
            self.session_key,
            "splunk_ta_cyberark_epm_policies_and_computers_"
            + (list(inputs.inputs.keys())[0]).split("//")[1],
        )

        try:
            for input_name, input_items in inputs.inputs.items():
                input_items["input_name"] = input_name

            try:
                validate_inputs_policies_and_computers(input_items)
            except Exception as err:
                add_ucc_error_logger(
                    _logger,
                    GENERAL_EXCEPTION,
                    err,
                    exc_label=UCC_EXECPTION_EXE_LABEL.format(
                        (list(inputs.inputs.keys())[0]).replace("://", ":")
                    ),
                    msg_before="Input Validation Error in input '{}' ".format(
                        input_items["input_name"],
                    ),
                )
                sys.exit("Input Validation Error. Terminating.")

            account_name = input_items.get("account_name")
            account_details = get_account_details(
                _logger, self.session_key, account_name
            )
            collect_data_for = set(input_items["collect_data_for"].split(","))
            collect_policy_details = input_items["collect_policy_details"]

            config = {
                "category": "Policies and Computers",
                "session_key": self.session_key,
                "input_params": input_items,
                "logger": _logger,
            }
            config.update(account_details)
            config["proxies"] = get_proxy_settings(_logger, self.session_key)

            obj = CyberarkConnect(config)
            obj.collect_policies_and_computers(
                collect_data_for, collect_policy_details, event_writer
            )

        except Exception as e:
            add_ucc_error_logger(
                _logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=UCC_EXECPTION_EXE_LABEL.format(
                    (list(inputs.inputs.keys())[0]).replace("://", ":")
                ),
                msg_before="Error in Policies and Computers Modular Input",
            )


if __name__ == "__main__":
    exit_code = PoliciesAndComputers().run(sys.argv)
    sys.exit(exit_code)

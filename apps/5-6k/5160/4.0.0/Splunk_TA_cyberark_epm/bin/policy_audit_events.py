#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""Modular Input Script for Policy Audit Events"""

import sys
import traceback

# isort: off
import import_declare_test  # noqa: F401

from cyberark_epm_connect import CyberarkConnect
from cyberark_epm_utils import (
    get_account_details,
    get_proxy_settings,
    set_logger,
    validate_inputs_for_categories,
    add_ucc_error_logger,
)
from splunklib import modularinput as smi
from constants import (
    GENERAL_EXCEPTION,
    UCC_EXECPTION_EXE_LABEL,
)


class PolicyAuditEvents(smi.Script):
    """
    This class contains methods to collect and validate data of Policy Audit category
    """

    def __init__(self):
        super(PolicyAuditEvents, self).__init__()

    def get_scheme(self):
        """
        This method collects input data from arguments
        """

        scheme = smi.Scheme("policy_audit_events")
        scheme.description = "Policy Audit Events"
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
                "publisher",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "policy_name",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "justification",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "application_type",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "use_existing_checkpoint",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "start_date",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "api_type",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition):
        """
        This method validates input arguments for the modular input
        """

        validate_inputs_for_categories(definition.parameters)

    def stream_events(self, inputs, ew):
        """
        This method is invoked for each input repeatedly at configured interval
        :param inputs: Input arguments for the particular modular input
        :param event_writer: Event Writer object
        """

        self.session_key = self._input_definition.metadata["session_key"]
        _logger = set_logger(
            self.session_key,
            "splunk_ta_cyberark_epm_policy_audit_events_"
            + (list(inputs.inputs.keys())[0]).split("//")[1],
        )

        try:
            for input_name, input_items in inputs.inputs.items():
                input_items["input_name"] = input_name
            try:
                validate_inputs_for_categories(input_items)
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

            if input_items["api_type"] == "raw_events":
                input_items["sourcetype"] = "cyberark:epm:raw:policy:audit"
            else:
                input_items["sourcetype"] = "cyberark:epm:aggregated:policy:audit"
            input_items[
                "collection_name"
            ] = import_declare_test.COLLECTION_VALUE_FROM_ENDPOINT[
                "policy_audit_events"
            ]
            config = {
                "session_key": self.session_key,
                "input_params": input_items,
                "logger": _logger,
            }
            config.update(account_details)
            config["proxies"] = get_proxy_settings(_logger, self.session_key)

            obj = CyberarkConnect(config)
            obj.collect_data()
        except Exception as e:
            add_ucc_error_logger(
                _logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=UCC_EXECPTION_EXE_LABEL.format(
                    (list(inputs.inputs.keys())[0]).replace("://", ":")
                ),
                msg_before="Error in Policy Audit Events Modular Input",
            )


if __name__ == "__main__":
    exit_code = PolicyAuditEvents().run(sys.argv)
    sys.exit(exit_code)

#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""Modular Input Script for Threat Detection"""

import sys
import traceback

# isort: off
import import_declare_test  # noqa: F401

from old_cyberark_epm_connect import CyberarkConnect
from old_cyberark_epm_utils import (
    get_account_details,
    get_proxy_settings,
    set_logger,
    validate_inputs_for_categories,
)
from splunklib import modularinput as smi
from cyberark_epm_utils import add_ucc_error_logger
from constants import CONFIGURATION_ERROR, GENERAL_EXCEPTION, UCC_EXECPTION_EXE_LABEL


class ThreatDetection(smi.Script):
    """
    This class contains methods to collect and validate data of Policy Audit category
    """

    def __init__(self):
        super(ThreatDetection, self).__init__()

    def get_scheme(self):
        """
        This method collects input data from arguments
        """

        scheme = smi.Scheme("threat_detection")
        scheme.description = "Threat Detection"
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

        return scheme

    def validate_input(self, definition):
        """
        This method validates input arguments for the modular input
        """

        validate_inputs_for_categories(definition.parameters)

    def stream_events(self, inputs, event_writer):
        """
        This method is invoked for each input repeatedly at configured interval
        :param inputs: Input arguments for the particular modular input
        :param event_writer: Event Writer object

        This mod-input is deprecated.
        To collect similar data, configure new modinput - Inbox Events and select API type as aggregated events
        """

        self.session_key = self._input_definition.metadata["session_key"]
        _logger = set_logger(
            self.session_key,
            "splunk_ta_cyberark_epm_threat_detection_"
            + (list(inputs.inputs.keys())[0]).split("//")[1],
        )
        _logger.warning(
            "This mod-input is deprecated. "
            "To collect similar data, configure new modinput - Inbox Events and select API type as aggregated events"
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
            input_items["sourcetype"] = "cyberark:epm:threat:detection"
            config = {
                "category": "ThreatDetection",
                "session_key": self.session_key,
                "input_params": input_items,
                "logger": _logger,
            }
            config.update(account_details)
            config["proxies"] = get_proxy_settings(_logger, self.session_key)

            obj = CyberarkConnect(config)
            obj.collect_data(event_writer)

        except Exception as e:
            add_ucc_error_logger(
                _logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=UCC_EXECPTION_EXE_LABEL.format(
                    (list(inputs.inputs.keys())[0]).replace("://", ":")
                ),
                msg_before="Error in Threat Detection Modular Input.",
            )


if __name__ == "__main__":
    exit_code = ThreatDetection().run(sys.argv)
    sys.exit(exit_code)

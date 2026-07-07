#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""Modular Input Script for Application Events"""
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
from constants import *


class ApplicationEvents(smi.Script):
    """
    This class contains methods to collect and validate data of Application Events category
    """

    def __init__(self):
        super(ApplicationEvents, self).__init__()

    def get_scheme(self):
        """
        This method collects input data from arguments
        """

        scheme = smi.Scheme("application_events")
        scheme.description = "Application Events"
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
                "justification",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "application_type",
                required_on_create=True,
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
        This mod-input is deprecated.
        To collect similar data, configure new modinput - Inbox Events and select API type as aggregated events
        """
        self.session_key = self._input_definition.metadata["session_key"]
        _logger = set_logger(
            self.session_key,
            "splunk_ta_cyberark_epm_application_events_"
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
                msg = "Input Validation Error. Terminating"
                add_ucc_error_logger(
                    _logger,
                    CONFIGURATION_ERROR,
                    err,
                    msg_before=msg,
                )
                sys.exit(msg)

            account_name = input_items.get("account_name")
            account_details = get_account_details(
                _logger, self.session_key, account_name
            )
            input_items["sourcetype"] = "cyberark:epm:application:events"
            config = {
                "category": "ApplicationEvents",
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
                msg_before="Error in streaming events",
            )


if __name__ == "__main__":
    exit_code = ApplicationEvents().run(sys.argv)
    sys.exit(exit_code)

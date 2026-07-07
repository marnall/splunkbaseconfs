#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""Modular Input Script for Admin audit logs"""
import sys
import traceback

# isort: off
import import_declare_test  # noqa: F401

from cyberark_epm_connect import CyberarkConnect
from cyberark_epm_utils import (
    set_logger,
    get_account_details,
    get_proxy_settings,
    add_ucc_error_logger,
)
from splunklib import modularinput as smi
from constants import *


class ADMIN_AUDIT_LOGS(smi.Script):
    def __init__(self):
        super(ADMIN_AUDIT_LOGS, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("admin_audit_logs")
        scheme.description = "Admin Audit Logs"
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

        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        """
        This method is invoked for each input repeatedly at configured interval
        :param inputs: Input arguments for the particular modular input
        :param event_writer: Event Writer object
        """
        self.session_key = self._input_definition.metadata["session_key"]
        _logger = set_logger(
            self.session_key,
            "splunk_ta_cyberark_epm_admin_audit_logs_"
            + (list(inputs.inputs.keys())[0]).split("//")[1],
        )

        try:
            for input_name, input_items in inputs.inputs.items():
                input_items["input_name"] = input_name
            account_name = input_items.get("account_name")
            account_details = get_account_details(
                _logger, self.session_key, account_name
            )

            input_items["sourcetype"] = "cyberark:epm:admin:audit"
            input_items[
                "collection_name"
            ] = import_declare_test.COLLECTION_VALUE_FROM_ENDPOINT["admin_audit_logs"]
            config = {
                "session_key": self.session_key,
                "input_params": input_items,
                "logger": _logger,
            }
            config.update(account_details)
            config["proxies"] = get_proxy_settings(_logger, self.session_key)

            obj = CyberarkConnect(config)
            obj.collect_admin_audit_logs()

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
    exit_code = ADMIN_AUDIT_LOGS().run(sys.argv)
    sys.exit(exit_code)

#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import time
from traceback import format_exc
from splunk import rest as splunk_rest

from snow_consts import GENERAL_EXCEPTION, LOGFILE_PREFIX
from snow_utility import add_ucc_error_logger
import snow_event_base as seb  # noqa : E402


class ModSnowEvent(seb.SnowEventBase):
    def __init__(self, payload, account, invocation_id, log_filename=""):
        self._payload = payload
        self.log_filename = (
            log_filename if log_filename else f"{LOGFILE_PREFIX}_snow_event"
        )
        self._payload["configuration"]["url"] = payload["results_link"]
        self._session_key = payload["session_key"]
        self.account = account
        self.is_failed = False
        self.invocation_id = invocation_id
        super(ModSnowEvent, self).__init__()

    def _get_session_key(self):
        return self._session_key

    def _get_events(self):
        return (self._payload["configuration"],)

    def _get_log_file(self):
        """Return the log filename"""
        return self.log_filename

    def handle(self):
        try:
            msg = self._do_handle()
            if msg and msg.get("Error Message"):
                self.is_failed = True
        except Exception as e:
            add_ucc_error_logger(
                logger=self.logger,
                logger_type=GENERAL_EXCEPTION,
                exception=e,
            )


def process_event(helper, *args, **kwargs):

    # Initialize the class and execute the code for alert action
    helper.log_info("Alert action snow_event started.")
    helper.settings["configuration"]["time_of_event"] = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.gmtime()
    )
    account_list = [
        account.strip()
        for account in helper.settings["configuration"].pop("account", "").split(",")
    ]

    failed_accounts = []

    for acc_name in account_list:
        try:
            handler = ModSnowEvent(
                helper.settings, acc_name, helper.invocation_id, helper.log_filename
            )
            handler.handle()
            if handler.is_failed:
                failed_accounts.append(acc_name)
        except Exception:
            helper.log_error(
                "Failed to create event for the account: {}. Reason: {}".format(
                    acc_name, format_exc()
                )
            )
            failed_accounts.append(acc_name)
            continue
    if failed_accounts:
        msg = f"Failed to create Servicenow events for accounts: {failed_accounts}"
        splunk_rest.simpleRequest(
            "messages",
            helper.settings["session_key"],
            postargs={
                "severity": "error",
                "name": "ServiceNow error message",
                "value": msg,
            },
            method="POST",
        )
    return 0

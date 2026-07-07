#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import sys

import snow_record_base as seb  # noqa : E402


class ModSnowRecord(seb.SnowRecordBase):
    def __init__(self, helper, invocation_id, log_filename=""):
        self._helper = helper
        self.log_filename = log_filename
        self._payload = helper.settings
        self.table_name = self._payload["configuration"]["table_name"]
        self._payload["configuration"]["url"] = helper.settings["results_link"]
        self._session_key = helper.settings["session_key"]
        self.account = helper.settings["configuration"]["account"]
        self.invocation_id = invocation_id
        super(ModSnowRecord, self).__init__()

    def _get_session_key(self):
        """Return the session_key"""
        return self._session_key

    def _get_events(self):
        """Return the events"""
        return (self._payload["configuration"],)

    def _get_log_file(self):
        """Return the log filename"""
        return self.log_filename

    def _get_table(self, event):
        """
        Get the table name from the event.

        :param event: A dictionary containing the event.
        :return table_name: Name of the table from event.
        """
        if event.get("table_name"):
            return event.get("table_name")
        return self.table_name

    def _write_error(self, message, exit: bool = False):
        """
        Log the error and exit if exit set to true.

        :param message: message to log.
        :param exit: whether to end the execution. Default to False.
        """
        self._helper.log_error(message)
        if exit:
            sys.exit(1)


def process_event(helper, *args, **kwargs):
    """Process the event"""
    helper.log_info("Alert action snow_record started.")
    handler = ModSnowRecord(helper, helper.invocation_id, helper.log_filename)
    handler.handle()
    return 0

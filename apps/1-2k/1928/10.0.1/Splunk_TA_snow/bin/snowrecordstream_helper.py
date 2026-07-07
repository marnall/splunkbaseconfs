#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import sys

import snow_utility as su
import snow_record_base as srb

from snow_consts import GENERAL_EXCEPTION, LOGFILE_PREFIX
from snow_utility import get_unique_id


_LOGGER = su.create_log_object(f"{LOGFILE_PREFIX}_snow_record_stream")


class SnowRecordStreamHelper(srb.SnowRecordBase):

    REQUIRED_FIELDS = ["account", "table_name", "fields"]

    def __init__(self, helper, records) -> None:
        self._helper = helper
        self.session_key = self._helper.metadata.searchinfo.session_key
        self.events = tuple(records)
        self.invocation_id = get_unique_id()
        if not self.events:
            sys.exit(0)

        self.validate_params()
        self.account = self._get_account()
        super(SnowRecordStreamHelper, self).__init__()

    def _get_session_key(self):
        """Get the session_key"""
        return self.session_key

    def _get_events(self):
        """Get the events"""
        return self.events

    def _get_log_file(self):
        """Return the log filename"""
        return f"{LOGFILE_PREFIX}_snow_record_stream"

    def _get_account(self):
        """
        Extracts the first non-empty 'account' value from the list of events.

        :return str or None: The first valid account found, or None if not found.
        """
        for event in self.events:
            account = event.get("account")
            if account:
                return account

        return None

    def validate_params(self):
        """
        Validates that all required fields are present in each event.

        :return bool: True if validation passes; logs error and exits on failure.
        """
        for event in self.events:
            missing_fields = [
                field for field in self.REQUIRED_FIELDS if not event.get(field)
            ]
            if missing_fields:
                self._write_error(
                    "Fields {} are required by ServiceNow for creating or updating records."
                    " Make sure that event containe non-empty values.".format(
                        missing_fields
                    ),
                    True,
                )
                break
        return True

    def _write_error(self, message, exit: bool = False):
        """
        Log and write the error and exit if exit set to True.

        :param message: Error message to show.
        :param exit: whether to end the execution. Default to False.
        """
        _LOGGER.error(
            "[invocation_id={}] Error: {}".format(self.invocation_id, message)
        )
        self._helper.write_error(message)
        if exit:
            sys.exit(1)

    def _handle(self):
        """Wrapper over the _do_handle function"""
        try:
            return self._do_handle()
        except Exception as e:
            msg = f"{self.get_invocation_id()} Error occured."
            su.add_ucc_error_logger(
                logger=self.logger,
                logger_type=GENERAL_EXCEPTION,
                exception=e,
                msg_before=msg,
            )

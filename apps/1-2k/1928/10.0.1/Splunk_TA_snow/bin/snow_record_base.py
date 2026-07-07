#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import time

import snow_base as sb

from snow_utility import split_string_to_dict, parse_string_to_dict


class SnowRecordBase(sb.SnowBase):
    """
    Create ServiceNow record automatically by running as a callback script
    when the corresponding alert/custom command is fired
    """

    def _prepare_data(self, event) -> dict:
        """
        Prepares event data for ServiceNow API request based on the presence of unique identifiers and fields.

        :param event: Dictionary containing raw event data.
        :return dict: Structured event data including table name, request method, parameters, and payload.
        """
        unique_identifier = parse_string_to_dict(
            event.get("unique_identifier", ""), key_separator="="
        )
        error = unique_identifier.get("Error Message")
        if error:
            self._write_error(error, True)

        if unique_identifier:
            event_data = {
                "table_name": event["table_name"],
                "snow_table_config": {
                    "method": "GET",
                    "subcommand": "get",
                    "params": unique_identifier,
                },
                "payload": {},
            }
        else:
            event_data = {
                "table_name": event["table_name"],
                "snow_table_config": {
                    "method": "POST",
                    "subcommand": "create",
                    "params": {},
                },
                "payload": {},
            }

        if event.get("fields"):
            payload = split_string_to_dict({}, event.get("fields"))
            error = payload.get("Error Message")
            if error:
                self._write_error(error, True)
            event_data["payload"] = payload

        self.logger.debug(
            "{} prepare_data: {}".format(self.get_invocation_id(), event_data)
        )
        return event_data

    def _process_results(self, results: list) -> list:
        """
        Processes the results into a list of structured records.

        :param results: List of (response content, raw event) tuples.
        :return list: Structured processed results.
        """
        processed_results = []

        for content, raw_event in results:
            resp = self._get_resp_record(content, True)
            if not resp:
                self.fail_count += 1
                continue
            if "Error Message" in resp:
                error_result = self._get_error_result(resp)
                error_result["_time"] = time.time()
                processed_results.append(error_result)
            else:
                result = self._get_result(resp, raw_event)
                result["_time"] = time.time()
                processed_results.append(result)

        return processed_results

    def _get_table(self, event):
        """
        Get the table name from the event.
        :param event: A dictionary contianing the event.
        """
        return event.get("table_name", "")

    def _get_result(self, resp, event) -> dict:
        """
        Build the result dictionary from the response.

        :param resp: Dictionary response from the ServiceNow API.
        :return dict: Dictionary containing result information to show.
        """
        result = {
            "Sys Id": resp.get("sys_id"),
            "Table Name": self._get_table(event),
            "Record Link": self._get_ticket_link(
                resp.get("sys_id"), event.get("table_name")
            ),
            "Response Payload": resp,
        }
        return result

    def _get_error_result(self, resp) -> dict:
        """
        Build a error response for event

        :param resp: response contain error information
        :return dict: Dictionary containing error information to show.
        """
        return {
            "Error": resp.get("Error Message", ""),
            "Status Code": resp.get("status_code", ""),
            "Response Payload": resp.get("error_content", ""),
        }

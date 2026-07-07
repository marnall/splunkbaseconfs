# File: anyrun_connector.py
#
# Copyright (c) ANYRUN FZCO, 2025-2026
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

# pylint: disable=wildcard-import
# pylint: disable=line-too-long


import json
import traceback
from typing import Union

# Phantom App imports
import phantom.app as phantom
import phantom.rules as phantom_rules
import requests
from anyrun import RunTimeException

# Usage of the consts file is recommended
from anyrun.connectors import LookupConnector, SandboxConnector
from anyrun.connectors.sandbox.operation_systems import AndroidConnector, LinuxConnector, WindowsConnector
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from anyrun_consts import *
from utils.utility_functions import convert_iocs_to_soar_format, save_file


class AnyRunConnector(BaseConnector):
    _anyrun_sandbox: SandboxConnector

    def __init__(self):
        super().__init__()
        self._state = None
        self._server = None
        self._api_key = None
        self._timeout = None

    def _handle_get_history(self, param: dict) -> list[dict]:
        """
        Handle get history

        :param param: Parameters
        :return: ActionResult object
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        entity_type = param.get("entity_type")
        entity_value = param.get("entity_value")

        if entity_type == "hash":
            hash_type = {32: "md5", 40: "sha1", 64: "sha256"}.get(len(entity_value))
            if not hash_type:
                return action_result.set_status(phantom.APP_ERROR, "Unsupported hash type. Allowed: sha1, sha256, md5")

        try:
            with self._windows_sandbox as sandbox:
                tasks = sandbox.get_analysis_history(True, 0, 100)
                if entity_type == "hash":
                    tasks = [task for task in tasks if task.get("hashes", {}).get(hash_type) == entity_value]
                else:
                    tasks = [task for task in tasks if entity_value in task.get("name", {})]

            action_result.add_data({"tasks": tasks})
            self.save_progress(ANYRUN_SUCCESS_SEARCH_ANALYSIS_HISTORY.format(entity_value))

            return action_result.set_status(phantom.APP_SUCCESS, ANYRUN_SUCCESS_SEARCH_ANALYSIS_HISTORY.format(entity_value))

        except RunTimeException as error:  # pylint: disable=broad-exception-caught
            self.save_progress(str(error))
            return action_result.set_status(phantom.APP_ERROR, str(error))
        except Exception:
            error_message = f"Unspecified Exception: {traceback.format_exc()}"
            self.save_progress(error_message)
            return action_result.set_status(phantom.APP_ERROR, error_message)

    def _handle_get_reputation(self, param: dict) -> list[dict]:
        """
        Handle get reputation

        :param param: Parameters
        :return: ActionResult object
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        action_data = dict()

        entity_type = param.get("entity_type")
        entity_value = param.get("entity_value")
        lookup_depth = param.get("lookup_depth")

        if entity_type == "hash":
            hash_type = {32: "md5", 40: "sha1", 64: "sha256"}.get(len(entity_value))
            if not hash_type:
                return action_result.set_status(phantom.APP_ERROR, "Unsupported hash type. Allowed: sha1, sha256, md5")
            query_params = {hash_type: entity_value}
        else:
            query_params = {entity_type: entity_value}

        try:
            with self._lookup as lookup:
                response = lookup.get_intelligence(**query_params, lookup_depth=lookup_depth)

            if response.get("relatedFiles"):
                file_info = response.get("relatedFiles")[0]
                ext = file_info.get("fileExtension")
                path = file_info.get("fileName")
                name = path.split("\\")[-1]

                action_data["filename"] = name
                action_data["filepath"] = path
                action_data["file_extension"] = ext
                action_data["sha256"] = file_info.get("hashes").get("sha256")
                action_data["sha1"] = file_info.get("hashes").get("sha1")
                action_data["md5"] = file_info.get("hashes").get("md5")
                action_data["ssdeep"] = file_info.get("hashes").get("ssdeep")

            if response.get("destinationIPgeo"):
                action_data["country"] = response.get("destinationIPgeo")[0].upper()

            if response.get("destinationPort"):
                action_data["port"] = response.get("destinationPort")[0]

            if response.get("destinationIpAsn"):
                action_data["asowner"] = response.get("destinationIpAsn")[0].get("asn").upper()

            if response.get("summary", {}).get("tags"):
                action_data["tags"] = ", ".join(response.get("summary", {}).get("tags"))

            if response.get("industries"):
                action_data["industries"] = ", ".join(
                    [
                        f"{industry.get('industryName')}({industry.get('confidence')}%)"
                        for industry in sorted(response.get("industries"), key=lambda x: x.get("confidence", 0), reverse=True)
                    ]
                )

            if response.get("sourceTasks"):
                action_data["last_analyses"] = ", ".join([task.get("related") for task in response.get("sourceTasks")[:5]])

            action_data["last_modified"] = response.get("summary", {}).get("lastSeen")
            action_data["verdict"] = VERDICT_RESOLVER.get(response.get("summary", {}).get("threatLevel", 0), "No info")
            action_data["lookup_url"] = (
                "https://intelligence.any.run/analysis/lookup#{%22query%22:%22"
                + entity_type
                + ":%5C%22"
                + entity_value
                + "%5C%22%22,%22dateRange%22:180}"
            )

            action_result.add_data(action_data)

            self.save_progress(ANYRUN_SUCCESS_GET_REPUTATION.format(entity_value))
            return action_result.set_status(phantom.APP_SUCCESS, ANYRUN_SUCCESS_GET_REPUTATION.format(entity_value))

        except RunTimeException as error:  # pylint: disable=broad-exception-caught
            self.save_progress(str(error))
            return action_result.set_status(phantom.APP_ERROR, str(error))
        except Exception:
            error_message = f"Unspecified Exception: {traceback.format_exc()}"
            self.save_progress(error_message)
            return action_result.set_status(phantom.APP_ERROR, error_message)

    def _handle_test_connectivity(self, param: dict) -> ActionResult:
        """
        Handle test connectivity

        NOTE: test connectivity does _NOT_ take any parameters
        i.e. the param dictionary passed to this handler will be empty.
        Also typically it does not add any data into an action_result either.
        The status and progress messages are more important.

        :param param: Parameters
        :return: ActionResult object
        """
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to endpoint")
        try:
            with self._windows_sandbox as sandbox:
                sandbox.check_authorization()

            self.save_progress(ANYRUN_SUCCESS_TEST_CONNECTIVITY)
            return action_result.set_status(phantom.APP_SUCCESS)

        except RunTimeException as error:  # pylint: disable=broad-exception-caught
            self.save_progress(str(error))
            return action_result.set_status(phantom.APP_ERROR, str(error))
        except Exception:
            error_message = f"Unspecified Exception: {traceback.format_exc()}"
            self.save_progress(error_message)
            return action_result.set_status(phantom.APP_ERROR, error_message)

    def _handle_get_report(self, param: dict, report_format: str = "summary") -> ActionResult:
        """
        Handle get report

        :param param: Parameters
        :param report_format: The format of the report to be returned
        :return: ActionResult object
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Making an API call
        analysis_id = param["analysis_id"]
        self.save_progress(f"Requesting report for analysis: {analysis_id}")

        try:
            with self._windows_sandbox as sandbox:
                for status in sandbox.get_task_status(analysis_id):
                    self.debug_print(f"Waiting for task to complete {analysis_id}: {status}")

                report = sandbox.get_analysis_report(analysis_id, report_format=report_format)
                summary = sandbox.get_analysis_report(analysis_id)
                verdict = sandbox.get_analysis_verdict(analysis_id)

            vault_id, report_name = save_file(self.get_container_id(), report, analysis_id, report_format)

            analysis_object = summary.get("data").get("analysis").get("content").get("mainObject")
            tags = summary.get("data").get("analysis").get("tags")

            object_type = analysis_object.get("type")

            action_result.add_data(
                {
                    "object_value": analysis_object.get("url") if object_type == "url" else analysis_object.get("filename"),
                    "object_type": object_type,
                    "verdict": verdict,
                    "tags": ", ".join(tag.get("tag") for tag in tags) if tags else "No info",
                    "analysis_url": f"https://app.any.run/tasks/{analysis_id}",
                    "vault_id": vault_id,
                    "report_name": report_name,
                    "summary": report,
                }
            )

            self.save_progress(ANYRUN_SUCCESS_GET_REPORT.format(analysis_id))
            return action_result.set_status(phantom.APP_SUCCESS, ANYRUN_SUCCESS_GET_REPORT.format(analysis_id))

        except RunTimeException as error:  # pylint: disable=broad-exception-caught
            self.save_progress(str(error))
            return action_result.set_status(phantom.APP_ERROR, str(error))
        except Exception:
            error_message = f"Unspecified Exception: {traceback.format_exc()}"
            self.save_progress(error_message)
            return action_result.set_status(phantom.APP_ERROR, error_message)

    def _handle_get_ioc(self, param: dict) -> ActionResult:
        """
        Handle get IoC

        :param param: Parameters
        :return: ActionResult object
        """

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Making an API call
        analysis_id = param["analysis_id"]
        self.save_progress(f"Requesting IoC report for submission: {analysis_id}.")

        try:
            with self._windows_sandbox as sandbox:
                for status in sandbox.get_task_status(analysis_id):
                    self.debug_print(f"Waiting for task to complete {analysis_id}: {status}")

                iocs = sandbox.get_analysis_report(analysis_id, report_format="ioc")
                iocs = sorted(iocs, key=lambda x: x["reputation"], reverse=True)
                iocs = [ioc for ioc in iocs if ioc.get("reputation") in (1, 2)]

            converted_iocs = convert_iocs_to_soar_format(iocs, analysis_id, self.get_container_id())

            if not converted_iocs:
                return action_result.set_status(phantom.APP_ERROR, "IOCs not found")

            self.save_progress(ANYRUN_SUCCESS_GET_IOC.format(analysis_id))

            if converted_iocs:
                self.save_artifacts(converted_iocs)
                action_result.update_summary(
                    {
                        "total_objects": len(converted_iocs),
                    }
                )

            iocs_csv = [
                [
                    ioc.get("category"),
                    ioc.get("type"),
                    ioc.get("name", "No info"),
                    ioc.get("ioc"),
                    {1: "Suspicious", 2: "Malicious"}.get(ioc.get("reputation"), 2),
                    ioc.get("discoveringEntryId"),
                ]
                for ioc in iocs
            ]
            iocs_csv.insert(0, ["category", "type", "name", "ioc", "reputation", "discoveringEntryId"])
            vault_id, report_name = save_file(self.get_container_id(), iocs_csv, analysis_id, "csv")

            for ioc in iocs:
                if ioc.get("reputation") == 1:
                    ioc["reputation"] = "Suspicious"
                else:
                    ioc["reputation"] = "Malicious"

            action_result.add_data(
                {
                    "ioc": iocs,
                    "vault_id": vault_id,
                    "report_name": report_name,
                }
            )

            return action_result.set_status(phantom.APP_SUCCESS, ANYRUN_SUCCESS_GET_IOC.format(analysis_id))

        except RunTimeException as error:  # pylint: disable=broad-exception-caught
            self.save_progress(str(error))
            return action_result.set_status(phantom.APP_ERROR, str(error))
        except Exception:
            error_message = f"Unspecified Exception: {traceback.format_exc()}"
            self.save_progress(error_message)
            return action_result.set_status(phantom.APP_ERROR, error_message)

    def _handle_detonate_url(self, param: dict, sandbox: Union[LinuxConnector, WindowsConnector, AndroidConnector]) -> ActionResult:
        """
        Handle detonate URL

        :param param: Parameters
        :return: ActionResult object
        """
        action_id = self.get_action_identifier()
        self.save_progress(f"In action handler for: {action_id}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress(f"Detonating URL: {param['obj_url']}")
        param.pop("context", None)

        try:
            with sandbox:
                analysis_id = sandbox.run_url_analysis(**param)

            self.save_progress(ANYRUN_SUCCESS_DETONATE_URL.format(param["obj_url"]))

            action_result.add_data(
                {
                    "analysis_id": analysis_id,
                    "status": "success",
                    "analysis_url": f"https://app.any.run/tasks/{analysis_id}",
                }
            )

            return action_result.set_status(phantom.APP_SUCCESS, ANYRUN_SUCCESS_DETONATE_URL.format(param["obj_url"]))

        except RunTimeException as error:  # pylint: disable=broad-exception-caught
            self.save_progress(str(error))
            return action_result.set_status(phantom.APP_ERROR, str(error))
        except Exception:
            error_message = f"Unspecified Exception: {traceback.format_exc()}"
            self.save_progress(error_message)
            return action_result.set_status(phantom.APP_ERROR, error_message)

    def _handle_detonate_file(self, param: dict, sandbox) -> ActionResult:
        """
        Handle detonate file

        :param param: Parameters
        :return: ActionResult object
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        vault_id = param.pop("vault_id")
        param.pop("context", None)

        try:
            success, message, vault_meta_info = phantom_rules.vault_info(vault_id=vault_id)
            vault_meta_info = list(vault_meta_info)
            if not success or not vault_meta_info:
                error_message = f"Error Details: {message}" if message else ""
                return action_result.set_status(
                    phantom.APP_ERROR,
                    "{}. {}".format(
                        ANYRUN_UNABLE_TO_FETCH_FILE_ERROR.format("vault meta info", vault_id),
                        error_message,
                    ),
                )

            if len(vault_meta_info) >= 1:
                self.save_progress(ANYRUN_VAULT_MULTIPLE_FILES_ERROR.format(vault_id))
            else:
                self.save_progress(ANYRUN_VAULT_NO_FILES_ERROR.format(vault_id))
                return action_result.set_status(phantom.APP_ERROR, ANYRUN_VAULT_NO_FILES_ERROR.format(vault_id))

            file_path = vault_meta_info[0].get("path")
            filename = vault_meta_info[0].get("name")

            if not file_path or not filename:
                return action_result.set_status(phantom.APP_ERROR, ANYRUN_UNABLE_TO_FETCH_FILE_ERROR.format("path", vault_id))

            # Making an API call
            self.save_progress(f"Detonating file with vault ID: {vault_id}")

            with sandbox:
                with open(file_path, "rb") as file:
                    analysis_id = sandbox.run_file_analysis(file_content=file.read(), filename=filename, **param)

            self.save_progress(ANYRUN_SUCCESS_DETONATE_FILE.format(vault_id))

            # Processing server response
            action_result.add_data(
                {
                    "analysis_id": analysis_id,
                    "filename": filename,
                    "status": "success",
                    "analysis_url": f"https://app.any.run/tasks/{analysis_id}",
                }
            )

            return action_result.set_status(phantom.APP_SUCCESS, ANYRUN_SUCCESS_DETONATE_FILE.format(vault_id))

        except RunTimeException as error:  # pylint: disable=broad-exception-caught
            self.save_progress(str(error))
            return action_result.set_status(phantom.APP_ERROR, str(error))
        except Exception:
            error_message = f"Unspecified Exception: {traceback.format_exc()}"
            self.save_progress(error_message)
            return action_result.set_status(phantom.APP_ERROR, error_message)

    def _handle_get_intelligence(self, param: dict) -> ActionResult:
        """
        Handle get intelligence

        :param param: Parameters
        :return: ActionResult object
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        query = param.get("query")
        lookup_depth = param.get("lookup_depth")

        # Making an API call
        self.save_progress("Initiating Threat Intelligence lookup.")
        try:
            with self._lookup as lookup:
                report = lookup.get_intelligence(query=query, lookup_depth=lookup_depth)

            self.save_progress(ANYRUN_SUCCESS_GET_INTELLIGENCE.format(query))

            vault_id, filename = save_file(self.get_container_id(), report, "anyrun_ti_lookup", "summary")

            verdict = VERDICT_RESOLVER.get(report.get("summary", {}).get("threatLevel"), "No info")

            lookup_url = (
                "https://intelligence.any.run/analysis/lookup#{%22query%22:%22"
                + query.replace('"', "%5C%22").replace(" ", "%20")
                + "%22,%22dateRange%22:180}"
            )

            action_result.add_data({"lookup_url": lookup_url, "vault_id": vault_id, "report_name": filename, "verdict": verdict})

            return action_result.set_status(phantom.APP_SUCCESS, ANYRUN_SUCCESS_GET_INTELLIGENCE.format(query))

        except RunTimeException as error:  # pylint: disable=broad-exception-caught
            self.save_progress(str(error))
            return action_result.set_status(phantom.APP_ERROR, str(error))
        except Exception:
            error_message = f"Unspecified Exception: {traceback.format_exc()}"
            self.save_progress(error_message)
            return action_result.set_status(phantom.APP_ERROR, error_message)

    def _handle_download_pcap(self, param: dict) -> ActionResult:
        """
        Handle download PCAP
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        analysis_id = param["analysis_id"]

        try:
            with self._windows_sandbox as sandbox:
                for status in sandbox.get_task_status(analysis_id):
                    self.debug_print(f"Waiting for analysis to complete: {status}")
                pcap = sandbox.download_pcap(analysis_id)

            vault_id, report_name = save_file(self.get_container_id(), pcap, analysis_id, "pcap")

            action_result.add_data({"vault_id": vault_id, "report_name": report_name})

            return action_result.set_status(phantom.APP_SUCCESS, ANYRUN_SUCCESS_DOWNLOAD_PCAP.format(analysis_id))

        except RunTimeException as error:  # pylint: disable=broad-exception-caught
            self.save_progress(str(error))
            return action_result.set_status(phantom.APP_ERROR, str(error))
        except Exception:
            error_message = f"Unspecified Exception: {traceback.format_exc()}"
            self.save_progress(error_message)
            return action_result.set_status(phantom.APP_ERROR, error_message)

    def _handle_delete_analysis(self, param: dict) -> ActionResult:
        """
        Handle delete submission
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        analysis_id = param["analysis_id"]

        try:
            with self._windows_sandbox as sandbox:
                sandbox.delete_task(analysis_id)

            self.save_progress(ANYRUN_SUCCESS_DELETE_ANALYSIS.format(analysis_id))

            action_result.add_data({"status": "Analysis deleted successfully."})

            return action_result.set_status(phantom.APP_SUCCESS, ANYRUN_SUCCESS_DELETE_ANALYSIS.format(analysis_id))

        except RunTimeException as error:  # pylint: disable=broad-exception-caught
            self.save_progress(str(error))
            return action_result.set_status(phantom.APP_ERROR, str(error))
        except Exception:
            error_message = f"Unspecified Exception: {traceback.format_exc()}"
            self.save_progress(error_message)
            return action_result.set_status(phantom.APP_ERROR, error_message)

    def _handle_get_analysis_verdict(self, param: dict) -> ActionResult:
        """
        Handle get analysis verdict
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        analysis_id = param["analysis_id"]

        try:
            with self._windows_sandbox as sandbox:
                for status in sandbox.get_task_status(analysis_id):
                    self.debug_print(f"Waiting for analysis to complete: {status}")

                verdict = sandbox.get_analysis_verdict(analysis_id)
                report = sandbox.get_analysis_report(analysis_id)

            analysis_object = report.get("data").get("analysis").get("content").get("mainObject")

            object_type = analysis_object.get("type")

            action_result.add_data(
                {
                    "object_value": analysis_object.get("url") if object_type == "url" else analysis_object.get("filename"),
                    "object_type": object_type,
                    "verdict": verdict,
                }
            )

            self.save_progress(ANYRUN_SUCCESS_GET_ANALYSIS_VERDICT.format(analysis_id))
            return action_result.set_status(phantom.APP_SUCCESS, ANYRUN_SUCCESS_GET_ANALYSIS_VERDICT.format(analysis_id))

        except RunTimeException as error:  # pylint: disable=broad-exception-caught
            self.save_progress(str(error))
            return action_result.set_status(phantom.APP_ERROR, str(error))
        except Exception:
            error_message = f"Unspecified Exception: {traceback.format_exc()}"
            self.save_progress(error_message)
            return action_result.set_status(phantom.APP_ERROR, error_message)

    def handle_action(self, param: dict) -> ActionResult:
        """
        Handle action

        :param param: Parameters
        :return: ActionResult object
        """
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == ACTION_ID_ANYRUN_SEARCH_ANALYSIS_HISTORY:
            ret_val = self._handle_get_history(param)
        elif action_id == ACTION_ID_ANYRUN_GET_REPUTATION:
            ret_val = self._handle_get_reputation(param)
        elif action_id == ACTION_ID_ANYRUN_GET_REPORT:
            ret_val = self._handle_get_report(param)
        elif action_id == ACTION_ID_ANYRUN_GET_REPORT_STIX:
            ret_val = self._handle_get_report(param, report_format="stix")
        elif action_id == ACTION_ID_ANYRUN_GET_REPORT_HTML:
            ret_val = self._handle_get_report(param, report_format="html")
        elif action_id == ACTION_ID_ANYRUN_GET_REPORT_MISP:
            ret_val = self._handle_get_report(param, report_format="misp")
        elif action_id == ACTION_ID_ANYRUN_GET_IOC:
            ret_val = self._handle_get_ioc(param)
        elif action_id == ACTION_ID_ANYRUN_DETONATE_URL_ANDROID:
            ret_val = self._handle_detonate_url(param, self._android_sandbox)
        elif action_id == ACTION_ID_ANYRUN_DETONATE_URL_LINUX:
            ret_val = self._handle_detonate_url(param, self._linux_sandbox)
        elif action_id == ACTION_ID_ANYRUN_DETONATE_URL_WINDOWS:
            ret_val = self._handle_detonate_url(param, self._windows_sandbox)
        elif action_id == ACTION_ID_ANYRUN_DETONATE_FILE_ANDROID:
            ret_val = self._handle_detonate_file(param, self._android_sandbox)
        elif action_id == ACTION_ID_ANYRUN_DETONATE_FILE_LINUX:
            ret_val = self._handle_detonate_file(param, self._linux_sandbox)
        elif action_id == ACTION_ID_ANYRUN_DETONATE_FILE_WINDOWS:
            ret_val = self._handle_detonate_file(param, self._windows_sandbox)
        elif action_id == ACTION_ID_ANYRUN_GET_INTELLIGENCE:
            ret_val = self._handle_get_intelligence(param)
        elif action_id == ACTION_ID_ANYRUN_TEST_CONNECTIVITY:
            ret_val = self._handle_test_connectivity(param)
        elif action_id == ACTION_ID_ANYRUN_DELETE_ANALYSIS:
            ret_val = self._handle_delete_analysis(param)
        elif action_id == ACTION_ID_ANYRUN_DOWNLOAD_PCAP:
            ret_val = self._handle_download_pcap(param)
        elif action_id == ACTION_ID_ANYRUN_GET_ANALYSIS_VERDICT:
            ret_val = self._handle_get_analysis_verdict(param)

        return ret_val

    def initialize(self) -> bool:
        """
        Initialize
        """
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        # Access values in asset config by the name

        # Required values can be accessed directly
        # required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        # optional_config_name = config.get('optional_config_name')

        self._api_key = config.get("anyrun_api_key")
        self._timeout = config.get("anyrun_timeout")

        self._anyrun_sandbox = SandboxConnector()

        generic_sandbox_parameters = {
            "api_key": self._api_key,
            "integration": VERSION,
            "timeout": self._timeout,
        }

        self._windows_sandbox = self._anyrun_sandbox.windows(**generic_sandbox_parameters)
        self._android_sandbox = self._anyrun_sandbox.android(**generic_sandbox_parameters)
        self._linux_sandbox = self._anyrun_sandbox.linux(**generic_sandbox_parameters)

        self._lookup = LookupConnector(
            api_key=self._api_key,
            integration=VERSION,
            timeout=self._timeout,
        )

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():  # pragma: no cover
    import argparse

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = AnyRunConnector.get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = AnyRunConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector.set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == "__main__":
    main()

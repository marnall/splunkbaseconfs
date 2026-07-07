#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test

import time
import traceback
import signal

import os, sys
from defusedxml.minidom import parseString
import box_helper
from checkpoint import Checkpointer
from box_client import BoxClient
from solnlib import conf_manager, log
from solnlib.utils import is_true
from splunk import rest
from boxsdk.exception import BoxAPIException
from solnlib.modular_input import event_writer

_LOGGER = log.Logs().get_logger("ta_box_file_ingestion")

SOURCETYPE = "box:filecontent"


class BoxFileIngestionService:
    def __init__(self, input_name, session_key, ew):
        self.input_name = input_name
        self.session_key = session_key
        self.ew = ew
        self.checkpoint_dict = None
        self.checkpoint_updated = False
        self.events_ingested = False
        self.checkpointer = Checkpointer(
            session_key,
            self.input_name,
            import_declare_test.FILE_INGESTION_CHECKPOINTER,
            _LOGGER,
        )
        self.box_client = None
        self.index = None
        self.valid_extensions = {"csv", "json", "txt", "text", "log", "xml"}
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        # for windows machine
        if os.name == "nt":
            signal.signal(signal.SIGBREAK, self.exit_gracefully)  # pylint:disable=E1101

    def exit_gracefully(self, signum, frame):
        """
        This method stores the checkpoint if not done already before terminating the input
        """
        _LOGGER.info("Execution about to get stopped due to SIGTERM.")
        try:
            if self.events_ingested and not self.checkpoint_updated:
                self.update_checkpoint()
                _LOGGER.info(
                    "Successfully updated the checkpoint for input '{}' before exiting.".format(
                        self.input_name
                    )
                )
        except Exception as exc:
            _LOGGER.error(
                "Unable to save checkpoint before SIGTERM termination. Error: {}".format(
                    exc
                )
            )
            sys.exit(0)

    def update_checkpoint(self):
        """Helper function to update checkpoint for either a file or a folder."""
        try:
            self.checkpointer.update_kv_checkpoint(self.checkpoint_dict)
            _LOGGER.debug(
                "Updated checkpoint for input '{}' to {}.".format(
                    self.input_name, self.checkpoint_dict
                )
            )
        except Exception as e:
            _LOGGER.error(
                "Failed to update checkpoint for input '{}'. Error details: {}".format(
                    self.input_name, e
                )
            )

    def file_content_ingestion(
        self,
        file_id,
        file_name,
        box_config=None,
    ):
        """Ingests the content of a specified file from Box into Splunk and update the checkpoint."""
        try:
            self.checkpoint_updated, self.events_ingested = False, False

            # Attempt to fetch the file content from Box
            file_content = box_helper.fetch_file_content(
                self.client,
                file_id,
                self.input_name,
                _LOGGER,
            )

            # Determine the sourcetype based on the file extension
            sourcetype = {
                ".xml": SOURCETYPE + ":xml",
                ".csv": SOURCETYPE + ":csv",
                ".json": SOURCETYPE + ":json",
            }.get(
                "." + file_name.split(".")[-1] if "." in file_name else "",
                SOURCETYPE,
            )
            source = "box_file_ingestion_service::" + self.input_name + "::" + file_name
            if sourcetype == "box:filecontent:xml":
                try:
                    # Parse the XML data
                    dom = parseString(file_content)
                    # # Return the XML with indentation
                    file_content = dom.toprettyxml(indent="  ")
                except Exception as e:
                    _LOGGER.error(
                        "Failed to parse XML content for file '{}' with source '{}', input '{}': {}. "
                        "This error is likely due to malformed XML. Please check the file content and try again.".format(
                            file_name, source, self.input_name, e
                        )
                    )
                    return

            if file_content:
                event = self.ew.create_event(
                    data=file_content,
                    time=time.time(),
                    sourcetype=sourcetype,
                    source=source,
                    index=self.index,
                )
                self.ew.write_events([event])

            self.events_ingested = True

            self.update_checkpoint()
            self.checkpoint_updated = True

            _LOGGER.info(
                "Successfully collected and ingested file id {} for input : {}".format(
                    file_id, self.input_name
                )
            )
        except BoxAPIException as api_ex:
            # Handle API-related issues (e.g., file not found, unauthorized access)
            _LOGGER.error(
                "Unable to retrieve file content from Box. "
                "Box API Error Details - Message: {0}, Status: {1}, Code: {2}".format(
                    api_ex.message, api_ex.status, api_ex.code
                )
            )
        except Exception as e:
            _LOGGER.error(
                "An error occurred while attempting to fetch the file content or updating the checkpoint from Box: {}".format(
                    e
                )
            )

    def fetch_file_details(self, params, file_or_folder_id):
        """Attempts to fetch file details."""
        try:
            return (
                box_helper.fetch_data(
                    self.client,
                    box_helper.fetch_file_information_uri(params, file_or_folder_id),
                    _LOGGER,
                ),
                True,
            )
        except Exception:
            return None, False

    def fetch_folder_details(self, params):
        """Attempts to fetch folder details."""
        try:
            offset = 0
            consolidated_data = None
            while True:
                # Fetch data chunk
                data_chunk = box_helper.fetch_data(
                    self.client,
                    box_helper.fetch_folder_information_uri(params, offset),
                    _LOGGER,
                )
                if data_chunk and "item_collection" in data_chunk:
                    entries = data_chunk["item_collection"]["entries"]
                    total_count = data_chunk["item_collection"]["total_count"]

                    # Initialize consolidated_data with the first chunk's data
                    if not consolidated_data:
                        consolidated_data = data_chunk
                        # Clear existing entries to consolidate manually
                        consolidated_data["item_collection"]["entries"] = []

                    # Append entries to consolidated_data
                    consolidated_data["item_collection"]["entries"].extend(entries)

                    # Update offset
                    offset += len(entries)

                    # Exit if all data is fetched
                    if offset >= total_count:
                        break
                else:
                    break
            # Update total_count in the consolidated data to match the collected entries
            if consolidated_data:
                consolidated_data["item_collection"]["total_count"] = len(
                    consolidated_data["item_collection"]["entries"]
                )
                consolidated_data["item_collection"]["offset"] = 0
            # Extracting file IDs
            file_ids = [
                file["id"]
                for file in consolidated_data["item_collection"]["entries"]
                if file["type"] == "file"
            ]
            _LOGGER.debug(
                "For input '{}', the following files were found in the folder with ID {}: {}".format(
                    self.input_name, consolidated_data["id"], file_ids
                )
            )
            return consolidated_data
        except Exception as folder_err:
            if getattr(folder_err, "status", None) == 404:
                _LOGGER.error("Item with the given ID is neither a file nor a folder.")
            else:
                _LOGGER.error(
                    "An error occurred when trying to fetch the folder: {}".format(
                        folder_err
                    )
                )
            return None

    def process_file_or_folder_for_no_checkpoint_found(
        self, params, file_or_folder_id, box_config
    ):
        """Main logic for processing file or folder based on ID when no checkpoint found."""
        file_details, is_file = self.fetch_file_details(params, file_or_folder_id)

        if is_file:
            # Process file
            if file_details["name"].split(".")[-1].lower() not in self.valid_extensions:
                _LOGGER.info(
                    "Skipping file: {} (unsupported extension)".format(
                        file_details["name"]
                    )
                )
                return
            self.checkpoint_dict = {"version": 1}
            self.checkpoint_dict["id"] = file_details.get("id")
            self.checkpoint_dict["content_modified_at"] = file_details.get(
                "content_modified_at"
            )

            self.file_content_ingestion(
                file_or_folder_id,
                file_details["name"],
                box_config,
            )
            pass
        else:
            _LOGGER.info(
                "Some files may not be processed if they do not have a supported file extension. Only files with the following extensions are eligible for processing: {}. ".format(
                    ", ".join(self.valid_extensions)
                )
            )

            folder_details = self.fetch_folder_details(params)
            if not folder_details:
                return
            ckpt_files_info = []
            # Extract files with specified extensions and required information
            file_details = [
                {
                    "id": entry["id"],
                    "content_modified_at": entry["content_modified_at"],
                    "name": entry["name"],
                }
                for entry in folder_details["item_collection"]["entries"]
                if entry["type"] == "file"
                and entry["name"].split(".")[-1].lower() in self.valid_extensions
            ]
            self.checkpoint_dict = {"version": 1}
            self.checkpoint_dict["id"] = folder_details.get("id")
            self.checkpoint_dict["content_modified_at"] = folder_details.get(
                "content_modified_at"
            )
            if len(file_details) == 0:
                self.checkpoint_dict["list_of_files"] = ckpt_files_info
                self.update_checkpoint()
                return
            for file in file_details:
                ckpt_files_info.append(
                    {
                        "id": file.get("id"),
                        "content_modified_at": file.get("content_modified_at"),
                    }
                )
                self.checkpoint_dict["list_of_files"] = ckpt_files_info

                self.file_content_ingestion(
                    file.get("id"),
                    file["name"],
                    box_config,
                )

    def process_file_or_folder_for_checkpoint_found(
        self, params, file_or_folder_id, box_config
    ):
        """Main logic for processing file or folder based on ID when checkpoint found."""
        ckpt_files_info = self.checkpoint_dict.get("list_of_files", [])
        ckpt_content_modified_at = self.checkpoint_dict.get("content_modified_at")

        _LOGGER.debug(
            "Last stored checkpoint for input '{}' is {}".format(
                self.input_name, self.checkpoint_dict
            )
        )
        is_file = (
            "list_of_files" not in self.checkpoint_dict
        )  # Determine if we're dealing with a file

        if is_file:
            file_details, _ = self.fetch_file_details(params, file_or_folder_id)
            if file_details.get("content_modified_at") != ckpt_content_modified_at:
                self.checkpoint_dict["content_modified_at"] = file_details.get(
                    "content_modified_at"
                )
                self.file_content_ingestion(
                    file_or_folder_id,
                    file_details["name"],
                    box_config,
                )
            else:
                _LOGGER.debug(
                    "No changes detected in the file. Data collection is up-to-date for the input '{}'".format(
                        self.input_name
                    )
                )
        else:
            _LOGGER.info(
                "Some files may not be processed if they do not have a supported file extension. Only files with the following extensions are eligible for processing: {}. ".format(
                    ", ".join(self.valid_extensions)
                )
            )

            folder_details = self.fetch_folder_details(params)
            file_details = [
                {
                    "id": entry["id"],
                    "content_modified_at": entry["content_modified_at"],
                    "name": entry["name"],
                }
                for entry in folder_details["item_collection"]["entries"]
                if entry["type"] == "file"
                and entry["name"].split(".")[-1].lower() in self.valid_extensions
            ]
            if folder_details.get(
                "content_modified_at"
            ) != ckpt_content_modified_at or len(file_details) != len(ckpt_files_info):
                # Create a lookup dictionary from ckpt_files_info for fast access
                files_lookup = {item["id"]: item for item in ckpt_files_info}

                # Filter ckpt_files_info to only include items where the 'id' is in file_details
                ckpt_files_info = [
                    item
                    for item in ckpt_files_info
                    if item["id"] in {f["id"] for f in file_details}
                ]

                _LOGGER.info(
                    "Detected changes in either the 'content_modified_at' timestamp or file count for the folder with ID {}. Updating the checkpoint to ensure the latest version and file information are reflected.".format(
                        file_or_folder_id
                    )
                )

                for file in file_details:
                    id = file["id"]
                    if id in files_lookup:
                        if files_lookup[id]["content_modified_at"] != file.get(
                            "content_modified_at"
                        ):
                            files_lookup[id]["content_modified_at"] = file[
                                "content_modified_at"
                            ]
                            self.checkpoint_dict["list_of_files"] = ckpt_files_info
                            self.file_content_ingestion(
                                id,
                                file["name"],
                                box_config,
                            )
                        else:
                            _LOGGER.debug(
                                "No changes detected in the file with file id {} for the input '{}'".format(
                                    id, self.input_name
                                )
                            )
                    else:
                        ckpt_files_info.append(
                            {
                                "id": file.get("id"),
                                "content_modified_at": file.get("content_modified_at"),
                            }
                        )
                        self.checkpoint_dict["list_of_files"] = ckpt_files_info
                        self.file_content_ingestion(
                            id,
                            file["name"],
                            box_config,
                        )
                self.checkpoint_updated = False
                self.checkpoint_dict["content_modified_at"] = folder_details.get(
                    "content_modified_at"
                )
                self.checkpoint_dict["list_of_files"] = ckpt_files_info
                self.update_checkpoint()
                self.checkpoint_updated = True
            else:
                _LOGGER.debug(
                    "No changes detected in the folder. Data collection is up-to-date for the input '{}'".format(
                        self.input_name
                    )
                )

    def process_file_or_folder_data(
        self,
        account_info,
        account_name,
        file_or_folder_id,
        proxy_config=None,
        box_config=None,
    ):
        """Collects and processes data from a specified endpoint in Box based on the input parameters."""

        params = {}
        self.checkpoint_dict = self.checkpointer.get_kv_checkpoint_value()

        params["session_key"] = self.session_key
        params["appname"] = import_declare_test.ta_name

        params.update(proxy_config)
        params.update(box_config)
        params.update(account_info)

        params["disable_ssl_certificate_validation"] = is_true(
            params.get("disable_ssl_certificate_validation", False)
        )

        params["account"] = account_name
        params["file_or_folder_id"] = file_or_folder_id

        self.client = BoxClient(params, logger=_LOGGER)

        try:
            account_id = box_helper.fetch_data(
                self.client, box_helper.fetch_account_id_uri(params), _LOGGER
            ).get("id")
        except Exception as err:
            account_id = None
            _LOGGER.error("Failed to fetch account_id, " "reason={}".format(err))

        if account_id is None:
            _LOGGER.info(
                "Box account ID not found for account: {} configured "
                "in the input : {}".format(account_name, self.input_name)
            )
            pass

        # Handle case when no checkpoint is found:
        # Processes the file or folder as a new item (first-time ingestion).
        if not self.checkpoint_dict:
            self.process_file_or_folder_for_no_checkpoint_found(
                params, file_or_folder_id, box_config
            )
            _LOGGER.info(
                "Data collection is ended for Input {}".format(self.input_name)
            )
            return

        # Handle case when a checkpoint is found:
        # Processes the file or folder based on previously stored checkpoint data.
        self.process_file_or_folder_for_checkpoint_found(
            params, file_or_folder_id, box_config
        )
        _LOGGER.info("Data collection is ended for Input {}".format(self.input_name))
        return


def stream_events(helper, inputs):
    try:
        input_name = list(inputs.inputs.keys())[0]
        session_key = inputs.metadata["session_key"]

        proxy_config, logging_config = box_helper.get_proxy_logging_config(
            session_key
        )  # noqa: E501

        loglevel = logging_config.get("loglevel", "INFO")
        _LOGGER.setLevel(loglevel)

        box_config = box_helper.get_box_config(session_key)

        try:
            account_cfm = conf_manager.ConfManager(
                session_key,
                import_declare_test.ta_name,
                realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_box_account".format(  # noqa: E501
                    import_declare_test.ta_name
                ),
            )

            splunk_ta_box_account_conf = account_cfm.get_conf(
                "splunk_ta_box_account", refresh=True
            ).get_all()

        except conf_manager.ConfManagerException:
            _LOGGER.info(
                "No account configurations found for this add-on. "
                "To start data collection, configure new "
                "account on Configurations page and link it to an input "
                "on Inputs page. Exiting TA.."
            )
            return

        index = inputs.inputs[input_name]["index"]

        account_name = inputs.inputs[input_name].get("account", "")
        file_or_folder_id = inputs.inputs[input_name].get("file_or_folder_id") or ""

        if not account_name:
            msg = "Account configuration is missing for the"
            " input: {} in Splunk Add-on for Box. ".format(input_name)
            "Fix the configuration to resume data collection"
            rest.simpleRequest(
                "messages",
                session_key,
                postargs={
                    "severity": "error",
                    "name": "Box error message",
                    "value": msg,
                },
                method="POST",
            )
            _LOGGER.error(msg)
            return

        account_info = {
            k: v for k, v in splunk_ta_box_account_conf.get(account_name).items()
        }

        input_name = input_name.replace("box_file_ingestion_service://", "")
        _LOGGER.info(
            "Start data collection for the "
            "input: {} configured with account name {}".format(input_name, account_name)
        )

        ew = event_writer.ClassicEventWriter()
        service = BoxFileIngestionService(input_name, session_key, ew)
        service.index = index

        service.process_file_or_folder_data(
            account_info,
            account_name,
            file_or_folder_id,
            proxy_config=proxy_config,
            box_config=box_config,
        )

    except Exception:
        _LOGGER.error(
            "Error occured during data collection - {}".format(traceback.format_exc())
        )

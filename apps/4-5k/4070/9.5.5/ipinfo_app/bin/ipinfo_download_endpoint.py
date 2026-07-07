import datetime
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ipinfo_bootstrap  # noqa: F401  -- pin vendored splunklib before any other import to defeat Splunk Enterprise Security sys.path collisions

import requests
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
from splunk.persistconn.application import PersistentServerConnectionApplication

from ipinfo.logging import get_logger
from ipinfo_constants import LIST_OF_FILES_TO_EXCLUDE
from ipinfo_download import download_mmdb_file
from ipinfo_utils import (
    get_bearer_token,
    get_config,
    get_shcluster_current_mgmt_uri,
    get_shcluster_members,
    post_message,
)


shc_replication = get_config("shc_replication")
lookup_path = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipinfo_app", "lookups"])
logger = get_logger(__file__)


def split_files(file_path):
    logger.debug("Splitting file: %s", file_path)
    CHUNK_SIZE = 100000000
    file_number = 1
    file_path = file_path + ".mmdb"
    logger.debug("File path: %s, chunk size: %d bytes", file_path, CHUNK_SIZE)

    with open(file_path, "rb") as f:
        chunk = f.read(CHUNK_SIZE)
        while chunk:
            chunk_file_path = file_path + "_" + str(file_number)
            logger.debug("Writing chunk %d to: %s", file_number, chunk_file_path)
            with open(chunk_file_path, "wb") as chunk_file:
                chunk_file.write(chunk)
            file_number += 1
            chunk = f.read(CHUNK_SIZE)

    logger.info("File split into %d chunks", file_number - 1)
    return file_number


class DownloadMmdb(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        logger.debug("Initializing DownloadMmdb")
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, in_string):
        logger.debug("Handling download request")
        request = json.loads(in_string.decode())
        session_key = request["session"]["authtoken"]
        query = request["query"]
        logger.debug("Query parameters: %s", query)

        download_response = {}
        query_parsed = {}
        for req in query:
            if req[0] == "output_mode":
                continue
            if req[0] == "shc_exist":
                query_parsed["shc_exist"] = True
            if req[0] == "mgmt_uri":
                query_parsed["mgmt_uri"] = req[1]

        response = {}
        # Download request from another machine
        if query_parsed.get("shc_exist") == True:
            logger.debug("SHC download request detected, shc_replication: %s", shc_replication)
            if shc_replication == "Externally":
                # No need to copy directly download from ipinfo server
                params = {}
                logger.info("Downloading from IPInfo (external replication)")
                for req in query:
                    if req[0] == "output_mode":
                        continue
                    if req[1].startswith("Yes"):
                        logger.info("Downloading %s from IPInfo", req[0])
                        download_response[req[0]] = download_mmdb_file(session_key, "", req[0])

            else:
                # Search head replication Internally need to copy
                logger.info("Downloading from another SHC (internal replication)")
                bearer_token = session_key

                headers = {
                    "Authorization": "Bearer " + bearer_token,
                    "Content-Type": "application/json",
                }
                for req in query:
                    if req[0] == "output_mode" or req[0] == "shc_exist" or req[0] == "mgmt_uri":
                        continue
                    if req[1].startswith("Yes"):
                        try:
                            logger.debug("Processing MMDB: %s", req[0])
                            name = req[0] + ".mmdb"
                            rename = req[0] + datetime.datetime.now().strftime("%m-%d-%Y_%H_%M_%S") + ".mmdb"
                            old_file = os.path.join(lookup_path, name)
                            new_file = os.path.join(lookup_path, rename)
                            source_server_uri = query_parsed["mgmt_uri"] + "/servicesNS/nobody/ipinfo_app/copy_mmdb"
                            offset = int(req[1].split("__")[1])
                            logger.debug("Expected chunks: %d, old_file: %s, new_file: %s", offset, old_file, new_file)

                            disable_splunk_local_ssl_request = False
                            if not os.path.exists(lookup_path):
                                logger.debug("Creating lookup path: %s", lookup_path)
                                os.makedirs(lookup_path)

                            for i in range(1, offset):
                                logger.debug("Downloading chunk %d of %s", i, req[0])
                                try:
                                    request = requests.post(
                                        source_server_uri,
                                        params={"name": name + "_" + str(i)},
                                        headers=headers,
                                        timeout=3600,
                                        verify=disable_splunk_local_ssl_request,
                                        stream=True,
                                    )
                                    request.raise_for_status()
                                except requests.exceptions.Timeout:
                                    logger.error("The request timed out for chunk %d", i)
                                except requests.exceptions.RequestException as e:
                                    logger.error("An error occurred downloading chunk %d: %s", i, e)
                                except Exception as e:
                                    logger.error("Unexpected error downloading chunk %d: %s", i, e)
                                    logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))

                                logger.debug("Writing chunk %d to file", i)
                                with open(new_file, "ab") as fh:
                                    for chunk in request.iter_content(10 * 1024 * 1024):
                                        fh.write(chunk)

                            logger.debug("All chunks downloaded, finalizing file")
                            if os.path.exists(old_file):
                                logger.debug("Removing old file: %s", old_file)
                                os.remove(old_file)
                            os.rename(new_file, old_file)
                            download_response[req[0]] = 0
                            logger.info("File downloaded successfully: %s", req[0])
                            post_message(session_key, req[0], "Ipinfo " + req[0] + ".mmdb downloaded successufly ", "info")
                        except Exception as e:
                            logger.error("Error processing MMDB %s: %s", req[0], e)
                            logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
                            download_response[req[0]] = 1

            logger.debug("Returning SHC download response")
            return {"payload": download_response, "status": 200}
        else:
            # Download request from current machine.
            logger.debug("Local machine download request")
            try:
                params = {}
                logger.info("Downloading from IPinfo")
                current_mgmt_uri = get_shcluster_current_mgmt_uri(session_key)
                response[current_mgmt_uri] = download_response
                if current_mgmt_uri != None and current_mgmt_uri != "":
                    logger.info("Search Head Cluster exists: %s", current_mgmt_uri)
                else:
                    logger.debug("No Search Head Cluster detected")

                for req in query:
                    if req[0] == "output_mode":
                        continue
                    if req[1].startswith("Yes"):
                        logger.info("Downloading %s from IPInfo", req[0])
                        download_response[req[0]] = download_mmdb_file(session_key, "", req[0])
                        # Split downloaded file into chunk if cluster exist
                        if download_response[req[0]] == 0 and current_mgmt_uri != None and current_mgmt_uri != "":
                            logger.debug("Splitting downloaded file: %s", req[0])
                            offset = split_files(os.path.join(lookup_path, req[0]))
                            params[req[0]] = req[1] + "__" + str(offset)

                # Check if search head cluster exist
                if current_mgmt_uri != None and current_mgmt_uri != "":
                    logger.info("Current Management URI: %s", current_mgmt_uri)
                    bearer_token = get_bearer_token(session_key, True)
                    if bearer_token != "":
                        logger.debug("Bearer token retrieved successfully")
                        params["mgmt_uri"] = current_mgmt_uri
                        params["shc_exist"] = True
                        headers = {
                            "Authorization": "Bearer " + bearer_token,
                            "Content-Type": "application/json",
                        }

                        list_of_peers = get_shcluster_members(session_key, current_mgmt_uri)
                        logger.debug("Retrieved %d cluster peers", len(list_of_peers))
                        try:
                            # Call download_endpoint of other search heads in search head cluster
                            for peer in list_of_peers:
                                logger.info("Requesting peer %s to download MMDB", peer)
                                url = peer + "/servicesNS/nobody/ipinfo_app/download_mmdb"
                                disable_splunk_local_ssl_request = False
                                refresh_mmdb_shc = requests.request(
                                    "GET", url, verify=disable_splunk_local_ssl_request, params=params, headers=headers
                                )
                                refresh_mmdb_shc.raise_for_status()
                                refresh_mmdb_shc_json = refresh_mmdb_shc.json()
                                logger.info("Response from peer %s: %s", peer, refresh_mmdb_shc_json)
                                if refresh_mmdb_shc.status_code == 200:
                                    response[peer] = refresh_mmdb_shc_json
                        except Exception as e:
                            logger.error("Error during peer download: %s", e)
                            post_message(
                                session_key,
                                "Bearer Token Issue",
                                "Ipinfo Bearer Token Issue. Check Logs dashboard for troubleshooting.",
                                "error",
                            )
                            logger.error("Most probable issue is Bearer token is expired")
                            logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))

                            logger.debug("Cleaning up downloaded files")
                            for path, folders, files in os.walk(lookup_path):
                                for file in files:
                                    if file in LIST_OF_FILES_TO_EXCLUDE:
                                        continue
                                    if len(file) > 22 and not file.startswith("iplocation_ext_labels"):
                                        continue
                                    if file.startswith("iplocation_ext_labels") and len(file) > 30:
                                        continue
                                    file_path = os.path.join(path, file)
                                    logger.info("Removing file: %s", file_path)
                                    os.remove(file_path)
                            return {
                                "payload": "Internal Error Occured. Most possible issue is Bearer token is expired. Check Logs dashboard for troubleshooting.",
                                "status": 500,
                            }

                    else:
                        logger.error("Bearer token not found or empty")
                        post_message(
                            session_key,
                            "Bearer Token Issue",
                            "Ipinfo Bearer Token Issue. Check Logs dashboard for troubleshooting.",
                            "error",
                        )
                        logger.error(
                            "Error while accessing bearer Token. Please check whether you have admin access or Bearer token is configured."
                        )
                        logger.error("Ipinfo was just updated on current machine")

                logger.debug("Cleaning up temporary files from lookup path")
                for path, folders, files in os.walk(lookup_path):
                    for file in files:
                        if file in LIST_OF_FILES_TO_EXCLUDE:
                            continue
                        if len(file) > 22 and not file.startswith("iplocation_ext_labels"):
                            continue
                        if file.startswith("iplocation_ext_labels") and len(file) > 30:
                            continue
                        file_path = os.path.join(path, file)
                        logger.info("Removing temporary file: %s", file_path)
                        os.remove(file_path)

            except Exception as e:
                logger.error("Exception during download process: %s", e)
                logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
                post_message(
                    session_key,
                    "Internal Error Occured",
                    "Ipinfo Internal Error Occured. Check Logs dashboard for troubleshooting.",
                    "error",
                )
                return {
                    "payload": "Internal Error Occured. Check Logs dashboard for troubleshooting.",
                    "status": 500,
                }

        logger.debug("Download process completed successfully")
        return {"payload": response, "status": 200}

import datetime
import json
import os
import traceback

import requests
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
import splunk.clilib.cli_common as scc

from download_mmdb import download_mmdb_file
from app_utils import get_logger
from splunk.persistconn.application import PersistentServerConnectionApplication


splunkd_uri = scc.getMgmtUri()
lookup_path = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipgeolocation_app", "lookups"])
logger = get_logger("refresh_mmdb_endpoint")


def split_files(file_path):
    CHUNK_SIZE = 100000000
    file_number = 1
    file_path = file_path + ".zip"

    with open(file_path, "rb") as f:
        chunk = f.read(CHUNK_SIZE)
        
        while chunk:
            with open(file_path + "_" + str(file_number), "wb") as chunk_file:
                chunk_file.write(chunk)
            
            file_number += 1
            chunk = f.read(CHUNK_SIZE)

    return file_number


def get_current_server_management_uri(session_key):
    response = ""
    url = splunkd_uri + "/servicesNS/admin/search/search/jobs"
    data = {
        "search": "| rest /servicesNS/-/-/configs/conf-server splunk_server=local | search title=shclustering | table mgmt_uri title splunk_server | dedup splunk_server",
        "exec_mode": "oneshot",
        "output_mode": "json",
    }
    headers = {
        "Authorization": "Splunk " + session_key,
        "Content-Type": "application/json",
    }
    disable_splunk_local_ssl_request = False
    response = requests.request("POST", url, headers=headers, verify=disable_splunk_local_ssl_request, data=data)
    current_mgmt_uri = ""

    if response.status_code == 200:
        response_json = response.json()
        results = response_json.get("results")
        current_mgmt_uri = results[0].get("mgmt_uri")

    return current_mgmt_uri


def get_shcluster_members(session_key, current_mgmt_uri):
    url = splunkd_uri + "/services/shcluster/status?output_mode=json"
    headers = {
        "Authorization": "Splunk " + session_key,
        "Content-Type": "application/json",
    }
    disable_splunk_local_ssl_request = False
    response = requests.request("GET", url, headers=headers, verify=disable_splunk_local_ssl_request)
    list_of_peers = []

    if response.status_code == 200:
        response_json = response.json()
        
        for entry_object in response_json.get("entry"):
            peers = entry_object.get("content").get("peers")
            
            for key in peers:
                value = peers[key]
                peer = value.get("mgmt_uri")
                
                if peer == current_mgmt_uri:
                    logger.info("Skipping for Peer" + peer)
                    continue
                
                list_of_peers.append(peer)

    return list_of_peers


def get_bearer_token(session_key):
    headers = {
        "Authorization": "Splunk " + session_key,
        "Content-Type": "application/json",
    }
    url = splunkd_uri + "/servicesNS/admin/search/search/jobs"
    data = {
        "search": "| rest /servicesNS/-/-/storage/passwords splunk_server=local | table realm username clear*",
        "exec_mode": "oneshot",
        "output_mode": "json",
    }

    disable_splunk_local_ssl_request = False
    response = requests.request("POST", url, headers=headers, verify=disable_splunk_local_ssl_request, data=data)
    response_json = response.json()
    results = response_json.get("results")
    bearer_token = ""

    for item in results:
        if item["username"] == "bearer_token" and item["realm"] == "ipgeolocation":
            bearer_token = item["clear_password"]

    return bearer_token


class IPGeolocationRefreshMMDB(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        PersistentServerConnectionApplication.__init__(self)

    # Handle a synchronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """
        request = json.loads(in_string.decode())
        request = json.loads(in_string)
        session_key = request["session"]["authtoken"]
        query = request["query"]
        response1 = {}
        query_parsed = {}
        list_of_files_to_exclude = [
            "db-ip-country.mmdb",
            "db-ip-location.mmdb",
            "db-ip-isp.mmdb",
            "db-ip-city-isp.mmdb",
            "db-ip-abuse.mmdb",
            "db-ip-asn.mmdb",
            "db-ip-city-company-asn-abuse.mmdb",
            "db-ip-city-company-asn.mmdb",
            "db-ip-company-asn.mmdb",
            "db-ip-company.mmdb",
            "db-ip-whois.mmdb",
            "db-ip-hosting.mmdb",
            "db-residential-proxy.mmdb",
            "db-ip-security.mmdb"
        ]

        for req in query:
            if req[0] == "output_mode":
                continue

            if req[0] == "download_locally":
                query_parsed["download_locally"] = True
            
            if req[0] == "mgmt_uri":
                query_parsed["mgmt_uri"] = req[1]

        response = {}
        logger.debug(query_parsed)

        if query_parsed.get("download_locally") == True:
            bearer_token = session_key

            logger.info("Downloading from another SHC")

            headers = {
                "Authorization": "Bearer " + bearer_token,
                "Content-Type": "application/json",
            }

            for req in query:
                if req[0] == "output_mode" or req[0] == "download_locally" or req[0] == "mgmt_uri":
                    continue

                if req[1].startswith("Yes"):
                    try:
                        name = "{}.zip".format(req[0])
                        rename = "{}-{}.zip".format(req[0], datetime.datetime.now().strftime("%m-%d-%Y_%H_%M_%S"))
                        old_file_path = os.path.join(lookup_path, name)
                        new_file_path = os.path.join(lookup_path, rename)
                        source_server_uri = query_parsed["mgmt_uri"] + "/services/download"
                        offset = int(req[1].split("__")[1])
                        disable_splunk_local_ssl_request = False

                        if not os.path.exists(lookup_path):
                            os.makedirs(lookup_path)

                        for i in range(1, offset):
                            try:
                                request = requests.post(
                                    source_server_uri,
                                    params={"name": name + "_" + str(i)},
                                    headers=headers,
                                    timeout=(3, 150),
                                    verify=disable_splunk_local_ssl_request,
                                    stream=True,
                                )
                                request.raise_for_status()
                            except requests.exceptions.Timeout:
                                logger.error("The request timed out")
                            except requests.exceptions.RequestException as e:
                                logger.error("An error occurred:", e)
                            except Exception as e:
                                logger.error(e)
                                logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

                            with open(new_file_path, "ab") as fh:
                                for chunk in request.iter_content(10 * 1024 * 1024):
                                    fh.write(chunk)

                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)

                        os.rename(new_file_path, old_file_path)
                        response1[req[0]] = 0
                        logger.info("File Downloaded Successfully" + req[0])
                    except Exception as e:
                        logger.error(e)
                        logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))
                        response1[req[0]] = 1

            return {"payload": response1, "status": 200}
        else:
            try:
                params = {}
                logger.info("Downloading from ipgeolocation.io")

                for req in query:
                    if req[0] == "output_mode":
                        continue
                    if req[1].startswith("Yes"):
                        logger.info("Downloading " + req[0] + " from ipgeolocation.io")
                        response1[req[0]] = download_mmdb_file(session_key, "", req[0])

                        if response1[req[0]] == 0:
                            offset = split_files(os.path.join(lookup_path, req[0]))
                            params[req[0]] = req[1] + "__" + str(offset)

                current_mgmt_uri = get_current_server_management_uri(session_key)
                response[current_mgmt_uri] = response1

                if current_mgmt_uri is not None and current_mgmt_uri != "":
                    bearer_token = get_bearer_token(session_key)

                    if bearer_token != "":
                        params["mgmt_uri"] = current_mgmt_uri
                        params["download_locally"] = True
                        headers = {
                            "Authorization": "Bearer " + bearer_token,
                            "Content-Type": "application/json",
                        }

                        list_of_peers = get_shcluster_members(session_key, current_mgmt_uri)

                        try:
                            for peer in list_of_peers:
                                logger.info("Requesting Peer" + peer + " to download from ipgeolocation.io server")

                                url = peer + "/servicesNS/admin/ipgeolocation_app/refresh_mmdb"
                                disable_splunk_local_ssl_request = False
                                refresh_mmdb_shc = requests.request(
                                    "GET", url, verify=disable_splunk_local_ssl_request, params=params, headers=headers
                                )
                                refresh_mmdb_shc.raise_for_status()
                                refresh_mmdb_shc_json = refresh_mmdb_shc.json()

                                logger.info("Response from remote server " + str(refresh_mmdb_shc_json))
                                
                                if refresh_mmdb_shc.status_code == 200:
                                    response[peer] = refresh_mmdb_shc_json
                        except Exception as e:
                            logger.error("Most possible issue is Bearer token is expired")
                            logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

                            for path, folders, files in os.walk(lookup_path):
                                for file in files:
                                    if file in list_of_files_to_exclude:
                                        continue
                                    if len(file) > 19:
                                        continue

                                    os.remove(os.path.join(path, file))
                                    logger.info("File Removed: " + os.path.join(path, file))
                            return {
                                "payload": "Internal Error Occured. Most possible issue is Bearer token is expired. But check $SPLUNK_HOME/var/log/splunk/ipgeolocation/ipgeolocation.log for more information.",
                                "status": 500
                            }
                    else:
                        logger.error(
                            "Error while accessing bearer Token. Please check whether you have admin access or Bearer token is configured."
                        )
                        logger.error("ipgeolocation.io was just updated on current machine")

                for path, folders, files in os.walk(lookup_path):
                    for file in files:
                        if file in list_of_files_to_exclude:
                            continue
                        if len(file) > 19:
                            continue
                        
                        os.remove(os.path.join(path, file))
                        logger.info("File Removed: " + os.path.join(path, file))

            except Exception as e:
                logger.error(e)
                logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))
                
                return {
                    "payload": "Internal Error Occurred. Please check $SPLUNK_HOME/var/log/splunk/ipgeolocation/ipgeolocation.log for more information.",
                    "status": 500,
                }

        logger.debug(response)
        return { "payload": response, "status": 200 }

    def handleStream(self, handle, in_string):
        """
        For future use
        """

        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass

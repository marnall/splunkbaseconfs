# File: nextcloud_connector.py
#
# Copyright (c) Ionut Ciubotarasu, 2023-2025
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
#
# !/usr/bin/python
# -*- coding: utf-8 -*-
# -----------------------------------------
# Phantom sample App Connector python file
# -----------------------------------------

# Python 3 Compatibility imports
import json
import random
import string
import sys

import nextcloud_client

# Phantom App imports
import phantom.app as phantom
import phantom.rules as ph_rules

# Usage of the consts file is recommended
# from nextcloud_consts import *
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class NextcloudConnector(BaseConnector):
    def __init__(self):
        super().__init__()
        self._state = None
        self._base_url = None
        self._username = None
        self._password = None
        self._verify_certs = None

    def _randomstr(self, size=20, chars=string.ascii_lowercase + string.digits):
        return "".join(random.choice(chars) for _ in range(size))

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to endpoint")
        self.debug_print("base_url", self._base_url)
        self.debug_print("verify_certs", self._verify_certs)

        nc = nextcloud_client.Client(self._base_url, verify_certs=self._verify_certs)
        nc.login(self._username, self._password)

        try:
            response = nc.get_version()
            self.save_progress(f"Nextcloud version:{response}")
        except Exception as e:
            response = None
            self.save_progress("Test Connectivity Failed.")
            return action_result.set_status(phantom.APP_ERROR, f"Error:{e}")
        finally:
            nc.logout()
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _make_rest_call(self, action, **kwargs):
        nc = nextcloud_client.Client(self._base_url, verify_certs=self._verify_certs)
        nc.login(self._username, self._password)
        rest_result = None
        if action == "upload_file":
            destination_path = kwargs.get("destination_path", None)
            file_path = kwargs.get("file_path", None)
            if destination_path is None and file_path is None:
                return False, rest_result
            result = nc.put_file(destination_path, file_path)
        elif action == "delete":
            delete_path = kwargs.get("delete_path", None)
            if delete_path is None:
                return False, rest_result
            result = nc.delete(delete_path)
        elif action == "create_folder":
            create_folder = kwargs.get("create_folder", None)
            if create_folder is None:
                return False, rest_result
            result = nc.mkdir(create_folder)
        elif action == "download_folder":
            download_folder = kwargs.get("download_folder", None)
            download_path = kwargs.get("download_path", None)
            file_name = kwargs.get("file_name", None)
            container_id = self.get_container_id()
            if download_folder is None or download_path is None or file_name is None:
                return False, rest_result
            result = nc.get_directory_as_zip(download_folder, download_path)
            rest_result = ph_rules.vault_add(container=container_id, file_location=download_path, file_name=file_name)
        elif action == "download_file":
            download_file = kwargs.get("download_file", None)
            download_path = kwargs.get("download_path", None)
            file_name = kwargs.get("file_name", None)
            container_id = self.get_container_id()
            if download_file is None or download_path is None or file_name is None:
                return False, rest_result
            result = nc.get_file(download_file, download_path)
            rest_result = ph_rules.vault_add(container=container_id, file_location=download_path, file_name=file_name)
        elif action == "list":
            path = kwargs.get("path", None)
            depth = kwargs.get("depth", None)
            if path is None or depth is None:
                return False, rest_result
            rest_result = nc.list(path, depth=depth)
            result = True
        elif action == "move":
            initial_path = kwargs.get("initial_path", None)
            destination_path = kwargs.get("destination_path", None)
            if initial_path is None or destination_path is None:
                return False, rest_result
            result = nc.move(initial_path, destination_path)
        elif action == "file_info":
            path = kwargs.get("path", None)
            if path is None:
                return False, rest_result
            rest_result = nc.file_info(path)
            result = True
        else:
            return False, rest_result
        if result is False:
            return False, rest_result
        return True, rest_result

    def _handle_upload_file(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        vault_id = param["vault_id"]
        self.save_progress(f"vault_id: {vault_id}")
        add_random_string = param["add_random_string"]
        try:
            success, _, data = ph_rules.vault_info(vault_id=vault_id)
            if not success:
                return action_result.set_status(phantom.APP_ERROR, f"Not found vault for {vault_id} id.")
            data = next(iter(data))
            name = data.get("name")
            file_path = data.get("path")
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "There was an issue opening the file: " + str(e))
        if add_random_string is False:
            destination_path = param["destination_path"].lstrip("/").rstrip("/") + "/" + name
        else:
            destination_path = param["destination_path"].lstrip("/").rstrip("/") + "/" + self._randomstr() + "_" + name
        result, rest_result = self._make_rest_call(action="upload_file", destination_path=destination_path, file_path=file_path)
        if result is False:
            return action_result.set_status(phantom.APP_ERROR, "Action failed")
        summary = action_result.update_summary({})
        summary["status"] = "Success"
        summary["destination_path"] = destination_path
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_item(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        path = param["path"].lstrip("/").rstrip("/")
        self.save_progress(f"path: {path}")
        result, rest_result = self._make_rest_call(action="delete", delete_path=path)
        if result is False:
            return action_result.set_status(phantom.APP_ERROR, "Action failed")
        summary = action_result.update_summary({})
        summary["status"] = "Success"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_folder(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        path = param["path"].lstrip("/").rstrip("/")
        self.save_progress(f"path: {path}")
        result, rest_result = self._make_rest_call(action="create_folder", create_folder=path)
        if result is False:
            return action_result.set_status(phantom.APP_ERROR, "Action failed")
        summary = action_result.update_summary({})
        summary["status"] = "Success"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_download_folder(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        path = param["path"].lstrip("/").rstrip("/")
        folder_name = path.split("/")[-1]
        download_path = "/tmp/" + self._randomstr() + folder_name + ".zip"
        self.save_progress(f"download_path: {download_path}")
        result, rest_result = self._make_rest_call(
            action="download_folder", download_folder=path, download_path=download_path, file_name=folder_name + ".zip"
        )
        if result is False:
            return action_result.set_status(phantom.APP_ERROR, "Action failed")
        summary = action_result.update_summary({})
        summary["status"] = "Success"
        summary["vault_id"] = rest_result[2]
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_download_file(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        path = param["path"].lstrip("/").rstrip("/")
        file_name = path.split("/")[-1]
        action_result = self.add_action_result(ActionResult(dict(param)))
        download_path = "/tmp/" + self._randomstr() + file_name
        self.save_progress(f"download_path: {download_path}")
        result, rest_result = self._make_rest_call(action="download_file", download_file=path, download_path=download_path, file_name=file_name)
        if result is False:
            return action_result.set_status(phantom.APP_ERROR, "Action failed")
        summary = action_result.update_summary({})
        summary["status"] = "Success"
        summary["vault_id"] = rest_result[2]
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_folder_content(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        path = param.get("path", "").lstrip("/").rstrip("/")
        self.save_progress(f"path: {path}")
        depth = param.get("depth", "")
        result, rest_result = self._make_rest_call(action="list", path=path, depth=depth)
        if result is False:
            return action_result.set_status(phantom.APP_ERROR, "Action failed")
        action_result.add_data({"result": [{"path": i.path, "file_type": i.file_type, "attributes": i.attributes} for i in rest_result]})
        summary = action_result.update_summary({})
        summary["status"] = "Success"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_move_file(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        initial_path = param.get("initial_path").lstrip("/").rstrip("/")
        self.save_progress(f"initial_path: {initial_path}")
        destination_path = param.get("destination_path").lstrip("/").rstrip("/")
        self.save_progress(f"destination_path: {destination_path}")
        result, rest_result = self._make_rest_call(action="move", initial_path=initial_path, destination_path=destination_path)
        if result is False:
            return action_result.set_status(phantom.APP_ERROR, "Action failed")
        summary = action_result.update_summary({})
        summary["status"] = "Success"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_file_info(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        path = param.get("path", "").lstrip("/").rstrip("/")
        self.save_progress(f"path: {path}")
        result, rest_result = self._make_rest_call(action="file_info", path=path)
        if result is False:
            return action_result.set_status(phantom.APP_ERROR, "Action failed")
        action_result.add_data({"path": rest_result.path, "file_type": rest_result.file_type, "attributes": rest_result.attributes})
        summary = action_result.update_summary({})
        summary["status"] = "Success"
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "upload_file":
            ret_val = self._handle_upload_file(param)

        if action_id == "delete_item":
            ret_val = self._handle_delete_item(param)

        if action_id == "create_folder":
            ret_val = self._handle_create_folder(param)

        if action_id == "download_folder":
            ret_val = self._handle_download_folder(param)

        if action_id == "download_file":
            ret_val = self._handle_download_file(param)

        if action_id == "get_folder_content":
            ret_val = self._handle_get_folder_content(param)

        if action_id == "move_file":
            ret_val = self._handle_move_file(param)

        if action_id == "get_file_info":
            ret_val = self._handle_get_file_info(param)

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        return ret_val

    def initialize(self):
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._base_url = config.get("nextcloud_url")
        self._username = config.get("username")
        self._password = config.get("password")
        self._verify_certs = config.get("verify_certs")

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", help="verify", required=False, default=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = NextcloudConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = NextcloudConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()

# File: playbookutils_connector.py
#
# Copyright (c) 2022-2025 Splunk Inc.
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

import json

import phantom.app as phantom
import requests
from anytree import NodeMixin, RenderTree
from anytree.exporter import DictExporter
from bs4 import BeautifulSoup
from phantom import rules as ph_rules
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


class Run(NodeMixin):
    def __init__(self, run_details, parent=None, children=None):
        self.run_details = run_details

        self.parent = parent
        if children:
            self.children = children


class PlaybookRun(Run):
    def __init__(self, run_details, parent=None, children=None):
        self.type = "playbook"

        self.run_id = run_details["id"]
        self.name = run_details["_pretty_playbook"]

        super().__init__(run_details, parent, children)


class AppRun(Run):
    def __init__(self, run_details, parent=None, children=None):
        self.type = "app"

        self.run_id = run_details["id"]
        self.name = run_details["action"]
        self.action = run_details["_pretty_action_run"]
        self.status = run_details["status"]

        super().__init__(run_details, parent, children)


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class PlaybookUtilsConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {e}"), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = f"Error from server. Status Code: {r.status_code} Data from server: {r.text.replace('{', '{{').replace('}', '}}')}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = (
            f"Can't process response from server. Status Code: {r.status_code} Data from server: {r.text.replace('{', '{{').replace('}', '}}')}"
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, url, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(ph_rules.requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        try:
            r = request_func(url, verify=config.get("verify_server_cert", False), timeout=30, **kwargs)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {e}"), resp_json)

        return self._process_response(r, action_result)

    def _determine_pb_run_id(self, action_result):
        """Figure out what the current playbook run id is by using the app_run_id, if it is running in a playbook. The current playbook
        run is the playbook run calling this specific instance of the current app run. If there is no associated playbook run, this will
        return an action_result error status.

        Args:
            action_result (ActionResult): Action result

        Returns:
            bool: Action result status
            str: Playbook repo name and playbook name
        """
        ret_val, app_run_resp = self._make_rest_call(
            ph_rules.build_phantom_rest_url("app_run", self.get_app_run_id(), "playbook_run"), action_result
        )
        if phantom.is_fail(ret_val):
            return RetVal(action_result.get_status(), None)

        pb_run_id = app_run_resp.get("playbook_run")
        if not pb_run_id:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"No playbook_run associated with this app_run: {self.get_app_run_id()}"), None
            )

        return RetVal(phantom.APP_SUCCESS, pb_run_id)

    def _determine_pb_and_repo_names(self, action_result):
        """Figure out what the current repo and playbook names by using the app_run_id, if it is running in a playbook.

        Args:
            action_result (ActionResult): Action result

        Returns:
            bool: Action result status
            (str, str): Playbook repo name and playbook name. None on error.
        """
        # Get playbook run ID
        ret_val, pb_run_id = self._determine_pb_run_id(action_result)
        if phantom.is_fail(ret_val):
            return RetVal(action_result.get_status(), (None, None))

        # Get playbook run details
        ret_val, pb_run_resp = self._make_rest_call(ph_rules.build_phantom_rest_url("playbook_run", pb_run_id), action_result, params={"pretty"})
        if phantom.is_fail(ret_val):
            return RetVal(action_result.get_status(), (None, None))

        repo_pb_names = (pb_run_resp.get("_pretty_scm_name"), pb_run_resp.get("_pretty_playbook"))

        if not all(repo_pb_names):
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, f"Unable to get playbook or repo name for app_run {self.get_app_run_id()}: {repo_pb_names}"
                ),
                repo_pb_names,
            )

        return RetVal(phantom.APP_SUCCESS, repo_pb_names)

    def _attach_pb_runs(self, action_result, pb_run, include_app_runs):
        """Attach playbook runs to the playbook.

        Args:
            action_result (ActionResult): Action result
            pb_run (PlaybookRun): Playbook run to attach app runs

        Returns:
            bool: Action result status
        """
        params = {"pretty": True, "_filter_parent_run": pb_run.run_id, "page_size": 0, "sort": "id"}
        ret_val, child_pb_runs = self._make_rest_call(ph_rules.build_phantom_rest_url("playbook_run"), action_result, params=params)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for child_pb_run_details in child_pb_runs.get("data", []):
            child_pb_run = PlaybookRun(child_pb_run_details, pb_run)
            ret_val = self._attach_descendants(action_result, child_pb_run, include_app_runs)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

        return phantom.APP_SUCCESS

    def _attach_app_runs(self, action_result, pb_run):
        """Attach app runs to a playbook as descendants

        Args:
            action_result (ActionResult): Action result
            pb_run (PlaybookRun): Playbook run to attach app runs

        Returns:
            bool: Action result status
        """
        params = {"pretty": True, "_filter_playbook_run": pb_run.run_id, "page_size": 0, "sort": "id"}
        ret_val, app_runs = self._make_rest_call(ph_rules.build_phantom_rest_url("app_run"), action_result, params=params)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for app_run in app_runs.get("data", []):
            if app_run.get("id"):
                # ret_val, app_run_details = self._get_app_run(action_result, app_run['id'])
                # if phantom.is_fail(ret_val):
                #     self.debug_print(f'Error getting details about app_run: {app_run["id"]}')
                #     continue
                # if app_run_details.get('failed'):
                #     self.debug_print(f'Error returned when getting details about app_run: {app_run["id"]} Error: {app_run_details["message"]}')
                #     continue

                AppRun(app_run, pb_run)

        return phantom.APP_SUCCESS

    def _attach_descendants(self, action_result, parent_pb_run, include_app_runs):
        """Attach app runs or child playbooks to another playbook

        Args:
            action_result (ActionResult): Action result
            parent_pb_run (PlaybookRun): Playbook run to attach descendants
            include_app_runs (bool): Include app runs as descendants to the playbook

        Returns:
            bool: Action result status
        """

        if include_app_runs:
            ret_val = self._attach_app_runs(action_result, parent_pb_run)
            if phantom.is_fail(ret_val):
                self.debug_print(action_result.get_message())
                action_result.set_status(phantom.APP_SUCCESS)

        self._attach_pb_runs(action_result, parent_pb_run, include_app_runs)

        return phantom.APP_SUCCESS

    def _get_app_run(self, action_result, app_run_id):
        """Get app run information

        Args:
            action_result (ActionResult): Action result
            app_run_id (int): App run ID of app run to get details

        Returns:
            RetVal:
                bool: ActionResult status
                dict: Phantom app run details
        """
        params = {"pretty": True}
        ret_val, app_run = self._make_rest_call(ph_rules.build_phantom_rest_url("app_run", app_run_id), action_result, params=params)
        if phantom.is_fail(ret_val):
            return RetVal(action_result.get_status(), {})

        return RetVal(phantom.APP_SUCCESS, app_run)

    def _get_pb_run(self, action_result, pb_run_id):
        """Get playbook run information

        Args:
            action_result (ActionResult): Action result
            pb_run_id (int): Playbook ID to get the run information

        Returns:
            RetVal:
                bool: ActionResult status
                dict: Phantom playbook run details
        """

        ret_val, pb_run_resp = self._make_rest_call(
            ph_rules.build_phantom_rest_url("playbook_run", pb_run_id), action_result, params={"pretty": True}
        )
        if phantom.is_fail(ret_val):
            return RetVal(action_result.get_status(), None)

        return RetVal(phantom.APP_SUCCESS, pb_run_resp)

    def _get_run_tree(self, action_result, pb_run_id, include_app_runs=True):
        """Get the root playbook and attach the descendants

        Args:
            action_result (ActionResult): Action result
            pb_run_id (int): Playbook run ID  that belongs to the tree that we are looking to get the tree
            include_app_runs (bool): Get the app runs of the playbooks in the tree

        Returns:
            RetVal:
                bool: ActionResult status
                PlaybookRun: Root playbook run
        """
        root_pb_run = None

        # Dive into each parent playbook, until we get the top_level (or root) playbook
        # Limit runs during development to 25
        for x in range(25, -1, -1):
            if x == 0:
                message = "Loop limit reached when trying to get to root pb"
                return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

            ret_val, pb_run = self._get_pb_run(action_result, pb_run_id)
            if phantom.is_fail(ret_val):
                return RetVal(action_result.get_status(), None)

            parent_run = pb_run.get("parent_run")
            if parent_run:
                pb_run_id = parent_run
            else:
                root_pb_run = PlaybookRun(pb_run)
                break

        if not root_pb_run:
            message = "Unable to get the root Playbook run"
            return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

        ret_val = self._attach_descendants(action_result, root_pb_run, include_app_runs)
        if phantom.is_fail(ret_val):
            return RetVal(action_result.get_status(), None)

        return RetVal(phantom.APP_SUCCESS, root_pb_run)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.

        self.save_progress("Connecting to endpoint")
        # make rest call
        ret_val, response = self._make_rest_call(ph_rules.build_phantom_rest_url("version"), action_result)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_playbook_tree(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        pb_run_id = param.get("playbook_run_id")
        include_app_runs = param.get("include_app_runs", True)

        # If it isn't provided, use the current app_run to get the PB Run ID
        if not pb_run_id:
            ret_val, pb_run_id = self._determine_pb_run_id(action_result)
            if phantom.is_fail(ret_val):
                return action_result.get_status()

        ret_val, run_tree = self._get_run_tree(action_result, pb_run_id, include_app_runs)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        exporter = DictExporter()

        summary = action_result.update_summary({})
        rendered_tree_list = []
        pb_run_ids = []
        app_run_ids = []
        for pre, fill, node in RenderTree(run_tree):
            # Replace space with a figure space to not get chopped down in action_results UI
            pre = pre.replace(" ", "\u2007")
            fill = fill.replace(" ", "\u2007")

            # Add each node into data
            data = exporter.export(node)
            data["tree_prefix"] = pre
            data["tree_fill"] = fill
            if "children" in data:
                del data["children"]
            action_result.add_data(data)

            # Create text representation of tree view
            if node.type == "app":
                rendered_tree_list.append(f"{pre}<{node.type}-{node.run_id}> {node.action} [{node.status}]")
                app_run_ids.append(node.run_id)
            else:
                rendered_tree_list.append(f"{pre}<{node.type}-{node.run_id}> {node.name}")
                pb_run_ids.append(node.run_id)

        summary["rendered_playbook_tree"] = rendered_tree_list
        summary["playbook_run_ids"] = sorted(pb_run_ids)

        app_run_message = ""
        if include_app_runs:
            summary["app_run_ids"] = sorted(app_run_ids)
            app_run_message = f" and {len(app_run_ids)} app run(s)"

        return action_result.set_status(phantom.APP_SUCCESS, f"Found {len(pb_run_ids)} playbook run(s){app_run_message}.")

    def handle_action(self, param):
        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", action_id)

        action_map = {"test_connectivity": self._handle_test_connectivity, "get_playbook_tree": self._handle_get_playbook_tree}

        if action_id not in action_map:
            return self.set_status(phantom.APP_ERROR, "Action identifier is not available.")

        return action_map[action_id](param)

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        self._base_url = config.get("base_url")

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse
    import sys

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

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
            login_url = PlaybookUtilsConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=30)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=30)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = PlaybookUtilsConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()

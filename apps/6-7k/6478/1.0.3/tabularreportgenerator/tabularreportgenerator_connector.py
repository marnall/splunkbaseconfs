# Copyright (c) 2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#!/usr/bin/python


# Usage of the consts file is recommended
import json
from pathlib import Path

# Phantom App imports
import phantom.app as phantom
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from pydantic import ValidationError

from tabularreportgenerator_consts import DEFAULT_TIMEOUT
from tabularreportgenerator_email import make_email
from tabularreportgenerator_html import load_template, make_html
from tabularreportgenerator_soar import get_custom_list
from tabularreportgenerator_types import Report


class TabularReportGeneratorConnector(BaseConnector):
    def __init__(self):
        super().__init__()
        self._state = None

    def initialize(self):
        self._state = self.load_state()
        config = self.get_config()
        self._image_list = config.get("image_list")

        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        if self._image_list:
            self.save_progress("Check if image lists exists")
            try:
                get_custom_list(self, self._image_list)
            except Exception as err:
                self.save_progress("Test Connectivity Failed")
                return action_result.set_status(phantom.APP_ERROR, f"Could not find custom list: {err}")

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_generate_report_email(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        from_email = param["from"]
        to_email = param["to"]
        subject = param["subject"]

        try:
            report_json = json.loads(param["report_json"])
        except ValueError as err:
            return action_result.set_status(phantom.APP_ERROR, f"Please provide valid JSON as report_json: {err}")

        try:
            report = Report(**report_json)
        except ValidationError as err:
            return action_result.set_status(phantom.APP_ERROR, f"Please provide a valid report specification as report_json: {err}")

        templates_dir = Path(__file__).parent.resolve() / "templates"
        report_template = templates_dir / Path("report.j2")
        report_template = load_template(report_template)
        report_html = make_html(report, report_template)

        try:
            report_rawmail = make_email(self, report, report_html, from_email, to_email, subject, self._image_list)
        except Exception as err:
            msg = f"Email generation failed: {err}"
            self.error_print(msg)
            return action_result.set_status(phantom.APP_ERROR, msg)

        action_result.add_data(report_rawmail)

        # summary = action_result.update_summary({})

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        action_id = self.get_action_identifier()
        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "generate_report_email":
            ret_val = self._handle_generate_report_email(param)

        return ret_val


def main():
    import argparse
    import sys

    import pudb

    pudb.set_trace()

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
            login_url = TabularReportGeneratorConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, timeout=DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, data=data, headers=headers, timeout=DEFAULT_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = TabularReportGeneratorConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()

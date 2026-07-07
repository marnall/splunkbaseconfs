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
# File: cybereason_session.py
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


import requests

from cybereason_consts import DEFAULT_REQUEST_TIMEOUT


class CybereasonSession:
    def __init__(self, connector):
        connector.save_progress("Logging in to the Cybereason console...")
        self.session = requests.Session()
        post_body = {"username": connector._username, "password": connector._password}
        try:
            url = f"{connector._base_url}/login.html"
            res = self.session.post(url, data=post_body, verify=connector._verify_server_cert, timeout=DEFAULT_REQUEST_TIMEOUT)
            if self.session.cookies.get_dict().get("JSESSIONID") is None:
                connector.save_progress("Error when logging in to the the Cybereason console: No session cookie returned")
                connector.save_progress(f"Status code: {res.status_code}")
                connector.debug_print(f"Status code: {res.status_code}, message: {res.text}")
            elif res.status_code != 200:
                connector.save_progress("Error when logging in to the Cybereason console: Unknown error")
                connector.save_progress(f"Status code: {res.status_code}")
                connector.debug_print(f"Status code: {res.status_code}, message: {res.text}")
            else:
                connector.save_progress("Successfully logged in to the Cybereason console")
                connector.save_progress("CybereasonSession created")
        except requests.exceptions.InvalidSchema:
            connector.save_progress(f"Error connecting to server. No connection adapters were found for {url}")
        except requests.exceptions.InvalidURL:
            connector.save_progress(f"Error connecting to server. Invalid URL {url}")
        except requests.exceptions.ConnectionError:
            connector.save_progress("Error Details: Connection Refused from the Server")
        except Exception as e:
            err = connector._get_error_message_from_exception(e)
            connector.save_progress(f"Error connecting to server. {err}")

    def get_session(self):
        return self.session

    def get_session_cookies(self):
        return self.session.cookies.get_dict()

    def post(self, **kwargs):
        return self.session.post(kwargs)

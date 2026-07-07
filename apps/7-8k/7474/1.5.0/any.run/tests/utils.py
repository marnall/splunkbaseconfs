# Copyright (c) 2025-2026 Splunk Inc.
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
from typing import Optional

import requests

from anyrun_connector import AnyRunConnector


def setup_connector(
    username: Optional[str] = None, password: Optional[str] = None, session_id: Optional[str] = None
) -> tuple[AnyRunConnector, str]:
    """
    Setup the connector and return the connector and the session id
    """
    connector = AnyRunConnector()

    if not session_id:
        connector.print_progress_message = True
        try:
            login_url = connector._get_phantom_base_url() + "/login"

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

            connector._set_csrf_info(csrftoken, headers["Referer"])
        except Exception as e:  # pylint: disable=broad-except
            print("Unable to get session id from the platform. Error: " + str(e))
            exit(1)

    return connector, session_id

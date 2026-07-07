# File: soleraconnector.py
#
# Copyright (c) 2019-2025 Splunk Inc.
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
import os
import os.path

import requests


DEFAULT_REQUEST_TIMEOUT = 60  # in seconds


class SoleraConnector:
    def __init__(self, username, apiKey, ip, version=False, verify=False):
        """The initlization method for the SoleraConnector.

        Keyword arguments:
        username -- A string that is the username of the person making the requests
        apiKey -- A string of the apiKey
        ip -- A string of the IP address of the appliance
        """
        self.username = username
        self.apiKey = apiKey
        self.ip = ip
        self.verify = verify

        if not version:
            result = self.getVersion()
            if "response" in result:
                version = result["response"].pop()
            elif "resultCode" in result and result["resultCode"] == "API_INVALID_USER_CODE":
                raise Exception("Invalid username/apiKey")
            else:
                raise Exception("Unable to determine api version")

        self.version = version

    def getVersion(self):
        baseUrl = f"https://{self.ip}/api/list"

        return self._request("GET", baseUrl)

    def callAPI(self, method, url, data={}, download=False):
        """Calls the API of a service and returns the result.

        Keyword arguments:
        method -- A string of the HTTP Method(GET,POST)
        url -- A string of the api url(not complete url)
        data -- A Dictionary of the data that will be sent(default {})
        download -- A string of the name the file should be give.
            If no string is given it assumes it's not a download(default False)
        """
        if url[0:1] == "/":
            url = url[1:]
        baseUrl = f"https://{self.ip}/api/v{self.version}/{url}"

        return self._request(method, baseUrl, data, download)

    def _request(self, method, url, data={}, download=False):
        post = {}
        files = {}
        if len(data) != 0:
            for k, v in data.items():
                try:
                    isStr = isinstance(v, basestring)
                except NameError:
                    isStr = isinstance(v, str)
                if isStr and os.path.isfile(v):
                    files[k] = open(v, "rb")
                else:
                    post[k] = json.dumps(v)
            if method != "POST":
                post["_method"] = method
            f = requests.post(
                url, auth=(self.username, self.apiKey), data=post, files=files, verify=self.verify, stream=True, timeout=DEFAULT_REQUEST_TIMEOUT
            )
        elif method == "POST":
            post = {}
            files = {}
            post["_method"] = method
            f = requests.post(
                url, auth=(self.username, self.apiKey), data=post, files=files, verify=self.verify, timeout=DEFAULT_REQUEST_TIMEOUT
            )
        else:
            f = requests.get(url, auth=(self.username, self.apiKey), verify=self.verify, stream=True, timeout=DEFAULT_REQUEST_TIMEOUT)

        # If download download to correct area
        if download:
            chunk_size = 1000
            with open(download, "wb") as dfile:
                for chunk in f.iter_content(chunk_size):
                    dfile.write(chunk)
            filesize = os.path.getsize(download)
            return {"download_file": download, "filesize": filesize}
        else:  # Else return the data
            resp = f.text
            return json.loads(resp)

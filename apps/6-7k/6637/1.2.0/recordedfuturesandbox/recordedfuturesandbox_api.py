# File: recordedfuturesandbox_api.py
#
# Copyright (c) 2022-2024 Recorded Future, Inc.
#
# This unpublished material is proprietary to Recorded Future. All
# rights reserved. The methods and techniques described herein are
# considered trade secrets and/or confidential. Reproduction or
# distribution, in whole or in part, is forbidden except by express
# written permission of Recorded Future.

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

import requests


class TriageAPI:
    def __init__(
        self, api_key, url=None, api_path=None, verify_ssl=True, user_agent=None
    ):
        """
        :type   api_key:    str
        :param  api_key:    The API key which can be found on the /account page
                            on the Triage web interface

        :type   url         str
        :param  url         The url (including the port) of the Triage instance
                            defaults to https://api.tria.ge

        :type   api_path    str
        :param  api_path    The path to the API on the Triage instance
                            defaults to /v0
        """

        self.api_key = api_key

        self.base_url = url or "https://api.tria.ge"

        if not self.base_url.startswith("http"):
            self.base_url = "https://{:s}".format(self.base_url)

        self.api_url = self.base_url + (api_path or "/v0").rstrip("/")

        self.headers = {"Authorization": "Bearer {:s}".format(api_key)}
        if user_agent:
            self.headers["User-Agent"] = user_agent

        self.verify_ssl = verify_ssl

    def request(self, uri, method="GET", params=None, files=None, _json=None):
        url = "{:s}{:s}".format(self.api_url, uri)

        response = requests.request(
            method, url, params=params, files=files, headers=self.headers, json=_json
        )

        try:
            response.raise_for_status()
        except requests.RequestException as e:
            raise TriageException(
                "Recorded Future Sandbox returned an unexpected "
                "HTTP status {:s}".format(str(e))
            )
        # Try parsing the response as JSON to see if we got a valid object.
        # We remove null byte characters because these can cause issues when
        # being inserted into PostgreSQL by Splunk.
        # (can be part of DNS PTR responses, etc)
        try:
            data = json.loads(
                response.content.replace(rb"\u0000", b"").replace(b"\x00", b"")
            )
        except ValueError as e:
            raise TriageException(
                "Recorded Future Sandbox returned a non JSON response "
                "{:s}".format(str(e))
            )

        # If we got a normal object check whether we didn't receive an error
        # object
        if "error" in data.keys():
            raise TriageException(
                "Recorded Future Sandbox raised an error: {:s} - {:s}".format(
                    data["error"], data["message"]
                )
            )

        # Everything is good to go
        return data

    def analyze(
        self, handle, filename, user_tags, timeout=None, profile=None, password=None
    ):
        """Submit a file for analysis.

        :type  handle:   File handle
        :param handle:   Handle to file to upload for analysis.
        :type  filename: str
        :param filename: File name.
        :type  profile   str
        :param profile   Profile ID
        :param password  If password protected file.
        :param user_tags Arrary of strings to mark sample.
        :param timeout   Timeout of the analysis.

        :rtype:  str
        :return: File ID as a string
        """
        files = {"file": (filename, handle)}

        data = {
            "kind": "file",
            "interactive": False,
            "user_tags": user_tags,
        }

        if timeout:
            data["defaults"] = {"timeout": timeout}

        if profile:
            data["profiles"] = [{"profile": profile}]

        if password:
            data.update({"password": password})

        params = {"_json": json.dumps(data)}

        # Ensure the handle is at offset 0.
        handle.seek(0)

        # Make the request to Triage
        data = self.request("/samples", method="POST", files=files, params=params)

        if "id" in data.keys():
            return data["id"]
        else:
            raise TriageException("Recorded Future Sandbox returned no ID")

    def analyze_url(self, url, kind="url", user_tags=None, timeout=None, profile=None):
        """Submit a file for analysis.

        :type  url:      str
        :param url:      URL to analyze.
        :type  kind:     str
        :param kind:     The kind of analysis to run: url|fetch
        :type  profile   str
        :param profile   Profile ID

        :rtype:  str
        :return: File ID as a string
        """
        params = {
            "url": url,
            "kind": kind,
            "interactive": False,
            "user_tags": user_tags,
        }

        if timeout:
            params["defaults"] = {"timeout": timeout}

        if profile:
            params["profiles"] = [profile]

        # Make the request to Triage
        data = self.request("/samples", method="POST", _json=params)

        if "id" in data.keys():
            return data["id"]
        else:
            raise TriageException("Recorded Future Sandbox returned no ID")

    def check(self, item_id):
        """Check if an analysis is complete.

        :type  item_id: str
        :param item_id: Analysis ID to check.

        :rtype:  str
        :return: String value containing current analysis status.
        """

        data = self.request("/samples/{:s}/summary".format(item_id))

        if "status" in data.keys():
            return data["status"]
        else:
            raise TriageException("Recorded Future Sandbox didn't return a status")

    def is_available(self):
        """Determine if the Triage server is alive.

        :rtype:  bool
        :return: True if service is available, False otherwise.
        """

        try:
            self.request("/samples")
        except TriageException:
            return False

        return True

    def report(self, item_id, report_format="json"):
        """Retrieves the specified report for the analyzed item,
        referenced by item_id. Note that the summary is returned and more
        detailed information is available.

        :param str item_id: The id of the submitted file.
        :param str report_format:   In here for compatibility though Triage
                                    only supports the JSON format

        :rtype: dic
        :return: Dictionary representing the JSON parsed data.
        """

        if report_format != "json":
            raise TriageException(
                "Recorded Future Sandbox api only supports the json report " "format"
            )

        data = self.request("/samples/{:s}/summary".format(item_id))
        tasks = data["tasks"]
        new_tasks = {}

        for key, value in tasks.items():
            new_key = key.replace("{:s}-".format(item_id), "")
            new_tasks[new_key] = value

        data["tasks"] = new_tasks

        return data

    def score(self, item_id):
        """Gives back the highest score choosing from all the analyses

        :param str item_id: The id of the submitted file.

        :rtype: int
        :return: int on a scale from 1 til 10
        """
        report = self.report(item_id)
        # 1 Is the Triage base score
        score = 1

        # Loop over the available reports to pick the highest score
        for task_id, task in report["tasks"].items():
            if "score" in task:
                if task["score"] > score:
                    score = task["score"]

        return score

    def full_report(self, item_id):
        """Retrieves the summary report and the full report of each task for
        the analyzed item, referenced by item_id.

        :param str item_id: The id of the submitted file.

        :rtype: dic
        :return: Dictionary representing the JSON parsed data.
        """
        report = self.report(item_id)
        full_report = {"summary": report, "tasks": {}}

        # Loop over all the tasks in the summary
        for task_id in report["tasks"]:
            # Remove the sample ID to get the task names
            task_name = task_id.replace("{:s}-".format(item_id), "")

            try:
                # Try to retrieve each full report
                triage_report = self.request(
                    "/samples/{:s}/{:s}/report_triage.json".format(item_id, task_name)
                )
                full_report["tasks"][task_name] = triage_report
            except TriageException:
                continue

        return full_report

    def get_pcap(self, item_id):
        pass


class TriageException(Exception):
    pass

# File: isightpartners_views.py
#
# Copyright (c) 2014-2025 Splunk Inc.
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


def get_report(provides, all_results, context):
    context["results"] = results = []

    headers = ["Report ID", "Report Title", "Publish Date"]
    context["headers"] = headers

    for summary, action_results in all_results:
        for result in action_results:
            table = dict()
            table["data"] = rows = []
            data = result.get_data()

            for item in data:
                row = []
                if not item.get("report"):
                    continue
                row.append({"value": item.get("report").get("reportId")})
                row.append({"value": item.get("report").get("title")})
                row.append({"value": item.get("report").get("publishDate")})
                rows.append(row)
            results.append(table)

    return "isightpartners_get_report.html"

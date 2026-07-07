# File: mongodb_view.py
#
# Copyright (c) 2018-2025 Splunk Inc.
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
def display_query_results(provides, all_results, context):
    headers = []
    context["results"] = results = []

    headers_set = set()
    for summary, action_results in all_results:
        for result in action_results:
            for record in result.get_data():
                headers_set.update(record.keys())

    if not headers_set:
        headers_set.update(headers)
    headers.extend(headers_set)
    headers.sort(key=str.lower)
    final_result = {"headers": headers, "data": []}

    for summary, action_results in all_results:
        for result in action_results:
            data = result.get_data()
            for item in data:
                row = []
                for header in headers:
                    row.append(item.get(header, ""))
                final_result["data"].append(row)

    results.append(final_result)
    return "display_results.html"

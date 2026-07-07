# File: microsoftsqlserver_view.py
#
# Copyright (c) 2017-2026 Splunk Inc.
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
#
# from django.http import HttpResponse
import json


def display_query_results(provides, all_results, context):
    context["results"] = results = []
    for summary, action_results in all_results:
        for result in action_results:
            ctx_result = {"param": result.get_param()}

            add_datasets_as_rows = ctx_result["param"].get("add_datasets_as_rows", False)
            # ctx_result['add_datasets_as_rows'] = add_datasets_as_rows
            # ctx_result['description_headers'] = ["name", "type_code", "display_size", "internal_size", "precision", "scale", "null_ok"]

            data = reformat_data(
                result.get_data(), ["name", "type_code", "display_size", "internal_size", "precision", "scale", "null_ok"], add_datasets_as_rows
            )

            if data:
                ctx_result["tables"] = data

            # ctx_result['headers'] = data[0]['headers']
            # ctx_result['rows'] = data[0]['rows']

            summary = result.get_summary()
            if summary:
                ctx_result["summary"] = summary

            results.append(ctx_result)

    return "run_query.html"


def reformat_data(data, description_headers, add_datasets_as_rows):
    ret = []

    if add_datasets_as_rows:
        for index, dataset in enumerate(data):
            newdataset = {}
            ret += [newdataset]
            newdataset["index"] = index
            newdataset["headers"] = sorted(dataset["dataset"][0].keys())
            newdataset["dataset"] = []

            for row in dataset["dataset"]:
                newrow = []
                newdataset["dataset"] += [newrow]

                for col in newdataset["headers"]:
                    newrow += [row[col]]

            newdataset["description"] = []
            for name in sorted(dataset["description"].keys()):
                newrow = []
                newdataset["description"] += [newrow]
                newrow += [name]

                for i, col in enumerate(description_headers):
                    if i:
                        newrow += [dataset["description"][name].get(col, "")]

            newdataset["dump"] = json.dumps(newdataset)

    else:
        index = 0
        headers = []

        for i, row in enumerate(data):
            newheaders = sorted(row.keys())
            if set(headers) != set(newheaders):
                headers = newheaders
                newdataset = {}
                ret += [newdataset]
                newdataset["index"] = index
                index += 1
                newdataset["headers"] = sorted(row.keys())
                newdataset["dataset"] = []

            newrow = []
            newdataset["dataset"] += [newrow]
            for col in headers:
                newrow += [row[col]]

            newdataset["dump"] = json.dumps(newdataset)

    newret = []
    for i, dataset in enumerate(ret):
        if "description" in dataset:
            newdataset = {}
            newret += [newdataset]
            newdataset["name"] = "Description for Dataset #" + str(i)
            newdataset["headers"] = description_headers
            newdataset["rows"] = dataset["description"]
            for r, row in enumerate(newdataset["rows"]):
                for c, cell in enumerate(row):
                    newdataset["rows"][r][c] = {"value": cell}

        newdataset = {}
        newret += [newdataset]
        newdataset["name"] = "Dataset #" + str(i)
        newdataset["headers"] = dataset["headers"]
        newdataset["rows"] = dataset["dataset"]
        for r, row in enumerate(newdataset["rows"]):
            for c, cell in enumerate(row):
                newdataset["rows"][r][c] = {"value": cell}

    return newret

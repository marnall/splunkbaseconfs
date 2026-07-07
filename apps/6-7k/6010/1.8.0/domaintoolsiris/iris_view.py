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
ACTION_VIEW_TEMPLATES_DICT = {
    "domain reputation": "iris_risk_score.html",
    "enrich domain": "iris_enrich_domain_profile.html",
    "lookup domain": "iris_domain_profile.html",
}


def display_view(provides, all_app_runs, context):
    context["results"] = results = []
    for _, action_results in all_app_runs:
        for result in action_results:
            ctx_result = get_ctx_result(result)
            if not ctx_result:
                continue

            results.append(ctx_result)

    return ACTION_VIEW_TEMPLATES_DICT.get(provides)


def get_ctx_result(result):
    ctx_result = {}
    param = result.get_param()
    data_list = result.get_data()
    if data_list:
        ctx_result["param"] = param
        ctx_result["data"] = []
        ctx_result["sorted_data"] = []
        for data in data_list:
            extracted_data = extract_data(data)
            ctx_result["data"].append(extracted_data)
            sorted_keys = sorted(
                extracted_data,
                key=lambda kv_pair: (not kv_pair.startswith("domain"), kv_pair),
            )
            sorted_data = []

            # TODO: This is temporary only. Remove this from the sorted_data once update on pivot links is implemented
            queried_domain = extracted_data.get("domain")

            for key in sorted_keys:
                if extracted_data[key] or extracted_data[key] == 0:
                    data_count = ""
                    if isinstance(extracted_data[key], dict):
                        value = extracted_data[key].get("value")
                        count = extracted_data[key].get("count")
                        if value in ("", "None", None):
                            continue
                        data_value = value
                        data_count = count if count and count != 0 else ""
                    else:
                        data_value = extracted_data[key]

                    is_list = isinstance(data_value, list)
                    key = " ".join(unique_list(key.split()))
                    sorted_data.append((key, data_value, data_count, is_list, queried_domain))
            ctx_result["sorted_data"].append(sorted_data)

    return ctx_result


def extract_data(data, parent_key="", sep=" "):
    items = []
    for k, v in data.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict) and "value" in v:
            items.append((new_key.replace("_", " "), v))
            continue

        if isinstance(v, dict):
            items.extend(extract_data(v, new_key, sep=sep).items())
        else:
            if v and isinstance(v, list):
                new_key = new_key.replace("_", " ")
                if new_key in ("domain risk components", "tags"):
                    items.append((new_key, remove_underscore(v)))
                else:
                    items.append((new_key.replace("_", " "), extract_list(v)))
                continue

            items.append((new_key.replace("_", " "), v))

    return dict(items)


def extract_list(value):
    items = []
    for val in value:
        if isinstance(val, dict):
            for k, v in val.items():
                if v and isinstance(v, list) and "value" in v[0]:
                    val[k] = v[0]

        items.append(val)

    return items


def remove_underscore(value):
    items = []
    for components in value:
        comp_dict = {}
        for k, v in components.items():
            if isinstance(v, str):
                v = v.replace("_", " ")
            if k != "risk_score":
                k = k.replace("_", " ")
            comp_dict[k] = v
        items.append(comp_dict)

    return items


def unique_list(raw_list):
    ulist = []
    [ulist.append(element) for element in raw_list if element not in ulist]

    return ulist

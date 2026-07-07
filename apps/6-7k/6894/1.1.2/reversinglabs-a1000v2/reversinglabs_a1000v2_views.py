# File: reversinglabs_a1000v2_views.py
#
# Copyright (c) ReversingLabs, 2023-2025
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
def advanced_search(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            for x in result.get_data():
                x["classification_color"] = color_code_classification(x.get("classification").upper())
            context["data"] = result.get_data()
            context["results_found"] = f"Results found: {len(result.get_data())!s}"
            context["param"] = result.get_param()

    return "views/reversinglabs_advanced_search.html"


def advanced_search_local(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
            for r in context["data"]["results"]:
                r["classification_color"] = color_code_classification(r.get("classification").upper())

    return "views/reversinglabs_advanced_search_local.html"


def advanced_search_ticloud(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
            for r in context["data"]["results"]:
                r["classification_color"] = color_code_classification(r["classification"].upper())

    return "views/reversinglabs_advanced_search_ticloud.html"


def get_classification(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["classification"] = context["data"].get("classification", "UNAVAILABLE").upper()
            context["classification_color"] = color_code_classification(context["classification"])
    return "views/reversinglabs_get_classification.html"


def get_detailed_report(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["classification"] = context["data"].get("results")[0].get("classification").upper()
            context["classification_color"] = color_code_classification(context["classification"])
            context["param"] = result.get_param()

    return "views/reversinglabs_get_detailed_report.html"


def get_summary_report(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["classification"] = context["data"].get("results")[0].get("classification").upper()
            context["classification_color"] = color_code_classification(context["classification"])
            context["param"] = result.get_param()

    return "views/reversinglabs_get_summary_report.html"


def get_titaniumcore_report(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["classification"] = get_status_from_ticore_classification(
                context["data"].get("classification").get("classification")
            ).upper()
            context["classification_color"] = color_code_classification(context["classification"])
            context["param"] = result.get_param()

    return "views/reversinglabs_get_titaniumcore_report.html"


def url_reputation(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["classification"] = context["data"].get("classification", "UNAVAILABLE").upper()
            context["classification_color"] = color_code_classification(context["classification"])
            context["summary"] = result.get_summary()

    return "views/reversinglabs_url_reputation.html"


def domain_reputation(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["summary"] = result.get_summary()

    return "views/reversinglabs_domain_reputation.html"


def ip_reputation(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["summary"] = result.get_summary()

    return "views/reversinglabs_ip_reputation.html"


def network_ip_to_domain(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()

    return "views/reversinglabs_network_ip_to_domain.html"


def network_urls_from_ip(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()

    return "views/reversinglabs_network_urls_from_ip.html"


def network_files_from_ip(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
            for x in context["data"].get("downloaded_files"):
                x["classification_color"] = color_code_classification(x.get("classification").upper())

    return "views/reversinglabs_network_files_from_ip.html"


def check_dynamic_analysis_report_status(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()

    return "views/reversinglabs_check_dynamic_analysis_report_status.html"


def check_pdf_report_status(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()

    return "views/reversinglabs_check_pdf_report_status.html"


def check_submitted_url_status(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
            if context["data"].get("report", {}).get("sample_summary", {}).get("classification", {}):
                classification = context["data"]["report"]["sample_summary"]["classification"].upper()
                context["classification_color"] = color_code_classification(classification)
                context["classification"] = classification

    return "views/reversinglabs_check_submitted_url_status.html"


def submit_url(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()

    return "views/reversinglabs_submit_url.html"


def get_user_tags(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()

    return "views/reversinglabs_get_user_tags.html"


def create_user_tags(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()

    return "views/reversinglabs_create_user_tags.html"


def delete_user_tags(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()

    return "views/reversinglabs_delete_user_tags.html"


def set_sample_classification(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = result.get_data()[0]
            context["param"] = result.get_param()
            context["data"] = data
            if data["source"] == "local":
                context["classification"] = data["content"].get("classification", "UNAVAILABLE").upper()
                context["classification_color"] = color_code_classification(context["classification"])

    return "views/reversinglabs_set_sample_classification.html"


def yara_get_rulesets(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
    return "views/reversinglabs_yara_get_rulesets.html"


def yara_get_ruleset_text(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
    return "views/reversinglabs_yara_get_ruleset_text.html"


def yara_get_matches(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
            context["summary"] = result.get_summary()
            classification = {
                "known": 0,
                "unknown": 0,
                "suspicious": 0,
                "malicious": 0,
                "total": 0,
            }
            for x in context["data"]["results"]:
                x["classification"] = get_status_from_ticore_classification(x.get("classification"))
                x["classification_color"] = color_code_classification(x["classification"])
                classification[x["classification"]] += 1
                classification["total"] += 1
            context["chart"] = {
                "classification": classification,
            }
    return "views/reversinglabs_yara_get_matches.html"


def yara_create_ruleset(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
    return "views/reversinglabs_yara_create_ruleset.html"


def yara_delete_ruleset(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
    return "views/reversinglabs_yara_delete_ruleset.html"


def yara_toggle_ruleset(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
    return "views/reversinglabs_yara_toggle_ruleset.html"


def yara_get_sync_time(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
    return "views/reversinglabs_yara_get_sync_time.html"


def yara_set_sync_time(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
    return "views/reversinglabs_yara_set_sync_time.html"


def yara_toggle_retro_scan_local(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
    return "views/reversinglabs_yara_toggle_retro_scan_local.html"


def yara_manage_retro_scan_cloud(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
    return "views/reversinglabs_yara_manage_retro_scan_cloud.html"


def yara_status_retro_scan_local(provides, all_app_runs, context):
    for summary, action_result in all_app_runs:
        for result in action_result:
            context["data"] = result.get_data()[0]
    return "views/reversinglabs_yara_status_retro_scan_local.html"


def yara_status_retro_scan_cloud(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
    return "views/reversinglabs_yara_status_retro_scan_cloud.html"


def list_containers_for_hash(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
    return "views/reversinglabs_list_containers_for_hash.html"


def reanalyze_samples(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()
    return "views/reversinglabs_reanalyze_samples.html"


def color_code_classification(classification):
    color = ""
    classification = classification.upper()
    if classification == "MALICIOUS":
        color = "red"
    elif classification == "SUSPICIOUS":
        color = "orange"
    elif classification == "KNOWN":
        color = "green"
    elif classification == "GOODWARE":
        color = "green"

    return color


def get_status_from_ticore_classification(classification_int):
    status_mapping = {3: "malicious", 2: "suspicious", 1: "known"}

    return status_mapping.get(classification_int, "unknown")

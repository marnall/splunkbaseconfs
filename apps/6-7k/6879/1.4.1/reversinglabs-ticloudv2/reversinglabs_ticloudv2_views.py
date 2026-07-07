# File: reversinglabs_ticloudv2_views.py
#
# Copyright (c) ReversingLabs, 2024-2025
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.


def file_reputation(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            malware_presence = result.get_data()[0].get("rl", {}).get("malware_presence")
            data["malware_presence"] = malware_presence
            data["classification_color"] = color_code_classification(malware_presence.get("status").upper())

            context["data"] = data
            context["summary"] = result.get_summary()

    return "views/reversinglabs_ticloudv2_file_reputation.html"


def av_scanners(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            sample = result.get_data()[0].get("rl", {}).get("sample")
            data["sample"] = sample

            context["data"] = data

    return "views/reversinglabs_ticloudv2_av_scanners.html"


def file_analysis(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            sample = result.get_data()[0].get("rl", {}).get("sample")
            data["sample"] = sample

            context["data"] = data

    return "views/reversinglabs_ticloudv2_file_analysis.html"


def uri_statistics(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            uri_state = result.get_data()[0].get("rl", {}).get("uri_state")
            data["uri_state"] = uri_state

            uri_type = uri_state.get("uri_type")
            uri = uri_state.get(uri_type)
            data["uri"] = uri
            data["uri_type"] = uri_type

            context["data"] = data

    return "views/reversinglabs_ticloudv2_uri_statistics.html"


def url_reputation(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            report_base = result.get_data()[0].get("rl", {})
            data["report_base"] = report_base

            classification = report_base.get("classification", "UNAVAILABLE").upper()
            data["classification"] = classification
            data["classification_color"] = color_code_classification(classification)

            context["summary"] = result.get_summary()
            context["data"] = data

    return "views/reversinglabs_ticloudv2_url_reputation.html"


def url_downloaded_files(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()
            for x in context["data"]:
                x["classification_color"] = color_code_classification(x.get("classification").upper())

            context["param"] = result.get_param()
    return "views/reversinglabs_ticloudv2_url_downloaded_files.html"


def latest_url_analysis_feed(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()
            context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_url_analysis_feed.html"


def url_analysis_feed_from_date(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()

        context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_url_analysis_feed.html"


def analyze_url(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            report_base = result.get_data()[0].get("rl", {})
            data["report_base"] = report_base

            context["data"] = data

    return "views/reversinglabs_ticloudv2_analyze_url.html"


def submit_for_dynamic_analysis(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            report_base = result.get_data()[0].get("rl", {})
            data["report_base"] = report_base

            context["data"] = data

    return "views/reversinglabs_ticloudv2_submit_for_dynamic.html"


def dynamic_analysis_results(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            report_base = result.get_data()[0].get("rl", {})
            data["report_base"] = report_base
            data["classification_color"] = color_code_classification(report_base.get("report").get("classification", "NO_THREATS_FOUND"))

            context["data"] = data
            context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_dynamic_analysis_results.html"


def dynamic_url_analysis_results(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = result.get_data()[0].get("rl", {})

            # Color code for general report
            data["classification_color"] = color_code_classification(data.get("report").get("classification"))

            # Color code for each dropped file entry
            dropped_files = data.get("report").get("dropped_files")

            if dropped_files is not None:
                for df in dropped_files:
                    df["classification_color_dropped_files"] = color_code_classification(df.get("classification"))

                    # get color coding for entries in merged report
                    if df.get("analysis_ids"):
                        analysis_ids = df.get("analysis_ids")
                        for an_id in analysis_ids:
                            an_id["classification_color_dropped_files_merged"] = color_code_classification(an_id.get("classification"))

            context["data"] = data
            context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_dynamic_url_analysis_results.html"


def advanced_search(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["results_found"] = f"Results found: {len(result.get_data())!s}"
            data = result.get_data()
            for x in data:
                x["classification_color"] = color_code_classification(x.get("classification").upper())

            context["data"] = data
            context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_advanced_search.html"


def functional_similarity(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["results_found"] = f"Results found: {len(result.get_data())!s}"
            data = result.get_data()
            for x in data:
                x["classification_color"] = color_code_classification(x.get("classification").upper())

            context["data"] = data
            context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_functional_similarity.html"


def imphash_similarity(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["results_found"] = f"Results found: {len(result.get_data())!s}"
            data = result.get_data()

            context["data"] = data
            context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_imphash_similarity.html"


def uri_index(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["results_found"] = f"Results found: {len(result.get_data())!s}"
            context["data"] = result.get_data()
            context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_uri_index.html"


def network_reputation(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()
            context["param"] = result.get_param()
            context["summary"] = result.get_summary()

    return "views/reversinglabs_ticloudv2_network_reputation_view.html"


def network_reputation_user_override(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            user_override = result.get_data()[0].get("rl", {}).get("user_override")
            data["user_override"] = user_override

            context["data"] = data

    return "views/reversinglabs_ticloudv2_network_reputation_user_override_view.html"


def file_reputation_user_overrides(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            user_override = result.get_data()[0].get("rl", {}).get("user_override")
            data["user_override"] = user_override

            context["data"] = data

    return "views/reversinglabs_ticloudv2_file_reputation_user_overrides.html"


def list_active_file_overrides(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0].get("user_override").get("hash_values")
            context["results_found"] = f"Results found: {len(context['data'])!s}"
            context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_list_active_file_user_overrides.html"


def customer_dayrange_usage(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0].get("usage_reports")
            context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_customer_dayrange_usage.html"


def customer_monthrange_usage(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0].get("usage_reports")
            context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_customer_monthrange_usage.html"


def domain_report(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            report_base = result.get_data()[0]
            data["report_base"] = report_base

            reputations = result.get_data()[0].get("third_party_reputations", {}).get("sources")

            if reputations is not None:
                for x in reputations:
                    x["classification_color"] = color_code_classification(x.get("detection").upper())

            context["data"] = data
            context["param"] = result.get_param()
            context["summary"] = result.get_summary()

    return "views/reversinglabs_ticloudv2_domain_report.html"


def domain_downloaded_files(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            report_base = result.get_data()[0]
            data["report_base"] = report_base

            downloaded_files = result.get_data()[0].get("downloaded_files", {})

            if downloaded_files is not None:
                for x in downloaded_files:
                    x["classification_color"] = color_code_classification(x.get("classification").upper())

            context["data"] = data
            context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_domain_downloaded_files.html"


def ip_report(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            report_base = result.get_data()[0]
            data["report_base"] = report_base

            reputations = result.get_data()[0].get("third_party_reputations", {}).get("sources")

            if reputations is not None:
                for x in reputations:
                    x["classification_color"] = color_code_classification(x.get("detection").upper())

            context["data"] = data
            context["param"] = result.get_param()
            context["summary"] = result.get_summary()

    return "views/reversinglabs_ticloudv2_ip_report.html"


def ip_downloaded_files(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            data = {}

            report_base = result.get_data()[0]
            data["report_base"] = report_base

            downloaded_files = result.get_data()[0].get("downloaded_files", {})

            if downloaded_files is not None:
                for x in downloaded_files:
                    x["classification_color"] = color_code_classification(x.get("classification").upper())

            context["data"] = data
            context["param"] = result.get_param()

    return "views/reversinglabs_ticloudv2_ip_downloaded_files.html"


def color_code_classification(classification):
    color = ""
    classification = classification.upper()
    if classification == "MALICIOUS":
        color = "red"
    elif classification == "SUSPICIOUS":
        color = "orange"
    elif classification == "KNOWN" or classification == "CLEAN" or classification == "NO_THREATS_FOUND":
        color = "green"

    return color

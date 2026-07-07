# File: silentpush_view.py
#
# Copyright (c) 2024-2025 Splunk Inc.
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

FORWARD_REVERSE_PADNS_LOOKUPS_VIEW = "views/silentpush_forward_and_reverse_padns_lookup.html"


def get_ctx_result(result, provides):
    """Get context result based on the input parameters.

    :param result: Action result or BaseConnector object
    :param provides: Action name
    :return: dict
    """
    ctx_result = {}

    param = result.get_param()
    summary = result.get_summary()
    data = result.get_data()

    ctx_result["param"] = param
    ctx_result["action_name"] = provides
    if summary:
        ctx_result["summary"] = summary

    if data:
        ctx_result["data"] = data

    return ctx_result


def display_view(provides, all_app_runs, context):
    """Display a specific view based on the 'provides' parameter.

    It processes the action results from 'all_app_runs' and returns the corresponding view path.

    :param provides: Action name
    :param all_app_runs: List of tuples containing summary and action results
    :param context: A dictionary containing the results
    :return: str
    """
    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = get_ctx_result(result, provides)
            if not ctx_result:
                continue
            results.append(ctx_result)

    if provides == "get enrichment data":
        return "views/silentpush_get_enrichment_data_view.html"
    elif provides == "search domains":
        return "views/silentpush_search_domains.html"
    elif provides == "get domain certificates":
        return "views/silentpush_get_domain_certificates.html"
    elif provides == "list domain infratags":
        return "views/silentpush_list_domain_infratags_view.html"
    elif provides == "get job status":
        return check_job_ouptut(results)
    elif provides == "density lookup":
        return "views/silentpush_density_lookup_view.html"
    elif provides == "live url screenshot":
        return "views/silentpush_live_url_screenshot_view.html"
    elif provides == "search scan data":
        return "views/silentpush_search_scan_data.html"


def check_job_ouptut(results):
    """Check job output result for various conditions and return different views based on the conditions met.

    :param results: List of job output results
    :return: str
    """
    if not results:
        return

    if results[0].get("data", [{}])[0].get("response", {}).get("job_status"):
        return "views/silentpush_get_job_status_view.html"
    elif results[0].get("data", [{}])[0].get("response", {}).get("domain_certificates"):
        return "views/silentpush_get_domain_certificates.html"
    elif results[0].get("data", [{}])[0].get("response", {}).get("records")[0].get("host"):
        return "views/silentpush_search_domains.html"
    elif results[0].get("data", [{}])[0].get("response", {}).get("records")[0].get("query"):
        results[0]["padns"] = True
        return FORWARD_REVERSE_PADNS_LOOKUPS_VIEW
    elif results[0].get("data", [{}])[0].get("response", {}).get("records")[0].get("rrname"):
        results[0]["cof"] = True
        return FORWARD_REVERSE_PADNS_LOOKUPS_VIEW


def process_action_results(action_results, provides):
    """Process action result by checking each result.

    :param action_results: List of action results
    :param provides: Type of information provided
    :return: List of processed results
    """
    results = []
    for result in action_results:
        ctx_result = get_ctx_result(result, provides)
        if not ctx_result:
            continue

        is_ip_error, is_ip_found = process_ip_data(result)
        ctx_result["is_ip_error"] = is_ip_error
        ctx_result["is_ip_found"] = is_ip_found
        results.append(ctx_result)
    return results


def process_ip_data(result):
    """Process IP data from the given result object.

    :param result: The result object containing the data to be processed
    :return: Tuple indicating if an IP error is present and if an IP is found
    """
    data = result.get_data()
    is_ip_error = False
    is_ip_found = False
    if data:
        ip_data = data[0]["response"]["ip2asn"]
        for ip in ip_data:
            if ip.get("error"):
                is_ip_error = True
            else:
                is_ip_found = True
    return is_ip_error, is_ip_found


def display_view_list_ip_information(provides, all_app_runs, context):
    """Display a list of IP information based on the 'provides' parameter.

    It processes the action results from 'all_app_runs' and returns the corresponding view path.

    :param provides: str
    :param all_app_runs: List of tuples containing summary and action results
    :param context: dict
    :return: str
    """
    context["results"] = []
    for summary, action_results in all_app_runs:
        context["results"].extend(process_action_results(action_results, provides))

    if provides == "list ip information":
        return "views/silentpush_list_ip_information_view.html"


def process_domain_data(result):
    """Process domain data from the given result object to determine if there is any error associated with the domain information.

    :param result: The result object containing the data to be processed
    :return: Tuple indicating if a domain error is present and if a domain is found
    """
    data = result.get_data()
    is_domain_error = False
    is_domain_found = False
    if data:
        domain_data = data[0]["domain_information"]
        for domain in domain_data:
            if domain.get("error"):
                is_domain_error = True
            else:
                is_domain_found = True
    return is_domain_error, is_domain_found


def process_view_list_domain_action_results(action_results, provides):
    """Process action result to generate a list of domain information based on the 'provides' parameter.

    :param action_results: List of action results
    :param provides: Type of information provided
    :return: List of processed results
    """
    results = []
    for result in action_results:
        ctx_result = get_ctx_result(result, provides)
        if not ctx_result:
            continue

        is_domain_error, is_domain_found = process_domain_data(result)
        ctx_result["is_domain_error"] = is_domain_error
        ctx_result["is_domain_found"] = is_domain_found
        results.append(ctx_result)
    return results


def display_view_list_domain_information(provides, all_app_runs, context):
    """Display a list of domain information based on the 'provides' parameter.

    :param provides: str
    :param all_app_runs: List of tuples containing summary and action results
    :param context: dict
    :return: str
    """
    context["results"] = []
    for summary, action_results in all_app_runs:
        context["results"].extend(process_view_list_domain_action_results(action_results, provides))

    if provides == "list domain information":
        return "views/silentpush_list_domain_information.html"


def display_view_forward_and_reverse_lookup(provides, all_app_runs, context):
    """Display a specific view based on the 'provides' parameter.

    It processes the action results from 'all_app_runs' and returns the corresponding view path.

    :param provides: a string indicating the type of view to display
    :param all_app_runs: a list of tuples containing summary and action results
    :param context: a dictionary containing the results

    :returns: The path to the corresponding view based on the 'provides' parameter
    """
    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = get_ctx_result(result, provides)
            data = result.get_data()
            if data and not data[0].get("response", {}).get("job_status") and not data[0].get("response", {}).get("error"):
                data = data[0]["response"]["records"]
                ctx_result["cof"] = any(record.get("rrname") for record in data)
                ctx_result["padns"] = any(record.get("query") for record in data)
            if not ctx_result:
                continue
            results.append(ctx_result)

    if provides == "forward padns lookup" or provides == "reverse padns lookup":
        return "views/silentpush_forward_and_reverse_padns_lookup.html"

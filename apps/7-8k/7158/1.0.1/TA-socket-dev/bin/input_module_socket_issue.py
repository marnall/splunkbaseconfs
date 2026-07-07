# encoding = utf-8

import datetime
import base64
import json

from socket_classes import IssueRecord, Report
from typing import Union
import random
from tools import Tools

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # repo = definition.parameters.get('repo', None)
    # branch = definition.parameters.get('branch', None)
    start_date = definition.parameters.get('start_date', None)
    if start_date is not None:
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        except Exception as error:
            msg = f"Invalid date format {start_date} for Start Date"
            helper.log_error(msg)
            helper.log_error(error)
    pass


def do_request(
        helper,
        path: str,
        method: str = "GET",
        headers: dict = None,
        parameters: dict = None,
        cookies: dict = None,
        verify: bool = True,
        timeout: int = 10,
        use_proxy: bool = True,
        payload: dict = None,
        api_key: str = None
) -> Union[dict, None]:
    base_url = "https://api.socket.dev/v0"
    url = base_url + '/' + path
    if headers is None:
        api_key += ":"
        token = base64.b64encode(api_key.encode()).decode('ascii')
        headers = {
            'Authorization': f"Basic {token}",
            'User-Agent': 'SocketSplunkApp/1.0.0',
            "accept": "application/json"
        }
    try:
        response = helper.send_http_request(
            url,
            method,
            parameters=parameters,
            payload=payload,
            headers=headers,
            cookies=cookies,
            verify=verify,
            timeout=timeout,
            use_proxy=use_proxy
        )
    except Exception as error:
        helper.log_error(f"Unable to process request for {url}")
        helper.log_error(error)
        exit(1)
    if response.status_code == 200:
        reports = response.json()
        return reports
    elif response.status_code == 401:
        raise Exception("API Key Access Denied")
    elif response.status_code == 403 or response.status_code == 429:
        raise Exception("Insufficient Quota remaining for request")


def get_reports(helper, org: str, previous_reports: list, api_key: str) -> list:
    path = "report/list"
    reports = []
    data = do_request(helper, path, api_key=api_key)
    if data is not None:
        for item in data:
            report = Report(**item)
            report.owner = org
            if report.id not in previous_reports:
                reports.append(report)
    return reports


def create_github_urls(record: Report) -> (Union[str, None], Union[str, None]):
    pr_url = ""
    commit_urls = ""
    github_base = f"https://github.com/{record.owner}/{record.repo}"
    for pr in record.pull_requests:
        pr_url += f"{github_base}/pull/{pr}\n"
        commit_urls += f"{github_base}/pull/{pr}/commits/{record.commit}\n"
    commit_urls = commit_urls.strip()
    pr_url = pr_url.strip()
    if commit_urls == "":
        commit_urls = None
    if pr_url == "":
        pr_url = None
    return pr_url, commit_urls


def get_issues(
        helper,
        report: Report,
        pr_url: str,
        commit_url: str,
        issues: list,
        api_key: str
) -> list:
    path = f"report/view/{report.id}"
    report_data = do_request(helper, path, api_key=api_key)
    report_issues = report_data.get("issues")
    if report_issues is not None:
        for alert in report_issues:
            issues = process_issue(report, alert, issues, pr_url, commit_url)
    return issues


def get_detected_packages(locations: list):
    packages = []
    for item in locations:
        pkg_type = item.get("type")
        item_value = item.get("value")
        if item_value is not None:
            pkg_name = item_value.get("package")
            pkg_version = item_value.get("version")
            pkg_data = (pkg_type, pkg_name, pkg_version)
            if pkg_data not in packages:
                packages.append(pkg_data)
    return packages


def create_alert_id(
        package: tuple,
        record: Report,
        issue_type: str,
        issue_severity: str,
        issue_category: str,
        pr_urls: str,
        commit_urls: str
) -> (str, str, str, str):
    (pkg_type, pkg_name, pkg_version) = package
    issue_id_values = [
        record.id,
        record.owner,
        record.repo,
        record.branch,
        pkg_type,
        pkg_name,
        pkg_version,
        issue_type,
        issue_severity,
        issue_category,
        pr_urls,
        record.commit,
        commit_urls,
        record.created_at,
        str(random.randint(0, 5000))
    ]
    issue_id_str = ":".join(issue_id_values)
    issue_id = Tools.generate_uuid_from_string(issue_id_str)
    return pkg_type, pkg_name, pkg_version, issue_id


def create_record(
        issue_id: str,
        record: Report,
        pkg_type: str,
        pkg_name: str,
        pkg_version: str,
        issue_category: str,
        issue_type: str,
        issue_severity: str,
        pr_urls: str,
        commit_urls: str
) -> IssueRecord:
    record_result = IssueRecord(
        id=issue_id,
        report_id=record.id,
        owner=record.owner,
        repo=record.repo,
        branch=record.branch,
        pkg_type=pkg_type,
        pkg_name=pkg_name,
        pkg_version=pkg_version,
        issue_category=issue_category,
        issue_type=issue_type,
        issue_severity=issue_severity,
        pr_url=pr_urls,
        commit=record.commit,
        commit_url=commit_urls,
        created_at=record.created_at.strip(" (Coordinated Universal Time)")
    )
    return record_result


def process_issue(
        record: Report,
        issue: dict,
        records: list,
        pr_urls: str,
        commit_urls: str
) -> list:
    issue_type = issue.get("type")
    values = issue.get("value")
    locations = values.get("locations")
    issue_severity = values.get("severity")
    issue_category = values.get("category")
    detected_pkgs = get_detected_packages(locations)
    for package in detected_pkgs:
        pkg_type, pkg_name, pkg_version, issue_id = create_alert_id(
            package,
            record,
            issue_type,
            issue_severity,
            issue_category,
            pr_urls,
            commit_urls
        )
        record_result = create_record(
            issue_id,
            record,
            pkg_type,
            pkg_name,
            pkg_version,
            issue_category,
            issue_type,
            issue_severity,
            pr_urls,
            commit_urls
        )
        records.append(record_result)
    return records


def output_found_reports(helper, reports: list) -> None:
    for report in reports:
        helper.log_info("New Reports Found:")
        helper.log_info(f"Report ID: {report.id}")


def get_issues_for_reports(
        helper,
        api_key: str,
        reports: list,
        start_date: str = None
):
    reports = filter_reports(
        reports,
        start_date,
        helper
    )
    output_found_reports(helper, reports)
    all_issues = []
    for report in reports:
        helper.log_info(f"Processing report {report.id}")
        pr_url, commit_url = create_github_urls(record=report)
        all_issues = get_issues(helper, report, pr_url, commit_url, all_issues, api_key)
    return all_issues


def filter_reports(
        reports: list,
        start_date: str,
        helper
) -> list:
    collect_reports = []
    helper.log_info("Filtering reports")
    if start_date is not None and start_date != "":
        # helper.log_info(start_date)
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    for report in reports:
        # helper.log_info(report.created_at)
        report_date = datetime.datetime.strptime(
            report.created_at,
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        if start_date != "" and report_date > start_date:
            helper.log_info(f"New Report ID: {report.id}")
            collect_reports.append(report)
    return collect_reports


def create_report_key(reports: list) -> list:
    report_ids = []
    for report in reports:
        report_ids.append(report.id)
    return report_ids


def collect_events(helper, ew):
    socket_key = 'socket_reports'
    # App Configuration
    opt_start_date = helper.get_arg('start_date')
    # get input type
    helper.get_input_type()

    # Global Configuration
    loglevel = helper.get_log_level()
    proxy_settings = helper.get_proxy()
    global_api_key = helper.get_global_setting("api_key")
    global_org = helper.get_global_setting("org")

    helper.set_log_level(loglevel)
    previous_reports = helper.get_check_point(socket_key)
    if previous_reports is not None:
        previous_reports = json.loads(previous_reports)
        number_of_previous_reports = len(previous_reports)
        helper.log_info(f"Previous Reports: {number_of_previous_reports}")
    else:
        helper.log_info("Previous Reports: None")
        previous_reports = []
    helper.log_info("Getting reports from API")
    reports = get_reports(helper, global_org, previous_reports, global_api_key)
    number_of_reports = len(reports)
    helper.log_info(f"Report IDs found: {number_of_reports}")
    events = get_issues_for_reports(
        helper,
        global_api_key,
        reports,
        opt_start_date
    )
    # index=helper.get_output_index(),
    helper.log_info(f"index={helper.get_output_index()}")
    for event in events:
        data = str(event)
        new_event = helper.new_event(
            data,
            index=helper.get_output_index(),
            source=helper.get_input_type(),
            sourcetype=helper.get_sourcetype()
        )
        ew.write_event(new_event)

    # save checkpoint
    report_ids = create_report_key(reports)
    helper.save_check_point(socket_key, json.dumps(report_ids))
    helper.delete_check_point(socket_key)

    # To create a splunk event

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''

    '''
    # The following example writes a random number as an event for each input config. (Single Instance Mode)
    # For advanced users, if you want to create single instance mod input, please use this code template.
    # Also, you need to uncomment use_single_instance_mode() above.
    import random
    input_type = helper.get_input_type()
    for stanza_name in helper.get_input_stanza_names():
        data = str(random.randint(0,100))
        event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
        ew.write_event(event)
    '''


import time
import json


# Sends an HTTP request to the Code Dx API
def send_request(helper, url, method, api_key, verify, payload=None):
    response = helper.send_http_request(url, method, payload=payload, headers={"API-Key": api_key}, verify=verify, use_proxy=False)
    # Comment from Splunk: check the response status, if the status is not successful, raise requests.HTTPError
    response.raise_for_status()
    return response


# Writes a single event to Splunk
def write_event(helper, ew, data):
    ew.write_event(helper.new_event(data=data, index=helper.get_output_index(), source=helper.get_input_type(), sourcetype=helper.get_sourcetype()))


# Writes an event to Splunk for each retrieved finding
def write_events(helper, ew, findings):
    for finding in findings:
        if finding != "":
            # For each finding, creates a Splunk event and writes the event to Splunk
            write_event(helper, ew, finding)


# Splits an HTTP response containing CSV data into a list of separate findings
def split_findings(response):
    # Extracts the CSV report from the response body
    r_text = response.text
    # Removes the headers from the CSV report
    text = r_text.split("\n", 1)[1]
    # Splits the string containing the CSV report into individual strings,
    # each containing a separate finding
    return text.split("\n")


# Checks if the job is done yet
def wait_for_job_completion(helper, config, job_id):
    status = "None"
    # Only exits this loop once the job is done
    while status not in ["completed", "failed", "cancelled"]:
        if status != "None":
            # If the job is still in progress, waits 2 seconds, then checks again
            time.sleep(2)
        # Sends an HTTP request to the "Query Job Status" endpoint to get the status of the job with job ID "jobId"
        response = send_request(helper, f"{config.server}/api/jobs/{job_id}", "GET", config.key, config.verify)
        # Extracts the status (status) of the job from the response body
        status = get_json_field(response, "status")
    # If the job fails or is cancelled, logs an error and returns false
    # Else returns true
    return is_complete(helper, status)


# If the job fails or is cancelled, logs an error and returns false
# Else returns true
def is_complete(helper, status):
    if status == "failed":
        helper.log_error("Job failed - no report generated")
        return False
    elif status == "cancelled":
        helper.log_error("Job was cancelled - no report generated")
        return False
    else:
        return True


# Retrieves the value of a specified JSON field from an HTTP response body
def get_json_field(response, field):
    # Comment from Splunk: get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
    # Extracts the value of the specified field from the response body
    return r_json[field]


# Retrieves each finding from the generated CSV report
def get_csv_findings(helper, config, job_id):
    # Sends an HTTP request to the "Get Job Result" endpoint to get the successfully generated CSV report
    response = send_request(helper, f"{config.server}/api/jobs/{job_id}/result", "GET", config.key, config.verify)
    # Splits the HTTP response into a list of separate findings
    return split_findings(response)


# Starts a job to generate a CSV report and returns the job's ID
def generate_report(helper, config, project_specifier, pl):
    # Sends an HTTP request to the "Generate Report" endpoint of the Code Dx API to generate a CSV report
    response = send_request(helper, f"{config.server}/api/projects/{project_specifier}/report/csv", "POST", config.key, config.verify, pl)
    # Extracts the job ID (jobId) of the report generation it just requested from the response body
    return get_json_field(response, "jobId")


# Determines which columns should appear in the CSV report
def configure_columns(helper, config, project_specifier, payload):
    # Sends an HTTP request to find out which columns are available for selection, for the user-given project specifier
    response = send_request(helper, f"{config.server}/api/projects/{project_specifier}/report/types", "GET", config.key, config.verify)
    r_json = response.json()
    payload["config"]["columns"] = []
    # Specifies which columns to include in the data, if available
    # noinspection SpellCheckingInspection
    columns = [
        "projectHierarchy",
        "id",
        "creationDate",
        "updateDate",
        "severity",
        "status",
        "cwe",
        "type",
        "tool",
        "location",
        "element",
        "loc.path",
        "loc.line",
        "host",
        "resultav.CVSSV2",
        "resultav.CVSSV3",
    ]
    # Checks if each column from the HTTP response is a column that should be included in the data
    for column in r_json["csv"]["configOptions"][0]["options"]:
        if column["id"] in columns:
            # Adds each column to the request payload
            payload["config"]["columns"].append(column["id"])


# Filters out all findings that have not been modified since the last run
def filter_by_last_modified(helper, payload):
    # Adds the lastModified filter to the request payload
    payload["filter"]["lastModified"] = {}
    # Gets current formatted time (f_time)
    f_time = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    # Checks if there is a checkpoint in Splunk's data for this input
    timestamp = helper.get_check_point(helper.get_input_stanza_names())
    if timestamp is None:
        helper.log_debug(f"timestamp ({helper.get_input_stanza_names()}): None")
        # If there is no timestamp (this is the first execution for this input), does not set a minimum value
    else:
        helper.log_debug(f"timestamp ({helper.get_input_stanza_names()}): {timestamp}")
        # Otherwise sets the minimum value to the timestamp from the last execution
        payload["filter"]["lastModified"]["min"] = timestamp
    # Sets the maximum value to the current time
    payload["filter"]["lastModified"]["max"] = f_time
    return f_time


# Matches each detection method specified with its corresponding ID
def configure_detection_methods(helper, config, detection_methods, payload):
    response = send_request(helper, f"{config.server}/api/detection-methods", "GET", config.key, config.verify)
    r_json = response.json()
    methods = {}
    # Gets the corresponding ID for each detection method
    for method in r_json:
        methods[method["name"]] = method["id"]
    if len(detection_methods) != 0 and detection_methods[0] != "" and detection_methods[0] != "[]":
        # Adds the detectionMethod filter to the request payload
        payload["filter"]["detectionMethod"] = list(map(lambda x: methods[x], detection_methods))


# Creates the JSON string to be used for the request payload
def write_payload(helper, config, project_specifier, detection_methods, severity, include_resolved_findings, filter_last_modified):
    # Creates a dictionary to store a Python representation of the request payload
    payload = {"filter": {}, "config": {}}
    if len(severity) != 0 and severity[0] != "" and severity[0] != "[]":
        # Adds the severity filter to the request payload
        payload["filter"]["severity"] = severity

    # Matches each detection method specified with its corresponding ID
    configure_detection_methods(helper, config, detection_methods, payload)

    # Filters out all resolved findings if the "Include resolved findings" checkbox is unchecked
    if not include_resolved_findings:
        # Adds the status filter to the request payload
        payload["filter"]["status"] = ["new", "escalated", "unresolved", "assigned", "reopened"]

    # Filters out all findings that have not been modified since the last run
    # if the "Filter by last modified" checkbox is checked
    f_time = None
    if filter_last_modified:
        f_time = filter_by_last_modified(helper, payload)

    # Determines which columns should appear in the CSV report
    configure_columns(helper, config, project_specifier, payload)

    # Pieces together and returns the string to be used for the request payload
    return json.dumps(payload), f_time

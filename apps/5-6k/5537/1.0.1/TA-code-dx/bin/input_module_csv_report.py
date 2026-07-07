# encoding = utf-8

import re
import helper_functions


# From Splunk:
#  IMPORTANT
#  Edit only the validate_input and collect_events functions.
#  Do not edit any other part in this file.
#  This file is generated only once when creating the modular input.

# Class for storing the configuration fields
class Config:
    def __init__(self, server, key, verify):
        self.server = server
        self.key = key
        self.verify = verify


# Checks what the user inputs for the "Project Specifier" filter and makes sure it in the correct format
# (all, 12, d12, 12_10, d10_12, ...)
def validate_input(helper, definition):
    project_specifier = definition.parameters.get('project_specifier', None)
    project_specifier_invalid = \
        project_specifier is not None and \
        re.fullmatch(r'all', project_specifier) is None and \
        re.fullmatch(r'd?[1-9][0-9]*', project_specifier) is None and \
        re.fullmatch(r'd?([1-9][0-9]*_)+[1-9][0-9]*', project_specifier) is None
    if project_specifier_invalid:
        raise ValueError("Invalid project specifier")
    pass


# Handles the implementation of the actual data input
def collect_events(helper, ew):
    helper.log_info(f"{helper.get_input_stanza_names()} - start")

    # Gets the values of each user input
    global_code_dx_server = helper.get_global_setting("code_dx_server")
    global_api_key = helper.get_global_setting("api_key")
    global_ca_bundle = helper.get_global_setting("ca_bundle")

    # Sets the value for the "verify" parameter in helper.send_http_request
    if global_ca_bundle == "":
        verify = True
    elif global_ca_bundle in ["ALL", "All", "all"]:
        verify = False
    else:
        verify = global_ca_bundle

    # Creates an object to store the configuration values
    global_code_dx_config = Config(global_code_dx_server, global_api_key, verify)

    # Gets the values of the user's configuration
    opt_project_specifier = helper.get_arg('project_specifier')
    # If "Project Specifier" is left blank, makes its value "all"
    if opt_project_specifier in ["", None]:
        opt_project_specifier = "all"
    helper.log_debug(f"opt_project_specifier: {opt_project_specifier}")
    opt_detection_method = helper.get_arg('detection_method')
    opt_severity = helper.get_arg('severity')
    opt_include_resolved_findings = helper.get_arg('include_resolved_findings')
    opt_filter_by_last_modified = helper.get_arg('filter_by_last_modified')

    # Creates the JSON string to be used for the request payload
    payload, f_time = helper_functions.write_payload(
        helper,
        global_code_dx_config,
        opt_project_specifier,
        opt_detection_method,
        opt_severity,
        opt_include_resolved_findings,
        opt_filter_by_last_modified,
    )
    helper.log_debug(f"payload: {payload}")

    # Starts a job to generate a CSV report and returns the job's ID
    job_id = helper_functions.generate_report(helper, global_code_dx_config, opt_project_specifier, payload)

    # Waits until the job is done
    # If the job fails or is cancelled, logs an error and exits the function
    if not helper_functions.wait_for_job_completion(helper, global_code_dx_config, job_id):
        return

    # Retrieves each finding from the generated CSV report
    findings = helper_functions.get_csv_findings(helper, global_code_dx_config, job_id)

    # Writes the events to Splunk
    helper_functions.write_events(helper, ew, findings)

    if opt_filter_by_last_modified:
        # If the last modified filter is on, saves the formatted time when this execution started (f_time)
        # to the checkpoint for this input, for use in next execution
        # to make sure next execution does not include findings not created/modified since this execution
        helper.save_check_point(helper.get_input_stanza_names(), f_time)

    helper.log_info(f"{helper.get_input_stanza_names()} - end")

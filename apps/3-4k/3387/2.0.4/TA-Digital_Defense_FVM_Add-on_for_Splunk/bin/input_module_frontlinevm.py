
# encoding = utf-8

import csv
import json
import os
import re
import requests
import time
import datetime

from splunk.clilib import cli_common as cli

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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

def send_mail_success(completion_time, run_count):
    print("Success Detected, sending email")

    fromaddr = "Integrations.Test@digitaldefense.com"
    toaddr = "Integrations.Test@digitaldefense.com"
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "Splunk Integration Result: Success"

    body = "Integration ran successfully\n\n" + "Completed at: " + str(completion_time) + "\n\nRun Count: " + str(run_count)
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('192.168.10.225', 25)
    server.starttls()
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()

def send_mail_failure(error_message):
    print("Failure Detected, sending email")

    fromaddr = "Integrations.Test@digitaldefense.com"
    toaddr = "Integrations.Test@digitaldefense.com"
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "Splunk Integration Result: Failure"

    body = "Integration did not run successfully\n\n" + error_message
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('192.168.10.225', 25)
    server.starttls()
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()

# Helper functions for CSV reading and writing
def get_time_and_count_from_state_file(state_file):
    cfg = cli.getConfStanza('fvm_state', 'state')
    last_time_ran = float(cfg.get('last_time_ran'))
    run_count = int(cfg.get('run_count'))
    if last_time_ran == 0.0 and run_count == 0:
        raise ValueError("Last_time_ran and run_count cannot be 0. There was an error reading the file.")
    else:
        return last_time_ran, run_count


def create_state_file(state_file_path, fieldnames):
    state_file = state_file_path
    # Create variables, so we have something to return
    last_time_ran = 0.0
    run_count = 0
    with open(state_file, "w") as st:
        current_time = time.time()
        st.write('[state]\n')
        st.write('last_time_ran=%f\n' % (current_time))
        st.write('run_count={count}\n'.format(count=run_count))

    cfg = cli.getConfStanza('fvm_state', 'state')
    last_time_ran = float(cfg.get('last_time_ran'))
    run_count = int(cfg.get('run_count'))

    if last_time_ran == 0.0:
        raise ValueError("last_time_ran should not be 0.0. Something went wrong reading the file.")
    else:
        return last_time_ran, run_count


def update_state_file(state_file, fieldnames, completion_time, run_count):
    with open(state_file, "w") as st:
        st.write('[state]\n')
        st.write('last_time_ran=%f\n' % (completion_time))
        st.write('run_count={count}\n'.format(count=run_count))



def validate_input(helper, definition):
    """Ensure the API Key is a possible API Key"""
    # Retrieve the API Key from input
    fvm_api_key = definition.parameters.get('fvm_api_key', None)
    if fvm_api_key is None:
        helper.log_error("No Frontline VM API key was entered.")
        raise ValueError("No Frontline VM API key was entered.")
    try:
        # Check if the API Key is a valid token
        if not re.match('[a-zA-Z0-9]{40,42}$', fvm_api_key, flags=re.IGNORECASE):
            helper.log_error("Not a valid Frontline VM API Token.")
    except ValueError as e:
        raise ValueError("Not a valid Frontline VM API Token. Error: {}".format(e))
    
    # This example accesses the modular input variable
    # display_name = definition.parameters.get('display_name', None)
    # pull_interval = definition.parameters.get('pull_interval', None)
    # api_key = definition.parameters.get('api_key', None)
    # minimum_severity = definition.parameters.get('minimum_severity', None)
    # new_vulnerabilities_only = definition.parameters.get('new_vulnerabilities_only', None)


def collect_events(helper, ew):
    scan_batch_size = 1000
    vuln_batch_size = 5000
    # Get the current time when the script runs
    current_time = time.time() + 60

    # Fieldnames for state.conf
    fieldnames = ["last_time_ran", "run_count"]

    log_level = helper.get_log_level()
    helper.set_log_level(log_level)

    # Get data from inputs
    fvm_api_key = str(helper.get_arg('fvm_api_key'))
    interval = helper.get_arg('interval')
    min_severity = helper.get_arg('minimum_severity')
    isNewOnly = helper.get_arg('new_vulnerabilities_only')

    if interval is None:
        # Default to 24 hours if interval is not set
        interval = 86400

    if not isinstance(interval, int) or not isinstance(interval, float):
        interval = float(interval)

    # Force input related variables into dictionaries
#    if not isinstance(fvm_api_key, dict):
#        fvm_api_key = {'default': fvm_api_key}

    fvm_url = "https://vm.frontline.cloud"

    # Retrieve the state of the most recent pull
    state_file = "{splunk_home}/etc/apps/{app_name}/local/fvm_state.conf".format(
        app_name=helper.get_app_name(),
        splunk_home=os.environ['SPLUNK_HOME']
    )

    if not os.path.exists(state_file):
        last_time_ran, run_count = create_state_file(state_file, fieldnames)
    else:
        last_time_ran, run_count = get_time_and_count_from_state_file(state_file)
        
#    for key, value in fvm_api_key.iteritems():
    # Check if the current_time is greater than the last_time_ran plus the interval
    if current_time >= (last_time_ran + interval) or run_count < 1:
        datetime_scan_finished = datetime.datetime.fromtimestamp(
            last_time_ran - interval
        ).strftime("%Y-%m-%dT%H:%M:%S")

        # Input related values, sometimes these are strings, sometimes they are dictionaries.
        splunk_input_name = helper.get_input_type()
        splunk_index = helper.get_output_index()
        splunk_sourcetype = 'frontlineVM'

        # Force all input related variables into dictionaries
#        if not isinstance(fvm_api_key, dict):
#            fvm_api_key = {key: fvm_api_key}
#        if not isinstance(splunk_input_name, dict):
#            splunk_input_name = {key: splunk_input_name}
#        if not isinstance(splunk_index, dict):
#            splunk_index = {key: splunk_index}

        # HTTP related variables
        ssl_verify = True
        http_timeout = 30
        http_auth_header = {"Authorization": "Token {}".format(fvm_api_key)}

        # Variables related to processing vulnerabilities
        have_all_vulns = False
        error_count = 0

        # Putting together the vulns request
        # Only requires the token instead of the /account/<account_id>
        vuln_req = "{url}/api/scanresults/active/vulnerabilities/".format(url=fvm_url)
        vuln_req += "?_0_lte_vuln_severity_ddi={severity}".format(severity=min_severity)
        if isNewOnly is True:
            vuln_req += "&_1_gte_vuln_active_view_datetime_first_created={datetime}".format(datetime=datetime_scan_finished)
        
        vuln_req += "&count={size}".format(size=scan_batch_size)
        
        while not have_all_vulns:
            if error_count > 3:
                helper.log_error("Unable to retrieve vulns from FVM.")
                send_mail_failure("Unable to retrieve vulns from FVM.")
                raise requests.HTTPError("Unable to retrieve vulns from FVM.")
            try:
                response = helper.send_http_request(
                    vuln_req,
                    'GET',
                    headers=http_auth_header,
                    verify=ssl_verify,
                    timeout=http_timeout
                )
                response.raise_for_status()
            except Exception:
                error_count += 1
                continue
            try:
                current_data = response.json()
            except Exception:
                    helper.log_error("Unable to parse vulnerability JSON data from Frontline VM.")
                    break

            # Send data to Splunk
            for vuln in current_data['results']:
                event = helper.new_event(
                    source=splunk_input_name,
                    index=splunk_index,
                    sourcetype=splunk_sourcetype,
                    data=json.dumps(vuln)
                )
                try:
                    ew.write_event(event)
                except Exception as e:
                    helper.log_error("Error processing vulnerability: {}".format(e))
                    continue

            if current_data['next'] is not None:
                vuln_req = current_data['next']
            else:
                have_all_vulns = True
        run_count += 1
        completion_time = time.time()
        dash_req = "{url}/api/dashboard".format(url=fvm_url)
        try:
            dash_resp = helper.send_http_request(
                dash_req,
                'GET',
                headers=http_auth_header,
                verify=ssl_verify,
                timeout=http_timeout
            )   
            dash_resp.raise_for_status()
            dash_data = dash_resp.json()
            dash_data = dash_data['security_gpa']
        except Exception as e:
            helper.log_error("Unable to parse dashboard data from Frontline VM. Error: {}".format(e))
                                
        event = helper.new_event(
            source=splunk_input_name,
            index=splunk_index,
            sourcetype=splunk_sourcetype,
            data=json.dumps(dash_data)
            )   
        try:
            ew.write_event(event)
        except Exception as e:
            helper.log_error("Error processing dashboard data: {}".format(e))
        if error_count < 3:
            update_state_file(state_file, fieldnames, completion_time, run_count)
            send_mail_success(completion_time, run_count)
    else:
        helper.log_error("There has not been enough time to run the add-on (less than {} seconds).".format(
            current_time - last_time_ran
        ))
        helper.log_error("Default time between data pulls is {} seconds.".format(interval))
        helper.log_error("Current time: {}\nLast time scan was ran: {}\nTime between pulls in seconds: {}".format(
            current_time,
            last_time_ran,
            current_time - last_time_ran
        ))
        helper.log_error("Amount of times script has been run: {}".format(run_count))

        send_mail_failure("There has not been enough time to run the add-on (less than {} seconds).".format(
            current_time - last_time_ran
            ) + "\nDefault time between data pulls is {} seconds.".format(interval) +
                " \nCurrent time: {}\nLast time scan was ran: {} \nTime between pulls in seconds: {}".format(
                    current_time,
                    last_time_ran,
                    current_time - last_time_ran
                    ) + "\nAmount of times script has been run: {}".format(run_count))
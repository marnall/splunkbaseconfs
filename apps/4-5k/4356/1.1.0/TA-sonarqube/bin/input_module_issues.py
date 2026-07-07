
# encoding = utf-8

import os
import sys
import time
import datetime
import base64
import json
from datetime import datetime


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
    # account_to_use = definition.parameters.get('account_to_use', None)
    # project_name = definition.parameters.get('project_name', None)
    # get_comments = definition.parameters.get('get_comments', None)
    pass

def collect_events(helper, ew):

    import random
    import datetime
    import re
    from datetime import datetime

    """
    Logging Standards for Application:

    Error - To report failures within application
    Info - To mark start and end times of each execution
    Debug - To be used to confirm all touch points and frequency of runs

    Important inclusions:
    event_id - randomly generated number which MUST be tagged as PROCID, enabling easy trace of each run
    MsgID - Must be a hardcoded abbreviation unique to the log message itself.
            Allows for easy identification within the code as to where the message originates
    Loops - Must have an identifier in each message to establish the instance of the iteration
    Purpose - Each log must clearly communicate its purpose for existance, including appropriate data wherever relevant
    """

    # Initialize
    event_id = str(random.randint(0,1000000))
    got_all_recs = False
    datetime_format = '%Y-%m-%dT%H:%M:%S'

    # Set Auth Details
    opt_global_account = helper.get_arg('account_to_use')

    inp_username = str(opt_global_account['username'])
    inp_token = helper.get_arg('project_token')

    if inp_token == None or inp_token == "":
        auth = base64.b64encode(inp_username + ":" + str(opt_global_account['password']))
    else:
        auth = base64.b64encode(inp_token + ":")

    # Get Input Params
    inp_url = helper.get_arg('server_url')
    inp_project = str(helper.get_arg('project_name'))
    inp_comments = str(helper.get_arg('get_comments'))

    # Parse Params
    if inp_project == None or inp_project == "None" or inp_project == "":
        inp_project = 'All'

    # Http Initialize
    page_no = 1
    method = 'GET'
    api_param = 'pageSize=100&sort=UPDATE_DATE&asc=false'
    headers = {'Authorization' : '{}'.format('Basic ' + str(auth))}
    path = '/api/issues/search'
    url = inp_url + path

    if inp_comments:
        api_param = api_param + '&additionalFields=comments'

    if inp_project != 'All':
        api_param = api_param + '&componentKeys=' + inp_project

    helper.log_info('PROCID=' + event_id + ' | Start')

    helper.log_debug(
        'PROCID=' + event_id +
        ' | MsgID=INITVARS' +
        ' | Input Params - Account=' + inp_username +
        ' | URL=' + inp_url +
        ' | Project=' + inp_project +
        ' | GetComments=' + inp_comments)

    # Get Checkpoint Value
    checkpoint = inp_project + '-' + "last_runtime"
    last_runtime = helper.get_check_point(checkpoint)

    # If there's no checkpoint value, set initial value to 2000-01-01
    if last_runtime == None:
        last_runtime = "2000-01-01T00:00:00"

    helper.log_debug(
        'PROCID=' + event_id +
        ' | MsgID=CKLRT' +
        ' | CheckPoint=' + checkpoint +
        ' | Value=' + last_runtime)

    # Set Current RunTime
    cur_runtime = datetime.now().strftime(datetime_format)

    helper.log_debug(
        'PROCID=' + event_id +
        ' | MsgID=RTSET' +
        ' | StartTime=' + str(last_runtime) +
        ' | EndTime=' + str(cur_runtime))

    """
    # Ensure no records created during run are considered!
    api_param = api_param + '&createdBefore=' + str(cur_runtime)
    """

    # Loop through requests for each page
    while not got_all_recs:

        helper.log_debug(
            'PROCID=' + event_id +
            ' | MsgID=RQLPST' +
            ' | Page=' + str(page_no) +
            ' | Loop Start')

        # Finalize Request
        params = api_param + '&pageIndex=' + str(page_no)

        # API Call to SonarQube
        response = helper.send_http_request(
            url,
            method,
            parameters=params,
            headers=headers)

        # Handle Response
        r_status = response.status_code
        response.raise_for_status()

        # If not Successful, report out error and finish processing
        if r_status != 200:
            helper.log_error(
                'PROCID=' + event_id +
                ' | MsgID=ISAPIE' +
                ' | Page=' + str(page_no) +
                ' | Params={' + params + '}' +
                ' | ResponseMsg=' + response.text)
            return

        # Handle JSON
        r_json = response.json()

        # Initialize Vars Prior To Loop
        stored_keys = []
        got_all_recs = True

        # Loop through each record
        for r_loop in r_json['issues']:

            got_all_recs = False

            helper.log_debug(
                'PROCID=' + event_id +
                ' | MsgID=LPISST' +
                ' | Page=' + str(page_no) +
                ' | Key=' + str(r_loop['key']) +
                ' | Start')


            # This should only be true if records have been updated whilst this process has been running
            if r_loop['key'] in stored_keys:
                continue

            # If update < last runtime then data will have already been stored in Splunk.
            # FUTURE REQUIREMENT: Include update date in API call header to limit responses, renderng this check obsolete
            ud = r_loop['updateDate']
            update_date = re.sub("[\-\+]\d{4}",'',ud)
            if datetime.strptime(update_date,'%Y-%m-%dT%H:%M:%S') < datetime.strptime(last_runtime,datetime_format):
                helper.log_debug(
                    'PROCID=' + event_id +
                    ' | MsgID=LPISFIN' +
                    ' | Page=' + str(page_no) +
                    ' | Key=' + str(r_loop['key']) +
                    ' | Event has already been stored in Splunk')
                got_all_recs = True
                break

            # This will only be true if an update has occurred whilst the routine is running. Storing now will result in
            # a double storage as the update will be stored as part of the routines next run
            if datetime.strptime(update_date,'%Y-%m-%dT%H:%M:%S') > datetime.strptime(cur_runtime,datetime_format):
                helper.log_debug(
                    'PROCID=' + event_id +
                    ' | MsgID=LPISNEW' +
                    ' | Page=' + str(page_no) +
                    ' | Key=' + str(r_loop['key']) +
                    ' | Event Updated After Runtime. Will be stored on next run')
                continue

            # Store record key in case update occurs, knocking pages
            stored_keys.append(r_loop['key'])

            # Build Dataset for storage in Splunk
            issue = {}

            if 'organization' in r_loop:
                issue['organization'] = r_loop['organization']

            if 'project' in r_loop:
                issue['project'] = r_loop['project']

            if 'component' in r_loop:
                issue['component'] = r_loop['component']

            if 'key' in r_loop:
                issue['key'] = r_loop['key']

            if 'line' in r_loop:
                issue['line'] = r_loop['line']

            if 'type' in r_loop:
                issue['type'] = r_loop['type']

            if 'severity' in r_loop:
                issue['severity'] = r_loop['severity']

            if 'status' in r_loop:
                issue['status'] = r_loop['status']

            if 'resolution' in r_loop:
                issue['resolution'] = r_loop['resolution']

            if 'author' in r_loop:
                issue['author'] = r_loop['author']

            if 'assignee' in r_loop:
                issue['assignee'] = r_loop['assignee']

            if 'effort' in r_loop:
                issue['effort'] = r_loop['effort']

            if 'debt' in r_loop:
                issue['debt'] = r_loop['debt']

            if 'creationDate' in r_loop:
                issue['creationDate'] = r_loop['creationDate']

            if 'updateDate' in r_loop:
                issue['updateDate'] = r_loop['updateDate']

            if 'message' in r_loop:
                issue['message'] = r_loop['message']

            if 'comments' in r_loop:
                issue['comments'] = r_loop['comments']

            if 'tags' in r_loop:
                issue['tags'] = r_loop['tags']

            helper.log_debug(
                'PROCID=' + event_id +
                ' | MsgID=LPISSV' +
                ' | Page=' + str(page_no) +
                ' | Key=' + str(r_loop['key']) +
                ' | Storing Data')

            # Store data into Splunk
            event = helper.new_event(
                data=json.dumps(issue),
                index=helper.get_output_index(),
                source=helper.get_input_type(),
                sourcetype=helper.get_sourcetype())

            try:
                ew.write_event(event)
            except Exception as e:
                raise e

        # Increment page no
        page_no = page_no + 1

        # Fail Safe to prevent infinite loop
        if page_no > 100:
            got_all_recs = True

    # Store current runtime in KV Store
    helper.save_check_point(
        checkpoint,
        cur_runtime)


    helper.log_info('PROCID=' + event_id + ' | End')

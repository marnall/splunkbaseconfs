"""User Input for Add-On."""

# encoding = utf-8

import json

import datetime
from datetime import datetime, timedelta

'''

    IMPORTANT

    Edit only the validate_input and collect_events functions.

    Do not edit any other part in this file.

    This file is generated only once when creating the modular input.



# For advanced users, if you want to create single instance mod input, uncomment this method.

def use_single_instance_mode():

    return True.'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # personal_access_token = definition.parameters.get('personal_access_token', None)
    # project_id = definition.parameters.get('project_id', None)
    pass

def collect_events(helper, event_write):
    """central event collection."""

    import random
    import re

    """
    Logging Standards for Application:

    Error - To report failures within application
    Info - To mark start and end times of each execution
    Debug - To be used to confirm all touch points and frequency of runs

    Important inclusions:
    event_id - randomly generated number which MUST be tagged as PROCID,
               enabling easy trace of each run
    MsgID - Must be a hardcoded abbreviation unique to the log message itself.
            Allows for easy identification within the code as to where the message originates
    Loops - Must have an identifier in each message to establish the instance of the iteration
    Purpose - Each log must clearly communicate its purpose for existance,
              including appropriate data wherever relevant."""

    # Initialize
    event_id = str(random.randint(0, 1000000)) #nosec
    got_all_recs = False
    datetime_format = '%Y-%m-%dT%H:%M:%S'
    api_datetime_format = '%Y-%m-%d'
    base_event_loop_count = 0

    # Get Inputs
    global_base_url = helper.get_global_setting("base_url")
    opt_personal_access_token = helper.get_arg('personal_access_token')
    opt_project_id = helper.get_arg('project_id')
    opt_get_trace = helper.get_arg('get_ci_trace_log')

    # HTTP Initialize
    method = 'GET'
    api_version = 'v4'
    headers = ""
    api_param = 'private_token=' + opt_personal_access_token

    helper.log_info('PROCID=' + event_id + ' | MsgID=Start')

    if (opt_project_id is None
            or opt_project_id == "None"
            or opt_project_id == ""):

        if global_base_url is None:
            global_base_url = "https://gitlab.com"
            helper.log_warning(
                'PROCID=' + event_id +
                ' | MsgID=DEFSET ' +
                " | Msg: 'Base URL is not set... Defaulting to " +
                str(global_base_url) + "'")

        helper.log_debug(
            'PROCID=' + event_id +
            ' | MsgID=INITVARS' +
            ' | Input Params - URL=' + global_base_url)
        url = global_base_url + '/api/' + api_version + '/events'

    else:
        helper.log_debug(
            'PROCID=' + event_id +
            ' | MsgID=INITVARS' +
            ' | Input Params - URL=' + global_base_url +
            ' | Project=' + opt_project_id)

        url = (global_base_url +
               '/api/' + api_version +
               '/projects/' + opt_project_id +
               '/events')

    # Get Checkpoint Value
    if opt_project_id is None or opt_project_id == "None" or opt_project_id == "":
        checkpoint = "GitLab" + '-' + opt_personal_access_token + '-' + "last_runtime"
        log_checkpoint = 'GitLab-PERSONALTOKEN-last_runtime'
    else:
        checkpoint = "GitLab" + '-' + opt_project_id + '-' + "last_runtime"
        log_checkpoint = "GitLab" + '-' + opt_project_id + '-' + "last_runtime"

    call_last_runtime = helper.get_check_point(checkpoint)

    # If there's no checkpoint value, set initial value to 2000-01-01
    if call_last_runtime is None:
        last_runtime = "2000-01-01"
        last_runtime_prevday = last_runtime
        dtm_last_runtime = "2000-01-01T00:00:00"
        call_last_runtime = "NEW RUN"
    else:
        last_runtime = datetime.strftime(
            datetime.strptime(call_last_runtime, datetime_format), api_datetime_format)
        last_runtime_prevday = datetime.strftime(
            datetime.strptime(call_last_runtime, datetime_format)
            - timedelta(days=1), api_datetime_format)
        dtm_last_runtime = call_last_runtime

    call_api_param = api_param + "&" + "after=" + str(last_runtime_prevday)

    helper.log_debug(
        'PROCID=' + event_id +
        ' | MsgID=CKLRT' +
        ' | CheckPoint=' + log_checkpoint +
        ' | API Date Value=' + last_runtime +
        ' | KV Datetime Value=' + call_last_runtime)

    # Set Current RunTime
    cur_runtime = datetime.utcnow().strftime(datetime_format)

    helper.log_debug(
        'PROCID=' + event_id +
        ' | MsgID=RTSET' +
        ' | StartTime=' + str(last_runtime) +
        ' | EndTime=' + str(cur_runtime))

    # Loop through requests for each page
    while not got_all_recs:

        base_event_loop_count = base_event_loop_count + 1

        helper.log_debug(
            'PROCID=' + event_id +
            ' | MsgID=EVLPST' +
            ' | Loop Start' +
            ' | LoopCount=' + str(base_event_loop_count))

        # API Call to GitLab
        response = helper.send_http_request(
            url,
            method,
            parameters=call_api_param,
            headers=headers)

        # Handle Response
        r_status = response.status_code
        response.raise_for_status()

        # If not Successful, report out error and finish processing
        if r_status != 200:
            helper.log_error(
                'PROCID=' + event_id +
                ' | MsgID=EVAPIE' +
                ' | Params={' + "TOKEN&" + "after=" + str(last_runtime) + '}' +
                ' | ResponseMsg=' + response.text)
            return

        # Handle JSON
        r_json = response.json()

        # Initialize Vars Prior To Loop
        got_all_recs = True
        projects = []
        users = []
        event_loop_count = 0

        # Loop through each event record
        for r_loop in r_json:
            got_all_recs = True
            event_loop_count = event_loop_count + 1

            helper.log_debug(
                'PROCID=' + event_id +
                ' | MsgID=EVCSST' +
                ' | Key=' + str(r_loop['project_id']) +
                ' | LoopCount=' + str(event_loop_count) +
                ' | EventDateTime=' + str(r_loop['created_at']) +
                ' | Start')

            if (datetime.strptime(r_loop['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    < datetime.strptime(dtm_last_runtime, datetime_format)):
                break

            # Build JSON for storage in SPlunk
            json_event = {}
            json_event['project_id'] = field_assign(
                r_loop, "project_id")
            json_event['action_name'] = field_assign(
                r_loop, "action_name")
            json_event['target_id'] = field_assign(
                r_loop, "target_id")
            json_event['target_iid'] = field_assign(
                r_loop, "target_iid")
            json_event['target_type'] = field_assign(
                r_loop, "target_type")
            json_event['author_id'] = field_assign(
                r_loop, "author_id")
            json_event['target_title'] = field_assign(
                r_loop, "target_title")
            json_event['created_at'] = field_assign(
                r_loop, "created_at")

            if 'author' in r_loop and r_loop['author'] != None:
                json_event['author_name'] = field_assign(r_loop['author'], "name")
                json_event['author_username'] = field_assign(
                    r_loop['author'], "username")

            if 'push_data' in r_loop and r_loop['push_data'] != None:
                json_event['pd_commit_count'] = field_assign(
                    r_loop['push_data'], "commit_count")
                json_event['pd_action'] = field_assign(
                    r_loop['push_data'], "action")
                json_event['pd_ref_type'] = field_assign(
                    r_loop['push_data'], "ref_type")
                json_event['pd_commit_from'] = field_assign(
                    r_loop['push_data'], "commit_from")
                json_event['pd_commit_to'] = field_assign(
                    r_loop['push_data'], "commit_to")
                json_event['pd_ref'] = field_assign(
                    r_loop['push_data'], "ref")
                json_event['pd_commit_title'] = field_assign(
                    r_loop['push_data'], "commit_title")

            if 'note' in r_loop and r_loop['note'] != None:
                json_event['note_body'] = field_assign(
                    r_loop['note'], "body")
                json_event['note_attachment'] = field_assign(
                    r_loop['note'], "attachment")
                json_event['note_attachment'] = field_assign(
                    r_loop['note'], "body", value="true")

                if 'author' in r_loop['note'] and r_loop['author'] != None:
                    json_event['note_author_name'] = field_assign(
                        r_loop['note']['author'], "name")
                    json_event['note_author_username'] = field_assign(
                        r_loop['note']['author'], "username")
                    json_event['note_target_id'] = field_assign(
                        r_loop['note']['author'], "noteable_id")
                    json_event['note_target_type'] = field_assign(
                        r_loop['note']['author'], "noteable_type")

            # Store data into and r_loop['created_at'] != None Splunk
            event = helper.new_event(
                data=json.dumps(json_event),
                index=helper.get_output_index(),
                source=helper.get_input_type(),
                sourcetype=helper.get_sourcetype())

            try:
                event_write.write_event(event)
            except Exception as raise_exception:
                raise raise_exception

            # Get Project Info
            if projects is None or not json_event['project_id'] in projects:

                helper.log_debug(
                    'PROCID=' + event_id +
                    ' | MsgID=PRJAPIS' +
                    ' | Key=' + str(json_event['project_id']) +
                    ' | LoopCount=' + str(event_loop_count) +
                    ' | Getting Project Info')

                # Store Project ID in array to prevent further retrieval
                projects.append(json_event['project_id'])

                # Get Project
                url = (global_base_url +
                       '/api/' + api_version +
                       '/projects/' + str(json_event['project_id']))

                # API Call to GitLab
                response = helper.send_http_request(
                    url,
                    method,
                    parameters=api_param,
                    headers=headers)

                # Handle Response
                r_status = response.status_code
                response.raise_for_status()

                # If not Successful, report out error and finish processing
                if r_status != 200:
                    helper.log_error(
                        'PROCID=' + event_id +
                        ' | MsgID=PRJAPIE' +
                        ' | Params=TOKEN' +
                        ' | ResponseMsg=' + response.text)

                    return

                # Handle JSON
                project_json = response.json()

                # Build JSON
                json_project = {}
                json_project['id'] = field_assign(
                    project_json, "id")
                json_project['description'] = field_assign(
                    project_json, "description")
                json_project['default_branch'] = field_assign(
                    project_json, "default_branch")
                json_project['visibility'] = field_assign(
                    project_json, "visibility")
                json_project['web_url'] = field_assign(
                    project_json, "web_url")
                json_project['readme_url'] = field_assign(
                    project_json, "readme_url")
                json_project['name'] = field_assign(
                    project_json, "name")
                json_project['name_with_namespace'] = field_assign(
                    project_json, "name_with_namespace")
                json_project['open_issues_count'] = field_assign(
                    project_json, "open_issues_count")
                json_project['created_at'] = field_assign(
                    project_json, "created_at")
                json_project['last_activity_at'] = field_assign(
                    project_json, "last_activity_at")
                json_project['archived'] = field_assign(
                    project_json, "archived")
                json_project['forks_count'] = field_assign(
                    project_json, "forks_count")
                json_project['star_count'] = field_assign(
                    project_json, "star_count")
                json_project['approvals_before_merge'] = field_assign(
                    project_json, "approvals_before_merge")
                json_project['merge_method'] = field_assign(
                    project_json, "merge_method")
                json_project['repository_storage'] = field_assign(
                    project_json, "repository_storage")
                json_project['tag_list'] = field_assign(
                    project_json, "tag_list")

                if "owner" in project_json and project_json['owner'] != None:
                    json_project['owner_name'] = field_assign(
                        project_json['owner'], "name")
                    json_project['owner_username'] = field_assign(
                        project_json['owner'], "username")

                if "namespace" in project_json and project_json['namespace'] != None:
                    json_project['namespace_name'] = field_assign(
                        project_json['namespace'], "name")
                    json_project['namespace_id'] = field_assign(
                        project_json['namespace'], "id")
                    json_project['namespace_kind'] = field_assign(
                        project_json['namespace'], "kind")

                # Store data into Splunk
                event = helper.new_event(
                    data=json.dumps(json_project),
                    index=helper.get_output_index(),
                    source=helper.get_input_type(),
                    sourcetype="GitLab:Project")

                try:
                    event_write.write_event(event)
                except Exception as raise_exception:
                    raise raise_exception

                # GET COMMITS FOR PROJECT

                # Build API Request
                url = (global_base_url +
                       '/api/' + api_version +
                       '/projects/' + str(json_event['project_id']) +
                       "/repository/commits")

                call_api_param = (
                    api_param +
                    "&since=" + str(dtm_last_runtime) +
                    "&until=" + str(cur_runtime))

                # API Call to GitLab
                response = helper.send_http_request(
                    url,
                    method,
                    parameters=call_api_param,
                    headers=headers)

                # Handle Response
                r_status = response.status_code
                response.raise_for_status()

                # If not Successful, report out error and finish processing
                if r_status != 200:
                    helper.log_error(
                        'PROCID=' + event_id +
                        ' | MsgID=COMAPIE' +
                        ' | Params={' +
                        "TOKEN&" +
                        "since=" + str(dtm_last_runtime) +
                        "&until=" + str(cur_runtime) +
                        "&with_stats=true" +
                        '}' +
                        ' | ResponseMsg=' + response.text)
                    return

                # Handle JSON Response
                commit_json = response.json()
                commit_loop_count = 0

                # Build JSON
                for commit_loop in commit_json:

                    commit_loop_count = commit_loop_count + 1

                    helper.log_debug(
                        'PROCID=' + event_id +
                        ' | MsgID=COMBUIS' +
                        ' | Key=' + str(commit_loop['id']) +
                        ' | LoopCount=' + str(commit_loop_count) +
                        ' | Building Commit JSON Start')

                    json_commit = {}
                    json_commit['id'] = field_assign(
                        commit_loop, "id")
                    json_commit['short_id'] = field_assign(
                        commit_loop, "short_id")
                    json_commit['title'] = field_assign(
                        commit_loop, "title")
                    json_commit['created_at'] = field_assign(
                        commit_loop, "created_at")
                    json_commit['parent_ids'] = field_assign(
                        commit_loop, "parent_ids")
                    json_commit['message'] = field_assign(
                        commit_loop, "message")
                    json_commit['author_name'] = field_assign(
                        commit_loop, "author_name")
                    json_commit['author_email'] = field_assign(
                        commit_loop, "author_email")
                    json_commit['authored_date'] = field_assign(
                        commit_loop, "authored_date")
                    json_commit['committer_name'] = field_assign(
                        commit_loop, "committer_name")
                    json_commit['committer_email'] = field_assign(
                        commit_loop, "committer_email")
                    json_commit['committed_date'] = field_assign(
                        commit_loop, "committed_date")

                    if "stats" in commit_loop and commit_loop['stats'] != None:
                        json_commit['stats_additions'] = field_assign(
                            commit_loop['stats'], "additions")
                        json_commit['stats_deletions'] = field_assign(
                            commit_loop['stats'], "deletions")
                        json_commit['stats_total'] = field_assign(
                            commit_loop['stats'], "total")

                    # Store data into Splunk
                    event = helper.new_event(
                        data=json.dumps(json_commit),
                        index=helper.get_output_index(),
                        source=helper.get_input_type(),
                        sourcetype="GitLab:Commit")

                    try:
                        event_write.write_event(event)
                    except Exception as raise_exception:
                        raise raise_exception

            if "target_type" in json_event:
                helper.log_debug(
                    'PROCID=' + event_id +
                    ' | MsgID=EVCTTAN' +
                    ' | Key=' + str(r_loop['project_id']) +
                    ' | LoopCount=' + str(event_loop_count) +
                    ' | TargetType=' + str(json_event['target_type']))

            # If target is project or note then no further processing required
            if ("target_type" in json_event and
                    (json_event['target_type'].lower() == "project"
                     or json_event['target_type'].lower() == "note")
                    or "target_type" not in json_event):
                helper.log_debug(
                    'PROCID=' + event_id +
                    ' | MsgID=EVCFIN' +
                    ' | Key=' + str(r_loop['project_id']) +
                    ' | LoopCount=' + str(event_loop_count) +
                    ' | Target Type is project, note, or null')
                continue

            # Build ISSUE Data
            if json_event['target_type'].lower() == "issue":

                # GitLab requires issue iid.
                # If this doesnt exist, nothing further can be done
                if "target_iid" not in json_event:
                    helper.log_debug(
                        'PROCID=' + event_id +
                        ' | MsgID=ISFIN' +
                        ' | Key=' + str(r_loop['project_id']) +
                        ' | LoopCount=' + str(event_loop_count) +
                        ' | Target iid is not populated')
                    continue

                # Build API Request
                url = (global_base_url +
                       '/api/' + api_version +
                       '/projects/' + str(json_event['project_id']) +
                       "/issues/" + str(json_event['target_iid']))

                # API Call to GitLab
                response = helper.send_http_request(
                    url,
                    method,
                    parameters=api_param,
                    headers=headers)

                # Handle Response
                r_status = response.status_code
                response.raise_for_status()

                # If not Successful, report out error and finish processing
                if r_status != 200:
                    helper.log_error(
                        'PROCID=' + event_id +
                        ' | MsgID=ISAPIE' +
                        ' | Params={TOKENONLY}' +
                        ' | LoopCount=' + str(event_loop_count) +
                        ' | ResponseMsg=' + response.text)
                    return

                # Handle JSON
                issue_json = response.json()

                # Build JSON for Splunk
                json_issue = {}
                json_issue['project_id'] = field_assign(
                    issue_json, "project_id")
                json_issue['description'] = field_assign(
                    issue_json, "description")
                json_issue['state'] = field_assign(
                    issue_json, "state")
                json_issue['id'] = field_assign(
                    issue_json, "id")
                json_issue['iid'] = field_assign(
                    issue_json, "iid")
                json_issue['title'] = field_assign(
                    issue_json, "title")
                json_issue['updated_at'] = field_assign(
                    issue_json, "updated_at")
                json_issue['created_at'] = field_assign(
                    issue_json, "created_at")
                json_issue['closed_at'] = field_assign(
                    issue_json, "closed_at")
                json_issue['upvotes'] = field_assign(
                    issue_json, "upvotes")
                json_issue['downvotes'] = field_assign(
                    issue_json, "downvotes")
                json_issue['labels'] = field_assign(
                    issue_json, "labels")
                json_issue['due_date'] = field_assign(
                    issue_json, "due_date")
                json_issue['confidential'] = field_assign(
                    issue_json, "confidential")

                if "time_stats" in issue_json and issue_json['time_stats'] != None:
                    json_issue['ts_time_estimate'] = field_assign(
                        issue_json['time_stats'], "time_estimate")
                    json_issue['ts_total_time_spent'] = field_assign(
                        issue_json['time_stats'], "total_time_spent")
                    json_issue['ts_human_time_estimate'] = field_assign(
                        issue_json['time_stats'], "human_time_estimate")
                    json_issue['ts_human_total_time_spent'] = field_assign(
                        issue_json['time_stats'], "human_total_time_spent")

                if "closed_by" in issue_json and issue_json['closed_by'] != None:
                    json_issue['closed_by_state'] = field_assign(
                        issue_json['closed_by'], "state")
                    json_issue['closed_by_username'] = field_assign(
                        issue_json['closed_by'], "username")
                    json_issue['closed_by_name'] = field_assign(
                        issue_json['closed_by'], "name")

                if "assignee" in issue_json and issue_json['assignee'] != None:
                    json_issue['assignee_state'] = field_assign(
                        issue_json['assignee'], "state")
                    json_issue['assignee_username'] = field_assign(
                        issue_json['assignee'], "username")
                    json_issue['assignee_name'] = field_assign(
                        issue_json['assignee'], "name")

                if "author" in issue_json and issue_json['author'] != None:
                    json_issue['auth_state'] = field_assign(
                        issue_json['author'], "state")
                    json_issue['auth_username'] = field_assign(
                        issue_json['author'], "username")
                    json_issue['auth_name'] = field_assign(
                        issue_json['author'], "name")

                if "milestone" in issue_json and issue_json['milestone'] != None:
                    json_issue['milestone_state'] = field_assign(
                        issue_json['milestone'], "state")
                    json_issue['milestone_title'] = field_assign(
                        issue_json['milestone'], "title")
                    json_issue['milestone_description'] = field_assign(
                        issue_json['milestone'], "description")
                    json_issue['milestone_due_date'] = field_assign(
                        issue_json['milestone'], "due_date")
                    json_issue['milestone_id'] = field_assign(
                        issue_json['milestone'], "id")
                    json_issue['milestone_iid'] = field_assign(
                        issue_json['milestone'], "iid")
                    json_issue['milestone_created_at'] = field_assign(
                        issue_json['milestone'], "created_at")
                    json_issue['milestone_updated_at'] = field_assign(
                        issue_json['milestone'], "updated_at")

                # Store data into Splunk
                event = helper.new_event(
                    data=json.dumps(json_issue),
                    index=helper.get_output_index(),
                    source=helper.get_input_type(),
                    sourcetype="GitLab:Issue")

                try:
                    event_write.write_event(event)
                except Exception as raise_exception:
                    raise raise_exception

                continue

            # Build MILESTONE Data
            if json_event['target_type'].lower() == "milestone":

                # The GitLab API Requires the milestone ID.
                # If this doesnt exist, nothing further can be done for this record
                if "target_id" not in json_event:
                    helper.log_debug(
                        'PROCID=' + event_id +
                        ' | MsgID=MSFIN' +
                        ' | Key=' + str(r_loop['project_id']) +
                        ' | LoopCount=' + str(event_loop_count) +
                        ' | Target id is not populated')
                    continue

                # Build API Request
                url = (global_base_url +
                       '/api/' + api_version +
                       '/projects/' + str(json_event['project_id']) +
                       "/milestones/" + str(json_event['target_id']))

                # API Call to GitLab
                response = helper.send_http_request(
                    url,
                    method,
                    parameters=api_param,
                    headers=headers)

                # Handle Response
                r_status = response.status_code
                response.raise_for_status()

                # If not Successful, report out error and finish processing
                if r_status != 200:
                    helper.log_error(
                        'PROCID=' + event_id +
                        ' | MsgID=MSAPIE' +
                        ' | Params={TOKEN}' +
                        ' | ResponseMsg=' + response.text)
                    return

                # Handle JSON
                milestone_json = response.json()

                # Build JSON
                json_milestone = {}
                json_milestone['state'] = field_assign(
                    milestone_json, "state")
                json_milestone['title'] = field_assign(
                    milestone_json, "title")
                json_milestone['description'] = field_assign(
                    milestone_json, "description")
                json_milestone['due_date'] = field_assign(
                    milestone_json, "due_date")
                json_milestone['id'] = field_assign(
                    milestone_json, "id")
                json_milestone['iid'] = field_assign(
                    milestone_json, "iid")
                json_milestone['created_at'] = field_assign(
                    milestone_json, "created_at")
                json_milestone['updated_at'] = field_assign(
                    milestone_json, "updated_at")

                # Store data into Splunk
                event = helper.new_event(
                    data=json.dumps(json_milestone),
                    index=helper.get_output_index(),
                    source=helper.get_input_type(),
                    sourcetype="GitLab:Milestone")

                try:
                    event_write.write_event(event)
                except Exception as raise_exception:
                    raise raise_exception

                continue

            # Build MERGE_REQUEST Data
            if json_event['target_type'].lower() == "mergerequest":

                # The GitLab API requires the merge request iid.
                # If this doesnt exist, nothing further can be done.
                if "target_iid" not in json_event:
                    helper.log_debug(
                        'PROCID=' + event_id +
                        ' | MsgID=MSFIN' +
                        ' | Key=' + str(r_loop['project_id']) +
                        ' | LoopCount=' + str(event_loop_count) +
                        ' | Target iid is not populated')
                    continue

                # Build API Request
                url = (global_base_url +
                       '/api/' + api_version +
                       '/projects/' + str(json_event['project_id']) +
                       "/merge_requests/" + str(json_event['target_iid']))

                # API Call to GitLab
                response = helper.send_http_request(
                    url,
                    method,
                    parameters=api_param,
                    headers=headers)

                # Handle Response
                r_status = response.status_code
                response.raise_for_status()

                # If not Successful, report out error and finish processing
                if r_status != 200:
                    helper.log_error(
                        'PROCID=' + event_id +
                        ' | MsgID=MRAPIE' +
                        ' | Params={TOKEN}' +
                        ' | ResponseMsg=' + response.text)
                    return

                # Handle JSON
                merge_request_json = response.json()

                # Response is not in an array so no loop is required
                # Build JSON
                json_merge_request = {}
                json_merge_request['id'] = field_assign(
                    merge_request_json, "id")
                json_merge_request['iid'] = field_assign(
                    merge_request_json, "iid")
                json_merge_request['project_id'] = field_assign(
                    merge_request_json, "project_id")
                json_merge_request['title'] = field_assign(
                    merge_request_json, "title")
                json_merge_request['description'] = field_assign(
                    merge_request_json, "description")
                json_merge_request['auth_state'] = field_assign(
                    merge_request_json, "state")
                json_merge_request['created_at'] = field_assign(
                    merge_request_json, "created_at")
                json_merge_request['updated_at'] = field_assign(
                    merge_request_json, "updated_at")
                json_merge_request['target_branch'] = field_assign(
                    merge_request_json, "target_branch")
                json_merge_request['source_branch'] = field_assign(
                    merge_request_json, "source_branch")
                json_merge_request['upvotes'] = field_assign(
                    merge_request_json, "upvotes")
                json_merge_request['downvotes'] = field_assign(
                    merge_request_json, "downvotes")
                json_merge_request['source_project_id'] = field_assign(
                    merge_request_json, "source_project_id")
                json_merge_request['target_project_id'] = field_assign(
                    merge_request_json, "target_project_id")
                json_merge_request['labels'] = field_assign(
                    merge_request_json, "labels")
                json_merge_request['work_in_progress'] = field_assign(
                    merge_request_json, "work_in_progress")
                json_merge_request['merge_when_pipeline_succeeds'] = field_assign(
                    merge_request_json, "merge_when_pipeline_succeeds")
                json_merge_request['merge_status'] = field_assign(
                    merge_request_json, "merge_status")
                json_merge_request['merge_error'] = field_assign(
                    merge_request_json, "merge_error")
                json_merge_request['user_notes_count'] = field_assign(
                    merge_request_json, "user_notes_count")
                json_merge_request['should_remove_source_branch'] = field_assign(
                    merge_request_json, "should_remove_source_branch")
                json_merge_request['force_remove_source_branch'] = field_assign(
                    merge_request_json, "force_remove_source_branch")
                json_merge_request['allow_maintainer_to_push'] = field_assign(
                    merge_request_json, "allow_maintainer_to_push")
                json_merge_request['web_url'] = field_assign(
                    merge_request_json, "web_url")
                json_merge_request['changes_count'] = field_assign(
                    merge_request_json, "changes_count")
                json_merge_request['allow_maintainer_to_push'] = field_assign(
                    merge_request_json, "allow_maintainer_to_push")
                json_merge_request['web_url'] = field_assign(
                    merge_request_json, "web_url")
                json_merge_request['merged_at'] = field_assign(
                    merge_request_json, "merged_at")
                json_merge_request['closed_by'] = field_assign(
                    merge_request_json, "closed_by")
                json_merge_request['closed_at'] = field_assign(
                    merge_request_json, "closed_at")
                json_merge_request['latest_build_started_at'] = field_assign(
                    merge_request_json, "latest_build_started_at")
                json_merge_request['latest_build_finished_at'] = field_assign(
                    merge_request_json, "latest_build_finished_at")
                json_merge_request['first_deployed_to_production_at'] = field_assign(
                    merge_request_json, "first_deployed_to_production_at")
                json_merge_request['diverged_commits_count'] = field_assign(
                    merge_request_json, "diverged_commits_count")
                json_merge_request['approvals_before_merge'] = field_assign(
                    merge_request_json, "approvals_before_merge")

                if "author" in merge_request_json and merge_request_json['author'] != None:
                    json_merge_request['auth_state'] = field_assign(
                        merge_request_json['author'], "state")
                    json_merge_request['auth_username'] = field_assign(
                        merge_request_json['author'], "username")
                    json_merge_request['auth_name'] = field_assign(
                        merge_request_json['author'], "name")

                if "assignee" in merge_request_json and merge_request_json['assignee'] != None:
                    json_merge_request['as_state'] = field_assign(
                        merge_request_json['assignee'], "state")
                    json_merge_request['as_username'] = field_assign(
                        merge_request_json['assignee'], "username")
                    json_merge_request['as_name'] = field_assign(
                        merge_request_json['assignee'], "name")

                if "merged_by" in merge_request_json and merge_request_json['merged_by'] != None:
                    json_merge_request['merge_state'] = field_assign(
                        merge_request_json['merged_by'], "state")
                    json_merge_request['merge_username'] = field_assign(
                        merge_request_json['merged_by'], "username")
                    json_merge_request['merge_name'] = field_assign(
                        merge_request_json['merged_by'], "name")

                if "milestone" in merge_request_json and merge_request_json['milestone'] != None:
                    json_merge_request['milestone_state'] = field_assign(
                        merge_request_json['milestone'], "state")
                    json_merge_request['milestone_title'] = field_assign(
                        merge_request_json['milestone'], "title")
                    json_merge_request['milestone_description'] = field_assign(
                        merge_request_json['milestone'], "description")
                    json_merge_request['milestone_due_date'] = field_assign(
                        merge_request_json['milestone'], "due_date")
                    json_merge_request['milestone_id'] = field_assign(
                        merge_request_json['milestone'], "id")
                    json_merge_request['milestone_iid'] = field_assign(
                        merge_request_json['milestone'], "iid")
                    json_merge_request['milestone_created_at'] = field_assign(
                        merge_request_json['milestone'], "created_at")
                    json_merge_request['milestone_updated_at'] = field_assign(
                        merge_request_json['milestone'], "updated_at")

                if "time_stats" in merge_request_json and merge_request_json['time_stats'] != None:
                    json_merge_request['ts_time_estimate'] = field_assign(
                        merge_request_json['time_stats'], "time_estimate")
                    json_merge_request['ts_total_time_spent'] = field_assign(
                        merge_request_json['time_stats'], "total_time_spent")
                    json_merge_request['ts_human_time_estimate'] = field_assign(
                        merge_request_json['time_stats'], "human_time_estimate")
                    json_merge_request['ts_human_total_time_spent'] = field_assign(
                        merge_request_json['time_stats'], "human_total_time_spent")

                # Store data into Splunk
                event = helper.new_event(
                    data=json.dumps(json_merge_request),
                    index=helper.get_output_index(),
                    source=helper.get_input_type(),
                    sourcetype="GitLab:MergeRequest")

                try:
                    event_write.write_event(event)
                except Exception as raise_exception:
                    raise raise_exception

                continue

            # Build SNIPPET Data
            if json_event['target_type'].lower() == "snippet":

                # The GitLab API requires the snippet ID.
                # If this doesnt exist, nothing further can be done with this record
                if "target_id" not in json_event:
                    helper.log_debug(
                        'PROCID=' + event_id +
                        ' | MsgID=SNFIN' +
                        ' | Key=' + str(r_loop['project_id']) +
                        ' | LoopCount=' + str(event_loop_count) +
                        ' | Target id is not populated')
                    continue

                # Build API Request
                url = (global_base_url +
                       '/api/' + api_version +
                       '/projects/' + str(json_event['project_id']) +
                       "/snippets/" + str(json_event['target_id']))

                # API Call to GitLab
                response = helper.send_http_request(
                    url,
                    method,
                    parameters=api_param,
                    headers=headers)

                # Handle Response
                r_status = response.status_code
                response.raise_for_status()

                # If not Successful, report out error and finish processing
                if r_status != 200:
                    helper.log_error(
                        'PROCID=' + event_id +
                        ' | MsgID=SNAPIE' +
                        ' | Params={TOKEN}' +
                        ' | ResponseMsg=' + response.text)
                    return

                # Handle JSON
                snippet_json = response.json()

                # Build JSON
                json_snippet = {}
                json_snippet['id'] = field_assign(snippet_json, "id")
                json_snippet['title'] = field_assign(snippet_json, "title")
                json_snippet['description'] = field_assign(snippet_json, "description")
                json_snippet['updated_at'] = field_assign(snippet_json, "updated_at")
                json_snippet['created_at'] = field_assign(snippet_json, "created_at")


                if "author" in snippet_json and snippet_json['author'] != None:
                    json_snippet['auth_state'] = field_assign(snippet_json['author'], "state")
                    json_snippet['auth_username'] = field_assign(snippet_json['author'], "username")
                    json_snippet['auth_name'] = field_assign(snippet_json['author'], "name")

                # Store data into Splunk
                event = helper.new_event(
                    data=json.dumps(json_snippet),
                    index=helper.get_output_index(),
                    source=helper.get_input_type(),
                    sourcetype="GitLab:Snippet")

                try:
                    event_write.write_event(event)
                except Exception as raise_exception:
                    raise raise_exception

                continue

            # Build User Data -
            # Checks are in place to prevent double entry of users into Splunk
            if (json_event['target_type'].lower() == "user"
                    and "target_id" in json_event
                    and (users is None
                         or json_event['target_id'] not in users)):

                helper.log_debug(
                    'PROCID=' + event_id +
                    ' | MsgID=USAPIS' +
                    ' | Key=' + str(json_event['target_id']) +
                    ' | LoopCount=' + str(event_loop_count) +
                    ' | Getting Project Info')

                # Store User Id to try and stop user from being stored twice in a run
                users.append(json_event['target_id'])

                # Build API Request
                url = (global_base_url +
                       '/api/' + api_version +
                       "/users/" + str(json_event['target_id']))

                # API Call to GitLab
                response = helper.send_http_request(
                    url,
                    method,
                    parameters=api_param,
                    headers=headers)

                # Handle Response
                r_status = response.status_code
                response.raise_for_status()

                # If not Successful, report out error and finish processing
                if r_status != 200:
                    helper.log_error(
                        'PROCID=' + event_id +
                        ' | MsgID=USAPIE' +
                        ' | Params={TOKEN}' +
                        ' | ResponseMsg=' + response.text)
                    return

                user_json = response.json()

                # Handle JSON
                json_user = {}
                json_user['username'] = field_assign(user_json, "username")
                json_user['name'] = field_assign(user_json, "name")
                json_user['state'] = field_assign(user_json, "state")
                json_user['last_sign_in_at'] = field_assign(user_json, "last_sign_in_at")
                json_user['last_activity_on'] = field_assign(user_json, "last_activity_on")

                # Store data into Splunk
                event = helper.new_event(
                    data=json.dumps(json_user),
                    index=helper.get_output_index(),
                    source=helper.get_input_type(),
                    sourcetype="GitLab:User")

                try:
                    event_write.write_event(event)
                except Exception as raise_exception:
                    raise raise_exception

                continue

    if opt_project_id != None and opt_project_id != "":
        url = (global_base_url +
               '/api/' + api_version +
               '/projects/' + opt_project_id +
               '/jobs')

        got_all_recs = False

        while not got_all_recs:
            base_event_loop_count = base_event_loop_count + 1

            helper.log_debug(
                'PROCID=' + event_id +
                ' | MsgID=JOBLPST' +
                ' | Loop Start' +
                ' | LoopCount=' + str(base_event_loop_count))

            # API Call to GitLab
            response = helper.send_http_request(
                url,
                method,
                parameters=call_api_param,
                headers=headers)

            # Handle Response
            r_status = response.status_code
            response.raise_for_status()

            # If not Successful, report out error and finish processing
            if r_status != 200:
                helper.log_error(
                    'PROCID=' + event_id +
                    ' | MsgID=JOBAPIE' +
                    ' | Params=TOKEN' +
                    ' | ResponseMsg=' + response.text)

                return

            # Handle JSON
            r_json = response.json()

            # Initialize Vars Prior To Loop
            got_all_recs = True
            projects = []
            users = []
            event_loop_count = 0

            # Loop through each event record
            for r_loop in r_json:
                got_all_recs = True
                event_loop_count = event_loop_count + 1

                helper.log_debug(
                    'PROCID=' + event_id +
                    ' | MsgID=JOBSST' +
                    ' | Key=' + str(opt_project_id) +
                    ' | LoopCount=' + str(event_loop_count) +
                    ' | EventDateTime=' + str(r_loop['created_at']) +
                    ' | Start')

                if ((datetime.strptime(r_loop['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
                     < datetime.strptime(dtm_last_runtime, datetime_format)
                     and r_loop['started_at'] is None and r_loop['finished_at'] is None)
                        or (r_loop['started_at'] != None
                            and datetime.strptime(r_loop['started_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
                            < datetime.strptime(dtm_last_runtime, datetime_format)
                            and r_loop['finished_at'] is None)
                        or (r_loop['finished_at'] != None
                            and datetime.strptime(r_loop['finished_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
                            < datetime.strptime(dtm_last_runtime, datetime_format))
                   ):
                    continue

                if r_loop['finished_at'] != None:
                    r_loop['event_time'] = r_loop['finished_at']
                elif r_loop['started_at'] != None:
                    r_loop['event_time'] = r_loop['started_at']
                else:
                    r_loop['event_time'] = r_loop['created_at']

                # Store data into and r_loop['created_at'] != None Splunk
                event = helper.new_event(
                    data=json.dumps(r_loop),
                    index=helper.get_output_index(),
                    source=helper.get_input_type(),
                    sourcetype="GitLab:Job")

                try:
                    event_write.write_event(event)
                except Exception as raise_exception:
                    raise raise_exception

                if r_loop['status'] == "failed" and opt_get_trace is True:
                    helper.log_debug(
                        'PROCID=' + event_id +
                        ' | MsgID=TRACESST' +
                        ' | Key=' + str(opt_project_id) +
                        ' | LoopCount=' + str(event_loop_count) +
                        ' | EventDateTime=' + str(r_loop['created_at']) +
                        ' | Start')

                    url = (global_base_url +
                           '/api/' + api_version +
                           '/projects/' + opt_project_id +
                           '/jobs/' + str(r_loop['id']) +
                           '/trace')

                    # API Call to GitLab
                    response = helper.send_http_request(
                        url,
                        method,
                        parameters=call_api_param,
                        headers=headers)


                    # Handle Response
                    r_status = response.status_code
                    response.raise_for_status()

                    # If not Successful, report out error and finish processing
                    if r_status != 200:
                        helper.log_error(
                            'PROCID=' + event_id +
                            ' | MsgID=TRACEAPIE' +
                            ' | Params=TOKEN' +
                            ' | ResponseMsg=' + response.text)

                        return

                    # Handle JSON
                    trace_text = response.text


                    helper.log_debug(
                        'PROCID=' + event_id +
                        ' | MsgID=TRACERES' +
                        ' | Key=' + str(opt_project_id) +
                        ' | Response=' + trace_text)

                    #trace_array = re.split("\n",trace_text)
                    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
                    trace_array = ansi_escape.split(trace_text)
                    line_no = 0
                    for trace_entry in trace_array:
                        if trace_entry == "" or trace_entry == "\n\n":
                            continue
                        line_no += 1
                        trace_json = {}
                        trace_json['job_id'] = str(r_loop['id'])
                        trace_json['line'] = line_no
                        trace_json['event'] = re.sub("[\n\r]", "", str(trace_entry))

                        event = helper.new_event(
                            data=json.dumps(trace_json),
                            index=helper.get_output_index(),
                            source=helper.get_input_type(),
                            sourcetype="GitLab:Job:Trace")
                        try:
                            event_write.write_event(event)
                        except Exception as raise_exception:
                            raise raise_exception


    helper.log_debug(
        'PROCID=' + event_id +
        ' | MsgID=CKSRT' +
        ' | CheckPoint=' + log_checkpoint +
        ' | KV Value=' + cur_runtime)

    helper.save_check_point(
        checkpoint,
        cur_runtime)

    helper.log_info('PROCID=' + event_id + ' | MsgID=End')

def field_assign(input_json, input_field, value=None):
    """Generic Field Assignment."""

    if input_field in input_json:
        test = input_json[input_field]

        if test is None:
            return ""

        if value is None:
            return str(input_json[input_field])

        return value

    return ""

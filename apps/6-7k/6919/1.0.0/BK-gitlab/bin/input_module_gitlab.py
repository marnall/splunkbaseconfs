import requests
import logging
import json
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from json import JSONEncoder

class DateTimeEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    gl_url = definition.parameters.get('gitlab_url', None)
    gl_token = definition.parameters.get('gitlab_api_key', None)
    email = definition.parameters.get('gitlab_mail', None)
    # Add the return statement at the end
    return None

def collect_events(helper, ew):
    """Implement your data collection logic here"""

    # Retrieve the input configurations from the setup page
    gl_url = helper.get_arg('gitlab_url')
    gl_token = helper.get_arg('gitlab_api_key')
    email = helper.get_arg('gitlab_mail')

    current_datetime = datetime.now(timezone.utc)
    one_minute_before = current_datetime - timedelta(minutes=5)

    start_min = one_minute_before.strftime("%Y-%m-%dT%H:%M:00Z")
    end_min = current_datetime.strftime("%Y-%m-%dT%H:%M:00Z")

    # Define headers for API calls
    headers = {
        'Authorization': 'Bearer ' + gl_token
    }

    # Define pagination parameters
    page = 1
    per_page = 100
    projects = []
    user_commits = []

    # Loop through pages of projects
    while True:
        # Get list of projects accessible by user
        url = gl_url + f'/api/v4/projects?membership=true&per_page={per_page}&page={page}'
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logging.error('Failed to get projects: ' + response.text)
            return {}
        try:
            page_projects = response.json()
        except json.JSONDecodeError as e:
            logging.error('Failed to parse JSON response for projects: ' + str(e))
            continue

        # Add projects to list and check if there are any more pages
        projects += page_projects
        if len(page_projects) < per_page:
            break
        else:
            page += 1

    for project in projects:
        # Get list of branches
        url = gl_url + '/api/v4/projects/' + str(project['id']) + '/repository/branches'
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logging.error('Failed to get branches for project ' + project['name'] + ': ' + response.text)
            continue
        branches = response.json()

        # Loop through branches
        for branch in branches:
            commits = []
            page = 1
            while True:
                url = gl_url + '/api/v4/projects/' + str(project['id']) + '/repository/commits?ref_name=' + branch[
                    'name'] + '&since=' + str(start_min) + '&until=' + str(end_min) + f'&per_page={per_page}&page={page}'
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    logging.error('Failed to get commits for branch ' + branch['name'] + ' in project ' +
                                  project['name'] + ': ' + response.text)
                    break
                try:
                    page_commits = response.json()
                except json.JSONDecodeError as e:
                    logging.error('Failed to parse JSON response for commits: ' + str(e))
                    break

                # Check if there are any commits left
                commits += page_commits
                if len(page_commits) == 0:
                    break
                elif len(page_commits) < per_page:
                    break
                else:
                    page += 1
            for commit in commits:
                if commit['committer_email'] == email:
                    # Get list of diffs for commit
                    url = gl_url + '/api/v4/projects/' + str(project['id']) + '/repository/commits/' + commit[
                        'id'] + '/diff'
                    response = requests.get(url, headers=headers)
                    if response.status_code != 200:
                        logging.error('Failed to get diffs for commit ' + commit['id'] + ' in project ' +
                                      project['name'] + ': ' + response.text)
                        continue
                    try:
                        diffs = response.json()
                    except json.JSONDecodeError as e:
                        logging.error('Failed to parse JSON response for diffs: ' + str(e))
                        continue

                    # Create list to store file changes for commit
                    commit_files = []

                    # Loop through diffs
                    for diff in diffs:
                        addition_count = 0
                        deletion_count = 0
                        for line in diff["diff"].split("\n"):
                            if line.startswith('+'):
                                addition_count += 1
                            elif line.startswith('-'):
                                deletion_count += 1
                        # check if diff is for a file (not a submodule or binary)
                        if diff.get('new_file') and not diff.get('deleted_file'):
                            commit_files.append(
                                {'action': 'create', 'file_path': diff['new_path'], 'Addition count': addition_count,
                                 'Deletion count': deletion_count})
                        elif not diff.get('new_file') and diff.get('deleted_file'):
                            commit_files.append(
                                {'action': 'delete', 'file_path': diff['old_path'], 'Addition count': addition_count,
                                 'Deletion count': deletion_count})
                        elif diff.get('new_file') and diff.get('deleted_file'):
                            commit_files.append(
                                {'action': 'move', 'previous_path': diff['old_path'], 'file_path': diff['new_path'],
                                 'Addition count': addition_count, 'Deletion count': deletion_count})
                        elif diff.get('renamed_file'):
                            commit_files.append(
                                {'action': 'move', 'previous_path': diff['old_path'], 'file_path': diff['new_path'],
                                 'Addition count': addition_count, 'Deletion count': deletion_count})
                        else:
                            # check if the file has been modified
                            if diff.get('diff'):
                                commit_files.append(
                                    {'action': 'modify', 'file_path': diff['new_path'],
                                     'Addition count': addition_count, 'Deletion count': deletion_count})
                            else:
                                commit_files.append(
                                    {'action': 'unchanged', 'file_path': diff['new_path'],
                                     'Addition count': addition_count, 'Deletion count': deletion_count})

                    commit_timestamp = datetime.strptime(commit['committed_date'], '%Y-%m-%dT%H:%M:%S.%f%z')
                    user_commits.append({
                        'project_id': project['id'],
                        'project_name': project['name'],
                        'project_description': project['description'],
                        'created_at': project['created_at'],
                        'last_activity_at': project['last_activity_at'],
                        'branch_name': branch['name'],
                        'branch_url': branch['name'],  # Corrected variable name
                        'commit_id': commit['id'],
                        'commit_title': commit['title'],
                        'commit_message': commit['message'],
                        'commit_url': commit['web_url'],
                        'commit_author_name': commit['author_name'],
                        'commit_author_email': commit['author_email'],
                        'commit_committed_date': commit['committed_date'],
                        'commit_timestamp': commit_timestamp,
                        'files_changed': commit_files,
                        'project_raw': project,
                        'branch_raw': branch,
                        'commit_raw': commit
                    })

    # Write events to Splunk
    for commit in user_commits:
        event_time = commit['commit_timestamp'].isoformat()
        data = json.dumps(commit, cls=DateTimeEncoder)
        event = helper.new_event(
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            data=data,
            time=event_time
        )
        ew.write_event(event)


# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json
import os.path
import gitlab

def isCheckpoint(check_file, chkpntID):
    file_exists = os.path.isfile(check_file) 
    if file_exists:
        with open(check_file, 'r') as file:
            chkpntID_list = file.read().splitlines()
    else:
        with open(check_file, 'w+') as file:
            chkpntID_list = file.read().splitlines()

    return (chkpntID in chkpntID_list)

def write2Checkpoint(check_file, log):
    with open(check_file,'a') as file:
        file.writelines(log + '\n')
        
def write2Splunk(helper, ew, data):
    event = helper.new_event(data, host=None, done=True, unbroken=True)

    try:
        ew.write_event(event)
    except Exception as e:
        raise e

def validate_input(helper, definition):
    gitlab_url = definition.parameters.get('gitlab_url', None)
    token = definition.parameters.get('token', None)
    endpoint = definition.parameters.get('endpoint', None)
    created_after = definition.parameters.get('created_after', None)
    project_id = definition.parameters.get('project_id', None)

def collect_events(helper, ew):
    opt_gitlab_url = helper.get_arg("gitlab_url")
    opt_token = helper.get_arg("token")
    opt_endpoint = helper.get_arg("endpoint")
    opt_created_after = helper.get_arg("created_after")
    opt_project_id = helper.get_arg("project_id")

    # Path para el archivo de checkpoint utilizado (se crea un archivo por fecha YYYYMMDD)
    dtFile = str(datetime.datetime.now().strftime("%Y%m%d"))
    check_file = os.path.join('/', os.path.dirname(os.path.abspath(__file__)), 'checkpoint', dtFile + '-gitlab')

    gl = gitlab.Gitlab(opt_gitlab_url, opt_token, per_page=100)
    
    if (opt_project_id):
        projects = gl.projects.get(opt_project_id)
        
        if opt_endpoint == 'events':
            for l in projects.events.list(after=opt_created_after):
                data = json.dumps(l.attributes)

                # Creates checkpoint ID for Event
                chkpntID = 'evt-' + str(l.attributes["project_id"]) + "|" + l.attributes["action_name"] + "|" + str(l.attributes["author_id"]) + "|" + l.attributes["created_at"] + "|" + l.attributes["author_username"]
                
                if not isCheckpoint(check_file, chkpntID):
                    # Write to Checkpoint File
                    write2Checkpoint(check_file, chkpntID)
                    # Write to Splunk
                    write2Splunk(helper, ew, data)
        elif opt_endpoint == 'jobs':
            for p in projects.pipelines.list():
                pipeline = projects.pipelines.get(p.attributes["id"])
                jobs = pipeline.jobs.list()
                for j in jobs:
                    data = json.dumps(j.attributes)
                    
                    # Creates checkpoint ID for Job
                    chkpntID = 'job-' + str(j.attributes["id"]) + "|" + str(j.attributes["status"]) + "|" + str(j.attributes["stage"]) + "|" + str(j.attributes["ref"]) + "|" + str(j.attributes["created_at"]) + "|" + str(j.attributes["started_at"]) + "|" + str(j.attributes["finished_at"]) + "|" + str(j.attributes["duration"]) + "|" + str(j.attributes["project_id"]) + "|" + str(j.attributes["pipeline_id"])
                    
                    if not isCheckpoint(check_file, chkpntID):
                        # Write to Checkpoint File
                        write2Checkpoint(check_file, chkpntID)
                        # Write to Splunk
                        write2Splunk(helper, ew, data)
        else:
            for c in projects.commits.list(since=opt_created_after):
                data = json.dumps(c.attributes)

                # Creates checkpoint ID for Event
                chkpntID = 'com-' + str(c.attributes["id"]) + "|" + c.attributes["short_id"] + "|" + str(c.attributes["created_at"]) + "|" + c.attributes["author_email"] + "|" + c.attributes["authored_date"] + "|" + c.attributes["committer_email"] + "|" + c.attributes["committed_date"] + "|" + str(c.attributes["project_id"])

                if not isCheckpoint(check_file, chkpntID):
                    # Write to Checkpoint File
                    write2Checkpoint(check_file, chkpntID)
                    # Write to Splunk
                    write2Splunk(helper, ew, data)
                
    else:
        if opt_endpoint == 'users':
            # List all Users
            users = gl.users.list()
            
            for u in users:
                data = json.dumps(u.attributes)
                
                # Creates checkpoint ID
                chkpntID = 'usr-' + str(u.attributes["id"]) + "|" + str(u.attributes["username"]) + "|" + str(u.attributes["state"]) + "|" + str(u.attributes["created_at"]) + "|" + str(u.attributes["last_sign_in_at"]) + "|" + str(u.attributes["confirmed_at"]) + "|" + str(u.attributes["last_activity_on"]) + "|" + str(u.attributes["email"]) + "|" + str(u.attributes["projects_limit"]) + "|" + str(u.attributes["current_sign_in_at"]) + "|" + str(u.attributes["can_create_group"]) + "|" + str(u.attributes["external"]) + "|" + str(u.attributes["two_factor_enabled"]) + "|" + str(u.attributes["private_profile"]) + "|" + str(u.attributes["is_admin"])
                
                if not isCheckpoint(check_file, chkpntID):
                    # Write to Checkpoint File
                    write2Checkpoint(check_file, chkpntID)
                    # Write to Splunk
                    write2Splunk(helper, ew, data)
        else:
            # List all the projects
            projects = gl.projects.list(as_list=False, all=True)
            
            if opt_endpoint == 'events':
                for project in projects:
                    for l in project.events.list(after=opt_created_after):
                        data = json.dumps(l.attributes)
    
                        # Creates checkpoint ID
                        chkpntID = 'evt-' + str(l.attributes["project_id"]) + "|" + l.attributes["action_name"] + "|" + str(l.attributes["author_id"]) + "|" + l.attributes["created_at"] + "|" + l.attributes["author_username"]
                        
                        if not isCheckpoint(check_file, chkpntID):
                            # Write to Checkpoint File
                            write2Checkpoint(check_file, chkpntID)
                            # Write to Splunk
                            write2Splunk(helper, ew, data)
            
            elif opt_endpoint == 'commits':
                for project in projects:
                    for c in project.commits.list(since=opt_created_after):
                        data = json.dumps(c.attributes)
    
                        # Creates checkpoint ID for Event
                        chkpntID = 'com-' + str(c.attributes["id"]) + "|" + c.attributes["short_id"] + "|" + str(c.attributes["created_at"]) + "|" + c.attributes["author_email"] + "|" + c.attributes["authored_date"] + "|" + c.attributes["committer_email"] + "|" + c.attributes["committed_date"] + "|" + str(c.attributes["project_id"])
    
                        if not isCheckpoint(check_file, chkpntID):
                            # Write to Checkpoint File
                            write2Checkpoint(check_file, chkpntID)
                            # Write to Splunk
                            write2Splunk(helper, ew, data)
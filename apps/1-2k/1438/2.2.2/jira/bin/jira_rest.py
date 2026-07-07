#!/usr/bin/python
# -*- coding: utf-8 -*-
import base64
import collections
import json
import re
import splunk.clilib.cli_common as spcli
import splunk.Intersplunk
import sys
import time
import urllib2
import urllib
from contextlib import closing
import logging
import logging.handlers
import os

import common
from common import logger
from jira_service import JiraService


def setup_jira_service():
    # Get configuration values from config.ini
    local_conf = common.getLocalConf()

    username = local_conf.get('jira', 'username')
    password = local_conf.get('jira', 'password')

    host = local_conf.get('jira', 'hostname')
    protocol = local_conf.get('jira', 'jira_protocol')
    port = local_conf.get('jira', 'jira_port')

    jira_service = JiraService(username, password, host, port, protocol)
    return jira_service


jira_service = setup_jira_service()

class DateHelper(object):
    pattern = '%Y-%m-%dT%H:%M:%S'
    date_pattern = "(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"
    date_values = re.compile(date_pattern)

    def make_epoch(self, date_str):
        return int(time.mktime(time.strptime(date_str, self.pattern)))

date_helper = DateHelper()

class SearchArgException(Exception):
    pass

def run_filters():
    results = []

    filters = jira_service.request("/rest/api/2/filter/favourite?expand")
    for filter in filters:
        row = {}
        row['name'] = filter['name']
        row['id'] = filter['id']
        row['owner'] = filter['owner']['name']
        row['owner_name'] = filter['owner']['displayName']
        row['search'] = filter['jql']
        row['url'] = filter['viewUrl']
        row['host'] = jira_service.host
        row['source'] = 'jira_rest'
        row['sourcetype'] = 'jira_filters'
        row['_time'] = int(time.time())
        row['_raw'] = str(row)
        results.append(row)

    splunk.Intersplunk.outputStreamResults(results)

def run_changelog(jql):
    target = '/rest/api/2/search'

    query_args = {
        "jql": jql,
        "fields": "key,id,reporter,assignee,summary",
        "maxResults": 1000,
        "expand": "changelog",
        "validateQuery": "false"
    }

    query_str = urllib.urlencode(query_args)

    changelog = jira_service.request(target +'?'+ query_str)
    results = []

    for issue in changelog['issues']:
        for field in issue['changelog']['histories']:
            for item in field['items']:
                row = {}

                row['created'] = field['created']
                row['user'] = field['author']['name']
                row['user_name'] = field['author']['displayName']
                row['field'] = item['field']
                row['from'] = item['fromString']
                row['to'] = item['toString']

                if date_helper.date_values.match(row['created']):
                    jdate = date_helper.date_values.match(row['created']).group(1)
                    epoch = date_helper.make_epoch(jdate)
                    row['_time'] = epoch

                row['_raw'] = str(row)
                row['host'] = jira_service.host
                row['source'] = 'jira_rest'
                row['sourcetype'] = 'jira_changelog'
                row['key'] = issue['key']
                if issue['fields']['reporter'] == None:
                    row['reporter'] = None
                    row['reporter_name'] = None
                else:
                    row['reporter'] = issue['fields']['reporter']['name']
                    row['reporter_name'] = issue['fields']['reporter']['displayName']
                if issue['fields']['assignee'] == None:
                    row['assignee'] = None
                    row['assignee_name'] = None
                else:
                    row['assignee'] = issue['fields']['assignee']['name']
                    row['assignee_name'] = issue['fields']['assignee']['displayName']
                row['summary'] = issue['fields']['summary']
                results.append(row)
    
    splunk.Intersplunk.outputStreamResults(results)

def sprints_by_rapidboard_id(rapidboard_id, rapidboard_name):
    results = []
    logger.info("rapidboard by ID")

    query_args = {
        "includeHistoricSprints": "true",
        "includeFutureSprints": "true"
    }
    query_str = urllib.urlencode(query_args)

    path = '/rest/greenhopper/1.0/sprintquery/' + str(rapidboard_id) + '?' + query_str
    sprints = jira_service.request(path)

    for sprint in sprints['sprints']:
        row = {}
        row['name'] = rapidboard_name
        row['id'] = rapidboard_id
        row['sprint_id'] = sprint['id']
        row['sprint_name'] = sprint['name']
        row['sprint_state'] = sprint['state']
        row['host'] = jira_service.host
        row['source'] = 'jira_rest'
        row['sourcetype'] = 'jira_sprints'
        row['_time'] = int(time.time())
        row['_raw'] = str(row)
        results.append(row)
    
    return results

def get_field_name(jirafield, field_list, use_internal_field_names):
    if use_internal_field_names == True:
        field = jirafield
    else:
        if jirafield in field_list:
            field = field_list[jirafield]
        else:
            field = jirafield

    return field

def sprints_by_rapidboard(rapidboards):
    logger.info("rapid boards all")
    results = []

    query_args = {
        "includeHistoricSprints": "true",
        "includeFutureSprints": "true"
    }
    query_str = urllib.urlencode(query_args)

    for view in rapidboards['views']:
        path = '/rest/greenhopper/1.0/sprintquery/' + str(view['id'])

        sprints = jira_service.request(path + "?" + query_str)

        for sprint in sprints['sprints']:
            row = {}
            row['sprint_id'] = sprint['id']
            row['sprint_name'] = sprint['name']
            row['sprint_state'] = sprint['state']
            row['host'] = jira_service.host
            row['source'] = 'jira_rest'
            row['sourcetype'] = 'jira_sprints'
            row['name'] = view['name']
            row['id'] = view['id']
            row['owner'] = view['filter']['owner']['userName']
            row['owner_name'] = view['filter']['owner']['displayName']
            row['filter_query'] = view['filter']['query']
            row['filter_name'] = view['filter']['name']
            row['filter_id'] = view['filter']['id']
            board_admins = []
            for admin in view['boardAdmins']['userKeys']:
                board_admins.append(admin['key'])
            row['boardAdmins'] = board_admins
            row['_time'] = int(time.time())
            row['_raw'] = str(row)
            results.append(row)
            
    
    return results

def parse_kv_string(kv_str_arr):
    data = []

    for kv in kv_str_arr:
        kv_arr_open = kv.find("[")
        kv_arr_close = kv.find("]")
        kv = kv[kv_arr_open+1:kv_arr_close]
        kv = kv.split(",")

        out = {}

        for item in kv:
            pair = item.split("=")
            logger.info(pair)
            k = pair[0]
            v = pair[1]
            out[k] = v

        data.append(out)

    return data

def parse_kv_string_fields(kv_string_fields, fieldlist, use_internal_field_names):
    kv_string_pretty_fields = []
    for kv_string_field in kv_string_fields:
        field = get_field_name(kv_string_field, fieldlist, use_internal_field_names)
        kv_string_pretty_fields.append(field)

    return kv_string_pretty_fields

def parse_issues(issues, fieldlist, use_internal_field_names, time_field, kv_string_fields=[]):
    results = []

    for issue in issues:
        row = {}

        kv_string_fields = parse_kv_string_fields(kv_string_fields, fieldlist, use_internal_field_names)

        for jirafield, v in issue["fields"].iteritems():
            field = get_field_name(jirafield, fieldlist, use_internal_field_names)

            if field in kv_string_fields:
                parsed_kv = parse_kv_string(v)
                row[field] = json.dumps(parsed_kv, sort_keys=True)
                row[field+"_orig"] = v

            elif isinstance(v, basestring) == True:
                row[field] = v
            else:
                row[field] = json.dumps(v)

        if use_internal_field_names != True:
            if row[fieldlist[time_field]] != None:
                if date_helper.date_values.match(row[fieldlist[time_field]]):
                    jdate = date_helper.date_values.match(row[fieldlist[time_field]]).group(1)
                    epoch = date_helper.make_epoch(jdate)
            else:
                epoch = 0
        else:
            if row[time_field] != None:
                if date_helper.date_values.match(row[time_field]):
                    jdate = date_helper.date_values.match(row[time_field]).group(1)
                    epoch = date_helper.make_epoch(jdate)
            else:
                epoch = 0

        if use_internal_field_names == True:
            row['key'] = issue['key']
        else:
            row['Key'] = issue['key']

        row['_time'] = epoch
        row['_raw'] = str(row)
        row['host'] = jira_service.host
        row['source'] = 'jira_rest'
        row['sourcetype'] = 'jira_issues'
        results.append(row)

    return results

# A lookup for specific summary field keys to internal field names
# Eg: assignee = assignee['name']
# Sub-items of a list field are multivalued
list_field_summary = {
    'assignee'   : 'name',
    'components' : 'name',
    'creator'    : 'name',
    'fixVersions': 'name',
    'inwardIssue': 'key',
    'priority'   : 'name',
    'project'    : 'key',
    'reporter'   : 'name',
    'resolution' : 'name',
    'status'     : 'name',
}

# Don't break and store these fields
ignore_fields = ['self','id','avatarUrls','timeZone','active','iconUrl']

# Iterate over nested dicts and lists and add strings to row
def semi_recursive_parse(d,row,jirafield,field,parent_type=None,path=None):
    if isinstance(d, dict):
        for k,v in d.iteritems():
            if k in ignore_fields:
                continue

            subpath = ""
            if not path:
                subpath = "%s_%s" % (field,str(k))
            else:
                subpath = "%s_%s" % (path,str(k))
            
            if isinstance(v, dict) or isinstance(v, list):
                semi_recursive_parse(v,row,jirafield,field,parent_type=dict,path=subpath)
                continue
            
            if jirafield in list_field_summary and k == list_field_summary[jirafield]:
                if parent_type == list:
                    row[field].append(v)
                else:
                    row[field] = v
            elif parent_type == list:
                if subpath in row:
                    row[subpath].append(str(v))
                else:
                    row[subpath] = [str(v)]
            else:
                row[subpath] = str(v)

    elif isinstance(d, list):
        
        if not path:
            subpath = "%s" % field
        else:
            subpath = "%s" % path

        row[subpath] = []
        
        for i,v in enumerate(d):
            if isinstance(v, dict):
                semi_recursive_parse(v,row,jirafield,field,parent_type=list,path=subpath)
            elif isinstance(v, basestring):
                row[subpath].append(v)
    
    elif isinstance(d, basestring):
        row[field] = d
    else:
        return


def parse_issues_no_kv(issues, fieldlist, use_internal_field_names, time_field):
    results = []

    for issue in issues:
        row = {}
        row['key'] = issue['key']

        for jirafield, v in issue["fields"].iteritems():
            field = get_field_name(jirafield, fieldlist, use_internal_field_names)
            field = field.replace("/","")

            # The unparsed field as a json string: 
            # row[field+"_orig"] = json.dumps(v)

            semi_recursive_parse(v,row,jirafield,field)

        if use_internal_field_names != True:
            if row[fieldlist[time_field]] != None:
                if date_helper.date_values.match(row[fieldlist[time_field]]):
                    jdate = date_helper.date_values.match(row[fieldlist[time_field]]).group(1)
                    epoch = date_helper.make_epoch(jdate)
            else:
                epoch = 0
        else:
            if row[time_field] != None:
                if date_helper.date_values.match(row[time_field]):
                    jdate = date_helper.date_values.match(row[time_field]).group(1)
                    epoch = date_helper.make_epoch(jdate)
            else:
                epoch = 0

        if use_internal_field_names == True:
            row['key'] = issue['key']
        else:
            row['Key'] = issue['key']

        row['_time'] = epoch
        row['_raw'] = str(row)
        row['host'] = jira_service.host
        row['source'] = 'jira_rest'
        row['sourcetype'] = '_json'
        results.append(row)

    return results

def parse_comments(issues, use_internal_field_names, time_field):
    results = []

    for issue in issues:
        row = {}

        path = '/rest/api/2/issue/' + issue['key'] + '/comment'
        comments = jira_service.request(path)
        comments = comments['comments']

        for comment in comments:
            for author in comment:
                if author == 'author' or author == 'updateAuthor':
                    row[author] = comment[author]['name']
                    row[author + '_name'] = comment[author]['displayName']
            row['created'] = comment['created']
            row['updated'] = comment['updated']
            row['comment'] = comment['body']
            if use_internal_field_names == True:
                row['key'] = issue['key']
            else:
                row['Key'] = issue['key']
            if row[time_field] != None:
                if date_helper.date_values.match(row[time_field]):
                    jdate = date_helper.date_values.match(row[time_field]).group(1)
                    epoch = date_helper.make_epoch(jdate)
            else:
                epoch = 0
            row['_time'] = epoch
            row['_raw'] = str(row)
            row['host'] = jira_service.host
            row['source'] = 'jira_rest'
            row['sourcetype'] = 'jira_comments'
            results.append(row)
    
    return results
        

def run_rapidboards_all():
    logger.info("run_rapidboards_all")

    path = '/rest/greenhopper/1.0/rapidviews/list'
    rapidboards = jira_service.request(path)
    results = sprints_by_rapidboard(rapidboards)
    splunk.Intersplunk.outputStreamResults(results)


def run_rapidboards_list():
    logger.info("run_rapidboards_list")

    path = '/rest/greenhopper/1.0/rapidview'
    rapidboards = jira_service.request(path)

    results = []
    for view in rapidboards['views']:
        row = {}
        row['name'] = view['name']
        row['id'] = view['id']
        row['host'] = jira_service.host
        row['source'] = 'jira_rest'
        row['sourcetype'] = 'jira_rapidboards'
        row['_time'] = int(time.time())
        row['_raw'] = str(row)
        results.append(row)

    splunk.Intersplunk.outputStreamResults(results)


def run_rapidboards_id(rapidboard_id):
    logger.info("run_rapidboards_id")

    path = '/rest/greenhopper/1.0/rapidview/' + rapidboard_id
    rapidboards = jira_service.request(path)

    results = sprints_by_rapidboard_id(rapidboard_id, rapidboards['name'])
    splunk.Intersplunk.outputStreamResults(results)


def run_rapidboards_id_issues(rapidboard_id):
    logger.info("run_rapidboards_id_issues")

    path = '/rest/greenhopper/1.0/xboard/work/allData/?rapidViewId=' + rapidboard_id
    rapidboards = jira_service.request(path)

    results = []
    columns = {}
    swimlanes = {}

    for cols in rapidboards['columnsData']['columns']:
        for status_id in cols['statusIds']:
            columns[status_id] = cols['name']

    if 'customSwimlanesData' in rapidboards['swimlanesData']:
        has_swimlanes = True
        for swimlane in rapidboards['swimlanesData']['customSwimlanesData']['swimlanes']:
            for issue_id in swimlane['issueIds']:
                swimlanes[issue_id] = {
                    'name': swimlane['name'],
                    'query': swimlane['query']
                }
    else:
        has_swimlanes = False

    for issues in rapidboards['issuesData']['issues']:
        row = {}
        for issue_id in issues:
            if 'Statistic' in issue_id:
                field = issues[issue_id]['statFieldId']
                if 'value' in issues[issue_id]['statFieldValue'].keys():
                    row[field] = str(issues[issue_id]['statFieldValue']['value'])
                else:
                    row[field] = ''
            else:
                if 'status' in issue_id:
                    if issue_id == 'statusName':
                        row['status'] = issues[issue_id]
                    if issue_id == 'statusId':
                        try:
                            row['column'].append(columns[issues[issue_id]])
                        except:
                            row['column'] = []
                            row['column'].append(columns[issues[issue_id]])
                elif 'type' in issue_id:
                    if issue_id == 'typeName':
                        row['type'] = issues[issue_id]
                elif 'priority' in issue_id:
                    if issue_id == 'priorityName':
                        row['priority'] = issues[issue_id]
                elif issue_id == 'fixVersions':
                    for fv in issues[issue_id]:
                        try:
                            row['fixVersions'].append(str(fv))
                        except:
                            row['fixVersions'] = []
                            row['fixVersions'].append(str(fv))
                elif issue_id == 'id':
                    if has_swimlanes:
                        row['swimlane'] = swimlanes[issues[issue_id]]['name']
                        row['swimlane_query'] = swimlanes[issues[issue_id]]['query']
                    row['id'] = issues[issue_id]
                else:
                    row[issue_id] = str(issues[issue_id])
        
        row['rapidboard'] = rapidboards['rapidViewId']
        row['source'] = 'rapidboards'
        row['host'] = 'JIRA'
        row['sourcetype'] = 'jira_rapidboards'
        row['_time'] = int(time.time())
        row['_raw'] = str(row)
        results.append(row)
    
    splunk.Intersplunk.outputStreamResults(results)


def run_rapidboards_id_sprints(rapidboard_id):
    logger.info("run_rapidboards_id_sprints")

    path = '/rest/greenhopper/1.0/xboard/work/allData/?rapidViewId=' + rapidboard_id
    rapidboards = jira_service.request(path)

    results = []

    for sprint in rapidboards['sprintsData']['sprints']:
        row = {}

        for k in sprint:
            if k == 'remoteLinks':
                for rl in sprint[k]:
                    if 'url' in rl:
                        try:
                            row['remoteLinks'].append(str(rl['url']))
                        except:
                            row['remoteLinks'] = []
                            row['remoteLinks'].append(str(rl['url']))
            else:
                row[k] = sprint[k]
        
        row['rapidboard'] = rapidboards['rapidViewId']
        row['host'] = jira_service.host
        row['source'] = 'jira_rest'
        row['sourcetype'] = 'jira_rapidboads'
        row['_time'] = int(time.time())
        row['_raw'] = str(row)

        results.append(row)
    
    splunk.Intersplunk.outputStreamResults(results)

def get_fields():
    path = '/rest/api/2/field'
    fullfields = jira_service.request(path)

    return fullfields

def run_jsqlsearch(jql, use_internal_field_names, show_comments, time_field, max_results=100000, is_issues_query=False, kv_string_fields=[]):
    offset = 0
    args = urllib.quote_plus(jql).split()

    target = '/rest/api/2/search'
    fullfields = get_fields()

    url_args = {
        "maxResults": max_results,
        "jql":jql,
        "validateQuery": "false"
    }

    encoded_url_args = urllib.urlencode(url_args)

    path = target + "?" + encoded_url_args
    issues = jira_service.request(path)

    # TODO: fix this
    # if show_comments == True:
    #     results = parse_comments(full2['issues'], change_field, time_field)
    #     splunk.Intersplunk.outputStreamResults(results)
    #     # return

    fieldlist = {}
    for fielditem in fullfields:
        fieldlist[fielditem['id']] = fielditem['name']

    if len(kv_string_fields) > 0:
        results = parse_issues(issues['issues'], fieldlist, use_internal_field_names, time_field, kv_string_fields=kv_string_fields)
    else:
        results = parse_issues_no_kv(issues['issues'], fieldlist, use_internal_field_names, time_field)
    
    splunk.Intersplunk.outputStreamResults(results)


def handle_rapidboard_args(args):
    invalid_args_msg = "Invalid search arguments"
    if len(args) < 2:
        run_rapidboards_list()
        return

    rapidboard_arg = args[1]

    if rapidboard_arg == "all":
        run_rapidboards_all()
    elif rapidboard_arg == "list":
        run_rapidboards_list()
    else: # ID
        rapidboard_id = rapidboard_arg

        if len(args) < 3: # nothing after ID
            run_rapidboards_id(rapidboard_id)
        else:
            rapidboard_id_arg = args[2]
            if rapidboard_id_arg == "sprints":
                run_rapidboards_id_sprints(rapidboard_id)

            elif rapidboard_id_arg == "issues":
                run_rapidboards_id_issues(rapidboard_id)

def handle_jql_args(args):
    if 'use_internal_field_names' in args[2:]:
        use_internal_field_names = True
    else:
        use_internal_field_names = False

    if 'show_comments' in args[2:]:
        show_comments = True
    else:
        show_comments = False


    if 'time_field' in args[2:]:
        time_field_idx = args.index('time_field') + 1
        if len(args) < time_field_idx + 1:
            raise SearchArgException("time_field used, but no field provided. Usage example: time_field foo")

        time_field = args[time_field_idx]

    else:
        time_field = 'created'

    if 'max_results' in args[2:]:
        max_results_idx = args.index('max_results') + 1
        if len(args) < max_results_idx + 1:
            raise SearchArgException("max_results used, but no number provided. Usage example: max_results 1000")
        
        max_results = args[max_results_idx]
        try:
            max_results = int(max_results)
        except:
            raise SearchArgException("max_results used, but a non-numeric argument was provided. Usage example: max_results 1000")
    else:
        max_results = 100000

    default_fields = ['key','id','created']

    jql = args[1]
    if args[0] == "batch":
        start_idx = 3

        batchargs = args[2]
        jql = jql + ' (' + batchargs + ')'

    else:
        start_idx = 2


    if 'kv_string_fields' in args[start_idx:]:
        kv_string_fields_idx = args.index('kv_string_fields') + 1
        if len(args) < kv_string_fields_idx + 1:
            raise SearchArgException("kv_string_fields used, but no field provided. Usage example: kv_string_fields 'foo,bar'")
        
        kv_string_fields = args[kv_string_fields_idx]
        kv_string_fields = kv_string_fields.split(",")
        logger.info("kv_string_fields: %s" % kv_string_fields)
    else:
        kv_string_fields = []


    # "issues" should really be named "filter" because that's what it really does
    if args[0] == "issues":
        jql = "filter="+jql

    logger.info("jql search: %s" % jql)
    run_jsqlsearch(jql, use_internal_field_names, show_comments, time_field, max_results=max_results, kv_string_fields=kv_string_fields)


def handle_args(args):
    logger.info("search args: %s" % args)
    invalid_args_msg = "Invalid search arguments"

    if args[0] == "filters":
        run_filters()

    elif args[0] == "changelog":
        jql = args[1]
        run_changelog(jql)

    elif args[0] == "rapidboards":
        handle_rapidboard_args(args)

    elif args[0] in ["jqlsearch", "batch", "issues"]:
        handle_jql_args(args)

    else:
        raise SearchArgException(invalid_args_msg)


try:
    handle_args(sys.argv[1:])

except SearchArgException, e:
    splunk.Intersplunk.outputStreamResults([{"exception":e, "_raw": e}])
    logger.exception(e)

except Exception, e:
    import traceback
    err = {}
    trace = traceback.format_exc()
    err['error'] = str(e)
    err['trace'] = str(trace)
    err['search'] = sys.argv[1:]
    logger.exception(err)


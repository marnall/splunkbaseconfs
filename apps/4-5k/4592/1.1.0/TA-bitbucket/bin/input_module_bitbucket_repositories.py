
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import re
import base64
import requests
import random
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
    # key = definition.parameters.get('key', None)
    # secret = definition.parameters.get('secret', None)
    # code = definition.parameters.get('code', None)
    pass


eventid = random.randint(0,1000000)

def collect_events(helper, ew):

    from datetime import datetime

    helper.log_info("EVENTID={},STATUS={}".format(eventid,"START"))

    createdtd = "is now"
    opt_key = helper.get_arg('key')
    opt_secret = helper.get_arg('secret')
    opt_code = helper.get_arg('code')
    opt_username = helper.get_arg('username')
    opt_url = helper.get_global_setting("base_url")

    datetime_format = '%Y-%m-%dT%H:%M:%S'

    auth = base64.b64encode(str(opt_key) + ':' + str(opt_secret))

    # Get Token Value
    checkpoint = auth + '-' + "access_token"
    accessToken = helper.get_check_point(checkpoint)

    if accessToken == None:
        accessToken=getTokensFromCode(helper,opt_key,opt_secret,opt_code)

        if accessToken=="ERROR":
            helper.log_error("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"ATRETER",accessToken))
            return


    # Get Checkpoint Value
    checkpoint = auth + '-' + "last_runtime"
    helper.bb_last_runtime = helper.get_check_point(checkpoint)

    # If there's no checkpoint value, set initial value to 2000-01-01
    if helper.bb_last_runtime == None:
        helper.bb_last_runtime = "2000-01-01T00%3A00%3A00"

    # Set Current RunTime
    helper.bb_cur_runtime = datetime.utcnow().strftime(datetime_format)
    helper.bb_cur_runtime = re.sub(":","%3A",str(helper.bb_cur_runtime))


    unparsedJson = callRepos(helper,ew,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username)

    if unparsedJson == None:
        return

    while 'next' in unparsedJson:

        unparsedJson = callRepos(helper,ew,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,unparsedJson['next'])

    helper.save_check_point(
        checkpoint,
        helper.bb_cur_runtime)

    helper.log_info("EVENTID={},STATUS={}".format(eventid,"END"))

def callRepos(helper,ew,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,nexturl=None):

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNCRST","callRepos start"))

    if nexturl == None:
        returnedJson=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,"repositories/{}".format(str(opt_username)))
    else:
        returnedJson=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,"repositories/{}".format(str(opt_username)),nexturl)

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"REPRETRP",returnedJson))

    if returnedJson == "ERROR":
        helper.log_error("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"REPRETER",returnedJson))
        return

    unparsedJson =returnedJson.json()

    parsedJson = transformRepo(helper,ew,unparsedJson,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username)


    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNCREN","callRepos end"))

    return unparsedJson

def callCommits(helper,ew,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,parsedRecord,nexturl=None):

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNCCST","callCommits start"))

    if nexturl == None:
        returnedCommits=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,"repositories/{}/{}/commits".format(str(opt_username),str(parsedRecord['slug'])))
    else:
        returnedCommits=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,"repositories/{}/{}/commits".format(str(opt_username),str(parsedRecord['slug'])),nexturl)

    returnedCommits = returnedCommits.json()

    loopCommits(helper,ew,returnedCommits,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,parsedRecord)

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNCCEN","callCommits end"))

    return returnedCommits

def callDiffStat(helper,ew,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,parsedRecord,parsedCommit,commit,nexturl=None):

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNCDSST","callDiffStat start"))

    if nexturl == None:
        returnedDiffStat=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,"repositories/{}/{}/diffstat/{}".format(str(opt_username),str(parsedRecord['slug']),str(parsedCommit['hash'])))
    else:
        returnedDiffStat=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,"repositories/{}/{}/diffstat/{}".format(str(opt_username),str(parsedRecord['slug']),str(parsedCommit['hash'])),nexturl)

    returnedDiffStat = returnedDiffStat.json()

    loopDiffStats(helper,ew,returnedDiffStat,commit)

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNCDSEN","callDiffStat end"))

    return returnedDiffStat

def callPullReqs(helper,ew,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,parsedRecord,unparsedRecord,nexturl=None):

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNCPRST","callPullReqs start"))

    if nexturl == None:
        returnedPullRequests=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,"repositories/{}/{}/pullrequests".format(str(opt_username),str(parsedRecord['slug'])))
    else:
        returnedPullRequests=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,"repositories/{}/{}/pullrequests".format(str(opt_username),str(parsedRecord['slug'])),nexturl)

    returnedPullRequests = returnedPullRequests.json()

    loopPullRequests(helper,ew,returnedPullRequests,unparsedRecord)

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNCPREN","callPullReqs end"))

    return returnedPullRequests

def callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,api_endpoint,url_override=None):

    helper.log_debug("EVENTID={},HCVAL={},FUNCTION={},MSG={}".format(eventid,"CAPIST","accessToken","START"))

    headers = {'Authorization' : '{}'.format('Bearer ' + str(accessToken))}

    if url_override == None:

        url = "{}/2.0/{}".format(str(opt_url),str(api_endpoint))
        params = "q=updated_on+%3E%3D+" + str(helper.bb_last_runtime) + "+AND+updated_on+%3C+" + str(helper.bb_cur_runtime)
        response = helper.send_http_request(url,"GET", parameters=params, headers=headers)
    else:
        url = url_override
        response = requests.get(url = url, headers=headers)

    r_status = response.status_code

    if r_status == 401:
        helper.log_debug('EVENTID={},HCVAL={},MSGVAL={}'.format(eventid,"TKREFST",'Refreshing Token'))

        accessToken = refreshToken(helper,auth,opt_key,opt_secret,opt_code)

        if accessToken == "ERROR":
            helper.log_error('EVENTID={},HCVAL={},MSGVAL={}'.format(eventid,"TKREFER",'Unable to refresh token'))
            return "ERROR"

        headers = {'Authorization' : '{}'.format('Bearer ' + str(accessToken))}
        response = requests.get(url = url, headers=headers)
        r_status = response.status_code
        response.raise_for_status()

    if r_status != 200:
        helper.log_error("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"ATRETER",r_status))
        return "ERROR"

    return response

def parseRepo(helper,ew,unparsedRecord):

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNPRST","parseRepo start"))

    parsedRecord = {}
    parsedRecord['name'] = addToJson(unparsedRecord,'name')
    parsedRecord['uuid'] = addToJson(unparsedRecord,'uuid')
    parsedRecord['updated_on'] = addToJson(unparsedRecord,'updated_on')
    parsedRecord['created_on'] = addToJson(unparsedRecord,'created_on')
    parsedRecord['has_issues'] = addToJson(unparsedRecord,'has_issues')
    parsedRecord['size'] = addToJson(unparsedRecord,'size')
    parsedRecord['type'] = addToJson(unparsedRecord,'type')
    parsedRecord['slug'] = addToJson(unparsedRecord,'slug')
    parsedRecord['is_private'] = addToJson(unparsedRecord,'is_private')
    parsedRecord['description'] = addToJson(unparsedRecord,'description')

    if 'owner' in unparsedRecord:
        parsedRecord['owner_name'] = addToJson(unparsedRecord['owner'],'display_name')
        parsedRecord['owner_uuid'] = addToJson(unparsedRecord['owner'],'uuid')
        parsedRecord['owner_nickname'] = addToJson(unparsedRecord['owner'],'nickname')
        parsedRecord['owner_type'] = addToJson(unparsedRecord['owner'],'type')
        parsedRecord['owner_account_id'] = addToJson(unparsedRecord['owner'],'account_id')

    if 'mainbranch' in unparsedRecord:
        parsedRecord['mainbr_type'] = addToJson(unparsedRecord['mainbranch'],'type')
        parsedRecord['mainbr_name'] = addToJson(unparsedRecord['mainbranch'],'name')

    if 'links' in unparsedRecord:
        if 'html' in unparsedRecord['links']:
            parsedRecord['link_html'] = addToJson(unparsedRecord['links']['html'],'href')

    helper.log_info(parsedRecord)

    write_parsedRecord = json.dumps(parsedRecord)
    event = helper.new_event(
        data=write_parsedRecord,
        index=helper.get_output_index(),
        source=helper.get_input_type(),
        sourcetype=helper.get_sourcetype() + ':repository'
        )
    ew.write_event(event)

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNPREN","parseRepo end"))

    return parsedRecord

def parseCommit(helper,ew,commit):

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNPCST","parseCommit start"))

    parsedCommit = {}
    parsedCommit['date'] = addToJson(commit,'date')
    parsedCommit['message'] = addToJson(commit,'message')
    parsedCommit['type'] = addToJson(commit,'type')
    parsedCommit['hash'] = addToJson(commit,'hash')

    if 'author' in commit:
        parsedCommit['auth_type'] = addToJson(commit['author'],'type')
        parsedCommit['auth_raw'] = addToJson(commit['author'],'raw')

        if 'user' in commit['author']:
            parsedCommit['auth_user_type'] = addToJson(commit['author']['user'],'type')
            parsedCommit['auth_user_nickname'] = addToJson(commit['author']['user'],'nickname')
            parsedCommit['auth_user_uuid'] = addToJson(commit['author']['user'],'uuid')
            parsedCommit['auth_user_accId'] = addToJson(commit['author']['user'],'account_id')


    if 'links' in commit:
        if 'html' in commit['links']:
            parsedCommit['link_html'] = addToJson(commit['links']['html'],'href')


    if 'repository' in commit:
        parsedCommit['repo_uuid'] = addToJson(commit['repository'],'uuid')

    if 'parents' in commit:
        i = 0
        for commitParent in commit['parents']:
            i += 1
            helper.log_debug("EVENTID={},HCVAL={},MSGVAL={},LOOP={}".format(eventid,"LPPPRST","parseCommit parents loop",str(i)))
            parsedCommit['parent_' + str(i) + '_hash'] = addToJson(commitParent['hash'],'uuid')
            parsedCommit['parent_' + str(i) + '_type'] = addToJson(commitParent['hash'],'type')

    write_parsedRecord = json.dumps(parsedCommit)
    event = helper.new_event(
        data=write_parsedRecord,
        index=helper.get_output_index(),
        source=helper.get_input_type(),
        sourcetype=helper.get_sourcetype() + ':commit'
        )
    ew.write_event(event)

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNPCEN","parseCommit end"))

    return parsedCommit

def parseDiffstat(helper,ew,diff,commit):

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNPDSST","parseDiffstat start"))

    parsedDiffstat = {}
    parsedDiffstat['date'] = addToJson(commit,'date')
    parsedDiffstat['hash'] = addToJson(commit,'hash')
    parsedDiffstat['type'] = addToJson(diff,'type')
    parsedDiffstat['status'] = addToJson(diff,'status')
    parsedDiffstat['lines_removed'] = addToJson(diff,'lines_removed')
    parsedDiffstat['lines_added'] = addToJson(diff,'lines_added')

    if 'old' in diff and diff['old'] != None:
        parsedDiffstat['old_path'] = addToJson(diff['old'],'path')
        parsedDiffstat['old_type'] = addToJson(diff['old'],'type')

    if 'new' in diff:
        parsedDiffstat['new_path'] = addToJson(diff['new'],'path')
        parsedDiffstat['new_type'] = addToJson(diff['new'],'type')

    write_parsedRecord = json.dumps(parsedDiffstat)
    event = helper.new_event(
        data=write_parsedRecord,
        index=helper.get_output_index(),
        source=helper.get_input_type(),
        sourcetype=helper.get_sourcetype() + ':diffstat'
        )
    ew.write_event(event)

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNPDSEN","parseDiffstat end"))

    return parsedDiffstat

def parsePullRequest(helper,ew,pullRequest,unparsedRecord):

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNPPRST","parsePullRequest start"))

    parsedPullRequest = {}
    parsedPullRequest['date_created'] = addToJson(pullRequest,'created_on')
    parsedPullRequest['date_updated'] = addToJson(pullRequest,'updated_on')
    parsedPullRequest['title'] = addToJson(pullRequest,'title')
    parsedPullRequest['state'] = addToJson(pullRequest,'state')
    parsedPullRequest['uuid'] = addToJson(unparsedRecord,'uuid')

    if 'reviewers' in pullRequest:
        i = 0
        for reviewers in pullRequest['reviewers']:
            i += 1
            helper.log_debug("EVENTID={},HCVAL={},MSGVAL={},LOOP={}".format(eventid,"LPPPRST","parsePullRequest reviewers loop",str(i)))

            parsedPullRequest['reviewer_type' + str(i)] = addToJson(reviewers['reviewers'],'type')
            parsedPullRequest['reviewer_nickname' + str(i)] = addToJson(reviewers['reviewers'],'nickname')
            parsedPullRequest['reviewer_uuid' + str(i)] = addToJson(reviewers['reviewers'],'uuid')
            parsedPullRequest['reviewer_accId' + str(i)] = addToJson(reviewers['reviewers'],'account_id')


    if 'links' in pullRequest:
        if 'html' in pullRequest['links']:
            parsedPullRequest['link_html'] = addToJson(pullRequest['links']['html'],'href')


    write_parsedRecord = json.dumps(parsedPullRequest)
    event = helper.new_event(
        data=write_parsedRecord,
        index=helper.get_output_index(),
        source=helper.get_input_type(),
        sourcetype=helper.get_sourcetype() + ':pullrequest'
        )
    ew.write_event(event)

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNPPRST","parsePullRequest start"))

    return parsedPullRequest

def loopCommits(helper,ew,returnedCommits,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,parsedRecord):

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNLCST","loopCommits start"))


    last_runtime = datetime.strptime(re.sub("%3A",":",str(helper.bb_last_runtime)),'%Y-%m-%dT%H:%M:%S')
    for commit in returnedCommits['values']:

        if last_runtime > datetime.strptime(commit['date'][:19],'%Y-%m-%dT%H:%M:%S'):
            continue

        parsedCommit = parseCommit(helper,ew,commit)

        returnedDiffStat = callDiffStat(helper,ew,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,parsedRecord,parsedCommit,commit)

        while 'next' in returnedDiffStat:

             returnedDiffStat = callDiffStat(helper,ew,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,parsedRecord,parsedCommit,commit,returnedDiffStat['next'])

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNLCEN","loopCommits end"))


def loopDiffStats(helper,ew,returnedDiffStat,commit):

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNLDSST","loopDiffStats start"))

    last_runtime = datetime.strptime(re.sub("%3A",":",str(helper.bb_last_runtime)),'%Y-%m-%dT%H:%M:%S')
    for diff in returnedDiffStat['values']:

        if last_runtime > datetime.strptime(commit['date'][:19],'%Y-%m-%dT%H:%M:%S'):
            continue

        parsedDiffstat = parseDiffstat(helper,ew,diff,commit)

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNLDSST","loopDiffStats end"))

def loopPullRequests(helper,ew,returnedPullRequests,unparsedRecord):

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNLPRST","loopPullRequests start"))

    for pullRequest in returnedPullRequests['values']:

        parsedPullRequest = parsePullRequest(helper,ew,pullRequest,unparsedRecord)

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNLPREN","loopPullRequests end"))


def transformRepo(helper,ew,unparsedJson,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username):

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNTRST","transformRepo start"))

    last_runtime = datetime.strptime(re.sub("%3A",":",str(helper.bb_last_runtime)),'%Y-%m-%dT%H:%M:%S')
    for unparsedRecord in unparsedJson['values']:

        if last_runtime > datetime.strptime(unparsedRecord['updated_on'][:19],'%Y-%m-%dT%H:%M:%S'):
            continue
        parsedRecord = parseRepo(helper,ew,unparsedRecord)

        returnedCommits = callCommits(helper,ew,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,parsedRecord)

        while 'next' in returnedCommits:

             returnedCommits = callCommits(helper,ew,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,parsedRecord,returnedCommits['next'])

        returnedPullRequests = callPullReqs(helper,ew,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,parsedRecord,unparsedRecord)

        while 'next' in returnedPullRequests:

            returnedPullRequests = callPullReqs(helper,ew,accessToken,auth,opt_key,opt_secret,opt_code,opt_url,opt_username,parsedRecord,unparsedRecord,returnedCommits['next'])

    helper.log_debug("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"FUNTREN","transformRepo end"))

def addToJson(jsonToSearch,fieldToTake):

    if fieldToTake in jsonToSearch:
        return jsonToSearch[fieldToTake]
    else:
        return None

def getTokensFromCode(helper,opt_key,opt_secret,opt_code):

    helper.log_debug("EVENTID={},HCVAL={},FUNCTION={},MSG={}".format(eventid,"GTFCST","getTokensFromCode","START"))
    url = "https://bitbucket.org/site/oauth2/access_token"
    auth = base64.b64encode(str(opt_key) + ':' + str(opt_secret))
    headers = {'Authorization' : '{}'.format('Basic ' + str(auth)),'Content-Type': 'application/x-www-form-urlencoded','Cache-Control': 'no-cache'}
    data = {"grant_type":'authorization_code', 'code': str(opt_code)}

    response = requests.post(url = url, headers=headers, data=data)

    # Handle Response
    r_status = response.status_code

    if r_status != 200:
        helper.log_error("EVENTID={},HCVAL={},FUNCTION={},CODE={},MSG={}".format(eventid,"GTFCER","getTokensFromCode",str(r_status),response.json()))
        return "ERROR"

    response = response.json()

    accessToken = response['access_token']
    refreshToken = response['refresh_token']

    helper.save_check_point(
        auth  + '-' + "access_token",
        accessToken)

    helper.save_check_point(
        auth  + '-' + "refresh_token",
        refreshToken)

    helper.log_debug("EVENTID={},HCVAL={},FUNCTION={},MSGVAL={}".format(eventid,"GTFCEN","getTokensFromCode",accessToken))

    return accessToken

def refreshToken(helper,auth,opt_key,opt_secret,opt_code):

    helper.log_debug("EVENTID={},HCVAL={},FUNCTION={},MSG={}".format(eventid,"RFTST","refreshToken","START"))

    checkpoint = auth  + '-' + "refresh_token"
    refresh_token = helper.get_check_point(checkpoint)

    url = "https://bitbucket.org/site/oauth2/access_token"
    auth = base64.b64encode(str(opt_key) + ':' + str(opt_secret))
    headers = {'Authorization' : '{}'.format('Basic ' + str(auth)),'Content-Type': 'application/x-www-form-urlencoded','Cache-Control': 'no-cache'}
    data = {"grant_type":'refresh_token', 'refresh_token': refresh_token}

    response = requests.post(url = url, headers=headers, data=data)

    response = response.json()

    accessToken = response['access_token']
    refreshToken = response['refresh_token']

    helper.save_check_point(
        auth + '-' + opt_code + '-' + "access_token",
        accessToken)

    helper.save_check_point(
        auth + '-' + opt_code + '-' + "refresh_token",
        refreshToken)

    helper.log_debug("EVENTID={},HCVAL={},FUNCTION={},MSG={}".format(eventid,"RFTEN","refreshToken","END"))

    return accessToken
    

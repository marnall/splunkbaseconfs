
# encoding = utf-8

import os
import sys
import time
import datetime
import base64
import json

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
    
    '''
    import random
    
    # Set Event Id For Logging
    eventId = str(random.randint(0,1000000))
    
    helper.log_debug('PROCID=' + str(eventId) + ' | Validation Start')
    
    # Initialize
    url_root = 'https://dev.azure.com/'
    method = 'GET'
    api_param = 'api-version=4.1'
    
    # This example accesses the modular input variable
    global_account = definition.parameters.get('global_account', None)
    valUsername = global_account['username']
    valPassword = global_account['password']
    valAuth = base64.b64encode(str(valUsername) + ':' + str(valPassword))
    organization = definition.parameters.get('organization', None)
    project = definition.parameters.get('project', None)
    team = definition.parameters.get('team', None)
    work_item_types = definition.parameters.get('work_item_types', None)
    proj_info = definition.parameters.get('get_project_info',None)
    team_info = definition.parameters.get('get_team_info',None)
    
    # Parse Params
    project = project.replace(' ',"%20")
    team = team.replace(' ',"%20")
    headers = {'Authorization' : '{}'.format('Basic ' + str(valAuth))}
    # Setup for API Call for Team Settings
    url = url_root + str(organization) + '/' + str(project) + '/' + str(team) + "/_apis/work/teamsettings"
    params = api_param
    
    helper.log_debug(
        'PROCID=' + str(eventId) + 
        ' | MsgID=VALTAPIS' + 
        ' | API URL=' + str(url)
        )
        
    # Call API and Validate Response
    response = helper.send_http_request(
        url,
        method,
        parameters=params,
        headers=headers
        )
            
    helper.log_debug(
        'PROCID=' + str(eventId) + 
        ' | MsgID=VALTAPIR' + 
        ' | Response=' + str(response)
        )    
        
    if str(response) != '<Response [200]>':
        raise "Failed to Connect to Azure DevOps using url : " + str(url) + ". Please confirm details entered are correct and the user has permission to access this service"
    
    helper.log_debug(
        'PROCID=' + str(eventId) + 
        ' | MsgID=VALINP' + 
        ' | Project=' + str(proj_info) +
        ' | Team=' + str(team_info) +
        ' | WorkItemTypes=' + str(len(work_item_types))
        )
    if (not proj_info and 
        not team_info and 
        len(work_item_types) == 0
        ):
        raise "No data inputs have been configured: Please specify a work item type or enable the project or team retrieval"
'''
    pass

def collect_events(helper, ew):
    
    import random
    from datetime import datetime
    
    # Initialize
    url_root = 'https://dev.azure.com/'
    method = 'GET'
    api_param = 'api-version=4.1'
    api_preview1 = '-preview.1'
    api_preview2 = '-preview.2'
    
    # Variables
    GetIteration = True
    statesToExclude = ["Done","Removed"]
    
    # Set Event Id For Logging
    eventId = str(random.randint(0,1000000))
    
    # Get Input Params
    helper.log_info('PROCID=' + str(eventId) + ' | Start')
    opt_global_account = helper.get_arg('global_account')
    username = opt_global_account['username']
    password = opt_global_account['password']
    auth = base64.b64encode(str(username) + ':' + str(password))
    opt_organization = helper.get_arg('organization')
    opt_project = helper.get_arg('project')
    opt_team = helper.get_arg('team')
    opt_work_item_types = helper.get_arg('work_item_types')
    opt_get_previous_work_items = helper.get_arg('get_previous_work_items')
    opt_get_team_info = helper.get_arg('get_team_info')
    
    global_getOnPrem = helper.get_global_setting("use_custom_endpoint")
    global_url = helper.get_global_setting("custom_endpoint")    
    
    helper.log_debug(
        'PROCID=' + str(eventId) + 
        ' | MsgID=INITVARS' + 
        ' | Input Params - Account=' + str(username) + 
        ' | Organization=' + str(opt_organization)  + 
        ' | Project=' + str(opt_project) + 
        ' | Team=' + str(opt_team) + 
        ' | Work Item Types=' + str(opt_work_item_types)
        )
    
    # Parse Params
    opt_project = opt_project.replace(' ',"%20")
    opt_team = opt_team.replace(' ',"%20")
    headers = {'Authorization' : '{}'.format('Basic ' + str(auth))}
    
    if global_getOnPrem:
        url_root = 'http://' + global_url + '/DefaultCollection'
    else:
        url_root = url_root + str(opt_organization)
    
    if len(opt_work_item_types) >= 1 and str(opt_work_item_types) != "[u'[]']":
        
        # Setup for Work Item Relation Types
        url = url_root + "/_apis/wit/workitemrelationtypes"
        params = api_param
        
        # Call API
        response = helper.send_http_request(
            url,
            method,
            parameters=params,
            headers=headers)
        helper.log_debug(
            'PROCID=' + str(eventId)  + 
            ' | MsgID=RTAPIR' + 
            ' | Relation Type Response - ' + str(response)
            )
        rel_json = response.json()
        
        # Error Handling
        if str(response) != '<Response [200]>':
            helper.log_error(
                'PROCID=' + str(eventId) + 
                ' | MsgID=RTAPIE' + 
                ' | API=ReleationType - ResponseCode=' + str(response) + 
                ' | ResponseMsg=' + str(rel_json)
                )
            return
        
        # Get List of Iterations to Exclude 
        if not opt_get_previous_work_items:
            
            # Get Iteration Exclusion Info from KV Store
            iterationsToExclude = helper.get_check_point(str(opt_organization) + '-' + str(opt_project) + '-' + str(opt_team) + 'Scrum-ITE')           # Scrum Items To Exclude
            currentIterationEndDate = helper.get_check_point(str(opt_organization) + '-' + str(opt_project) + '-' + str(opt_team) + 'Scrum-CIED')      # Scrum Current Iteration End Date
            
            helper.log_debug(
                'PROCID=' + str(eventId) + 
                ' | MsgID=ITKVR' + 
                ' | Reading Records' +
                ' | KV_Store_Ref[' + str(opt_organization) + '-' + str(opt_project) + '-' + str(opt_team) + 'Scrum-ITE]=' + str(iterationsToExclude) + 
                ' | KV_Store_Ref[' + str(opt_organization) + '-' + str(opt_project) + '-' + str(opt_team) + 'Scrum-CIED]=' + str(currentIterationEndDate)
                )
            
            # Validate Iteration List To Exclude
            if (iterationsToExclude == None or 
                datetime.strptime(currentIterationEndDate, '%Y-%m-%d').date() < datetime.today().date()
                ):
                # Setup for API Call for Iterations
                url = url_root + '/' + str(opt_project) + '/' + str(opt_team) + "/_apis/work/teamsettings/iterations"
                params = api_param
                
                # Call API
                response = helper.send_http_request(
                    url,
                    method,
                    parameters=params,
                    headers=headers
                    )
                    
                helper.log_debug('PROCID=' + str(eventId) + 
                    ' | MsgID=ITKVAPIR' + 
                    ' | Iterations Response - ' + str(response)
                    )
                    
                it_json = response.json()
                
                # Error Handling
                if str(response) != '<Response [200]>':
                    helper.log_error(
                        'PROCID=' + str(eventId) + ' | MsgID=ITKVAPIE' + 
                        ' | API=Iterations - ResponseCode=' + str(response) + 
                        ' | ResponseMsg=' + str(it_json)
                        )
                    return
                
                GetIteration = False    # Prevents additional API call to same service further down 
                
                # Set List of Iterations for Which Associated Work Items will be Excluded
                iterationsToExclude = []
                for iterationLoop in it_json['value']:
                    
                    if iterationLoop['attributes']['finishDate'] != None:
                        isValidDate = True
                        try:
                            day,month,year = iterationLoop['attributes']['finishDate'].split('/')
                            EndDate = datetime.datetime(int(year),int(month),int(day))
                        except ValueError:
                            isValidDate = False
                            
                        if (isValidDate and 
                            EndDate.date() < datetime.today().date()
                            ):
                            iterationsToExclude.append(iterationLoop['name'])
                        elif (isValidDate and 
                            iterationLoop['attribute']['startDate'].date() < datetime.today().date()
                            ):
                            currentIterationEndDate = EndDate
            
            if currentIterationEndDate == None:
                currentIterationEndDate = datetime.now().strftime('%Y-%m-%d')
            
            # Store Values in KV Store
            helper.log_debug(
                'PROCID=' + str(eventId) + 
                ' | MsgID=ITKVS' + 
                ' | Writing Records' + 
                ' | KV_Store_Ref[' + str(opt_organization) + '-' + str(opt_project) + '-' + str(opt_team) + 'Scrum-ITE]=' + str(iterationsToExclude) + 
                ' | KV_Store_Ref[' + str(opt_organization) + '-' + str(opt_project) + '-' + str(opt_team) + 'Scrum-CIED]=' + str(currentIterationEndDate)
                )
                
            helper.save_check_point(
                str(opt_organization) + '-' + str(opt_project) + '-' + str(opt_team) + 'Scrum-ITE',
                iterationsToExclude
                )
                
            helper.save_check_point(
                str(opt_organization) + '-' + str(opt_project) + '-' + str(opt_team) + 'Scrum-CIED',
                currentIterationEndDate
                )
            
        # Loop Through User Selected Work Items
        for wit in opt_work_item_types:
    
            # Reset Vars
            wiList = ""
            
            # Get List of Work Items to Exclude 
            if not opt_get_previous_work_items:
                itemsToExclude = helper.get_check_point(str(opt_organization) + '-' + str(opt_project) + '-' + str(opt_team) + 'Scrum-WITE-' + wit)    # Scrum Work Item Type Exclusion
                if itemsToExclude == None:
                    itemsToExclude = []   
                    
                helper.log_debug(
                    'PROCID=' + str(eventId) + 
                    ' | MsgID=WITKVR' + 
                    ' | Reading Records' +
                    ' | WorkItemID=' + wit + 
                    ' | KV_Store_Ref[Scrum-WITE-' + wit + ']=' + str(iterationsToExclude) + 
                    ' | KV_Store_Ref[Scrum-CIED]=' + str(currentIterationEndDate)
                    )
                                
            if global_getOnPrem:
                # Setup for API Call for Work Item Types
                url = url_root + '/' + str(opt_project) + '/' + str(opt_team) + '/_apis/work/backlogs/Microsoft.' + str(wit) + 'Category/workItems'
                params = api_param + api_preview1
                WIMethod = method
                # Call API
                response = helper.send_http_request(
                    url,
                    method,
                    parameters=params,
                    headers=headers
                    )
                    
                helper.log_debug(
                    'PROCID=' + str(eventId) + 
                    ' | MsgID=WBLAPIR' +
                    ' | WorkItemID=' + wit + 
                    ' | BacklogResponse - ' + str(response)
                    )
                
                r_json = response.json()
            
                # Error Handling
                if str(response) != '<Response [200]>':
                    helper.log_error(
                        'PROCID=' + str(eventId) + 
                        ' | MsgID=WBLAPIE' + 
                        ' | WorkItemID=' + wit + 
                        ' | API=BacklogWorkItems - ResponseCode=' + str(response) + 
                        ' | ResponseMsg=' + str(r_json)
                        )
                    return
                
                # Build List of Work Items for Specified Type
                for respLoop in r_json['workItems']:
                    if not (
                        not opt_get_previous_work_items and  
                        respLoop['target']['id'] in itemsToExclude
                        ):
                        wiList = str(wiList) + str(respLoop['target']['id']) + ","
                
            else:
                GotAllWorkItems=False
                url = "https://almsearch.dev.azure.com/"  + str(opt_organization) + '/' + str(opt_project)  + "/_apis/search/workitemsearchresults"
                params = api_param + api_preview1
                WIMethod = "POST"
                i = 0
                while not GotAllWorkItems:
                    i = i + 1000 
                    
                    if wit == "Requirement":
                        WIWit = "Backlog"
                    elif wit == "Task":
                        WIWit = "Task OR Bug"
                    else:
                        WIWit = wit
                        
                    WIBody = {}
                    WIBody['searchText'] = "t:" + str(WIWit)
                    WIBody['$Skip'] = i - 1000
                    WIBody['$top'] = i
                    WIBody['filters'] = {}
                    WIBody['$orderBy'] = []
                    WIBody['$orderBy'].append({})
                    WIBody['$orderBy'][0]['field'] = "system.id"
                    WIBody['$orderBy'][0]['sortOrder'] = "ASC"
                
                    helper.log_debug(
                        'PROCID=' + str(eventId) + 
                        ' | MsgID=REQUESTTEST' +
                        ' | url=' + str(url) + 
                        ' | wibody=' + str(WIBody)
                        )
    
                    # Call API
                    response = helper.send_http_request(
                        url,
                        WIMethod,
                        payload=WIBody,
                        parameters=params,
                        headers=headers
                        )
                        
                    helper.log_debug(
                        'PROCID=' + str(eventId) + 
                        ' | MsgID=WSHAPIR' +
                        ' | WorkItemID=' + wit + 
                        ' | BacklogResponse - ' + str(response)
                        )
                        
                    if (str(response) != '<Response [200]>' and
                        i == 1000):
                        helper.log_error(
                            'PROCID=' + str(eventId) + 
                            ' | MsgID=WSHAPIE' + 
                            ' | WorkItemID=' + wit + 
                            ' | API=BacklogWorkItems - ResponseCode=' + str(response) + 
                            ' | ResponseMsg=' + str(r_json)
                            )
                        return
                    elif str(response) == '<Response [200]>':
                        
                        temp_json = response.json()
                        if len(temp_json['results']) < 999:
                            GotAllWorkItems = True
                            
                        for respLoop in temp_json['results']:
                            if ('fields' in respLoop and 
                                'system.id' in respLoop['fields'] and
                                not (
                                not opt_get_previous_work_items and  
                                respLoop['fields']['system.id'] in itemsToExclude
                                )):
                                wiList = str(wiList) + str(respLoop['fields']['system.id']) + ","
                    else:
                        GotAllWorkItems = True
                        
            GotAllWIs = False
            iTop = 0
            iSkip = 0
            r_json = {}
            r_json['value'] = []
            
            helper.log_debug(
                    'PROCID=' + str(eventId) + 
                    ' | MsgID=WILISTSET' + 
                    ' | WorkItemID=' + wit + 
                    ' | wiList Response - ' + str(wiList)
                    )
            
            while not GotAllWIs:
                iSkip = iTop
                iTop = iTop + 190
                iRec = 0
                wiListSend = ""
                
                for wiListEntry in wiList.split(","):
                    iRec = iRec + 1
                    if iRec < iSkip:
                        continue
                    if iRec > iTop:
                        break
                    wiListSend = wiListSend + str(wiListEntry) + ","
                    
                    helper.log_debug(
                        'PROCID=' + str(eventId) + 
                        ' | MsgID=WILISTLOOP' + 
                        ' | WorkItemID=' + wit + 
                        ' | wiList Response - ' + str(wiListSend)
                        )
                
                if iRec >= len(wiList.split(",")):
                    GotAllWIs = True
                    
                wiListSend = wiListSend.strip(",")
                    
                # Setup for API Call for Work Items
                url = url_root + '/' + str(opt_project) + '/_apis/wit/workitems'
                params = 'ids=' + wiListSend + '&' + '$expand=Relations' + '&' + api_param
                
                
                
                # Call API
                response = helper.send_http_request(
                    url,
                    method,
                    parameters=params,headers=headers)
                    
                helper.log_debug(
                    'PROCID=' + str(eventId) + 
                    ' | MsgID=WITAPIR' + 
                    ' | WorkItemID=' + wit + 
                    ' | WorkItem Response - ' + str(response)
                    )
                
                # Error Handling
                if str(response) != '<Response [200]>':
                    helper.log_error(
                        'PROCID=' + str(eventId) + 
                        ' | MsgID=WITAPIE' + 
                        ' | WorkItemID=' + wit + 
                        ' | API=WorkItem - ResponseCode=' + str(response) + 
                        ' | ResponseMsg=' + str(r_json)
                        )
                    return    
                
                temp_json = response.json()
                
                for tempJsonLoop in temp_json['value']:
                    r_json['value'].append(tempJsonLoop)
                
            # Loop Through Each Work Item
            for respLoop in r_json['value']:
                                
                # Skip if Work Item is Associated to an Expired Iteration
                if (not opt_get_previous_work_items and 
                    iterationsToExclude != None and 
                    respLoop['fields']['System.IterationPath'] in iterationsToExclude and
                    respLoop['fields']['System.State'] in statesToExclude and
                    datetime.strptime(respLoop['fields']['System.ChangedDate'], '%Y-%m-%d').date() < datetime.today().date()
                    ):
                    itemsToExclude.append('id')
                    continue
                    
                # Build Work Item Record
                WorkItem = {}
                WorkItem['id'] = respLoop['id']
                WorkItem['name'] = respLoop['fields']['System.Title']
                WorkItem['state'] = respLoop['fields']['System.State']
                WorkItem['type'] = respLoop['fields']['System.WorkItemType']
                WorkItem['project'] = respLoop['fields']['System.TeamProject']
                WorkItem['iteration'] = respLoop['fields']['System.IterationPath']
                WorkItem['lastUpdatedDate'] = respLoop['fields']['System.ChangedDate']
                WorkItem['url'] = respLoop['url']
                
                if 'System.BoardColumn' in respLoop['fields']:
                    WorkItem['list'] = respLoop['fields']['System.BoardColumn']
                
                if 'Microsoft.VSTS.Scheduling.Effort' in respLoop['fields']:
                    WorkItem['effort'] = respLoop['fields']['Microsoft.VSTS.Scheduling.Effort']
                elif 'Microsoft.VSTS.Scheduling.RemainingWork' in respLoop['fields']:
                    WorkItem['effort'] = respLoop['fields']['Microsoft.VSTS.Scheduling.RemainingWork']
                    
                if 'Microsoft.VSTS.Common.BacklogPriority' in respLoop['fields']:
                    WorkItem['backlogPriority'] = respLoop['fields']['Microsoft.VSTS.Common.BacklogPriority']
                
                if 'System.AssignedTo' in respLoop['fields']:
                    WorkItem['assignee'] = respLoop['fields']['System.AssignedTo']
                    
                if 'System.Tags' in respLoop['fields']:
                    WorkItem['tags'] = respLoop['fields']['System.Tags']
                
                if 'Microsoft.VSTS.CMMI.Blocked' in respLoop['fields']:
                    WorkItem['blocked'] = respLoop['fields']['Microsoft.VSTS.CMMI.Blocked']
                    
                if 'Microsoft.VSTS.Common.Activity' in respLoop['fields']:
                    WorkItem['activity'] = respLoop['fields']['Microsoft.VSTS.Common.Activity']
                    
                if 'Microsoft.VSTS.Common.ValueArea' in respLoop['fields']:
                    WorkItem['valueArea'] = respLoop['fields']['Microsoft.VSTS.Common.ValueArea']
                    
                if 'Microsoft.VSTS.Common.BusinessValue' in respLoop['fields']:
                    WorkItem['businessValue'] = respLoop['fields']['Microsoft.VSTS.Common.BusinessValue']
                
                # Get Work Item Relations
                if 'relations' in respLoop:
                    WorkItemRelations = []
                    for relLoop in respLoop['relations']:
                        WorkItemRelation = {}
                        WorkItemRelation['linkedTo'] = str(relLoop['url'].replace("https://dev.azure.com/mhm-uk-as/_apis/wit/workItems/",""))
                        relationType = next(d for d in rel_json['value'] if d['referenceName'] == relLoop['rel'])
                        WorkItemRelation['type'] = relationType['name']
                        WorkItemRelations.append(WorkItemRelation)
                        
                    WorkItem['rel'] = WorkItemRelations
                
                # Write Work Item to Splunk
                write_WorkItem = json.dumps(WorkItem)
                event = helper.new_event(
                    data=write_WorkItem,
                    index=helper.get_output_index(),
                    source=helper.get_input_type(),
                    sourcetype=helper.get_sourcetype() + ':WorkItem'
                    )
                ew.write_event(event)
        
            # Save Work Item Exclusions to KV Store
            if not opt_get_previous_work_items:
                helper.log_debug(
                    'PROCID=' + str(eventId) + 
                    ' | MsgID=WITKVS' + 
                    ' | WorkItemID=' + wit + 
                    ' | Writing Records'
                    ' | KV_Store_Ref[Scrum-WITE-' + wit + ']=' + str(itemsToExclude)
                    )
                    
                helper.save_check_point(
                    str(opt_organization) + '-' + str(opt_project) + '-' + str(opt_team) + 'Scrum-WITE-' + wit, 
                    itemsToExclude)
    
    if opt_get_team_info:
        # Setup for API Call for Team Settings
        url = url_root + '/' + str(opt_project) + '/' + str(opt_team) + "/_apis/work/teamsettings"
        params = api_param
        
        # Call API
        response = helper.send_http_request(
            url,
            method,
            parameters=params,
            headers=headers
            )
            
        helper.log_debug(
            'PROCID=' + str(eventId) + 
            ' | MsgID=ITSAPIR' + 
            ' | Team Settings Response - ' + str(response))
            
        ts_json = response.json()
        
        #Error Handling
        if str(response) != '<Response [200]>':
            helper.log_error(
                'PROCID=' + str(eventId) + 
                ' | MsgID=ITSAPIE' + 
                ' | API=TeamSettings - ResponseCode=' + str(response) + 
                ' | ResponseMsg=' + str(ts_json)
                )
            return
        
        if GetIteration:
            # Setup for API Call for Iterations
            url = url_root + '/' + str(opt_project) + '/' + str(opt_team) + "/_apis/work/teamsettings/iterations"
            params = api_param
            
            # Call API
            response = helper.send_http_request(
                url,
                method,
                parameters=params,
                headers=headers
                )
                
            helper.log_debug(
                'PROCID=' + str(eventId) + 
                ' | MsgID=IIAPIR' + 
                ' | Iterations Response - ' + str(response))
                
            it_json = response.json()
            
            #Error Handling
            if str(response) != '<Response [200]>':
                helper.log_error(
                    'PROCID=' + str(eventId) +
                    ' | MsgID=IIAPIE' + 
                    ' | API=Iterations - ResponseCode=' + str(response) + 
                    ' | ResponseMsg=' + str(it_json))
                return
        
        # Loop Through Each Iteration
        for iterationLoop in it_json['value']:
            
            # Build Iteration Record
            iteration = {}
            iteration['id'] = iterationLoop['id']
            iteration['name'] = iterationLoop['name']
            iteration['path'] = iterationLoop['path']
            iteration['startDate'] = iterationLoop['attributes']['startDate']
            iteration['endDate'] = iterationLoop['attributes']['finishDate']
            iteration['workDays'] = ts_json['workingDays']
            
            # Setup for API Call for Team Days Off
            url = url_root + '/' + str(opt_project) + '/' + str(opt_team) + "/_apis/work/teamsettings/iterations/" + str(iterationLoop['id']) + "/teamdaysoff"
            params = api_param
            
            # Call API
            response = helper.send_http_request(
                url,
                method,
                parameters=params,
                headers=headers
                )
                
            helper.log_debug('PROCID=' + str(eventId) + 
                ' | MsgID=ITDOAPIR' + 
                ' | IterationID=' + iteration['id'] + 
                ' | Team Days Off Response - ' + str(response)
                )
                
            tdo_json = response.json()
            
            #Error Handling
            if str(response) != '<Response [200]>':
                
                helper.log_error('PROCID=' + str(eventId) + 
                    ' | MsgID=ITDOAPIE' + 
                    ' | IterationID=' + iteration['id'] + 
                    ' | API=BacklogWorkItems - TeamDaysOff=' + str(response) + 
                    ' | ResponseMsg=' + str(tdo_json))
                    
                return
            
            iteration['daysOff'] = tdo_json['daysOff']
            
            # Write Iteration to Splunk
            write_iteration = json.dumps(iteration)
            
            event = helper.new_event(
                data=write_iteration,
                index=helper.
                get_output_index(),
                source=helper.get_input_type(),
                sourcetype=helper.get_sourcetype() + ':Iteration'
                )
                
            ew.write_event(event)
            
            # Setup for API Call for Team Capacities
            url = url_root + '/' + str(opt_project) + '/' + str(opt_team) + "/_apis/work/teamsettings/iterations/" + str(iterationLoop['id']) + "/capacities"
            params = api_param
            
            # Call API
            response = helper.send_http_request(url,method,parameters=params,headers=headers)
            helper.log_debug(
                'PROCID=' + str(eventId) + 
                ' | MsgID=ICAPIR' + 
                ' | IterationID=' + iteration['id'] + 
                ' | Team Capacity Response - ' + str(response)
                )
            cap_json = response.json()
            
            #Error Handling
            if str(response) != '<Response [200]>':
                helper.log_error(
                    'PROCID=' + str(eventId) + 
                    ' | MsgID=ICAPIE' +
                    ' | IterationID=' + iteration['id'] + 
                    ' | API=TeamCapacity - ResponseCode=' + str(response) + 
                    ' | ResponseMsg=' + str(cap_json)
                    )
                return
            
            # Loop Through Each Capacity
            for capLoop in cap_json['value']:
                if 'teamMember' in capLoop:
                    
                    # Build Capacity Record
                    capacity = {}
                    capacity['iterationId'] = iteration['id']
                    capacity['iterationPath'] = iteration['path']
                    capacity['memberId'] = capLoop['teamMember']['id']
                    capacity['memberName'] = capLoop['teamMember']['displayName']
                    capacity['memberUsername'] = capLoop['teamMember']['uniqueName']
                    capacity['activities'] = capLoop['activities']
                    capacity['daysOff'] = capLoop['daysOff']
                    
                    # Write Capacity To Splunk
                    write_capacity = json.dumps(capacity)
                    event = helper.new_event(
                        data=write_capacity,
                        index=helper.get_output_index(),
                        source=helper.get_input_type(),
                        sourcetype=helper.get_sourcetype() + ':Capacity'
                        )
                    ew.write_event(event)
    
    helper.log_info('PROCID=' + str(eventId) + ' | End')

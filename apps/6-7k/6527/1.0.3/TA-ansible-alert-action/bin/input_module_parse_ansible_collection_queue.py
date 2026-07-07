
# encoding = utf-8

import os
import sys
import time
import datetime
import base64 
import json
import requests
import lxml.etree as ET 
from urllib.parse import urlsplit
import splunklib.client as client

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
    # description = definition.parameters.get('description', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_description = helper.get_arg('description')
    # In single instance mode, to get arguments of a particular input, use
    opt_description = helper.get_arg('description', stanza_name)

    # get input type
    helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    helper.get_input_stanza()
    # get specific input stanza with stanza name
    helper.get_input_stanza(stanza_name)
    # get all stanza names
    helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    account = helper.get_user_credential_by_username("username")
    account = helper.get_user_credential_by_id("account id")
    # get global variable configuration
    global_outputtoindex = helper.get_global_setting("outputtoindex")
    global_ansible_tower_awx_host = helper.get_global_setting("ansible_tower_awx_host")
    global_ansible_tower_awx_user = helper.get_global_setting("ansible_tower_awx_user")
    global_ansible_tower_awx_pass = helper.get_global_setting("ansible_tower_awx_pass")

    # The following examples show usage of logging related helper functions.
    # write to the log for this modular input using configured global log level or INFO as default
    helper.log("log message")
    # write to the log using specified log level
    helper.log_debug("log message")
    helper.log_info("log message")
    helper.log_warning("log message")
    helper.log_error("log message")
    helper.log_critical("log message")
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(log_level)

    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    # get the response headers
    r_headers = response.headers
    # get the response body as text
    r_text = response.text
    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
    # get response cookies
    r_cookies = response.cookies
    # get redirect history
    historical_responses = response.history
    # get response status code
    r_status = response.status_code
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()

    # The following examples show usage of check pointing related helper functions.
    # save checkpoint
    helper.save_check_point(key, state)
    # delete checkpoint
    helper.delete_check_point(key)
    # get checkpoint
    state = helper.get_check_point(key)

    # To create a splunk event
    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    """

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''

    '''
    # The following example writes a random number as an event for each input config. (Single Instance Mode)
    # For advanced users, if you want to create single instance mod input, please use this code template.
    # Also, you need to uncomment use_single_instance_mode() above.
    import random
    input_type = helper.get_input_type()
    for stanza_name in helper.get_input_stanza_names():
        data = str(random.randint(0,100))
        event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
        ew.write_event(event)
    '''
    
    collectionName = "ansibleQueue"
    
    scheme, netloc, _, _, _ = urlsplit(helper.context_meta['server_uri'], allow_fragments=False)
    splunkd_host, splunkd_port = netloc.split(':')
    service = client.connect(scheme=scheme, host=splunkd_host, port=splunkd_port, token=helper.context_meta['session_key'], owner="nobody")
      
    myHostname = service.settings.content['host']   
    queueHandler = helper.get_arg('queue_handler')   
         
         
    if not collectionName in service.kvstore:
        service.kvstore.create(collectionName)
         
    collection = service.kvstore[collectionName]  
    
    queue = collection.data.query()
    
    if len(queue) == 0:
      helper.log_info("Nothing in the queue, exit 0")
      return 0
  
    batchSize = helper.get_arg('batch_size')
    if not batchSize is None and len(batchSize)>0:
      batchSize = 9999  
  
    towerUrl = helper.get_global_setting("ansible_tower_awx_host")

    #get credentials
    towerUser=helper.get_global_setting("ansible_tower_awx_user")
    towerPass=helper.get_global_setting("ansible_tower_awx_pass")
 
    helper.log_info("Found Username: {}".format(towerUser))  
  
    itemCount = 1
    for item in queue:
       
      helper.log_info("Queue item: {}".format(item))
      
      helper.log_info("QueueHandler={}, myHostname={}, itemHost/splunkHost: {}".format(queueHandler,myHostname,item['splunkHost']))
      
      if queueHandler == "thisServer" and item['splunkHost'] != myHostname:
        helper.log_info("This event is not for me, this is for {}, skipping this item".format(item['splunkHost']))
        continue
    
      role = myKvRole(helper,service)
      if queueHandler == "kvCaptain" and role != "KV Store captain":
        helper.log_info("This event is not for me, since im not the kv captain, so skipping this item, im: {}".format(role))
        continue
        
     
         
      if itemCount >= batchSize:
        helper.log_info("Reached batch size: {}, more will be executed next time".format(itemCount))
        break
      itemCount += 1
     
        
      template = item['template']
      templateType = item['templateType']
      map_id = item['map_id']
      payload = json.dumps(item['payload'])
      
      itsiGroupId = False
      if 'itsiGroupId' in item and item['itsiGroupId']:
        itsiGroupId = item['itsiGroupId']
    
      
      if not template.isnumeric():
        templateOrg = template
        helper.log_info("No id provided, trying to get id from name: {}".format(template))
        template = getTowerTemplateId(helper,towerUser,towerPass,template,templateType)
        if template == False:
          itsi(helper,itsiGroupId,"Unknown template defined, please check spelling/id: {}".format(templateOrg))
          log2index(helper,ew,map_id,"Unknown template defined, please check spelling/id: {}".format(templateOrg))
          collection.data.delete_by_id(id = item['_key'])
          continue      
    
    
      try: 
          
        result = runPlaybook(helper,template,templateType,payload,towerUser,towerPass)

        if result and "weberror" in result:
          collection.data.delete_by_id(id = item['_key'])
          log2index(helper,ew,map_id,"Ansible gave us the following error: {}".format(result['weberror']))
          itsi(helper,itsiGroupId,"Ansible gave us the following error: {}".format(result['weberror']))            
          continue
 
        if result and "details" in result:
          raise Exception(result["details"])
        
        if result and "ignored_fields" in result and result["ignored_fields"]:
          ignored_fields = json.dumps(result["ignored_fields"])
          log2index(helper,ew,map_id,"Ansible seems to have accepted our request, but did ignore some fields: {}".format(ignored_fields))
          itsi(helper,itsiGroupId,"Ansible seems to have accepted our request, but did ignore some fields: {}".format(ignored_fields))
        
        jobId = result['id']
        runStatus = result['status']
        created = result['created']
        jobName = result['name']
        jobStatus = ""        
        
        log2index(helper,ew,map_id,"Successfully: sent job to ansible, with jobId: {}".format(jobId))   
        itsi(helper,itsiGroupId,"Executing Playbook",jobId,"{}/#/jobs/playbook/{}".format(towerUrl,jobId))
        collection.data.delete_by_id(id = item['_key'])
        

        
        outputtoindex = helper.get_global_setting("outputtoindex")
        if not outputtoindex is None and outputtoindex == "1":
          helper.log_debug("Adding to kvstore")
          kvstore(helper, service, "ansibleResults", "add", {"_key": map_id, "mapId": map_id, "jobId": jobId, "created": created, "runStatus": runStatus, "jobName": jobName, "templateId": template, "templateType": templateType, "splunkHost": myHostname })
        else:
          helper.log_debug("NOT adding to kvstore, OutputToIndex is false")        
        
        
      
      except Exception as e:
        helper.log_error("Error when trying to contact ansible: {}".format(e))
        itsi(helper,itsiGroupId,"Error when trying to contact ansible: {}".format(e))
 
 
def myKvRole(helper,service):
  try:
    data = service.request("/services/kvstore/status", method='GET')
    root = ET.fromstring(data.body.read())
    replicationStatus = root.xpath('//*[local-name()="key" and @name="current"]//*[local-name()="key" and @name="replicationStatus"]/text()')
    return replicationStatus[0]
    
  except Exception as e:
    helper.log_info("Error when trying to get my role from url /services/kvstore/status: {}".format(e))
    return False
       
def log2index(helper,ew,map_id,log):
 
  helper.log_info(log)
    
  outputtoindex = helper.get_global_setting("outputtoindex")
  if outputtoindex is None or outputtoindex == "0":
    helper.log_info("OutputToIndex is not enabled, no reason to run this")
    return 0
    
  splunkdata = {}
  splunkdata['map_id'] = map_id
  splunkdata['message'] = log
    
  now = datetime.datetime.now()
  splunkdataOut = now.strftime("%d/%m/%Y %H:%M:%S")+" "
  splunkdataOut += ' '.join('{!s}="{}"'.format(key,val) for (key,val) in splunkdata.items())
  
  helper.log_info(splunkdataOut)
 
  stanza_name = helper.get_input_stanza_names()
  event = helper.new_event(source="TriforkAnsible", index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=splunkdataOut)      
  w = ew.write_event(event)



def runPlaybook(helper,template,templateType,payload,towerUser,towerPass):

 
    baseUrl = helper.get_global_setting("ansible_tower_awx_host")
    
    if templateType == "template":
      path = "/api/v2/job_templates/{}/launch/".format(template)
 
    if templateType == "workflow":
      path = "/api/v2/workflow_job_templates/{}/launch/".format(template)
 
    userAndPass = towerUser+":"+towerPass;
    userAndPass = base64.b64encode(userAndPass.encode()).decode()
    headers = { 'Authorization' : 'Basic %s' %  userAndPass, 'Content-Type': 'application/json' }
    

    result = webRequest(helper, baseUrl, path, "POST", headers, None, True, payload)

    return result
    
           
       
    
    
def itsi(helper,group_id, comment, ticket_id=None, ticket_url=None):
 if not group_id:
   helper.log_info("Not an ITSI event, skipping updating ITSI")
   return 1
   
 try:
   # Import ITSI-specific libraries
   from splunk.clilib.bundle_paths import make_splunkhome_path
   sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
   import itsi_path
   from itsi.event_management.sdk.grouping import EventGroup
   from itsi.event_management.sdk.custom_group_action_base import CustomGroupActionBase

   itsi_episode = EventGroup(helper.context_meta['session_key'])

   if not ticket_id == None:
     itsi_episode.update_ticket_info(group_ids=[group_id], ticket_system='Ansible Tower/AWX', ticket_id=str(ticket_id), ticket_url=str(ticket_url))
     
   itsi_episode.create_comment(group_id, comment)   
        
 except Exception as e:
   helper.log_info("Error creating entry in itsi, maybe not running itsi at all?: {}".format(e))
   
   
   
   
   
   
def kvstore(helper, service, collectionName, task, data):
    
    dataOrg = data
    data = json.dumps(data)
    dataJson = json.loads(data)
    
    if not collectionName in service.kvstore:
        service.kvstore.create(collectionName)
    
    collection = service.kvstore[collectionName]
    
    
    kvRecord = None
    try:
      kvRecord = collection.data.query_by_id(dataJson['_key'])
    except Exception as e:
      print ('Didnt find key, creating new entry')
        
    if kvRecord == None:
        collection.data.insert(data)
        print('Inserted %s', dataJson['_key'])
    else:
        collection.data.update(id = dataJson['_key'], data = data)
        print('Updated %s', dataJson['_key'])
    
    print("Should have our data: %s" % json.dumps(collection.data.query(), indent=1))
    
    return 0
    
    
    
       
       
def getTowerTemplateId(helper,towerUser,towerPass,template,templateType):
    
    if templateType == "template":
      path = "/api/v2/job_templates/"
     
    if templateType == "workflow":
      path = "/api/v2/workflow_job_templates/"
    
    userAndPass = towerUser+":"+towerPass;
    userAndPass = base64.b64encode(userAndPass.encode()).decode()
    headers = { 'Authorization' : 'Basic %s' %  userAndPass }
    
    baseUrl = helper.get_global_setting("ansible_tower_awx_host")
    
    helper.log_info("getTowerTemplateId - Calling: {}{}".format(baseUrl,path))
    
    response = webRequest(helper,baseUrl,path,"GET",headers,None,False)

    json_response = response

    for result in json_response['results']:
      if result['name'].lower() == template.lower():
        helper.log_info("From name: {}, i got id: {}".format(template,result['id']))
        return result['id']
        
    
    return False       




def webRequest(helper,baseUrl,path,method,headers=None,cert=None,onlyFirstPage=True,data=None):
 
    json_response = {}
    
    
    verify = helper.get_global_setting("cert_ca_bundle_path")
    if verify is None or len(verify) == 0:
      verify = False 
      
    try:
        breakLoop=True
        count=0

        #loop though all pages if any
        while breakLoop:
            if count > 500:
                helper.log_error("Over 500 pages on "+baseUrl+path+"?, dont think so, breaking out")
                breakLoop=False
                break
            
            count=count+1
            
            helper.log_info("webRequest - Calling, count: {}, baseUrl: {}{}".format(count,baseUrl,path))
            
            response=helper.send_http_request(baseUrl+path,method,parameters=None, payload=data, headers=headers, cookies=None, verify=verify, cert=cert, timeout=10)
            helper.log_debug("Response Code: {}".format(response.status_code))
            helper.log_debug("Response: {}".format(response.text))
            
            responseCode = str(response.status_code)
            if responseCode.startswith('4'):
              return {"weberror":"Got an error: {}, deleting from queue".format(responseCode)}
          
            
            response.raise_for_status()
     
            part_json = json.loads(response.content)

            #if this is the first time we run though the pages(also if there is only 1), set the newly downloaded json to the main json_response
            #ELSE if its not the first time in the loop, append the results to the main json_response variable.
            if count == 1:
                json_response = part_json
            else:
                for sub in part_json['results']:
                    json_response['results'].append(sub)
                
            #if we only request the first page, break
            if onlyFirstPage:
                breakLoop=False
                break        

            #if the object contains a next key, and its over 4 chars, it must be a url to the next page, set the path to "next" and then re-run the loop
            if "next" in json_response:
                if not part_json['next'] is None and len(part_json['next']) > 4:
                    if "results" in json_response:
                        path = part_json['next']
                        
                else:
                    break
            
            else:
              break
            
            time.sleep(0.5)

    
    except requests.exceptions.HTTPError as err:
        raise requests.exceptions.HTTPError(
            "An HTTP Error occured while trying to access the Ansible API: " + str(err))      


    
    return json_response
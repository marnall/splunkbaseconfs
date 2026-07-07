
# encoding = utf-8

import os
import sys
import time
import datetime
import csv
import requests
import json
import base64
import fileinput
from urllib.parse import urlsplit
from pprint import pprint
import lxml.etree as ET

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
    global_index = helper.get_global_setting("index")
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

    helper.log_info(helper.context_meta)
    scheme, netloc, _, _, _ = urlsplit(helper.context_meta['server_uri'], allow_fragments=False)
    splunkd_host, splunkd_port = netloc.split(':')
    service = client.connect(scheme=scheme, host=splunkd_host, port=splunkd_port, token=helper.context_meta['session_key'], owner="nobody")
    
    myHostname = service.settings.content['host']   
    queueHandler = helper.get_arg('queue_handler')    

    outputtoindex = helper.get_global_setting("outputtoindex")
    if outputtoindex is None or outputtoindex == "0":
      helper.log_info("OutputToIndex is not enabled, no reason to run this")
      return 0
      
    #get credentials
    towerUser=helper.get_global_setting("ansible_tower_awx_user")
    towerPass=helper.get_global_setting("ansible_tower_awx_pass")
 
    helper.log_info("Found Username: {}".format(towerUser))
    

    data = kvstore(helper,service,"readall")
    
    helper.log_info("Data in keystore to loop though: {}".format(data))
    
    for entry in data:
        try:
          if entry.get('jobId') is None:
            continue

          if queueHandler == "thisServer" and entry['splunkHost'] != myHostname:
            helper.log_info("This event is not for me, this is for {}, skipping this item".format(entry['splunkHost']))
            continue
        
          role = myKvRole(helper,service)
          if queueHandler == "kvCaptain" and role != "KV Store captain":
            helper.log_info("This event is not for me, since im not the kv captain, so skipping this item, im: {}".format(role))
            continue
          
          jobData = {}
          
          if entry.get('templateType') is None:
            entry['templateType'] = 'template'
        
          if entry['templateType'] == "workflow":
            jobData = getWorkflowData(helper, entry['jobId'], towerUser, towerPass)
            
          if entry['templateType'] == "template":
            jobData = getTemplateData(helper, entry['jobId'], towerUser, towerPass)
            
            
            
          if not jobData.get('finished') is None and len(jobData['finished']) > 0:
            
            entry['runStatus'] = jobData['status']
          
            helper.log_info(jobData)
            helper.log_info(entry)
             
            entry['mapId'] = entry['_key']
            del entry['_user']
            del entry['_key']
              
            splunkdata = entry
            splunkdata['status'] = jobData['status']
            splunkdata['finished'] = jobData['finished']
              
            now = datetime.datetime.now()
            splunkdataOut = now.strftime("%d/%m/%Y %H:%M:%S")+" "
            splunkdataOut += ' '.join('{!s}="{}"'.format(key,val) for (key,val) in splunkdata.items())
              
            helper.log_info(splunkdataOut)
             
            kvstore(helper, service, "delete", {'_key': entry['mapId']})
             
            stanza_name = helper.get_input_stanza_names()
            event = helper.new_event(source="TriforkAnsible", index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=splunkdataOut)
              
            w = ew.write_event(event)

        except Exception as e:  
          helper.log_error("Error when looping though item: "+e)
          helper.log_error("Item: "+entry)
        
    helper.log_info("--- Done with loop, see you next time! ---")    
    return 0


def myKvRole(helper,service):
  try:
    data = service.request("/services/kvstore/status", method='GET')
    root = ET.fromstring(data.body.read())
    replicationStatus = root.xpath('//*[local-name()="key" and @name="current"]//*[local-name()="key" and @name="replicationStatus"]/text()')
    return replicationStatus[0]
    
  except Exception as e:
    helper.log_info("Error when trying to get my role from url /services/kvstore/status: {}".format(e))
    return False
        
        
def getWorkflowData(helper, jobId, towerUser, towerPass):
  baseUrl = helper.get_global_setting("ansible_tower_awx_host")
  path = "/api/v2/workflow_jobs/{}/".format(jobId)
  
  userAndPass = towerUser+":"+towerPass;
  userAndPass = base64.b64encode(userAndPass.encode()).decode()
  headers = { 'Authorization' : 'Basic %s' %  userAndPass, 'Content-Type': 'application/json' }

  result = webRequest(helper, baseUrl, path, "GET", headers, None)
    
  return result
  
  
  
        
def getTemplateData(helper, jobId, towerUser, towerPass):
  baseUrl = helper.get_global_setting("ansible_tower_awx_host")
  path = "/api/v2/jobs/{}/".format(jobId)
  
  userAndPass = towerUser+":"+towerPass;
  userAndPass = base64.b64encode(userAndPass.encode()).decode()
  headers = { 'Authorization' : 'Basic %s' %  userAndPass, 'Content-Type': 'application/json' }

  result = webRequest(helper, baseUrl, path, "GET", headers, None)
    
  return result
    
    
    
def kvstore(helper, service, task, data=None):
    collectionName = "ansibleResults"
    
    if not data is None:
      dataOrg = data
      data = json.dumps(data)
      dataJson = json.loads(data)
    

    if not collectionName in service.kvstore:
        service.kvstore.create(collectionName)
    
    collection = service.kvstore[collectionName]

    kvRecord = None
    if task == "readall":
      kvRecord = collection.data.query()
      return kvRecord  
    
    if task == "delete":
      collection.data.delete_by_id(id = dataJson['_key'])
      return 0
    
    try:
      kvRecord = collection.data.query_by_id(dataJson['_key'])
    except Exception as e:
      print ('Found HTTPError: ', e)
    
    if task == "read":
      return kvRecord
        
    if kvRecord == None:
        collection.data.insert(data)
        print('Inserted %s', dataJson['_key'])
    else:
        collection.data.update(id = dataJson['_key'], data = data)
        print('Updated %s', dataJson['_key'])
    
    print("Should have our data: %s" % json.dumps(collection.data.query(), indent=1))
    
    return 0

    

def webRequest(helper,baseUrl,path,method,headers=None,cert=None,onlyFirstPage=True):
 
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
            
            response=helper.send_http_request(baseUrl+path,method,parameters=None, payload=None, headers=headers, cookies=None, verify=verify, cert=cert, timeout=10)
            helper.log_debug("Response: {}".format(response.text))
            
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
                if len(part_json['next']) > 4:
                    if "results" in json_response:
                        path = part_json['next']
                        
                else:
                    break
                
            else:
              break
          
            time.sleep(0.5)

    
    except requests.exceptions.HTTPError as err:
        raise requests.exceptions.HTTPError(
            "An HTTP Error occured while trying to access the CyberArk API: " + str(err))      


    
    return json_response
    

    
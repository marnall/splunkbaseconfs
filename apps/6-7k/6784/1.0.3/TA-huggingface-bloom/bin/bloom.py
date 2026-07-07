### Author: Michael Camp Bentley aka JKat54
### Copyright 2023 Michael Camp Bentley
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###             http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
### SCRIPT NAME: bloom.py
###

import splunk.Intersplunk
import splunk.mining.dcutils as dcu
import traceback
import re
import json
import os,sys
import xml.etree.ElementTree as ET
#add the app's library to the path so we can ship openai and its dependencies with the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "lib"))
from splunklib.client import Service
import requests

# Setup logging/logger
logger = dcu.getLogger()

# Setup namespace
namespace = "TA-huggingface-bloom"

def getConfig(sessionKey):
    try:
        service = Service(token=sessionKey)
        passwords = service.storage_passwords
        response_xml = passwords.get('TA-huggingface-bloom:api_key')["body"]
        root = ET.fromstring(str(response_xml))
        password = root.findall(".//*[@name='clear_password']")[0].text
        return password
        
    except Exception as e:
        stack = traceback.format_exc()
        splunk.Intersplunk.generateErrorResults(str(e))
        logger.error(str(e) + ". Traceback: " + str(stack))

def execute():
    try:
        # get the keywords suplied to the curl command
        argv = splunk.Intersplunk.win32_utf8_argv() or sys.argv

        # for each arg
        first = True
        options = {}
        pattern=re.compile("^\s*([^=]+)=(.*)")
        for arg in argv:
            if first:
                first = False
                continue
            else:
                result = pattern.match(arg)
                options[result.group(1)] = result.group(2)
        
        if 'query' in options:
            query = json.dumps(options['query'])
        else:
            query  = json.dumps("How long has Michael Bentley been a member of the Splunk Trust?")

        if 'model' in options:
            '''
            ref: https://huggingface.co/models 
            '''                
            model = str(options['model'])
        else:
            model = "google/flan-t5-xl"
            
        # additional parameters:
        # ref:https://huggingface.co/docs/api-inference/detailed_parameters

        if 'min_length' in options:
            min_length = int(options['min_length'])
        else:
            min_length = None

        if 'max_length' in options:
            max_length = int(options['max_length'])
        else:
            max_length = None

        if 'top_k' in options:
            top_k = int(options['top_k'])
        else:
            top_k = None

        if 'top_p' in options:
            top_p = float(options['top_p'])
        else:
            top_p = None

        if 'temperature' in options:
            temperature = float(options['temperature'])
            if temperature > 100:
                temperature = 100
        else:
            temperature = 1.0                

        if 'repetition_penalty' in options:
            repetition_penalty = float(options['repetition_penalty'])
            if repetition_penalty > 100:
                repetition_penalty = 100
        else:
            repetition_penalty = None

        if 'max_time' in options:
            max_time = float(options['max_time'])
            if max_time > 120:
                max_time = 120
        else:
            max_time = None

        if 'use_cache' in options:
            use_cache = bool(options['use_cache'])
        else:
            use_cache = True

        if 'wait_for_model' in options:
            wait_for_model = bool(options['wait_for_model'])
        else:
            wait_for_model = True
            
        # get the previous search results and settings
        results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
        sessionKey = settings.get("sessionKey")      
        api_key = getConfig(sessionKey)
        api_url =  "https://api-inference.huggingface.co/models/" + str(model)
        headers = {} 
        headers["Authorization"] = f"Bearer %s" % (api_key)
        response = requests.request("POST", api_url, headers=headers, data=query)
        response = response.content.decode("utf-8")
        results.append({"bloom_query":str(query),"bloom_model":model,"bloom_response":response})
        splunk.Intersplunk.outputResults(results)

    except Exception as e:
        stack = traceback.format_exc()
        splunk.Intersplunk.generateErrorResults(str(e))
        logger.error(str(e) + ". Traceback: " + str(stack))

if __name__ == '__main__':
    execute()

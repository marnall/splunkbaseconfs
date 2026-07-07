### SCRIPT NAME: motd.py
### AUTHOR: Michael Camp Bentley aka JKat54 (JKat54 at datashepherds.com)
### Copyright 2016 Michael Camp Bentley
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###    http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###
### Description: Used as an inline generating search command, this command createsa Message Of The Day (Splunk banner/alert)

import requests
import splunk.Intersplunk 
import splunk.mining.dcutils as dcu

# setup the logger
logger = dcu.getLogger()

def motd(results,options,sessionKey):
 title=None
 message=None
 severity=None
 try:
  if title not in options:
   title="default title"
  if message not in options:
   message="default message"
  if severity not in options:
   severity="info"
  uri = "https://localhost:8089/services/messages/new"
  headers = {'Authorization':''}
  headers['Authorization'] = 'Splunk ' + sessionKey
  data = {'name':options['title'],'value':options['message'],'severity':options['severity']}
  logger.info(data)
  r = requests.post(uri, headers=headers, data=data, verify=False)
  if r.status_code<300:
   logger.info("Status Code: " + str(r.status_code))
   for result in results:
    result["motd"] = "true"
   return results
  else:
   logger.error("Status Code: " + str(r.status_code))
   for result in results:
    result["motd"] = str(r.status_code)	
   return results
 except Exception, e:
  logger.exception(e)
  for result in results:
   result["motd"] = e
  return results

def execute():
  # get the previous search results
  results,dummy,settings = splunk.Intersplunk.getOrganizedResults()
  sessionKey = settings.get("sessionKey")

  # get the keywords and options passed to this command
  keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
  
  # make sure there are 3 options provided
  if len(options) <= 2:
    results = []
    results.append({"error":'syntax: motd title="<title>" message="<message>" severity="<severity>"'})
    results.append({"error":'example: | motd title="TestMessage" message="Heres a message" severity="ERROR"'})  
    splunk.Intersplunk.outputResults(results) 
  # return the previous search results
  else: 
   splunk.Intersplunk.outputResults(motd(results,options,sessionKey)) 
  
if __name__ == '__main__':
    execute()

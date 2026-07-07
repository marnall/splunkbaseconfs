### SCRIPT NAME: webSSL_rest.py
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

import splunk.admin as admin
import os, sys, requests, errno, ConfigParser
import splunk.mining.dcutils as dcu

logger = dcu.getLogger()

class webSSL(admin.MConfigHandler):
  CONF_FILE = 'webSSL'

  def setup(self):
    if self.requestedAction in (admin.ACTION_CREATE,admin.ACTION_EDIT):
      self.supportedArgs.addReqArg("certname")
      self.supportedArgs.addReqArg("cert")
      self.supportedArgs.addReqArg("key")
  
  def handleEdit(self, confInfo):
    if not 'certname' in self.callerArgs.data.keys() and self.callerArgs['certname']:
       raise admin.ArgValidationException, "A certname must be provided"
    if not 'cert' in self.callerArgs.data.keys() and self.callerArgs['cert']:
       raise admin.ArgValidationException, "A cert must be provided"   
    if not 'key' in self.callerArgs.data.keys() and self.callerArgs['key']:
       raise admin.ArgValidationException, "A key must be provided"   
    
    #handle long cert pasted in small field remove header and footer and break spaces into new rows
    certname = self.callerArgs['certname'][0]
    cert = self.callerArgs['cert'][0].replace('-----BEGIN CERTIFICATE-----','').replace('-----END CERTIFICATE-----','').replace(" ","\n")
    key = self.callerArgs['key'][0].replace('-----BEGIN RSA PRIVATE KEY-----','').replace('-----END RSA PRIVATE KEY-----','').replace(" ","\n")

    #set paths for cert & key
    scriptDir = sys.path[0]

    #scriptDir = C:\Program Files\Splunk\bin
    certPath = os.path.join(scriptDir,'..','etc','myauth',certname+'.pem')
    keyPath = os.path.join(scriptDir,'..','etc','myauth',certname+'.key')
    webConfPath = os.path.join(scriptDir,'..','etc','system','local','web.conf')

    #handle myauth/cert folder missing
    if not os.path.exists(os.path.dirname(certPath)):
     try:
      os.makedirs(os.path.dirname(certPath))
     except OSError as exc: 
      if exc.errno != errno.EEXIST:
       raise

    #write cert & key adding header & footer back
    with open(certPath,"w") as f:
     f.write("-----BEGIN CERTIFICATE-----" + cert + "-----END CERTIFICATE-----")	
    with open(keyPath,"w") as f:
     f.write("-----BEGIN RSA PRIVATE KEY-----" + key + "-----END RSA PRIVATE KEY-----")

    #modify & write web.conf
    try:
     config = ConfigParser.RawConfigParser()
     config.optionxform = str
     config.read(webConfPath)
     if not config.has_section("settings"):
      config.add_section("settings")
     config.set("settings","enableSplunkWebSSL",True)
     config.set("settings","caCertPath",certPath)
     config.set("settings","privKeyPath",keyPath)
     with open(webConfPath,"wb") as confFile:
      config.write(confFile)
    except Exception as e:
     logging.error(e)

    #prompt user to restart splunk web
    sessionKey=self.getSessionKey()
    headers = {'Authorization':''}
    headers['Authorization'] = 'Splunk ' + sessionKey  
    data = {'name':'restart_link','value':'Splunk must be restarted for changes to take effect.  [[/manager/search/control| Click here to restart from the Manager.]]','severity':'warn'}
    r = requests.post("https://localhost:8089/services/messages/new", headers=headers, data=data, verify=False)
    data = {'name':'restart_reason','value':'A user triggered the create action on app ssl_installer, and the following objects required a restart: ssl configuration','severity':'warn'}
    r = requests.post("https://localhost:8089/services/messages/new", headers=headers, data=data, verify=False)
    pass

  def handleList(self, confInfo):
   confDict = self.readConf(self.CONF_FILE)
   if None != confDict:
    for stanza, settings in confDict.items():
     for key, val in settings.items():
      if val is None:
       confInfo[stanza].append(key, "")
      else:
       confInfo[stanza].append(key, val)
                    
    
  def handleReload(self, confInfo):
    pass

admin.init(webSSL, admin.CONTEXT_NONE)

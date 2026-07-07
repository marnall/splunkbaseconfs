#   Copyright 2011 Splunk, Inc.                                                                       
#                                                                                                        
#   Licensed under the Apache License, Version 2.0 (the "License");                                      
#   you may not use this file except in compliance with the License.                                     
#   You may obtain a copy of the License at                                                              
#                                                                                                        
#       http://www.apache.org/licenses/LICENSE-2.0                                                       
#                                                                                                        
#   Unless required by applicable law or agreed to in writing, software                                  
#   distributed under the License is distributed on an "AS IS" BASIS,                                    
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.                             
#   See the License for the specific language governing permissions and                                  
#   limitations under the License.    

from __future__ import unicode_literals
import logging
import splunk.admin as admin
import splunk.entity as en
import os
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from io import open

logger = logging.getLogger('splunk')

BASE_DIR = make_splunkhome_path(["etc","apps","SA-cbquery"])
CONF_FILE = 'credentials'
PROTECTION_FILE = os.path.join(BASE_DIR,'bin','.carbonblack','credentials.protection')
RESPONSE_FILE = os.path.join(BASE_DIR,'bin','.carbonblack','credentials.response')
DEFENSE_FILE = os.path.join(BASE_DIR,'bin','.carbonblack','credentials.defense')

class CbAPIQueryHandler(admin.MConfigHandler):
    cb_args = ("protection_url", "protection_token", "protection_ssl_verify",
               "response_url","response_token","response_ssl_verify",
               "defense_url","defense_token","defense_ssl_verify")

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            #for arg in ['url', 'token', 'ssl_verify']:
            for arg in self.cb_args:
                self.supportedArgs.addOptArg(arg)


    def handleList(self, confInfo):
        # reads file from CONF_FILE
        confDict = self.readConf(CONF_FILE)
        if None != confDict:
            for stanza, settings in list(confDict.items()):
                for key, val in list(settings.items()):
                    if key in ['protection_ssl_verify', 'response_ssl_verify', 'defense_ssl_verify']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    if key in ['protection_url', 'response_url', 'defense_url'] and val in [None,'']:
                        val = ''
                    if key in ['protection_token', 'response_token', 'defense_token'] and val in [None,'']:
                        val = ''
                    confInfo[stanza].append(key, val)


    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs
        

        if int(self.callerArgs.data['protection_ssl_verify'][0]) == 1:
            self.callerArgs.data['protection_ssl_verify'][0] = '1'
        else:
            self.callerArgs.data['protection_ssl_verify'][0] = '0'
        if int(self.callerArgs.data['response_ssl_verify'][0]) == 1:
            self.callerArgs.data['response_ssl_verify'][0] = '1'
        else:
            self.callerArgs.data['response_ssl_verify'][0] = '0'
        if int(self.callerArgs.data['defense_ssl_verify'][0]) == 1:
            self.callerArgs.data['defense_ssl_verify'][0] = '1'
        else:
            self.callerArgs.data['defense_ssl_verify'][0] = '0'

        if self.callerArgs.data['protection_url'][0] in [None, '']:
            self.callerArgs.data['protection_url'][0] = ''
        if self.callerArgs.data['response_url'][0] in [None, '']:
            self.callerArgs.data['response_url'][0] = ''
        if self.callerArgs.data['defense_url'][0] in [None, '']:
            self.callerArgs.data['defense_url'][0] = ''

        if self.callerArgs.data['protection_token'][0] in [None, '']:
            self.callerArgs.data['protection_token'][0] = ''
        if self.callerArgs.data['response_token'][0] in [None, '']:
            self.callerArgs.data['response_token'][0] = ''
        if self.callerArgs.data['defense_token'][0] in [None, '']:
            self.callerArgs.data['defense_token'][0] = ''

        self.writeConf(CONF_FILE, 'default', self.callerArgs.data)

        #make sure the dir is created if is not
        dir = os.path.dirname(PROTECTION_FILE)
        if not os.path.exists(dir):
            os.makedirs(dir)

        #create the real credential file used by the cbapi
        f = open(PROTECTION_FILE, 'w')
        f.write('[default]\n')
        f.write('url = ' + self.callerArgs.data['protection_url'][0] + '\n')
        f.write('token = ' + self.callerArgs.data['protection_token'][0] + '\n')
        if int(self.callerArgs.data['protection_ssl_verify'][0]) == 1:
            f.write('ssl_verify = true')
        else:
            f.write('ssl_verify = false')
        f.close
        f = open(RESPONSE_FILE, 'w')
        f.write('[default]\n')
        f.write('url = ' + self.callerArgs.data['response_url'][0] + '\n')
        f.write('token = ' + self.callerArgs.data['response_token'][0] + '\n')
        if int(self.callerArgs.data['response_ssl_verify'][0]) == 1:
            f.write('ssl_verify = true')
        else:
            f.write('ssl_verify = false')
        f.close
        f = open(DEFENSE_FILE, 'w')
        f.write('[default]\n')
        f.write('url = ' + self.callerArgs.data['defense_url'][0] + '\n')
        f.write('token = ' + self.callerArgs.data['defense_token'][0] + '\n')
        if int(self.callerArgs.data['defense_ssl_verify'][0]) == 1:
            f.write('ssl_verify = true')
        else:
            f.write('ssl_verify = false')
        f.close

# initialize the handler
admin.init(CbAPIQueryHandler, admin.CONTEXT_NONE) 

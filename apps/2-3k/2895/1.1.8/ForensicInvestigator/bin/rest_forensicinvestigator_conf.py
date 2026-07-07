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

import logging
import splunk.admin as admin
import splunk.entity as en
import xml.etree.cElementTree as et
import lxml.etree as ET
import re
import os
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

logger = logging.getLogger('splunk')

BASE_DIR = make_splunkhome_path(["etc","apps","ForensicInvestigator"])
CONF_FILE = 'forensicinvestigator'

#take Windows OS path into considerations
#NAV_FILE = BASE_DIR + '/default/data/ui/nav/default.xml'
#NAV_OUTPUT = BASE_DIR + '/local/data/ui/nav/default.xml'

#adjusted for windows path
NAV_FILE = os.path.join(BASE_DIR,'default','data','ui','nav','default.xml')
NAV_OUTPUT = os.path.join(BASE_DIR,'local','data','ui','nav','default.xml')

#make a etree element of the navigation file
tree = ET.parse(NAV_FILE)
root = tree.getroot()

class ForensicInvestigatorHandler(admin.MConfigHandler):


    def setup(self):


        if self.requestedAction == admin.ACTION_EDIT:
              for arg in ['MIR']:
                self.supportedArgs.addOptArg(arg)
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ["vt_api_key"]:
                self.supportedArgs.addOptArg(arg)
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ["proxy_enabled"]:
                self.supportedArgs.addOptArg(arg)
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ["http_proxy"]:
                self.supportedArgs.addOptArg(arg)
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ["https_proxy"]:
                self.supportedArgs.addOptArg(arg)



    def handleList(self, confInfo):
    # reads file from CONF_FILE
        confDict = self.readConf(CONF_FILE)
        if None != confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in ['MIR']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    if key in ['vt_api_key'] and val in [None,'']:
                        val = ''
                    confInfo[stanza].append(key, val)


    def handleEdit(self, confInfo):

        name = self.callerArgs.id
        args = self.callerArgs

        if int(self.callerArgs.data['MIR'][0]) == 1:
            self.callerArgs.data['MIR'][0] = '1'
        else:
            self.callerArgs.data['MIR'][0] = '0'
            for panels in root:
                for dashboard in panels:
                    dash = dashboard.attrib
                    for v in dash.values():
                        if re.match('mir*',v):
                            panels.remove(dashboard)

        if self.callerArgs.data['vt_api_key'][0] in [None, '']:
            self.callerArgs.data['vt_api_key'][0] = ''

        if self.callerArgs.data['proxy_enabled'][0] in [None, '']:
            self.callerArgs.data['proxy_enabled'][0] = ''


        if self.callerArgs.data['http_proxy'][0] in [None, '']:
            self.callerArgs.data['http_proxy'][0] = ''

        if self.callerArgs.data['https_proxy'][0] in [None, '']:
            self.callerArgs.data['https_proxy'][0] = ''


        self.writeConf('forensicinvestigator', 'setupentity', self.callerArgs.data)
        #make sure the dir is created if is not


        dir = os.path.dirname(NAV_OUTPUT)

        if not os.path.exists(dir):
            os.makedirs(dir)

        tree.write(NAV_OUTPUT)


# initialize the handler
admin.init(ForensicInvestigatorHandler, admin.CONTEXT_NONE) 



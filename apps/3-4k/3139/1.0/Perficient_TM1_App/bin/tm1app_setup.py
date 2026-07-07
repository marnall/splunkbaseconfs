import splunk.admin as admin
import splunk.entity as en
import splunk.auth as auth
import sys
import re
import shutil
import json
from sys import platform as _platform
import os.path
import os
import errno
import subprocess
from splunk.clilib import cli_common as cli
import urllib, urllib2
from xml.dom import minidom
import xml.etree.ElementTree as ET
import splunk.Intersplunk


class ConfigApp(admin.MConfigHandler):
  appName = 'Perficient_TM1_App'

  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['tm1_index_name']:
        self.supportedArgs.addOptArg(arg)
        
  def handleList(self, confInfo):
    confDict = self.readConf("tm1app_setup")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          if key in ['tm1_index_name'] and val in [None, '']:
            val = ''
          confInfo[stanza].append(key, val)
  
  def make_sure_path_exists(self, path):
    try:
      os.makedirs(path)
    except OSError as exception:
      if exception.errno != errno.EEXIST:
        raise
  

# This function needs an additional logic statement to prevent it from running in the event that the index name has changed via setup.  User should remove local dir before rerunning setup
  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs
    for key in self.callerArgs.keys():
      if self.callerArgs.data[key][0] in [None, '']:
        self.callerArgs.data.pop(key)
    self.writeConf('tm1app_setup', 'tm1app_parameters', self.callerArgs.data)
    if 'tm1_index_name' in self.callerArgs.keys():
      session_key = self.getSessionKey()
      base_url = 'https://localhost:8089'
      endpoint = '/servicesNS/nobody/Perficient_TA_TM1/admin/macros'
      confInput = self.readConf("macros")
      for stanza, settings in confInput.items():
        origStanza = stanza
        macro = 'tm1_index'
        macroBase = '''index='''
        try:
          if re.search(r'index=tm1', settings['definition']) is not None:
            newStanza = stanza
            settings['definition'] = re.sub(r'tm1', self.callerArgs.data['tm1_index_name'][0], settings['definition'])
            self.writeConf('macros', newStanza, settings)
        except:
          nothing = 0
          
    self.restartRequired=True
    session_key = self.getSessionKey()
    base_url = 'https://localhost:8089'
    endpoint = '/services/messages'
    payload = { 'name':'tm1_restart','severity':'warn','value':'Splunk restart required to complete TM1 Dashboard installation.' }
    headers = { 'Authorization': ('Splunk %s' %session_key)}
    r = urllib2.Request(base_url + endpoint, data = urllib.urlencode(payload), headers=headers)
    results = urllib2.urlopen(r)
    
admin.init(ConfigApp, admin.CONTEXT_NONE)

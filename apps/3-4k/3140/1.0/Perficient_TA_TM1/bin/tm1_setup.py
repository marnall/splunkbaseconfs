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
  appName = 'Perficient_TA_TM1'

  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['data_location', 'use_forwarder_bool', 'windows_splunk_dir', 'tm1_index_name', 'eventgen_bool']:
        self.supportedArgs.addOptArg(arg)
        
  def handleList(self, confInfo):
    confDict = self.readConf("tm1_setup")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          if key in ['data_location', 'tm1_index_name', 'windows_splunk_dir'] and val in [None, '']:
            val = ''
          if key in ['use_forwarder_bool']:
            if int(val) == 1:
              val = '1'
            else:
              val = '0'
          if key in ['eventgen_bool']:
            if int(val) == 1:
              val = '1'
            else:
              val = '0'
          confInfo[stanza].append(key, val)
  
  def make_sure_path_exists(self, path):
    try:
      os.makedirs(path)
    except OSError as exception:
      if exception.errno != errno.EEXIST:
        raise
  
  def createTAApp(self):
    targetFolder = 'Perficient_TA_TM1_FWD'
    if _platform == 'win32':
      confDict = self.readConf("tm1_setup")
      slash = '\\'
      for stanza, settings in confDict.items():
        if stanza == 'tm1_parameters':
          appsDir = settings['windows_splunk_dir'] + '\\Splunk\\etc\\apps'
          dir = appsDir + slash + self.appName + '\\appserver\\addons'
    else:
      slash = '/'
      homeDir = os.environ.get('SPLUNK_HOME')
      appsDir = homeDir + '/etc/apps'
      dir = appsDir + slash + self.appName + '/appserver/addons'

    self.make_sure_path_exists(dir + slash + targetFolder)
    for source in ['local', 'default']:
      self.make_sure_path_exists(dir + slash + targetFolder + slash + source)
      for sourceFile in ['app.conf', 'inputs.conf']:
        src = appsDir + slash + self.appName + slash + source + slash + sourceFile
        tgt = dir + slash + targetFolder + slash + source + slash + sourceFile
        if os.path.isfile(src):
          shutil.copyfile(src, tgt)


  def createSAApp(self):
    targetFolder = 'Perficient_SA_TM1_IDX'
    if _platform == 'win32':
      confDict = self.readConf("tm1_setup")
      slash = '\\'
      for stanza, settings in confDict.items():
        if stanza == 'tm1_parameters':
          appsDir = settings['windows_splunk_dir'] + '\\Splunk\\etc\\apps'
          dir = appsDir + slash + self.appName + '\\appserver\\addons'
    else:
      slash = '/'
      homeDir = os.environ.get('SPLUNK_HOME')
      appsDir = homeDir + '/etc/apps'
      dir = appsDir + slash + self.appName + '/appserver/addons'

    self.make_sure_path_exists(dir + slash + targetFolder)
    for source in ['local', 'default']:
      self.make_sure_path_exists(dir + slash + targetFolder + slash + source)
      for sourceFile in ['indexes.conf','props.conf']:
        src = appsDir + slash + self.appName + slash + source + slash + sourceFile
        tgt = dir + slash + targetFolder + slash + source + slash + sourceFile
        if os.path.isfile(src):
          shutil.copyfile(src, tgt)


  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs
    # modify tm1_setup.conf
    # skip any variables without data
    for key in self.callerArgs.keys():
      if self.callerArgs.data[key][0] in [None, '']:
        self.callerArgs.data.pop(key)
    # handle a '\' or '/' at the end of the data location
    if 'data_location' in self.callerArgs.keys():
      if self.callerArgs.data['data_location'][0][-1:] in ['\\','/']:
        self.callerArgs.data['data_location'][0] = self.callerArgs.data['data_location'][0][:-1]

    # handle a '\' or '/' at the end of the Windows Splunk directory
    if 'windows_splunk_dir' in self.callerArgs.keys():
      if self.callerArgs.data['windows_splunk_dir'][0][-1:] in ['\\','/']:
        self.callerArgs.data['windows_splunk_dir'][0] = self.callerArgs.data['windows_splunk_dir'][0][:-1]
    # standardize boolean values
    if int(self.callerArgs.data['use_forwarder_bool'][0]) == 1:
      self.callerArgs.data['use_forwarder_bool'][0] = '1'
    else:
      self.callerArgs.data['use_forwarder_bool'][0] = '0'
    if int(self.callerArgs.data['eventgen_bool'][0]) == 1:
      self.callerArgs.data['eventgen_bool'][0] = '1'
    else:
      self.callerArgs.data['eventgen_bool'][0] = '0'

    # write settings to tm1_setup.conf
    self.writeConf('tm1_setup', 'tm1_parameters', self.callerArgs.data)

    
    # modify inputs.conf
    if 'data_location' in self.callerArgs.keys():
      confInput = self.readConf("inputs")
      for stanza, settings in confInput.items():
        origStanza = stanza
        serverlog = '''SETUP_INPUTS/.../tm1server.log'''
        processerror = '''SETUP_INPUTS/.../TM1ProcessError*.log'''
        tm1 = '''SETUP_INPUTS/.../tm1s.cfg'''

        # change the monitored directories
        if ( stanza.find(serverlog) > 0 or stanza.find(processerror) > 0 or stanza.find(tm1) > 0 ) and ( 'data_location' in self.callerArgs.keys() ):
          dataLoc = self.callerArgs.data['data_location'][0]
          if stanza.find('SETUP_INPUTS') >= 0:
            if dataLoc.find('\\') >= 0:
              newStanza = stanza.replace('/SETUP_INPUTS',self.callerArgs.data['data_location'][0])
              newStanza = newStanza.replace('/','\\')
              newStanza = newStanza.replace('monitor:\\\\','monitor://')
            else:
              newStanza = stanza.replace('/SETUP_INPUTS',self.callerArgs.data['data_location'][0])

            settings['index'] = self.callerArgs.data['tm1_index_name'][0]
            if self.callerArgs.data['use_forwarder_bool'][0] == '1':
              settings['disabled'] = '1'
            else:
              settings['disabled'] = '0'
            settings.pop('_rcvbuf', None)
            settings.pop('evt_resolve_ad_obj', None)
            settings.pop('host', None)
            self.writeConf('inputs', newStanza, settings)
          else:
            pass


    if 'tm1_index_name' in self.callerArgs.keys():
      session_key = self.getSessionKey()
      base_url = 'https://localhost:8089'
      endpoint = '/servicesNS/nobody/Perficient_TA_TM1/admin/indexes'
      confInput = self.readConf("indexes")
      for stanza, settings in confInput.items():
        origStanza = stanza
        index = 'tm1'
        splunkHomeVar = '''$SPLUNK_DB'''
        coldPathEnd = 'colddb'
        homePathEnd = 'db'
        thawedPathEnd = 'thaweddb'
        slash = '''/'''
        try:
          if re.search(r'SPLUNK_DB\/tm1\/db', settings['homePath']) is not None:
            #  there is proably a better way of doing this, but this prevents dragging over all of the default values over
            # into the new indexes.conf file in local
            settings.pop('assureUTF8', None)
            settings.pop('bucketRebuildMemoryHint', None)
            settings.pop('coldPath.maxDataSizeMB', None)
            settings.pop('compressRawdata', None)
            settings.pop('defaultDatabase', None)
            settings.pop('enableOnlineBucketRepair', None)
            settings.pop('enableRealtimeSearch', None)
            settings.pop('frozenTimePeriodInSecs', None)
            settings.pop('homePath.maxDataSizeMB', None)
            settings.pop('indexThreads', None)
            settings.pop('maxBloomBackfillBucketAge', None)
            settings.pop('maxBucketSizeCacheEntries', None)
            settings.pop('maxConcurrentOptimizes', None)
            settings.pop('maxDataSize', None)
            settings.pop('maxHotBuckets', None)
            settings.pop('maxHotIdleSecs', None)
            settings.pop('maxHotSpanSecs', None)
            settings.pop('maxMemMB', None)
            settings.pop('maxMetaEntries', None)
            settings.pop('maxRunningProcessGroups', None)
            settings.pop('maxRunningProcessGroupsLowPriority', None)
            settings.pop('maxTimeUnreplicatedNoAcks', None)
            settings.pop('maxTimeUnreplicatedWithAcks', None)
            settings.pop('maxTotalDataSizeMB', None)
            settings.pop('maxWarmDBCount', None)
            settings.pop('memPoolMB', None)
            settings.pop('minRawFileSyncSecs', None)
            settings.pop('partialServiceMetaPeriod', None)
            settings.pop('processTrackerServiceInterval', None)
            settings.pop('quarantineFutureSecs', None)
            settings.pop('quarantinePastSecs', None)
            settings.pop('rawChunkSizeBytes', None)
            settings.pop('repFactor', None)
            settings.pop('rotatePeriodInSecs', None)
            settings.pop('serviceMetaPeriod', None)
            settings.pop('serviceOnlyAsNeeded', None)
            settings.pop('serviceSubtaskTimingPeriod', None)
            settings.pop('sync', None)
            settings.pop('syncMeta', None)
            settings.pop('throttleCheckPeriod', None)
            settings.pop('tstatsHomePath', None)
            # after popping out the unecessary values, set the new stanza name to what is defined by the user in the setup page
            newStanza = stanza.replace('tm1',self.callerArgs.data['tm1_index_name'][0])
            # replace the values in homepath, thawedpath, coldpath with the new index name
            settings['homePath'] = re.sub(r'tm1', self.callerArgs.data['tm1_index_name'][0], settings['homePath'])
            settings['thawedPath'] = re.sub(r'tm1', self.callerArgs.data['tm1_index_name'][0], settings['thawedPath'])
            settings['coldPath'] = re.sub(r'tm1', self.callerArgs.data['tm1_index_name'][0], settings['coldPath'])
            # write out the new config file for indexes into local
            self.writeConf('indexes', newStanza, settings)
        except:
          nothing = 0

      #Turn eventgen stanza on if user selects demo mode
      if self.callerArgs.data['eventgen_bool'][0] == '1':
        session_key = self.getSessionKey()
        base_url = 'https://localhost:8089'
        endpoint = '/servicesNS/nobody/Perficient_TA_TM1/admin/eventgen'
        confInput = self.readConf('eventgen')
        samples = '''tm1lab'''
        ignore = '''global'''
        for stanza, settings in confInput.items():
          origStanza = stanza
          if re.search(r'tm1lab', origStanza) is not None:
            try:
              if re.search(r'\w+', settings['disabled']) is not None:
                settings['disabled'] = 'false'
                self.writeConf('eventgen', origStanza, settings)
            except:
              nothing = 0


    # Create the folder and files that will be used for the TA app
    self.createTAApp()
    self.createSAApp()
    self.restartRequired=True

    # create banner message alerting user Splunk requires a manual restart
    session_key = self.getSessionKey()
    base_url = 'https://localhost:8089'
    endpoint = '/services/messages'
    payload = { 'name':'tm1_restart','severity':'warn','value':'Splunk restart required to complete TM1 TA installation.' }
    headers = { 'Authorization': ('Splunk %s' %session_key)}
    r = urllib2.Request(base_url + endpoint, data = urllib.urlencode(payload), headers=headers)
    results = urllib2.urlopen(r)
    
admin.init(ConfigApp, admin.CONTEXT_NONE)
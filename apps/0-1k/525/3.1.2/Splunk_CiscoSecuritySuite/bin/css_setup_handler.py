import splunk.admin as admin
import splunk.entity as en
import os
import re
import platform
import xml.etree.ElementTree as ET
import splunklib.client as client
import splunklib.results as results
import json
#from subprocess import call
# import your required python modules

'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values 
      corresponds to handleractions = edit in restmap.conf

'''

class ConfigApp(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['asa', 'esa', 'ise', 'ips', 'wsa', 'csf', 'not_indexed_ta']:
        self.supportedArgs.addOptArg(arg)

  '''
  Read the initial values of the parameters from the custom file
      css_views.conf, and write them to the setup screen.

  If the app has never been set up,
      uses .../<appname>/default/css_views.conf.

  If app has been set up, looks at
      .../local/css_views.conf first, then looks at
  .../default/css_views.conf only if there is no value for a field in
      .../local/css_views.conf

  For text fields, if the conf file says None, set to the empty string.
  '''

  def handleList(self, confInfo):
    confDict = self.readConf('css_views')
    if confDict is not None:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          if key in ['asa', 'esa', 'ise', 'ips', 'wsa', 'csf']:
            if int(val) == 1:
              val = '1'
            else:
              val = '0'
          confInfo[stanza].append(key, val)


    service = client.Service(token=self.getSessionKey())
    jobs = service.jobs
    info = dict()
    info['asa_count'] = 0
    info['esa_count'] = 0
    info['ise_count'] = 0
    info['ips_count'] = 0
    info['wsa_count'] = 0
    info['csf_count'] = 0

    job = jobs.oneshot('search sourcetype=cisco:asa OR sourcetype=cisco:fwsm OR sourcetype=cisco:pix | head 1 | stats count')
    reader = results.ResultsReader(job)
    for item in reader:
     info['asa_count'] = item['count']
     break

    job = jobs.oneshot('search sourcetype=cisco:esa:authentication OR sourcetype=cisco:esa:http OR sourcetype=cisco:esa:textmail | head 1 | stats count')
    reader = results.ResultsReader(job)
    for item in reader:
     info['esa_count'] = item['count']
     break

    job = jobs.oneshot('search sourcetype=cisco:ise:syslog | head 1 | stats count')
    reader = results.ResultsReader(job)
    for item in reader:
     info['ise_count'] = item['count']
     break

    job = jobs.oneshot('search sourcetype=cisco:ips:syslog | head 1 | stats count')
    reader = results.ResultsReader(job)
    for item in reader:
     info['ips_count'] = item['count']
     break

    job = jobs.oneshot('search sourcetype=cisco:wsa:squid OR sourcetype=cisco:wsa:w3c OR sourcetype=cisco:wsa:l4tm | head 1 | stats count')
    reader = results.ResultsReader(job)
    for item in reader:
     info['wsa_count'] = item['count']
     break

    job = jobs.oneshot('search sourcetype=estreamer OR sourcetype=client_check | head 1 | stats count')
    reader = results.ResultsReader(job)
    for item in reader:
     info['csf_count'] = item['count']
     break

    confInfo['default'].append('not_indexed_ta', json.dumps(info))

  '''
  After user clicks Save on setup screen, take updated parameters,
  normalize them, and save them somewhere
  '''
  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs

    if int(self.callerArgs.data['asa'][0]) == 1:
     self.callerArgs.data['asa'][0] = '1'
    else:
     self.callerArgs.data['asa'][0] = '0'

    if int(self.callerArgs.data['esa'][0]) == 1:
     self.callerArgs.data['esa'][0] = '1'
    else:
     self.callerArgs.data['esa'][0] = '0'

    if int(self.callerArgs.data['ise'][0]) == 1:
     self.callerArgs.data['ise'][0] = '1'
    else:
     self.callerArgs.data['ise'][0] = '0'

    if int(self.callerArgs.data['ips'][0]) == 1:
     self.callerArgs.data['ips'][0] = '1'
    else:
     self.callerArgs.data['ips'][0] = '0'

    if int(self.callerArgs.data['wsa'][0]) == 1:
     self.callerArgs.data['wsa'][0] = '1'
    else:
     self.callerArgs.data['wsa'][0] = '0'

    if int(self.callerArgs.data['csf'][0]) == 1:
     self.callerArgs.data['csf'][0] = '1'
    else:
     self.callerArgs.data['csf'][0] = '0'

    SPLUNK_HOME = os.environ['SPLUNK_HOME']

    app_file = os.path.join(SPLUNK_HOME, 'etc', 'apps', 'Splunk_CiscoSecuritySuite', 'local', 'app.conf')
    if (os.path.exists(app_file)):
      f = open(app_file,"w")
      f.write("")
      f.close()

    nav_path_default = os.path.join(SPLUNK_HOME, 'etc', 'apps', 'Splunk_CiscoSecuritySuite', 'default', 'data', 'ui', 'nav')
    nav_path_local   = os.path.join(SPLUNK_HOME, 'etc', 'apps', 'Splunk_CiscoSecuritySuite', 'local', 'data', 'ui', 'nav')

    if not os.path.exists(nav_path_local):
      os.makedirs(nav_path_local)

    tree = ET.parse(os.path.join(nav_path_default, 'default.xml'))
    root = tree.getroot()

    # Remove ASA views if not selected
    if self.callerArgs.data['asa'][0] == '0':
        for collection in root.findall('collection'):
            label = collection.get('label')

            # ASA views are in the 'Network Security' collection
            if label == "Network Security":
                for view in collection.findall('view'):
                    name = view.get('name')
                    if name in ['asa_overview', 'asa_search']:
                        collection.remove(view)

    # Remove ESA views if not selected
    if self.callerArgs.data['esa'][0] == '0':
        for collection in root.findall('collection'):
            label = collection.get('label')
            if label == 'Email Security':
                root.remove(collection)

    # Remove IPS views if not selected
    if self.callerArgs.data['ips'][0] == '0':
        for collection in root.findall('collection'):
            label = collection.get('label')

            # ASA views are in the 'Network Security' collection
            if label == "Network Security":
                for view in collection.findall('view'):
                    name = view.get('name')
                    if name in ['ips_overview', 'ips_analyst', 'ips_global_threats']:
                        collection.remove(view)

    # Remove ISE views if not selected
    if self.callerArgs.data['ise'][0] == '0':
        for collection in root.findall('collection'):
            label = collection.get('label')
            if label == 'Identity Services':
                root.remove(collection)

    # Remove Sourcefire views if not selected
    if self.callerArgs.data['csf'][0] == '0':
        for collection in root.findall('collection'):
            label = collection.get('label')

            # Sourcefire view collection is in the 'Network Security' collection
            if label == "Network Security":
                for ns_collection in collection.findall('collection'):
                    ns_label = ns_collection.get('label')
                    if ns_label == "Sourcefire IPS IDS":
                        collection.remove(ns_collection)

    # Remove WSA views if not selected
    if self.callerArgs.data['wsa'][0] == '0':
        for collection in root.findall('collection'):
            label = collection.get('label')
            if label == 'Web Security':
                root.remove(collection)


    with open(os.path.join(nav_path_local, 'default.xml'), 'w+'):
        tree.write(os.path.join(nav_path_local, 'default.xml'))

    self.writeConf('css_views', 'default', self.callerArgs.data)

    # Refresh the nav endpoint so that our changes take effect
    nav_entity = en.getEntities('data/ui/nav/_reload', sessionKey = self.getSessionKey(), namespace='Splunk_CiscoSecuritySuite', owner='admin')

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)

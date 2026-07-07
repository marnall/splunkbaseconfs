import splunk.admin as admin
import splunk.entity as en
import socket
import splunk.mining.dcutils as dcu
logger = dcu.getLogger()

# Example logging statement: logger.error('Hello World')

'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values
      corresponds to handleractions = edit in restmap.conf

'''

# Inject this value in build
cloud = False

class ConfigApp(admin.MConfigHandler):
  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['schema', 'hostname', 'port', 'debug']:
        self.supportedArgs.addOptArg(arg)

  def handleList(self, confInfo):
    confDict = self.readConf("2steps")

    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          if key in ['debug']:
            if int(val) == 0:
              val = '0'
            else:
              val = '1'
          if key in ['schema']:
            if int(val) == 0:
              val = '0'
            else:
              val = '1'
          if key in ['hostname'] and val in [None, '']:
            val = socket.gethostname()
          if key in ['port'] and val in [None, '']:
            val = "5000"
          confInfo[stanza].append(key, val)

  def handleEdit(self, confInfo):
    args = self.callerArgs

    if int(args.data['debug'][0]) == 0:
      args.data['debug'][0] = '0'
    else:
      args.data['debug'][0] = '1'

    if not cloud and int(args.data['schema'][0]) == 0:
      args.data['schema'][0] = '0'
    else:
      args.data['schema'][0] = '1'

    if args.data['hostname'][0] in [None, '']:
      args.data['hostname'][0] = socket.gethostname()

    if args.data['port'][0] in [None, '']:
      args.data['port'][0] = "5000"

    self.writeConf('2steps', 'twostepsstandard', self.callerArgs.data)

admin.init(ConfigApp, admin.CONTEXT_NONE)

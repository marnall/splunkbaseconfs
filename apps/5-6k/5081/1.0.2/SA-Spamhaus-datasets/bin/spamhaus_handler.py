import splunk.admin as admin
import splunk.entity as en
 
class ConfigApp(admin.MConfigHandler):
   def setup(self):
      if self.requestedAction == admin.ACTION_EDIT:
        for arg in ['token', 'proxy_enabled', 'proxy_address', 'proxy_port', 'proxy_https', 'proxy_user', 'proxy_passw']:
          self.supportedArgs.addOptArg(arg)
      pass
 
   def handleList(self, confInfo):
     confDict = self.readConf("spamhaus_setup")
     if None != confDict:
       for stanza, settings in confDict.items():
         for key, val in settings.items():
           if key in ['token'] and val in [None, '']:
             val = ''
           if key in ['proxy_enabled'] and val in [None, '']:
             val = ''
           if key in ['proxy_address'] and val in [None, '']:
             val = ''
           if key in ['proxy_port'] and val in [None, '']:
             val = ''
           if key in ['proxy_https'] and val in [None, '']:
             val = ''
           if key in ['proxy_user'] and val in [None, '']:
             val = ''
           if key in ['proxy_passw'] and val in [None, '']:
             val = ''
           confInfo[stanza].append(key, val)
 
   def handleEdit(self, confInfo):
     name = self.callerArgs.id
     args = self.callerArgs

     if self.callerArgs.data['token'][0] in [None, '']:
            self.callerArgs.data['token'][0] = ''
     if self.callerArgs.data['proxy_enabled'][0] in [None, '']:
            self.callerArgs.data['proxy_enabled'][0] = ''
     if self.callerArgs.data['proxy_address'][0] in [None, '']:
            self.callerArgs.data['proxy_address'][0] = ''
     if self.callerArgs.data['proxy_port'][0] in [None, '']:
            self.callerArgs.data['proxy_port'][0] = ''
     if self.callerArgs.data['proxy_https'][0] in [None, '']:
            self.callerArgs.data['proxy_https'][0] = ''
     if self.callerArgs.data['proxy_user'][0] in [None, '']:
            self.callerArgs.data['proxy_user'][0] = ''
     if self.callerArgs.data['proxy_passw'][0] in [None, '']:
            self.callerArgs.data['proxy_passw'][0] = ''
     
     self.writeConf('spamhaus_setup', 'app_config', self.callerArgs.data)
 
admin.init(ConfigApp, admin.CONTEXT_NONE)
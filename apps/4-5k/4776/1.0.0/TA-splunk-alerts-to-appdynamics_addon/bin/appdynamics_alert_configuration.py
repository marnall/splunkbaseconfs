import splunk
import splunk.admin as admin

class ConfigApp(admin.MConfigHandler):
    
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['appdynamics_url', 'access_token']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        confDict = self.readConf("appdynamics_alert")
        if confDict is not None:
            configurations = confDict.get('appdynamics_alert')
            for key, val in configurations.items():
                confInfo['appdynamics_alert'].append(key, val)

    def handleEdit(self, confInfo):
        args = self.callerArgs.data
        for key, val in args.items():
            if val[0] is None:
                val[0] = ''

        appdynamics_url = args['appdynamics_url'][0]
        access_token = args['access_token'][0]
        
        self.writeConf('appdynamics_alert', 'appdynamics_alert', self.callerArgs.data)
        
        splunk.rest.simpleRequest("/services/apps/local/_reload", self.getSessionKey(), postargs=None, method='POST', timeout=180)
        
# intialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
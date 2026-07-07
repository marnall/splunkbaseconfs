import splunk.admin as admin
import splunk.entity as en
 
class ConfigApp(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for myarg in ['host', 'url', 'country']:
                self.supportedArgs.addOptArg(myarg)
 
    def handleList(self, confInfo):
        confDict = self.readConf("climatesetup")
        if None != confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in ['host', 'url', 'country'] and val in [None, '']:
                        val = ''
                    confInfo[stanza].append(key, val)
 
    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs
        self.writeConf('climatesetup', 'climate_config', self.callerArgs.data)
 
admin.init(ConfigApp, admin.CONTEXT_NONE)

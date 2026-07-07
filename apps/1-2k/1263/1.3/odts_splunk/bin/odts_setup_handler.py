import splunk.admin as admin
import splunk.entity as en

class ConfigApp(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            self.supportedArgs.addOptArg('oo_python_path')
            self.supportedArgs.addOptArg('oo_python_port')

    def handleList(self, confInfo):
        confDict = self.readConf("odts")
        if None != confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in ['oo_python_path','oo_python_port'] and val in [None, '']:
                        val = ''
                    confInfo[stanza].append(key, val)

    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs
        if self.callerArgs.data['oo_python_path'][0] in [None, '']:
            self.callerArgs.data['oo_python_path'][0] = ''
        if int(self.callerArgs.data['oo_python_port'][0]) < 0 or int(self.callerArgs.data['oo_python_port'][0]) > 65536:
            self.callerArgs.data['field_3'][0] = '2002'
        self.writeConf('odts', 'odts_config', self.callerArgs.data)

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
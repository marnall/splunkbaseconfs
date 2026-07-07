import splunk.admin as admin
import splunk.entity as en
# import your required python modules


class ConfigApp(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['api_key', 'server_ip', 'disable_verify', 'proxy_host', 'index', 'max_jobs']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        confDict = self.readConf("vmray_analyzer_app_config")
        if confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in ['api_key', 'server_ip','proxy_host'] and val in [None, '']:
                        val = ''
                    if key in ['max_jobs'] and val in [None, '']:
                        val = 1
                    if key in ['disable_verify']:
                        if int(val) == 1:
                            val = '1'
                        else:
                            val = '0'
                    confInfo[stanza].append(key, val)

    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs

        if self.callerArgs.data['api_key'][0] is None:
            self.callerArgs.data['api_key'][0] = ''

        if self.callerArgs.data['server_ip'][0] is None:
            self.callerArgs.data['server_ip'][0] = ''

        if self.callerArgs.data['proxy_host'][0] is None:
            self.callerArgs.data['proxy_host'][0] = ''

        if self.callerArgs.data['max_jobs'][0] is None:
            self.callerArgs.data['max_jobs'][0] = ''

        if int(self.callerArgs.data['disable_verify'][0]) == 1:
            self.callerArgs.data['disable_verify'][0] = '1'
        else:
            self.callerArgs.data['disable_verify'][0] = '0'

        self.writeConf('vmray_analyzer_app_config', 'vmray_analyzer_general', self.callerArgs.data)

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)

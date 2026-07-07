import splunk.admin as admin


class ConfigApp(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['api_key']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        confDict = self.readConf("mac_address_io_setup")
        if None != confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in ['api_key'] and val in [None, '']:
                        val = ''
                    confInfo[stanza].append(key, val)

    def handleEdit(self, confInfo):
        self.writeConf('mac_address_io_setup', 'mac_address_io_config', self.callerArgs.data)


admin.init(ConfigApp, admin.CONTEXT_NONE)

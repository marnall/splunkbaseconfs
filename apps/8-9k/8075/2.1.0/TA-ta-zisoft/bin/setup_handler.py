import splunk.admin as admin

class SetupHandler(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['zisoft_index', 'zisoft_sourcetype']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        confInfo['setup']['zisoft_index'] = self.readConf('appsetup')['setup']['zisoft_index']
        confInfo['setup']['zisoft_sourcetype'] = self.readConf('appsetup')['setup']['zisoft_sourcetype']

    def handleEdit(self, confInfo):
        self.writeConf('appsetup', 'setup', {
            'zisoft_index': self.callerArgs.data['zisoft_index'][0],
            'zisoft_sourcetype': self.callerArgs.data['zisoft_sourcetype'][0]
        })

if __name__ == "__main__":
    admin.init(SetupHandler, admin.CONTEXT_APP_AND_USER)

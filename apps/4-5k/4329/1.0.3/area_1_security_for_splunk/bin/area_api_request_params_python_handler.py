import splunk.admin as admin


class ConfigApp(admin.MConfigHandler):

    # Set up supported arguments
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['area_api_url', 'username', 'password', 'disposition']:
                self.supportedArgs.addOptArg(arg)

    # Read the initial values of the parameters from the custom file
    # areaoneapi.conf, and write them to the setup page.
    def handleList(self, confInfo):
        confDict = self.readConf("areaoneapi")
        if None != confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in ['area_api_url'] and val in [None, '']:
                        val = ''
                    if key in ['username'] and val in [None, '']:
                        val = ''
                    if key in ['password'] and val in [None, '']:
                        val = ''
                    if key in ['disposition'] and val in [None, '']:
                        val = ''
                    confInfo[stanza].append(key, val)

    # After user clicks Save on setup page, take updated parameters,
    # normalize them, and save
    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs

        if self.callerArgs.data['area_api_url'][0] in [None, '']:
            self.callerArgs.data['area_api_url'][0] = ''
        if self.callerArgs.data['username'][0] in [None, '']:
            self.callerArgs.data['username'][0] = ''
        if self.callerArgs.data['password'][0] in [None, '']:
            self.callerArgs.data['password'][0] = ''
        if self.callerArgs.data['disposition'][0] in [None, '']:
            self.callerArgs.data['disposition'][0] = ''

        self.writeConf('areaoneapi', 'area_api_request_params', self.callerArgs.data)


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)

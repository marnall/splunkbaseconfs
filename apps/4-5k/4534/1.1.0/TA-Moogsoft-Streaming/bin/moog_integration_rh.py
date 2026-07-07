import splunk.admin as admin

CONF_FILE_NAME = "moog_server"
ARGS = ['url', 'severity', 'moog_certificate', 'max_batch_size', 'enforce_https']


class MoogIntegrationRH(admin.MConfigHandler):

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for myarg in ARGS:
                self.supportedArgs.addOptArg(myarg)

    def handleList(self, confInfo):
        conf_dict = self.readConf(CONF_FILE_NAME)
        if None != conf_dict:
            for stanza, settings in conf_dict.items():
                for key, val in settings.items():
                    try:
                        if key in ARGS and val in [None, '']:
                            val = ''
                    except Exception as exp:
                        pass
                    confInfo[stanza].append(key, val)

    def handleEdit(self, confInfo):
        if self.callerArgs.data['url'][0] in [None, '']:
            raise Exception("URL is mandatory field")
        elif self.callerArgs.data['severity'][0] in [None, '']:
            raise Exception("Severity is mandatory field")
        elif self.callerArgs.data['max_batch_size'][0] in [None, '']:
            raise Exception("Max Batch Size Limit is mandatory field")
        if self.callerArgs.data['moog_certificate'][0] is None:
            self.callerArgs.data['moog_certificate'] = ['']
        self.writeConf(CONF_FILE_NAME, 'moogsoft', self.callerArgs.data)


admin.init(MoogIntegrationRH, admin.CONTEXT_NONE)

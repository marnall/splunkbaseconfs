import splunk.admin as admin
import splunk.entity as entity

confFileName = "nrql_connections"


class ConfigApp(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ["apiEndpoint", "accountId", "queryKey"]:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        confDict = self.readConf(confFileName)
        if confDict != None:
            for stanza, settings in list(confDict.items()):
                for key, val in list(settings.items()):
                    if key in ["apiEndpoint"] and val in [None, ""]:
                        val = ""
                    if key in ["accountId"] and val in [None, ""]:
                        val = ""
                    if key in ["queryKey"] and val in [None, ""]:
                        val = ""
                    confInfo[stanza].append(key, val)


admin.init(ConfigApp, admin.CONTEXT_NONE)

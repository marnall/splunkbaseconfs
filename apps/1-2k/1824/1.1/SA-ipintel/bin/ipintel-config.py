import splunk.admin as admin

class IpintelConfig(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ["maxmind_license", "shodan_api_key", "virustotal_api_key"]:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        confDict = self.readConf("ipintel")

        for k in confDict:
            for cK in confDict[k]:
                confInfo[k].append("{}_{}".format(k,cK), confDict[k][cK])

    def handleEdit(self, confInfo):
        for k,v in self.callerArgs.data.items():
            if k.lower() == "maxmind_license":
                self.writeConf("ipintel", "maxmind", {"license": v})
            elif k.lower() == "shodan_api_key":
                self.writeConf("ipintel", "shodan", {"api_key": v})
            elif k.lower() == "virustotal_api_key":
                self.writeConf("ipintel", "virustotal", {"api_key": v})

admin.init(IpintelConfig, admin.CONTEXT_NONE)

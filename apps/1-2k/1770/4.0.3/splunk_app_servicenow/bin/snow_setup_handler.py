__author__ = 'strong'

import splunk.admin as admin
import base_handler as base
import splunklib.client as client
import splunklib.binding as binding

REQUIRE_PARAMETERS = ['collection_interval','since_when','loglevel']

ARG_TARGET = "target"

class SnowSetupHandler(base.BaseHandler):
    def setup(self):
        self.supportedArgs.addReqArg(ARG_TARGET)
        if self.requestedAction in [admin.ACTION_CREATE, admin.ACTION_EDIT]:
            for param in REQUIRE_PARAMETERS:
                self.supportedArgs.addReqArg(param)

    def handleCreate(self, confInfo):
        self.handleEdit(confInfo)

    def handleEdit(self, confInfo):
        target = self.callerArgs[ARG_TARGET][0]
        service = self._get_ta_target_service(target)
        snow_default = self._get_snow_default(service)
        collection_interval = self.callerArgs["collection_interval"][0]
        since_when = self.callerArgs["since_when"][0]
        since_when = since_when if since_when else ""
        loglevel = self.callerArgs["loglevel"][0]
        props = {"collection_interval": collection_interval, "since_when": since_when, "loglevel": loglevel}
        snow_default.update(
            **{"body": binding._encode(**props),"app": "Splunk_TA_snow","owner": service.namespace.get('owner')})
        return self._get_snow_default(service)

    def handleList(self, confInfo):
        target = self.callerArgs[ARG_TARGET][0]
        service = self._get_ta_target_service(target)
        snow_default = self._get_snow_default(service)

        if snow_default:
            content = snow_default.content
            default_in_response = confInfo[snow_default.name]
            for arg in REQUIRE_PARAMETERS:
                default_in_response[arg] = content[arg]

    def _get_snow_default(self, service):
        collection = client.Collection(service,"service_now_setup/snow_account").list()
        for item in collection:
            if item.name == "snow_default":
                return item

admin.init(SnowSetupHandler, admin.CONTEXT_APP_ONLY)
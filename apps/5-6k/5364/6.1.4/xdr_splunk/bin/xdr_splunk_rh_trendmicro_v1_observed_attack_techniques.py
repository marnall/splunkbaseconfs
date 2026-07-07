import import_declare_test

from endpoints.oat_endpoint import endpoint
from endpoints.detection_endpoint import endpoint as detection_endpoint
from splunktaucclib.splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler import admin_external
from splunktaucclib.rest_handler.handler import RestHandler
from splunktaucclib.rest_handler.admin_external import get_splunkd_endpoint, build_conf_info
from solnlib.utils import is_true


class XDRConfigMigrationHandler(ConfigMigrationHandler):
    
    def __init__(self, *args, **kwargs):
        # use classic inheritance to be compatible for
        # old version of Splunk private SDK
        self.detection_endpoint = detection_endpoint
        super(XDRConfigMigrationHandler, self).__init__(*args, **kwargs)
        self.detection_handler = RestHandler(
            get_splunkd_endpoint(),
            self.getSessionKey(),
            self.detection_endpoint,
        )
    
    @build_conf_info
    def handleCreate(self, confInfo):
        self.create_hook(
            session_key=self.getSessionKey(),
            config_name=self._get_name(),
            stanza_id=self.callerArgs.id,
            payload=self.payload,
        )
        result = self.handler.create(
            self.callerArgs.id,
            self.payload,
        )
        return result
    
    @build_conf_info
    def handleEdit(self, confInfo):
        disabled = self.payload.get("disabled")
        if disabled is None:
            oat_global_account = self.payload.get("global_account")
            disabled = self.get_input_payload("disabled")
            if not is_true(disabled):
                self.is_able_to_enable(oat_global_account=oat_global_account)
            self.edit_hook(
                session_key=self.getSessionKey(),
                config_name=self._get_name(),
                stanza_id=self.callerArgs.id,
                payload=self.payload,
            )
            return self.handler.update(
                self.callerArgs.id,
                self.payload,
            )
        elif is_true(disabled):
            return self.handler.disable(self.callerArgs.id)
        else:
            oat_global_account = self.get_input_payload("global_account")
            self.is_able_to_enable(oat_global_account=oat_global_account)
            return self.handler.enable(self.callerArgs.id)
        
    def is_able_to_enable(self, oat_global_account):
        decrypt = self.callerArgs.data.get(
            self.ACTION_CRED,
            [False],
        )
        decrypt = is_true(decrypt[0])
        result = self.detection_handler.all(
                decrypt=decrypt,
                count=0,
        )
        for entity in result:
            content = entity.content
            disabled = content.get('disabled', False)
            global_account = content.get('global_account', None)
            if oat_global_account==global_account  and not disabled :
                raise ValueError("Unable to enable XDR_OAT. XDR_OAT and XDR_Detection cannot be enabled for one account at the same time. Disable XDR_Detection in order to enable XDR_OAT.")
        return result
    
    def get_input_payload(self, payload_name):
        decrypt = self.callerArgs.data.get(
            self.ACTION_CRED,
            [False],
        )
        decrypt = is_true(decrypt[0])
        result = self.handler.all(
                decrypt=decrypt,
                count=0,
        )
        for entity in result:
            content = entity.content
            name = entity.name
            if self.callerArgs.id== name:
                return content.get(payload_name, None)





if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=XDRConfigMigrationHandler,
    )

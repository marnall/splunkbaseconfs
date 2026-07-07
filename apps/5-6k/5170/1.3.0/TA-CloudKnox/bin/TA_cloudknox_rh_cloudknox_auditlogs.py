import ta_cloudknox_declare
import os.path as op

from solnlib.modular_input import checkpointer
from cloudknox_validators import StartDatetimeValidator
from cloudknox_collect import CloudKnoxCollect

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.error import RestError
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """Extended custom input config handler."""

    def handleCreate(self, conf_info):
        """To override the input creation process."""
        session_key = self.getSessionKey()
        app_name = self.appName
        # Initialize CloudKnoxCollect Object
        collect_obj = CloudKnoxCollect(session_key, app_name)
        try:
            collect_obj.check_credentials()
        except Exception as e:
            raise RestError("500", str(e))
        super(CustomConfigMigrationHandler, self).handleCreate(conf_info)

    def handleRemove(self, conf_info):
        """To override the input deletion process."""
        input_name = self.callerArgs.id
        session_key = self.getSessionKey()
        app_name = __file__.split(op.sep)[-3]
        ck = checkpointer.KVStoreCheckpointer("{}_checkpointer".format(app_name), session_key, app_name)
        last_chekpoint = ck.get(input_name)
        if last_chekpoint:
            ck.delete(input_name)
        super(CustomConfigMigrationHandler, self).handleRemove(conf_info)


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=3600,
            max_val=None,
            is_int=True
        )
    ),
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1,
            max_len=80,
        )
    ),
    field.RestField(
        'start_datetime',
        required=False,
        encrypted=False,
        default=None,
        validator=StartDatetimeValidator()
    ),
    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    'cloudknox_auditlogs',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )

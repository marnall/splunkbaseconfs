import ta_armis_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from utils_account import KeyValidator
from armis_utils import GetSessionKey, read_conf_file
from splunk import admin
import armis_constants as constants

util.remove_http_proxy_env_vars()


class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server.

    :param ConfigMigrationHandler: inhereting ConfigMigrationHandler
    """

    def handleRemove(self, confInfo):
        """Handle the delete operation."""
        session_key = GetSessionKey().session_key
        inputs_file = read_conf_file(session_key, "inputs")
        created_inputs = list(inputs_file.keys())
        input_list = []
        
        for each in created_inputs:
            armis_input = each.split('://')
            if armis_input[0] in constants.input_type_list:
                configured_account = inputs_file.get(each).get('global_account')
                if configured_account == self.callerArgs.id:
                    input_list.append(armis_input[1])
        if len(input_list) > 0:
            raise admin.ArgValidationException(
                "Account will not be deleted because it is linked with the \
                 following inputs: {}".format(", ".join(input_list)))
        else:
            super(ConfigMigrationHandler, self).handleRemove(confInfo)


fields = [
    field.RestField(
        'armis_hostname',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'armis_api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=KeyValidator()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_armis_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )

import ta_flashpoint_intelligence_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunk import admin

from account_validation import APIKeyValidator
from utils import read_conf_file

util.remove_http_proxy_env_vars()

class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()

class AccountHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server
    :param ConfigMigrationHandler: inhereting ConfigMigrationHandler
    """
    def handleRemove(self, confInfo):
        """Handle the delete operation."""
        session_key = GetSessionKey().session_key
        inputs_file = read_conf_file(session_key, "inputs")
        created_inputs = list(inputs_file.keys())
        input_list = []
        input_type_list = ["flashpoint_intelligence"]
        for _input in created_inputs:
            flashpoint_input = _input.split('://')
            if flashpoint_input[0] in input_type_list:
                configured_account = inputs_file.get(_input).get('global_account')
                if configured_account == self.callerArgs.id:
                    input_list.append(flashpoint_input[1])
        if len(input_list) > 0:
            raise admin.ArgValidationException(
                "\"{}\" cannot be deleted because it is in use by the following inputs: {}".format(
                    self.callerArgs.id, input_list
                )
            )
        else:
            super(ConfigMigrationHandler, self).handleRemove(confInfo)

fields = [
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=APIKeyValidator()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_flashpoint_intelligence_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AccountHandler,
    )

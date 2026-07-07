
import ta_precrime_threat_intelligence_declare
from precrime_server_validation import ValidateAccount
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from utils_precrime import GetSessionKey, read_conf_file
from splunk import admin

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
        input_type_list = ["precrime"]
        for each in created_inputs:
            precrime_inp = each.split('://')
            if precrime_inp[0] in input_type_list:
                configured_account = inputs_file.get(each).get('global_account')
                if configured_account == self.callerArgs.id:
                    input_list.append(precrime_inp[1])
        if len(input_list) > 0:
            raise admin.ArgValidationException(
                "Account will not be deleted because it is linked with the \
                 following inputs: {}".format(", ".join(input_list)))
        else:
            super(ConfigMigrationHandler, self).handleRemove(confInfo)

fields = [
    field.RestField(
        'api_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=200, 
        )
    ), 
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=ValidateAccount()
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_precrime_threat_intelligence_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )

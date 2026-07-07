
import ta_pps_ondemand_declare
from proofpoint_account_validation import ValidateAccount

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler.error import RestError
import proofpoint_utility as utility

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=200, 
        )
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=ValidateAccount())

    
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_pps_ondemand_account',
    model,
)


class CustomAccountHandler(ConfigMigrationHandler):
    """
    This class handles the parameters in the account page
    """

    def __init__(self, *args, **kwargs):
        ConfigMigrationHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, conf_info):
        """Handle the delete operation."""
        session_key = self.getSessionKey()
        inputs_file = utility.read_conf_file(session_key, "inputs")
        created_inputs = list(inputs_file.keys())
        input_list = []
        for each in created_inputs:
            each_proofpoint_input = each.split("://")
            if each.startswith("{}://".format(each_proofpoint_input[0])):
                configured_account = inputs_file.get(each).get("global_account")
                if configured_account == self.callerArgs.id:
                    input_list.append(each_proofpoint_input[1])
        if len(input_list) > 0:
            raise RestError(
                409,
                "Account will not be deleted because it is linked with the \
                 following inputs: {}".format(
                    ", ".join(input_list)
                )
            )
        else:
            super(CustomAccountHandler, self).handleRemove(conf_info)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomAccountHandler,
    )


import json
import ta_extrahop_addon_declare
from extrahop_validator import ValidateFields, ValidateAccount

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler.error import RestError
from splunk import rest

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'instance_type',
        required=True,
        encrypted=False,
        default=None,
        validator=ValidateFields()
    ),
    field.RestField(
        'hostname',
        required=True,
        encrypted=False,
        default=None,
        validator=ValidateAccount()
    ), 
    field.RestField(
        'api_key',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'client_id',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'client_secret',
        required=False,
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
    'ta_extrahop_addon_account',
    model,
)

class CustomAccountHandler(ConfigMigrationHandler):
    """
    This class handles the parameters in the account page
    """

    def __init__(self, *args, **kwargs):
        ConfigMigrationHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, conf_info):
        """
        This method is called when account is deleted. It deletes the account if it is not used in the input configurations.
        :param conf_info: The directory containing configurable parameters.
        """
        session_key = self.getSessionKey()
        stanza_name = self.callerArgs.id
        try:
            response_status, response_content = rest.simpleRequest("/servicesNS/nobody/" + str(ta_extrahop_addon_declare.ta_name) + "/configs/conf-inputs/", sessionKey=session_key, getargs={"output_mode": "json"}, raiseAllErrors=True)
            res = json.loads(response_content)
            input_list = []
            if "entry" in res:
                for inputs in res["entry"]:
                    if "name" in inputs:
                        input_name = (inputs["name"]).replace("extrahop://", "")
                        if "content" in inputs and "global_account" in inputs["content"]:
                            global_account = inputs["content"]["global_account"]
                            if global_account == stanza_name:
                                input_list.append(input_name)
            if input_list:
                raise RestError(409, "Cannot delete the account as it is already been used in {}.".format(", ".join(input_list)))
        except Exception as e:
            raise RestError(409, "Something went wrong while deleting the account.{}".format(str(e)))
        super(CustomAccountHandler, self).handleRemove(conf_info)

if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomAccountHandler,
    )


import ta_riskiq_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from riskiq_validators import ValidateRiskIQEndpoints

import riskiq_logger_manager as log
import riskiq_common_utility as riskiq_utils

util.remove_http_proxy_env_vars()
_LOGGER = log.setup_logging("ta_riskiq_setup")

fields = [
    field.RestField(
        'api_key',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=200, 
        )
    ), 
    field.RestField(
        'api_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'customer_name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=200, 
        )
    ),
    field.RestField(
        'endpoint_select',
        required=False,
        encrypted=False,
        default=None,
        validator=ValidateRiskIQEndpoints()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_riskiq_account',
    model,
)

class CustomInputsHandler(ConfigMigrationHandler):

    def handleCreate(self, confInfo):
        try:
            endpoints = ''.join(self.callerArgs.data.get('endpoint_select'))
            selected_endpoints = endpoints.split('~')
            riskiq_utils.create_riskiq_input(self.callerArgs.id, selected_endpoints, self.getSessionKey())
        except Exception as e:
            _LOGGER.error("Error occured while creating modular input stanza for account {} \nError: {}".format(self.callerArgs.id, str(e)))
        super(CustomInputsHandler,self).handleCreate(confInfo)

if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomInputsHandler,
    )

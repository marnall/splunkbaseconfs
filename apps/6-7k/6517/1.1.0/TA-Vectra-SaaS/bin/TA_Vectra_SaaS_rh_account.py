
import ta_vectra_saas_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
import splunk.rest as rest
import json
import splunk.admin as admin
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from common import log
from account_validation import ValidateAccountCreds
logger = log.get_logger("TA_Vectra_SaaS_rh_account")

util.remove_http_proxy_env_vars()

class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server
    :param ConfigMigrationHandler: inheriting ConfigMigrationHandler
    """
    
    def get_input_details(self, input_type):
        """Fetch the input details"""
        # rest call to get inputs.
        _, response_content = rest.simpleRequest(
                "/servicesNS/nobody/TA-Vectra-SaaS/data/inputs/{}".format(input_type),
                sessionKey=self.getSessionKey(),
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )
        return json.loads(response_content)

    def handleRemove(self, confInfo):
        """Handle the delete operation"""
        try:
            account_scoring_response = self.get_input_details("account_scoring_input")
            account_detection_response = self.get_input_details("account_detection_input")
        except Exception as e:
            logger.error("Vectra SaaS account deletion: Error occured while getting input details. Error_message=\"{}\"".format(str(e)))
            raise admin.ArgValidationException("Error occured while getting input details. Error=\"{}\"".format(str(e)))
        else:
            # list of input that linked with account
            input_list = []

            for input in range(len(account_scoring_response['entry'])):
                if account_scoring_response['entry'][input]['content']['vectra_saas_account'] == self.callerArgs.id:
                    account_name = self.callerArgs.id
                    input_list.append(account_scoring_response['entry'][input]['name'])

            for input in range(len(account_detection_response['entry'])):
                if account_detection_response['entry'][input]['content']['vectra_saas_account'] == self.callerArgs.id:
                    account_name = self.callerArgs.id
                    input_list.append(account_detection_response['entry'][input]['name'])

            if len(input_list) > 0:
                logger.error("Vectra SaaS account deletion: Account \"{}\" can not be deleted because "
                            "it is linked with the following inputs: [\"{}\"]".format(account_name,"\", \"".join(input_list)))
                raise admin.ArgValidationException(
                    "Account \"{}\" can not be deleted because it is linked with the following inputs=[\"{}\"]"
                    .format(account_name,"\", \"".join(input_list)))
            super(CustomConfigMigrationHandler, self).handleRemove(confInfo)

fields = [
    field.RestField(
        'server_url',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ),
     field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'client_secret_key',
        required=True,
        encrypted=True,
        default='',
        validator=ValidateAccountCreds()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_vectra_saas_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )

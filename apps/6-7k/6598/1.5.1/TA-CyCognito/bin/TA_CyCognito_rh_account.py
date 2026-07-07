
import ta_cycognito_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from ta_cycognito_validations import AccountValidator
from ta_cycognito_logger_manager import setup_logging
import splunk.admin as admin
import splunk.rest as rest
import json

util.remove_http_proxy_env_vars()


logger = setup_logging('ta_cycognito_validation')

class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server
    :param ConfigMigrationHandler: inheriting ConfigMigrationHandler
    """
    
    def get_input_details(self, input_type):
        """Fetch the input details"""
        # rest call to get inputs.
        _, response_content = rest.simpleRequest(
                "/servicesNS/nobody/TA-CyCognito/data/inputs/{}".format(input_type),
                sessionKey=self.getSessionKey(),
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )
        return json.loads(response_content)

    def handleRemove(self, confInfo):
        """Handle the delete operation"""
        try:
            assets_response = self.get_input_details("cycognito_assets")
            issues_response = self.get_input_details("cycognito_issues")
        except Exception as e:
            logger.error("CyCognito Validation: Error occured while getting input details. Error_message=\"{}\"".format(str(e)))
            raise admin.ArgValidationException("Error occured while getting input details. Error_message=\"{}\"".format(str(e)))
        else:
            # list of input that linked with account
            input_list = []

            for input in range(len(assets_response['entry'])):
                if assets_response['entry'][input]['content']['cycognito_account'] == self.callerArgs.id:
                    cycognito_account_name = self.callerArgs.id
                    input_list.append(assets_response['entry'][input]['name'])
                    
            for input in range(len(issues_response['entry'])):
                if issues_response['entry'][input]['content']['cycognito_account'] == self.callerArgs.id:
                    cycognito_account_name = self.callerArgs.id
                    input_list.append(issues_response['entry'][input]['name'])

            if len(input_list) > 0:
                logger.error("CyCognito Validation: \"{}\" Account will not be deleted because "
                            "it is linked with the following inputs: \"{}\"".format(cycognito_account_name,", ".join(input_list)))
                raise admin.ArgValidationException(
                    "\"{}\" Account will not be deleted because it is linked with the following inputs=\"{}\"".format(cycognito_account_name,", ".join(input_list)))
            super(CustomConfigMigrationHandler, self).handleRemove(confInfo)


fields = [
    field.RestField(
        'platform_url',
        required=True,
        encrypted=False,
        default="api.platform.cycognito.com",
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'api_token',
        required=True,
        encrypted=True,
        default=None,
        validator=AccountValidator()
    )
]

model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_cycognito_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )

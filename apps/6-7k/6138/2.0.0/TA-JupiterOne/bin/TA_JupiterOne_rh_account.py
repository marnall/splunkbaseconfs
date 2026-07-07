
import ta_jupiterone_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from ta_jupiterone_validations import AccountValidator
from ta_jupiterone_log_manager import setup_logging
import splunk.admin as admin
import splunk.rest as rest
import json

util.remove_http_proxy_env_vars()

logger = setup_logging('ta_jupiterone_rh_account')


class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server
    :param ConfigMigrationHandler: inhereting ConfigMigrationHandler
    """

    def handleRemove(self, confInfo):
        """Handle the delete operation"""
        try:
            # rest call to get inputs.
            _, response_content = rest.simpleRequest(
                "/servicesNS/nobody/TA-JupiterOne/data/inputs/jupiterone_alerts",
                sessionKey=self.getSessionKey(),
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )
            response_content = json.loads(response_content)
        except Exception:
            logger.error("JupiterOne Error: Error occured while getting inputs.")
            super(CustomConfigMigrationHandler, self).handleRemove(confInfo)
        else:
            # list of input that linked with account
            input_list = []

            for input in range(len(response_content['entry'])):
                if response_content['entry'][input]['content']['jupiterone_account'] == self.callerArgs.id:
                    input_list.append(response_content['entry'][input]['name'])

            if len(input_list) > 0:
                logger.info("JupiterOne Info: Account will not be deleted because "
                            "it is linked with the following inputs: {}".format(", ".join(input_list)))
                raise admin.ArgValidationException(
                    "Account will not be deleted because it is linked with the following inputs: {}".format(", ".join(input_list)))
            else:
                super(CustomConfigMigrationHandler, self).handleRemove(confInfo)


fields = [
    field.RestField(
        'account_id',
        required=True,
        encrypted=False,
        default='',
        validator=None
    ),
    field.RestField(
        'base_url',
        required=True,
        encrypted=False,
        default='https://graphql.us.jupiterone.io',
        validator=AccountValidator()
    ),
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default='',
        validator=AccountValidator()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_jupiterone_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )

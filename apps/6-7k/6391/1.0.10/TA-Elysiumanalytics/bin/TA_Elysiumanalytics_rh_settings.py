
import ta_elysiumanalytics_declare
from elysiumanalytics_validators import ValidateElysiumanalyticsInstance
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()

from log_manager import setup_logging

# _LOGGER = setup_logging("global_configuartion")


fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_elysiumanalytics_credentials = [
    field.RestField(
        'snowflake_instance',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=500,
        )
    ),
   
   
    field.RestField(
        'snowflake_refresh_token',
        required=True,
        encrypted=True,
        default='',
        validator=ValidateElysiumanalyticsInstance()
    ),
    field.RestField(
        'client_id',
        required=True,
        encrypted=True,
        default=''
      
    ),
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default=''
      
    ),
    field.RestField(
        'cust_options',
        required=True,
      
        default='',
        validator=validator.String(
            min_len=0,
            max_len=500,
        )
    ),
    field.RestField(
        'cust_id',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=500,
        )
    )
   
]
model_elysiumanalytics_credentials = RestModel(fields_elysiumanalytics_credentials, name='elysiumanalytics_credentials')
# _LOGGER.info(model_elysiumanalytics_credentials)

endpoint = MultipleModel(
    'ta_elysiumanalytics_settings',
    models=[
        model_logging,
        model_elysiumanalytics_credentials
    ],
)

# _LOGGER.info("----------------- endpint ----------------------")
# _LOGGER.info(endpoint)
if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )

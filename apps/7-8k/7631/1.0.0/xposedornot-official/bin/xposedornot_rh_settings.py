import xposedornot_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
import requests
import logging

# Initialize logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

util.remove_http_proxy_env_vars()

# Define a custom validator for the API key
class APIKeyValidator(validator.Validator):
    def validate(self, value, data):
        # Check if the API key is 32 characters long
        if len(value) != 32:
            raise ValueError("API Key must be exactly 32 characters long.")

        # Define the endpoint URL to validate the API key
        validation_url = "https://api.xposedornot.com/v1/domain-breaches/"
        headers = {"Authorization": f"Bearer {value}"}

        try:
            # Make a POST request to validate the API key
            response = requests.post(validation_url, headers=headers)

            # If the response status is not 200, raise an error
            if response.status_code != 200:
                raise ValueError("Invalid API Key.")
        
        except requests.RequestException as e:
            logger.error(f"Error during API Key validation: {str(e)}")
            raise ValueError(f"Error validating API Key: {str(e)}")

        return True

# Define fields for logging configuration
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

# Define fields for additional parameters with custom API key validator
fields_additional_parameters = [
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default='',
        validator=APIKeyValidator()  # Use the custom validator here
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')

# Define the endpoint with multiple models
endpoint = MultipleModel(
    'xposedornot_settings',
    models=[
        model_logging, 
        model_additional_parameters
    ],
)

if __name__ == '__main__':
    try:
        logger.debug("Starting configuration handler.")
        admin_external.handle(
            endpoint,
            handler=ConfigMigrationHandler,
        )
    except Exception as e:
        logger.error(f"Error handling configuration: {str(e)}")

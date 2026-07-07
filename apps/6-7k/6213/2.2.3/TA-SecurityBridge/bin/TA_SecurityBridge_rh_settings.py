
import ta_securitybridge_declare

import os
import sys
import json
import uuid

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
import splunk.rest as rest

util.remove_http_proxy_env_vars()


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


fields_additional_parameters = [
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')


fields_push_settings = [
    field.RestField(
        'webhook_enabled',
        required=False,
        encrypted=False,
        default='0',
        validator=None
    ),
    field.RestField(
        'hec_token',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'hec_token_name',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=256,
            min_len=0,
        )
    ),
    field.RestField(
        'hec_url',
        required=False,
        encrypted=False,
        default='https://localhost:8088/services/collector',
        validator=validator.String(
            max_len=4096,
            min_len=0,
        )
    ),
    field.RestField(
        'sap_webhook_url',
        required=False,
        encrypted=False,
        default='https://<SPLUNK_HOST>:8088/services/collector/raw?sourcetype=sapsb_push_json&index=sap',
        validator=validator.String(
            max_len=4096,
            min_len=0,
        )
    ),
    field.RestField(
        'target_index',
        required=False,
        encrypted=False,
        default='main',
        validator=validator.String(
            max_len=80,
            min_len=0,
        )
    )
]
model_push_settings = RestModel(fields_push_settings, name='push_settings')


endpoint = MultipleModel(
    'ta_securitybridge_settings',
    models=[
        model_logging,
        model_additional_parameters,
        model_push_settings
    ],
)


class PushSettingsHandler(ConfigMigrationHandler):
    """
    Custom handler that extends ConfigMigrationHandler to add HEC token auto-creation and deletion
    """

    def handleList(self, confInfo):
        """Handle list request - initialize credentials if they don't exist"""
        import logging
        try:
            ConfigMigrationHandler.handleList(self, confInfo)
        except Exception as e:
            # Handle CredentialNotExistException (singular) - initialize empty credentials
            error_name = type(e).__name__
            error_str = str(e)
            if 'CredentialNotExist' in error_name or 'CredentialNotExist' in error_str:
                logging.warning(f"Credentials not found, initializing empty config: {error_str}")
                # Initialize empty push_settings credentials
                try:
                    session_key = self.getSessionKey()
                    self._initialize_empty_credentials(session_key)
                    # Retry the list operation
                    ConfigMigrationHandler.handleList(self, confInfo)
                except Exception as retry_error:
                    logging.error(f"Failed to initialize credentials: {str(retry_error)}")
                    # Return empty config info to avoid breaking the UI
                    pass
            else:
                # Re-raise other exceptions
                raise

    def _initialize_empty_credentials(self, session_key):
        """Initialize empty credentials for push_settings in the password store"""
        import logging
        try:
            # Create credential entry in storage/passwords
            uri = '/servicesNS/nobody/TA-SecurityBridge/storage/passwords'
            postargs = {
                'name': 'push_settings',
                'realm': '__REST_CREDENTIAL__#TA-SecurityBridge#configs/conf-ta_securitybridge_settings',
                'password': '',
                'output_mode': 'json'
            }
            response, content = rest.simpleRequest(
                uri,
                sessionKey=session_key,
                method='POST',
                postargs=postargs
            )
            if response.status in [200, 201, 409]:  # 409 = already exists
                logging.info("Initialized empty push_settings credentials in password store")
                return True
            else:
                logging.warning(f"Failed to initialize credentials: HTTP {response.status}")
        except Exception as e:
            logging.error(f"Error initializing credentials: {str(e)}")
        return False

    def handleEdit(self, confInfo):
        """Handle edit request - auto-create/delete HEC token based on webhook_enabled"""
        import logging
        created_token_name = None  # Track if we created a new token

        try:
            # Check if this is a push_settings update
            if self.callerArgs.id == 'push_settings':
                session_key = self.getSessionKey()

                # Check if Push API is being disabled
                # Handle various checkbox values: '0', '1', 'true', 'false', '', 0, 1, True, False
                webhook_enabled_raw = self.callerArgs.data.get('webhook_enabled', ['0'])[0] if self.callerArgs.data.get('webhook_enabled') else '0'
                webhook_enabled = str(webhook_enabled_raw).lower() in ('1', 'true', 'yes', 'on')

                logging.info(f"Push API webhook_enabled raw value: {webhook_enabled_raw}, parsed: {webhook_enabled}")

                if not webhook_enabled:
                    # Push API is being disabled - delete HEC token if it exists
                    existing_config = self._get_existing_config(session_key)
                    if existing_config:
                        token_name = existing_config.get('hec_token_name', '')
                        if token_name:
                            # Delete the HEC token
                            delete_result = self._delete_hec_token(session_key, token_name)
                            logging.info(f"Delete HEC token '{token_name}' result: {delete_result}")
                        # Clear token fields regardless of delete result
                        self.callerArgs.data['hec_token'] = ['']
                        self.callerArgs.data['hec_token_name'] = ['']
                        logging.info("Cleared HEC token fields")
                else:
                    # Push API is enabled - create HEC token if needed
                    hec_token = self.callerArgs.data.get('hec_token', [''])[0] if self.callerArgs.data.get('hec_token') else ''

                    # If no token provided or token is masked, check if we need to create one
                    if not hec_token or hec_token == '' or hec_token.startswith('***'):
                        # Check existing config for token
                        existing_token = self._get_existing_hec_token(session_key)

                        if existing_token:
                            # Keep existing token
                            self.callerArgs.data['hec_token'] = [existing_token]
                            # Also preserve token name
                            existing_config = self._get_existing_config(session_key)
                            if existing_config and existing_config.get('hec_token_name'):
                                self.callerArgs.data['hec_token_name'] = [existing_config.get('hec_token_name')]
                        else:
                            # Create new HEC token
                            target_index = self.callerArgs.data.get('target_index', ['main'])[0] if self.callerArgs.data.get('target_index') else 'main'
                            token_name = f"sap_securitybridge_push_{uuid.uuid4().hex[:8]}"

                            new_token = self._create_hec_token(session_key, token_name, target_index)
                            if new_token:
                                self.callerArgs.data['hec_token'] = [new_token]
                                self.callerArgs.data['hec_token_name'] = [token_name]
                                created_token_name = token_name  # Store for post-save update
                                logging.info(f"Created HEC token: {token_name}")

            # Call parent handler
            ConfigMigrationHandler.handleEdit(self, confInfo)

            # After parent handler saves, ensure hec_token_name is stored via direct REST call
            # This is needed because fields not in the original form submission may not be saved
            if created_token_name and self.callerArgs.id == 'push_settings':
                session_key = self.getSessionKey()
                self._update_config_field(session_key, 'hec_token_name', created_token_name)
                logging.info(f"Explicitly saved hec_token_name: {created_token_name}")

        except Exception as e:
            # Log error but don't break - fall back to parent handler
            logging.error(f"PushSettingsHandler error: {str(e)}")
            ConfigMigrationHandler.handleEdit(self, confInfo)

    def _update_config_field(self, session_key, field_name, field_value):
        """Update a specific field in push_settings config via direct REST call"""
        import logging
        try:
            uri = '/servicesNS/nobody/TA-SecurityBridge/configs/conf-ta_securitybridge_settings/push_settings'
            postargs = {
                field_name: field_value,
                'output_mode': 'json'
            }

            response, content = rest.simpleRequest(
                uri,
                sessionKey=session_key,
                method='POST',
                postargs=postargs
            )

            if response.status in [200, 201]:
                logging.info(f"Successfully updated {field_name} to {field_value}")
                return True
            else:
                logging.warning(f"Failed to update {field_name}: {response.status}")

        except Exception as e:
            logging.error(f"Error updating {field_name}: {str(e)}")

        return False

    def _get_existing_config(self, session_key):
        """Get existing push settings configuration"""
        try:
            uri = '/servicesNS/nobody/TA-SecurityBridge/configs/conf-ta_securitybridge_settings/push_settings'
            response, content = rest.simpleRequest(
                uri,
                sessionKey=session_key,
                method='GET',
                getargs={'output_mode': 'json'}
            )
            if response.status == 200:
                data = json.loads(content)
                if 'entry' in data and data['entry']:
                    return data['entry'][0]['content']
        except Exception:
            pass
        return None

    def _get_existing_hec_token(self, session_key):
        """Get existing HEC token from config"""
        config = self._get_existing_config(session_key)
        if config:
            return config.get('hec_token', '')
        return None

    def _delete_hec_token(self, session_key, token_name):
        """Delete HEC token from Splunk"""
        try:
            # URL encode the token name for the REST API
            from urllib.parse import quote
            encoded_name = quote(token_name, safe='')
            uri = f'/servicesNS/nobody/splunk_httpinput/data/inputs/http/{encoded_name}'

            response, content = rest.simpleRequest(
                uri,
                sessionKey=session_key,
                method='DELETE',
                getargs={'output_mode': 'json'}
            )

            if response.status in [200, 204]:
                import logging
                logging.info(f"Successfully deleted HEC token: {token_name}")
                return True
            else:
                import logging
                logging.warning(f"Failed to delete HEC token {token_name}: {response.status}")

        except Exception as e:
            import logging
            logging.error(f"Error deleting HEC token {token_name}: {str(e)}")

        return False

    def _create_hec_token(self, session_key, token_name, index='main'):
        """Create HEC token in Splunk and return the token value"""
        try:
            # First, ensure HEC is enabled
            self._enable_hec(session_key)

            # Create the HEC token
            uri = '/servicesNS/nobody/splunk_httpinput/data/inputs/http'

            postargs = {
                'name': token_name,
                'index': index,
                'indexes': index,
                'sourcetype': 'sapsb_push_json',
                'source': 'sap:securitybridge:push',
                'disabled': '0',
                'useACK': '0',
                'output_mode': 'json'
            }

            response, content = rest.simpleRequest(
                uri,
                sessionKey=session_key,
                method='POST',
                postargs=postargs
            )

            if response.status in [200, 201]:
                data = json.loads(content)
                if 'entry' in data and data['entry']:
                    token_value = data['entry'][0]['content'].get('token')
                    return token_value

        except Exception as e:
            import logging
            logging.error(f"Error creating HEC token: {str(e)}")

        return None

    def _enable_hec(self, session_key):
        """Enable HEC if not already enabled"""
        try:
            uri = '/servicesNS/nobody/splunk_httpinput/data/inputs/http/http'

            postargs = {
                'disabled': '0',
                'enableSSL': '1',
                'output_mode': 'json'
            }

            response, content = rest.simpleRequest(
                uri,
                sessionKey=session_key,
                method='POST',
                postargs=postargs
            )

            return response.status in [200, 201]
        except Exception:
            pass
        return False


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=PushSettingsHandler,
    )

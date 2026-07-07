import os
import re
import sys


def _setup_python_path():
    """Setup Python path BEFORE any local imports."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_root = os.path.dirname(script_dir)

    # Resolve to real paths to prevent path traversal
    app_root = os.path.realpath(app_root)
    script_dir = os.path.realpath(script_dir)

    lib_path = os.path.join(app_root, 'lib')

    # Ensure lib_path is within app_root (prevent path traversal)
    lib_path = os.path.realpath(lib_path)

    for p in (lib_path, script_dir):
        p = os.path.realpath(p)
        if os.path.exists(p) and p not in sys.path:
            sys.path.insert(0, p)


# CRITICAL: Setup path BEFORE any local imports
_setup_python_path()

# pylint: disable=import-error
import splunk.rest as rest
from aws_credentials_provider import AwsCredentialsProvider
from integration_handler_utils import APP_NAME, _get_proxy_config, create_service_connection, extract_payload, reset_app_configuration
from integration_request import IntegrationRequest, ProxyUpdateRequest, UpdateIntegration
from logging_setup import setup_logging
from pydantic import ValidationError
from splunk_kv_store_db_services import SplunkKVStoreDBServices, UserConfiguration
from splunk_secrets_manager import SplunkSecretsManager

# Configure logging after imports
logger = setup_logging(APP_NAME)

MAX_ALLOWED_INTEGRATIONS = 5


def _validate_device_name(device_name: str) -> tuple:
    """Validate device name format."""
    if not device_name:
        return False, 'device_name is required'

    if len(device_name) > 256:
        return False, 'device_name exceeds maximum length of 256 characters'

    # Allow alphanumeric, underscores, hyphens, and brackets
    if not re.match(r'^[a-zA-Z0-9_\-\[\]]+$', device_name):
        return False, 'device_name contains invalid characters. Use only alphanumeric, underscores, hyphens, and brackets.'

    return True, ''


class IntegrationHandler(rest.BaseRestHandler):
    """Scripted REST handler for:
      GET    /cyberark_integrations
      POST   /cyberark_integrations
      DELETE /cyberark_integrations/{device}
    """

    def __init__(self, *args, **kwargs):
        super(IntegrationHandler, self).__init__(*args, **kwargs)
        self._path_info = None
        self._request_args = None
        self._service = None
        self._kv_store = None
        self._secrets_manager = None
        logger.debug('IntegrationHandler initialized')

    @property
    def service(self):
        """Returns a Splunk service object for this script invocation."""
        try:
            if self._service is not None:
                return self._service

            self._service = create_service_connection(self.sessionKey, logger)
            return self._service
        except Exception as e:
            logger.error(f'Failed to create Splunk service: {e}', exc_info=True)
            return None

    @property
    def kv_store(self):
        """Lazy-loaded KV store instance (reused across all integrations)"""
        if self._kv_store is None:
            self._kv_store = SplunkKVStoreDBServices(service=self.service, logger=logger, app_name=APP_NAME)
        return self._kv_store

    @property
    def secrets_manager(self):
        """Lazy-loaded secrets manager instance (reused across all integrations)"""
        if self._secrets_manager is None:
            self._secrets_manager = SplunkSecretsManager(service=self.service, logger=logger)
        return self._secrets_manager

    def handle_GET(self):
        """Handle GET requests to retrieve all integrations."""
        logger.info('GET request started')

        try:
            entries = []
            for c in self.kv_store.get_all_user_configs():
                entries.append({
                    'name': c.device_name,
                    'content': {
                        'device_name': c.device_name,
                        'integration_display_name': c.integration_display_name,
                        'auth_endpoint': c.auth_endpoint,
                        'api_endpoint': c.api_endpoint,
                        'api_region': c.api_region,
                        'services_filter': c.services_filter,
                        'initial_minutes_back_start': c.initial_minutes_back_start,
                        'index_name': c.index_name,
                        'sourcetype': c.sourcetype,
                        'host': c.host,
                        'page_size': c.page_size,
                    },
                })

            logger.info(f'Retrieved {len(entries)} integration(s)')

            return {'entry': entries, 'proxy': self._get_proxy_status()}
        except Exception as e:
            logger.error(f'GET failed: {str(e)}', exc_info=True)
            raise

    def _get_proxy_status(self) -> dict:
        """Return saved proxy settings for the UI so the form can be pre-filled."""
        proxy = {
            'proxy_enabled': False,
            'proxy_host': None,
            'proxy_port': None,
            'proxy_verify_ssl': True,
            'proxy_username': None,
            'proxy_password': None,
        }
        try:
            global_config = self.kv_store.get_global_proxy_config()
            if global_config:
                proxy['proxy_enabled'] = bool(global_config.get('proxy_enabled', False))
                proxy['proxy_host'] = global_config.get('proxy_host')
                proxy['proxy_port'] = global_config.get('proxy_port')
                proxy['proxy_verify_ssl'] = bool(global_config.get('proxy_verify_ssl', True))
        except Exception as e:
            logger.warning(f'Could not fetch proxy config from KV store: {e}')

        try:
            proxy['proxy_username'] = self.secrets_manager.get_secret(f'proxy_username_{APP_NAME}')
            self.secrets_manager.get_secret(f'proxy_password_{APP_NAME}')
            proxy['proxy_password'] = '*****'
        except Exception:
            pass

        return proxy

    def handle_POST(self):
        """Handle POST requests to create or update integrations."""
        logger.info('POST request started')

        try:
            data = extract_payload(self.request, logger)

            if data.get('update_proxy', False):
                del data['update_proxy']
                return self.update_proxy_details(data)

            if data.get('update_integration', False):
                del data['update_integration']
                return self.update_integration(data)

            validated_data, error = self._validate_post_request(data, self.kv_store, self.service)
            if error:
                return error

            device = validated_data.device_name
            cert = validated_data.certificate
            pkey = validated_data.private_key
            config = self._create_user_config(validated_data, device)
            proxy_config = _get_proxy_config(self.kv_store, self.secrets_manager, logger)
            err_msg = {'messages': [{'type': 'ERROR', 'text': 'Certificate or private key validation failed'}], 'validation_failed': True}
            try:
                AwsCredentialsProvider(aws_region=validated_data.api_region, auth_endpoint=validated_data.auth_endpoint, device_name=device,
                                       certificate=cert, private_key=pkey, logger=logger,
                                       proxy_config=proxy_config).validate_user_configurations()
            except Exception as err:
                logger.error(f'Certificate/key validation failed for device {device}, err={err}', exc_info=True)
                self.response.setStatus(400)
                return err_msg

            logger.info(f'Saving validated credentials for device: {device}')
            user_credentials = {'device_name': device, 'certificate': cert, 'private_key': pkey}

            self.secrets_manager.save_user_credentials(**user_credentials)

            self.kv_store.create_user_config(config)
            logger.info(f'Configuration saved successfully for device: {device}')
            return {
                'device_name': device,
                'status': 'success',
                'messages': [{
                    'type': 'INFO',
                    'text': 'Integration configuration saved successfully'
                }]
            }

        except Exception as e:
            logger.error(f'POST failed: {str(e)}', exc_info=True)
            self.response.setStatus(500)
            # Return generic error to avoid information disclosure
            return {'messages': [{'type': 'ERROR', 'text': 'An internal error occurred. Please try again.'}]}

    def _validate_post_request(self, data, kv, service):
        """Validate POST request data using Pydantic model."""
        try:
            # Validate all fields using Pydantic
            request = IntegrationRequest(**data)
            device = request.device_name
        except ValidationError as e:
            logger.error(f'Validation failed: {str(e)}', exc_info=True)
            error_msg = e.errors()[0]['msg']
            self.response.setStatus(400)
            return None, {'messages': [{'type': 'ERROR', 'text': error_msg}], 'validation_failed': True}

        # Validate integration limits and duplicates (business logic - stays here)
        validation_error = self._validate_integration_limits(kv, device, data)
        if validation_error:
            return None, validation_error

        return request, None

    def _validate_integration_limits(self, kv, device, data):
        """Validate integration count limits and duplicate endpoints."""
        existing_configs = kv.get_all_user_configs()
        if len(existing_configs) >= MAX_ALLOWED_INTEGRATIONS:
            self.response.setStatus(400)
            return {'messages': [{'type': 'ERROR', 'text': f'Maximum limit of {MAX_ALLOWED_INTEGRATIONS} integrations reached.'}]}

        existing = kv.get_user_config(device)
        if existing:
            logger.warning(f'Integration already exists for device: {device}')
            self.response.setStatus(409)
            return {'messages': [{'type': 'ERROR', 'text': 'Integration for this device already exists.'}]}

        api_endpoint = data.get('api_endpoint', '').strip()
        duplicate = kv.find_duplicate_api_endpoint(api_endpoint)
        if duplicate:
            self.response.setStatus(409)
            return {'messages': [{'type': 'ERROR', 'text': 'An integration already exists.'}], 'validation_failed': True}

        return None

    @staticmethod
    def _create_user_config(data: IntegrationRequest, device: str):
        return UserConfiguration(
            device_name=device,
            integration_display_name=data.integration_display_name,
            auth_endpoint=data.auth_endpoint,
            api_endpoint=data.api_endpoint,
            api_region=data.api_region,
            services_filter=data.services_filter,
            initial_minutes_back_start=data.initial_minutes_back_start,
            index_name=data.index_name,
            sourcetype=data.sourcetype,
            host=data.host,
            page_size=data.page_size,
        )

    def handle_DELETE(self):
        """Handle DELETE requests to remove integrations."""
        logger.info('DELETE request started')

        try:
            data = extract_payload(self.request, logger)
            device = data.get('device_name', '').strip()
            logger.info(f'DELETE request for device: {device}')

            # Validate device name
            is_valid, error_msg = _validate_device_name(device)
            if not is_valid:
                self.response.setStatus(400)
                return {'messages': [{'type': 'ERROR', 'text': error_msg}]}

            existing = self.kv_store.get_user_config(device)
            if not existing:
                self.response.setStatus(404)
                return {'messages': [{'type': 'ERROR', 'text': 'Device not found'}]}

            self.kv_store.delete_user_config(device)
            self.secrets_manager.delete_user_credentials(device)
            logger.info(f'Deleted device: {device}')
            remaining = self.kv_store.get_all_user_configs(enabled_only=False)
            if len(remaining) == 0:
                logger.info('No integrations left - resetting app to unconfigured state')
                reset_app_configuration(self.service, logger)

            return {'device_name': device, 'status': 'deleted'}

        except Exception as e:
            logger.error(f'DELETE failed: {str(e)}', exc_info=True)
            self.response.setStatus(500)
            # Return generic error to avoid information disclosure
            return {'messages': [{'type': 'ERROR', 'text': 'An internal error occurred.'}]}

    @staticmethod
    def _merge_config(data: UpdateIntegration, existing: UserConfiguration) -> UserConfiguration:
        """Merge update data with existing configuration."""
        merge_fields = [
            'integration_display_name',
            'auth_endpoint',
            'api_endpoint',
            'api_region',
            'services_filter',
            'initial_minutes_back_start',
            'index_name',
            'sourcetype',
            'host',
            'page_size',
        ]
        merged = {'device_name': data.device_name}
        for field in merge_fields:
            new_val = getattr(data, field, None)
            old_val = getattr(existing, field, None)
            merged[field] = new_val or old_val

        return UserConfiguration(**merged)

    def update_integration(self, data):
        """Handle PUT requests to update existing integrations."""
        logger.info('update integration request started')

        try:
            data = UpdateIntegration(**data)
            device = data.device_name

            # Check if integration exists
            existing_user = self.kv_store.get_user_config(device, raw_data=True)

            if not existing_user:
                self.response.setStatus(404)
                return {'messages': [{'type': 'ERROR', 'text': 'Integration not found'}]}

            existing_user_config = UserConfiguration.from_dict(existing_user)

            merged_config = self._merge_config(data, existing_user_config)

            self.kv_store.update_user_config(merged_config, existing_user)
            logger.info(f'Updated integration: {device}')

            return {'device_name': device, 'status': 'updated', 'messages': [{'type': 'INFO', 'text': 'Integration updated successfully'}]}
        except ValidationError as e:
            # Extract first error message
            error_msg = e.errors()[0]['msg']
            self.response.setStatus(400)
            return {'messages': [{'type': 'ERROR', 'text': error_msg}], 'validation_failed': True}

        except Exception as e:
            logger.error(f'PUT failed: {str(e)}', exc_info=True)
            self.response.setStatus(500)
            return {'messages': [{'type': 'ERROR', 'text': 'An internal error occurred.'}]}

    def update_proxy_details(self, data):
        """Handle PUT requests to update proxy settings for existing integrations."""
        logger.info('PUT request started')
        # Small, linear flow: parse -> persist -> optional verify -> save creds -> respond
        proxy_request, validation_error = self._parse_proxy_request(data)
        if validation_error:
            self.response.setStatus(400)
            return validation_error

        proxy_doc = {
            'proxy_enabled': bool(proxy_request.proxy_enabled),
            'proxy_host': proxy_request.proxy_host,
            'proxy_port': proxy_request.proxy_port,
            'proxy_verify_ssl': bool(proxy_request.proxy_verify_ssl),
        }

        ok, err = self._persist_global_proxy(proxy_doc)
        if not ok:
            self.response.setStatus(500)
            return {'messages': [{'type': 'ERROR', 'text': 'Failed to save proxy configuration'}]}

        # Non-fatal verification (logs a warning only)
        self._verify_saved_proxy_nonfatal(proxy_doc)

        is_new_password = (proxy_request.proxy_password and proxy_request.proxy_password != '*****')

        if not proxy_request.proxy_enabled:
            self._delete_proxy_credentials()
        elif proxy_request.proxy_username and is_new_password:
            ok, err = self._save_proxy_credentials(proxy_request.proxy_username, proxy_request.proxy_password)
            if not ok:
                return {'status': 'partial', 'messages': [{'type': 'WARN', 'text': 'Proxy settings saved but failed to save credentials'}]}
        # else: proxy enabled — no new credentials submitted or sentinel returned — keep existing

        logger.info('Global proxy configuration updated successfully')
        return {'status': 'updated', 'messages': [{'type': 'INFO', 'text': 'Proxy configuration updated successfully'}]}

    @staticmethod
    def _parse_proxy_request(data):
        """Validate and parse proxy request payload. Returns (ProxyUpdateRequest, error_dict)."""
        try:
            proxy_request = ProxyUpdateRequest(**data)
            return proxy_request, None
        except ValidationError as e:
            error_msg = e.errors()[0]['msg']
            return None, {'messages': [{'type': 'ERROR', 'text': error_msg}], 'validation_failed': True}

    def _verify_saved_proxy_nonfatal(self, proxy_doc: dict) -> None:
        """Attempt to read back saved proxy and log a warning on mismatch; non-fatal."""
        try:
            saved = self.kv_store.get_global_proxy_config()
            if not saved or saved.get('proxy_host') != proxy_doc.get('proxy_host'):
                logger.warning('Post-save verification mismatch for global proxy (continuing)')
        except Exception:
            logger.warning('Could not verify saved proxy config; continuing')

    def _persist_global_proxy(self, proxy_doc: dict) -> tuple:
        """Persist global proxy doc to KV store; return (ok, error_message)."""
        try:
            existing = self.kv_store.get_global_proxy_config()
            if existing:
                self.kv_store.update_global_proxy_config(proxy_doc)
            else:
                self.kv_store.save_global_proxy_config(proxy_doc)
            return True, None
        except Exception as err:
            logger.error(f'Failed to persist global proxy configuration: {err}', exc_info=True)
            return False, str(err)

    def _save_proxy_credentials(self, username: str, password: str) -> tuple:
        """Save proxy credentials to Secrets Manager; return (ok, error_message)."""
        try:
            self.secrets_manager.save_proxy_credentials(APP_NAME, username, password)
            return True, None
        except Exception as err:
            logger.error(f'Failed to save proxy credentials: {err}', exc_info=True)
            return False, str(err)

    def _delete_proxy_credentials(self) -> None:
        """Delete proxy credentials from Secrets Manager when proxy is disabled or credentials are cleared."""
        try:
            self.secrets_manager.delete_proxy_credentials(APP_NAME)
            logger.info('Proxy credentials deleted successfully')
        except Exception as err:
            logger.warning(f'Failed to delete proxy credentials (non-fatal): {err}')

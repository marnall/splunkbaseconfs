#!/usr/bin/env python

import sys
import os
import json
import hashlib
import secrets
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ta_securitybridge", "aob_py3"))

import splunk
import splunk.admin as admin
import splunk.entity as en
from splunk.appserver.mrsparkle.lib import util
import splunk.rest as rest
import splunk.util as sutil
from solnlib import conf_manager
from solnlib import log
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'webhook_enabled',
        required=False,
        encrypted=False,
        default=False,
        validator=validator.Boolean()
    ),
    field.RestField(
        'hec_token',
        required=False,
        encrypted=True,
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
        'webhook_secret',
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            max_len=256,
            min_len=0,
        )
    ),
    field.RestField(
        'enable_signature_validation',
        required=False,
        encrypted=False,
        default=True,
        validator=validator.Boolean()
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
    ),
    field.RestField(
        'allowed_source_ips',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=1024,
            min_len=0,
        )
    ),
    field.RestField(
        'max_payload_size',
        required=False,
        encrypted=False,
        default=1048576,  # 1MB
        validator=validator.Number(
            max_val=10485760,  # 10MB
            min_val=1024,      # 1KB
        )
    ),
    field.RestField(
        'webhook_timeout',
        required=False,
        encrypted=False,
        default=30,
        validator=validator.Number(
            max_val=300,  # 5 minutes
            min_val=5,    # 5 seconds
        )
    ),
    field.RestField(
        'enable_detailed_logging',
        required=False,
        encrypted=False,
        default=False,
        validator=validator.Boolean()
    ),
    field.RestField(
        'webhook_url_display',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=4096,
            min_len=0,
        )
    )
]


model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_securitybridge_push_settings',
    model,
)


class PushSettingsHandler(AdminExternalHandler):
    """
    Custom handler for SAP Push API settings with HEC token management
    """

    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self.logger = log.Logs().get_logger('sap_push_settings')

    def handleCreate(self, confInfo):
        """Handle create request - create HEC token in Splunk"""
        try:
            session_key = self.getSessionKey()

            # Check if HEC token provided, if not create one
            hec_token = self.callerArgs.data.get('hec_token', [''])[0]
            if not hec_token:
                # Create HEC token in Splunk
                token_name = f"sap_securitybridge_push_{uuid.uuid4().hex[:8]}"
                target_index = self.callerArgs.data.get('target_index', ['main'])[0]

                created_token = self.create_hec_token(session_key, token_name, target_index)
                if created_token:
                    self.callerArgs.data['hec_token'] = [created_token]
                    self.callerArgs.data['hec_token_name'] = [token_name]
                    self.logger.info(f"Created HEC token: {token_name}")
                else:
                    self.logger.error("Failed to create HEC token")

            # Auto-generate webhook secret if signature validation is enabled
            enable_sig = self.callerArgs.data.get('enable_signature_validation', ['true'])[0]
            webhook_secret = self.callerArgs.data.get('webhook_secret', [''])[0]
            if str(enable_sig).lower() == 'true' and not webhook_secret:
                self.callerArgs.data['webhook_secret'] = [self.generate_webhook_secret()]
                self.logger.info("Auto-generated webhook secret for signature validation")

            # Generate display URL
            hec_url = self.callerArgs.data.get('hec_url', ['https://localhost:8088/services/collector'])[0]
            target_index = self.callerArgs.data.get('target_index', ['main'])[0]
            display_url = f"{hec_url}/raw?sourcetype=sapsb_push_json&index={target_index}"
            self.callerArgs.data['webhook_url_display'] = [display_url]

            AdminExternalHandler.handleCreate(self, confInfo)

        except Exception as e:
            self.logger.error(f"Error in handleCreate: {str(e)}")
            raise

    def handleEdit(self, confInfo):
        """Handle edit request with validation"""
        try:
            session_key = self.getSessionKey()

            # Check if we need to create a new HEC token
            hec_token = self.callerArgs.data.get('hec_token', [''])[0]
            if not hec_token or hec_token == '***HIDDEN***':
                # Get existing token from config
                existing_config = self.get_existing_config(session_key)
                if existing_config and existing_config.get('hec_token'):
                    # Keep existing token
                    self.callerArgs.data['hec_token'] = [existing_config['hec_token']]
                else:
                    # Create new token
                    token_name = f"sap_securitybridge_push_{uuid.uuid4().hex[:8]}"
                    target_index = self.callerArgs.data.get('target_index', ['main'])[0]
                    created_token = self.create_hec_token(session_key, token_name, target_index)
                    if created_token:
                        self.callerArgs.data['hec_token'] = [created_token]
                        self.callerArgs.data['hec_token_name'] = [token_name]

            # Handle webhook secret similarly
            webhook_secret = self.callerArgs.data.get('webhook_secret', [''])[0]
            if not webhook_secret or webhook_secret == '***HIDDEN***':
                existing_config = self.get_existing_config(session_key)
                if existing_config and existing_config.get('webhook_secret'):
                    self.callerArgs.data['webhook_secret'] = [existing_config['webhook_secret']]
                else:
                    enable_sig = self.callerArgs.data.get('enable_signature_validation', ['true'])[0]
                    if str(enable_sig).lower() == 'true':
                        self.callerArgs.data['webhook_secret'] = [self.generate_webhook_secret()]

            # Update display URL
            hec_url = self.callerArgs.data.get('hec_url', ['https://localhost:8088/services/collector'])[0]
            target_index = self.callerArgs.data.get('target_index', ['main'])[0]
            display_url = f"{hec_url}/raw?sourcetype=sapsb_push_json&index={target_index}"
            self.callerArgs.data['webhook_url_display'] = [display_url]

            # Validate HEC URL format
            if hec_url and not self.validate_hec_url(hec_url):
                raise admin.ArgValidationException("Invalid HEC URL format")

            # Validate IP addresses if provided
            allowed_ips = self.callerArgs.data.get('allowed_source_ips', [''])[0]
            if allowed_ips and not self.validate_ip_list(allowed_ips):
                raise admin.ArgValidationException("Invalid IP address format in allowed_source_ips")

            AdminExternalHandler.handleEdit(self, confInfo)

        except Exception as e:
            self.logger.error(f"Error in handleEdit: {str(e)}")
            raise

    def get_existing_config(self, session_key):
        """Get existing push settings configuration"""
        try:
            uri = '/servicesNS/nobody/TA-SecurityBridge/configs/conf-ta_securitybridge_push_settings/push_settings'
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
        except Exception as e:
            self.logger.debug(f"Could not get existing config: {str(e)}")
        return None

    def create_hec_token(self, session_key, token_name, index='main'):
        """Create HEC token in Splunk and return the token value"""
        try:
            # First, check if HEC is enabled
            self.enable_hec(session_key)

            # Create the HEC token
            uri = '/servicesNS/nobody/TA-SecurityBridge/data/inputs/http'

            postargs = {
                'name': token_name,
                'index': index,
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
                    self.logger.info(f"Successfully created HEC token: {token_name}")
                    return token_value
            else:
                self.logger.error(f"Failed to create HEC token: {response.status} - {content}")

        except Exception as e:
            self.logger.error(f"Error creating HEC token: {str(e)}")

        return None

    def enable_hec(self, session_key):
        """Enable HEC if not already enabled"""
        try:
            uri = '/servicesNS/nobody/TA-SecurityBridge/data/inputs/http/http'

            postargs = {
                'disabled': '0',
                'output_mode': 'json'
            }

            response, content = rest.simpleRequest(
                uri,
                sessionKey=session_key,
                method='POST',
                postargs=postargs
            )

            if response.status in [200, 201]:
                self.logger.info("HEC enabled successfully")
                return True
        except Exception as e:
            self.logger.debug(f"Could not enable HEC (may already be enabled): {str(e)}")

        return False

    def generate_webhook_secret(self):
        """Generate a secure webhook secret"""
        return secrets.token_urlsafe(32)  # 43-character URL-safe string

    def validate_hec_url(self, url):
        """Validate HEC URL format"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return (parsed.scheme in ['http', 'https'] and
                   parsed.netloc and
                   '/services/collector' in parsed.path)
        except Exception:
            return False

    def validate_ip_list(self, ip_list):
        """Validate comma-separated IP addresses"""
        if not ip_list.strip():
            return True  # Empty list is valid

        import ipaddress
        try:
            ips = [ip.strip() for ip in ip_list.split(',')]
            for ip in ips:
                # Try to parse as IP address or CIDR block
                ipaddress.ip_network(ip, strict=False)
            return True
        except Exception:
            return False

    def handleList(self, confInfo):
        """Handle list request with webhook URL generation"""
        AdminExternalHandler.handleList(self, confInfo)

        # Add computed fields and mask sensitive data
        for name, obj in confInfo.items():
            # Mask sensitive fields
            if obj.get('hec_token'):
                # Show last 4 characters only
                token = obj['hec_token']
                if len(token) > 4:
                    obj['hec_token_masked'] = f"****{token[-4:]}"
                else:
                    obj['hec_token_masked'] = '****'

            if obj.get('webhook_secret'):
                obj['webhook_secret'] = '***HIDDEN***'

            # Generate webhook URL for display
            hec_url = obj.get('hec_url', 'https://localhost:8088/services/collector')
            target_index = obj.get('target_index', 'main')
            obj['webhook_url_display'] = f"{hec_url}/raw?sourcetype=sapsb_push_json&index={target_index}"


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=PushSettingsHandler,
    )
